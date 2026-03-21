"""PDF 파서 — PyMuPDF(fitz) 또는 pdfplumber 기반 텍스트/표 추출."""

from __future__ import annotations

import logging

from app.ralph.parsers.base import ParsedFile, ParsedTable

logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> ParsedFile:
    """PDF 파일을 파싱한다. PyMuPDF 우선, fallback으로 pdfplumber."""
    try:
        return _parse_with_fitz(file_path)
    except ImportError:
        pass

    try:
        return _parse_with_pdfplumber(file_path)
    except ImportError:
        return ParsedFile(
            source_path=file_path,
            file_type="pdf",
            parse_error="PyMuPDF(fitz) 또는 pdfplumber가 설치되지 않았습니다",
        )
    except Exception as exc:
        logger.warning("PDF 파싱 실패 %s: %s", file_path, exc)
        return ParsedFile(
            source_path=file_path,
            file_type="pdf",
            parse_error=str(exc),
        )


def _parse_with_fitz(file_path: str) -> ParsedFile:
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    try:
        all_text: list[str] = []
        tables: list[ParsedTable] = []
        page_count = len(doc)

        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                all_text.append(f"[페이지 {page_num}]")
                all_text.append(text)

            # 표 추출 시도 (PyMuPDF 1.23+)
            try:
                page_tables = page.find_tables()
                for t in page_tables:
                    data = t.extract()
                    if data:
                        tables.append(
                            ParsedTable(
                                headers=data[0] if data else [],
                                rows=data[1:] if len(data) > 1 else [],
                            )
                        )
            except Exception:
                pass  # 표 추출 미지원 버전

        return ParsedFile(
            source_path=file_path,
            file_type="pdf",
            text="\n".join(all_text),
            tables=tables,
            metadata={"page_count": page_count},
        )
    finally:
        doc.close()


def _parse_with_pdfplumber(file_path: str) -> ParsedFile:
    import pdfplumber

    all_text: list[str] = []
    tables: list[ParsedTable] = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                all_text.append(f"[페이지 {page_num}]")
                all_text.append(text)

            for t in page.extract_tables():
                if t:
                    str_rows = [[str(c) if c else "" for c in row] for row in t]
                    tables.append(
                        ParsedTable(
                            headers=str_rows[0] if str_rows else [],
                            rows=str_rows[1:] if len(str_rows) > 1 else [],
                        )
                    )

    return ParsedFile(
        source_path=file_path,
        file_type="pdf",
        text="\n".join(all_text),
        tables=tables,
        metadata={"page_count": len(all_text)},
    )
