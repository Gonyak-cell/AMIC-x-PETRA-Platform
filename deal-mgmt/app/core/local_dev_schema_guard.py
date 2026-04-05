from __future__ import annotations

import logging
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOWED_SQLITE_ROOTS = (PROJECT_ROOT,)
UPLOAD_SCHEMA_MANIFEST: dict[str, frozenset[str]] = {
    "attachments": frozenset(
        {
            "description",
            "entity_id",
            "uploaded_by_email",
            "vdr_document_id",
            "processing_status",
            "processing_error",
        }
    ),
    "marketing_materials": frozenset({"source_mode", "attachment_id"}),
}
REQUIRED_MARKETING_MATERIAL_COLUMNS = UPLOAD_SCHEMA_MANIFEST["marketing_materials"]
REQUIRED_ATTACHMENT_COLUMNS = UPLOAD_SCHEMA_MANIFEST["attachments"]
AUTO_REPAIRABLE_UPLOAD_COLUMNS = frozenset(
    {
        ("attachments", "description"),
        ("attachments", "entity_id"),
        ("attachments", "uploaded_by_email"),
        ("attachments", "vdr_document_id"),
        ("attachments", "processing_status"),
        ("attachments", "processing_error"),
        ("marketing_materials", "source_mode"),
        ("marketing_materials", "attachment_id"),
    }
)
AUTO_REPAIRABLE_UPLOAD_TYPE_COLUMNS = frozenset({("attachments", "entity_id")})
UPLOAD_SCHEMA_TYPE_EXPECTATIONS: dict[tuple[str, str], str] = {
    ("attachments", "entity_id"): "VARCHAR(50)",
}
UPLOAD_SCHEMA_COLUMN_TABLES: dict[str, tuple[str, ...]] = {}
for _table_name, _column_names in UPLOAD_SCHEMA_MANIFEST.items():
    for _column_name in _column_names:
        UPLOAD_SCHEMA_COLUMN_TABLES.setdefault(_column_name, ())
        UPLOAD_SCHEMA_COLUMN_TABLES[_column_name] = tuple(
            sorted({*UPLOAD_SCHEMA_COLUMN_TABLES[_column_name], _table_name})
        )

