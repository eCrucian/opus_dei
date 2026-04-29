from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    TESTING = "testing"
    GENERATING_REPORT = "generating_report"
    DONE = "done"
    ERROR = "error"


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class RiskFactor(BaseModel):
    name: str
    type: str  # "spot" | "rate" | "vol" | "spread" | "other"
    description: str
    curve_or_index: Optional[str] = None
    is_accrued: Optional[bool] = None
    is_projected: Optional[bool] = None


class ModelEquation(BaseModel):
    label: str
    latex: str
    description: str
    variables: List[str] = []


class ModelUnderstanding(BaseModel):
    product_type: str
    product_description: str
    scope: str
    risk_factors: List[RiskFactor]
    parameters: List[Dict[str, str]]
    equations: List[ModelEquation]
    pricing_methodology: str
    has_monte_carlo: bool = False
    has_multiple_assets: bool = False
    regulatory_scope: Optional[str] = None
    raw_summary: str


class ParsedDocument(BaseModel):
    filename: str
    format: str
    raw_text: str
    sections: Dict[str, str] = {}
    equations_raw: List[str] = []
    metadata: Dict[str, Any] = {}


class ParsedCode(BaseModel):
    files: List[Dict[str, Any]] = []
    excel_sheets: List[Dict[str, Any]] = []
    language: str = "mixed"
    summary: str = ""


class TestResult(BaseModel):
    test_id: str
    test_name: str
    status: TestStatus = TestStatus.PENDING
    score: Optional[float] = None
    max_score: Optional[float] = None
    summary: str = ""
    details: Dict[str, Any] = {}
    recommendations: List[str] = []
    impediments: List[str] = []
    figures: List[str] = []
    generated_code: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ValidationJob(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    doc_filename: Optional[str] = None
    code_filenames: List[str] = []
    model_understanding: Optional[ModelUnderstanding] = None
    test_results: List[TestResult] = []
    report_path: Optional[str] = None
    error: Optional[str] = None
    progress_log: List[str] = []

    def log(self, msg: str) -> None:
        self.progress_log.append(f"[{datetime.utcnow().isoformat()}] {msg}")
        self.updated_at = datetime.utcnow()
