"""PDF 파서 — PyMuPDF(fitz) 또는 pdfplumber 기반 텍스트/표 추출."""

from __future__ import annotations

import io
import logging
import re

from app.ralph.parsers.base import ParsedFile, ParsedTable

logger = logging.getLogger(__name__)
_PDF_MIN_MEANINGFUL_TEXT_CHARS = 40
_OCR_RENDER_SCALE = 1.0


def get_pdf_ocr_status() -> dict[str, bool | str | None]:
    """Return the OCR fallback runtime status used by health checks."""
    try:
        import fitz  # noqa: F401
        import pytesseract
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        return {
            "enabled": False,
            "available": False,
            "required": False,
            "reason": str(exc),
        }

    try:
        version = str(pytesseract.get_tesseract_version())
    except Exception as exc:
        return {
            "enabled": True,
            "available": False,
            "required": False,
            "reason": str(exc),
        }

    return {
        "enabled": True,
        "available": True,
        "required": False,
        "reason": None,
        "engine": "pytesseract",
        "version": version,
    }


def parse_pdf(
    file_path: str,
    *,
    ocr_page_limit: int | None = None,
    ocr_char_limit: int | None = None,
) -> ParsedFile:
    """PDF 파일을 파싱한다. PyMuPDF 우선, fallback으로 pdfplumber."""
    best_candidate: ParsedFile | None = None
    try:
        candidate = _parse_with_fitz(file_path)
        best_candidate = _choose_better_pdf_candidate(best_candidate, candidate)
        if _parsed_pdf_has_meaningful_text(candidate):
            return candidate
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("PDF parse failed via fitz %s: %s", file_path, exc)

    try:
        candidate = _parse_with_pdfplumber(file_path)
        best_candidate = _choose_better_pdf_candidate(best_candidate, candidate)
        if _parsed_pdf_has_meaningful_text(candidate):
            return candidate
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("PDF parse failed via pdfplumber %s: %s", file_path, exc)

    ocr_candidate = _parse_with_ocr_fallback(
        file_path,
        base_candidate=best_candidate,
        ocr_page_limit=ocr_page_limit,
        ocr_char_limit=ocr_char_limit,
    )
    if ocr_candidate is not None and _parsed_pdf_has_meaningful_text(ocr_candidate):
        return ocr_candidate
    if best_candidate is not None:
        return best_candidate
    return ParsedFile(
        source_path=file_path,
        file_type="pdf",
        parse_error="PyMuPDF(fitz), pdfplumber, and OCR fallback could not extract text from the PDF.",
    )


def _parse_with_fitz(file_path: str) -> ParsedFile:
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    try:
        all_text: list[str] = []
        tables: list[ParsedTable] = []
        chunks: list[dict] = []
        page_count = len(doc)

        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                all_text.append(f"[페이지 {page_num}]")
                all_text.append(text)
                chunks.append(
                    {
                        "chunk_id": f"page-{page_num}",
                        "locator_type": "page",
                        "page": page_num,
                        "ordinal": page_num,
                        "text": text.strip(),
                    }
                )

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
            metadata={"page_count": page_count, "chunks": chunks},
        )
    finally:
        doc.close()


def _parse_with_pdfplumber(file_path: str) -> ParsedFile:
    import pdfplumber

    all_text: list[str] = []
    tables: list[ParsedTable] = []
    chunks: list[dict] = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                all_text.append(f"[페이지 {page_num}]")
                all_text.append(text)
                chunks.append(
                    {
                        "chunk_id": f"page-{page_num}",
                        "locator_type": "page",
                        "page": page_num,
                        "ordinal": page_num,
                        "text": text.strip(),
                    }
                )

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
        metadata={"page_count": len(pdf.pages), "chunks": chunks},
    )


