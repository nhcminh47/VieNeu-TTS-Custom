from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from ..config import ServerConfig
from ..inference.engine import TtsEngine, TtsRequest
from ..models.registry import is_allowed_model_id
from .events import JobEvent
from .queue import JobRecord, JobStatus
from .storage import OutputStorage


logger = logging.getLogger("vieneu_server.jobs")


class JobManager:
    def __init__(self, config: ServerConfig, engine: TtsEngine, semaphore: asyncio.Semaphore | None = None):
        self.config = config
        self.engine = engine
        self.storage = OutputStorage(config.output_dir, config.max_output_files, config.max_output_bytes)
        self.jobs: dict[str, JobRecord] = {}
        self._subscribers: dict[str, list[asyncio.Queue[JobEvent]]] = {}
        self._semaphore = semaphore or asyncio.Semaphore(config.max_concurrent_jobs)
        self._loop: asyncio.AbstractEventLoop | None = None

    def create_job(
        self,
        text: str,
        model_id: str,
        voice_reference_id: str | None = None,
        voice_reference_path: Path | None = None,
        format_name: str = "wav",
    ) -> JobRecord:
        if len(text) > self.config.max_text_length:
            raise ValueError(f"text exceeds maximum length of {self.config.max_text_length}")
        if not is_allowed_model_id(model_id):
            raise ValueError(f"Unsupported VieNeu model id: {model_id}")
        if format_name.lower() != "wav":
            raise ValueError("Only wav output is supported.")

        job_id = str(uuid4())
        job = JobRecord(
            job_id=job_id,
            text=text,
            model_id=model_id,
            status=JobStatus.QUEUED,
            voice_reference_id=voice_reference_id,
            voice_reference_path=voice_reference_path,
            format=format_name.lower(),
        )
        self.jobs[job_id] = job
        self._publish(job_id, JobEvent("job.status", job_id, job.status.value, 0.0, "Queued"))
        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)

    def start_job(self, job_id: str) -> asyncio.Task[None]:
        self._loop = asyncio.get_running_loop()
        return asyncio.create_task(self._run_job(job_id))

    async def _run_job(self, job_id: str) -> None:
        job = self.jobs[job_id]
        async with self._semaphore:
            try:
                self._set_status(job, JobStatus.RUNNING, 0.1, "Running")
                output_path = self.storage.path_for(job.job_id, job.format)
                request = TtsRequest(
                    text=job.text,
                    model_id=job.model_id,
                    output_path=output_path,
                    voice_reference_id=job.voice_reference_id,
                    voice_reference_path=job.voice_reference_path,
                    format=job.format,
                )

                def progress(value: float, message: str) -> None:
                    job.progress = value
                    logger.info(
                        "job_id=%s status=%s progress=%d%% message=%s",
                        job.job_id,
                        job.status.value,
                        round(value * 100),
                        message,
                    )
                    self._publish(job.job_id, JobEvent("job.status", job.job_id, job.status.value, value, message))

                result = await asyncio.to_thread(self.engine.synthesize, request, progress)
                job.audio_path = result.audio_path
                job.audio_url = f"/tts/jobs/{job.job_id}/audio"
                self._set_status(job, JobStatus.COMPLETED, 1.0, "Completed")
                self._prune_outputs(protected={result.audio_path})
            except Exception as exc:
                job.error = str(exc)
                self._set_status(job, JobStatus.FAILED, job.progress, str(exc))

    async def subscribe(self, job_id: str) -> asyncio.Queue[JobEvent]:
        queue: asyncio.Queue[JobEvent] = asyncio.Queue()
        self._subscribers.setdefault(job_id, []).append(queue)
        job = self.get_job(job_id)
        if job:
            event_type = "job.completed" if job.status == JobStatus.COMPLETED else "job.failed" if job.status == JobStatus.FAILED else "job.status"
            await queue.put(JobEvent(event_type, job.job_id, job.status.value, job.progress, audio_url=job.audio_url, error=job.error))
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[JobEvent]) -> None:
        subscribers = self._subscribers.get(job_id)
        if not subscribers:
            return
        if queue in subscribers:
            subscribers.remove(queue)
        if not subscribers:
            self._subscribers.pop(job_id, None)

    def _set_status(self, job: JobRecord, status: JobStatus, progress: float, message: str) -> None:
        job.status = status
        job.progress = progress
        logger.info(
            "job_id=%s status=%s progress=%d%% message=%s",
            job.job_id,
            status.value,
            round(progress * 100),
            message,
        )
        event_type = "job.completed" if status == JobStatus.COMPLETED else "job.failed" if status == JobStatus.FAILED else "job.status"
        self._publish(job.job_id, JobEvent(event_type, job.job_id, status.value, progress, message, job.audio_url, job.error))

    def _publish(self, job_id: str, event: JobEvent) -> None:
        for queue in self._subscribers.get(job_id, []):
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(queue.put_nowait, event)
            else:
                queue.put_nowait(event)

    def _prune_outputs(self, protected: set[Path] | None = None) -> None:
        deleted = {path.resolve() for path in self.storage.prune(protected=protected)}
        if not deleted:
            return
        for job in self.jobs.values():
            if job.audio_path and job.audio_path.resolve() in deleted:
                job.audio_path = None
                job.audio_url = None
                self._publish(
                    job.job_id,
                    JobEvent("job.status", job.job_id, job.status.value, job.progress, "Audio removed by storage retention"),
                )
