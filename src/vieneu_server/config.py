from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .models.registry import DEFAULT_MODEL_ID, is_allowed_model_id


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _cors_origins_from_env() -> tuple[str, ...]:
    origins = list(_env_list("VIENEU_CORS_ORIGINS", ("http://localhost:3000", "http://127.0.0.1:3000")))
    public_frontend_origin = os.getenv("VIENEU_PUBLIC_FRONTEND_ORIGIN", "").strip().rstrip("/")
    if public_frontend_origin and public_frontend_origin not in origins:
        origins.append(public_frontend_origin)
    return tuple(origins)


@dataclass(frozen=True)
class ServerConfig:
    backend: str = "torch"
    disable_lmdeploy: bool = True
    disable_flash_attn: bool = True
    disable_torch_compile: bool = True
    device: str = "auto"
    dtype: str = "auto"
    model_id: str = DEFAULT_MODEL_ID
    model_cache_dir: Path = Path("./models")
    output_dir: Path = Path("./outputs")
    max_output_files: int = 100
    max_output_bytes: int = 2 * 1024 * 1024 * 1024
    max_text_length: int = 3000
    max_chapter_text_length: int = 120_000
    max_concurrent_jobs: int = 1
    tts_max_chars: int = 180
    tts_temperature: float = 0.4
    tts_top_k: int = 50
    tts_silence_seconds: float = 0.18
    tts_crossfade_seconds: float = 0.015
    tts_apply_watermark: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")

    @classmethod
    def from_env(cls) -> "ServerConfig":
        model_id = os.getenv("VIENEU_MODEL_ID", DEFAULT_MODEL_ID)
        if not is_allowed_model_id(model_id):
            raise ValueError(f"Unsupported VieNeu model id: {model_id}")

        return cls(
            backend=os.getenv("VIENEU_BACKEND", "torch").strip().lower(),
            disable_lmdeploy=_env_bool("VIENEU_DISABLE_LMDEPLOY", True),
            disable_flash_attn=_env_bool("VIENEU_DISABLE_FLASH_ATTN", True),
            disable_torch_compile=_env_bool("VIENEU_DISABLE_TORCH_COMPILE", True),
            device=os.getenv("VIENEU_DEVICE", "auto").strip().lower(),
            dtype=os.getenv("VIENEU_DTYPE", "auto").strip().lower(),
            model_id=model_id,
            model_cache_dir=Path(os.getenv("VIENEU_MODEL_CACHE_DIR", "./models")),
            output_dir=Path(os.getenv("VIENEU_OUTPUT_DIR", "./outputs")),
            max_output_files=_env_int("VIENEU_MAX_OUTPUT_FILES", 100),
            max_output_bytes=_env_int("VIENEU_MAX_OUTPUT_BYTES", 2 * 1024 * 1024 * 1024),
            max_text_length=_env_int("VIENEU_MAX_TEXT_LENGTH", 3000),
            max_chapter_text_length=_env_int("VIENEU_MAX_CHAPTER_TEXT_LENGTH", 120_000),
            max_concurrent_jobs=_env_int("VIENEU_MAX_CONCURRENT_JOBS", 1),
            tts_max_chars=_env_int("VIENEU_TTS_MAX_CHARS", 180),
            tts_temperature=_env_float("VIENEU_TTS_TEMPERATURE", 0.4),
            tts_top_k=_env_int("VIENEU_TTS_TOP_K", 50),
            tts_silence_seconds=_env_float("VIENEU_TTS_SILENCE_SECONDS", 0.18),
            tts_crossfade_seconds=_env_float("VIENEU_TTS_CROSSFADE_SECONDS", 0.015),
            tts_apply_watermark=_env_bool("VIENEU_TTS_APPLY_WATERMARK", True),
            host=os.getenv("VIENEU_HOST", "127.0.0.1"),
            port=_env_int("VIENEU_PORT", 8000),
            cors_origins=_cors_origins_from_env(),
        )

    def validate(self) -> None:
        if self.backend != "torch":
            raise ValueError("Only the torch backend is supported by the server MVP.")
        if self.max_text_length <= 0:
            raise ValueError("VIENEU_MAX_TEXT_LENGTH must be positive.")
        if self.max_chapter_text_length <= 0:
            raise ValueError("VIENEU_MAX_CHAPTER_TEXT_LENGTH must be positive.")
        if self.max_concurrent_jobs <= 0:
            raise ValueError("VIENEU_MAX_CONCURRENT_JOBS must be positive.")
        if self.max_output_files < 0:
            raise ValueError("VIENEU_MAX_OUTPUT_FILES must be zero or positive.")
        if self.max_output_bytes < 0:
            raise ValueError("VIENEU_MAX_OUTPUT_BYTES must be zero or positive.")
        if self.tts_max_chars <= 0:
            raise ValueError("VIENEU_TTS_MAX_CHARS must be positive.")
        if not 0 < self.tts_temperature <= 2:
            raise ValueError("VIENEU_TTS_TEMPERATURE must be between 0 and 2.")
        if self.tts_top_k <= 0:
            raise ValueError("VIENEU_TTS_TOP_K must be positive.")
        if self.tts_silence_seconds < 0:
            raise ValueError("VIENEU_TTS_SILENCE_SECONDS must be zero or positive.")
        if self.tts_crossfade_seconds < 0:
            raise ValueError("VIENEU_TTS_CROSSFADE_SECONDS must be zero or positive.")
        if not is_allowed_model_id(self.model_id):
            raise ValueError(f"Unsupported VieNeu model id: {self.model_id}")
