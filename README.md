# EZRag

EZRag is a local-first RAG app scaffold designed to make it easy to:

- ingest files from mounted directories,
- embed and store them in a vector database,
- query an LLM with source-backed answers.

## Current Status

The project is in active development.

- Frontend app, router, chat view, and file management view are implemented.
- Backend ingestion, query, and file-watch pipelines are implemented.
- Development compose file is ready.

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
- Ollama (qwen3:1.7b, auto-pulled on first start, can be changed)
- ChromaDB 0.4.14 (vector store)
- Apache Tika (document parsing — PDFs, DOCX, etc.)
- Redis

## Repository Layout

- `FE/` — Vue frontend
- `BE/` — Python backend
- `mcp/` — MCP server exposing semantic search as a Claude Code tool
- `data/` — Drop files here for ingestion (mounted at `/data` in BE container)
- `docker-compose.yml` — default compose; builds FE/BE images
- `docker-compose.dev.example.yml` — dev compose template; copy to `docker-compose.dev.yml` to use
- `docker-compose.local.yml` — local machine overrides (gitignored); add extra volume mounts and env vars here

## Prerequisites

- Docker Desktop (with Compose v2, supports `compose develop watch`)
- Bun (for local FE workflows if needed)
- Python 3.11+ (for local BE workflows if needed)

## Running (pre-built)

For users who just want to run EzRag without modifying the source:

```bash
docker compose up
```

- Frontend: <http://localhost:80>
- Backend API: <http://localhost:8000>
- Drop files in `./data/` to ingest them.

On first start, images are built and the Ollama model is pulled automatically. Subsequent starts are fast.

## Development

### Setup

Copy the dev compose template and create a local overrides file:

```bash
cp docker-compose.dev.example.yml docker-compose.dev.yml
```

Then create `docker-compose.local.yml` (gitignored) to mount extra directories or override env vars without touching tracked files:

```yaml
# docker-compose.local.yml
services:
  be:
    volumes:
      - /absolute/path/to/your/notes:/notes:ro
    environment:
      RAG_DIRS: /data,/notes
```

### Starting services

```bash
docker compose -f docker-compose.dev.yml -f docker-compose.local.yml up --watch
```

Omit `-f docker-compose.local.yml` if you have not created that file.

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000>

Notes:

- FE changes in `FE/` sync into the FE container and hot-reload.
- BE changes in `BE/` sync into the BE container; Uvicorn reload is enabled.
- Changes to `FE/package.json`, `FE/bun.lock`, or `BE/requirements.txt` trigger service rebuilds.
- Tika runs as a separate container — no Java needed in the BE image.

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

1. Stretch goals

   - Store approved web-fetched knowledge in vector DB
   - Persist conversations for future context in a way that doesn't compromise reference integrity

## License

Add your preferred license file and update this section.
