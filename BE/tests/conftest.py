"""
Shared fixtures for the EZRag test suite.

All tests run with external services (ChromaDB, SentenceTransformer, watchdog Observer)
mocked out so the suite is fast and self-contained.
"""

import sys
from unittest.mock import MagicMock

# Pre-stub sentence_transformers before any app module is imported.
# The installed version (2.2.2) is incompatible with the system huggingface_hub
# and raises ImportError at module load time.  A MagicMock satisfies all
# `from sentence_transformers import SentenceTransformer` calls in app code.
sys.modules.setdefault("sentence_transformers", MagicMock())

import pytest

# Import app modules once here (after stubs) so the autouse fixtures can
# reference them without re-importing on every test.
import app.watch as _watch_module
from app.status import model_status, ingestion_status
import app.ingest as _ingest_module


# ---------------------------------------------------------------------------
# Status reset
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_status():
    """Return singleton status objects to their initial state between tests."""
    def _reset():
        model_status.state = "idle"
        model_status.progress = 0.0
        model_status.message = ""
        ingestion_status.state = "idle"
        ingestion_status.files_done = 0
        ingestion_status.files_total = 0

    _reset()
    yield
    _reset()


# ---------------------------------------------------------------------------
# Watcher global reset
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_observer():
    """Ensure the module-level _observer is None between tests."""
    _watch_module._observer = None
    yield
    if _watch_module._observer:
        try:
            _watch_module._observer.stop()
        except Exception:
            pass
    _watch_module._observer = None


# ---------------------------------------------------------------------------
# Embedding model cache reset
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_embedding_cache():
    """Clear the cached SentenceTransformer instance between tests."""
    _ingest_module._embedding_model = None
    yield
    _ingest_module._embedding_model = None


# ---------------------------------------------------------------------------
# External service mocks (opt-in)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_collection(mocker):
    """A pre-configured mock ChromaDB collection."""
    col = mocker.MagicMock()
    col.count.return_value = 0
    col.get.return_value = {"ids": [], "metadatas": [], "documents": []}
    col.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    return col


@pytest.fixture
def mock_chromadb(mocker, mock_collection):
    """Patch chromadb.HttpClient to return the mock collection."""
    client = mocker.MagicMock()
    client.get_or_create_collection.return_value = mock_collection
    mocker.patch("chromadb.HttpClient", return_value=client)
    return mock_collection


@pytest.fixture
def mock_embed_model(mocker):
    """
    Patch SentenceTransformer in app.ingest so no model is downloaded.

    We patch the name bound in app.ingest (not sentence_transformers.SentenceTransformer)
    because the from-import already captured the reference at module load time.
    """
    model = mocker.MagicMock()
    model.encode.return_value = [0.0] * 384
    mocker.patch("app.ingest.SentenceTransformer", return_value=model)
    return model


# ---------------------------------------------------------------------------
# FastAPI TestClient (all background tasks mocked)
# ---------------------------------------------------------------------------

@pytest.fixture
def app_client(mocker):
    """
    FastAPI TestClient with every startup side-effect mocked.

    Ingestion, model loading, and the file watcher are all replaced with no-ops
    so the test server starts and stops instantly.
    """
    mocker.patch("app.main._run_ingestion")
    mocker.patch("app.main.start_model_loading")
    mocker.patch("app.main.start_watching")
    mocker.patch("app.main.stop_watching")

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        yield client
