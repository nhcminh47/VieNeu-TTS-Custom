from __future__ import annotations

import pytest

from vieneu_server.config import ServerConfig
from vieneu_server.models.registry import ALLOWED_MODEL_IDS, is_allowed_model_id


def test_config_defaults():
    config = ServerConfig()
    assert config.backend == "torch"
    assert config.disable_lmdeploy is True
    assert config.disable_flash_attn is True
    assert config.disable_torch_compile is True


def test_config_merges_public_frontend_origin(monkeypatch):
    monkeypatch.setenv("VIENEU_PUBLIC_FRONTEND_ORIGIN", "https://tts.olieycantho.vn")
    config = ServerConfig.from_env()
    assert "http://localhost:3000" in config.cors_origins
    assert "https://tts.olieycantho.vn" in config.cors_origins
    assert config.max_concurrent_jobs == 1


def test_config_rejects_unsupported_backend():
    config = ServerConfig(backend="lmdeploy")
    with pytest.raises(ValueError):
        config.validate()


def test_model_registry_allows_only_vieneu_models():
    assert all(is_allowed_model_id(model_id) for model_id in ALLOWED_MODEL_IDS)
    assert not is_allowed_model_id("openai/tts")
    assert not is_allowed_model_id("pnnbao-ump/Other-Model")


def test_config_rejects_non_vieneu_model():
    config = ServerConfig(model_id="openai/tts")
    with pytest.raises(ValueError):
        config.validate()
