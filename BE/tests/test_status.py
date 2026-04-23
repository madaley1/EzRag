"""Unit tests for the status state objects (app/status.py)."""

import pytest
from app.status import ModelStatus, IngestionStatus


class TestModelStatus:
    def test_initial_state(self):
        s = ModelStatus()
        assert s.state == "idle"
        assert s.progress == 0.0
        assert s.message == ""

    def test_as_dict_keys(self):
        s = ModelStatus()
        d = s.as_dict()
        assert set(d.keys()) == {"state", "progress", "message"}

    def test_as_dict_progress_rounded(self):
        s = ModelStatus()
        s.progress = 0.123456789
        assert s.as_dict()["progress"] == pytest.approx(0.123, abs=0.001)

    def test_state_transitions(self):
        s = ModelStatus()
        for state in ("idle", "loading", "ready", "error"):
            s.state = state
            assert s.as_dict()["state"] == state

    def test_progress_clamped_in_dict(self):
        s = ModelStatus()
        s.progress = 0.75
        s.message = "Loading Qwen3-32B…"
        d = s.as_dict()
        assert 0.0 <= d["progress"] <= 1.0
        assert "Qwen3" in d["message"]


class TestIngestionStatus:
    def test_initial_state(self):
        s = IngestionStatus()
        assert s.state == "idle"
        assert s.files_done == 0
        assert s.files_total == 0

    def test_progress_zero_when_total_unknown(self):
        s = IngestionStatus()
        assert s.progress == 0.0

    def test_progress_calculation(self):
        s = IngestionStatus()
        s.files_done = 3
        s.files_total = 12
        assert s.progress == pytest.approx(0.25)

    def test_progress_full_when_complete(self):
        s = IngestionStatus()
        s.files_done = 50
        s.files_total = 50
        assert s.progress == pytest.approx(1.0)

    def test_as_dict_keys(self):
        s = IngestionStatus()
        d = s.as_dict()
        assert set(d.keys()) == {"state", "progress", "files_done", "files_total"}

    def test_as_dict_reflects_live_counts(self):
        s = IngestionStatus()
        s.state = "running"
        s.files_done = 7
        s.files_total = 20
        d = s.as_dict()
        assert d["state"] == "running"
        assert d["files_done"] == 7
        assert d["files_total"] == 20
        assert d["progress"] == pytest.approx(0.35)
