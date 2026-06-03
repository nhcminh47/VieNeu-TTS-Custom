from __future__ import annotations

import sys
from types import SimpleNamespace

from vieneu_server.runtime.device import get_runtime_device
from vieneu_server.runtime.dtype import dtype_name


def fake_torch(cuda_available=False, name="GPU", capability=(6, 1)):
    cuda = SimpleNamespace(
        is_available=lambda: cuda_available,
        get_device_name=lambda index: name,
        get_device_capability=lambda index: capability,
    )
    return SimpleNamespace(
        cuda=cuda,
        float16="torch.float16",
        float32="torch.float32",
        device=lambda value: value,
    )


def test_runtime_cpu_only(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", fake_torch(cuda_available=False))
    runtime = get_runtime_device()
    assert runtime.device == "cpu"
    assert dtype_name(runtime.dtype) == "float32"


def test_runtime_cuda_sm61(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", fake_torch(True, "NVIDIA GeForce GTX 1070 Ti", (6, 1)))
    runtime = get_runtime_device()
    assert runtime.device == "cuda"
    assert runtime.compute_capability == (6, 1)
    assert dtype_name(runtime.dtype) == "float16"


def test_runtime_cuda_below_sm61_falls_back(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", fake_torch(True, "Old GPU", (5, 2)))
    runtime = get_runtime_device()
    assert runtime.device == "cpu"
    assert "below required" in runtime.reason


def test_runtime_newer_cuda(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", fake_torch(True, "NVIDIA RTX", (8, 6)))
    runtime = get_runtime_device()
    assert runtime.device == "cuda"


def test_runtime_explicit_dtype(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", fake_torch(cuda_available=False))
    runtime = get_runtime_device(dtype="fp32")
    assert dtype_name(runtime.dtype) == "float32"