LOCAL_DEV_ENTRYPOINT_HINT = (
    "Restart the MA backend via python deal-mgmt/scripts/run_dev_server.py "
    "or scripts/start-platform-dev-stack.ps1 so the local dev database can be rebuilt."
)
BACKEND_ATTACHMENT_UPLOAD_SCHEMA_HINT = (
    "MA backend database is missing uploaded marketing material schema. "
    "Run alembic upgrade head for deal-mgmt and restart the backend."
)
BACKEND_ATTACHMENT_PROCESSING_SCHEMA_HINT = BACKEND_ATTACHMENT_UPLOAD_SCHEMA_HINT
VALID_ATTACHMENT_PROCESSING_STATUSES = frozenset({"PENDING", "RUNNING", "SYNCED", "FAILED", "SKIPPED"})
MISSING_COLUMN_SQLSTATES = frozenset({"42703"})
INCOMPATIBLE_TYPE_SQLSTATES = frozenset({"42804"})
UPLOAD_SCHEMA_ERROR_PATTERNS = (
    re.compile(
        r'table\s+"?(?P<table>[a-z_][a-z0-9_]*)"?\s+has no column named\s+"?(?P<column>[a-z_][a-z0-9_]*)"?',
        re.IGNORECASE,
    ),
    re.compile(
        r'column\s+"?(?P<column>[a-z_][a-z0-9_]*)"?\s+of relation\s+"?(?P<table>[a-z_][a-z0-9_]*)"?\s+does not exist',
        re.IGNORECASE,
    ),
    re.compile(
        r'no such column:\s+(?:(?P<table>[a-z_][a-z0-9_]*)\.)?"?(?P<column>[a-z_][a-z0-9_]*)"?',
        re.IGNORECASE,
    ),
    re.compile(
        r'column\s+(?:(?P<table>[a-z_][a-z0-9_]*)\.)?"?(?P<column>[a-z_][a-z0-9_]*)"?\s+does not exist',
        re.IGNORECASE,
    ),
)
UPLOAD_SCHEMA_TYPE_ERROR_PATTERNS = (
    re.compile(
        r'column\s+"?(?P<column>[a-z_][a-z0-9_]*)"?\s+is of type\s+(?P<actual_type>[a-z0-9_ ()]+)\s+but expression is of type\s+(?P<expression_type>[a-z0-9_ ()]+)',
        re.IGNORECASE,
    ),
)
STATEMENT_TABLE_PATTERN = re.compile(
    r'\b(?:insert\s+into|update|from|join)\s+(?:"?[a-z_][a-z0-9_]*"?\.)?"?(?P<table>[a-z_][a-z0-9_]*)"?',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LocalSQLiteSchemaGuardResult:
    database_path: Path | None
    rebuild_reason: str | None
    rebuilt: bool = False


@dataclass(frozen=True)
class AttachmentUploadSchemaIssue:
    table: str
    column: str
    reason: str
    repairable: bool
    expected_type: str | None = None
    actual_type: str | None = None

    @property
    def qualified_column(self) -> str:
        return f"{self.table}.{self.column}"


@dataclass(frozen=True)
class AttachmentUploadSchemaRepairResult:
    issues: tuple[AttachmentUploadSchemaIssue, ...] = ()
    repaired: bool = False
    repair_attempted: bool = False

    @property
    def missing_columns(self) -> tuple[str, ...]:
        return tuple(sorted(issue.column for issue in self.issues))

    @property
    def qualified_missing_columns(self) -> tuple[str, ...]:
        return tuple(sorted(issue.qualified_column for issue in self.issues))

    @property
    def qualified_schema_elements(self) -> tuple[str, ...]:
        return tuple(sorted(issue.qualified_column for issue in self.issues))

    @property
    def repairable_issues(self) -> tuple[AttachmentUploadSchemaIssue, ...]:
        return tuple(issue for issue in self.issues if issue.repairable)

    @property
    def ok(self) -> bool:
        return not self.issues


AttachmentProcessingSchemaRepairResult = AttachmentUploadSchemaRepairResult


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


def _build_schema_issue(table: str, column: str, *, reason: str) -> AttachmentUploadSchemaIssue | None:
    normalized_table = table.strip().strip('"').strip("'").lower()
    normalized_column = column.strip().strip('"').strip("'").lower()
    if normalized_table not in UPLOAD_SCHEMA_MANIFEST:
        return None
    if normalized_column not in UPLOAD_SCHEMA_MANIFEST[normalized_table]:
        return None
    repairable = False
    if reason == "missing_column":
        repairable = (normalized_table, normalized_column) in AUTO_REPAIRABLE_UPLOAD_COLUMNS
    elif reason == "incompatible_type":
        repairable = (normalized_table, normalized_column) in AUTO_REPAIRABLE_UPLOAD_TYPE_COLUMNS
    return AttachmentUploadSchemaIssue(
        table=normalized_table,
        column=normalized_column,
        reason=reason,
        repairable=repairable,
        expected_type=UPLOAD_SCHEMA_TYPE_EXPECTATIONS.get((normalized_table, normalized_column)),
    )


def _render_column_type(column_type: object | None) -> str | None:
    if column_type is None:
        return None
    rendered = str(column_type).strip()
    if rendered:
        return rendered
    return column_type.__class__.__name__


def _load_postgres_column_type(sync_conn, *, table: str, column: str) -> str | None:
    query = text(
        """
        SELECT format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute AS a
        JOIN pg_class AS c ON c.oid = a.attrelid
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = current_schema()
          AND c.relname = :table_name
          AND a.attname = :column_name
          AND a.attnum > 0
          AND NOT a.attisdropped
        """
    )
    return sync_conn.execute(query, {"table_name": table, "column_name": column}).scalar_one_or_none()


def _has_expected_upload_column_type(
    *,
    table: str,
    column: str,
    column_type: object | None,
    dialect_name: str,
    sync_conn=None,
) -> bool:
    if (table, column) == ("attachments", "entity_id"):
        if dialect_name == "postgresql":
            actual_type = _load_postgres_column_type(sync_conn, table=table, column=column) if sync_conn else None
            return (actual_type or "").strip().lower() == "character varying(50)"
        return True
    return True


def _infer_statement_table(statement: str | None) -> str | None:
    if not statement:
        return None
    match = STATEMENT_TABLE_PATTERN.search(statement.lower())
    if not match:
        return None
    table_name = match.group("table")
    if table_name not in UPLOAD_SCHEMA_MANIFEST:
        return None
    return table_name


def _infer_table_for_upload_column(column: str, *, statement: str | None = None) -> str | None:
    candidate_tables = UPLOAD_SCHEMA_COLUMN_TABLES.get(column, ())
    if len(candidate_tables) == 1:
        return candidate_tables[0]

    statement_table = _infer_statement_table(statement)
    if statement_table and column in UPLOAD_SCHEMA_MANIFEST.get(statement_table, ()):
        return statement_table
    return None


def get_local_dev_rebuild_reason(db_path: Path) -> str | None:
    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path)
    try:
        tables = _get_sqlite_tables(conn)
        for table_name, required_columns in UPLOAD_SCHEMA_MANIFEST.items():
            if table_name not in tables:
                continue
            existing_columns = set(_get_sqlite_columns(conn, table_name))
            missing_columns = sorted(required_columns - existing_columns)
            if missing_columns:
                return f"{table_name} is missing required columns: {', '.join(missing_columns)}"

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


