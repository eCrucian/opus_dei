"""Tests for MethodologyTest."""
import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.models.validation import TestStatus
from app.services.llm.base import LLMResponse
from app.services.tests.methodology import MethodologyTest


def _method_payload(recomendacoes=None, impeditivos=None):
    return {
        "premissas": [
            {"premissa": "Mercado eficiente", "tipo": "mercado",
             "avaliacao": "razoavel", "impacto_se_violada": "alto", "contexto_br": "BR ok"}
        ],
        "alternativas": [
            {"nome": "Monte Carlo", "descricao": "MC approach",
             "vantagens": ["flexível"], "desvantagens": ["lento"], "quando_usar": "complexo"}
        ],
        "testes_quantitativos": [
            {"nome": "Boundary test", "descricao": "test", "tipo": "boundary", "prioridade": "alta"}
        ],
        "limitacoes_modelo": ["Assume distribuição normal"],
        "recomendacoes": recomendacoes or ["Adicionar stress test"],
        "impeditivos": impeditivos or [],
        "sumario": "Análise metodológica concluída.",
    }


def _make_llm(payload):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=LLMResponse(content=json.dumps(payload), model="test"))
    return llm


class TestMethodologyTest:
    async def test_always_passed(self, sample_model_understanding):
        llm = _make_llm(_method_payload())
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert result.status == TestStatus.PASSED

    async def test_details_has_premissas(self, sample_model_understanding):
        llm = _make_llm(_method_payload())
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert "premissas" in result.details
        assert len(result.details["premissas"]) == 1

    async def test_details_has_alternativas(self, sample_model_understanding):
        llm = _make_llm(_method_payload())
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert "alternativas" in result.details
        assert result.details["alternativas"][0]["nome"] == "Monte Carlo"

    async def test_details_has_testes_sugeridos(self, sample_model_understanding):
        llm = _make_llm(_method_payload())
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert "testes_sugeridos" in result.details

    async def test_details_has_limitacoes(self, sample_model_understanding):
        llm = _make_llm(_method_payload())
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert "limitacoes" in result.details

    async def test_recommendations_populated(self, sample_model_understanding):
        llm = _make_llm(_method_payload(recomendacoes=["Review premises"]))
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert "Review premises" in result.recommendations

    async def test_impediments_populated(self, sample_model_understanding):
        llm = _make_llm(_method_payload(impeditivos=["Missing risk factor"]))
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert "Missing risk factor" in result.impediments

    async def test_summary_from_payload(self, sample_model_understanding):
        llm = _make_llm(_method_payload())
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert "Análise metodológica" in result.summary

    async def test_handles_model_with_no_equations(self, sample_model_understanding):
        sample_model_understanding.equations = []
        llm = _make_llm(_method_payload())
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert result.status == TestStatus.PASSED

    async def test_test_id(self, sample_model_understanding):
        llm = _make_llm(_method_payload())
        test = MethodologyTest(llm)
        result = await test.run(sample_model_understanding)
        assert result.test_id == "T02_methodology"
