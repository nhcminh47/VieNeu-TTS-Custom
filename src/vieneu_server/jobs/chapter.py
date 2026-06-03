from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from uuid import uuid4

import numpy as np
import soundfile as sf

from ..audio.io import write_wav
from ..config import ServerConfig
from ..inference.engine import TtsEngine, TtsRequest
from ..models.registry import is_allowed_model_id
from .events import JobEvent
from .queue import JobStatus


logger = logging.getLogger("vieneu_server.chapter")


class SegmentStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ChapterSegment:
    index: int
    paragraph_index: int
    paragraph_segment_index: int
    paragraph_segment_count: int
    text: str
    status: SegmentStatus = SegmentStatus.QUEUED
    progress: float = 0.0
    audio_path: Path | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, object | None]:
        return {
            "index": self.index,
            "paragraph_index": self.paragraph_index,
            "paragraph_segment_index": self.paragraph_segment_index,
            "paragraph_segment_count": self.paragraph_segment_count,
            "text_length": len(self.text),
            "status": self.status.value,
            "progress": self.progress,
            "audio_path": str(self.audio_path) if self.audio_path else None,
            "error": self.error,
        }


@dataclass
class ChapterJobRecord:
    job_id: str
    title: str
    text: str
    normalized_text: str
    model_id: str
    segments: list[ChapterSegment]
    paragraph_count: int
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    audio_path: Path | None = None
    audio_url: str | None = None
    manifest_path: Path | None = None
    error: str | None = None
    voice_reference_id: str | None = None
    voice_reference_path: Path | None = None
    format: str = "wav"

    def as_dict(self) -> dict[str, object | None]:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "status": self.status.value,
            "progress": self.progress,
            "audio_url": self.audio_url,
            "error": self.error,
            "paragraph_count": self.paragraph_count,
            "segment_count": len(self.segments),
            "completed_segments": sum(1 for segment in self.segments if segment.status == SegmentStatus.COMPLETED),
            "failed_segments": sum(1 for segment in self.segments if segment.status == SegmentStatus.FAILED),
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "segments": [segment.as_dict() for segment in self.segments],
        }

    def manifest(self) -> dict[str, object | None]:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "status": self.status.value,
            "progress": self.progress,
            "model_id": self.model_id,
            "format": self.format,
            "raw_text_length": len(self.text),
            "normalized_text_length": len(self.normalized_text),
            "paragraph_count": self.paragraph_count,
            "segment_count": len(self.segments),
            "completed_segments": sum(1 for segment in self.segments if segment.status == SegmentStatus.COMPLETED),
            "failed_segments": sum(1 for segment in self.segments if segment.status == SegmentStatus.FAILED),
            "audio_path": str(self.audio_path) if self.audio_path else None,
            "audio_url": self.audio_url,
            "error": self.error,
            "segments": [segment.as_dict() for segment in self.segments],
        }


