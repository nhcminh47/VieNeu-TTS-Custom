from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobRecord:
    job_id: str
    text: str
    model_id: str
    status: JobStatus
    progress: float = 0.0
    audio_path: Path | None = None
    audio_url: str | None = None
    error: str | None = None
    voice_reference_id: str | None = None
    voice_reference_path: Path | None = None
    format: str = "wav"

    def as_dict(self) -> dict[str, object | None]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "audio_url": self.audio_url,
            "error": self.error,
        }
