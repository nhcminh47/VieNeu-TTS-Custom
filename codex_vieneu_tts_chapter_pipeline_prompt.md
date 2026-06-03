# Codex Prompt: Adjust VieNeu Custom TTS Pipeline for Long Novel Chapters

## Role

You are a senior full-stack/audio pipeline engineer.  
Your task is to refactor and improve the current custom TTS pipeline based on VieNeu/VieNue TTS so it can handle long novel chapters reliably.

The current system already works well for short text inputs around **120 characters**, but the audio quality becomes poor when generating a full novel chapter directly.  
Do **not** replace the model first. The primary goal is to fix the chapter synthesis pipeline.

---

## Current Problem

Short input:

```txt
~120 Vietnamese characters
```

works well.

Long input:

```txt
full novel chapter
```

produces bad audio quality, such as:

- unstable rhythm
- bad pauses
- swallowed words
- repeated audio
- robotic flow
- poor pronunciation around punctuation/dialogue
- inconsistent voice/prosody
- noisy or broken chunks
- very long generation time
- hard-to-debug output

The likely cause is that the system feeds too much text into the TTS model at once, instead of splitting the chapter into safe speech units.

---

## Goal

Implement a production-ready **chapter synthesis pipeline**:

```txt
Novel chapter
→ text normalization
→ smart semantic chunking
→ generate each chunk
→ validate generated audio
→ retry or split failed chunks
→ add natural pauses
→ concatenate audio
→ loudness normalize final output
→ return final audio URL and manifest
```

The system should continue supporting short preview TTS, but long chapter TTS must use an async job-based pipeline.

---

## Non-goals

Do not fine-tune the model in this task.

Do not replace VieNeu/VieNue TTS unless the existing generator cannot generate valid audio for short chunks.

Do not generate a full chapter in one model call.

Do not rely only on fixed character slicing.

Do not make the UI wait for a single blocking long request.

---

## Expected Architecture

Create or refactor the pipeline into these components:

```txt
TTS API
├── Preview TTS Endpoint
│   └── generate short text immediately
│
└── Chapter TTS Job Endpoint
    ├── create job
    ├── normalize text
    ├── split into smart chunks
    ├── generate chunk audio
    ├── validate audio
    ├── retry failed chunk
    ├── split failed chunk if needed
    ├── add silence/pause after chunk
    ├── concatenate chunks
    ├── normalize final audio
    ├── persist manifest
    └── return progress/final result
```

---

## Required Features

### 1. Separate Preview Mode and Chapter Mode

Implement two different flows.

#### Preview mode

Used for short input.

Requirements:

```txt
max input: configurable, default 180 characters
synchronous response is acceptable
no chapter chunking required
```

Example endpoint:

```http
POST /tts/preview
```

Example response:

```json
{
  "audioUrl": "/outputs/preview/abc123.wav",
  "durationMs": 4200
}
```

#### Chapter mode

Used for long novel text.

Requirements:

```txt
async job
progress tracking
chunk-level manifest
resume/retry support if possible
final concatenated audio
```

Example endpoint:

```http
POST /tts/jobs
```

Example response:

```json
{
  "jobId": "tts-job-20260603-abc123",
  "status": "queued"
}
```

Status endpoint:

```http
GET /tts/jobs/:jobId
```

Example response:

```json
{
  "jobId": "tts-job-20260603-abc123",
  "status": "processing",
  "progress": {
    "totalChunks": 42,
    "completedChunks": 17,
    "failedChunks": 0,
    "percent": 40
  }
}
```

Final response:

```json
{
  "jobId": "tts-job-20260603-abc123",
  "status": "completed",
  "audioUrl": "/outputs/tts-job-20260603-abc123/final.mp3",
  "manifestUrl": "/outputs/tts-job-20260603-abc123/manifest.json"
}
```

---

## 2. Text Normalization

Before chunking, normalize Vietnamese novel text.

Create a `TextNormalizer` module.

It should handle:

```txt
curly quotes → normal quotes
multiple spaces → single space
multiple blank lines → paragraph boundary
weird punctuation → normalized punctuation
repeated dots → ellipsis
em dash dialogue markers
unsupported symbols
common Vietnamese number/time/currency patterns
```

Examples:

```txt
“Xin chào...” → "Xin chào…"
...... → …
— Ngươi là ai? → Ngươi là ai?
3h sáng → ba giờ sáng
10.000đ → mười nghìn đồng
AI → ây ai or a i, configurable
```

Do not over-normalize names or novel-specific terms.

Add tests for text normalization.

---

## 3. Smart Semantic Chunking

Create a `SmartChunker` module.

