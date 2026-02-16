"""Auto-detect upload file type from Excel headers and sheet names.

Algorithm:
1. Read first row (headers) from each sheet
2. Normalize headers via HEADER_SYNONYMS
3. Score each UploadType by field signature overlap (0.7) + keyword match (0.3)
4. Return highest-scoring type with confidence
"""

from dataclasses import dataclass
from decimal import Decimal

from openpyxl import load_workbook

from app.models.upload import UploadType
from app.services.ingestion.header_map import (
    HEADER_SYNONYMS,
    TYPE_KEYWORDS,
    TYPE_SIGNATURES,
)


@dataclass
class DetectionResult:
    detected_type: UploadType | None
    confidence: Decimal | None
    all_scores: dict[str, float]
    normalized_headers: list[str]


def normalize_header(raw: str) -> str | None:
    """Normalize a raw header cell to a canonical field name."""
    if not raw:
        return None
    cleaned = str(raw).strip().lower().replace(" ", "_")
    # Try cleaned version first, then original stripped
    return HEADER_SYNONYMS.get(cleaned) or HEADER_SYNONYMS.get(str(raw).strip())


def detect_upload_type(file_path: str) -> DetectionResult:
    """Detect the upload type from an Excel file."""
    wb = load_workbook(file_path, read_only=True, data_only=True)

    best_type: str | None = None
    best_score = 0.0
    all_scores: dict[str, float] = {}
    best_headers: list[str] = []

    for sheet in wb.worksheets:
        raw_headers: list[str] = []
        for row in sheet.iter_rows(min_row=1, max_row=1, values_only=True):
            raw_headers = [str(cell) if cell is not None else "" for cell in row]
            break

        if not raw_headers:
            continue

        normalized = [normalize_header(h) for h in raw_headers]
        normalized_set = {h for h in normalized if h is not None}

        for type_name, signature_fields in TYPE_SIGNATURES.items():
            # Field overlap score
            overlap = normalized_set & signature_fields
            field_score = (
                len(overlap) / len(signature_fields) if signature_fields else 0.0
            )

            # Keyword score (sheet name + raw headers)
            keyword_score = 0.0
            sheet_name_lower = sheet.title.lower()
            for kw in TYPE_KEYWORDS.get(type_name, []):
                if kw in sheet_name_lower:
                    keyword_score = 1.0
                    break
                if any(kw in h.lower() for h in raw_headers if h):
                    keyword_score = 0.5
                    break

            score = field_score * 0.7 + keyword_score * 0.3
            all_scores[f"{sheet.title}:{type_name}"] = round(score, 4)

            if score > best_score:
                best_score = score
                best_type = type_name
                best_headers = [h for h in normalized if h is not None]

    wb.close()

    if best_type and best_score >= 0.3:
        return DetectionResult(
            detected_type=UploadType(best_type),
            confidence=Decimal(str(round(min(best_score, 1.0), 4))),
            all_scores=all_scores,
            normalized_headers=best_headers,
        )

    return DetectionResult(
        detected_type=None,
        confidence=None,
        all_scores=all_scores,
        normalized_headers=best_headers,
    )