class ChapterJobManager:
    def __init__(self, config: ServerConfig, engine: TtsEngine, semaphore: asyncio.Semaphore | None = None):
        self.config = config
        self.engine = engine
        self.jobs: dict[str, ChapterJobRecord] = {}
        self._subscribers: dict[str, list[asyncio.Queue[JobEvent]]] = {}
        self._semaphore = semaphore or asyncio.Semaphore(config.max_concurrent_jobs)
        self._loop: asyncio.AbstractEventLoop | None = None

    def create_job(
        self,
        text: str,
        model_id: str,
        title: str | None = None,
        voice_reference_id: str | None = None,
        voice_reference_path: Path | None = None,
        format_name: str = "wav",
    ) -> ChapterJobRecord:
        normalized_text = normalize_chapter_text(text)
        if len(normalized_text) > self.config.max_chapter_text_length:
            raise ValueError(f"text exceeds maximum chapter length of {self.config.max_chapter_text_length}")
        if not is_allowed_model_id(model_id):
            raise ValueError(f"Unsupported VieNeu model id: {model_id}")
        if format_name.lower() != "wav":
            raise ValueError("Only wav output is supported.")

        paragraphs = split_chapter_paragraphs(normalized_text)
        segments = build_chapter_segments(paragraphs, self.config.tts_max_chars)
        if not segments:
            raise ValueError("chapter text must contain readable text")

        job_id = str(uuid4())
        job = ChapterJobRecord(
            job_id=job_id,
            title=title or "Novel chapter",
            text=text,
            normalized_text=normalized_text,
            model_id=model_id,
            segments=segments,
            paragraph_count=len(paragraphs),
            voice_reference_id=voice_reference_id,
            voice_reference_path=voice_reference_path,
            format=format_name.lower(),
        )
        self.jobs[job_id] = job
        self._publish(job_id, JobEvent("chapter.status", job_id, job.status.value, 0.0, f"Queued {len(paragraphs)} paragraphs / {len(segments)} chunks"))
        return job

    def get_job(self, job_id: str) -> ChapterJobRecord | None:
        return self.jobs.get(job_id)

    def start_job(self, job_id: str) -> asyncio.Task[None]:
        self._loop = asyncio.get_running_loop()
        return asyncio.create_task(self._run_job(job_id))

    async def _run_job(self, job_id: str) -> None:
        job = self.jobs[job_id]
        async with self._semaphore:
            try:
                self._set_status(job, JobStatus.RUNNING, 0.01, f"Processing {len(job.segments)} segments")
                output_dir = self.config.output_dir / job.job_id
                output_dir.mkdir(parents=True, exist_ok=True)
                job.manifest_path = output_dir / "manifest.json"
                self._write_manifest(job)

                for segment in job.segments:
                    await asyncio.to_thread(self._run_segment, job, segment, output_dir)

                final_path = output_dir / "chapter.wav"
                self._set_status(job, JobStatus.RUNNING, 0.99, "Merging chapter audio")
                self._merge_segments(job, final_path)
                job.audio_path = final_path
                job.audio_url = f"/tts/chapter-jobs/{job.job_id}/audio"
                self._set_status(job, JobStatus.COMPLETED, 1.0, "Chapter completed")
            except Exception as exc:
                job.error = str(exc)
                self._set_status(job, JobStatus.FAILED, job.progress, str(exc))

    def _run_segment(self, job: ChapterJobRecord, segment: ChapterSegment, output_dir: Path) -> None:
        segment.status = SegmentStatus.RUNNING
        segment_label = self._segment_label(segment, len(job.segments))
        self._update_parent_progress(job, f"{segment_label} running")
        paragraph_dir = output_dir / f"paragraph-{segment.paragraph_index:03d}"
        paragraph_dir.mkdir(parents=True, exist_ok=True)
        output_path = paragraph_dir / f"{segment.paragraph_segment_index:03d}.wav"

        def progress(value: float, message: str) -> None:
            segment.progress = value
            self._update_parent_progress(job, f"{segment_label}: {message}")

        try:
            result = self.engine.synthesize(
                TtsRequest(
                    text=segment.text,
                    model_id=job.model_id,
                    output_path=output_path,
                    voice_reference_id=job.voice_reference_id,
                    voice_reference_path=job.voice_reference_path,
                    format=job.format,
                ),
                progress=progress,
            )
            segment.status = SegmentStatus.COMPLETED
            segment.progress = 1.0
            segment.audio_path = result.audio_path
            self._update_parent_progress(job, f"{segment_label} completed")
        except Exception as exc:
            segment.status = SegmentStatus.FAILED
            segment.error = str(exc)
            self._write_manifest(job)
            raise

    def _merge_segments(self, job: ChapterJobRecord, final_path: Path) -> None:
        chunks: list[np.ndarray] = []
        sample_rate = 24_000
        chunk_silence_seconds = self.config.tts_silence_seconds
        paragraph_silence_seconds = max(self.config.tts_silence_seconds * 1.8, self.config.tts_silence_seconds + 0.12)
        for index, segment in enumerate(job.segments):
            if segment.audio_path is None:
                raise RuntimeError(f"segment {segment.index} missing audio")
            audio, sample_rate = sf.read(str(segment.audio_path), dtype="float32", always_2d=False)
            chunks.append(np.asarray(audio, dtype=np.float32))
            next_segment = job.segments[index + 1] if index + 1 < len(job.segments) else None
            if next_segment is not None:
                silence_seconds = paragraph_silence_seconds if next_segment.paragraph_index != segment.paragraph_index else chunk_silence_seconds
                chunks.append(np.zeros(int(sample_rate * silence_seconds), dtype=np.float32))
        final_audio = np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)
        write_wav(final_path, final_audio, sample_rate)

    async def subscribe(self, job_id: str) -> asyncio.Queue[JobEvent]:
        queue: asyncio.Queue[JobEvent] = asyncio.Queue()
        self._subscribers.setdefault(job_id, []).append(queue)
        job = self.get_job(job_id)
        if job:
            event_type = "chapter.completed" if job.status == JobStatus.COMPLETED else "chapter.failed" if job.status == JobStatus.FAILED else "chapter.status"
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

    def _update_parent_progress(self, job: ChapterJobRecord, message: str) -> None:
        completed = sum(1 for segment in job.segments if segment.status == SegmentStatus.COMPLETED)
        running_progress = sum(segment.progress for segment in job.segments if segment.status == SegmentStatus.RUNNING)
        total = max(len(job.segments), 1)
        job.progress = min(0.98, (completed + running_progress) / total)
        logger.info("chapter_id=%s status=%s progress=%d%% message=%s", job.job_id, job.status.value, round(job.progress * 100), message)
        self._write_manifest(job)
        self._publish(job.job_id, JobEvent("chapter.status", job.job_id, job.status.value, job.progress, message))

    def _set_status(self, job: ChapterJobRecord, status: JobStatus, progress: float, message: str) -> None:
        job.status = status
        job.progress = progress
        logger.info("chapter_id=%s status=%s progress=%d%% message=%s", job.job_id, status.value, round(progress * 100), message)
        self._write_manifest(job)
        event_type = "chapter.completed" if status == JobStatus.COMPLETED else "chapter.failed" if status == JobStatus.FAILED else "chapter.status"
        self._publish(job.job_id, JobEvent(event_type, job.job_id, status.value, progress, message, job.audio_url, job.error))

    def _publish(self, job_id: str, event: JobEvent) -> None:
        for queue in self._subscribers.get(job_id, []):
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(queue.put_nowait, event)
            else:
                queue.put_nowait(event)

    def _write_manifest(self, job: ChapterJobRecord) -> None:
        if job.manifest_path is None:
            return
        job.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = job.manifest_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(job.manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(job.manifest_path)

    @staticmethod
    def _segment_label(segment: ChapterSegment, total_segments: int) -> str:
        return (
            f"Paragraph {segment.paragraph_index} chunk "
            f"{segment.paragraph_segment_index}/{segment.paragraph_segment_count} "
            f"(segment {segment.index}/{total_segments})"
        )


CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?\u3002\uff01\uff1f\u2026])\s+")
SOFT_BOUNDARY_RE = re.compile(r"(?<=[,;:\uff0c\uff1b\uff1a])\s*")