The chunker must prioritize natural speech boundaries instead of cutting by fixed character count.

Preferred split priority:

```txt
1. paragraph breaks
2. sentence endings: . ! ? …
3. dialogue boundaries
4. comma / semicolon / colon
5. fallback character limit
```

Default config:

```env
TTS_CHUNK_TARGET_CHARS=120
TTS_CHUNK_MAX_CHARS=180
TTS_CHUNK_MIN_CHARS=40
```

Rules:

- Try to keep chunks between `min` and `max`.
- Prefer chunks around `target`.
- Never split in the middle of a word unless unavoidable.
- Preserve punctuation that affects pause.
- Keep short dialogue lines intact.
- Merge tiny chunks if they are too short and safe to merge.
- Split long paragraphs into sentence-level chunks.
- Split long sentences at commas or phrase boundaries.
- If a chunk still exceeds max length, use fallback splitting at word boundaries.

Example input:

```txt
Đêm ấy, mưa rơi rất lớn. Hắn đứng trước cửa, im lặng thật lâu.

— Ngươi thật sự muốn đi sao?

Nàng không trả lời. Chỉ khẽ gật đầu.
```

Expected chunks:

```json
[
  {
    "index": 1,
    "text": "Đêm ấy, mưa rơi rất lớn.",
    "pauseAfterMs": 350,
    "boundary": "sentence"
  },
  {
    "index": 2,
    "text": "Hắn đứng trước cửa, im lặng thật lâu.",
    "pauseAfterMs": 900,
    "boundary": "paragraph"
  },
  {
    "index": 3,
    "text": "Ngươi thật sự muốn đi sao?",
    "pauseAfterMs": 450,
    "boundary": "dialogue"
  },
  {
    "index": 4,
    "text": "Nàng không trả lời.",
    "pauseAfterMs": 350,
    "boundary": "sentence"
  },
  {
    "index": 5,
    "text": "Chỉ khẽ gật đầu.",
    "pauseAfterMs": 350,
    "boundary": "sentence"
  }
]
```

Add unit tests for chunking.

---

## 4. Pause Rules

After each chunk, add silence based on the ending punctuation or boundary.

Default config:

```env
TTS_PAUSE_COMMA_MS=150
TTS_PAUSE_SENTENCE_MS=350
TTS_PAUSE_QUESTION_MS=450
TTS_PAUSE_EXCLAMATION_MS=450
TTS_PAUSE_ELLIPSIS_MS=700
TTS_PAUSE_PARAGRAPH_MS=900
TTS_PAUSE_CHAPTER_MS=1500
```

Pause detection:

```txt
, / ; / :     → short pause
.             → sentence pause
?             → question pause
!             → exclamation pause
…             → long pause
paragraph end → paragraph pause
chapter end   → chapter pause
```

Add slight randomization if safe, for example ±10%, but keep it configurable.

```env
TTS_PAUSE_RANDOMIZE=false
TTS_PAUSE_RANDOMIZE_PERCENT=10
```

---

## 5. Chunk Audio Generation

Create a `ChunkGenerator` wrapper around the existing VieNeu/VieNue TTS call.

Requirements:

- Generate one chunk at a time.
- Use stable speaker/reference/voice settings across all chunks.
- Use the same seed if the model supports seed control.
- Keep generation params consistent across the full job.
- Save each chunk as a separate `.wav`.
- Store per-chunk metadata.

Output structure:

```txt
outputs/
  {jobId}/
    chunks/
      0001.wav
      0002.wav
      0003.wav
    silence/
      pause_0350.wav
      pause_0900.wav
    manifest.json
    concat_list.txt
    final.wav
    final.mp3
```

---

## 6. Audio Validation

Create an `AudioValidator` module.

Detect invalid or suspicious generated chunk audio.

Validation checks:

```txt
file exists
file size > minimum bytes
duration > minimum duration
duration < maximum expected duration
peak/rms volume is not silent
sample rate is expected
channels are expected
```

Use a rough expected duration heuristic.

Vietnamese narration is often around:

```txt
10–15 characters per second
```

For safety, use configurable bounds:

```env
TTS_EXPECTED_CHARS_PER_SECOND_MIN=7
TTS_EXPECTED_CHARS_PER_SECOND_MAX=20
TTS_MIN_CHUNK_DURATION_MS=500
TTS_MAX_CHUNK_DURATION_MULTIPLIER=2.5
TTS_MIN_RMS_DB=-45
```

Example:

```txt
120 characters → expected roughly 6–18 seconds
```

If generated audio is too short, too long, silent, broken, or missing, mark the chunk as failed.

---

## 7. Retry and Split-on-Failure

