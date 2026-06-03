from __future__ import annotations

from pathlib import Path

import numpy as np

from vieneu_server.config import ServerConfig
from vieneu_server.inference.engine import TtsRequest, VieNeuTorchEngine
from vieneu_server.runtime.device import get_runtime_device


class FakeLoadedTts:
    sample_rate = 24_000

    def __init__(self):
        self.kwargs = {}

    def infer(self, text, voice=None, **kwargs):
        self.kwargs = kwargs
        return np.zeros(240, dtype=np.float32)


def test_torch_engine_forwards_long_form_quality_settings(tmp_path: Path):
    config = ServerConfig(
        output_dir=tmp_path,
        tts_max_chars=160,
        tts_temperature=0.35,
        tts_top_k=40,
        tts_silence_seconds=0.2,
        tts_crossfade_seconds=0.015,
        tts_apply_watermark=False,
    )
    engine = VieNeuTorchEngine(config, get_runtime_device(device="cpu"))
    fake_tts = FakeLoadedTts()
    engine._tts = fake_tts
    engine._loaded_model_id = config.model_id

    result = engine.synthesize(TtsRequest(text="Xin chao", model_id=config.model_id, output_path=tmp_path / "out.wav"))

    assert result.audio_path.exists()
    assert fake_tts.kwargs["max_chars"] == 160
    assert fake_tts.kwargs["temperature"] == 0.35
    assert fake_tts.kwargs["top_k"] == 40
    assert fake_tts.kwargs["silence_p"] == 0.2
    assert fake_tts.kwargs["crossfade_p"] == 0.015
    assert fake_tts.kwargs["apply_watermark"] is False
