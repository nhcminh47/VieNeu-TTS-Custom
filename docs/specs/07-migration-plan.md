# Migration Plan

## Goals
- Move toward a backend-only API server without breaking the existing SDK.
- Isolate LMDeploy and UI/demo paths from the new server.

## Non-goals
- No deletion of legacy apps in the MVP.
- No rewrite of training or fine-tuning scripts.

## Constraints
- Specs must exist before major implementation.
- Migration should be incremental and testable.

## Design Decisions
- Current entrypoints:
  - `apps/gradio_main.py` for Gradio UI.
  - `apps/web_stream.py` for a local demo web/streaming app.
  - `src/vieneu/serve.py` for LMDeploy API server startup.
  - `vieneu-web` and `vieneu-stream` console scripts.
- Current inference paths:
  - `src/vieneu/standard.py` for PyTorch/GGUF.
  - `src/vieneu/turbo.py` for Turbo GGUF/PyTorch and optional LMDeploy.
  - `src/vieneu/fast.py` for LMDeploy.
  - `src/vieneu/remote.py` for remote LMDeploy-compatible APIs.
- Model loading happens in `standard.py`, `turbo.py`, `base.py`, and demo apps.
- Hugging Face model IDs are configured in `config.yaml`, README examples, and engine defaults.

## Acceptance Criteria
- Backend MVP uses `vieneu_server`, not UI modules.
- LMDeploy is optional and never imported by server startup.
- Legacy entrypoints continue to exist for compatibility.

## Risks
- Some existing tests mock LMDeploy as first-class behavior; new server tests should avoid that dependency.

## Open Questions
- Whether legacy LMDeploy server docs should be moved to an archive section later.
