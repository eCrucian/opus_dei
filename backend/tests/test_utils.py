"""Tests for storage and code_executor utilities."""
import json
import subprocess
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.models.validation import ValidationJob, JobStatus, TestResult, TestStatus
from app.utils.storage import save_job, load_job, list_jobs, _job_path
from app.utils.code_executor import safe_exec


# ── Storage ───────────────────────────────────────────────────────────────────

class TestStorage:
    def _patch_sessions(self, monkeypatch, sessions_dir: Path):
        import app.utils.storage as stor
        monkeypatch.setattr(type(stor.settings), "sessions_dir", property(lambda s: sessions_dir))

    def test_job_path_returns_json_file(self, tmp_path, monkeypatch):
        self._patch_sessions(monkeypatch, tmp_path)
        path = _job_path("abc-123")
        assert str(path).endswith("abc-123.json")

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        self._patch_sessions(monkeypatch, tmp_path)
        job = ValidationJob(job_id="roundtrip-id", doc_filename="model.pdf")
        save_job(job)
        loaded = load_job("roundtrip-id")
        assert loaded is not None
        assert loaded.job_id == "roundtrip-id"
        assert loaded.doc_filename == "model.pdf"

    def test_save_preserves_status(self, tmp_path, monkeypatch):
        self._patch_sessions(monkeypatch, tmp_path)
        job = ValidationJob(job_id="status-id", status=JobStatus.DONE)
        save_job(job)
        loaded = load_job("status-id")
        assert loaded.status == JobStatus.DONE

    def test_save_preserves_test_results(self, tmp_path, monkeypatch):
        self._patch_sessions(monkeypatch, tmp_path)
        job = ValidationJob(job_id="results-id")
        job.test_results.append(
            TestResult(test_id="T01", test_name="Q", status=TestStatus.PASSED, score=8.0, max_score=10.0)
        )
        save_job(job)
        loaded = load_job("results-id")
        assert len(loaded.test_results) == 1
        assert loaded.test_results[0].score == pytest.approx(8.0)

    def test_load_job_returns_none_for_missing(self, tmp_path, monkeypatch):
        self._patch_sessions(monkeypatch, tmp_path)
        result = load_job("nonexistent-id")
        assert result is None

    def test_list_jobs_returns_sorted_list(self, tmp_path, monkeypatch):
        self._patch_sessions(monkeypatch, tmp_path)
        for i in range(3):
            job = ValidationJob(job_id=f"job-{i}", doc_filename=f"doc{i}.pdf")
            save_job(job)
        jobs = list_jobs()
        assert len(jobs) == 3
        assert all("job_id" in j for j in jobs)
        assert all("status" in j for j in jobs)

    def test_list_jobs_skips_invalid_json(self, tmp_path, monkeypatch):
        self._patch_sessions(monkeypatch, tmp_path)
        bad_file = tmp_path / "corrupt.json"
        bad_file.write_text("not valid json")
        job = ValidationJob(job_id="valid-job")
        save_job(job)
        jobs = list_jobs()
        assert len(jobs) == 1  # corrupt file skipped

    def test_list_jobs_includes_product_type(self, tmp_path, monkeypatch, sample_model_understanding):
        self._patch_sessions(monkeypatch, tmp_path)
        job = ValidationJob(job_id="mu-job", model_understanding=sample_model_understanding)
        save_job(job)
        jobs = list_jobs()
        assert jobs[0]["product_type"] == "Swap de Taxa de Juros"

    def test_save_job_creates_file(self, tmp_path, monkeypatch):
        self._patch_sessions(monkeypatch, tmp_path)
        job = ValidationJob(job_id="file-check")
        save_job(job)
        assert (tmp_path / "file-check.json").exists()

    def test_load_job_parses_model_understanding(self, tmp_path, monkeypatch, sample_model_understanding):
        self._patch_sessions(monkeypatch, tmp_path)
        job = ValidationJob(job_id="mu-test", model_understanding=sample_model_understanding)
        save_job(job)
        loaded = load_job("mu-test")
        assert loaded.model_understanding is not None
        assert loaded.model_understanding.product_type == "Swap de Taxa de Juros"


# ── Code Executor ─────────────────────────────────────────────────────────────

class TestSafeExec:
    def test_simple_integer_result(self):
        code = "_result = 42"
        result = safe_exec(code, "_result")
        assert result == 42

    def test_dict_result(self):
        code = "_result = {'key': 'value', 'num': 99}"
        result = safe_exec(code, "_result")
        assert result == {"key": "value", "num": 99}

    def test_list_result(self):
        code = "_result = [1, 2, 3]"
        result = safe_exec(code, "_result")
        assert result == [1, 2, 3]

    def test_numpy_int_serialization(self):
        code = "import numpy as np\n_result = {'val': np.int64(7)}"
        result = safe_exec(code, "_result")
        assert result == {"val": 7}
        assert isinstance(result["val"], int)

    def test_numpy_float_serialization(self):
        code = "import numpy as np\n_result = {'val': np.float64(3.14)}"
        result = safe_exec(code, "_result")
        assert result is not None
        assert abs(result["val"] - 3.14) < 1e-6

    def test_numpy_array_serialization(self):
        code = "import numpy as np\n_result = {'arr': np.array([1, 2, 3])}"
        result = safe_exec(code, "_result")
        assert result == {"arr": [1, 2, 3]}

    def test_returns_none_on_runtime_error(self):
        code = "raise ValueError('boom')\n_result = 1"
        result = safe_exec(code, "_result")
        assert result is None

    def test_returns_none_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="python", timeout=1)):
            result = safe_exec("_result = 1", "_result", timeout=1)
        assert result is None

    def test_returns_none_on_subprocess_exception(self):
        with patch("subprocess.run", side_effect=OSError("no python")):
            result = safe_exec("_result = 1", "_result")
        assert result is None

    def test_missing_result_var_returns_none(self):
        code = "x = 42"  # _result is never set
        result = safe_exec(code, "_result")
        assert result is None

    def test_cleans_up_temp_file(self):
        import tempfile
        created_files = []
        original_ntf = tempfile.NamedTemporaryFile

        def tracking_ntf(*args, **kwargs):
            f = original_ntf(*args, **kwargs)
            created_files.append(f.name)
            return f

        with patch("tempfile.NamedTemporaryFile", side_effect=tracking_ntf):
            safe_exec("_result = 1", "_result")

        for path in created_files:
            assert not Path(path).exists()

    def test_boolean_result(self):
        code = "_result = True"
        result = safe_exec(code, "_result")
        assert result is True

    def test_nested_dict(self):
        code = "_result = {'a': {'b': [1, 2]}}"
        result = safe_exec(code, "_result")
        assert result == {"a": {"b": [1, 2]}}

    def test_cleanup_handles_oserror(self):
        with patch("os.unlink", side_effect=OSError("permission denied")):
            result = safe_exec("_result = 42", "_result")
        assert result == 42