Implement retry logic per chunk.

Default config:

```env
TTS_MAX_RETRIES_PER_CHUNK=2
TTS_SPLIT_ON_RETRY=true
```

Behavior:

```txt
attempt 1: generate original chunk
attempt 2: retry original chunk
attempt 3: split chunk into smaller parts and generate subchunks
```

If a chunk fails after retries:

- Mark the chunk as failed in manifest.
- Do not silently ignore it.
- Prefer failing the job with clear error details unless partial output is explicitly enabled.

Optional config:

```env
TTS_ALLOW_PARTIAL_OUTPUT=false
```

---

## 8. Concatenation

Use ffmpeg or an equivalent reliable audio library.

Requirements:

- Ensure all chunk audio has the same sample rate.
- Ensure all chunk audio has the same channel count.
- Insert silence after each chunk.
- Concatenate using a generated concat file.
- Normalize final loudness.

Preferred output:

```txt
final.wav
final.mp3
```

Recommended defaults:

```env
TTS_OUTPUT_SAMPLE_RATE=24000
TTS_OUTPUT_CHANNELS=1
TTS_NORMALIZE_LOUDNESS=true
TTS_FINAL_FORMAT=mp3
```

Use ffmpeg commands similar to:

```bash
ffmpeg -y -i input.wav -ar 24000 -ac 1 normalized_chunk.wav
```

Concat:

```bash
ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy final.wav
```

Loudness normalize final:

```bash
ffmpeg -y -i final.wav -af loudnorm final_normalized.wav
```

Encode MP3:

```bash
ffmpeg -y -i final_normalized.wav -codec:a libmp3lame -qscale:a 2 final.mp3
```

Make sure the code handles paths safely.

---

## 9. Manifest

Create or update `manifest.json` during the job.

Example:

```json
{
  "jobId": "tts-job-20260603-abc123",
  "status": "completed",
  "source": {
    "title": "Chapter 1",
    "textLength": 5230,
    "createdAt": "2026-06-03T00:00:00.000Z"
  },
  "config": {
    "targetChars": 120,
    "maxChars": 180,
    "minChars": 40,
    "sampleRate": 24000,
    "channels": 1
  },
  "chunks": [
    {
      "index": 1,
      "text": "Đêm ấy, mưa rơi rất lớn.",
      "textLength": 27,
      "boundary": "sentence",
      "pauseAfterMs": 350,
      "audio": "chunks/0001.wav",
      "durationMs": 3100,
      "attempts": 1,
      "status": "done"
    }
  ],
  "output": {
    "wav": "final.wav",
    "mp3": "final.mp3",
    "durationMs": 523000
  },
  "errors": []
}
```

Update the manifest after each chunk so progress can recover if the process crashes.

---

## 10. Progress and WebSocket/SSE

If the existing project already has WebSocket, integrate job progress events.

Emit events such as:

```json
{
  "type": "tts.job.created",
  "jobId": "tts-job-20260603-abc123"
}
```

```json
{
  "type": "tts.chunk.completed",
  "jobId": "tts-job-20260603-abc123",
  "chunkIndex": 12,
  "totalChunks": 42,
  "percent": 29
}
```

```json
{
  "type": "tts.job.completed",
  "jobId": "tts-job-20260603-abc123",
  "audioUrl": "/outputs/tts-job-20260603-abc123/final.mp3"
}
```

```json
{
  "type": "tts.job.failed",
  "jobId": "tts-job-20260603-abc123",
  "error": "Chunk 18 failed after retries"
}
```

If WebSocket does not exist, implement polling first.

---

## 11. Environment Variables

Add these variables with safe defaults:

```env
# Chunking
TTS_PREVIEW_MAX_CHARS=180
TTS_CHUNK_TARGET_CHARS=120
TTS_CHUNK_MAX_CHARS=180
TTS_CHUNK_MIN_CHARS=40

# Pause
TTS_PAUSE_COMMA_MS=150
TTS_PAUSE_SENTENCE_MS=350
TTS_PAUSE_QUESTION_MS=450
TTS_PAUSE_EXCLAMATION_MS=450
TTS_PAUSE_ELLIPSIS_MS=700
TTS_PAUSE_PARAGRAPH_MS=900
TTS_PAUSE_CHAPTER_MS=1500
TTS_PAUSE_RANDOMIZE=false
TTS_PAUSE_RANDOMIZE_PERCENT=10

# Retry
TTS_MAX_RETRIES_PER_CHUNK=2
TTS_SPLIT_ON_RETRY=true
TTS_ALLOW_PARTIAL_OUTPUT=false

# Audio
TTS_OUTPUT_SAMPLE_RATE=24000
TTS_OUTPUT_CHANNELS=1
TTS_NORMALIZE_LOUDNESS=true
TTS_FINAL_FORMAT=mp3

# Validation
TTS_EXPECTED_CHARS_PER_SECOND_MIN=7
TTS_EXPECTED_CHARS_PER_SECOND_MAX=20
TTS_MIN_CHUNK_DURATION_MS=500
TTS_MAX_CHUNK_DURATION_MULTIPLIER=2.5
TTS_MIN_RMS_DB=-45

# Runtime
TTS_MAX_CONCURRENT_JOBS=1
TTS_MAX_CONCURRENT_CHUNKS=1
TTS_OUTPUT_DIR=/workspace/outputs
```

