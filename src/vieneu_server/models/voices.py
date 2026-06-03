from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download

from .registry import is_allowed_model_id


def _load_voices_file(repo_id: str) -> Path | None:
    try:
        return Path(hf_hub_download(repo_id=repo_id, filename="voices.json", repo_type="model"))
    except Exception:
        try:
            return Path(hf_hub_download(repo_id=repo_id, filename="voices.json", repo_type="model", local_files_only=True))
        except Exception:
            return None


@lru_cache(maxsize=16)
def list_model_voices(repo_id: str) -> list[dict[str, Any]]:
    if not is_allowed_model_id(repo_id):
        raise ValueError(f"Unsupported VieNeu model id: {repo_id}")

    voices_file = _load_voices_file(repo_id)
    if voices_file is None:
        return []

    with voices_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    presets = data.get("presets", {})
    default_voice = data.get("default_voice")
    voices: list[dict[str, Any]] = []
    for voice_id, voice_data in presets.items():
        if isinstance(voice_data, dict):
            voices.append(
                {
                    "id": voice_id,
                    "description": voice_data.get("description") or voice_id,
                    "text": voice_data.get("text"),
                    "default": voice_id == default_voice,
                }
            )
        else:
            voices.append({"id": voice_id, "description": str(voice_data), "text": None, "default": voice_id == default_voice})
    return voices
