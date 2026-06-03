# API Contract

## Goals
- Provide a stable backend contract for a future Next.js PWA.
- Support job creation, status polling, audio retrieval, and progress streaming.

## Non-goals
- No UI routes.
- No OpenAI-compatible API surface.

## Constraints
- JSON responses must be simple and typed.
- `wav` is the only accepted output format for MVP.

## Design Decisions
- `GET /health` returns service status and version.
- `GET /runtime` returns backend, selected device, CUDA details, dtype, and optional accelerator flags.
- `GET /models` returns allowed VieNeu model IDs and the configured default.
- `POST /tts/jobs` creates an async local job.
- `GET /tts/jobs/{job_id}` returns current job state.
- `GET /tts/jobs/{job_id}/audio` returns the generated file after completion.
- `WS /ws/jobs/{job_id}` streams job events as JSON.

## Acceptance Criteria
- Unknown jobs return 404 on HTTP status/audio endpoints.
- WebSocket subscribers receive current state or failure information.
- Requests over max text length are rejected.

## Risks
- WebSocket clients may connect after a job completes; the server must still send a terminal event.

## Open Questions
- Whether streaming audio chunks should be added after the job/event MVP.
