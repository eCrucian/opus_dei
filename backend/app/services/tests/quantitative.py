"""Test 3: Run AI-proposed quantitative tests by generating and executing code."""
from pathlib import Path
from typing import List
from app.models.validation import ModelUnderstanding, TestResult, TestStatus
from .base import BaseTest
from app.services.agents.quant_test_generator import QuantTestGeneratorAgent
from app.utils.code_executor import safe_exec
from app.config import settings


class QuantitativeTest(BaseTest):
    test_id = "T03_quantitative"
    test_name = "Testes Quantitativos Gerados por IA"

    async def _execute(
        self,
        result: TestResult,
        mu: ModelUnderstanding,
        methodology_analysis: dict,
        replication_code: str,
        job_id: str,
    ) -> None:
        agent = QuantTestGeneratorAgent(self.llm)
        method_str = str(methodology_analysis.get("testes_sugeridos", ""))
        proposed = await agent.propose_tests(mu, method_str)

        if not proposed:
            result.status = TestStatus.SKIPPED
            result.summary = "Nenhum teste quantitativo proposto."
            return

        test_outcomes = []
        code_dir = settings.generated_code_dir / job_id
        code_dir.mkdir(parents=True, exist_ok=True)

        for t in proposed[:6]:  # cap at 6 auto-tests
            test_id_str = t.get("test_id", t.get("nome", "qt_xx")).replace(" ", "_")
            code = await agent.generate_test_code(t, mu, replication_code)

            code_path = code_dir / f"{test_id_str}.py"
            code_path.write_text(code, encoding="utf-8")

            full_code = replication_code + "\n\n" + code
            fn_name = f"run_test_{test_id_str}"
            exec_result = safe_exec(full_code + f"\n_out = {fn_name}(ModelPricer)", "_out")

            test_outcomes.append({
                "test_id": test_id_str,
                "name": t.get("name", t.get("nome", "")),
                "description": t.get("description", t.get("descricao", "")),
                "code_file": str(code_path),
                "passed": exec_result.get("passed") if exec_result else None,
                "details": exec_result.get("details") if exec_result else "Erro de execução",
                "metrics": exec_result.get("metrics", {}) if exec_result else {},
                "figures": exec_result.get("figures_base64", []) if exec_result else [],
            })

        passed = sum(1 for t in test_outcomes if t.get("passed") is True)
        total = len(test_outcomes)

        result.score = float(passed) / total * 10 if total else None
        result.max_score = 10.0
        result.status = TestStatus.PASSED if passed == total else (
            TestStatus.WARNING if passed > 0 else TestStatus.FAILED
        )
        result.details = {"tests": test_outcomes}
        result.summary = f"{passed}/{total} testes quantitativos passaram."
        for t in test_outcomes:
            for fig in t.get("figures", []):
                result.figures.append(fig)
