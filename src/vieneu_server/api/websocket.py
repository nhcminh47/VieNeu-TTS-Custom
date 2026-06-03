from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..jobs.queue import JobStatus


router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_events(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    manager = websocket.app.state.job_manager
    if manager.get_job(job_id) is None:
        await websocket.send_json({"type": "job.failed", "job_id": job_id, "status": "failed", "progress": 0.0, "error": "job not found"})
        await websocket.close()
        return

    queue = await manager.subscribe(job_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event.as_dict())
            if event.status in {JobStatus.COMPLETED.value, JobStatus.FAILED.value}:
                await websocket.close()
                return
    except WebSocketDisconnect:
        return
    finally:
        manager.unsubscribe(job_id, queue)


@router.websocket("/ws/chapter-jobs/{job_id}")
async def websocket_chapter_job_events(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    manager = websocket.app.state.chapter_job_manager
    if manager.get_job(job_id) is None:
        await websocket.send_json({"type": "chapter.failed", "job_id": job_id, "status": "failed", "progress": 0.0, "error": "chapter job not found"})
        await websocket.close()
        return

    queue = await manager.subscribe(job_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event.as_dict())
            if event.status in {JobStatus.COMPLETED.value, JobStatus.FAILED.value}:
                await websocket.close()
                return
    except WebSocketDisconnect:
        return
    finally:
        manager.unsubscribe(job_id, queue)
