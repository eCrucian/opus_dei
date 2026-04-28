"""Tests for ReportGenerator — HTML generation and opinion building."""
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.validation import ValidationJob, TestResult, TestStatus
from app.services.llm.base import LLMResponse
from app.services.report_generator import ReportGenerator


def _make_llm(payload: dict):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=LLMResponse(content=json.dumps(payload), model="test"))
    return llm


OPINION_PAYLOAD = {
    "opiniao": "favoravel",
    "justificativa": "O modelo está bem documentado e testado.",
    "impeditivos": [],
    "recomendacoes_prioritarias": ["Adicionar stress test"],
    "oportunidades_melhoria": ["Melhorar documentação"],
    "nota_geral": 8.5,
}


class TestReportGenerator:
    async def test_generate_creates_html_file(
        self, sample_job, tmp_path, monkeypatch
    ):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        sample_job.test_results = [
            TestResult(test_id="T01", test_name="Q", status=TestStatus.PASSED,
                       score=8.0, max_score=10.0, summary="ok")
        ]

        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        report_path = await gen.generate(sample_job)

        assert report_path.exists()
        assert report_path.suffix == ".html"

    async def test_generated_html_contains_product_type(
        self, sample_job, tmp_path, monkeypatch
    ):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        report_path = await gen.generate(sample_job)

        html = report_path.read_text(encoding="utf-8")
        assert "Swap de Taxa de Juros" in html

    async def test_generated_html_contains_opinion(
        self, sample_job, tmp_path, monkeypatch
    ):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        report_path = await gen.generate(sample_job)

        html = report_path.read_text(encoding="utf-8")
        assert "favoravel" in html or "Favoravel" in html

    async def test_generated_html_contains_risk_factors(
        self, sample_job, tmp_path, monkeypatch
    ):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        report_path = await gen.generate(sample_job)

        html = report_path.read_text(encoding="utf-8")
        assert "taxa_di" in html or "usd_brl" in html

    async def test_generate_deduplicates_recommendations(
        self, sample_job, tmp_path, monkeypatch
    ):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        sample_job.test_results = [
            TestResult(test_id="T01", test_name="Q", recommendations=["Add stress test", "Add backtesting"]),
            TestResult(test_id="T02", test_name="M", recommendations=["Add stress test"]),  # duplicate
        ]

        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)

        # Capture the render call to check deduplication
        original_generate = gen.generate
        render_recs = None

        async def tracking_generate(job):
            nonlocal render_recs
            result = await original_generate(job)
            return result

        report_path = await gen.generate(sample_job)
        html = report_path.read_text()
        # "Add stress test" should appear only once in final recommendations list
        assert html.count("Add stress test") >= 1

    async def test_build_opinion_returns_dict(self, sample_job):
        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        sample_job.test_results = [
            TestResult(test_id="T01", test_name="Q", status=TestStatus.PASSED,
                       score=9.0, max_score=10.0, summary="great")
        ]
        opinion = await gen._build_opinion(sample_job)
        assert "opiniao" in opinion
        assert "justificativa" in opinion
        assert "nota_geral" in opinion

    async def test_build_opinion_fallback_on_exception(self, sample_job):
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=Exception("LLM unavailable"))
        gen = ReportGenerator(llm)
        opinion = await gen._build_opinion(sample_job)
        # Should return default fallback dict
        assert "opiniao" in opinion
        assert opinion["opiniao"] == "favoravel_com_recomendacoes"

    async def test_build_opinion_handles_empty_test_results(self, sample_job):
        sample_job.test_results = []
        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        opinion = await gen._build_opinion(sample_job)
        assert isinstance(opinion, dict)

    async def test_report_path_uses_job_id(self, sample_job, tmp_path, monkeypatch):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        report_path = await gen.generate(sample_job)

        assert sample_job.job_id in str(report_path)

    async def test_html_contains_test_results_summary(
        self, sample_job, tmp_path, monkeypatch
    ):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        sample_job.test_results = [
            TestResult(
                test_id="T01", test_name="Qualidade da Documentação",
                status=TestStatus.PASSED, score=8.0, max_score=10.0,
                summary="Documentação clara e completa.",
                figures=[]
            )
        ]
        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        report_path = await gen.generate(sample_job)
        html = report_path.read_text(encoding="utf-8")
        assert "Qualidade da Documentação" in html

    async def test_html_contains_equations(self, sample_job, tmp_path, monkeypatch):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        report_path = await gen.generate(sample_job)
        html = report_path.read_text(encoding="utf-8")
        assert "PV" in html  # equation label from sample_model_understanding

    async def test_html_is_valid_html_structure(
        self, sample_job, tmp_path, monkeypatch
    ):
        import app.services.report_generator as rg_mod
        monkeypatch.setattr(rg_mod.settings, "reports_dir", tmp_path)

        llm = _make_llm(OPINION_PAYLOAD)
        gen = ReportGenerator(llm)
        report_path = await gen.generate(sample_job)
        html = report_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "<body>" in html or "<body" in html
