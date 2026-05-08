import logging
from typing import Any

import requests

from . import config
from .ingest import get_collection, get_embedding_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def _api_generate(messages: list) -> str:
    url = f"{config.MODEL_BASE_URL}/api/chat"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def retrieve(question: str) -> dict:
    """Return raw chunks from ChromaDB without calling the LLM.
    Used by the MCP server so Claude can answer from the retrieved context itself.
    """
    collection = get_collection()
    embed_model = get_embedding_model()

    q_embedding = embed_model.encode(question).tolist()

    try:
        total = collection.count()
        n = min(config.QUERY_N_RESULTS, total) if total > 0 else 0
        results = collection.query(
            query_embeddings=[q_embedding],
            n_results=n,
            where={"deleted": 0},
            include=["documents", "metadatas", "distances"],
        ) if n > 0 else {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    except Exception as e:
        logger.error(f"ChromaDB retrieve error: {e}")
        results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    chunks = []
    for doc, meta, dist in zip(docs, metas, distances):
        if meta.get("deleted", 0):
            continue
        chunks.append({
            "text": doc,
            "source": meta["source"],
            "filename": meta["filename"],
            "chunk_index": meta.get("chunk_index", 0),
            "score": round(1 - dist, 4),
        })

    return {"chunks": chunks}


def _build_context(results: dict) -> tuple:
    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]

    sources = []
    context_parts = []
    seen_sources: set = set()

    for doc, meta in zip(docs, metas):
        if meta.get("deleted", 0):
            continue
        source = meta["source"]
        filename = meta["filename"]
        context_parts.append(f"[Source: {filename} | {source}]\n{doc}")
        if source not in seen_sources:
            seen_sources.add(source)
            sources.append({"source": source, "filename": filename})

    return "\n\n---\n\n".join(context_parts), sources


def query(question: str) -> dict:
    collection = get_collection()
    embed_model = get_embedding_model()

    q_embedding = embed_model.encode(question).tolist()

    try:
        total = collection.count()
        n = min(config.QUERY_N_RESULTS, total) if total > 0 else 0
        results = collection.query(
            query_embeddings=[q_embedding],
            n_results=n,
            where={"deleted": 0},
            include=["documents", "metadatas", "distances"],
        ) if n > 0 else {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    except Exception as e:
        logger.error(f"ChromaDB query error: {e}")
        results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    context, sources = _build_context(results)

    if context:
        system_msg = (
            "You are a helpful assistant with access to a curated knowledge base. "
            "Answer the user's question using only the provided context. "
            "Always cite your sources by referencing the filename(s). "
            "If the context is insufficient, say so explicitly — do not invent information."
            f"\n\nContext:\n{context}"
        )
    else:
        system_msg = (
            "You are a helpful assistant. The knowledge base does not contain any relevant "
            "information about this topic. Tell the user clearly that no relevant information "
            "was found in the knowledge base."
        )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": question},
    ]

    answer = _api_generate(messages)
    return {"answer": answer, "sources": sources}
