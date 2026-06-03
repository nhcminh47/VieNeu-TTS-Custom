from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from .. import __version__
from ..jobs.queue import JobStatus
from ..models.registry import is_allowed_model_id, list_models
from ..models.voices import list_model_voices
from ..runtime.dtype import dtype_name
from .schemas import (
    HealthResponse,
    ChapterJobCreateRequest,
    ChapterJobStatusResponse,
    RuntimeResponse,
    StorageResponse,
    TtsJobCreateRequest,
    TtsJobCreateResponse,
    TtsJobStatusResponse,
    VoiceInfo,
)


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True, service="vieneu-server", version=__version__)


@router.get("/runtime", response_model=RuntimeResponse)
async def runtime_info(request: Request) -> RuntimeResponse:
    config = request.app.state.config
    runtime = request.app.state.runtime
    return RuntimeResponse(
        backend=config.backend,
        device=runtime.device,
        gpu_name=runtime.gpu_name,
        compute_capability=list(runtime.compute_capability) if runtime.compute_capability else None,
        dtype=dtype_name(runtime.dtype),
        lmdeploy_enabled=not config.disable_lmdeploy,
        flash_attn_enabled=not config.disable_flash_attn,
        torch_compile_enabled=not config.disable_torch_compile,
        reason=runtime.reason,
    )


@router.get("/models")
async def models(request: Request) -> list[dict[str, object]]:
    return list_models(request.app.state.config.model_id)


@router.get("/storage", response_model=StorageResponse)
async def storage_info(request: Request) -> StorageResponse:
    usage = request.app.state.job_manager.storage.usage()
    return StorageResponse(
        output_dir=str(usage.output_dir),
        file_count=usage.file_count,
        total_bytes=usage.total_bytes,
        max_files=usage.max_files,
        max_bytes=usage.max_bytes,
    )


@router.get("/models/{model_id:path}/voices", response_model=list[VoiceInfo])
async def model_voices(model_id: str) -> list[VoiceInfo]:
    if not is_allowed_model_id(model_id):
        raise HTTPException(status_code=404, detail="model not found")
    return [VoiceInfo(**voice) for voice in list_model_voices(model_id)]


@router.post("/tts/jobs", response_model=TtsJobCreateResponse)
async def create_tts_job(
    payload: TtsJobCreateRequest,
    request: Request,
) -> TtsJobCreateResponse:
    manager = request.app.state.job_manager
    config = request.app.state.config
    model_id = payload.model_id or config.model_id
    try:
        job = manager.create_job(
            text=payload.text,
            model_id=model_id,
            voice_reference_id=payload.voice_reference_id,
            voice_reference_path=Path(payload.voice_reference_path) if payload.voice_reference_path else None,
            format_name=payload.format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    manager.start_job(job.job_id)
    return TtsJobCreateResponse(job_id=job.job_id, status=job.status.value)


@router.post("/tts/chapter-jobs", response_model=TtsJobCreateResponse)
async def create_chapter_job(
    payload: ChapterJobCreateRequest,
    request: Request,
) -> TtsJobCreateResponse:
    manager = request.app.state.chapter_job_manager
    config = request.app.state.config
    model_id = payload.model_id or config.model_id
    try:
        job = manager.create_job(
            text=payload.text,
            title=payload.title,
            model_id=model_id,
            voice_reference_id=payload.voice_reference_id,
            voice_reference_path=Path(payload.voice_reference_path) if payload.voice_reference_path else None,
            format_name=payload.format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    manager.start_job(job.job_id)
    return TtsJobCreateResponse(job_id=job.job_id, status=job.status.value)


@router.get("/tts/jobs/{job_id}", response_model=TtsJobStatusResponse)
async def get_tts_job(job_id: str, request: Request) -> TtsJobStatusResponse:
    job = request.app.state.job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return TtsJobStatusResponse(**job.as_dict())


@router.get("/tts/chapter-jobs/{job_id}", response_model=ChapterJobStatusResponse)
async def get_chapter_job(job_id: str, request: Request) -> ChapterJobStatusResponse:
    job = request.app.state.chapter_job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="chapter job not found")
    return ChapterJobStatusResponse(**job.as_dict())


@router.get("/tts/jobs/{job_id}/audio")
async def get_tts_job_audio(job_id: str, request: Request) -> FileResponse:
    job = request.app.state.job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status == JobStatus.COMPLETED and job.audio_path is None:
        raise HTTPException(status_code=410, detail="audio expired by storage retention")
    if job.status != JobStatus.COMPLETED or job.audio_path is None:
        raise HTTPException(status_code=409, detail="audio is not ready")
    if not job.audio_path.exists():
        raise HTTPException(status_code=404, detail="audio file not found")
    return FileResponse(str(job.audio_path), media_type="audio/wav", filename=f"{job_id}.wav")


@router.get("/tts/chapter-jobs/{job_id}/audio")
async def get_chapter_job_audio(job_id: str, request: Request) -> FileResponse:
    job = request.app.state.chapter_job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="chapter job not found")
    if job.status == JobStatus.COMPLETED and job.audio_path is None:
        raise HTTPException(status_code=410, detail="audio expired by storage retention")
    if job.status != JobStatus.COMPLETED or job.audio_path is None:
        raise HTTPException(status_code=409, detail="chapter audio is not ready")
    if not job.audio_path.exists():
        raise HTTPException(status_code=404, detail="chapter audio file not found")
    return FileResponse(str(job.audio_path), media_type="audio/wav", filename=f"{job_id}-chapter.wav")


@router.get("/tts/chapter-jobs/{job_id}/manifest")
async def get_chapter_job_manifest(job_id: str, request: Request) -> FileResponse:
    job = request.app.state.chapter_job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="chapter job not found")
    if job.manifest_path is None:
        raise HTTPException(status_code=409, detail="chapter manifest is not ready")
    if not job.manifest_path.exists():
        raise HTTPException(status_code=404, detail="chapter manifest file not found")
    return FileResponse(str(job.manifest_path), media_type="application/json", filename=f"{job_id}-manifest.json")