def normalize_chapter_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = CONTROL_CHARS_RE.sub(" ", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def split_chapter_paragraphs(text: str) -> list[str]:
    normalized = normalize_chapter_text(text)
    return [item.strip() for item in re.split(r"\n\s*\n+", normalized) if item.strip()]


def build_chapter_segments(paragraphs: list[str], target_chars: int) -> list[ChapterSegment]:
    segments: list[ChapterSegment] = []
    segment_index = 1
    for paragraph_index, paragraph in enumerate(paragraphs, start=1):
        chunks = split_paragraph_text(paragraph, target_chars)
        chunk_count = len(chunks)
        for chunk_index, chunk in enumerate(chunks, start=1):
            segments.append(
                ChapterSegment(
                    index=segment_index,
                    paragraph_index=paragraph_index,
                    paragraph_segment_index=chunk_index,
                    paragraph_segment_count=chunk_count,
                    text=chunk,
                )
            )
            segment_index += 1
    return segments


def split_chapter_text(text: str, target_chars: int) -> list[str]:
    segments: list[str] = []
    for paragraph in split_chapter_paragraphs(text):
        segments.extend(split_paragraph_text(paragraph, target_chars))
    return segments


def split_paragraph_text(paragraph: str, target_chars: int) -> list[str]:
    segments: list[str] = []
    sentences = [item.strip() for item in SENTENCE_BOUNDARY_RE.split(paragraph) if item.strip()]
    if not sentences:
        sentences = [paragraph]
    current = ""
    for sentence in sentences:
        if len(sentence) > target_chars * 2:
            if current:
                segments.append(current)
                current = ""
            segments.extend(_split_long_sentence(sentence, target_chars))
            continue
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > target_chars:
            segments.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        segments.append(current)
    return segments


def _split_long_sentence(sentence: str, target_chars: int) -> list[str]:
    parts = [item.strip() for item in SOFT_BOUNDARY_RE.split(sentence) if item.strip()]
    segments: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current} {part}".strip()
        if current and len(candidate) > target_chars:
            segments.append(current)
            current = part
        else:
            current = candidate
    if current:
        segments.append(current)
    return _split_oversized_parts(segments, target_chars)


def _split_oversized_parts(parts: list[str], target_chars: int) -> list[str]:
    max_chars = max(target_chars * 2, target_chars + 1)
    segments: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            segments.append(part)
            continue
        words = part.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > target_chars:
                segments.append(current)
                current = word
            else:
                current = candidate
        if current:
            segments.append(current)
    return segments