def classify_attachment_upload_schema_error(exc: Exception) -> AttachmentUploadSchemaIssue | None:
    if not isinstance(exc, DBAPIError):
        return None

    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    statement = getattr(exc, "statement", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)

    diag_table = getattr(diag, "table_name", None)
    diag_column = getattr(diag, "column_name", None)
    if diag_table and diag_column:
        reason = "incompatible_type" if sqlstate in INCOMPATIBLE_TYPE_SQLSTATES else "missing_column"
        issue = _build_schema_issue(diag_table, diag_column, reason=reason)
        if issue is not None:
            return issue

    message = " ".join(part for part in (str(exc), str(orig) if orig is not None else None, statement) if part).lower()

    for pattern in UPLOAD_SCHEMA_ERROR_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue

        column = match.group("column")
        table = match.groupdict().get("table")
        if table is None:
            table = _infer_table_for_upload_column(column, statement=statement)
        if table is None:
            continue

        issue = _build_schema_issue(table, column, reason="missing_column")
        if issue is not None:
            return issue

    for pattern in UPLOAD_SCHEMA_TYPE_ERROR_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue

        column = match.group("column")
        table = _infer_table_for_upload_column(column, statement=statement)
        if table is None:
            continue

        issue = _build_schema_issue(table, column, reason="incompatible_type")
        if issue is None:
            continue
        return AttachmentUploadSchemaIssue(
            table=issue.table,
            column=issue.column,
            reason=issue.reason,
            repairable=issue.repairable,
            expected_type=issue.expected_type,
            actual_type=match.group("actual_type").strip().upper()
            if match.group("actual_type").strip() == "uuid"
            else match.group("actual_type").strip(),
        )

    if sqlstate not in MISSING_COLUMN_SQLSTATES:
        if sqlstate not in INCOMPATIBLE_TYPE_SQLSTATES:
            return None
        if "entity_id" in message:
            table = _infer_table_for_upload_column("entity_id", statement=statement)
            if table is not None:
                issue = _build_schema_issue(table, "entity_id", reason="incompatible_type")
                if issue is not None:
                    actual_type = "UUID" if "uuid" in message else None
                    return AttachmentUploadSchemaIssue(
                        table=issue.table,
                        column=issue.column,
                        reason=issue.reason,
                        repairable=issue.repairable,
                        expected_type=issue.expected_type,
                        actual_type=actual_type,
                    )
        return None

    for column, candidate_tables in UPLOAD_SCHEMA_COLUMN_TABLES.items():
        if column not in message:
            continue
        table = _infer_table_for_upload_column(column, statement=statement)
        if table is None and len(candidate_tables) == 1:
            table = candidate_tables[0]
        if table is None:
            continue
        issue = _build_schema_issue(table, column, reason="missing_column")
        if issue is not None:
            return issue

    return None


def is_attachment_upload_schema_error(exc: Exception) -> bool:
    return classify_attachment_upload_schema_error(exc) is not None


def is_local_sqlite_attachment_upload_schema_error(
    exc: Exception,
    *,
    database_url: str | None,
) -> bool:
    return is_file_based_sqlite_database_url(database_url) and is_attachment_upload_schema_error(exc)


def is_attachment_processing_schema_error(exc: Exception) -> bool:
    issue = classify_attachment_upload_schema_error(exc)
    return (
        issue is not None
        and issue.table == "attachments"
        and issue.column
        in {
            "processing_status",
            "processing_error",
        }
    )


def is_local_sqlite_attachment_processing_schema_error(
    exc: Exception,
    *,
    database_url: str | None,
) -> bool:
    return is_file_based_sqlite_database_url(database_url) and is_attachment_processing_schema_error(exc)


