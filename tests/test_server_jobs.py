from __future__ import annotations

import asyncio

import numpy as np

from vieneu_server.audio.io import write_wav
from vieneu_server.config import ServerConfig
from vieneu_server.inference.engine import TtsEngine, TtsRequest, TtsResult
from vieneu_server.jobs.manager import JobManager
from vieneu_server.jobs.queue import JobStatus


class FakeEngine(TtsEngine):
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.requests: list[TtsRequest] = []

    def load(self, model_id: str | None = None) -> None:
        return None

    def synthesize(self, request: TtsRequest, progress=None) -> TtsResult:
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("synthesis failed")
        if progress:
            progress(0.5, "half")
        write_wav(request.output_path, np.zeros(240, dtype=np.float32))
        return TtsResult(audio_path=request.output_path)

    def unload(self) -> None:
        return None


def test_job_manager_completed(tmp_path):
    config = ServerConfig(output_dir=tmp_path)
    manager = JobManager(config, FakeEngine())
    job = manager.create_job("Xin chao", config.model_id)
    asyncio.run(manager._run_job(job.job_id))
    completed = manager.get_job(job.job_id)
    assert completed is not None
    assert completed.status == JobStatus.COMPLETED
    assert completed.audio_path is not None
    assert completed.audio_path.exists()
    assert completed.audio_url == f"/tts/jobs/{job.job_id}/audio"


def test_job_manager_failed(tmp_path):
    config = ServerConfig(output_dir=tmp_path)
    manager = JobManager(config, FakeEngine(fail=True))
    job = manager.create_job("Xin chao", config.model_id)
    asyncio.run(manager._run_job(job.job_id))
    failed = manager.get_job(job.job_id)
    assert failed is not None
    assert failed.status == JobStatus.FAILED
    assert failed.error == "synthesis failed"


def test_job_manager_default_concurrency(tmp_path):
    config = ServerConfig(output_dir=tmp_path)
    manager = JobManager(config, FakeEngine())
    assert manager.config.max_concurrent_jobs == 1


def test_job_manager_prunes_old_completed_audio(tmp_path):
    config = ServerConfig(output_dir=tmp_path, max_output_files=1, max_output_bytes=0)
    manager = JobManager(config, FakeEngine())

    first = manager.create_job("Xin chao", config.model_id)
    asyncio.run(manager._run_job(first.job_id))
    second = manager.create_job("Xin chao lan hai", config.model_id)
    asyncio.run(manager._run_job(second.job_id))

    first_completed = manager.get_job(first.job_id)
    second_completed = manager.get_job(second.job_id)
    assert first_completed is not None
    assert second_completed is not None
    assert first_completed.status == JobStatus.COMPLETED
    assert first_completed.audio_path is None
    assert first_completed.audio_url is None
    assert second_completed.audio_path is not None
    assert second_completed.audio_path.exists()
    assert second_completed.audio_url == f"/tts/jobs/{second.job_id}/audio"


def test_job_manager_publishes_worker_thread_progress(tmp_path):
    async def run() -> list[str | None]:
        config = ServerConfig(output_dir=tmp_path)
        manager = JobManager(config, FakeEngine())
        job = manager.create_job("Xin chao", config.model_id)
        queue = await manager.subscribe(job.job_id)
        task = manager.start_job(job.job_id)
        messages: list[str | None] = []
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=2)
            messages.append(event.message)
            if event.type == "job.completed":
                break
        await task
        return messages

    messages = asyncio.run(run())
    assert "Running" in messages
    assert "half" in messages
    assert "Completed" in messages
