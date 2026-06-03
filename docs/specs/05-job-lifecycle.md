# Job Lifecycle

## Goals
- Provide a simple local queue for TTS jobs.
- Emit progress events over WebSocket.
- Save completed audio files predictably.

## Non-goals
- No Redis, Celery, distributed workers, retries, or persistent metadata.

## Constraints
- Default max concurrency is 1.
- Output path is `outputs/{job_id}.wav` unless configured otherwise.
- Completed audio files are immutable per job until storage retention removes older files.
- Default retention keeps up to 100 WAV files or 2 GiB, configured by `VIENEU_MAX_OUTPUT_FILES` and `VIENEU_MAX_OUTPUT_BYTES`.

## Design Decisions
- Jobs move through `queued`, `running`, `completed`, or `failed`.
- Job state is in memory.
- Event subscribers use per-job asyncio queues.
- Lifecycle progress is used for MVP; chunk-level progress can be added inside engines later.

## Acceptance Criteria
- Job creation returns a UUID and queued status.
- Completed jobs expose an audio URL.
- Failed jobs expose an error string.
- WebSocket clients receive terminal events.

## Risks
- In-memory state is lost on process restart.
- Old completed jobs can remain in history after their audio file is removed by retention; these jobs must expose `audio_url: null`.

## Open Questions
- Whether later deployments should persist job metadata across restarts.
