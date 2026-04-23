"""Shared in-process status state. Written by background threads, read by /status endpoint."""


class ModelStatus:
    def __init__(self):
        self.state: str = "idle"   # idle | loading | ready | error
        self.progress: float = 0.0  # 0.0–1.0
        self.message: str = ""

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "progress": round(self.progress, 3),
            "message": self.message,
        }


class IngestionStatus:
    def __init__(self):
        self.state: str = "idle"   # idle | running | done
        self.files_done: int = 0
        self.files_total: int = 0

    @property
    def progress(self) -> float:
        if self.files_total == 0:
            return 0.0
        return self.files_done / self.files_total

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "progress": round(self.progress, 3),
            "files_done": self.files_done,
            "files_total": self.files_total,
        }


model_status = ModelStatus()
ingestion_status = IngestionStatus()
