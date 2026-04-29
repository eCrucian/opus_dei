"""Tests for QuantitativeTest — AI-generated test execution."""
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.validation import TestStatus
from app.services.llm.base import LLMResponse
from app.services.tests.quantitative import QuantitativeTest


class TestQuantitativeTest:
    async def test_skipped_when_no_tests_proposed(
        self, sample_model_understanding, minimal_pricer_code, tmp_path, monkeypatch
    ):
        import app.services.tests.quantitative as qt_mod
        monkeypatch.setattr(type(qt_mod.settings), "generated_code_dir", property(lambda s: tmp_path))

        llm = MagicMock()
        llm.complete = AsyncMock(
            return_value=LLMResponse(content='{"tests": []}', model="test")
        )
        test = QuantitativeTest(llm)
        result = await test.run(
            sample_model_understanding, {}, minimal_pricer_code, "job-001"
        )
        assert result.status == TestStatus.SKIPPED

    async def test_passed_when_all_tests_pass(
        self, sample_model_understanding, minimal_pricer_code, tmp_path, monkeypatch
    ):
        import app.services.tests.quantitative as qt_mod
        monkeypatch.setattr(type(qt_mod.settings), "generated_code_dir", property(lambda s: tmp_path))

        proposed = [{"test_id": "qt_001", "name": "Bound", "description": "desc",
                     "risk_factors_involved": ["taxa_di"]}]
        test_code = "def run_test_qt_001(pricer_class):\n    return {'passed': True, 'details': 'ok', 'metrics': {}, 'figures_base64': []}\n"

        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=[
            LLMResponse(content=json.dumps({"tests": proposed}), model="test"),  # propose
            LLMResponse(content=test_code, model="test"),  # generate
        ])

        with patch("app.services.tests.quantitative.safe_exec", return_value={"passed": True, "details": "ok", "metrics": {}, "figures_base64": []}):
            test = QuantitativeTest(llm)
            result = await test.run(sample_model_understanding, {"testes_sugeridos": []}, minimal_pricer_code, "job-002")

        assert result.status == TestStatus.PASSED
        assert result.score == pytest.approx(10.0)

    async def test_warning_when_some_tests_fail(
        self, sample_model_understanding, minimal_pricer_code, tmp_path, monkeypatch
    ):
        import app.services.tests.quantitative as qt_mod
        monkeypatch.setattr(type(qt_mod.settings), "generated_code_dir", property(lambda s: tmp_path))

        proposed = [
            {"test_id": "qt_001", "name": "T1", "description": "d1", "risk_factors_involved": []},
            {"test_id": "qt_002", "name": "T2", "description": "d2", "risk_factors_involved": []},
        ]
        exec_results = [
            {"passed": True, "details": "ok", "metrics": {}, "figures_base64": []},
            {"passed": False, "details": "fail", "metrics": {}, "figures_base64": []},
        ]

        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=[
            LLMResponse(content=json.dumps({"tests": proposed}), model="test"),
            LLMResponse(content="def run_test_qt_001(p): pass", model="test"),
            LLMResponse(content="def run_test_qt_002(p): pass", model="test"),
        ])

        exec_call_count = 0
        def mock_exec(code, var, **kwargs):
            nonlocal exec_call_count
            r = exec_results[exec_call_count % 2]
            exec_call_count += 1
            return r

        with patch("app.services.tests.quantitative.safe_exec", side_effect=mock_exec):
            test = QuantitativeTest(llm)
            result = await test.run(sample_model_understanding, {}, minimal_pricer_code, "job-003")

        assert result.status == TestStatus.WARNING

    async def test_failed_when_all_tests_fail(
        self, sample_model_understanding, minimal_pricer_code, tmp_path, monkeypatch
    ):
        import app.services.tests.quantitative as qt_mod
        monkeypatch.setattr(type(qt_mod.settings), "generated_code_dir", property(lambda s: tmp_path))

        proposed = [{"test_id": "qt_001", "name": "T1", "description": "d", "risk_factors_involved": []}]

        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=[
            LLMResponse(content=json.dumps({"tests": proposed}), model="test"),
            LLMResponse(content="def run_test_qt_001(p): pass", model="test"),
        ])

        with patch("app.services.tests.quantitative.safe_exec", return_value={"passed": False, "details": "err", "metrics": {}, "figures_base64": []}):
            test = QuantitativeTest(llm)
            result = await test.run(sample_model_understanding, {}, minimal_pricer_code, "job-004")

        assert result.status == TestStatus.FAILED

    async def test_exec_returns_none_is_handled(
        self, sample_model_understanding, minimal_pricer_code, tmp_path, monkeypatch
    ):
        import app.services.tests.quantitative as qt_mod
        monkeypatch.setattr(type(qt_mod.settings), "generated_code_dir", property(lambda s: tmp_path))

        proposed = [{"test_id": "qt_001", "name": "T1", "description": "d", "risk_factors_involved": []}]
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=[
            LLMResponse(content=json.dumps({"tests": proposed}), model="test"),
            LLMResponse(content="def run_test_qt_001(p): pass", model="test"),
        ])

        with patch("app.services.tests.quantitative.safe_exec", return_value=None):
            test = QuantitativeTest(llm)
            result = await test.run(sample_model_understanding, {}, minimal_pricer_code, "job-005")

        # passed=None, neither True → score/status computed correctly
        assert result.score is not None or result.status == TestStatus.FAILED

    async def test_generated_code_saved_to_disk(
        self, sample_model_understanding, minimal_pricer_code, tmp_path, monkeypatch
    ):
        import app.services.tests.quantitative as qt_mod
        monkeypatch.setattr(type(qt_mod.settings), "generated_code_dir", property(lambda s: tmp_path))

        proposed = [{"test_id": "qt_save", "name": "Save Test", "description": "d", "risk_factors_involved": []}]
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=[
            LLMResponse(content=json.dumps({"tests": proposed}), model="test"),
            LLMResponse(content="def run_test_qt_save(p): return {'passed': True, 'details': '', 'metrics': {}, 'figures_base64': []}", model="test"),
        ])

        with patch("app.services.tests.quantitative.safe_exec", return_value={"passed": True, "details": "", "metrics": {}, "figures_base64": []}):
            test = QuantitativeTest(llm)
            await test.run(sample_model_understanding, {}, minimal_pricer_code, "job-save")

        code_files = list((tmp_path / "job-save").glob("*.py"))
        assert len(code_files) == 1

    async def test_figures_appended_to_result(
        self, sample_model_understanding, minimal_pricer_code, tmp_path, monkeypatch
    ):
        import app.services.tests.quantitative as qt_mod
        monkeypatch.setattr(type(qt_mod.settings), "generated_code_dir", property(lambda s: tmp_path))

        proposed = [{"test_id": "qt_fig", "name": "Fig", "description": "d", "risk_factors_involved": []}]
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=[
            LLMResponse(content=json.dumps({"tests": proposed}), model="test"),
            LLMResponse(content="def run_test_qt_fig(p): pass", model="test"),
        ])

        fake_fig = "base64encodedpng"
        with patch("app.services.tests.quantitative.safe_exec",
                   return_value={"passed": True, "details": "", "metrics": {}, "figures_base64": [fake_fig]}):
            test = QuantitativeTest(llm)
            result = await test.run(sample_model_understanding, {}, minimal_pricer_code, "job-fig")

        assert fake_fig in result.figures
