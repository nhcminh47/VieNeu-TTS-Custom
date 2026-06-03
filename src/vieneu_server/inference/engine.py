from __future__ import annotations

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from ..audio.io import write_wav
from ..audio.validate import validate_audio_format
from ..config import ServerConfig
from ..models.registry import is_allowed_model_id
from ..runtime.device import RuntimeDevice, get_runtime_device

ProgressCallback = Callable[[float, str], None]
logger = logging.getLogger("vieneu_server.inference")


@dataclass(frozen=True)
class TtsRequest:
    text: str
    model_id: str
    output_path: Path
    voice_reference_id: str | None = None
    voice_reference_path: Path | None = None
    format: str = "wav"


@dataclass(frozen=True)
class TtsResult:
    audio_path: Path
    sample_rate: int = 24_000


class TtsEngine(ABC):
    @abstractmethod
    def load(self, model_id: str | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def synthesize(self, request: TtsRequest, progress: ProgressCallback | None = None) -> TtsResult:
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        raise NotImplementedError


class VieNeuTorchEngine(TtsEngine):
    def __init__(self, config: ServerConfig, runtime: RuntimeDevice | None = None):
        self.config = config
        self.runtime = runtime or get_runtime_device(config.device, config.dtype)
        self._tts = None
        self._loaded_model_id: str | None = None

    def load(self, model_id: str | None = None) -> None:
        selected_model = model_id or self.config.model_id
        if not is_allowed_model_id(selected_model):
            raise ValueError(f"Unsupported VieNeu model id: {selected_model}")
        if self._tts is not None and self._loaded_model_id == selected_model:
            return

        self.unload()
        os.environ.setdefault("VIENEU_DISABLE_LMDEPLOY", "true")
        os.environ.setdefault("VIENEU_DISABLE_FLASH_ATTN", "true")
        os.environ.setdefault("VIENEU_DISABLE_TORCH_COMPILE", "true")

        from vieneu import Vieneu

        if selected_model == "pnnbao-ump/VieNeu-TTS-v2-Turbo":
            self._tts = Vieneu(
                mode="turbo_gpu",
                backbone_repo=selected_model,
                device=self.runtime.device,
                backend="standard",
            )
        else:
            self._tts = Vieneu(
                mode="standard",
                backbone_repo=selected_model,
                backbone_device=self.runtime.device,
                codec_repo="neuphonic/neucodec-onnx-decoder-int8",
                codec_device="cpu",
                gguf_filename=None,
            )
        self._loaded_model_id = selected_model

    def synthesize(self, request: TtsRequest, progress: ProgressCallback | None = None) -> TtsResult:
        validate_audio_format(request.format)
        self.load(request.model_id)
        if self._tts is None:
            raise RuntimeError("TTS engine failed to load.")

        if progress:
            progress(0.2, "Model loaded")

        voice = None
        kwargs = {}
        if request.voice_reference_id:
            voice = self._tts.get_preset_voice(request.voice_reference_id)
        if request.voice_reference_path:
            kwargs["ref_audio"] = str(request.voice_reference_path)
        kwargs.update(
            {
                "max_chars": self.config.tts_max_chars,
                "temperature": self.config.tts_temperature,
                "top_k": self.config.tts_top_k,
                "silence_p": self.config.tts_silence_seconds,
                "crossfade_p": self.config.tts_crossfade_seconds,
                "apply_watermark": self.config.tts_apply_watermark,
            }
        )

        if progress:
            progress(0.5, "Generating audio")

        def chunk_progress(done: int, total: int, message: str) -> None:
            total = max(total, 1)
            value = 0.5 + (0.45 * min(done, total) / total)
            logger.info("job_output=%s chunk=%d/%d message=%s", request.output_path.name, done, total, message)
            if progress:
                progress(value, message)

        kwargs["progress_callback"] = chunk_progress
        audio = self._tts.infer(text=request.text, voice=voice, **kwargs)
        if not isinstance(audio, np.ndarray):
            audio = np.asarray(audio, dtype=np.float32)

        write_wav(request.output_path, audio, getattr(self._tts, "sample_rate", 24_000))
        if progress:
            progress(1.0, "Audio written")
        return TtsResult(audio_path=request.output_path, sample_rate=getattr(self._tts, "sample_rate", 24_000))

    def unload(self) -> None:
        if self._tts is not None:
            close = getattr(self._tts, "close", None)
            if callable(close):
                close()
        self._tts = None
        self._loaded_model_id = None
