# Codex Prompt — Refactor VieNeu-TTS Backend for sm_61 GPU Compatibility

## Role

You are a senior Python ML infrastructure engineer and backend architect.

You are working on a fork of the VieNeu-TTS repository. The goal is to refactor the Python side into a clean API server that can run VieNeu Hugging Face models on older NVIDIA GPUs starting from `sm_61`, especially GTX 1070 Ti 8GB, without requiring LMDeploy.

The frontend UI is out of scope. A separate Next.js PWA with WebSocket support will be built later.

---

## Project Context

This repository is based on VieNeu-TTS.

Relevant facts:

- VieNeu-TTS is an on-device Vietnamese TTS system with instant voice cloning.
- The model source must remain Hugging Face VieNeu models only.
- The official repo currently optimizes for GPU through LMDeploy and also supports CPU/GGUF/ONNX paths.
- For this fork, LMDeploy must not be required for the main inference path.
- The target machine includes older NVIDIA GPUs such as GTX 1070 Ti with compute capability `sm_61`.
- The backend should expose a Python API server only.
- The frontend will be implemented separately using Next.js, WebSocket, and PWA.

References to consider while inspecting the repo:

- Hugging Face model family:
  - `pnnbao-ump/VieNeu-TTS`
  - `pnnbao-ump/VieNeu-TTS-0.3B`
  - `pnnbao-ump/VieNeu-TTS-v2`
  - `pnnbao-ump/VieNeu-TTS-v2-Turbo`
- Avoid changing model weights or training logic.
- Do not introduce non-VieNeu models.

---

## Main Objective

Refactor the repository into a maintainable Python API server that supports:

1. Loading VieNeu models from Hugging Face.
2. Running inference with PyTorch as the core backend.
3. Supporting NVIDIA GPUs from `sm_61` upward.
4. Running without LMDeploy.
5. Falling back to CPU when CUDA is unavailable or unsupported.
6. Providing HTTP and WebSocket APIs for TTS job creation, progress streaming, and audio result retrieval.
7. Keeping the code clean, modular, testable, and spec-driven.

---

## Hard Requirements

### Backend only

Do not build any UI.

Remove, ignore, or isolate frontend/demo code unless required by the inference pipeline.

The final result should focus on:

- Python API server
- Model loading
- Inference orchestration
- Job queue
- WebSocket event streaming
- Audio file output
- Health/debug endpoints
- Tests
- Documentation

---

### No LMDeploy requirement

LMDeploy must not be required for the main app to start or run.

Treat LMDeploy as optional only.

The default backend must be:

```txt
PyTorch inference
```

Not:

```txt
LMDeploy
```

Add config flags:

```env
VIENEU_BACKEND=torch
VIENEU_DISABLE_LMDEPLOY=true
VIENEU_DISABLE_FLASH_ATTN=true
VIENEU_DISABLE_TORCH_COMPILE=true
VIENEU_DEVICE=auto
VIENEU_DTYPE=auto
```

If LMDeploy-specific imports exist, make them lazy and optional.

The server must not crash when LMDeploy is not installed.

---

### GPU compatibility target

The target GPU compatibility starts at:

```txt
NVIDIA compute capability sm_61
```

Example target GPU:

```txt
GTX 1070 Ti 8GB
```

Implement explicit CUDA capability detection.

Expected behavior:

- If CUDA is available and compute capability is >= `sm_61`, allow CUDA inference.
- If CUDA is unavailable, fallback to CPU.
- If CUDA exists but compute capability is lower than `sm_61`, fallback to CPU.
- Never require BF16.
- Prefer FP16 on CUDA.
- Prefer FP32 on CPU.
- Avoid hard dependencies on FlashAttention, Triton, XFormers, LMDeploy, or `torch.compile`.

Create a module like:

```txt
src/vieneu_server/runtime/device.py
```

With functions similar to:

```python
def get_runtime_device() -> RuntimeDevice:
    ...
```

The returned object should include:

```python
device: str
torch_device: torch.device
cuda_available: bool
gpu_name: str | None
compute_capability: tuple[int, int] | None
dtype: torch.dtype
reason: str
```

---

### Hugging Face model source only

Models must be downloaded or loaded only from VieNeu Hugging Face repositories.

