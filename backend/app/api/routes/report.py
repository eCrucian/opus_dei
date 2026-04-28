"""Report download endpoint."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from app.utils.storage import load_job

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/{job_id}", response_class=HTMLResponse)
async def get_report_html(job_id: str):
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")
    if not job.report_path:
        raise HTTPException(404, "Relatório ainda não gerado.")
    path = Path(job.report_path)
    if not path.exists():
        raise HTTPException(404, "Arquivo de relatório não encontrado.")
    return HTMLResponse(content=path.read_text(encoding="utf-8"))


@router.get("/{job_id}/download")
async def download_report(job_id: str):
    job = load_job(job_id)
    if not job or not job.report_path:
        raise HTTPException(404, "Relatório não disponível.")
    path = Path(job.report_path)
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado.")
    return FileResponse(
        path=str(path),
        filename=f"relatorio_validacao_{job_id[:8]}.html",
        media_type="text/html",
    )
