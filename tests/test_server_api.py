from __future__ import annotations

import asyncio

import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch

from vieneu_server.audio.io import write_wav
from vieneu_server.config import ServerConfig
from vieneu_server.inference.engine import TtsEngine, TtsRequest, TtsResult
from vieneu_server.jobs.queue import JobStatus
from vieneu_server.main import create_app
from vieneu_server.runtime.device import get_runtime_device


class FakeEngine(TtsEngine):
    def __init__(self):
        self.requests: list[TtsRequest] = []

    def load(self, model_id: str | None = None) -> None:
        return None

    def synthesize(self, request: TtsRequest, progress=None) -> TtsResult:
        self.requests.append(request)
        if progress:
            progress(0.6, "fake progress")
        write_wav(request.output_path, np.zeros(240, dtype=np.float32))
        return TtsResult(audio_path=request.output_path)

    def unload(self) -> None:
        return None


def make_client(tmp_path, engine: TtsEngine | None = None):
    config = ServerConfig(output_dir=tmp_path)
    app = create_app(config=config, engine=engine or FakeEngine(), runtime=get_runtime_device(device="cpu"))
    return TestClient(app)


def test_health_runtime_models(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/health").json()["service"] == "vieneu-server"
    runtime = client.get("/runtime").json()
    assert runtime["backend"] == "torch"
    assert runtime["lmdeploy_enabled"] is False
    models = client.get("/models").json()
    assert any(item["id"] == "pnnbao-ump/VieNeu-TTS-v2-Turbo" for item in models)


def test_storage_info(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/storage")
    assert response.status_code == 200
    body = response.json()
    assert body["file_count"] == 0
    assert body["total_bytes"] == 0
    assert body["max_files"] == 100
    assert body["max_bytes"] == 2147483648


def test_cors_allows_next_frontend_origin(tmp_path):
    client = make_client(tmp_path)
    response = client.options(
        "/models",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_model_voices(tmp_path):
    client = make_client(tmp_path)
    with patch(
        "vieneu_server.api.http.list_model_voices",
        return_value=[{"id": "voice_a", "description": "Voice A", "text": "Xin chao", "default": True}],
    ):
        response = client.get("/models/pnnbao-ump/VieNeu-TTS-v2/voices")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "voice_a"


def test_model_voices_rejects_unknown_model(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/models/openai/tts/voices")
    assert response.status_code == 404


def test_create_and_get_job(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/tts/jobs", json={"text": "Xin chao"})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    status = client.get(f"/tts/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["job_id"] == job_id


def test_create_and_get_chapter_job(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/tts/chapter-jobs", json={"title": "Chapter 1", "text": "Cau mot. Cau hai.\n\nCau ba."})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    status = client.get(f"/tts/chapter-jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["job_id"] == job_id
    assert body["title"] == "Chapter 1"
    assert body["paragraph_count"] == 2
    assert body["segment_count"] >= 1
    assert body["segments"][0]["paragraph_index"] == 1


def test_unknown_job_returns_404(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/tts/jobs/missing").status_code == 404
    assert client.get("/tts/jobs/missing/audio").status_code == 404


def test_audio_endpoint_for_completed_job(tmp_path):
    client = make_client(tmp_path)
    manager = client.app.state.job_manager
    job = manager.create_job("Xin chao", client.app.state.config.model_id)
    asyncio.run(manager._run_job(job.job_id))
    response = client.get(f"/tts/jobs/{job.job_id}/audio")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")


def test_chapter_audio_endpoint_for_completed_job(tmp_path):
    client = make_client(tmp_path)
    manager = client.app.state.chapter_job_manager
    job = manager.create_job("Cau mot. Cau hai.", client.app.state.config.model_id, title="Chapter 1")
    asyncio.run(manager._run_job(job.job_id))
    response = client.get(f"/tts/chapter-jobs/{job.job_id}/audio")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")

    manifest = client.get(f"/tts/chapter-jobs/{job.job_id}/manifest")
    assert manifest.status_code == 200
    assert manifest.headers["content-type"].startswith("application/json")
    assert manifest.json()["job_id"] == job.job_id


def test_audio_endpoint_for_retained_job_without_file_returns_gone(tmp_path):
    client = make_client(tmp_path)
    manager = client.app.state.job_manager
    job = manager.create_job("Xin chao", client.app.state.config.model_id)
    asyncio.run(manager._run_job(job.job_id))
    job.audio_path.unlink()
    job.audio_path = None
    job.audio_url = None

    response = client.get(f"/tts/jobs/{job.job_id}/audio")
    assert response.status_code == 410


def test_websocket_terminal_event_shape(tmp_path):
    client = make_client(tmp_path)
    manager = client.app.state.job_manager
    job = manager.create_job("Xin chao", client.app.state.config.model_id)
    asyncio.run(manager._run_job(job.job_id))

    with client.websocket_connect(f"/ws/jobs/{job.job_id}") as ws:
        event = ws.receive_json()
        assert event["type"] == "job.completed"
        assert event["job_id"] == job.job_id
        assert event["status"] == JobStatus.COMPLETED.value
