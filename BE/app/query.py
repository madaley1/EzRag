import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from . import config
from .ingest import get_collection, get_embedding_model
from .web_search import search_web, format_web_context

logger = logging.getLogger(__name__)

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

def retrieve(question: str) -> dict:
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

def _build_context_with_distances(results: dict) -> tuple:
    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    strong_parts = []
    weak_parts = []
    strong_sources = []
    weak_sources = []
    seen_strong: set = set()
    seen_weak: set = set()

    for doc, meta, dist in zip(docs, metas, distances):
        if meta.get("deleted", 0):
            continue
        source = meta["source"]
        filename = meta["filename"]
        entry = f"[Source: {filename}]\n{doc}"

        if dist <= config.DISTANCE_THRESHOLD_STRONG:
            strong_parts.append(entry)
            if source not in seen_strong:
                seen_strong.add(source)
                strong_sources.append({"source": source, "filename": filename})
        elif dist <= config.DISTANCE_THRESHOLD_WEAK:
            weak_parts.append(entry)
            if source not in seen_weak:
                seen_weak.add(source)
                weak_sources.append({"source": source, "filename": filename})

    strong_ctx = "\n\n---\n\n".join(strong_parts)
    weak_ctx = "\n\n---\n\n".join(weak_parts)
    return strong_ctx, weak_ctx, strong_sources, weak_sources

def _write_note(question: str, answer: str, sources: list[dict]) -> str | None:
    try:
        out_dir = Path(config.STORAGE_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^\w\s-]", "", question[:50]).strip().replace(" ", "_").lower()
        filename = f"{timestamp}_{slug}.md"
        filepath = out_dir / filename

        source_list = "\n".join(
            f"- [{s['filename']}]({s['source']})" for s in sources
        )

        content = (
            f"---\n"
            f"generated: true\n"
            f"date: {datetime.now().isoformat()}\n"
            f"question: \"{question}\"\n"
            f"---\n\n"
            f"# {question}\n\n"
            f"{answer}\n\n"
            f"## Sources\n\n"
            f"{source_list}\n"
        )

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Stored note: {filepath}")
        return str(filepath)
    except Exception as e:
        logger.error(f"Failed to write note: {e}")
        return None

def _build_system_prompt(
    rigidity: str,
    strong_ctx: str,
    weak_ctx: str,
    web_ctx: str | None,
    connectivity: bool,
) -> str:

    has_strong = bool(strong_ctx)
    has_weak = bool(weak_ctx)
    has_web = bool(web_ctx)

    if rigidity == "strict":
        if has_strong:
            context_block = strong_ctx
            if connectivity and has_web:
                context_block += f"\n\n===\n\nWeb search results:\n{web_ctx}"
            return (
                "You are a helpful assistant with access to a curated knowledge base. "
                "Answer the user's question using only the provided context. "
                "Always cite your sources by referencing the filename(s). "
                "If a source is only tangentially related (shares a keyword but is about "
                "a different topic), acknowledge it as a weak match rather than presenting "
                "it as the answer. Do not invent information beyond what the sources provide."
                f"\n\nContext:\n{context_block}"
            )
        else:
            return (
                "You are a helpful assistant. The knowledge base does not contain any "
                "relevant information about this topic. Tell the user clearly that no "
                "relevant information was found in the knowledge base."
            )

    if rigidity == "suggestive":
        if has_strong:
            context_block = strong_ctx
            if connectivity and has_web:
                context_block += f"\n\n===\n\nWeb search results:\n{web_ctx}"
            return (
                "You are a helpful assistant with access to a curated knowledge base. "
                "Answer the user's question using the provided context. "
                "Always cite your sources by referencing the filename(s). "
                "Do not invent information beyond what the sources provide."
                f"\n\nContext:\n{context_block}"
            )
        elif has_weak:
            context_block = weak_ctx
            if connectivity and has_web:
                context_block += f"\n\n===\n\nWeb search results:\n{web_ctx}"
            return (
                "You are a helpful assistant with access to a curated knowledge base. "
                "The search returned some results, but they are only loosely related to "
                "the user's question. Present them as suggestions — say something like: "
                "\"I couldn't find much information on your request, but here's the "
                "closest thing I could find.\" Do NOT present these as direct answers. "
                "Briefly describe what each source contains and why it might be tangentially "
                "relevant. Do not invent information."
                f"\n\nPartially related context:\n{context_block}"
            )
        elif connectivity and has_web:
            return (
                "You are a helpful assistant. The local knowledge base did not contain "
                "relevant information, but web search results are available. "
                "Answer using the web results and cite URLs. Stay factual."
                f"\n\nWeb search results:\n{web_ctx}"
            )
        else:
            return (
                "You are a helpful assistant. The knowledge base does not contain any "
                "relevant information about this topic. Tell the user clearly that no "
                "relevant information was found."
            )

    local_parts = []
    if has_strong:
        local_parts.append(strong_ctx)
    if has_weak:
        local_parts.append(weak_ctx)
    local_ctx = "\n\n---\n\n".join(local_parts)

    parts = []
    if local_ctx:
        parts.append(f"Local knowledge base:\n{local_ctx}")
    if connectivity and has_web:
        parts.append(f"Web search results:\n{web_ctx}")

    if parts:
        combined = "\n\n===\n\n".join(parts)
        return (
            "You are a helpful assistant with access to a local knowledge base"
            + (" and web search results" if connectivity and has_web else "")
            + ". Answer the user's question using the provided context as a starting point. "
            "You may infer connections between multiple sources, extrapolate from context "
            "clues, and provide your best educated interpretation even when sources don't "
            "explicitly state the answer. Clearly distinguish between what sources directly "
            "state vs. what you are inferring. Cite your sources where applicable."
            f"\n\n{combined}"
        )
    else:
        return (
            "You are a helpful assistant. No local sources or web results were found. "
            "Answer the user's question to the best of your ability based on your training, "
            "but clearly state that this is from general knowledge, not from their documents."
        )

def query(question: str, settings: dict | None = None) -> dict:
    s = settings or {}
    rigidity = s.get("rigidity") or config.RIGIDITY
    connectivity = s.get("connectivity") if s.get("connectivity") is not None else config.CONNECTIVITY
    storage = s.get("storage") if s.get("storage") is not None else config.STORAGE

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

    strong_ctx, weak_ctx, strong_sources, weak_sources = _build_context_with_distances(results)

    web_ctx = None
    web_sources = []
    if connectivity:
        web_results = search_web(question)
        web_ctx = format_web_context(web_results)
        web_sources = [{"source": r["url"], "filename": r["title"]} for r in web_results]

    system_msg = _build_system_prompt(rigidity, strong_ctx, weak_ctx, web_ctx, connectivity)

    if rigidity == "strict":
        local_sources = strong_sources
    elif rigidity == "suggestive":
        local_sources = strong_sources if strong_sources else weak_sources
    else:
        local_sources = strong_sources + weak_sources

    all_sources = local_sources + web_sources

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": question},
    ]
    answer = _api_generate(messages)

    result = {"answer": answer, "sources": all_sources}

    if storage:
        note_path = _write_note(question, answer, all_sources)
        if note_path:
            result["stored"] = note_path

    return result
