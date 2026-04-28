"""Shared fixtures for all tests."""
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

# Force Agg backend before any matplotlib import
os.environ["MPLBACKEND"] = "Agg"

from app.models.validation import (
    ValidationJob, ModelUnderstanding, ParsedDocument, ParsedCode,
    RiskFactor, ModelEquation, TestResult, JobStatus, TestStatus,
)
from app.services.llm.base import BaseLLMClient, LLMResponse


# ── LLM mock ─────────────────────────────────────────────────────────────────

def make_llm_mock(json_payload: dict | None = None, text: str = "ok") -> MagicMock:
    """Return a mock BaseLLMClient whose complete() returns predetermined content."""
    content = json.dumps(json_payload) if json_payload is not None else text
    llm = MagicMock(spec=BaseLLMClient)
    llm.complete = AsyncMock(
        return_value=LLMResponse(content=content, model="test-model")
    )
    llm.complete_json = AsyncMock(return_value=content)
    llm.stream = AsyncMock()
    return llm


@pytest.fixture
def mock_llm():
    return make_llm_mock({"test": "ok"})


# ── Domain objects ────────────────────────────────────────────────────────────

@pytest.fixture
def rate_factor():
    return RiskFactor(
        name="taxa_di",
        type="rate",
        description="Taxa DI Over",
        curve_or_index="DI",
        is_accrued=True,
        is_projected=True,
    )


@pytest.fixture
def spot_factor():
    return RiskFactor(
        name="usd_brl",
        type="spot",
        description="Taxa de câmbio USD/BRL",
        curve_or_index="PTAX",
    )


@pytest.fixture
def vol_factor():
    return RiskFactor(
        name="vol_ibov",
        type="vol",
        description="Volatilidade implícita IBOV",
    )


@pytest.fixture
def sample_equation():
    return ModelEquation(
        label="PV",
        latex=r"PV = N \cdot e^{-r \cdot T}",
        description="Valor presente do fluxo",
        variables=["N", "r", "T"],
    )


@pytest.fixture
def sample_model_understanding(rate_factor, spot_factor, sample_equation):
    return ModelUnderstanding(
        product_type="Swap de Taxa de Juros",
        product_description="Swap pré × DI com pagamento semestral",
        scope="Precificação de swaps plain vanilla",
        pricing_methodology="Desconto de fluxos a valor presente usando curva DI",
        has_monte_carlo=False,
        has_multiple_assets=False,
        risk_factors=[rate_factor, spot_factor],
        parameters=[{"name": "notional", "description": "Valor nominal", "unit": "BRL"}],
        equations=[sample_equation],
        raw_summary="Modelo de swap de taxa de juros DI × Pré.",
        regulatory_scope="BACEN/ANBIMA",
    )


@pytest.fixture
def mc_model_understanding(rate_factor, vol_factor, sample_equation):
    return ModelUnderstanding(
        product_type="Opção Europeia",
        product_description="Opção europeia de compra sobre IBOV",
        scope="Precificação de opções vanillas sobre índice",
        pricing_methodology="Monte Carlo com simulação de caminhos",
        has_monte_carlo=True,
        has_multiple_assets=False,
        risk_factors=[rate_factor, vol_factor],
        parameters=[{"name": "strike", "description": "Preço de exercício"}],
        equations=[sample_equation],
        raw_summary="Opção europeia precificada via Monte Carlo.",
    )


@pytest.fixture
def sample_parsed_doc():
    return ParsedDocument(
        filename="modelo_swap.pdf",
        format="pdf",
        raw_text=(
            "# Modelo de Swap\n\n"
            "Este modelo precifica swaps pré × DI.\n\n"
            r"$$PV = N \cdot e^{-r \cdot T}$$"
        ),
        sections={"Modelo de Swap": "Este modelo precifica swaps pré × DI."},
        equations_raw=[r"PV = N \cdot e^{-r \cdot T}"],
        metadata={"path": "/tmp/modelo_swap.pdf", "size_bytes": 1024},
    )


@pytest.fixture
def sample_parsed_code():
    return ParsedCode(
        files=[
            {
                "filename": "pricer.py",
                "language": "python",
                "content": (
                    "import numpy as np\n\n"
                    "class ModelPricer:\n"
                    "    def __init__(self, **kw): self.notional = kw.get('notional', 1e6)\n"
                    "    def price(self, rf): return self.notional * np.exp(-rf.get('taxa_di', 0.12))\n"
                    "    def get_risk_factors(self): return ['taxa_di']\n"
                ),
                "lines": 5,
            }
        ],
        excel_sheets=[],
        language="python",
        summary="1 arquivo | python",
    )


@pytest.fixture
def minimal_pricer_code():
    return (
        "import numpy as np\n\n"
        "# RISK_FACTORS = ['taxa_di']\n\n"
        "class ModelPricer:\n"
        "    def __init__(self, **kw):\n"
        "        self.notional = kw.get('notional', 1_000_000)\n"
        "    def price(self, risk_factors: dict) -> float:\n"
        "        r = risk_factors.get('taxa_di', 0.12)\n"
        "        return self.notional * float(np.exp(-r * 1.0))\n"
        "    def greeks(self, rf, bump=1e-4):\n"
        "        pv0 = self.price(rf)\n"
        "        d = {}\n"
        "        for k, v in rf.items():\n"
        "            up = dict(rf); up[k] = v * (1 + bump)\n"
        "            dn = dict(rf); dn[k] = v * (1 - bump)\n"
        "            d[k] = (self.price(up) - self.price(dn)) / (2 * v * bump)\n"
        "        return d\n"
        "    def get_risk_factors(self): return ['taxa_di']\n\n"
        "if __name__ == '__main__':\n"
        "    p = ModelPricer()\n"
        "    print(p.price({'taxa_di': 0.12}))\n"
    )


@pytest.fixture
def sample_job(sample_model_understanding):
    job = ValidationJob(
        job_id="test-job-abc123",
        doc_filename="modelo.pdf",
        code_filenames=[],
        model_understanding=sample_model_understanding,
    )
    return job


@pytest.fixture
def passed_test_result():
    return TestResult(
        test_id="T01_doc_quality",
        test_name="Qualidade da Documentação",
        status=TestStatus.PASSED,
        score=8.5,
        max_score=10.0,
        summary="Documentação de boa qualidade.",
        recommendations=["Adicionar referências bibliográficas."],
        impediments=[],
    )


# ── Storage patch helper ──────────────────────────────────────────────────────

@pytest.fixture
def storage_dirs(tmp_path):
    """Create isolated storage directories for tests."""
    dirs = {
        "sessions": tmp_path / "sessions",
        "uploads": tmp_path / "uploads",
        "generated_code": tmp_path / "generated_code",
        "reports": tmp_path / "reports",
    }
    for d in dirs.values():
        d.mkdir()
    return dirs
