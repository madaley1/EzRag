"""
Integration tests for server startup behavior.

These tests verify that:
- The HTTP server is ready immediately (before background tasks complete).
- The /status endpoint accurately reflects ingestion and model state.
- Background tasks (ingestion, file watcher) are all started at startup
  and the watcher is stopped cleanly at shutdown.
- The WebSocket endpoint handles queries correctly.

All external services are mocked via the app_client fixture in conftest.py.
"""

import pytest
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


def test_status_model_idle(app_client):
    """Model state stays idle (Ollama/OpenAI used via API)."""
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
    mocker.patch("app.main.start_watching")
    mocker.patch("app.main.stop_watching")

    from app.main import app
    with TestClient(app):
        pass

    run_mock.assert_called_once()


def test_file_watcher_starts_at_startup(mocker):
    mocker.patch("app.main._run_ingestion")
    watch_mock = mocker.patch("app.main.start_watching")
    mocker.patch("app.main.stop_watching")

    from app.main import app
    with TestClient(app):
        pass

    watch_mock.assert_called_once()


def test_file_watcher_stops_on_shutdown(mocker):
    mocker.patch("app.main._run_ingestion")
    mocker.patch("app.main.start_watching")
    stop_mock = mocker.patch("app.main.stop_watching")

    from app.main import app
    with TestClient(app):
        pass

    stop_mock.assert_called_once()


# ---------------------------------------------------------------------------
# WebSocket — query handling
# ---------------------------------------------------------------------------

def test_ws_query_returns_answer(app_client, mocker):
    """Queries proceed normally via Ollama/OpenAI API."""
    mocker.patch("app.main.query", return_value={"answer": "hi", "sources": []})

    with app_client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"message": "hello"})
        data = ws.receive_json()

    assert data["type"] == "answer"
