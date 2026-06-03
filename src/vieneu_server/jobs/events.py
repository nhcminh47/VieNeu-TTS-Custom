from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobEvent:
    type: str
    job_id: str
    status: str
    progress: float
    message: str | None = None
    audio_url: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type,
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
        }
        if self.message is not None:
            data["message"] = self.message
        data["audio_url"] = self.audio_url
        if self.error is not None:
            data["error"] = self.error
        return data
