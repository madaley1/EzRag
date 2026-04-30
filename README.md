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
- Ollama (local LLM inference)
- websockets
- watchdog
- Apache Tika (remote service for document extraction)

### Infrastructure

- Docker Compose
- Ollama (qwen3:1.7b, auto-pulled on first start)
- ChromaDB 0.4.14 (vector store)
- Apache Tika (document parsing — PDFs, DOCX, etc.)
- Redis

## Repository Layout

- `FE/` — Vue frontend
- `BE/` — Python backend
- `data/` — Drop files here for ingestion (mounted at `/data` in BE container)
- `docker-compose.dev.yml` — dev services with file watching/sync
- `docker-compose.template.yml` — minimal template for reference
- `README.spec.md` — project acceptance criteria and roadmap

## Prerequisites

- Docker Desktop (with Compose v2, supports `compose develop watch`)
- Bun (for local FE workflows if needed)
- Python 3.11+ (for local BE workflows if needed)

## Development (Docker, Recommended)

Start all services with live development sync:

1. From repo root, run: `docker compose -f docker-compose.dev.yml up --watch`
2. Frontend is available at: <http://localhost:5173>
3. Backend API is available at: <http://localhost:8000>
4. Place files in `./data/` — they are mounted into the BE container at `/data` and ingested automatically.

On first start, the Ollama model (`qwen3:1.7b`) is pulled automatically. Subsequent starts use the cached model from the `ollama_data` volume.

Notes:

- FE changes in `FE/` sync into the FE container and hot-reload.
- BE changes in `BE/` sync into the BE container; Uvicorn reload is enabled.
- Changes to `FE/package.json`, `FE/bun.lock`, or `BE/requirements.txt` trigger service rebuilds.
- Tika runs as a separate container — no Java needed in the BE image.

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
5. Ensure ChromaDB, Redis, Ollama, and Tika are running (e.g. via `docker compose -f docker-compose.dev.yml up -d chromadb redis model tika`)
6. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

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
  "model":     { "state": "idle", "progress": 0.0, "message": "" },
  "ingestion": { "state": "running", "progress": 0.45, "files_done": 45, "files_total": 100 }
}
```

`model.state` values: `idle` | `loading` | `ready` | `error`

`ingestion.state` values: `idle` | `running` | `done`

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
