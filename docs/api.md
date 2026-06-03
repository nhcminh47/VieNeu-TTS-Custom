# VieNeu Server API

## Health

`GET /health`

```json
{"ok": true, "service": "vieneu-server", "version": "0.1.0"}
```

## Runtime

`GET /runtime`

Returns backend, selected device, GPU name, compute capability, dtype, accelerator flags, and fallback reason.

## Storage

`GET /storage`

Returns generated-audio storage usage and configured retention limits.

```json
{
  "output_dir": "outputs",
  "file_count": 3,
  "total_bytes": 1245184,
  "max_files": 100,
  "max_bytes": 2147483648
}
```

## Models

`GET /models`

Returns allowed VieNeu model IDs. Arbitrary model IDs are rejected.

## Create TTS Job

`POST /tts/jobs`

```json
{
  "text": "Xin chao Viet Nam",
  "model_id": "pnnbao-ump/VieNeu-TTS-v2-Turbo",
  "voice_reference_id": null,
  "voice_reference_path": null,
  "format": "wav"
}
```

Response:

```json
{"job_id": "uuid", "status": "queued"}
```

## Create Chapter Job

`POST /tts/chapter-jobs`

Use this for novel chapters and audiobook-style long-form synthesis. The server normalizes and sanitizes text, splits it by paragraph, splits oversized paragraphs into sentence-group chunks, synthesizes each chunk sequentially, then merges `chapter.wav`.

```json
{
  "title": "Chapter 1",
  "text": "Long chapter text...",
  "model_id": "pnnbao-ump/VieNeu-TTS-v2",
  "voice_reference_id": "preset_voice",
  "voice_reference_path": null,
  "format": "wav"
}
```

Response:

```json
{"job_id": "uuid", "status": "queued"}
```

## Job Status

`GET /tts/jobs/{job_id}`

```json
{
  "job_id": "uuid",
  "status": "queued",
  "progress": 0.0,
  "audio_url": null,
  "error": null
}
```

`GET /tts/chapter-jobs/{job_id}`

Returns parent chapter progress plus segment progress.

```json
{
  "job_id": "uuid",
  "title": "Chapter 1",
  "status": "running",
  "progress": 0.42,
  "audio_url": null,
  "error": null,
  "paragraph_count": 42,
  "segment_count": 120,
  "completed_segments": 50,
  "failed_segments": 0,
  "manifest_path": "/workspace/outputs/uuid/manifest.json",
  "segments": [
    {
      "index": 1,
      "paragraph_index": 1,
      "paragraph_segment_index": 1,
      "paragraph_segment_count": 3,
      "text_length": 164,
      "status": "completed",
      "progress": 1.0,
      "audio_path": "/workspace/outputs/uuid/paragraph-001/001.wav",
      "error": null
    }
  ]
}
```

## Audio

`GET /tts/jobs/{job_id}/audio`

Returns a WAV file after the job is completed.

Returns `410 Gone` when the job is completed but its WAV file was removed by storage retention.

`GET /tts/chapter-jobs/{job_id}/audio`

Returns the merged chapter WAV after all segments complete.

`GET /tts/chapter-jobs/{job_id}/manifest`

Returns the JSON processing manifest after the chapter worker has started. Use it to inspect paragraph/chunk boundaries, per-chunk files, failures, and final merge metadata.

## WebSocket Events

`WS /ws/jobs/{job_id}`

Events use `job.status`, `job.completed`, or `job.failed`.

`WS /ws/chapter-jobs/{job_id}`

Events use `chapter.status`, `chapter.completed`, or `chapter.failed`.
