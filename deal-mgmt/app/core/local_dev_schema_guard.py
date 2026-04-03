from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOWED_SQLITE_ROOTS = (PROJECT_ROOT,)
REQUIRED_MARKETING_MATERIAL_COLUMNS = frozenset({"source_mode", "attachment_id"})
REQUIRED_ATTACHMENT_COLUMNS = frozenset({"processing_status", "processing_error"})
LOCAL_DEV_ENTRYPOINT_HINT = (
    "Restart the MA backend via python deal-mgmt/scripts/run_dev_server.py "
    "or scripts/start-platform-dev-stack.ps1 so the local dev database can be rebuilt."
)
BACKEND_ATTACHMENT_PROCESSING_SCHEMA_HINT = (
    "MA backend database is missing attachment processing columns. "
    "Run alembic upgrade head for deal-mgmt and restart the backend."
)
VALID_ATTACHMENT_PROCESSING_STATUSES = frozenset({"PENDING", "RUNNING", "SYNCED", "FAILED", "SKIPPED"})


@dataclass(frozen=True)
class LocalSQLiteSchemaGuardResult:
    database_path: Path | None
    rebuild_reason: str | None
    rebuilt: bool = False


@dataclass(frozen=True)
class AttachmentProcessingSchemaRepairResult:
    missing_columns: tuple[str, ...] = ()
    repaired: bool = False


def configure_sqlite_type_compilers_for_local_dev() -> None:
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
    SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "CHAR(36)"


def is_file_based_sqlite_database_url(database_url: str | None) -> bool:
    if not database_url:
        return False

    try:
        url = make_url(database_url)
    except Exception:
        return False

    database_name = url.database
    return url.get_backend_name() == "sqlite" and bool(database_name and database_name != ":memory:")


def _normalize_sqlite_database_path(raw_database_path: str) -> Path:
    normalized = raw_database_path
    if len(normalized) >= 3 and normalized[0] == "/" and normalized[2] == ":":
        normalized = normalized[1:]

    db_path = Path(normalized).expanduser()
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()
    else:
        db_path = db_path.resolve()
    return db_path


def _normalize_allowed_roots(allowed_roots: Iterable[Path] | None) -> tuple[Path, ...]:
    roots = tuple(allowed_roots or DEFAULT_ALLOWED_SQLITE_ROOTS)
    return tuple(root.expanduser().resolve() for root in roots)


def resolve_local_sqlite_database_path(
    database_url: str | None,
    *,
    allowed_roots: Iterable[Path] | None = None,
) -> Path | None:
    if not is_file_based_sqlite_database_url(database_url):
        return None

    try:
        url = make_url(database_url)
    except Exception:
        return None

    db_path = _normalize_sqlite_database_path(url.database or "")
    roots = _normalize_allowed_roots(allowed_roots)
    if not any(db_path.is_relative_to(root) for root in roots):
        return None
    return db_path


def _get_sqlite_tables(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'",
        ).fetchall()
    }


def _get_sqlite_columns(conn: sqlite3.Connection, table_name: str) -> dict[str, tuple]:
    return {row[1]: row for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def get_local_dev_rebuild_reason(db_path: Path) -> str | None:
    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path)
    try:
        tables = _get_sqlite_tables(conn)
        if "marketing_materials" in tables:
            marketing_columns = set(_get_sqlite_columns(conn, "marketing_materials"))
            missing_marketing_columns = sorted(REQUIRED_MARKETING_MATERIAL_COLUMNS - marketing_columns)
            if missing_marketing_columns:
                return f"marketing_materials is missing required columns: {', '.join(missing_marketing_columns)}"

        if "attachments" in tables:
            attachment_columns = set(_get_sqlite_columns(conn, "attachments"))
            missing_attachment_columns = sorted(REQUIRED_ATTACHMENT_COLUMNS - attachment_columns)
            if missing_attachment_columns:
                return f"attachments is missing required columns: {', '.join(missing_attachment_columns)}"

        if "ndas" in tables:
            nda_columns = _get_sqlite_columns(conn, "ndas")
            buyer_candidate = nda_columns.get("buyer_candidate_id")
            buyer_candidate_not_null = bool(buyer_candidate and buyer_candidate[3])
            if "party_type" not in nda_columns or buyer_candidate_not_null:
                return "ndas table uses a legacy schema that cannot be repaired safely"
    finally:
        conn.close()

    return None


def rebuild_local_dev_database_if_needed(
    db_path: Path,
    *,
    logger: logging.Logger | None = None,
) -> str | None:
    rebuild_reason = get_local_dev_rebuild_reason(db_path)
    if not rebuild_reason:
        return None

    active_logger = logger or logging.getLogger(__name__)
    active_logger.warning(
        "Rebuilding stale local SQLite dev database %s: %s",
        db_path,
        rebuild_reason,
    )
    db_path.unlink(missing_ok=True)
    return rebuild_reason


