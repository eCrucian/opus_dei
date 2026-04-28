"""Tests for all agent classes and _parse_json helper."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.base import LLMResponse
from app.services.agents.base import BaseAgent, _parse_json, QUANT_SYSTEM
from app.services.agents.document_analyzer import DocumentAnalyzerAgent
from app.services.agents.model_replicator import ModelReplicatorAgent
from app.services.agents.quant_test_generator import QuantTestGeneratorAgent
from app.services.agents.replica_comparator import ReplicaComparatorAgent
from app.models.validation import ModelUnderstanding, RiskFactor, ModelEquation


# ── _parse_json ───────────────────────────────────────────────────────────────

class TestParseJson:
    def test_clean_json(self):
        result = _parse_json('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_strips_json_markdown_fence(self):
        text = "```json\n{\"key\": \"val\"}\n```"
        result = _parse_json(text)
        assert result == {"key": "val"}

    def test_strips_plain_markdown_fence(self):
        text = "```\n{\"x\": 1}\n```"
        result = _parse_json(text)
        assert result == {"x": 1}

    def test_strips_leading_and_trailing_whitespace(self):
        result = _parse_json('  \n{"a": "b"}\n  ')
        assert result == {"a": "b"}

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("not valid json at all")

    def test_nested_json(self):
        data = {"outer": {"inner": [1, 2, 3]}}
        result = _parse_json(json.dumps(data))
        assert result == data


# ── BaseAgent ─────────────────────────────────────────────────────────────────

class TestBaseAgent:
    def _agent_with_response(self, content: str):
        llm = MagicMock()
        llm.complete = AsyncMock(return_value=LLMResponse(content=content, model="test"))
        return BaseAgent(llm), llm

    async def test_ask_calls_llm_complete(self):
        agent, llm = self._agent_with_response("answer text")
        result = await agent.ask("my prompt")
        assert result == "answer text"
        llm.complete.assert_called_once()

    async def test_ask_passes_quant_system(self):
        agent, llm = self._agent_with_response("ok")
        await agent.ask("prompt")
        call_kwargs = llm.complete.call_args
        assert QUANT_SYSTEM in (call_kwargs[1].get("system") or call_kwargs[0][1])

    async def test_ask_json_returns_dict(self):
        agent, llm = self._agent_with_response('{"score": 9}')
        result = await agent.ask_json("prompt")
        assert result == {"score": 9}

    async def test_ask_json_strips_markdown_fence(self):
        content = "```json\n{\"result\": true}\n```"
        agent, llm = self._agent_with_response(content)
        result = await agent.ask_json("prompt")
        assert result == {"result": True}

    async def test_ask_uses_temperature_param(self):
        agent, llm = self._agent_with_response("ok")
        await agent.ask("p", temperature=0.9)
        call_kwargs = llm.complete.call_args
        assert call_kwargs[1].get("temperature") == 0.9 or call_kwargs[0][2] == 0.9

    async def test_ask_uses_max_tokens_param(self):
        agent, llm = self._agent_with_response("ok")
        await agent.ask("p", max_tokens=4096)
        call_kwargs = llm.complete.call_args
        assert 4096 in call_kwargs[0] or call_kwargs[1].get("max_tokens") == 4096


# ── DocumentAnalyzerAgent ─────────────────────────────────────────────────────

class TestDocumentAnalyzerAgent:
    def _agent_with_json(self, payload: dict):
        llm = MagicMock()
        llm.complete = AsyncMock(
            return_value=LLMResponse(content=json.dumps(payload), model="test")
        )
        return DocumentAnalyzerAgent(llm)

    async def test_analyze_returns_model_understanding(self, sample_parsed_doc):
        payload = {
            "product_type": "Swap DI",
            "product_description": "Swap pré × DI",
            "scope": "plain vanilla",
            "regulatory_scope": "BACEN",
            "pricing_methodology": "NPV",
            "has_monte_carlo": False,
            "has_multiple_assets": False,
            "risk_factors": [
                {"name": "taxa_di", "type": "rate", "description": "DI Over",
                 "curve_or_index": "DI1", "is_accrued": True, "is_projected": True}
            ],
            "parameters": [{"name": "notional", "description": "VN", "unit": "BRL"}],
            "equations": [
                {"label": "PV", "latex": r"PV = N e^{-r}", "description": "valor presente", "variables": ["N", "r"]}
            ],
            "raw_summary": "Modelo de swap simples.",
        }
        agent = self._agent_with_json(payload)
        result = await agent.analyze(sample_parsed_doc)

        assert isinstance(result, ModelUnderstanding)
        assert result.product_type == "Swap DI"
        assert len(result.risk_factors) == 1
        assert result.risk_factors[0].name == "taxa_di"
        assert len(result.equations) == 1
        assert result.regulatory_scope == "BACEN"
        assert result.has_monte_carlo is False

    async def test_analyze_handles_empty_lists(self, sample_parsed_doc):
        payload = {
            "product_type": "Unknown",
            "product_description": "desc",
            "scope": "scope",
            "regulatory_scope": None,
            "pricing_methodology": "NPV",
            "has_monte_carlo": False,
            "has_multiple_assets": False,
            "risk_factors": [],
            "parameters": [],
            "equations": [],
            "raw_summary": "summary",
        }
        agent = self._agent_with_json(payload)
        result = await agent.analyze(sample_parsed_doc)

        assert result.risk_factors == []
        assert result.equations == []
        assert result.regulatory_scope is None

    async def test_analyze_no_equations_in_doc(self, sample_parsed_doc):
        sample_parsed_doc.equations_raw = []
        payload = {
            "product_type": "Bond",
            "product_description": "desc",
            "scope": "scope",
            "regulatory_scope": None,
            "pricing_methodology": "NPV",
            "has_monte_carlo": False,
            "has_multiple_assets": False,
            "risk_factors": [],
            "parameters": [],
            "equations": [],
            "raw_summary": "summary",
        }
        agent = self._agent_with_json(payload)
        result = await agent.analyze(sample_parsed_doc)
        assert isinstance(result, ModelUnderstanding)


# ── ModelReplicatorAgent ──────────────────────────────────────────────────────

class TestModelReplicatorAgent:
    async def test_replicate_returns_python_code(self, sample_model_understanding):
        code = "class ModelPricer:\n    def price(self, rf): return 100.0"
        llm = MagicMock()
        llm.complete = AsyncMock(return_value=LLMResponse(content=code, model="test"))
        agent = ModelReplicatorAgent(llm)
        result = await agent.replicate(sample_model_understanding)
        assert "ModelPricer" in result

    async def test_replicate_strips_markdown_fence(self, sample_model_understanding):
        code = "```python\nclass ModelPricer:\n    pass\n```"
        llm = MagicMock()
        llm.complete = AsyncMock(return_value=LLMResponse(content=code, model="test"))
        agent = ModelReplicatorAgent(llm)
        result = await agent.replicate(sample_model_understanding)
        assert not result.startswith("```")
        assert "class ModelPricer" in result

    async def test_replicate_handles_no_equations(self, sample_model_understanding):
        sample_model_understanding.equations = []
        code = "class ModelPricer: pass"
        llm = MagicMock()
        llm.complete = AsyncMock(return_value=LLMResponse(content=code, model="test"))
        agent = ModelReplicatorAgent(llm)
        result = await agent.replicate(sample_model_understanding)
        assert result == "class ModelPricer: pass"


# ── QuantTestGeneratorAgent ───────────────────────────────────────────────────

class TestQuantTestGeneratorAgent:
    async def test_propose_tests_returns_list(self, sample_model_understanding):
        tests_payload = {"tests": [
            {"test_id": "qt_001", "name": "Boundary Test",
             "description": "Test boundary conditions",
             "category": "boundary",
             "expected_outcome": "PV > 0",
             "risk_factors_involved": ["taxa_di"]},
        ]}
        llm = MagicMock()
        llm.complete = AsyncMock(
            return_value=LLMResponse(content=json.dumps(tests_payload), model="test")
        )
        agent = QuantTestGeneratorAgent(llm)
        result = await agent.propose_tests(sample_model_understanding, "methodology analysis")
        assert len(result) == 1
        assert result[0]["test_id"] == "qt_001"

    async def test_propose_tests_empty_if_no_tests_key(self, sample_model_understanding):
        llm = MagicMock()
        llm.complete = AsyncMock(
            return_value=LLMResponse(content='{"other": "data"}', model="test")
        )
        agent = QuantTestGeneratorAgent(llm)
        result = await agent.propose_tests(sample_model_understanding, "")
        assert result == []

    async def test_generate_test_code_strips_fence(self, sample_model_understanding):
        code = "```python\ndef run_test_qt_001(pricer): return {'passed': True}\n```"
        llm = MagicMock()
        llm.complete = AsyncMock(return_value=LLMResponse(content=code, model="test"))
        agent = QuantTestGeneratorAgent(llm)
        test = {"test_id": "qt_001", "name": "Test", "description": "desc",
                "risk_factors_involved": ["taxa_di"]}
        result = await agent.generate_test_code(test, sample_model_understanding, "class ModelPricer: pass")
        assert not result.startswith("```")
        assert "def run_test_qt_001" in result

    async def test_generate_test_code_truncates_large_code(self, sample_model_understanding):
        large_code = "x = 1\n" * 5000
        llm = MagicMock()
        llm.complete = AsyncMock(return_value=LLMResponse(content="def f(): pass", model="test"))
        agent = QuantTestGeneratorAgent(llm)
        test = {"test_id": "qt_001", "name": "T", "description": "d", "risk_factors_involved": []}
        await agent.generate_test_code(test, sample_model_understanding, large_code)
        prompt = llm.complete.call_args[0][0]
        assert len(prompt) < 200_000  # large code was truncated to 3000 chars


# ── ReplicaComparatorAgent ────────────────────────────────────────────────────

class TestReplicaComparatorAgent:
    async def test_compare_returns_dict(self, sample_model_understanding, sample_parsed_code):
        payload = {
            "adherence_score": 8.5,
            "adheres_to_methodology": True,
            "findings": [],
            "risk_factors_mapped": ["taxa_di"],
            "risk_factors_missing": [],
            "undocumented_logic": [],
            "summary": "Boa aderência.",
        }
        llm = MagicMock()
        llm.complete = AsyncMock(
            return_value=LLMResponse(content=json.dumps(payload), model="test")
        )
        agent = ReplicaComparatorAgent(llm)
        result = await agent.compare(sample_model_understanding, sample_parsed_code, "class ModelPricer: pass")

        assert result["adherence_score"] == pytest.approx(8.5)
        assert result["risk_factors_mapped"] == ["taxa_di"]

    async def test_compare_truncates_files(self, sample_model_understanding):
        """Covers the for f in provided_code.files[:5] branch."""
        from app.models.validation import ParsedCode
        # Create code with 7 files — only first 5 should be included
        files = [
            {"filename": f"file{i}.py", "language": "python",
             "content": f"class M{i}: pass", "lines": 1}
            for i in range(7)
        ]
        parsed_code = ParsedCode(files=files)

        payload = {"adherence_score": 7, "adheres_to_methodology": True,
                   "findings": [], "risk_factors_mapped": [],
                   "risk_factors_missing": [], "undocumented_logic": [],
                   "summary": "ok"}
        llm = MagicMock()
        llm.complete = AsyncMock(
            return_value=LLMResponse(content=json.dumps(payload), model="test")
        )
        agent = ReplicaComparatorAgent(llm)
        prompt_text = None

        original_ask_json = agent.ask_json
        async def capture_ask_json(prompt, **kwargs):
            nonlocal prompt_text
            prompt_text = prompt
            return await original_ask_json(prompt, **kwargs)
        agent.ask_json = capture_ask_json

        await agent.compare(sample_model_understanding, parsed_code, "")
        # The prompt should include file7 but only the first 5 files
        assert "file0.py" in prompt_text
        assert "file4.py" in prompt_text
