from __future__ import annotations

import asyncio

import numpy as np

from vieneu_server.audio.io import write_wav
from vieneu_server.config import ServerConfig
from vieneu_server.inference.engine import TtsEngine, TtsRequest, TtsResult
from vieneu_server.jobs.chapter import ChapterJobManager, normalize_chapter_text, split_chapter_text
from vieneu_server.jobs.queue import JobStatus


class FakeEngine(TtsEngine):
    def __init__(self):
        self.requests: list[TtsRequest] = []

    def load(self, model_id: str | None = None) -> None:
        return None

    def synthesize(self, request: TtsRequest, progress=None) -> TtsResult:
        self.requests.append(request)
        if progress:
            progress(1.0, "segment done")
        write_wav(request.output_path, np.ones(240, dtype=np.float32))
        return TtsResult(audio_path=request.output_path)

    def unload(self) -> None:
        return None


def test_split_chapter_text_preserves_sentence_groups():
    text = "Cau mot rat ngan. Cau hai cung ngan.\n\nDoan hai bat dau o day. Ket thuc."
    segments = split_chapter_text(text, 32)
    assert len(segments) >= 2
    assert all(segment for segment in segments)
    assert segments[0].endswith(".")


def test_normalize_chapter_text_sanitizes_control_chars_and_blank_lines():
    text = "  Dong mot.\r\n\r\n\r\nDong\x00 hai.  \t Ket thuc.  "
    normalized = normalize_chapter_text(text)
    assert normalized == "Dong mot.\n\nDong hai. Ket thuc."


def test_chapter_job_manager_completed(tmp_path):
    config = ServerConfig(output_dir=tmp_path, tts_max_chars=28)
    engine = FakeEngine()
    manager = ChapterJobManager(config, engine)
    job = manager.create_job("Cau mot rat ngan. Cau hai cung ngan.\n\nCau ba.", config.model_id, title="Chapter 1")

    assert job.paragraph_count == 2
    assert job.segments[0].paragraph_index == 1
    assert job.segments[-1].paragraph_index == 2

    asyncio.run(manager._run_job(job.job_id))

    completed = manager.get_job(job.job_id)
    assert completed is not None
    assert completed.status == JobStatus.COMPLETED
    assert completed.audio_path is not None
    assert completed.audio_path.exists()
    assert completed.audio_url == f"/tts/chapter-jobs/{job.job_id}/audio"
    assert completed.manifest_path is not None
    assert completed.manifest_path.exists()
    assert '"paragraph_count": 2' in completed.manifest_path.read_text(encoding="utf-8")
    assert len(engine.requests) == len(completed.segments)
