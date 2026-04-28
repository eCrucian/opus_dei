"""Tests for MonteCarloTest — convergence and vol window sensitivity."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.validation import TestStatus, RiskFactor
from app.services.tests.monte_carlo import MonteCarloTest, _plot_convergence, _plot_vol_sensitivity


def _make_llm():
    return MagicMock(complete=AsyncMock())


MC_OUTPUT_CONVERGED = {
    "path_counts": [100, 500, 1000, 2000, 5000, 10000],
    "prices": [980.0, 978.5, 979.2, 979.0, 978.8, 978.9],
    "converged": True,
    "n_for_convergence": 10000,
}

MC_OUTPUT_NOT_CONVERGED = {
    "path_counts": [100, 500, 1000, 2000, 5000, 10000],
    "prices": [950.0, 990.0, 960.0, 1020.0, 970.0, 1005.0],
    "converged": False,
    "n_for_convergence": None,
}


class TestMonteCarloTest:
    async def test_skipped_when_not_mc_model(
        self, sample_model_understanding, minimal_pricer_code
    ):
        sample_model_understanding.has_monte_carlo = False
        test = MonteCarloTest(_make_llm())
        result = await test.run(sample_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.SKIPPED
        assert "Monte Carlo" in result.summary

    async def test_warning_when_safe_exec_returns_none(
        self, mc_model_understanding, minimal_pricer_code
    ):
        with patch("app.services.tests.monte_carlo.safe_exec", return_value=None):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.WARNING

    async def test_passed_when_converged(self, mc_model_understanding, minimal_pricer_code):
        with patch("app.services.tests.monte_carlo.safe_exec", return_value=MC_OUTPUT_CONVERGED):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.PASSED

    async def test_warning_when_not_converged(self, mc_model_understanding, minimal_pricer_code):
        with patch("app.services.tests.monte_carlo.safe_exec", return_value=MC_OUTPUT_NOT_CONVERGED):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)
        assert result.status == TestStatus.WARNING

    async def test_recommendation_when_not_converged(self, mc_model_understanding, minimal_pricer_code):
        with patch("app.services.tests.monte_carlo.safe_exec", return_value=MC_OUTPUT_NOT_CONVERGED):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)
        assert len(result.recommendations) > 0

    async def test_no_recommendation_when_converged(self, mc_model_understanding, minimal_pricer_code):
        with patch("app.services.tests.monte_carlo.safe_exec", return_value=MC_OUTPUT_CONVERGED):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)
        assert len(result.recommendations) == 0

    async def test_vol_window_test_run_when_vol_factor_present(
        self, mc_model_understanding, minimal_pricer_code
    ):
        vol_sensitivity = {
            "vol_sensitivity": [
                {"window_days": 21, "vol": 0.15, "price": 55.0},
                {"window_days": 252, "vol": 0.25, "price": 70.0},
            ]
        }

        exec_returns = [MC_OUTPUT_CONVERGED, vol_sensitivity]
        call_count = 0

        def mock_exec(code, var, **kwargs):
            nonlocal call_count
            r = exec_returns[call_count % 2]
            call_count += 1
            return r

        with patch("app.services.tests.monte_carlo.safe_exec", side_effect=mock_exec):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)

        assert "vol_window_sensitivity" in result.details or result.status in (TestStatus.PASSED, TestStatus.WARNING)

    async def test_rf_base_populated_for_different_types(
        self, mc_model_understanding, minimal_pricer_code
    ):
        # Add spot factor to MC model
        mc_model_understanding.risk_factors.append(
            RiskFactor(name="usd_brl", type="spot", description="FX")
        )
        with patch("app.services.tests.monte_carlo.safe_exec", return_value=MC_OUTPUT_CONVERGED):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)
        # Should run without error
        assert result.status in (TestStatus.PASSED, TestStatus.WARNING)

    async def test_convergence_detail_stored(self, mc_model_understanding, minimal_pricer_code):
        with patch("app.services.tests.monte_carlo.safe_exec", return_value=MC_OUTPUT_CONVERGED):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)
        assert "convergence" in result.details

    async def test_summary_contains_convergence_info(
        self, mc_model_understanding, minimal_pricer_code
    ):
        with patch("app.services.tests.monte_carlo.safe_exec", return_value=MC_OUTPUT_CONVERGED):
            test = MonteCarloTest(_make_llm())
            result = await test.run(mc_model_understanding, minimal_pricer_code)
        assert "SIM" in result.summary or "convergência" in result.summary.lower()


class TestPlotConvergence:
    def test_returns_none_when_no_valid_prices(self):
        output = {"path_counts": [100, 500], "prices": [None, None]}
        result = _plot_convergence(output)
        assert result is None

    def test_returns_base64_with_valid_data(self):
        output = {
            "path_counts": [100, 500, 1000, 5000],
            "prices": [980.0, 978.5, 979.0, 979.1],
        }
        result = _plot_convergence(output)
        assert result is not None
        assert isinstance(result, str)

    def test_handles_mixed_none_prices(self):
        output = {
            "path_counts": [100, 500, 1000],
            "prices": [None, 978.5, 979.0],
        }
        result = _plot_convergence(output)
        assert result is not None


class TestPlotVolSensitivity:
    def test_returns_none_for_empty_list(self):
        result = _plot_vol_sensitivity([])
        assert result is None

    def test_returns_none_when_no_price_key(self):
        result = _plot_vol_sensitivity([{"window_days": 21, "error": "timeout"}])
        assert result is None

    def test_returns_base64_with_valid_data(self):
        data = [
            {"window_days": 21, "vol": 0.15, "price": 55.0},
            {"window_days": 63, "vol": 0.20, "price": 62.0},
            {"window_days": 252, "vol": 0.25, "price": 70.0},
        ]
        result = _plot_vol_sensitivity(data)
        assert result is not None
        assert isinstance(result, str)