def guard_local_sqlite_database_url(
    database_url: str | None,
    *,
    allowed_roots: Iterable[Path] | None = None,
    logger: logging.Logger | None = None,
) -> LocalSQLiteSchemaGuardResult:
    db_path = resolve_local_sqlite_database_path(database_url, allowed_roots=allowed_roots)
    if db_path is None:
        return LocalSQLiteSchemaGuardResult(database_path=None, rebuild_reason=None, rebuilt=False)

    rebuild_reason = rebuild_local_dev_database_if_needed(db_path, logger=logger)
    return LocalSQLiteSchemaGuardResult(
        database_path=db_path,
        rebuild_reason=rebuild_reason,
        rebuilt=rebuild_reason is not None,
    )


def is_attachment_processing_schema_error(exc: Exception) -> bool:
    if not isinstance(exc, (OperationalError, ProgrammingError)):
        return False

    parts = [str(exc).lower()]
    orig = getattr(exc, "orig", None)
    if orig is not None:
        parts.append(str(orig).lower())
    message = " ".join(parts)

    has_missing_column = "has no column named" in message or "no such column" in message or "does not exist" in message
    targets_attachment_processing_columns = "attachments" in message and (
        "processing_status" in message or "processing_error" in message
    )
    return has_missing_column and targets_attachment_processing_columns


def is_local_sqlite_attachment_processing_schema_error(
    exc: Exception,
    *,
    database_url: str | None,
) -> bool:
    return is_file_based_sqlite_database_url(database_url) and is_attachment_processing_schema_error(exc)


def _get_missing_attachment_processing_columns(sync_conn) -> tuple[str, ...]:
    inspector = inspect(sync_conn)
    if "attachments" not in set(inspector.get_table_names()):
        return ()

    existing_columns = {column["name"] for column in inspector.get_columns("attachments")}
    return tuple(sorted(REQUIRED_ATTACHMENT_COLUMNS - existing_columns))


async def repair_attachment_processing_schema_if_needed(
    *,
    database_url: str | None,
    engine_override=None,
    logger: logging.Logger | None = None,
) -> AttachmentProcessingSchemaRepairResult:
    from app.core.database import engine as default_engine

    if resolve_local_sqlite_database_path(database_url) is not None:
        return AttachmentProcessingSchemaRepairResult()

    active_logger = logger or logging.getLogger(__name__)
    active_engine = engine_override or default_engine

    try:
        async with active_engine.begin() as conn:
            missing_columns = await conn.run_sync(_get_missing_attachment_processing_columns)
            if not missing_columns:
                return AttachmentProcessingSchemaRepairResult()

            active_logger.warning(
                "Repairing missing attachment processing columns on backend database: %s",
                ", ".join(missing_columns),
            )

            if "processing_status" in missing_columns:
                await conn.execute(
                    text(
                        """
                        ALTER TABLE attachments
                        ADD COLUMN processing_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                        """
                    )
                )

            if "processing_error" in missing_columns:
                await conn.execute(
                    text(
                        """
                        ALTER TABLE attachments
                        ADD COLUMN processing_error TEXT
                        """
                    )
                )

            valid_statuses = ", ".join(f"'{status}'" for status in sorted(VALID_ATTACHMENT_PROCESSING_STATUSES))
            where_clause = ""
            if "processing_status" not in missing_columns:
                where_clause = f"""
                    WHERE processing_status IS NULL
                       OR TRIM(processing_status) = ''
                       OR UPPER(TRIM(processing_status)) NOT IN ({valid_statuses})
                """
            await conn.execute(
                text(
                    f"""
                    UPDATE attachments
                    SET processing_status = CASE
                        WHEN vdr_document_id IS NOT NULL THEN 'SYNCED'
                        WHEN entity_type = 'MARKETING_MATERIAL' THEN 'SKIPPED'
                        ELSE 'PENDING'
                    END
                    {where_clause}
                    """
                )
            )

            remaining_missing_columns = await conn.run_sync(_get_missing_attachment_processing_columns)
    except Exception:
        active_logger.exception("Attachment processing schema repair failed")
        return AttachmentProcessingSchemaRepairResult(
            missing_columns=missing_columns if "missing_columns" in locals() else (),
            repaired=False,
        )

    return AttachmentProcessingSchemaRepairResult(
        missing_columns=missing_columns,
        repaired=not remaining_missing_columns,
    )


def build_local_sqlite_rebuild_required_detail(*, stage: str) -> str:
    return (
        f"Uploaded marketing material failed during {stage}. "
        "Local SQLite dev database is stale and missing attachment processing columns. "
        f"{LOCAL_DEV_ENTRYPOINT_HINT}"
    )


def build_backend_attachment_processing_schema_required_detail(*, stage: str) -> str:
    return f"Uploaded marketing material failed during {stage}. {BACKEND_ATTACHMENT_PROCESSING_SCHEMA_HINT}"