For current hardware, keep concurrency low:

```env
TTS_MAX_CONCURRENT_JOBS=1
TTS_MAX_CONCURRENT_CHUNKS=1
```

---

## 12. Testing Requirements

Add tests for:

### TextNormalizer

Cases:

```txt
curly quotes
ellipsis
dialogue dash
multiple spaces
currency
time
unsupported symbols
```

### SmartChunker

Cases:

```txt
short paragraph
long paragraph
dialogue
sentence ending
question/exclamation
ellipsis
very long sentence
tiny chunks merging
Vietnamese punctuation
```

### AudioValidator

Use small fixture WAV files or mocked metadata.

Cases:

```txt
valid audio
missing file
silent audio
too short
too long
wrong sample rate
```

### Job Pipeline

Use mocked TTS generator.

Cases:

```txt
chapter job completes
chunk failure retries
chunk split after repeated failure
manifest updates
final concat is called
job failed state is saved
```

---

## 13. Implementation Notes

Use the existing code style and project structure.

Prefer small modules with clear responsibilities:

```txt
tts/
  normalizer.py or normalizer.ts
  chunker.py or chunker.ts
  pause.py or pause.ts
  generator.py or generator.ts
  validator.py or validator.ts
  concat.py or concat.ts
  jobs.py or jobs.ts
  manifest.py or manifest.ts
```

Do not hardcode absolute paths.

Do not block the main API server process for very long work if the current architecture has a background worker.

If there is no background worker yet, implement a simple in-process queue first, but keep the interface easy to move to Redis/BullMQ/Celery later.

---

## 14. Acceptance Criteria

The task is done when:

- Short preview TTS still works.
- Long chapter TTS no longer calls the model with the full chapter.
- Chapter text is normalized before synthesis.
- Chapter text is split into semantic chunks.
- Each chunk is generated separately.
- Each chunk is validated.
- Failed chunks are retried.
- Persisted manifest shows chunk-level status.
- Final audio is concatenated with natural pauses.
- Final audio is loudness-normalized.
- API exposes job status and final audio URL.
- Chunk size and pause rules are configurable via env.
- Tests cover normalizer, chunker, validator, and job pipeline.
- Documentation explains how to tune chunk sizes for VieNeu/VieNue.

---

## 15. Suggested First Implementation Plan

1. Inspect current TTS endpoints and generator function.
2. Extract the existing short TTS call into a reusable `ChunkGenerator`.
3. Add `TextNormalizer`.
4. Add `SmartChunker`.
5. Add manifest writing.
6. Add chapter job endpoint.
7. Generate chunks sequentially.
8. Add audio validation.
9. Add retry and split-on-failure.
10. Add ffmpeg concat and final normalization.
11. Add status endpoint.
12. Add tests.
13. Update README or docs.

---

## 16. Important Quality Notes

The best output for novel chapters usually comes from **many small good chunks**, not one giant generation.

Start with:

```env
TTS_CHUNK_TARGET_CHARS=120
TTS_CHUNK_MAX_CHARS=180
TTS_CHUNK_MIN_CHARS=40
```

If output feels too fragmented, try:

```env
TTS_CHUNK_TARGET_CHARS=150
TTS_CHUNK_MAX_CHARS=220
```

If output starts degrading, reduce back to:

```env
TTS_CHUNK_TARGET_CHARS=100
TTS_CHUNK_MAX_CHARS=160
```

For the current machine, avoid parallel generation at first:

```env
TTS_MAX_CONCURRENT_JOBS=1
TTS_MAX_CONCURRENT_CHUNKS=1
```

Prioritize stability over speed.

---

## 17. Final Deliverable

Please implement the pipeline and return:

1. Summary of changed files.
2. Explanation of the new chapter TTS flow.
3. New environment variables.
4. How to test preview mode.
5. How to test chapter mode.
6. Known limitations.
7. Any recommended tuning values for VieNeu/VieNue on short chunks.

