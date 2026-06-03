# Testing Strategy

## Goals
- Cover runtime selection, config validation, API routes, and job lifecycle.
- Avoid model downloads in automated tests.

## Non-goals
- No CI requirement for real synthesis.
- No GPU requirement for unit tests.

## Constraints
- Use mocks for `torch.cuda`.
- Use a fake TTS engine for API and job tests.

## Design Decisions
- Unit tests cover runtime, config, model registry, and job manager behavior.
- API tests use FastAPI `TestClient`.
- Manual scripts cover runtime inspection and real TTS smoke testing.

## Acceptance Criteria
- `pytest` passes without downloading VieNeu models.
- `scripts/check_runtime.py` prints selected runtime details.
- `scripts/smoke_test_tts.py` writes a WAV file when dependencies and model access are available.

## Risks
- FastAPI test dependency versions may need `httpx` compatible with installed FastAPI.

## Open Questions
- Whether to add optional slow tests guarded by an environment variable.
