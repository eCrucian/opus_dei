"""Code file parser — Python, MATLAB, SQL, R."""
from pathlib import Path
from typing import List, Dict
from app.models.validation import ParsedCode


CODE_EXTENSIONS = {".py", ".m", ".sql", ".r", ".jl", ".cpp", ".c", ".f90"}
EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xlsb", ".xls"}


def parse_code_files(file_paths: List[Path]) -> ParsedCode:
    code_files: List[Dict[str, str]] = []
    excel_sheets: List[Dict] = []
    languages = set()

    for path in file_paths:
        suffix = path.suffix.lower()
        if suffix in CODE_EXTENSIONS:
            lang = _detect_language(suffix)
            languages.add(lang)
            content = path.read_text(encoding="utf-8", errors="replace")
            code_files.append({
                "filename": path.name,
                "language": lang,
                "content": content[:50_000],  # 50k char limit per file
                "lines": content.count("\n"),
            })
        elif suffix in EXCEL_EXTENSIONS:
            from .excel import excel_to_text, parse_excel
            sheets, named_ranges = parse_excel(path)
            excel_sheets.extend(sheets)
            code_files.append({
                "filename": path.name,
                "language": "excel",
                "content": excel_to_text(path)[:50_000],
                "lines": sum(s.get("rows", []) and len(s["rows"]) for s in sheets),
            })
            languages.add("excel")

    lang_str = ", ".join(sorted(languages)) if languages else "unknown"
    summary = f"{len(code_files)} arquivo(s) de implementação | linguagens: {lang_str}"

    return ParsedCode(
        files=code_files,
        excel_sheets=excel_sheets,
        language=lang_str,
        summary=summary,
    )


def _detect_language(suffix: str) -> str:
    return {
        ".py": "python", ".m": "matlab", ".sql": "sql",
        ".r": "r", ".jl": "julia", ".cpp": "cpp",
        ".c": "c", ".f90": "fortran",
    }.get(suffix, "unknown")
