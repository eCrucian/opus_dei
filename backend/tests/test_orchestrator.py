"""Tests for the orchestrator pipeline — mocking all agents and tests."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.validation import ValidationJob, JobStatus, TestStatus, TestResult
from app.services.orchestrator import run_validation


def _make_test_result(test_id: str, status: TestStatus = TestStatus.PASSED) -> TestResult:
    return TestResult(test_id=test_id, test_name=test_id, status=status, summary="ok")


@pytest.fixture
def mock_orchestrator_deps(sample_parsed_doc, sample_parsed_code, sample_model_understanding, tmp_path):
    """Patch all external dependencies in the orchestrator."""
    replication_code = "class ModelPricer:\n    def price(self, rf): return 100.0\n"

    patches = {
        "app.services.orchestrator.create_llm_client": MagicMock(return_value=MagicMock()),
        "app.services.orchestrator.parse_document": MagicMock(return_value=sample_parsed_doc),
        "app.services.orchestrator.parse_code_files": MagicMock(return_value=sample_parsed_code),
        "app.services.orchestrator.save_job": MagicMock(),
        "app.services.orchestrator.settings.generated_code_dir": tmp_path / "gen_code",
    }
    return patches, replication_code, sample_model_understanding


class TestRunValidation:
    async def test_full_pipeline_success_without_code(
        self, sample_model_understanding, sample_parsed_doc, tmp_path, monkeypatch
    ):
        import app.services.orchestrator as orch
        monkeypatch.setattr(orch.settings, "generated_code_dir", tmp_path / "gen")
        (tmp_path / "gen").mkdir()

        job = ValidationJob(job_id="full-test")
        doc_path = tmp_path / "model.md"
        doc_path.write_text("# Model\n\ncontent")

        with patch.multiple(
            "app.services.orchestrator",
            create_llm_client=MagicMock(return_value=MagicMock()),
            parse_document=MagicMock(return_value=sample_parsed_doc),
            parse_code_files=MagicMock(return_value=None),
            save_job=MagicMock(),
        ):
            with patch("app.services.orchestrator.DocumentAnalyzerAgent") as MockDA:
                MockDA.return_value.analyze = AsyncMock(return_value=sample_model_understanding)

                with patch("app.services.orchestrator.DocQualityTest") as MockT01:
                    MockT01.return_value.run = AsyncMock(return_value=_make_test_result("T01"))

                    with patch("app.services.orchestrator.MethodologyTest") as MockT02:
                        MockT02.return_value.run = AsyncMock(return_value=_make_test_result("T02"))

                        with patch("app.services.orchestrator.ModelReplicatorAgent") as MockRep:
                            MockRep.return_value.replicate = AsyncMock(return_value="class ModelPricer: pass")

                            with patch("app.services.orchestrator.QuantitativeTest") as MockT03:
                                MockT03.return_value.run = AsyncMock(return_value=_make_test_result("T03"))

                                with patch("app.services.orchestrator.StabilityTest") as MockT05:
                                    MockT05.return_value.run = AsyncMock(return_value=_make_test_result("T05"))

                                    with patch("app.services.orchestrator.PerformanceTest") as MockT06:
                                        MockT06.return_value.run = AsyncMock(return_value=_make_test_result("T06"))

                                        with patch("app.services.orchestrator.MonteCarloTest") as MockT07:
                                            MockT07.return_value.run = AsyncMock(return_value=_make_test_result("T07", TestStatus.SKIPPED))

                                            with patch("app.services.orchestrator.ReplicationTest") as MockT08:
                                                MockT08.return_value.run = AsyncMock(return_value=_make_test_result("T08"))

                                                with patch("app.services.orchestrator.ReportGenerator") as MockRG:
                                                    report_path = tmp_path / "report.html"
                                                    report_path.write_text("<html/>")
                                                    MockRG.return_value.generate = AsyncMock(return_value=report_path)

                                                    await run_validation(job, doc_path, [])

        assert job.status == JobStatus.DONE
        assert job.report_path is not None
        assert len(job.test_results) >= 6

    async def test_pipeline_runs_t08_when_code_provided(
        self, sample_model_understanding, sample_parsed_doc, sample_parsed_code, tmp_path, monkeypatch
    ):
        import app.services.orchestrator as orch
        monkeypatch.setattr(orch.settings, "generated_code_dir", tmp_path / "gen")
        (tmp_path / "gen").mkdir()

        job = ValidationJob(job_id="t08-test")
        doc_path = tmp_path / "model.md"
        doc_path.write_text("# Model")
        code_path = tmp_path / "pricer.py"
        code_path.write_text("class ModelPricer: pass")

        with patch.multiple(
            "app.services.orchestrator",
            create_llm_client=MagicMock(return_value=MagicMock()),
            parse_document=MagicMock(return_value=sample_parsed_doc),
            parse_code_files=MagicMock(return_value=sample_parsed_code),
            save_job=MagicMock(),
        ):
            with patch("app.services.orchestrator.DocumentAnalyzerAgent") as MockDA:
                MockDA.return_value.analyze = AsyncMock(return_value=sample_model_understanding)
                with patch("app.services.orchestrator.DocQualityTest") as MT01:
                    MT01.return_value.run = AsyncMock(return_value=_make_test_result("T01"))
                    with patch("app.services.orchestrator.MethodologyTest") as MT02:
                        MT02.return_value.run = AsyncMock(return_value=_make_test_result("T02"))
                        with patch("app.services.orchestrator.ModelReplicatorAgent") as MR:
                            MR.return_value.replicate = AsyncMock(return_value="class ModelPricer: pass")
                            with patch("app.services.orchestrator.QuantitativeTest") as MT03:
                                MT03.return_value.run = AsyncMock(return_value=_make_test_result("T03"))
                                with patch("app.services.orchestrator.StabilityTest") as MT05:
                                    MT05.return_value.run = AsyncMock(return_value=_make_test_result("T05"))
                                    with patch("app.services.orchestrator.PerformanceTest") as MT06:
                                        MT06.return_value.run = AsyncMock(return_value=_make_test_result("T06"))
                                        with patch("app.services.orchestrator.MonteCarloTest") as MT07:
                                            MT07.return_value.run = AsyncMock(return_value=_make_test_result("T07"))
                                            with patch("app.services.orchestrator.ReplicationTest") as MT08:
                                                MT08.return_value.run = AsyncMock(return_value=_make_test_result("T08"))
                                                with patch("app.services.orchestrator.ReportGenerator") as MRG:
                                                    rp = tmp_path / "r.html"
                                                    rp.write_text("<html/>")
                                                    MRG.return_value.generate = AsyncMock(return_value=rp)
                                                    await run_validation(job, doc_path, [code_path])

        assert job.status == JobStatus.DONE
        # T08 should have been called since code was provided
        MT08.return_value.run.assert_called_once()

    async def test_error_handling_sets_status_to_error(self, sample_parsed_doc, tmp_path):
        import app.services.orchestrator as orch

        job = ValidationJob(job_id="error-test")
        doc_path = tmp_path / "model.md"
        doc_path.write_text("# Model")

        with patch.multiple(
            "app.services.orchestrator",
            create_llm_client=MagicMock(return_value=MagicMock()),
            parse_document=MagicMock(side_effect=RuntimeError("parse failed")),
            save_job=MagicMock(),
        ):
            with pytest.raises(RuntimeError, match="parse failed"):
                await run_validation(job, doc_path, [])

        assert job.status == JobStatus.ERROR
        assert "parse failed" in job.error

    async def test_error_log_appended(self, tmp_path):
        import app.services.orchestrator as orch

        job = ValidationJob(job_id="err-log")
        doc_path = tmp_path / "m.md"
        doc_path.write_text("x")

        with patch.multiple(
            "app.services.orchestrator",
            create_llm_client=MagicMock(return_value=MagicMock()),
            parse_document=MagicMock(side_effect=ValueError("boom")),
            save_job=MagicMock(),
        ):
            with pytest.raises(ValueError):
                await run_validation(job, doc_path, [])

        assert any("ERRO" in log for log in job.progress_log)

    async def test_replication_code_saved_to_disk(
        self, sample_model_understanding, sample_parsed_doc, tmp_path, monkeypatch
    ):
        import app.services.orchestrator as orch
        gen_dir = tmp_path / "gen"
        gen_dir.mkdir()
        monkeypatch.setattr(orch.settings, "generated_code_dir", gen_dir)

        job = ValidationJob(job_id="save-code")
        doc_path = tmp_path / "model.md"
        doc_path.write_text("# Model")
        replication_code = "class ModelPricer:\n    def price(self, rf): return 999.0\n"

        with patch.multiple(
            "app.services.orchestrator",
            create_llm_client=MagicMock(return_value=MagicMock()),
            parse_document=MagicMock(return_value=sample_parsed_doc),
            parse_code_files=MagicMock(return_value=None),
            save_job=MagicMock(),
        ):
            with patch("app.services.orchestrator.DocumentAnalyzerAgent") as MockDA:
                MockDA.return_value.analyze = AsyncMock(return_value=sample_model_understanding)
                with patch("app.services.orchestrator.DocQualityTest") as MT01:
                    MT01.return_value.run = AsyncMock(return_value=_make_test_result("T01"))
                    with patch("app.services.orchestrator.MethodologyTest") as MT02:
                        MT02.return_value.run = AsyncMock(return_value=_make_test_result("T02"))
                        with patch("app.services.orchestrator.ModelReplicatorAgent") as MR:
                            MR.return_value.replicate = AsyncMock(return_value=replication_code)
                            with patch("app.services.orchestrator.QuantitativeTest") as MT03:
                                MT03.return_value.run = AsyncMock(return_value=_make_test_result("T03"))
                                with patch("app.services.orchestrator.StabilityTest") as MT05:
                                    MT05.return_value.run = AsyncMock(return_value=_make_test_result("T05"))
                                    with patch("app.services.orchestrator.PerformanceTest") as MT06:
                                        MT06.return_value.run = AsyncMock(return_value=_make_test_result("T06"))
                                        with patch("app.services.orchestrator.MonteCarloTest") as MT07:
                                            MT07.return_value.run = AsyncMock(return_value=_make_test_result("T07"))
                                            with patch("app.services.orchestrator.ReportGenerator") as MRG:
                                                rp = tmp_path / "r.html"
                                                rp.write_text("<html/>")
                                                MRG.return_value.generate = AsyncMock(return_value=rp)
                                                await run_validation(job, doc_path, [])

        saved = gen_dir / "save-code" / "model_replication.py"
        assert saved.exists()
        assert "ModelPricer" in saved.read_text()
