"""Tests for StabilityTest — first derivatives (delta) checks."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.validation import TestStatus
from app.services.tests.stability import StabilityTest


def _make_llm():
    llm = MagicMock()
    llm.complete = AsyncMock()
    return llm


class TestStabilityTest:
    async def test_warning_when_safe_exec_returns_none(
        self, sample_model_understanding, minimal_pricer_code
    ):
        with patch("app.services.tests.stability.safe_exec", return_value=None):
            test = StabilityTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.WARNING

    async def test_passed_when_all_deltas_finite_and_nonzero(
        self, sample_model_understanding, minimal_pricer_code
    ):
        exec_output = {
            "n_points": 200,
            "all_deltas_finite": True,
            "any_delta_nonzero": True,
            "sample_results": [],
            "passed": True,
        }
        with patch("app.services.tests.stability.safe_exec", return_value=exec_output):
            test = StabilityTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.PASSED

    async def test_failed_when_delta_is_infinite(
        self, sample_model_understanding, minimal_pricer_code
    ):
        exec_output = {
            "n_points": 200,
            "all_deltas_finite": False,
            "any_delta_nonzero": True,
            "sample_results": [],
            "passed": False,
        }
        with patch("app.services.tests.stability.safe_exec", return_value=exec_output):
            test = StabilityTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.FAILED
        assert any("infinito" in imp.lower() or "nan" in imp.lower() for imp in result.impediments)

    async def test_failed_when_all_deltas_zero(
        self, sample_model_understanding, minimal_pricer_code
    ):
        exec_output = {
            "n_points": 200,
            "all_deltas_finite": True,
            "any_delta_nonzero": False,
            "sample_results": [],
            "passed": False,
        }
        with patch("app.services.tests.stability.safe_exec", return_value=exec_output):
            test = StabilityTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.FAILED
        assert any("zero" in imp.lower() for imp in result.impediments)

    async def test_details_structure(self, sample_model_understanding, minimal_pricer_code):
        exec_output = {
            "n_points": 100,
            "all_deltas_finite": True,
            "any_delta_nonzero": True,
            "sample_results": [{"pv": 950000, "deltas": {"taxa_di": -850000}}],
            "passed": True,
        }
        with patch("app.services.tests.stability.safe_exec", return_value=exec_output):
            test = StabilityTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert "n_points_simulated" in result.details
        assert "all_deltas_finite" in result.details

    async def test_summary_contains_n_points(self, sample_model_understanding, minimal_pricer_code):
        exec_output = {
            "n_points": 200,
            "all_deltas_finite": True,
            "any_delta_nonzero": True,
            "sample_results": [],
            "passed": True,
        }
        with patch("app.services.tests.stability.safe_exec", return_value=exec_output):
            test = StabilityTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert "200" in result.summary

    async def test_plot_stability_returns_none_on_no_valid_samples(self, sample_model_understanding):
        test = StabilityTest(_make_llm())
        fig = await test._plot_stability({"sample_results": []}, ["taxa_di"])
        assert fig is None

    async def test_plot_stability_returns_none_on_no_rf_names(self, sample_model_understanding):
        test = StabilityTest(_make_llm())
        fig = await test._plot_stability(
            {"sample_results": [{"deltas": {"taxa_di": -800}, "pv": 1e6}]},
            []
        )
        assert fig is None

    async def test_plot_stability_returns_base64_with_valid_data(self, sample_model_understanding):
        test = StabilityTest(_make_llm())
        samples = [{"deltas": {"taxa_di": -850000.0 + i * 1000}, "pv": 950000.0} for i in range(5)]
        fig = await test._plot_stability({"sample_results": samples}, ["taxa_di"])
        assert fig is not None
        assert isinstance(fig, str)
        assert len(fig) > 100  # base64 should be substantial

    async def test_plot_exception_does_not_crash_test(self, sample_model_understanding, minimal_pricer_code):
        exec_output = {
            "n_points": 5,
            "all_deltas_finite": True,
            "any_delta_nonzero": True,
            "sample_results": [],
            "passed": True,
        }
        with patch("app.services.tests.stability.safe_exec", return_value=exec_output):
            with patch.object(StabilityTest, "_plot_stability", side_effect=RuntimeError("plot error")):
                test = StabilityTest(_make_llm())
                result = await test.run(sample_model_understanding, minimal_pricer_code)
        # should still pass despite plot error (caught by try/except)
        assert result.status == TestStatus.PASSED

    async def test_test_id_and_name(self, sample_model_understanding, minimal_pricer_code):
        with patch("app.services.tests.stability.safe_exec", return_value=None):
            test = StabilityTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.test_id == "T05_stability"
        assert "Estabilidade" in result.test_name
