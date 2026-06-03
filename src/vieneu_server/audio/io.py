from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def write_wav(path: Path, audio: np.ndarray, sample_rate: int = 24_000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sample_rate)
    return path