def _get_attachment_upload_schema_issues(sync_conn) -> tuple[AttachmentUploadSchemaIssue, ...]:
    inspector = inspect(sync_conn)
    dialect_name = sync_conn.dialect.name
    table_names = set(inspector.get_table_names())
    issues: list[AttachmentUploadSchemaIssue] = []
    for table_name, required_columns in UPLOAD_SCHEMA_MANIFEST.items():
        if table_name not in table_names:
            for column_name in sorted(required_columns):
                issue = _build_schema_issue(table_name, column_name, reason="missing_table")
                if issue is not None:
                    issues.append(issue)
            continue

        existing_columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        for column_name in sorted(required_columns - set(existing_columns)):
            issue = _build_schema_issue(table_name, column_name, reason="missing_column")
            if issue is not None:
                issues.append(issue)
        for column_name, column_info in existing_columns.items():
            if (table_name, column_name) not in UPLOAD_SCHEMA_TYPE_EXPECTATIONS:
                continue
            if _has_expected_upload_column_type(
                table=table_name,
                column=column_name,
                column_type=column_info.get("type"),
                dialect_name=dialect_name,
                sync_conn=sync_conn,
            ):
                continue
            actual_type = _render_column_type(column_info.get("type"))
            if dialect_name == "postgresql":
                actual_type = _load_postgres_column_type(sync_conn, table=table_name, column=column_name) or actual_type
            issue = _build_schema_issue(table_name, column_name, reason="incompatible_type")
            if issue is not None:
                issues.append(
                    AttachmentUploadSchemaIssue(
                        table=issue.table,
                        column=issue.column,
                        reason=issue.reason,
                        repairable=issue.repairable,
                        expected_type=issue.expected_type,
                        actual_type=actual_type,
                    )
                )
    return tuple(issues)


def _build_add_column_sql(dialect_name: str, table: str, column: str) -> str:
    uuid_type = "UUID" if dialect_name == "postgresql" else "CHAR(36)"
    column_definitions = {
        ("attachments", "description"): "TEXT",
        ("attachments", "entity_id"): "VARCHAR(50)",
        ("attachments", "uploaded_by_email"): "VARCHAR(255)",
        ("attachments", "vdr_document_id"): uuid_type,
        ("attachments", "processing_status"): "VARCHAR(20) NOT NULL DEFAULT 'PENDING'",
        ("attachments", "processing_error"): "TEXT",
        ("marketing_materials", "source_mode"): "VARCHAR(20) NOT NULL DEFAULT 'GENERATED'",
        ("marketing_materials", "attachment_id"): uuid_type,
    }
    definition = column_definitions[(table, column)]
    return f"ALTER TABLE {table} ADD COLUMN {column} {definition}"


def _build_repair_issue_sql(dialect_name: str, issue: AttachmentUploadSchemaIssue) -> str:
    if issue.reason == "missing_column":
        return _build_add_column_sql(dialect_name, issue.table, issue.column)
    if issue.reason == "incompatible_type" and issue.table == "attachments" and issue.column == "entity_id":
        if dialect_name != "postgresql":
            raise ValueError("attachments.entity_id type repair is only supported on PostgreSQL")
        return "ALTER TABLE attachments ALTER COLUMN entity_id TYPE VARCHAR(50) USING entity_id::text"
    raise ValueError(f"Unsupported schema repair issue: {issue.qualified_column} ({issue.reason})")


async def _backfill_attachment_processing_status(conn, *, force_all: bool = False) -> None:
    valid_statuses = ", ".join(f"'{status}'" for status in sorted(VALID_ATTACHMENT_PROCESSING_STATUSES))
    where_clause = ""
    if not force_all:
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


async def probe_attachment_upload_schema(
    *,
    engine_override=None,
    logger: logging.Logger | None = None,
) -> AttachmentUploadSchemaRepairResult:
    from app.core.database import engine as default_engine

    active_logger = logger or logging.getLogger(__name__)
    active_engine = engine_override or default_engine

    try:
        async with active_engine.begin() as conn:
            issues = await conn.run_sync(_get_attachment_upload_schema_issues)
    except Exception:
        active_logger.exception("Attachment upload schema probe failed")
        raise

    return AttachmentUploadSchemaRepairResult(
        issues=issues,
        repaired=False,
        repair_attempted=False,
    )


