"""PDF parsing with native extraction and optional OCR fallback."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.ralph.parsers.base import ParsedFile, ParsedTable

logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> ParsedFile:
    """Parse a PDF with native extraction first, then OCR when needed."""
    errors: list[str] = []
    native_result = _try_native_parser(_parse_with_fitz, file_path, errors)
    if _has_meaningful_text(native_result):
        return native_result

    plumber_result = _try_native_parser(_parse_with_pdfplumber, file_path, errors)
    if _has_meaningful_text(plumber_result):
        return plumber_result

    merged_native = _merge_native_results(native_result, plumber_result)
    ocr_result = _parse_with_ocr_if_available(file_path)
    if _has_meaningful_text(ocr_result):
        return _merge_ocr_with_native(merged_native, ocr_result)

    if merged_native is not None:
        if _needs_strict_ocr_failure(merged_native):
            status = get_pdf_ocr_status()
            merged_native.parse_error = (
                merged_native.parse_error
                or f"Scanned PDF OCR is required but unavailable: {status['reason']}"
            )
        return merged_native

    parse_error = "; ".join(errors) if errors else "Unable to parse PDF content."
    return ParsedFile(
        source_path=file_path,
        file_type="pdf",
        parse_error=parse_error,
    )


def get_pdf_ocr_status() -> dict[str, Any]:
    """Return OCR runtime readiness for health checks and startup logging."""
    status = dict(_cached_pdf_ocr_status())
    status["enabled"] = bool(settings.OCR_ENABLED)
    status["required"] = bool(settings.OCR_REQUIRE_FOR_SCANNED_PDF)
    status["engine"] = settings.OCR_ENGINE
    status["languages"] = settings.OCR_LANGUAGES
    status["binary"] = settings.TESSERACT_CMD or None
    return status


def _parse_with_fitz(file_path: str) -> ParsedFile:
    import fitz

    doc = fitz.open(file_path)
    try:
        all_text: list[str] = []
        tables: list[ParsedTable] = []
        chunks: list[dict[str, Any]] = []
        page_count = len(doc)

        for page_num, page in enumerate(doc, 1):
            text = page.get_text() or ""
            if text.strip():
                all_text.append(f"[Page {page_num}]")
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

            try:
                page_tables = page.find_tables()
                for table in page_tables:
                    data = table.extract()
                    if data:
                        tables.append(
                            ParsedTable(
                                headers=data[0] if data else [],
                                rows=data[1:] if len(data) > 1 else [],
                            )
                        )
            except Exception:
                pass

        return ParsedFile(
            source_path=file_path,
            file_type="pdf",
            text="\n".join(all_text),
            tables=tables,
            metadata={"page_count": page_count, "chunks": chunks, "ocr_used": False},
        )
    finally:
        doc.close()


def _parse_with_pdfplumber(file_path: str) -> ParsedFile:
    import pdfplumber

    all_text: list[str] = []
    tables: list[ParsedTable] = []
    chunks: list[dict[str, Any]] = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                all_text.append(f"[Page {page_num}]")
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

            for table in page.extract_tables():
                if table:
                    rows = [[str(cell) if cell else "" for cell in row] for row in table]
                    tables.append(
                        ParsedTable(
                            headers=rows[0] if rows else [],
                            rows=rows[1:] if len(rows) > 1 else [],
                        )
                    )

        return ParsedFile(
            source_path=file_path,
            file_type="pdf",
            text="\n".join(all_text),
            tables=tables,
            metadata={"page_count": len(pdf.pages), "chunks": chunks, "ocr_used": False},
        )


def _parse_with_ocr(file_path: str) -> ParsedFile:
    import fitz
    import pytesseract
    from PIL import Image

    _configure_tesseract_binary(pytesseract)

    doc = fitz.open(file_path)
    try:
        all_text: list[str] = []
        chunks: list[dict[str, Any]] = []
        page_count = len(doc)
        matrix = fitz.Matrix(2, 2)

        for page_num, page in enumerate(doc, 1):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            text = pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGES or None).strip()
            if not text:
                continue

            all_text.append(f"[Page {page_num}]")
            all_text.append(text)
            chunks.append(
                {
                    "chunk_id": f"page-{page_num}",
                    "locator_type": "page",
                    "page": page_num,
                    "ordinal": page_num,
                    "text": text,
                }
            )

        return ParsedFile(
            source_path=file_path,
            file_type="pdf",
            text="\n".join(all_text),
            tables=[],
            metadata={"page_count": page_count, "chunks": chunks, "ocr_used": True},
        )
    finally:
        doc.close()


def _try_native_parser(parser: Any, file_path: str, errors: list[str]) -> ParsedFile | None:
    try:
        return parser(file_path)
    except ImportError as exc:
        errors.append(str(exc))
    except Exception as exc:
        logger.warning("PDF native parse failed for %s via %s: %s", file_path, parser.__name__, exc)
        errors.append(str(exc))
    return None


def _parse_with_ocr_if_available(file_path: str) -> ParsedFile | None:
    status = get_pdf_ocr_status()
    if not status["enabled"] or not status["available"]:
        return None

    try:
        return _parse_with_ocr(file_path)
    except Exception as exc:
        logger.warning("PDF OCR parse failed for %s: %s", file_path, exc)
        return None


def _merge_native_results(primary: ParsedFile | None, secondary: ParsedFile | None) -> ParsedFile | None:
    if primary is None:
        return secondary
    if secondary is None:
        return primary

    primary_text = primary.text or ""
    secondary_text = secondary.text or ""
    if len(secondary_text.strip()) > len(primary_text.strip()):
        chosen = secondary
        fallback = primary
    else:
        chosen = primary
        fallback = secondary

    metadata = dict(fallback.metadata or {})
    metadata.update(chosen.metadata or {})
    metadata["ocr_used"] = bool(metadata.get("ocr_used"))
    chosen.metadata = metadata
    if not chosen.tables and fallback.tables:
        chosen.tables = fallback.tables
    return chosen


def _merge_ocr_with_native(native_result: ParsedFile | None, ocr_result: ParsedFile) -> ParsedFile:
    if native_result is None:
        return ocr_result

    metadata = dict(native_result.metadata or {})
    metadata.update(ocr_result.metadata or {})
    metadata["ocr_used"] = True
    return ParsedFile(
        source_path=ocr_result.source_path,
        file_type="pdf",
        text=ocr_result.text or native_result.text,
        tables=native_result.tables or ocr_result.tables,
        metadata=metadata,
        ddrl_sections=native_result.ddrl_sections or ocr_result.ddrl_sections,
        parse_error=None,
    )


def _has_meaningful_text(parsed: ParsedFile | None) -> bool:
    return bool(parsed and (parsed.text or "").strip())


def _needs_strict_ocr_failure(parsed: ParsedFile) -> bool:
    status = get_pdf_ocr_status()
    return bool(
        settings.OCR_ENABLED
        and settings.OCR_REQUIRE_FOR_SCANNED_PDF
        and not _has_meaningful_text(parsed)
        and not status["available"]
    )


def _configure_tesseract_binary(pytesseract_module: Any) -> None:
    if settings.TESSERACT_CMD:
        pytesseract_module.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


@lru_cache(maxsize=1)
def _cached_pdf_ocr_status() -> dict[str, Any]:
    if not settings.OCR_ENABLED:
        return {"available": False, "reason": "disabled by settings"}
    if settings.OCR_ENGINE.lower() != "tesseract":
        return {"available": False, "reason": f"unsupported OCR engine: {settings.OCR_ENGINE}"}

    try:
        import pytesseract
    except ImportError:
        return {"available": False, "reason": "pytesseract is not installed"}

    try:
        _configure_tesseract_binary(pytesseract)
        version = str(pytesseract.get_tesseract_version())
    except Exception as exc:
        return {"available": False, "reason": str(exc)}

    return {"available": True, "reason": "ok", "version": version}
