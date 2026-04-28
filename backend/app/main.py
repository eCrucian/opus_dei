from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import upload, validation, report

app = FastAPI(
    title="Validador de Modelos MtM",
    description="Sistema automático de validação de modelos de mark-to-market",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(validation.router, prefix="/api")
app.include_router(report.router, prefix="/api")


@app.get("/api/health")
async def health():
    from app.config import settings
    return {"status": "ok", "llm_provider": settings.llm_provider}
