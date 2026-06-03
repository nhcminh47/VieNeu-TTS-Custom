from __future__ import annotations

import logging
import os
import asyncio

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.http import router as http_router
from .api.websocket import router as websocket_router
from .config import ServerConfig
from .inference.engine import TtsEngine, VieNeuTorchEngine
from .jobs.chapter import ChapterJobManager
from .jobs.manager import JobManager
from .runtime.device import RuntimeDevice, get_runtime_device


logging.basicConfig(level=os.getenv("VIENEU_LOG_LEVEL", "INFO").upper())


def create_app(
    config: ServerConfig | None = None,
    engine: TtsEngine | None = None,
    runtime: RuntimeDevice | None = None,
) -> FastAPI:
    config = config or ServerConfig.from_env()
    config.validate()
    runtime = runtime or get_runtime_device(config.device, config.dtype)
    engine = engine or VieNeuTorchEngine(config, runtime)

    app = FastAPI(title="VieNeu Server", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.config = config
    app.state.runtime = runtime
    app.state.engine = engine
    shared_semaphore = asyncio.Semaphore(config.max_concurrent_jobs)
    app.state.job_manager = JobManager(config, engine, shared_semaphore)
    app.state.chapter_job_manager = ChapterJobManager(config, engine, shared_semaphore)
    app.include_router(http_router)
    app.include_router(websocket_router)
    return app


app = create_app()


def main() -> None:
    config = ServerConfig.from_env()
    uvicorn.run("vieneu_server.main:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    main()
