"""Tests for all API routes — upload, validation, report."""
import io
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from app.main import app
from app.models.validation import ValidationJob, JobStatus, TestResult, TestStatus


client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_doc_upload(content: bytes = b"# Model\n\n$$PV = N$$", filename: str = "model.md"):
    return ("document", (filename, io.BytesIO(content), "text/markdown"))


def _make_code_upload(content: bytes = b"class ModelPricer: pass", filename: str = "pricer.py"):
    return ("implementations", (filename, io.BytesIO(content), "text/x-python"))


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "llm_provider" in data


# ── Upload routes ─────────────────────────────────────────────────────────────

class TestUploadRoutes:
    def _post_start(self, files, extra_files=None, monkeypatch_settings=True):
        return client.post("/api/upload/start", files=files)

    def test_start_with_document_only(self, tmp_path, monkeypatch):
        import app.api.routes.upload as upload_mod
        up, sess = tmp_path / "uploads", tmp_path / "sessions"
        monkeypatch.setattr(type(upload_mod.settings), "uploads_dir", property(lambda s: up))
        monkeypatch.setattr(type(upload_mod.settings), "sessions_dir", property(lambda s: sess))
        up.mkdir(); sess.mkdir()

        with patch("app.api.routes.upload.run_validation", new=AsyncMock()):
            with patch("app.api.routes.upload.save_job"):
                resp = client.post(
                    "/api/upload/start",
                    files=[_make_doc_upload()],
                )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert len(data["job_id"]) > 0

    def test_start_with_document_and_code(self, tmp_path, monkeypatch):
        import app.api.routes.upload as upload_mod
        up, sess = tmp_path / "uploads", tmp_path / "sessions"
        monkeypatch.setattr(type(upload_mod.settings), "uploads_dir", property(lambda s: up))
        monkeypatch.setattr(type(upload_mod.settings), "sessions_dir", property(lambda s: sess))
        up.mkdir(); sess.mkdir()

        with patch("app.api.routes.upload.run_validation", new=AsyncMock()):
            with patch("app.api.routes.upload.save_job"):
                resp = client.post(
                    "/api/upload/start",
                    files=[_make_doc_upload(), _make_code_upload()],
                )
        assert resp.status_code == 200

    def test_invalid_document_format_returns_400(self, tmp_path, monkeypatch):
        import app.api.routes.upload as upload_mod
        up = tmp_path / "uploads"
        monkeypatch.setattr(type(upload_mod.settings), "uploads_dir", property(lambda s: up))
        up.mkdir()

        resp = client.post(
            "/api/upload/start",
            files=[("document", ("bad.xyz", io.BytesIO(b"data"), "text/plain"))],
        )
        assert resp.status_code == 400
        assert "suportado" in resp.json()["detail"].lower()

    def test_invalid_code_format_skipped_silently(self, tmp_path, monkeypatch):
        import app.api.routes.upload as upload_mod
        up, sess = tmp_path / "uploads", tmp_path / "sessions"
        monkeypatch.setattr(type(upload_mod.settings), "uploads_dir", property(lambda s: up))
        monkeypatch.setattr(type(upload_mod.settings), "sessions_dir", property(lambda s: sess))
        up.mkdir(); sess.mkdir()

        with patch("app.api.routes.upload.run_validation", new=AsyncMock()):
            with patch("app.api.routes.upload.save_job"):
                resp = client.post(
                    "/api/upload/start",
                    files=[
                        _make_doc_upload(),
                        ("implementations", ("bad.xyz", io.BytesIO(b"data"), "text/plain")),
                    ],
                )
        # Invalid implementation format is silently skipped
        assert resp.status_code == 200

    def test_get_jobs_returns_list(self):
        with patch("app.api.routes.upload.list_jobs", return_value=[
            {"job_id": "abc", "status": "done", "created_at": "2026-01-01T00:00:00", "doc_filename": "m.pdf", "product_type": "Swap"}
        ]):
            resp = client.get("/api/upload/jobs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_pdf_document_accepted(self, tmp_path, monkeypatch):
        import app.api.routes.upload as upload_mod
        up, sess = tmp_path / "uploads", tmp_path / "sessions"
        monkeypatch.setattr(type(upload_mod.settings), "uploads_dir", property(lambda s: up))
        monkeypatch.setattr(type(upload_mod.settings), "sessions_dir", property(lambda s: sess))
        up.mkdir(); sess.mkdir()

        with patch("app.api.routes.upload.run_validation", new=AsyncMock()):
            with patch("app.api.routes.upload.save_job"):
                resp = client.post(
                    "/api/upload/start",
                    files=[("document", ("model.pdf", io.BytesIO(b"%PDF fake"), "application/pdf"))],
                )
        assert resp.status_code == 200

    def test_docx_document_accepted(self, tmp_path, monkeypatch):
        import app.api.routes.upload as upload_mod
        up, sess = tmp_path / "uploads", tmp_path / "sessions"
        monkeypatch.setattr(type(upload_mod.settings), "uploads_dir", property(lambda s: up))
        monkeypatch.setattr(type(upload_mod.settings), "sessions_dir", property(lambda s: sess))
        up.mkdir(); sess.mkdir()

        with patch("app.api.routes.upload.run_validation", new=AsyncMock()):
            with patch("app.api.routes.upload.save_job"):
                resp = client.post(
                    "/api/upload/start",
                    files=[("document", ("model.docx", io.BytesIO(b"PK fake"), "application/octet-stream"))],
                )
        assert resp.status_code == 200


# ── Validation routes ─────────────────────────────────────────────────────────

class TestValidationRoutes:
    def _make_job(self, status=JobStatus.DONE, product_type="Swap"):
        return ValidationJob(
            job_id="test-abc",
            status=status,
            doc_filename="model.pdf",
        )

    def test_get_status_returns_job_info(self):
        job = self._make_job(status=JobStatus.TESTING)
        with patch("app.api.routes.validation.load_job", return_value=job):
            resp = client.get("/api/validation/test-abc/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "test-abc"
        assert data["status"] == "testing"

    def test_get_status_returns_404_for_missing_job(self):
        with patch("app.api.routes.validation.load_job", return_value=None):
            resp = client.get("/api/validation/nonexistent/status")
        assert resp.status_code == 404

    def test_get_status_includes_progress_log(self):
        job = self._make_job()
        job.log("Step 1 done")
        job.log("Step 2 done")
        with patch("app.api.routes.validation.load_job", return_value=job):
            resp = client.get("/api/validation/test-abc/status")
        data = resp.json()
        assert len(data["progress_log"]) == 2

    def test_get_status_limits_log_to_20(self):
        job = self._make_job()
        for i in range(50):
            job.log(f"Step {i}")
        with patch("app.api.routes.validation.load_job", return_value=job):
            resp = client.get("/api/validation/test-abc/status")
        assert len(resp.json()["progress_log"]) <= 20

    def test_get_results_returns_full_data(self, sample_model_understanding):
        job = self._make_job()
        job.model_understanding = sample_model_understanding
        job.test_results = [
            TestResult(test_id="T01", test_name="Q", status=TestStatus.PASSED, score=8.0, max_score=10.0)
        ]
        with patch("app.api.routes.validation.load_job", return_value=job):
            resp = client.get("/api/validation/test-abc/results")
        assert resp.status_code == 200
        data = resp.json()
        assert "model_understanding" in data
        assert "test_results" in data
        assert len(data["test_results"]) == 1

    def test_get_results_returns_404_for_missing(self):
        with patch("app.api.routes.validation.load_job", return_value=None):
            resp = client.get("/api/validation/missing-id/results")
        assert resp.status_code == 404

    def test_get_status_includes_error_field(self):
        job = self._make_job(status=JobStatus.ERROR)
        job.error = "Something went wrong"
        with patch("app.api.routes.validation.load_job", return_value=job):
            resp = client.get("/api/validation/test-abc/status")
        assert resp.json()["error"] == "Something went wrong"

    def test_get_status_includes_tests_completed(self):
        job = self._make_job()
        job.test_results = [
            TestResult(test_id="T01", test_name="Q")
        ]
        with patch("app.api.routes.validation.load_job", return_value=job):
            resp = client.get("/api/validation/test-abc/status")
        assert resp.json()["tests_completed"] == 1


# ── Report routes ─────────────────────────────────────────────────────────────

class TestReportRoutes:
    def test_get_report_returns_html(self, tmp_path):
        report_file = tmp_path / "report.html"
        report_file.write_text("<html><body>Report</body></html>", encoding="utf-8")

        job = ValidationJob(job_id="rep-id", report_path=str(report_file))
        with patch("app.api.routes.report.load_job", return_value=job):
            resp = client.get("/api/report/rep-id")
        assert resp.status_code == 200
        assert "Report" in resp.text

    def test_get_report_returns_404_for_missing_job(self):
        with patch("app.api.routes.report.load_job", return_value=None):
            resp = client.get("/api/report/nonexistent")
        assert resp.status_code == 404

    def test_get_report_returns_404_when_no_report_path(self):
        job = ValidationJob(job_id="no-rep", report_path=None)
        with patch("app.api.routes.report.load_job", return_value=job):
            resp = client.get("/api/report/no-rep")
        assert resp.status_code == 404

    def test_get_report_returns_404_when_file_missing(self, tmp_path):
        job = ValidationJob(job_id="file-gone", report_path=str(tmp_path / "nonexistent.html"))
        with patch("app.api.routes.report.load_job", return_value=job):
            resp = client.get("/api/report/file-gone")
        assert resp.status_code == 404

    def test_download_report(self, tmp_path):
        report_file = tmp_path / "report.html"
        report_file.write_text("<html>Content</html>")

        job = ValidationJob(job_id="dl-id", report_path=str(report_file))
        with patch("app.api.routes.report.load_job", return_value=job):
            resp = client.get("/api/report/dl-id/download")
        assert resp.status_code == 200

    def test_download_report_404_for_missing_job(self):
        with patch("app.api.routes.report.load_job", return_value=None):
            resp = client.get("/api/report/missing/download")
        assert resp.status_code == 404

    def test_download_report_404_when_file_missing(self, tmp_path):
        job = ValidationJob(job_id="dl-miss", report_path=str(tmp_path / "gone.html"))
        with patch("app.api.routes.report.load_job", return_value=job):
            resp = client.get("/api/report/dl-miss/download")
        assert resp.status_code == 404
