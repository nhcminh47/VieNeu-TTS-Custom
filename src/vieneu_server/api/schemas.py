from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str


class RuntimeResponse(BaseModel):
    backend: str
    device: str
    gpu_name: str | None
    compute_capability: list[int] | None
    dtype: str
    lmdeploy_enabled: bool
    flash_attn_enabled: bool
    torch_compile_enabled: bool
    reason: str


class StorageResponse(BaseModel):
    output_dir: str
    file_count: int
    total_bytes: int
    max_files: int
    max_bytes: int


class ModelInfo(BaseModel):
    id: str
    default: bool = False


class VoiceInfo(BaseModel):
    id: str
    description: str
    text: str | None = None
    default: bool = False


class TtsJobCreateRequest(BaseModel):
    text: str = Field(min_length=1)
    model_id: str | None = None
    voice_reference_id: str | None = None
    voice_reference_path: str | None = None
    format: str = "wav"


class ChapterJobCreateRequest(BaseModel):
    text: str = Field(min_length=1)
    title: str | None = None
    model_id: str | None = None
    voice_reference_id: str | None = None
    voice_reference_path: str | None = None
    format: str = "wav"


class TtsJobCreateResponse(BaseModel):
    job_id: str
    status: str


class TtsJobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    audio_url: str | None
    error: str | None


class ChapterSegmentResponse(BaseModel):
    index: int
    paragraph_index: int
    paragraph_segment_index: int
    paragraph_segment_count: int
    text_length: int
    status: str
    progress: float
    audio_path: str | None = None
    error: str | None


class ChapterJobStatusResponse(BaseModel):
    job_id: str
    title: str
    status: str
    progress: float
    audio_url: str | None
    error: str | None
    paragraph_count: int
    segment_count: int
    completed_segments: int
    failed_segments: int
    manifest_path: str | None = None
    segments: list[ChapterSegmentResponse]
