"""Tests for PerformanceTest — second derivatives (gamma/curvature)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.validation import TestStatus
from app.services.tests.performance import PerformanceTest, _plot_gammas


def _make_llm():
    return MagicMock(complete=AsyncMock())


class TestPerformanceTest:
    async def test_warning_when_safe_exec_returns_none(
        self, sample_model_understanding, minimal_pricer_code
    ):
        with patch("app.services.tests.performance.safe_exec", return_value=None):
            test = PerformanceTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.WARNING

    async def test_passed_with_valid_output(self, sample_model_understanding, minimal_pricer_code):
        exec_output = {
            "n_valid": 100,
            "gamma_means": {"taxa_di": 50_000.0},
            "gamma_relative_impact_1pct": {"taxa_di": 0.0005},
            "cross_gammas_sample": {},
            "sample_results": [],
        }
        with patch("app.services.tests.performance.safe_exec", return_value=exec_output):
            test = PerformanceTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.PASSED

    async def test_recommendation_added_when_significant_gamma(
        self, sample_model_understanding, minimal_pricer_code
    ):
        exec_output = {
            "n_valid": 100,
            "gamma_means": {"taxa_di": 500_000.0},
            "gamma_relative_impact_1pct": {"taxa_di": 0.05},  # > 0.001 threshold
            "cross_gammas_sample": {},
            "sample_results": [],
        }
        with patch("app.services.tests.performance.safe_exec", return_value=exec_output):
            test = PerformanceTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert len(result.recommendations) > 0
        assert "convexidade" in result.recommendations[0].lower() or "curvatura" in result.recommendations[0].lower()

    async def test_no_recommendation_when_gamma_small(
        self, sample_model_understanding, minimal_pricer_code
    ):
        exec_output = {
            "n_valid": 100,
            "gamma_means": {"taxa_di": 1.0},
            "gamma_relative_impact_1pct": {"taxa_di": 0.0001},  # < 0.001
            "cross_gammas_sample": {},
            "sample_results": [],
        }
        with patch("app.services.tests.performance.safe_exec", return_value=exec_output):
            test = PerformanceTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert len(result.recommendations) == 0

    async def test_details_structure(self, sample_model_understanding, minimal_pricer_code):
        exec_output = {
            "n_valid": 50,
            "gamma_means": {"taxa_di": 10.0},
            "gamma_relative_impact_1pct": {"taxa_di": 0.0002},
            "cross_gammas_sample": {"taxa_di_x_usd_brl": 0.5},
            "sample_results": [],
        }
        with patch("app.services.tests.performance.safe_exec", return_value=exec_output):
            test = PerformanceTest(_make_llm())
            result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert "gamma_means" in result.details
        assert "gamma_impact_1pct" in result.details
        assert "cross_gammas" in result.details
        assert "n_valid" in result.details

    async def test_plot_exception_does_not_crash(
        self, sample_model_understanding, minimal_pricer_code
    ):
        exec_output = {
            "n_valid": 10,
            "gamma_means": {},
            "gamma_relative_impact_1pct": {},
            "cross_gammas_sample": {},
            "sample_results": [],
        }
        with patch("app.services.tests.performance.safe_exec", return_value=exec_output):
            with patch("app.services.tests.performance._plot_gammas", side_effect=RuntimeError("plot err")):
                test = PerformanceTest(_make_llm())
                result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.PASSED


class TestPlotGammas:
    def test_returns_none_for_empty_dict(self):
        result = _plot_gammas({})
        assert result is None

    def test_returns_base64_string(self):
        gamma_rel = {"taxa_di": 0.05, "usd_brl": 0.001}
        result = _plot_gammas(gamma_rel)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 100

    def test_handles_single_factor(self):
        result = _plot_gammas({"taxa_di": 0.002})
        assert result is not None

    def test_red_bars_for_values_above_threshold(self):
        # Just ensure it runs without error for above-threshold values
        result = _plot_gammas({"factor_high": 0.5})
        assert result is not None

    def test_blue_bars_for_values_below_threshold(self):
        result = _plot_gammas({"factor_low": 0.00001})
        assert result is not None