Supported model IDs should be configurable:

```env
VIENEU_MODEL_ID=pnnbao-ump/VieNeu-TTS-v2-Turbo
VIENEU_MODEL_CACHE_DIR=./models
```

Allowed examples:

```txt
pnnbao-ump/VieNeu-TTS
pnnbao-ump/VieNeu-TTS-0.3B
pnnbao-ump/VieNeu-TTS-v2
pnnbao-ump/VieNeu-TTS-v2-Turbo
```

Do not add unrelated TTS models.

Do not add cloud inference APIs.

Do not add OpenAI, ElevenLabs, Google TTS, Azure TTS, or other external TTS providers.

---

## Spec-Driven Development Process

Before editing implementation code, create or update the following spec files:

```txt
docs/specs/00-product-scope.md
docs/specs/01-architecture.md
docs/specs/02-api-contract.md
docs/specs/03-runtime-compatibility.md
docs/specs/04-inference-pipeline.md
docs/specs/05-job-lifecycle.md
docs/specs/06-testing-strategy.md
docs/specs/07-migration-plan.md
```

Each spec must contain:

- Goals
- Non-goals
- Constraints
- Design decisions
- Acceptance criteria
- Risks
- Open questions

Do not implement large changes until the relevant spec is written.

After writing specs, implement in small commits or logical phases.

---

## Desired Architecture

Refactor toward this structure if it fits the current repo:

```txt
src/
  vieneu_server/
    __init__.py

    main.py
    config.py

    api/
      __init__.py
      http.py
      websocket.py
      schemas.py

    runtime/
      __init__.py
      device.py
      dtype.py
      compatibility.py

    models/
      __init__.py
      registry.py
      downloader.py
      loader.py

    inference/
      __init__.py
      engine.py
      pipeline.py
      preprocessing.py
      postprocessing.py

    jobs/
      __init__.py
      manager.py
      queue.py
      events.py
      storage.py

    audio/
      __init__.py
      io.py
      validate.py

    observability/
      __init__.py
      logging.py
      metrics.py

tests/
  unit/
  integration/
scripts/
  check_runtime.py
  smoke_test_tts.py
docs/
  specs/
```

Keep naming consistent with the existing repo if there is already a better convention.

---

## API Requirements

Use FastAPI unless the repo already uses a different Python web framework that is clearly better to preserve.

Implement these endpoints:

### Health

```http
GET /health
```

Returns:

```json
{
  "ok": true,
  "service": "vieneu-server",
  "version": "0.1.0"
}
```

---

### Runtime info

```http
GET /runtime
```

Returns detected runtime:

```json
{
  "backend": "torch",
  "device": "cuda",
  "gpu_name": "NVIDIA GeForce GTX 1070 Ti",
  "compute_capability": [6, 1],
  "dtype": "float16",
  "lmdeploy_enabled": false,
  "flash_attn_enabled": false,
  "torch_compile_enabled": false
}
```

---

### List models

```http
GET /models
```

Returns configured and supported VieNeu model IDs.

---

### Create TTS job

```http
POST /tts/jobs
```

Request:

```json
{
  "text": "Xin chào, đây là bản thử nghiệm giọng nói tiếng Việt.",
  "model_id": "pnnbao-ump/VieNeu-TTS-v2-Turbo",
  "voice_reference_id": null,
  "voice_reference_path": null,
  "format": "wav"
}
```

Response:

