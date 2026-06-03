from __future__ import annotations

from .engine import TtsEngine, TtsRequest, TtsResult


def synthesize(engine: TtsEngine, request: TtsRequest) -> TtsResult:
    return engine.synthesize(request)
