# VieNeu Server Setup for sm_61 GPUs

This fork targets backend-only local inference. The default server backend is PyTorch and LMDeploy is optional.

## GTX 1070 Ti / CUDA 11.8

Use a PyTorch wheel that still supports older Pascal GPUs such as GTX 1070 Ti.

```bash
conda create -n vieneu-sm61 python=3.10 -y
conda activate vieneu-sm61

pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118
pip install -e .
```

With `uv`:

```bash
uv venv --python 3.10
uv pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118
uv pip install -e .
```

If you use `uv run`, remember that it runs commands inside the project `.venv`. When `.venv` is recreated, base dependencies are installed from this project, but PyTorch is not installed automatically because the CUDA wheel must be selected explicitly for sm_61. Install PyTorch into the same `.venv` before checking CUDA:

```bash
uv sync
uv pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118
uv run python scripts/check_runtime.py
```

Do not use `uv run` alone as proof that CUDA is unavailable. If PyTorch is missing, the runtime check can only report CPU metadata.

## CPU Install

```bash
pip install -e .
```

GGUF support uses `llama-cpp-python`, which may require native build tools on Windows when a wheel is not available. Install it only when you need GGUF mode:

```bash
pip install -e ".[gguf]"
```

## Runtime Check

```bash
python scripts/check_runtime.py
```

Expected output includes CUDA availability, GPU name, compute capability, selected dtype, selected backend, and disabled LMDeploy status.

## Start Server

```bash
vieneu-server
```

The default URL is `http://127.0.0.1:8000`.
