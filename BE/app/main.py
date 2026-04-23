"""
EZRag FastAPI application entry point.

Startup sequence (all steps happen concurrently so the server accepts
requests the moment uvicorn is ready):

1. Uvicorn binds the port — HTTP is immediately available.
2. lifespan() fires two background tasks via the thread pool:
   a. _run_ingestion() — recursively walks every RAG_DIRS path, extracts
      text via Tika, embeds with sentence-transformers, and upserts into
      ChromaDB.  Progress is tracked in ingestion_status.
   b. start_model_loading() — if LOCAL_MODEL_PATH is set, loads the
      HuggingFace model in bf16 and tracks estimated % complete in
      model_status.  No-op when using Ollama or OpenAI.
3. start_watching() — watchdog Observer begins monitoring RAG_DIRS for
   file creates/deletes/renames and updates ChromaDB in real time.

Poll GET /status to observe progress.  The WebSocket endpoint (/ws/chat)
gates queries on model readiness when a local model is configured.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .ingest import ingest_directory, list_files, remove_file
from .query import query, start_model_loading
from .status import ingestion_status, model_status
from .watch import start_watching, stop_watching

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _run_ingestion() -> None:
    ingestion_status.state = "running"
    for directory in config.RAG_DIRS:
        ingest_directory(directory)
    ingestion_status.state = "done"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("EZRag starting up")

    loop = asyncio.get_event_loop()

    # Ingestion and model loading run concurrently in the thread pool —
    # the server accepts requests immediately while both work in the background.
    loop.run_in_executor(None, _run_ingestion)
    start_model_loading()  # no-op when LOCAL_MODEL_PATH is unset

    start_watching()
    yield
    stop_watching()
    logger.info("EZRag shutdown complete")


app = FastAPI(title="EZRag", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def get_status():
    return {
        "model": model_status.as_dict(),
        "ingestion": ingestion_status.as_dict(),
    }


@app.get("/files")
async def get_files():
    return {"files": list_files()}


@app.delete("/files")
async def delete_file(path: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: remove_file(path))
    return {"status": "deleted", "path": path}


@app.post("/ingest")
async def trigger_ingest():
    loop = asyncio.get_event_loop()
    ingestion_status.state = "running"
    ingestion_status.files_done = 0
    ingestion_status.files_total = 0

    async def _do():
        await loop.run_in_executor(None, _run_ingestion)

    asyncio.create_task(_do())
    return {"status": "started"}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()
    try:
        while True:
            data = await websocket.receive_json()
            message = (data.get("message") or "").strip()
            if not message:
                continue

            # If a local model is configured but hasn't finished loading yet, tell the client.
            if config.LOCAL_MODEL_PATH and model_status.state == "loading":
                await websocket.send_json({
                    "type": "model_loading",
                    "progress": model_status.progress,
                    "message": model_status.message,
                })
                continue

            try:
                result = await loop.run_in_executor(None, lambda: query(message))
                await websocket.send_json({
                    "type": "answer",
                    "content": result["answer"],
                    "sources": result["sources"],
                })
            except Exception as e:
                logger.error(f"Query error: {e}")
                await websocket.send_json({"type": "error", "content": str(e)})
    except WebSocketDisconnect:
        pass
