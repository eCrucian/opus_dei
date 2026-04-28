"""Test 8: Compare provided code/Excel vs documentation (qualitative)."""
from app.models.validation import ModelUnderstanding, ParsedCode, TestResult, TestStatus
from .base import BaseTest
from app.services.agents.replica_comparator import ReplicaComparatorAgent


_SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}


class ReplicationTest(BaseTest):
    test_id = "T08_replication"
    test_name = "Comparação Implementação vs Documentação"

    async def _execute(
        self,
        result: TestResult,
        mu: ModelUnderstanding,
        provided_code: ParsedCode,
        replication_code: str,
    ) -> None:
        if not provided_code or not provided_code.files:
            result.status = TestStatus.SKIPPED
            result.summary = "Nenhum código/planilha fornecido — teste de replicação ignorado."
            return

        agent = ReplicaComparatorAgent(self.llm)
        data = await agent.compare(mu, provided_code, replication_code)

        score = float(data.get("adherence_score", 0))
        findings = data.get("findings", [])
        criticals = [f for f in findings if f.get("severity") == "critical"]

        result.score = score
        result.max_score = 10.0
        result.details = {
            "adherence_score": score,
            "adheres": data.get("adheres_to_methodology"),
            "findings": findings,
            "risk_factors_mapped": data.get("risk_factors_mapped", []),
            "risk_factors_missing": data.get("risk_factors_missing", []),
            "undocumented_logic": data.get("undocumented_logic", []),
        }
        result.summary = data.get("summary", "")
        result.recommendations = [
            f["description"] for f in findings
            if f.get("type") in ("discrepancy", "gap") and f.get("severity") in ("major", "minor")
        ]
        result.impediments = [f["description"] for f in criticals]

        if criticals:
            result.status = TestStatus.FAILED
        elif score >= 7:
            result.status = TestStatus.PASSED
        else:
            result.status = TestStatus.WARNING
