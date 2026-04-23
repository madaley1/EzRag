import os

RAG_DIRS = [d.strip() for d in os.getenv("RAG_DIRS", "/data").split(",") if d.strip()]
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "ezrag")
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Set to an absolute path to load a local HuggingFace model instead of Ollama/OpenAI.
# Requires: pip install -r requirements-local-llm.txt
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "")
# Device for local model: "auto" lets accelerate decide (picks MPS on Apple Silicon, CUDA on NVIDIA)
LOCAL_MODEL_DEVICE = os.getenv("LOCAL_MODEL_DEVICE", "auto")
LOCAL_MODEL_MAX_NEW_TOKENS = int(os.getenv("LOCAL_MODEL_MAX_NEW_TOKENS", "1024"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
QUERY_N_RESULTS = int(os.getenv("QUERY_N_RESULTS", "5"))
