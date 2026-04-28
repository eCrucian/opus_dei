"""Validation status and results endpoints."""
from fastapi import APIRouter, HTTPException
from app.utils.storage import load_job

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/{job_id}/status")
async def get_status(job_id: str):
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress_log": job.progress_log[-20:],
        "error": job.error,
        "tests_completed": len(job.test_results),
        "product_type": job.model_understanding.product_type if job.model_understanding else None,
    }


@router.get("/{job_id}/results")
async def get_results(job_id: str):
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "model_understanding": job.model_understanding,
        "test_results": job.test_results,
        "report_path": job.report_path,
    }
