# Architecture

## Goals
- Separate backend server concerns from the existing SDK and demo apps.
- Keep runtime detection, model validation, inference, jobs, API schemas, and storage modular.

## Non-goals
- No broad SDK refactor.
- No removal of existing Gradio or legacy server entrypoints in the MVP.

## Constraints
- Python 3.10+ with type hints.
- FastAPI for HTTP and WebSocket APIs.
- Local in-memory job state for MVP.

## Design Decisions
- New package layout:
  - `vieneu_server.config`
  - `vieneu_server.runtime`
  - `vieneu_server.models`
  - `vieneu_server.inference`
  - `vieneu_server.jobs`
  - `vieneu_server.api`
  - `vieneu_server.main`
- The API owns request validation and job orchestration.
- The inference adapter owns lazy model loading and output writing.

## Acceptance Criteria
- Importing `vieneu_server.main` does not import LMDeploy.
- Existing `vieneu` package remains import-compatible.
- Tests can construct the API with a fake engine.

## Risks
- Shared global model instances can make tests flaky if not isolated.

## Open Questions
- Whether later versions should persist job metadata in SQLite.
