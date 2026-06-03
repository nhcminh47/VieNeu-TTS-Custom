from __future__ import annotations

from dataclasses import dataclass

from .registry import is_allowed_model_id


@dataclass(frozen=True)
class ModelSelection:
    model_id: str


def select_model(model_id: str) -> ModelSelection:
    if not is_allowed_model_id(model_id):
        raise ValueError(f"Unsupported VieNeu model id: {model_id}")
    return ModelSelection(model_id=model_id)
