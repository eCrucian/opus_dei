"""Tests for app/models/validation.py — all Pydantic models and enums."""
import pytest
from datetime import datetime
from app.models.validation import (
    JobStatus, TestStatus, RiskFactor, ModelEquation,
    ModelUnderstanding, ParsedDocument, ParsedCode, TestResult, ValidationJob,
)


class TestJobStatus:
    def test_all_values_exist(self):
        values = {s.value for s in JobStatus}
        assert values == {"pending", "parsing", "analyzing", "testing",
                          "generating_report", "done", "error"}

    def test_is_str_enum(self):
        assert isinstance(JobStatus.DONE, str)
        assert JobStatus.DONE == "done"


class TestTestStatus:
    def test_all_values_exist(self):
        values = {s.value for s in TestStatus}
        assert values == {"pending", "running", "passed", "failed", "warning", "skipped"}

    def test_is_str_enum(self):
        assert isinstance(TestStatus.PASSED, str)


class TestRiskFactor:
    def test_required_fields(self):
        rf = RiskFactor(name="usd", type="spot", description="câmbio")
        assert rf.name == "usd"
        assert rf.type == "spot"
        assert rf.description == "câmbio"

    def test_optional_fields_default_none(self):
        rf = RiskFactor(name="x", type="rate", description="y")
        assert rf.curve_or_index is None
        assert rf.is_accrued is None
        assert rf.is_projected is None

    def test_all_fields(self):
        rf = RiskFactor(
            name="di", type="rate", description="DI Over",
            curve_or_index="DI1", is_accrued=True, is_projected=False,
        )
        assert rf.curve_or_index == "DI1"
        assert rf.is_accrued is True
        assert rf.is_projected is False


class TestModelEquation:
    def test_required_fields(self):
        eq = ModelEquation(label="PV", latex=r"PV=N\cdot e^{-r}", description="valor presente")
        assert eq.label == "PV"
        assert eq.variables == []

    def test_variables_list(self):
        eq = ModelEquation(label="F", latex="F=S*e^{rT}", description="forward", variables=["S", "r", "T"])
        assert eq.variables == ["S", "r", "T"]


class TestModelUnderstanding:
    def test_defaults(self):
        mu = ModelUnderstanding(
            product_type="Swap",
            product_description="desc",
            scope="scope",
            pricing_methodology="NPV",
            risk_factors=[],
            parameters=[],
            equations=[],
            raw_summary="summary",
        )
        assert mu.has_monte_carlo is False
        assert mu.has_multiple_assets is False
        assert mu.regulatory_scope is None

    def test_with_nested_models(self, rate_factor, sample_equation):
        mu = ModelUnderstanding(
            product_type="Option",
            product_description="call",
            scope="vanilla",
            pricing_methodology="BS",
            risk_factors=[rate_factor],
            parameters=[],
            equations=[sample_equation],
            raw_summary="BS model",
            has_monte_carlo=True,
            has_multiple_assets=True,
            regulatory_scope="BACEN",
        )
        assert len(mu.risk_factors) == 1
        assert mu.risk_factors[0].name == "taxa_di"
        assert mu.has_monte_carlo is True
        assert mu.regulatory_scope == "BACEN"


class TestParsedDocument:
    def test_defaults(self):
        doc = ParsedDocument(filename="a.pdf", format="pdf", raw_text="text")
        assert doc.sections == {}
        assert doc.equations_raw == []
        assert doc.metadata == {}

    def test_with_all_fields(self):
        doc = ParsedDocument(
            filename="model.docx", format="docx", raw_text="content",
            sections={"Intro": "intro text"},
            equations_raw=[r"PV = N"],
            metadata={"size": 1024},
        )
        assert doc.sections["Intro"] == "intro text"


class TestParsedCode:
    def test_defaults(self):
        pc = ParsedCode()
        assert pc.files == []
        assert pc.excel_sheets == []
        assert pc.language == "mixed"
        assert pc.summary == ""


class TestTestResult:
    def test_defaults(self):
        tr = TestResult(test_id="T01", test_name="Qualidade")
        assert tr.status == TestStatus.PENDING
        assert tr.score is None
        assert tr.max_score is None
        assert tr.recommendations == []
        assert tr.impediments == []
        assert tr.figures == []
        assert tr.started_at is None
        assert tr.finished_at is None

    def test_with_score(self):
        tr = TestResult(test_id="T01", test_name="Q", score=8.5, max_score=10.0)
        assert tr.score == pytest.approx(8.5)


class TestValidationJob:
    def test_defaults(self):
        job = ValidationJob(job_id="abc")
        assert job.status == JobStatus.PENDING
        assert job.doc_filename is None
        assert job.code_filenames == []
        assert job.model_understanding is None
        assert job.test_results == []
        assert job.report_path is None
        assert job.error is None
        assert job.progress_log == []

    def test_log_appends_message(self):
        job = ValidationJob(job_id="abc")
        before = job.updated_at
        job.log("Step 1 done")
        assert len(job.progress_log) == 1
        assert "Step 1 done" in job.progress_log[0]
        assert job.updated_at >= before

    def test_log_multiple(self):
        job = ValidationJob(job_id="abc")
        job.log("msg1")
        job.log("msg2")
        assert len(job.progress_log) == 2

    def test_log_includes_timestamp(self):
        job = ValidationJob(job_id="abc")
        job.log("test")
        assert "T" in job.progress_log[0]  # ISO format has T separator

    def test_status_assignment(self):
        job = ValidationJob(job_id="abc")
        job.status = JobStatus.DONE
        assert job.status == JobStatus.DONE
