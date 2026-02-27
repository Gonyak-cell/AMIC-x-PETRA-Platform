"""실사자료 파서 — Excel, PDF, DOCX, HWP → 구조화 데이터."""

from __future__ import annotations

from pathlib import Path

from app.ralph.parsers.base import ParsedFile, ParsedTable

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".pdf", ".docx", ".hwp", ".hwpx"}


def parse_file(file_path: str) -> ParsedFile:
    """확장자에 따라 적절한 파서를 선택하여 파일을 파싱한다."""
    ext = Path(file_path).suffix.lower()

    if ext in (".xlsx", ".xls"):
        from app.ralph.parsers.excel_parser import parse_excel

        return parse_excel(file_path)
    elif ext == ".pdf":
        from app.ralph.parsers.pdf_parser import parse_pdf

        return parse_pdf(file_path)
    elif ext == ".docx":
        from app.ralph.parsers.docx_parser import parse_docx

        return parse_docx(file_path)
    elif ext in (".hwp", ".hwpx"):
        from app.ralph.parsers.hwp_parser import parse_hwp

        return parse_hwp(file_path)
    else:
        return ParsedFile(
            source_path=file_path,
            file_type="unknown",
            parse_error=f"지원하지 않는 파일 형식: {ext}",
        )


__all__ = ["SUPPORTED_EXTENSIONS", "ParsedFile", "ParsedTable", "parse_file"]
