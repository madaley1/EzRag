# EZRag

EZRag is a local-first RAG app scaffold designed to make it easy to:

- ingest files from mounted directories,
- embed and store them in a vector database,
- query an LLM with source-backed answers.

This repository currently includes:

- FE: Vue 3 + Vite + Bun
- BE: Python FastAPI / LangChain / ChromaDB
- Dev orchestration: Docker Compose with live sync and rebuild watching

## Current Status

The project is in active development.

- Frontend app, router, chat view, and file management view are implemented.
- Backend ingestion, query, and file-watch pipelines are implemented.
- Development compose file is ready.

Specification source: README.spec.md

## Tech Stack

### Frontend

- Vue 3
- Vite
- TypeScript
- Bun

### Backend

- Python 3.11+
- FastAPI
- Uvicorn
- LangChain
- Sentence-Transformers
- ChromaDB
- OpenAI SDK
- websockets
- watchdog
- Apache Tika

## Repository Layout

- `FE/` — Vue frontend
- `BE/` — Python backend
- `docker-compose.dev.yml` — dev services with file watching/sync
- `README.spec.md` — project acceptance criteria and roadmap

## Prerequisites

- Docker Desktop (with Compose v2, supports `compose develop watch`)
- Bun (for local FE workflows if needed)
- Python 3.11+ (for local BE workflows if needed)
- Java runtime for Tika when that parsing flow is implemented

## Development (Docker, Recommended)

Start both FE and BE with live development sync:

1. From repo root, run: `docker compose -f docker-compose.dev.yml up --watch`
2. Frontend is available at: <http://localhost:5173>
3. Backend is available at: <http://localhost:8000>

Notes:

- FE changes in `FE/` sync into the FE container and hot-reload.
- BE changes in `BE/` sync into the BE container; Uvicorn reload is enabled.
- Changes to `FE/package.json`, `FE/bun.lock`, or `BE/requirements.txt` trigger service rebuilds.

## Backend App Module

The backend container starts Uvicorn with `app.main:app`. To override:

```bash
BE_APP_MODULE=main:app docker compose -f docker-compose.dev.yml up --watch
```

## Local Development (Without Docker)

### Frontend (local)

1. `cd FE`
2. `bun install`
3. `bun run dev`

### Backend (local)

1. `cd BE`
2. `python -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Startup Sequence

The server is available immediately. All heavy work runs in background threads so
the UI is never blocked waiting for startup to finish.

```text
uvicorn ready → HTTP available instantly
      │
      ├─ thread: _run_ingestion()
      │    Walk RAG_DIRS → Tika extract → embed → ChromaDB upsert
      │    Updates ingestion_status.files_done / files_total as it goes
      │
      ├─ thread: start_model_loading()   (only when LOCAL_MODEL_PATH is set)
      │    Reads shard sizes → estimates load time → loads model in bf16
      │    Updates model_status.progress every 0.5 s
      │
      └─ start_watching()
           watchdog Observer on all RAG_DIRS
           on_created  → ingest_file()
           on_deleted  → mark_deleted() (sets deleted=1 in ChromaDB metadata)
           on_moved    → mark_deleted() + ingest_file()
```

### Progress monitoring

Poll `GET /status` (the FE does this automatically every 2 s while loading):

```json
{
  "model":     { "state": "loading", "progress": 0.72, "message": "Loading Qwen3-32B…" },
  "ingestion": { "state": "running", "progress": 0.45, "files_done": 45, "files_total": 100 }
}
```

`model.state` values: `idle` (Ollama/OpenAI in use) | `loading` | `ready` | `error`

`ingestion.state` values: `idle` | `running` | `done`

The chat WebSocket (`/ws/chat`) returns a `model_loading` frame instead of an
answer while `model.state == "loading"` and `LOCAL_MODEL_PATH` is set. The FE
disables the input and shows the progress banner automatically.

### Running tests

```bash
cd BE
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

The test suite mocks ChromaDB, SentenceTransformer, and watchdog so no external
services are required.

## Planned Milestones

Based on README.spec.md:

1. Initial ingestion

   - Recursively find files from configured directories
   - Track file paths and metadata
   - Generate embeddings
   - Insert vectors into ChromaDB

1. Query workflow

   - Retrieve relevant context from vector DB
   - Ensure LLM responses cite sources
   - Return explicit "no info found" when context is missing
   - Ask user before external web access

1. Directory change handling

   - Monitor source directories for add/delete
   - Auto-ingest added files
   - Mark deleted files and expose deletion management in FE

1. Stretch goals

   - Store approved web-fetched knowledge in vector DB
   - Persist conversations for future context

## License

Add your preferred license file and update this section.