```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

---

### Get job status

```http
GET /tts/jobs/{job_id}
```

Response:

```json
{
  "job_id": "uuid",
  "status": "queued | running | completed | failed",
  "progress": 0.0,
  "audio_url": null,
  "error": null
}
```

---

### Download generated audio

```http
GET /tts/jobs/{job_id}/audio
```

Returns generated audio file.

---

### WebSocket job events

```http
WS /ws/jobs/{job_id}
```

Events:

```json
{
  "type": "job.status",
  "job_id": "uuid",
  "status": "running",
  "progress": 0.25,
  "message": "Generating acoustic tokens"
}
```

```json
{
  "type": "job.completed",
  "job_id": "uuid",
  "status": "completed",
  "progress": 1.0,
  "audio_url": "/tts/jobs/{job_id}/audio"
}
```

```json
{
  "type": "job.failed",
  "job_id": "uuid",
  "status": "failed",
  "error": "..."
}
```

---

## Job Lifecycle

Implement a simple local job manager first.

MVP behavior:

```txt
queued -> running -> completed
queued -> running -> failed
```

Do not add Redis/Celery unless necessary.

Use in-memory job state for MVP, but design the interface so persistent storage can be added later.

Generated audio files should be stored locally:

```txt
outputs/{job_id}.wav
```

Add config:

```env
VIENEU_OUTPUT_DIR=./outputs
VIENEU_MAX_TEXT_LENGTH=3000
VIENEU_MAX_CONCURRENT_JOBS=1
```

For GTX 1070 Ti, default concurrent GPU jobs should be 1.

---

## Inference Requirements

Create a clean inference abstraction:

```python
class TtsEngine:
    def load(self) -> None:
        ...

    def synthesize(self, request: TtsRequest) -> TtsResult:
        ...

    def unload(self) -> None:
        ...
```

The engine must:

- Load VieNeu model from Hugging Face.
- Select device using runtime detection.
- Use FP16 on CUDA where safe.
- Use FP32 on CPU.
- Avoid BF16.
- Avoid FlashAttention by default.
- Avoid torch.compile by default.
- Avoid LMDeploy by default.
- Emit progress events if possible.
- Return a local audio file path.

If the current VieNeu code has multiple inference paths, preserve them behind separate backend classes, for example:

```txt
TorchVieNeuEngine
GgufOnnxVieNeuEngine
LmdeployVieNeuEngine optional only
```

Default must be:

```txt
TorchVieNeuEngine
```

If direct PyTorch inference is not currently possible with the repo structure, document exactly why in `docs/specs/04-inference-pipeline.md` and create the cleanest adapter around the existing supported local inference path while preserving the no-LMDeploy requirement.

---

## Dependency Requirements

Do not let the package manager accidentally install a torch version that breaks `sm_61`.

Do not put generic `torch` in the main dependency list without documenting how CUDA wheels should be installed.

Create install docs for GTX 1070 Ti:

```bash
conda create -n vieneu-sm61 python=3.10 -y
conda activate vieneu-sm61

pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118

