import os

RAG_DIRS = [d.strip() for d in os.getenv("RAG_DIRS", "/data").split(",") if d.strip()]
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "ezrag")
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
QUERY_N_RESULTS = int(os.getenv("QUERY_N_RESULTS", "5"))
IGNORE_DOTFILES = os.getenv("IGNORE_DOTFILES", "true").lower() in ("1", "true", "yes")
IGNORE_DIRS = {d.strip() for d in os.getenv("IGNORE_DIRS", "node_modules").split(",") if d.strip()}
INGEST_EXTENSIONS: set | None = (
    {e.strip().lower().lstrip(".") for e in os.getenv("INGEST_EXTENSIONS", "").split(",") if e.strip()}
    or None
)
