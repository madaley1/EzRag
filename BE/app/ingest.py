import hashlib
import logging
from pathlib import Path
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

from . import config
from .status import ingestion_status

logger = logging.getLogger(__name__)


def _is_dotpath(path: str) -> bool:
    return any(part.startswith(".") for part in Path(path).parts)


def _should_skip(file_path: Path, base: Path | None = None) -> bool:
    parts = file_path.relative_to(base).parts if base else file_path.parts
    if config.IGNORE_DOTFILES and any(p.startswith(".") for p in parts):
        return True
    if config.IGNORE_DIRS and any(p in config.IGNORE_DIRS for p in parts):
        return True
    if config.INGEST_EXTENSIONS and file_path.suffix.lower().lstrip(".") not in config.INGEST_EXTENSIONS:
        return True
    return False

_embedding_model: Optional[SentenceTransformer] = None


def _file_id_prefix(path: str) -> str:
    return hashlib.md5(path.encode()).hexdigest()[:12]


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _embedding_model


def get_chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(host=config.CHROMA_HOST, port=config.CHROMA_PORT)


def get_collection(client=None):
    if client is None:
        client = get_chroma_client()
    return client.get_or_create_collection(config.CHROMA_COLLECTION)


def extract_text(file_path: str) -> Optional[str]:
    try:
        from tika import parser as tika_parser
        parsed = tika_parser.from_file(file_path)
        content = (parsed or {}).get("content") or ""
        if content.strip():
            return content.strip()
    except Exception as e:
        logger.warning(f"Tika extraction failed for {file_path}: {e}")

    try:
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Cannot read {file_path}: {e}")
        return None


def ingest_file(file_path: str, collection=None) -> bool:
    if collection is None:
        collection = get_collection()

    path = str(Path(file_path).resolve())
    text = extract_text(path)
    if not text or not text.strip():
        logger.warning(f"No text extracted from {path}")
        return False

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    chunks = splitter.split_text(text)
    if not chunks:
        return False

    model = get_embedding_model()
    embeddings = model.encode(chunks).tolist()

    prefix = _file_id_prefix(path)
    ids = [f"{prefix}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": path,
            "filename": Path(path).name,
            "chunk_index": i,
            "deleted": 0,
        }
        for i in range(len(chunks))
    ]

    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    logger.info(f"Ingested {path}: {len(chunks)} chunks")
    return True


def ingest_directory(directory: str) -> int:
    path = Path(directory)
    if not path.exists():
        logger.warning(f"RAG directory not found: {directory}")
        return 0

    all_files = [
        f for f in path.rglob("*")
        if f.is_file() and not _should_skip(f, base=path)
    ]
    ingestion_status.files_total += len(all_files)

    collection = get_collection()
    count = 0
    for file_path in all_files:
        try:
            if ingest_file(str(file_path), collection):
                count += 1
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}")
        finally:
            ingestion_status.files_done += 1

    logger.info(f"Ingested {count}/{len(all_files)} files from {directory}")
    return count


def mark_deleted(file_path: str, collection=None) -> None:
    if collection is None:
        collection = get_collection()
    path = str(Path(file_path).resolve())

    results = collection.get(where={"source": path}, include=["metadatas"])
    if not results["ids"]:
        return

    updated = [{**m, "deleted": 1} for m in results["metadatas"]]
    collection.update(ids=results["ids"], metadatas=updated)
    logger.info(f"Marked deleted: {path} ({len(results['ids'])} chunks)")


def remove_file(file_path: str, collection=None) -> None:
    if collection is None:
        collection = get_collection()
    path = str(Path(file_path).resolve())

    results = collection.get(where={"source": path})
    if results["ids"]:
        collection.delete(ids=results["ids"])
    logger.info(f"Permanently removed: {path}")


def list_files(collection=None) -> list:
    if collection is None:
        collection = get_collection()

    results = collection.get(include=["metadatas"])
    seen: dict = {}
    for meta in results.get("metadatas") or []:
        source = meta["source"]
        if _should_skip(Path(source)):
            continue
        if source not in seen:
            seen[source] = {
                "source": source,
                "filename": meta["filename"],
                "deleted": bool(meta.get("deleted", 0)),
            }
        elif meta.get("deleted", 0):
            seen[source]["deleted"] = True

    return list(seen.values())
