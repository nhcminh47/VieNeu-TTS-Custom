from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .compatibility import MIN_CUDA_CAPABILITY, is_supported_cuda_capability


@dataclass(frozen=True)
class RuntimeDevice:
    device: str
    torch_device: Any
    cuda_available: bool
    gpu_name: str | None
    compute_capability: tuple[int, int] | None
    dtype: Any
    reason: str


def _import_torch() -> Any:
    try:
        import torch
    except ImportError:
        return None
    return torch


def _select_dtype(torch: Any, device: str, requested_dtype: str) -> Any:
    if torch is None:
        return "float32"
    if requested_dtype and requested_dtype != "auto":
        mapping = {
            "float16": torch.float16,
            "fp16": torch.float16,
            "float32": torch.float32,
            "fp32": torch.float32,
        }
        if requested_dtype not in mapping:
            raise ValueError("VIENEU_DTYPE must be auto, float16, fp16, float32, or fp32.")
        return mapping[requested_dtype]
    return torch.float16 if device == "cuda" else torch.float32


def get_runtime_device(device: str = "auto", dtype: str = "auto") -> RuntimeDevice:
    torch = _import_torch()
    requested_device = (device or "auto").lower()
    requested_dtype = (dtype or "auto").lower()

    if torch is None:
        return RuntimeDevice(
            device="cpu",
            torch_device="cpu",
            cuda_available=False,
            gpu_name=None,
            compute_capability=None,
            dtype="float32",
            reason="PyTorch is not installed; using CPU metadata only.",
        )

    cuda_available = bool(torch.cuda.is_available())
    gpu_name = None
    capability = None

    if cuda_available:
        try:
            raw_gpu_name = torch.cuda.get_device_name(0)
            gpu_name = raw_gpu_name if isinstance(raw_gpu_name, str) else None
            raw_capability = tuple(torch.cuda.get_device_capability(0))
            if len(raw_capability) >= 2:
                capability = (int(raw_capability[0]), int(raw_capability[1]))
            else:
                capability = None
        except Exception:
            capability = None

    selected_device = "cpu"
    reason = "CUDA unavailable; using CPU."

    if requested_device == "cpu":
        reason = "CPU explicitly requested."
    elif requested_device not in {"auto", "cuda"}:
        raise ValueError("VIENEU_DEVICE must be auto, cpu, or cuda.")
    elif cuda_available and is_supported_cuda_capability(capability):
        selected_device = "cuda"
        reason = f"CUDA GPU is supported with compute capability {capability[0]}.{capability[1]}."
    elif cuda_available:
        min_cc = f"{MIN_CUDA_CAPABILITY[0]}.{MIN_CUDA_CAPABILITY[1]}"
        cc_text = "unknown" if capability is None else f"{capability[0]}.{capability[1]}"
        reason = f"CUDA GPU compute capability {cc_text} is below required sm_{min_cc.replace('.', '')}; using CPU."
    elif requested_device == "cuda":
        reason = "CUDA explicitly requested but unavailable; using CPU."

    selected_dtype = _select_dtype(torch, selected_device, requested_dtype)
    return RuntimeDevice(
        device=selected_device,
        torch_device=torch.device(selected_device),
        cuda_available=cuda_available,
        gpu_name=gpu_name,
        compute_capability=capability,
        dtype=selected_dtype,
        reason=reason,
    )
