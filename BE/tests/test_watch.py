"""
Unit tests for the filesystem watcher (app/watch.py).

RagFileHandler translates watchdog events into ingest/mark-deleted calls.
start_watching / stop_watching manage the Observer lifecycle.
"""

import pytest
from unittest.mock import MagicMock, patch
from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    DirCreatedEvent,
    DirDeletedEvent,
)


# ---------------------------------------------------------------------------
# RagFileHandler — event routing
# ---------------------------------------------------------------------------

@pytest.fixture
def handler(mocker):
    """RagFileHandler with a pre-injected mock collection."""
    mocker.patch("app.watch.get_collection", return_value=MagicMock())
    from app.watch import RagFileHandler
    h = RagFileHandler()
    _ = h.collection  # prime the lazy property
    return h


def test_created_file_is_ingested(handler, mocker):
    ingest = mocker.patch("app.watch.ingest_file")
    handler.on_created(FileCreatedEvent("/data/report.pdf"))
    ingest.assert_called_once_with("/data/report.pdf", handler.collection)


def test_created_directory_is_ignored(handler, mocker):
    ingest = mocker.patch("app.watch.ingest_file")
    handler.on_created(DirCreatedEvent("/data/newdir"))
    ingest.assert_not_called()


def test_deleted_file_is_marked(handler, mocker):
    mark = mocker.patch("app.watch.mark_deleted")
    handler.on_deleted(FileDeletedEvent("/data/old.txt"))
    mark.assert_called_once_with("/data/old.txt", handler.collection)


def test_deleted_directory_is_ignored(handler, mocker):
    mark = mocker.patch("app.watch.mark_deleted")
    handler.on_deleted(DirDeletedEvent("/data/olddir"))
    mark.assert_not_called()


def test_moved_file_marks_old_and_ingests_new(handler, mocker):
    mark = mocker.patch("app.watch.mark_deleted")
    ingest = mocker.patch("app.watch.ingest_file")
    handler.on_moved(FileMovedEvent("/data/a.txt", "/data/b.txt"))
    mark.assert_called_once_with("/data/a.txt", handler.collection)
    ingest.assert_called_once_with("/data/b.txt", handler.collection)


def test_ingest_error_is_swallowed(handler, mocker):
    """Handler must not propagate exceptions — watchdog runs it in its own thread."""
    mocker.patch("app.watch.ingest_file", side_effect=RuntimeError("disk full"))
    handler.on_created(FileCreatedEvent("/data/bad.bin"))  # should not raise


def test_mark_deleted_error_is_swallowed(handler, mocker):
    mocker.patch("app.watch.mark_deleted", side_effect=RuntimeError("db down"))
    handler.on_deleted(FileDeletedEvent("/data/gone.txt"))  # should not raise


def test_moved_error_is_swallowed(handler, mocker):
    mocker.patch("app.watch.mark_deleted", side_effect=RuntimeError("db down"))
    mocker.patch("app.watch.ingest_file")
    handler.on_moved(FileMovedEvent("/data/a.txt", "/data/b.txt"))  # should not raise


# ---------------------------------------------------------------------------
# start_watching / stop_watching — Observer lifecycle
# ---------------------------------------------------------------------------

def test_start_watching_schedules_existing_directory(mocker, tmp_path):
    mocker.patch("app.watch.config.RAG_DIRS", [str(tmp_path)])
    observer = MagicMock()
    mocker.patch("app.watch.Observer", return_value=observer)

    from app.watch import start_watching
    start_watching()

    observer.schedule.assert_called_once()
    observer.start.assert_called_once()


def test_start_watching_skips_missing_directory(mocker, tmp_path):
    missing = str(tmp_path / "does_not_exist")
    mocker.patch("app.watch.config.RAG_DIRS", [missing])
    observer = MagicMock()
    mocker.patch("app.watch.Observer", return_value=observer)

    from app.watch import start_watching
    start_watching()

    observer.schedule.assert_not_called()
    observer.start.assert_not_called()


def test_start_watching_is_idempotent(mocker, tmp_path):
    """Calling start_watching twice must not create a second Observer."""
    mocker.patch("app.watch.config.RAG_DIRS", [str(tmp_path)])
    observer = MagicMock()
    mocker.patch("app.watch.Observer", return_value=observer)

    import app.watch as watch_module
    from app.watch import start_watching
    start_watching()
    start_watching()  # second call is a no-op

    assert observer.start.call_count == 1


def test_stop_watching_stops_and_clears_observer(mocker, tmp_path):
    mocker.patch("app.watch.config.RAG_DIRS", [str(tmp_path)])
    observer = MagicMock()
    mocker.patch("app.watch.Observer", return_value=observer)

    from app.watch import start_watching, stop_watching
    start_watching()
    stop_watching()

    observer.stop.assert_called_once()
    observer.join.assert_called_once()

    import app.watch as watch_module
    assert watch_module._observer is None


def test_stop_watching_is_safe_when_never_started():
    """stop_watching must not raise if the watcher was never started."""
    from app.watch import stop_watching
    stop_watching()  # _observer is None — no-op


def test_stop_watching_is_safe_called_twice(mocker, tmp_path):
    mocker.patch("app.watch.config.RAG_DIRS", [str(tmp_path)])
    mocker.patch("app.watch.Observer", return_value=MagicMock())

    from app.watch import start_watching, stop_watching
    start_watching()
    stop_watching()
    stop_watching()  # second call — should not raise
