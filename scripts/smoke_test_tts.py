from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vieneu_server.config import ServerConfig
from vieneu_server.inference.engine import TtsRequest, VieNeuTorchEngine
from vieneu_server.runtime.device import get_runtime_device


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a VieNeu server TTS smoke test.")
    parser.add_argument("--text", default="Xin chao Viet Nam")
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    config = ServerConfig.from_env()
    runtime = get_runtime_device(config.device, config.dtype)
    model_id = args.model_id or config.model_id
    output_path = Path(args.output) if args.output else config.output_dir / "smoke_test.wav"

    engine = VieNeuTorchEngine(config, runtime)
    result = engine.synthesize(TtsRequest(text=args.text, model_id=model_id, output_path=output_path))
    print(f"Wrote audio: {result.audio_path}")


if __name__ == "__main__":
    main()