pip install -e .
```

Also provide CPU install instructions.

If using `uv`, keep torch installation explicit and separated:

```bash
uv pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118
uv pip install -e .
```

Add a runtime check script:

```bash
python scripts/check_runtime.py
```

Expected output includes:

```txt
CUDA available
GPU name
Compute capability
Selected dtype
Selected backend
LMDeploy disabled
```

---

## Testing Requirements

Add tests for:

### Runtime detection

- CPU only
- CUDA available with `sm_61`
- CUDA available with lower than `sm_61`
- CUDA available with newer GPU
- dtype selection

Use mocks for `torch.cuda`.

### Config

- Default backend is torch
- LMDeploy disabled by default
- FlashAttention disabled by default
- torch.compile disabled by default
- model ID validation only allows VieNeu Hugging Face model IDs

### API

- `/health`
- `/runtime`
- `/models`
- create TTS job
- get job status
- WebSocket event schema

### Inference smoke test

Add one smoke test script that can run manually:

```bash
python scripts/smoke_test_tts.py --text "Xin chào Việt Nam"
```

The smoke test should generate an audio file under:

```txt
outputs/
```

Do not require this test to run in CI unless model download is explicitly enabled.

---

## Documentation Requirements

Update or create:

```txt
README.md
docs/setup-sm61.md
docs/api.md
docs/troubleshooting.md
docs/specs/*.md
```

The README must clearly state:

- This fork is backend-only.
- UI is out of scope.
- Default backend is PyTorch/local inference.
- LMDeploy is optional, not required.
- Target compatibility starts from NVIDIA `sm_61`.
- GTX 1070 Ti is a target test device.
- Models must come from VieNeu Hugging Face repositories only.

Troubleshooting should include:

- CUDA not detected
- GPU too old
- out of memory
- torch CUDA wheel mismatch
- LMDeploy import errors should not crash server
- slow generation on CPU
- WebSocket connection issues

---

## Implementation Phases

Follow these phases strictly.

### Phase 1 — Repository analysis

Inspect the current repo.

Produce a short report in:

```txt
docs/specs/07-migration-plan.md
```

Include:

- Current entrypoints
- Current inference paths
- Where LMDeploy is used
- Where model loading happens
- Where Hugging Face model IDs are defined
- What can be reused
- What should be isolated
- What should be removed from backend MVP

Do not refactor yet.

---

### Phase 2 — Specs

Create all spec files under:

```txt
docs/specs/
```

Do not skip acceptance criteria.

---

### Phase 3 — Runtime compatibility layer

Implement:

```txt
runtime/device.py
runtime/dtype.py
runtime/compatibility.py
scripts/check_runtime.py
```

Add tests.

---

### Phase 4 — Config and model registry

Implement:

```txt
config.py
models/registry.py
models/downloader.py
models/loader.py
```

Add model ID validation.

Only allow VieNeu Hugging Face model IDs.

---

### Phase 5 — API server skeleton

Implement FastAPI app:

```txt
main.py
api/http.py
api/websocket.py
api/schemas.py
```

Endpoints:

```txt
GET /health
GET /runtime
GET /models
POST /tts/jobs
GET /tts/jobs/{job_id}
GET /tts/jobs/{job_id}/audio
WS /ws/jobs/{job_id}
```

Use stub inference initially if necessary.

---

### Phase 6 — Job manager

Implement:

```txt
jobs/manager.py
jobs/queue.py
jobs/events.py
jobs/storage.py
```

Support local queue and progress events.

Default concurrency:

```txt
1
```

---

### Phase 7 — Inference adapter

Refactor existing VieNeu inference into:

```txt
inference/engine.py
inference/pipeline.py
```

Default backend:

```txt
torch
```

LMDeploy backend must remain optional and lazy-loaded only.

If direct torch inference is not feasible immediately, document blockers and implement the closest local non-LMDeploy path available in the repo.

---

### Phase 8 — Smoke test and docs

Add:

```txt
scripts/smoke_test_tts.py
docs/setup-sm61.md
docs/api.md
docs/troubleshooting.md
```

---

## Acceptance Criteria

The task is done when:

1. The server starts without LMDeploy installed.
2. `GET /health` works.
3. `GET /runtime` reports CUDA/device/dtype/backend.
4. The app does not crash on GTX 1070 Ti / `sm_61`.
5. The app falls back to CPU if CUDA is unavailable or unsupported.
6. Model IDs are restricted to VieNeu Hugging Face repositories.
7. A TTS job can be created through HTTP.
8. Job progress can be streamed through WebSocket.
9. Generated audio is saved under `outputs/`.
10. The repo includes clear setup instructions for GTX 1070 Ti.
11. Tests cover runtime detection, config, API routes, and job lifecycle.
12. Specs are written before major implementation.
13. LMDeploy is optional only and never required for the default path.

---

## Non-Goals

Do not implement:

- Next.js UI
- PWA
- Authentication
- Payment
- Cloud deployment
- Distributed queue
- Redis/Celery unless absolutely necessary
- Training or fine-tuning
- New non-VieNeu TTS models
- OpenAI/ElevenLabs/Azure/Google TTS integrations
- LMDeploy-first architecture

---

## Coding Standards

Use:

- Python 3.10+
- Type hints
- Pydantic schemas
- FastAPI
- Clear module boundaries
- Small functions
- Lazy optional imports
- Structured logging
- Meaningful errors
- Unit tests where possible

Avoid:

- Global hidden state except controlled app singleton
- Hardcoded local paths
- Hardcoded CUDA requirements
- Unconditional import of optional GPU accelerators
- Large untested rewrites
- Silent fallback without logging
- Mixing UI/demo code with API server code

---

## Output Format

Before making changes, provide:

```md
## Repo Analysis Summary

## Proposed Specs

## Implementation Plan

## Risks / Open Questions
```

Then proceed phase by phase.

After each phase, summarize:

```md
## Completed

## Files Changed

## Tests Added

## How To Run

## Known Limitations
```

Do not claim success unless commands/tests actually pass.

Run relevant tests after each phase.

If a command fails, report the exact failure and propose the smallest fix.
