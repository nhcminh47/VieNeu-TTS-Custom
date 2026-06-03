from __future__ import annotations

ALLOWED_MODEL_IDS = (
    "pnnbao-ump/VieNeu-TTS",
    "pnnbao-ump/VieNeu-TTS-0.3B",
    "pnnbao-ump/VieNeu-TTS-v2",
    "pnnbao-ump/VieNeu-TTS-v2-Turbo",
)

DEFAULT_MODEL_ID = "pnnbao-ump/VieNeu-TTS-v2-Turbo"


def is_allowed_model_id(model_id: str | None) -> bool:
    return bool(model_id and model_id in ALLOWED_MODEL_IDS)


def list_models(default_model_id: str = DEFAULT_MODEL_ID) -> list[dict[str, object]]:
    return [
        {"id": model_id, "default": model_id == default_model_id}
        for model_id in ALLOWED_MODEL_IDS
    ]