def _parse_with_ocr_fallback(
    file_path: str,
    *,
    base_candidate: ParsedFile | None = None,
    ocr_page_limit: int | None = None,
    ocr_char_limit: int | None = None,
) -> ParsedFile | None:
    if base_candidate is not None and _parsed_pdf_has_meaningful_text(base_candidate):
        return base_candidate

    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
    except ImportError:
        return base_candidate
    except Exception as exc:
        logger.warning("PDF OCR fallback unavailable %s: %s", file_path, exc)
        return base_candidate

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        logger.warning("PDF OCR fallback open failed %s: %s", file_path, exc)
        return base_candidate

    try:
        all_text: list[str] = []
        chunks: list[dict] = []
        ocr_languages = "kor+eng"
        collected_chars = 0
        for page_num in _select_ocr_page_numbers(len(doc), ocr_page_limit):
            if ocr_char_limit is not None and collected_chars >= ocr_char_limit:
                break
            page = doc[page_num - 1]
            pix = page.get_pixmap(
                matrix=fitz.Matrix(_OCR_RENDER_SCALE, _OCR_RENDER_SCALE),
                alpha=False,
            )
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text = (pytesseract.image_to_string(image, lang=ocr_languages) or "").strip()
            if not text:
                continue

            all_text.append(f"[OCR Page {page_num}]")
            all_text.append(text)
            chunks.append(
                {
                    "chunk_id": f"ocr-page-{page_num}",
                    "locator_type": "page",
                    "page": page_num,
                    "ordinal": page_num,
                    "text": text,
                    "ocr_used": True,
                }
            )
            collected_chars += len(text)

        if not all_text:
            return base_candidate

        metadata = dict((base_candidate.metadata if base_candidate else {}) or {})
        metadata.update(
            {
                "page_count": len(doc),
                "chunks": chunks,
                "ocr_used": True,
                "ocr_engine": "pytesseract",
                "ocr_languages": ocr_languages,
            }
        )
        return ParsedFile(
            source_path=file_path,
            file_type="pdf",
            text="\n".join(all_text),
            tables=list((base_candidate.tables if base_candidate else []) or []),
            metadata=metadata,
            ddrl_sections=list((base_candidate.ddrl_sections if base_candidate else []) or []),
        )
    except Exception as exc:
        logger.warning("PDF OCR fallback failed %s: %s", file_path, exc)
        return base_candidate
    finally:
        doc.close()


def _parsed_pdf_has_meaningful_text(parsed: ParsedFile | None) -> bool:
    if parsed is None:
        return False
    if parsed.tables:
        return True
    normalized_text = re.sub(r"\[[^\]]+\]", " ", parsed.text or "")
    normalized_text = re.sub(r"\s+", " ", normalized_text).strip()
    return len(normalized_text) >= _PDF_MIN_MEANINGFUL_TEXT_CHARS


def _choose_better_pdf_candidate(current: ParsedFile | None, candidate: ParsedFile | None) -> ParsedFile | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    current_score = _pdf_candidate_score(current)
    candidate_score = _pdf_candidate_score(candidate)
    return candidate if candidate_score >= current_score else current


def _pdf_candidate_score(parsed: ParsedFile) -> int:
    normalized_text = re.sub(r"\[[^\]]+\]", " ", parsed.text or "")
    normalized_text = re.sub(r"\s+", " ", normalized_text).strip()
    table_bonus = 200 * len(parsed.tables or [])
    return len(normalized_text) + table_bonus


def _select_ocr_page_numbers(total_pages: int, page_limit: int | None) -> list[int]:
    if total_pages <= 0:
        return []
    if page_limit is None or page_limit >= total_pages:
        return list(range(1, total_pages + 1))
    if page_limit <= 2:
        return list(range(1, page_limit + 1))

    head_count = max(1, page_limit - 2)
    tail_count = page_limit - head_count
    pages: list[int] = list(range(1, min(head_count, total_pages) + 1))

    for page_num in range(max(1, total_pages - tail_count + 1), total_pages + 1):
        if page_num not in pages:
            pages.append(page_num)

    return pages[:page_limit]