async def repair_attachment_upload_schema_if_needed(
    *,
    database_url: str | None,
    engine_override=None,
    logger: logging.Logger | None = None,
) -> AttachmentUploadSchemaRepairResult:
    from app.core.database import engine as default_engine

    if resolve_local_sqlite_database_path(database_url) is not None:
        return AttachmentUploadSchemaRepairResult()

    active_logger = logger or logging.getLogger(__name__)
    active_engine = engine_override or default_engine

    try:
        async with active_engine.begin() as conn:
            issues = await conn.run_sync(_get_attachment_upload_schema_issues)
            repairable_issues = tuple(
                issue
                for issue in issues
                if issue.repairable and issue.reason in {"missing_column", "incompatible_type"}
            )
            if not repairable_issues:
                return AttachmentUploadSchemaRepairResult(
                    issues=issues,
                    repaired=not issues,
                    repair_attempted=False,
                )

            active_logger.warning(
                "Repairing uploaded marketing material schema issues on backend database: %s",
                ", ".join(f"{issue.qualified_column}({issue.reason})" for issue in repairable_issues),
            )

            dialect_name = conn.dialect.name
            for issue in repairable_issues:
                await conn.execute(text(_build_repair_issue_sql(dialect_name, issue)))

            remaining_issues = await conn.run_sync(_get_attachment_upload_schema_issues)
            remaining_columns = {issue.qualified_column for issue in remaining_issues}
            if {
                "attachments.processing_status",
                "attachments.vdr_document_id",
            }.isdisjoint(remaining_columns):
                await _backfill_attachment_processing_status(
                    conn,
                    force_all=any(
                        issue.qualified_column == "attachments.processing_status" for issue in repairable_issues
                    ),
                )
                remaining_issues = await conn.run_sync(_get_attachment_upload_schema_issues)
    except Exception:
        active_logger.exception("Uploaded marketing material schema repair failed")
        return AttachmentUploadSchemaRepairResult(
            issues=issues if "issues" in locals() else (),
            repaired=False,
            repair_attempted=True,
        )

    return AttachmentUploadSchemaRepairResult(
        issues=issues,
        repaired=not remaining_issues,
        repair_attempted=True,
    )


async def repair_attachment_processing_schema_if_needed(
    *,
    database_url: str | None,
    engine_override=None,
    logger: logging.Logger | None = None,
) -> AttachmentUploadSchemaRepairResult:
    return await repair_attachment_upload_schema_if_needed(
        database_url=database_url,
        engine_override=engine_override,
        logger=logger,
    )


def build_local_sqlite_upload_schema_rebuild_required_detail(
    *,
    stage: str,
    issue: AttachmentUploadSchemaIssue | None = None,
    request_id: str | None = None,
) -> str:
    issue_detail = ""
    if issue is not None:
        issue_detail = f" Missing schema element: {issue.qualified_column}."

    request_detail = ""
    if request_id:
        request_detail = f" If you need support, include request ID {request_id}."

    return (
        f"Uploaded marketing material failed during {stage}. "
        "Local SQLite dev database is stale and missing uploaded marketing material schema."
        f"{issue_detail} "
        f"{LOCAL_DEV_ENTRYPOINT_HINT}"
        f"{request_detail}"
    ).strip()


def build_local_sqlite_rebuild_required_detail(
    *,
    stage: str,
    issue: AttachmentUploadSchemaIssue | None = None,
    request_id: str | None = None,
) -> str:
    return build_local_sqlite_upload_schema_rebuild_required_detail(
        stage=stage,
        issue=issue,
        request_id=request_id,
    )


def build_backend_attachment_upload_schema_required_detail(
    *,
    stage: str,
    issue: AttachmentUploadSchemaIssue | None = None,
    request_id: str | None = None,
) -> str:
    issue_detail = ""
    if issue is not None:
        if issue.reason == "incompatible_type":
            actual_type = issue.actual_type
            if actual_type is not None and actual_type.lower() == "uuid":
                actual_type = "UUID"
            actual_type_detail = f" Found {actual_type}." if actual_type else ""
            expected_type_detail = f" Expected {issue.expected_type}." if issue.expected_type else ""
            issue_detail = (
                f" Schema element {issue.qualified_column} has an incompatible database type."
                f"{expected_type_detail}{actual_type_detail}"
            )
        else:
            issue_detail = f" Missing schema element: {issue.qualified_column}."

    request_detail = ""
    if request_id:
        request_detail = f" If you need support, provide request ID {request_id}."

    return (
        f"Uploaded marketing material failed during {stage}. "
        f"{BACKEND_ATTACHMENT_UPLOAD_SCHEMA_HINT}"
        f"{issue_detail} "
        f"{request_detail}"
    ).strip()


def build_backend_attachment_processing_schema_required_detail(
    *,
    stage: str,
    issue: AttachmentUploadSchemaIssue | None = None,
    request_id: str | None = None,
) -> str:
    return build_backend_attachment_upload_schema_required_detail(
        stage=stage,
        issue=issue,
        request_id=request_id,
    )
