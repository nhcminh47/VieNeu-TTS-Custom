from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vieneu_server.config import ServerConfig
from vieneu_server.runtime.device import get_runtime_device
from vieneu_server.runtime.dtype import dtype_name


def main() -> None:
    config = ServerConfig.from_env()
    runtime = get_runtime_device(config.device, config.dtype)

    print(f"CUDA available: {runtime.cuda_available}")
    print(f"GPU name: {runtime.gpu_name or 'none'}")
    print(f"Compute capability: {runtime.compute_capability or 'none'}")
    print(f"Selected device: {runtime.device}")
    print(f"Selected dtype: {dtype_name(runtime.dtype)}")
    print(f"Selected backend: {config.backend}")
    print(f"LMDeploy disabled: {config.disable_lmdeploy}")
    print(f"FlashAttention disabled: {config.disable_flash_attn}")
    print(f"torch.compile disabled: {config.disable_torch_compile}")
    print(f"Reason: {runtime.reason}")
    if runtime.reason.startswith("PyTorch is not installed"):
        print("")
        print("Install PyTorch explicitly for GTX 1070 Ti / sm_61:")
        print("uv pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118")


if __name__ == "__main__":
    main()
