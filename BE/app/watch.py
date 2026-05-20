"""
Filesystem watcher for RAG source directories.

RagFileHandler translates watchdog filesystem events into ChromaDB operations:
  - File created  → ingest_file()   (embed and upsert into ChromaDB)
  - File deleted  → mark_deleted()  (sets deleted=1 in ChromaDB metadata)
  - File moved    → mark_deleted() old path + ingest_file() new path

start_watching() is called once during lifespan startup.  It schedules one
watchdog Observer across all configured RAG_DIRS.  Directories that don't
exist yet are silently skipped.  stop_watching() is called on shutdown.
"""

import logging
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from . import config
from .ingest import get_collection, ingest_file, mark_deleted

logger = logging.getLogger(__name__)

_observer = None


def _should_skip(path: str) -> bool:
    """Return True if the path should be excluded based on config."""
    p = Path(path)
    if config.IGNORE_DOTFILES and any(part.startswith(".") for part in p.parts):
        return True
    if config.IGNORE_DIRS and any(part in config.IGNORE_DIRS for part in p.parts):
        return True
    if config.INGEST_EXTENSIONS and p.suffix.lower().lstrip(".") not in config.INGEST_EXTENSIONS:
        return True
    return False


class RagFileHandler(FileSystemEventHandler):
    def __init__(self):
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = get_collection()
        return self._collection

    def on_created(self, event):
        if not event.is_directory and not _should_skip(event.src_path):
            logger.info(f"File created: {event.src_path}")
            try:
                ingest_file(event.src_path, self.collection)
            except Exception as e:
                logger.error(f"Error ingesting {event.src_path}: {e}")

    def on_deleted(self, event):
        if not event.is_directory and not _should_skip(event.src_path):
            logger.info(f"File deleted: {event.src_path}")
            try:
                mark_deleted(event.src_path, self.collection)
            except Exception as e:
                logger.error(f"Error marking deleted {event.src_path}: {e}")

    def on_moved(self, event):
        if not event.is_directory and not _should_skip(event.src_path) and not _should_skip(event.dest_path):
            logger.info(f"File moved: {event.src_path} -> {event.dest_path}")
            try:
                mark_deleted(event.src_path, self.collection)
                ingest_file(event.dest_path, self.collection)
            except Exception as e:
                logger.error(f"Error handling move {event.src_path}: {e}")


def start_watching() -> None:
    global _observer
    if _observer is not None:
        return

    handler = RagFileHandler()
    _observer = Observer()

    watched = 0
    for directory in config.RAG_DIRS:
        path = Path(directory)
        if path.exists():
            _observer.schedule(handler, str(path), recursive=True)
            logger.info(f"Watching directory: {directory}")
            watched += 1
        else:
            logger.warning(f"Watch directory not found (will skip): {directory}")

    if watched:
        _observer.start()
        logger.info("File watcher started")
    else:
        logger.warning("No valid directories to watch — file watcher not started")
        _observer = None


def stop_watching() -> None:
    global _observer
    if _observer:
        _observer.stop()
        _observer.join()
        _observer = None
        logger.info("File watcher stopped")
