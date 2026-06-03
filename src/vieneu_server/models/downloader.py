from __future__ import annotations

from pathlib import Path

from huggingface_hub import snapshot_download

from .registry import is_allowed_model_id


def download_model(model_id: str, cache_dir: Path) -> Path:
    if not is_allowed_model_id(model_id):
        raise ValueError(f"Unsupported VieNeu model id: {model_id}")
    path = snapshot_download(repo_id=model_id, cache_dir=str(cache_dir), repo_type="model")
    return Path(path)
