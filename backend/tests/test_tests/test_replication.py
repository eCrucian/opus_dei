"""Tests for ReplicationTest — implementation vs documentation comparison."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.validation import ParsedCode, TestStatus
from app.services.llm.base import LLMResponse
from app.services.tests.replication import ReplicationTest


def _make_llm(payload: dict):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=LLMResponse(content=json.dumps(payload), model="test"))
    return llm


def _make_findings(score=8.5, findings=None, criticals=None):
    all_findings = findings or []
    if criticals:
        all_findings += [{"type": "discrepancy", "element": "risk_factor", "description": c, "severity": "critical"} for c in criticals]
    return {
        "adherence_score": score,
        "adheres_to_methodology": score >= 7,
        "findings": all_findings,
        "risk_factors_mapped": ["taxa_di"],
        "risk_factors_missing": [],
        "undocumented_logic": [],
        "summary": f"Aderência: {score}/10",
    }


class TestReplicationTest:
    async def test_skipped_when_no_code_provided(
        self, sample_model_understanding, minimal_pricer_code
    ):
        llm = _make_llm({})
        test = ReplicationTest(llm)
        empty_code = ParsedCode()  # no files
        result = await test.run(sample_model_understanding, empty_code, minimal_pricer_code)
        assert result.status == TestStatus.SKIPPED

    async def test_skipped_when_parsed_code_is_none(
        self, sample_model_understanding, minimal_pricer_code
    ):
        # The condition is `if not provided_code or not provided_code.files`
        llm = _make_llm({})
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, None, minimal_pricer_code)
        assert result.status == TestStatus.SKIPPED

    async def test_passed_when_score_above_7_no_criticals(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        llm = _make_llm(_make_findings(score=8.5))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert result.status == TestStatus.PASSED

    async def test_failed_when_critical_findings_exist(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        llm = _make_llm(_make_findings(score=7.5, criticals=["Missing risk factor mapping"]))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert result.status == TestStatus.FAILED

    async def test_warning_when_score_below_7_no_criticals(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        llm = _make_llm(_make_findings(score=5.0))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert result.status == TestStatus.WARNING

    async def test_impediments_populated_from_criticals(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        llm = _make_llm(_make_findings(score=6.0, criticals=["Critical issue A", "Critical issue B"]))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert "Critical issue A" in result.impediments
        assert "Critical issue B" in result.impediments

    async def test_recommendations_from_major_discrepancies(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        findings = [
            {"type": "discrepancy", "element": "eq1", "description": "Equation differs", "severity": "major"},
            {"type": "gap", "element": "rf2", "description": "Risk factor missing", "severity": "minor"},
            {"type": "match", "element": "rf1", "description": "OK", "severity": "info"},
        ]
        llm = _make_llm(_make_findings(score=6.0, findings=findings))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert "Equation differs" in result.recommendations
        assert "Risk factor missing" in result.recommendations
        assert "OK" not in result.recommendations  # info findings not included

    async def test_score_and_max_score(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        llm = _make_llm(_make_findings(score=7.0))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert result.score == pytest.approx(7.0)
        assert result.max_score == pytest.approx(10.0)

    async def test_details_structure(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        llm = _make_llm(_make_findings(score=8.0))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert "adherence_score" in result.details
        assert "findings" in result.details
        assert "risk_factors_mapped" in result.details

    async def test_test_id_and_name(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        llm = _make_llm(_make_findings(score=9.0))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert result.test_id == "T08_replication"
        assert "Comparação" in result.test_name

    async def test_boundary_score_exactly_7_is_passed(
        self, sample_model_understanding, sample_parsed_code, minimal_pricer_code
    ):
        llm = _make_llm(_make_findings(score=7.0))
        test = ReplicationTest(llm)
        result = await test.run(sample_model_understanding, sample_parsed_code, minimal_pricer_code)
        assert result.status == TestStatus.PASSED
