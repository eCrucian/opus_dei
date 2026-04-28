"""Job persistence — JSON files in storage/sessions/."""
import json
from pathlib import Path
from typing import Optional
from app.config import settings
from app.models.validation import ValidationJob


def _job_path(job_id: str) -> Path:
    return settings.sessions_dir / f"{job_id}.json"


def save_job(job: ValidationJob) -> None:
    path = _job_path(job.job_id)
    path.write_text(job.model_dump_json(indent=2), encoding="utf-8")


def load_job(job_id: str) -> Optional[ValidationJob]:
    path = _job_path(job_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ValidationJob(**data)


def list_jobs() -> list[dict]:
    jobs = []
    for p in sorted(settings.sessions_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            jobs.append({
                "job_id": data["job_id"],
                "status": data["status"],
                "created_at": data["created_at"],
                "doc_filename": data.get("doc_filename"),
                "product_type": (data.get("model_understanding") or {}).get("product_type"),
            })
        except Exception:
            continue
    return jobs
