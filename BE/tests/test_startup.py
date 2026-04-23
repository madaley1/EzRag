"""
Integration tests for server startup behavior.

These tests verify that:
- The HTTP server is ready immediately (before background tasks complete).
- The /status endpoint accurately reflects ingestion and model state.
- Background tasks (ingestion, model loading, file watcher) are all started
  at startup and the watcher is stopped cleanly at shutdown.
- The WebSocket endpoint gates queries on model readiness when a local model
  is configured.

All external services are mocked via the app_client fixture in conftest.py.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Server availability
# ---------------------------------------------------------------------------

def test_health_endpoint_is_immediately_available(app_client):
    """GET /health must return 200 before any background work completes."""
    r = app_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /status endpoint structure
# ---------------------------------------------------------------------------

def test_status_endpoint_returns_200(app_client):
    r = app_client.get("/status")
    assert r.status_code == 200


def test_status_has_model_and_ingestion_keys(app_client):
    data = app_client.get("/status").json()
    assert "model" in data
    assert "ingestion" in data


def test_status_model_has_required_fields(app_client):
    model = app_client.get("/status").json()["model"]
    assert {"state", "progress", "message"} <= set(model.keys())


def test_status_ingestion_has_required_fields(app_client):
    ing = app_client.get("/status").json()["ingestion"]
    assert {"state", "progress", "files_done", "files_total"} <= set(ing.keys())


def test_status_model_idle_when_no_local_model_configured(app_client):
    """When LOCAL_MODEL_PATH is unset the model state stays idle (Ollama/OpenAI used)."""
    with patch("app.config.LOCAL_MODEL_PATH", ""):
        data = app_client.get("/status").json()
    assert data["model"]["state"] == "idle"


# ---------------------------------------------------------------------------
# /status reflects live background state
# ---------------------------------------------------------------------------

def test_status_reflects_model_loading(app_client):
    from app.status import model_status
    model_status.state = "loading"
    model_status.progress = 0.42
    model_status.message = "Loading Qwen3-32B…"

    data = app_client.get("/status").json()["model"]
    assert data["state"] == "loading"
    assert data["progress"] == pytest.approx(0.42, abs=0.001)
    assert "Qwen3" in data["message"]


def test_status_reflects_model_ready(app_client):
    from app.status import model_status
    model_status.state = "ready"
    model_status.progress = 1.0
    model_status.message = "Qwen3-32B ready"

    data = app_client.get("/status").json()["model"]
    assert data["state"] == "ready"
    assert data["progress"] == pytest.approx(1.0)


def test_status_reflects_ingestion_running(app_client):
    from app.status import ingestion_status
    ingestion_status.state = "running"
    ingestion_status.files_done = 12
    ingestion_status.files_total = 40

    ing = app_client.get("/status").json()["ingestion"]
    assert ing["state"] == "running"
    assert ing["files_done"] == 12
    assert ing["files_total"] == 40
    assert ing["progress"] == pytest.approx(0.3, abs=0.001)


def test_status_reflects_ingestion_done(app_client):
    from app.status import ingestion_status
    ingestion_status.state = "done"
    ingestion_status.files_done = 100
    ingestion_status.files_total = 100

    ing = app_client.get("/status").json()["ingestion"]
    assert ing["state"] == "done"
    assert ing["progress"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Background task lifecycle
# ---------------------------------------------------------------------------

def test_ingestion_is_submitted_at_startup(mocker):
    """_run_ingestion must be called during lifespan startup."""
    run_mock = mocker.patch("app.main._run_ingestion")
    mocker.patch("app.main.start_model_loading")
    mocker.patch("app.main.start_watching")
    mocker.patch("app.main.stop_watching")

    from app.main import app
    with TestClient(app):
        pass

    run_mock.assert_called_once()


def test_model_loading_is_started_at_startup(mocker):
    """start_model_loading must be called during lifespan startup."""
    mocker.patch("app.main._run_ingestion")
    load_mock = mocker.patch("app.main.start_model_loading")
    mocker.patch("app.main.start_watching")
    mocker.patch("app.main.stop_watching")

    from app.main import app
    with TestClient(app):
        pass

    load_mock.assert_called_once()


def test_file_watcher_starts_at_startup(mocker):
    mocker.patch("app.main._run_ingestion")
    mocker.patch("app.main.start_model_loading")
    watch_mock = mocker.patch("app.main.start_watching")
    mocker.patch("app.main.stop_watching")

    from app.main import app
    with TestClient(app):
        pass

    watch_mock.assert_called_once()


def test_file_watcher_stops_on_shutdown(mocker):
    mocker.patch("app.main._run_ingestion")
    mocker.patch("app.main.start_model_loading")
    mocker.patch("app.main.start_watching")
    stop_mock = mocker.patch("app.main.stop_watching")

    from app.main import app
    with TestClient(app):
        pass

    stop_mock.assert_called_once()


# ---------------------------------------------------------------------------
# WebSocket — model loading gate
# ---------------------------------------------------------------------------

def test_ws_passes_through_when_no_local_model(app_client, mocker):
    """Queries proceed normally when LOCAL_MODEL_PATH is unset."""
    mocker.patch("app.main.query", return_value={"answer": "hi", "sources": []})

    with patch("app.config.LOCAL_MODEL_PATH", ""):
        with app_client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"message": "hello"})
            data = ws.receive_json()

    assert data["type"] == "answer"


def test_ws_returns_model_loading_when_local_model_not_ready(app_client):
    """While the local model is still loading the WS returns a model_loading frame."""
    from app.status import model_status
    model_status.state = "loading"
    model_status.progress = 0.55
    model_status.message = "Loading Qwen3-32B…"

    with patch("app.config.LOCAL_MODEL_PATH", "/path/to/Qwen3-32B"):
        with app_client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"message": "hello"})
            data = ws.receive_json()

    assert data["type"] == "model_loading"
    assert data["progress"] == pytest.approx(0.55, abs=0.001)
    assert data["message"] == "Loading Qwen3-32B…"


def test_ws_does_not_return_model_loading_when_ready(app_client, mocker):
    """Once the model is ready queries are processed, not gated."""
    mocker.patch("app.main.query", return_value={"answer": "ok", "sources": []})

    from app.status import model_status
    model_status.state = "ready"

    with patch("app.config.LOCAL_MODEL_PATH", "/path/to/Qwen3-32B"):
        with app_client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"message": "hello"})
            data = ws.receive_json()

    assert data["type"] == "answer"
