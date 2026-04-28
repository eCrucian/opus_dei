"""Orchestrator — coordinates all agents and tests in the correct sequence."""
import asyncio
from pathlib import Path
from typing import Optional
from app.models.validation import ValidationJob, JobStatus, ParsedCode
from app.utils.storage import save_job
from app.config import settings
from app.services.llm.factory import create_llm_client
from app.services.parsers.document import parse_document
from app.services.parsers.code import parse_code_files
from app.services.agents.document_analyzer import DocumentAnalyzerAgent
from app.services.agents.model_replicator import ModelReplicatorAgent
from app.services.tests.doc_quality import DocQualityTest
from app.services.tests.methodology import MethodologyTest
from app.services.tests.quantitative import QuantitativeTest
from app.services.tests.stability import StabilityTest
from app.services.tests.performance import PerformanceTest
from app.services.tests.monte_carlo import MonteCarloTest
from app.services.tests.replication import ReplicationTest
from app.services.report_generator import ReportGenerator


async def run_validation(
    job: ValidationJob,
    doc_path: Path,
    code_paths: list[Path],
) -> None:
    llm = create_llm_client()

    try:
        # ── Step 1: Parse document ────────────────────────────────────────────
        job.status = JobStatus.PARSING
        job.log("Lendo e parseando documento...")
        save_job(job)

        doc = parse_document(doc_path)

        parsed_code: Optional[ParsedCode] = None
        if code_paths:
            job.log(f"Lendo {len(code_paths)} arquivo(s) de implementação...")
            parsed_code = parse_code_files(code_paths)

        # ── Step 2: Understand the model ─────────────────────────────────────
        job.status = JobStatus.ANALYZING
        job.log("Analisando documento com IA — extraindo modelo, equações, fatores de risco...")
        save_job(job)

        mu = await DocumentAnalyzerAgent(llm).analyze(doc)
        job.model_understanding = mu
        job.log(f"Modelo entendido: {mu.product_type} | {len(mu.risk_factors)} fatores de risco | {len(mu.equations)} equações")
        save_job(job)

        # ── Step 3: Tests ─────────────────────────────────────────────────────
        job.status = JobStatus.TESTING
        save_job(job)

        # T01 — Doc quality (can run in parallel with T02)
        job.log("T01: Avaliando qualidade da documentação...")
        t01 = await DocQualityTest(llm).run(doc, mu)
        job.test_results.append(t01)
        save_job(job)

        # T02 — Methodology
        job.log("T02: Análise metodológica...")
        t02 = await MethodologyTest(llm).run(mu)
        job.test_results.append(t02)
        save_job(job)

        # Model replication (needed for T03, T05, T06, T07, T08)
        job.log("Gerando código de replicação do modelo...")
        replication_code = await ModelReplicatorAgent(llm).replicate(mu)
        rep_path = settings.generated_code_dir / job.job_id / "model_replication.py"
        rep_path.parent.mkdir(parents=True, exist_ok=True)
        rep_path.write_text(replication_code, encoding="utf-8")
        job.log(f"Código de replicação salvo em {rep_path}")
        save_job(job)

        # T03 — AI-generated quantitative tests
        job.log("T03: Gerando e executando testes quantitativos...")
        methodology_details = t02.details
        t03 = await QuantitativeTest(llm).run(mu, methodology_details, replication_code, job.job_id)
        job.test_results.append(t03)
        save_job(job)

        # T05 — Stability (first derivatives)
        job.log("T05: Teste de estabilidade — derivadas primeiras...")
        t05 = await StabilityTest(llm).run(mu, replication_code)
        job.test_results.append(t05)
        save_job(job)

        # T06 — Performance/curvature (second derivatives)
        job.log("T06: Teste de curvatura — derivadas segundas...")
        t06 = await PerformanceTest(llm).run(mu, replication_code)
        job.test_results.append(t06)
        save_job(job)

        # T07 — Monte Carlo convergence (only if applicable)
        job.log("T07: Teste de convergência Monte Carlo...")
        t07 = await MonteCarloTest(llm).run(mu, replication_code)
        job.test_results.append(t07)
        save_job(job)

        # T08 — Replication vs provided code (only if code was provided)
        if parsed_code:
            job.log("T08: Comparando implementação fornecida com documentação...")
            t08 = await ReplicationTest(llm).run(mu, parsed_code, replication_code)
            job.test_results.append(t08)
            save_job(job)

        # ── Step 4: Generate report ───────────────────────────────────────────
        job.status = JobStatus.GENERATING_REPORT
        job.log("Gerando relatório final...")
        save_job(job)

        report_path = await ReportGenerator(llm).generate(job)
        job.report_path = str(report_path)
        job.status = JobStatus.DONE
        job.log(f"Concluído! Relatório disponível em {report_path}")
        save_job(job)

    except Exception as exc:
        job.status = JobStatus.ERROR
        job.error = str(exc)
        job.log(f"ERRO: {exc}")
        save_job(job)
        raise
