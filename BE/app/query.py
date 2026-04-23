import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from . import config
from .ingest import get_collection, get_embedding_model
from .status import model_status

logger = logging.getLogger(__name__)

_local_model: Any = None
_local_tokenizer: Any = None
_model_ready = threading.Event()  # set once the model is loaded and usable


# ---------------------------------------------------------------------------
# Background model loading
# ---------------------------------------------------------------------------

def start_model_loading() -> None:
    """Kick off local model loading in a daemon thread. No-op if not configured."""
    if not config.LOCAL_MODEL_PATH:
        return
    t = threading.Thread(target=_load_model_bg, daemon=True, name="model-loader")
    t.start()


def _estimate_load_seconds() -> float:
    """Estimate load time from safetensors shard sizes. Falls back to 90 s."""
    try:
        model_path = Path(config.LOCAL_MODEL_PATH)
        index_file = model_path / "model.safetensors.index.json"
        if index_file.exists():
            with open(index_file) as f:
                index = json.load(f)
            shard_files = set(index["weight_map"].values())
            total_bytes = sum((model_path / sf).stat().st_size for sf in shard_files)
        else:
            sf = model_path / "model.safetensors"
            total_bytes = sf.stat().st_size if sf.exists() else 100 * 1024 ** 3

        throughput = 2.0 * 1024 ** 3  # 2 GB/s — conservative NVMe → RAM estimate
        return total_bytes / throughput
    except Exception:
        return 90.0


def _load_model_bg() -> None:
    global _local_model, _local_tokenizer

    model_name = Path(config.LOCAL_MODEL_PATH).name
    model_status.state = "loading"
    model_status.message = f"Loading {model_name}…"

    estimated_secs = _estimate_load_seconds()
    start = time.monotonic()

    def _progress_monitor():
        while model_status.state == "loading":
            elapsed = time.monotonic() - start
            model_status.progress = min(elapsed / estimated_secs, 0.95)
            time.sleep(0.5)

    threading.Thread(target=_progress_monitor, daemon=True, name="model-progress").start()

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        model_status.state = "error"
        model_status.message = (
            "transformers/torch not installed — run: pip install -r requirements-local-llm.txt"
        )
        return

    try:
        _local_tokenizer = AutoTokenizer.from_pretrained(config.LOCAL_MODEL_PATH)
        _local_model = AutoModelForCausalLM.from_pretrained(
            config.LOCAL_MODEL_PATH,
            torch_dtype=torch.bfloat16,
            device_map=config.LOCAL_MODEL_DEVICE,
        )
        _local_model.eval()

        model_status.state = "ready"
        model_status.progress = 1.0
        model_status.message = f"{model_name} ready"
        _model_ready.set()
        logger.info(f"Local model loaded in {time.monotonic() - start:.1f}s")
    except Exception as e:
        model_status.state = "error"
        model_status.message = str(e)
        logger.error(f"Failed to load local model: {e}")


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def _local_generate(messages: list) -> str:
    import torch

    _model_ready.wait()  # blocks caller until load completes (safety net)

    try:
        text = _local_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,  # Qwen3 — disable chain-of-thought for RAG answers
        )
    except TypeError:
        text = _local_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    inputs = _local_tokenizer([text], return_tensors="pt").to(_local_model.device)

    with torch.no_grad():
        output_ids = _local_model.generate(
            **inputs,
            max_new_tokens=config.LOCAL_MODEL_MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=_local_tokenizer.eos_token_id,
        )

    new_tokens = output_ids[0][inputs.input_ids.shape[-1]:]
    return _local_tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def _api_generate(messages: list) -> str:
    if config.OPENAI_API_KEY:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        model_name = "gpt-4o-mini"
    else:
        client = OpenAI(base_url=f"{config.MODEL_BASE_URL}/v1", api_key="ollama")
        model_name = config.OLLAMA_MODEL

    response = client.chat.completions.create(model=model_name, messages=messages)
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Public query function
# ---------------------------------------------------------------------------

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

    answer = _local_generate(messages) if config.LOCAL_MODEL_PATH else _api_generate(messages)
    return {"answer": answer, "sources": sources}
