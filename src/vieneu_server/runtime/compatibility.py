from __future__ import annotations

MIN_CUDA_CAPABILITY = (6, 1)


def is_supported_cuda_capability(capability: tuple[int, int] | None) -> bool:
    if capability is None:
        return False
    return capability >= MIN_CUDA_CAPABILITY
