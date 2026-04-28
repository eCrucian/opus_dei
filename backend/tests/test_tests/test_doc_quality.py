"""Tests for DocQualityTest — score-to-status mapping and details structure."""
import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.models.validation import TestStatus
from app.services.llm.base import LLMResponse
from app.services.tests.doc_quality import DocQualityTest


def _make_doc_quality_payload(nota: float, impeditivos=None, recomendacoes=None):
    return {
        "scores": {
            "clareza": {"score": nota, "justificativa": "ok"},
            "completude": {"score": nota, "justificativa": "ok"},
        },
        "nota_geral": nota,
        "pontos_fortes": ["ponto forte"],
        "pontos_fracos": ["ponto fraco"],
        "recomendacoes": recomendacoes or [],
        "impeditivos": impeditivos or [],
        "sumario": f"Nota: {nota}",
    }


def _make_llm(payload: dict):
    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=LLMResponse(content=json.dumps(payload), model="test")
    )
    return llm


class TestDocQualityTest:
    async def test_status_passed_when_score_above_7(self, sample_parsed_doc, sample_model_understanding):
        llm = _make_llm(_make_doc_quality_payload(8.5))
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert result.status == TestStatus.PASSED
        assert result.score == pytest.approx(8.5)

    async def test_status_warning_when_score_between_4_and_7(self, sample_parsed_doc, sample_model_understanding):
        llm = _make_llm(_make_doc_quality_payload(5.0))
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert result.status == TestStatus.WARNING

    async def test_status_failed_when_score_below_4(self, sample_parsed_doc, sample_model_understanding):
        llm = _make_llm(_make_doc_quality_payload(2.0))
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert result.status == TestStatus.FAILED

    async def test_status_passed_at_boundary_7(self, sample_parsed_doc, sample_model_understanding):
        llm = _make_llm(_make_doc_quality_payload(7.0))
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert result.status == TestStatus.PASSED

    async def test_status_warning_at_boundary_4(self, sample_parsed_doc, sample_model_understanding):
        llm = _make_llm(_make_doc_quality_payload(4.0))
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert result.status == TestStatus.WARNING

    async def test_details_structure(self, sample_parsed_doc, sample_model_understanding):
        payload = _make_doc_quality_payload(7.5, recomendacoes=["Add more detail"])
        llm = _make_llm(payload)
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert "scores" in result.details
        assert "pontos_fortes" in result.details
        assert "pontos_fracos" in result.details

    async def test_recommendations_populated(self, sample_parsed_doc, sample_model_understanding):
        payload = _make_doc_quality_payload(8.0, recomendacoes=["Add stress test", "Add backtesting"])
        llm = _make_llm(payload)
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert "Add stress test" in result.recommendations

    async def test_impediments_populated(self, sample_parsed_doc, sample_model_understanding):
        payload = _make_doc_quality_payload(2.0, impeditivos=["Missing equations"])
        llm = _make_llm(payload)
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert "Missing equations" in result.impediments

    async def test_max_score_is_10(self, sample_parsed_doc, sample_model_understanding):
        llm = _make_llm(_make_doc_quality_payload(9.0))
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert result.max_score == pytest.approx(10.0)

    async def test_test_id_and_name(self, sample_parsed_doc, sample_model_understanding):
        llm = _make_llm(_make_doc_quality_payload(7.0))
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert result.test_id == "T01_doc_quality"
        assert "Qualidade" in result.test_name

    async def test_defaults_when_keys_missing(self, sample_parsed_doc, sample_model_understanding):
        """Covers .get() defaults when some keys are absent from payload."""
        llm = _make_llm({})  # empty payload
        test = DocQualityTest(llm)
        result = await test.run(sample_parsed_doc, sample_model_understanding)
        assert result.score == pytest.approx(0.0)
        assert result.status == TestStatus.FAILED
