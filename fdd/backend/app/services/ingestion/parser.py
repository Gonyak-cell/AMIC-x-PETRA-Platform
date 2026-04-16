"""Excel parser with chunked DB insertion.

Streams rows using openpyxl read_only mode for O(1) memory per row.
Commits in batches of BATCH_SIZE rows for performance.
Sprint 14: structured logging added.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.core.log_decorators import log_error_with_input
from app.core.logging import get_logger
from app.models.journal_entry import JournalEntry
from app.models.upload import UploadFile, UploadType
from app.services.ingestion.type_detector import find_header_row

logger = get_logger(__name__)

BATCH_SIZE = 5000

CORE_FIELDS = {
    "account_code",
    "account_name",
    "entry_date",
    "description",
    "currency",
    "debit",
    "credit",
    "balance",
    "amount",
    "entry_id",
    "line_id",
    "counterparty",
}


@dataclass
class IngestionResult:
    total_rows: int
    rows_processed: int
    rows_skipped: int


def safe_decimal(value: object) -> Decimal | None:
    """Convert a cell value to Decimal. float ??str ??Decimal to avoid precision loss."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace(" ", "").strip()
        if not cleaned or cleaned == "-":
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def safe_date(value: object) -> date | None:
    """Convert a cell value to a date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def safe_str(value: object) -> str | None:
    """Convert a cell value to a stripped string, or None if empty."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


@log_error_with_input
def ingest_file(
    db: Session,
    upload: UploadFile,
    effective_type: UploadType,
    *,
    user_period_date: date | None = None,
    deal_period_end: date | None = None,
) -> IngestionResult:
    """Parse Excel and insert rows into journal_entry table.

    Args:
        user_period_date: 사용자가 직접 지정한 TB 기간 (최우선 적용).
        deal_period_end: Deal.reference_date (period detection 폴백).
    """
    from app.services.ingestion.period_extractor import detect_tb_period

    logger.info(
        "Ingestion started",
        extra={
            "ctx": {
                "upload_id": str(upload.id),
                "deal_id": str(upload.deal_id),
                "filename": upload.original_filename,
                "type": effective_type.value,
            }
        },
    )

    wb = load_workbook(upload.stored_path, read_only=True, data_only=True)
    sheet = wb.active

    # Read and normalize headers
    header_row_idx, raw_headers, normalized = find_header_row(sheet)

    # Build column index map: canonical_name -> column_index (first occurrence wins)
    col_map: dict[str, int] = {}
    for idx, name in enumerate(normalized):
        if name and name not in col_map:
            col_map[name] = idx

    mapped_fields = [k for k in col_map if k in CORE_FIELDS]
    logger.info(
        "Headers mapped",
        extra={
            "ctx": {
                "upload_id": str(upload.id),
                "total_columns": len(raw_headers),
                "mapped_fields": mapped_fields,
            }
        },
    )

    # TB 파일의 기간 자동 탐지
    detected_period = None
    if effective_type == UploadType.TB:
        detected_period = detect_tb_period(
            filename=upload.original_filename,
            sheet_name=sheet.title if sheet.title else "",
            headers=raw_headers,
            deal_period_end=deal_period_end,
            user_period_date=user_period_date,
        )
        if detected_period:
            logger.info(
                "TB period detected",
                extra={
                    "ctx": {
                        "upload_id": str(upload.id),
                        "period_date": str(detected_period.period_date),
                        "source": detected_period.source,
                        "confidence": str(detected_period.confidence),
                    }
                },
            )

    total_rows = 0
    rows_processed = 0
    rows_skipped = 0
    batch: list[JournalEntry] = []

    for row in sheet.iter_rows(min_row=header_row_idx + 1, values_only=True):
        total_rows += 1

        # Skip completely empty rows
        if all(cell is None or str(cell).strip() == "" for cell in row):
            rows_skipped += 1
            continue

        def get_val(field: str, _row: tuple[object, ...] = row) -> object:
            idx = col_map.get(field)
            if idx is None or idx >= len(_row):
                return None
            return _row[idx]

        # Build extra_data for unmapped columns
        extra: dict[str, str] = {}
        for name, idx in col_map.items():
            if name not in CORE_FIELDS and idx < len(row) and row[idx] is not None:
                extra[name] = str(row[idx])

        entry_date = safe_date(get_val("entry_date"))
        if entry_date is None and detected_period is not None:
            entry_date = detected_period.period_date

        entry = JournalEntry(
            upload_file_id=upload.id,
            deal_id=upload.deal_id,
            source_type=effective_type.value,
            row_number=header_row_idx + total_rows,
            account_code=safe_str(get_val("account_code")),
            account_name=safe_str(get_val("account_name")),
            entry_date=entry_date,
            description=safe_str(get_val("description")),
            currency=safe_str(get_val("currency")),
            debit=safe_decimal(get_val("debit")),
            credit=safe_decimal(get_val("credit")),
            balance=safe_decimal(get_val("balance")),
            amount=safe_decimal(get_val("amount")),
            entry_id=safe_str(get_val("entry_id")),
            line_id=safe_str(get_val("line_id")),
            counterparty=safe_str(get_val("counterparty")),
            extra_data=extra if extra else None,
        )
        batch.append(entry)
        rows_processed += 1

        # Batch commit
        if len(batch) >= BATCH_SIZE:
            db.add_all(batch)
            db.flush()
            upload.rows_processed = rows_processed
            db.flush()
            batch = []
            logger.info(
                "Batch committed",
                extra={
                    "ctx": {
                        "upload_id": str(upload.id),
                        "rows_processed": rows_processed,
                    }
                },
            )

    # Final batch
    if batch:
        db.add_all(batch)
        db.flush()

    upload.rows_processed = rows_processed
    db.flush()

    wb.close()

    logger.info(
        "Ingestion completed",
        extra={
            "ctx": {
                "upload_id": str(upload.id),
                "deal_id": str(upload.deal_id),
                "total_rows": total_rows,
                "rows_processed": rows_processed,
                "rows_skipped": rows_skipped,
            }
        },
    )

    return IngestionResult(
        total_rows=total_rows,
        rows_processed=rows_processed,
        rows_skipped=rows_skipped,
    )
