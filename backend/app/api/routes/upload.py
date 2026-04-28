"""Upload endpoints — document and implementation files."""
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from app.config import settings
from app.models.validation import ValidationJob
from app.utils.storage import save_job, list_jobs
from app.services.orchestrator import run_validation

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_DOC = {".pdf", ".docx", ".ipynb", ".md", ".txt"}
ALLOWED_CODE = {".py", ".m", ".sql", ".r", ".jl", ".xlsx", ".xlsm", ".xlsb", ".xls"}


@router.post("/start")
async def start_validation(
    background_tasks: BackgroundTasks,
    document: UploadFile = File(..., description="Documento do modelo"),
    implementations: List[UploadFile] = File(default=[], description="Planilhas/scripts (opcional)"),
):
    doc_ext = Path(document.filename).suffix.lower()
    if doc_ext not in ALLOWED_DOC:
        raise HTTPException(400, f"Formato de documento não suportado: {doc_ext}. Use: {ALLOWED_DOC}")

    job_id = str(uuid.uuid4())
    job_dir = settings.uploads_dir / job_id
    job_dir.mkdir(parents=True)

    # Save document
    doc_path = job_dir / document.filename
    doc_path.write_bytes(await document.read())

    # Save implementation files
    code_paths: List[Path] = []
    for impl in implementations:
        ext = Path(impl.filename).suffix.lower()
        if ext not in ALLOWED_CODE:
            continue
        p = job_dir / impl.filename
        p.write_bytes(await impl.read())
        code_paths.append(p)

    # Create job
    job = ValidationJob(
        job_id=job_id,
        doc_filename=document.filename,
        code_filenames=[p.name for p in code_paths],
    )
    save_job(job)

    background_tasks.add_task(run_validation, job, doc_path, code_paths)

    return {"job_id": job_id, "message": "Validação iniciada com sucesso."}


@router.get("/jobs")
async def get_jobs():
    return list_jobs()
