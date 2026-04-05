import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.local_dev_schema_guard import (
    AttachmentUploadSchemaIssue,
    classify_attachment_upload_schema_error,
    guard_local_sqlite_database_url,
    probe_attachment_upload_schema,
    repair_attachment_upload_schema_if_needed,
)
from app.main import (
    _bootstrap_attachment_processing_schema_for_startup,
    _bootstrap_attachment_upload_migration_state_for_startup,
    _bootstrap_local_sqlite_schema_for_startup,
)
from scripts.run_dev_server import (
    _get_local_dev_rebuild_reason,
    _rebuild_local_dev_database_if_needed,
    _resolve_reload_enabled,
)


def _write_db(db_path: Path, ddl: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(ddl)
        conn.commit()
    finally:
        conn.close()


def test_get_local_dev_rebuild_reason_returns_none_for_missing_db(tmp_path):
    db_path = tmp_path / "missing.db"
    assert _get_local_dev_rebuild_reason(db_path) is None


def test_get_local_dev_rebuild_reason_detects_stale_marketing_material_columns(tmp_path):
    db_path = tmp_path / "stale.db"
    _write_db(
        db_path,
        """
        CREATE TABLE marketing_materials (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL
        );
        """,
    )

    reason = _get_local_dev_rebuild_reason(db_path)

    assert reason is not None
    assert "marketing_materials" in reason
    assert "source_mode" in reason
    assert "attachment_id" in reason


def test_get_local_dev_rebuild_reason_accepts_current_marketing_material_schema(tmp_path):
    db_path = tmp_path / "current.db"
    _write_db(
        db_path,
        """
        CREATE TABLE marketing_materials (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL,
            source_mode TEXT NOT NULL,
            attachment_id TEXT
        );
        """,
    )

    assert _get_local_dev_rebuild_reason(db_path) is None


def test_get_local_dev_rebuild_reason_detects_stale_attachment_columns(tmp_path):
    db_path = tmp_path / "stale-attachments.db"
    _write_db(
        db_path,
        """
        CREATE TABLE attachments (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            mime_type TEXT NOT NULL
        );
        """,
    )

    reason = _get_local_dev_rebuild_reason(db_path)

    assert reason is not None
    assert "attachments" in reason
    assert "description" in reason
    assert "uploaded_by_email" in reason
    assert "vdr_document_id" in reason
    assert "processing_status" in reason
    assert "processing_error" in reason


def test_get_local_dev_rebuild_reason_detects_legacy_nda_schema(tmp_path):
    db_path = tmp_path / "legacy-nda.db"
    _write_db(
        db_path,
        """
        CREATE TABLE ndas (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            buyer_candidate_id TEXT NOT NULL,
            nda_type TEXT NOT NULL
        );
        """,
    )

    reason = _get_local_dev_rebuild_reason(db_path)

    assert reason is not None
    assert "legacy schema" in reason


def test_rebuild_local_dev_database_if_needed_deletes_stale_db(tmp_path):
    db_path = tmp_path / "stale.db"
    _write_db(
        db_path,
        """
        CREATE TABLE marketing_materials (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL
        );
        """,
    )

    assert db_path.exists()

    _rebuild_local_dev_database_if_needed(db_path)

    assert not db_path.exists()


def test_guard_local_sqlite_database_url_ignores_non_sqlite(tmp_path):
    result = guard_local_sqlite_database_url(
        "postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
        allowed_roots=[tmp_path],
    )

    assert result.database_path is None
    assert result.rebuilt is False


def test_guard_local_sqlite_database_url_leaves_current_schema_untouched(tmp_path):
    db_path = tmp_path / "current-local.db"
    _write_db(
        db_path,
        """
        CREATE TABLE marketing_materials (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL,
            source_mode TEXT NOT NULL,
            attachment_id TEXT
        );
        CREATE TABLE attachments (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            description TEXT,
            uploaded_by_email TEXT,
            vdr_document_id TEXT,
            processing_status TEXT NOT NULL,
            processing_error TEXT
        );
        """,
    )

    result = guard_local_sqlite_database_url(
        f"sqlite+aiosqlite:///{db_path.as_posix()}",
        allowed_roots=[tmp_path],
    )

    assert result.database_path == db_path.resolve()
    assert result.rebuilt is False
    assert db_path.exists()


@pytest.mark.asyncio
async def test_bootstrap_local_sqlite_schema_for_startup_recreates_stale_db(tmp_path):
    db_path = tmp_path / "stale-startup.db"
    _write_db(
        db_path,
        """
        CREATE TABLE attachments (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            mime_type TEXT NOT NULL
        );
        """,
    )

    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_async_engine(database_url, echo=False)
    try:
        result = await _bootstrap_local_sqlite_schema_for_startup(
            database_url=database_url,
            engine_override=engine,
            allowed_roots=[tmp_path],
        )
    finally:
        await engine.dispose()

    assert result.rebuilt is True

    conn = sqlite3.connect(db_path)
    try:
        attachments_columns = {row[1] for row in conn.execute("PRAGMA table_info(attachments)").fetchall()}
        marketing_columns = {row[1] for row in conn.execute("PRAGMA table_info(marketing_materials)").fetchall()}
    finally:
        conn.close()

    assert {
        "description",
        "uploaded_by_email",
        "vdr_document_id",
        "processing_status",
        "processing_error",
    } <= attachments_columns
    assert {"source_mode", "attachment_id"} <= marketing_columns


@pytest.mark.asyncio
async def test_repair_attachment_processing_schema_if_needed_adds_missing_columns_for_nonlocal_db(tmp_path):
    db_path = tmp_path / "nonlocal-stale.db"
    _write_db(
        db_path,
        """
        CREATE TABLE attachments (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            mime_type TEXT NOT NULL
        );
        CREATE TABLE marketing_materials (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL
        );
        INSERT INTO attachments (
            id,
            transaction_id,
            entity_type,
            entity_id,
            file_path,
            file_name,
            file_size_bytes,
            mime_type
        ) VALUES (
            'att-1',
            'txn-1',
            'MARKETING_MATERIAL',
            'mat-1',
            '/tmp/uploaded.pdf',
            'uploaded.pdf',
            123,
            'application/pdf'
        );
        INSERT INTO marketing_materials (
            id,
            transaction_id,
            doc_type,
            title,
            status
        ) VALUES (
            'mat-1',
            'txn-1',
            'TM',
            'Uploaded teaser',
            'READY'
        );
        """,
    )

    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_async_engine(database_url, echo=False)
    try:
        result = await repair_attachment_upload_schema_if_needed(
            database_url=database_url,
            engine_override=engine,
        )
    finally:
        await engine.dispose()

    assert result.repaired is True
    assert result.qualified_missing_columns == (
        "attachments.description",
        "attachments.processing_error",
        "attachments.processing_status",
        "attachments.uploaded_by_email",
        "attachments.vdr_document_id",
        "marketing_materials.attachment_id",
        "marketing_materials.source_mode",
    )

    conn = sqlite3.connect(db_path)
    try:
        attachment_rows = conn.execute(
            """
            SELECT description, uploaded_by_email, vdr_document_id, processing_status, processing_error
            FROM attachments
            WHERE id = 'att-1'
            """
        ).fetchall()
        marketing_rows = conn.execute(
            """
            SELECT source_mode, attachment_id
            FROM marketing_materials
            WHERE id = 'mat-1'
            """
        ).fetchall()
    finally:
        conn.close()

    assert attachment_rows == [(None, None, None, "SKIPPED", None)]
    assert marketing_rows == [("GENERATED", None)]


@pytest.mark.asyncio
async def test_bootstrap_attachment_processing_schema_for_startup_repairs_missing_columns(tmp_path):
    db_path = tmp_path / "startup-nonlocal.db"
    _write_db(
        db_path,
        """
        CREATE TABLE attachments (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            mime_type TEXT NOT NULL
        );
        CREATE TABLE marketing_materials (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL
        );
        """,
    )

    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_async_engine(database_url, echo=False)
    try:
        result = await _bootstrap_attachment_processing_schema_for_startup(
            database_url=database_url,
            engine_override=engine,
        )
    finally:
        await engine.dispose()

    assert result.repaired is True

    conn = sqlite3.connect(db_path)
    try:
        attachments_columns = {row[1] for row in conn.execute("PRAGMA table_info(attachments)").fetchall()}
        marketing_columns = {row[1] for row in conn.execute("PRAGMA table_info(marketing_materials)").fetchall()}
    finally:
        conn.close()

    assert {
        "description",
        "uploaded_by_email",
        "vdr_document_id",
        "processing_status",
        "processing_error",
    } <= attachments_columns
    assert {"source_mode", "attachment_id"} <= marketing_columns


@pytest.mark.asyncio
async def test_bootstrap_attachment_upload_migration_state_for_startup_reconciles_safe_drift(
    monkeypatch: pytest.MonkeyPatch,
):
    reconcile_calls: list[dict[str, object]] = []

    async def _fake_reconcile_attachment_upload_migration_state(**kwargs):
        reconcile_calls.append(kwargs)
        return SimpleNamespace(
            reconciled=True,
            attempted=True,
            safe_stamp_candidate=True,
            target_head="095",
            error=None,
        )

    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.reconcile_attachment_upload_migration_state",
        _fake_reconcile_attachment_upload_migration_state,
    )

    result = await _bootstrap_attachment_upload_migration_state_for_startup(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
        engine_override=SimpleNamespace(),
    )

    assert result.reconciled is True
    assert reconcile_calls == [
        {
            "database_url": "postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
            "engine_override": SimpleNamespace(),
            "logger": ANY,
        }
    ]


def test_classify_attachment_upload_schema_error_detects_postgres_vdr_document_id():
    class _FakeOrigError(Exception):
        sqlstate = "42703"

        def __str__(self):
            return 'column "vdr_document_id" of relation "attachments" does not exist'

    exc = ProgrammingError(
        "INSERT INTO attachments (...) VALUES (...)",
        {},
        _FakeOrigError(),
    )

    issue = classify_attachment_upload_schema_error(exc)

    assert issue is not None
    assert issue.table == "attachments"
    assert issue.column == "vdr_document_id"
    assert issue.repairable is True


def test_classify_attachment_upload_schema_error_detects_postgres_processing_status():
    class _FakeOrigError(Exception):
        sqlstate = "42703"

        def __str__(self):
            return "column attachments.processing_status does not exist"

    exc = ProgrammingError(
        "INSERT INTO attachments (...) VALUES (...)",
        {},
        _FakeOrigError(),
    )

    issue = classify_attachment_upload_schema_error(exc)

    assert issue is not None
    assert issue.table == "attachments"
    assert issue.column == "processing_status"
    assert issue.repairable is True


def test_classify_attachment_upload_schema_error_detects_postgres_entity_id_type_mismatch():
    class _FakeOrigError(Exception):
        sqlstate = "42804"

        def __str__(self):
            return 'column "entity_id" is of type uuid but expression is of type character varying'

    exc = ProgrammingError(
        "INSERT INTO attachments (...) VALUES (...)",
        {},
        _FakeOrigError(),
    )

    issue = classify_attachment_upload_schema_error(exc)

    assert issue is not None
    assert issue.table == "attachments"
    assert issue.column == "entity_id"
    assert issue.reason == "incompatible_type"
    assert issue.repairable is True
    assert issue.expected_type == "VARCHAR(50)"
    assert issue.actual_type == "UUID"


def test_classify_attachment_upload_schema_error_detects_sqlite_missing_column():
    exc = OperationalError(
        "INSERT INTO attachments (...) VALUES (...)",
        {},
        sqlite3.OperationalError("table attachments has no column named processing_status"),
    )

    issue = classify_attachment_upload_schema_error(exc)

    assert issue is not None
    assert issue.table == "attachments"
    assert issue.column == "processing_status"


def test_classify_attachment_upload_schema_error_ignores_non_schema_db_errors():
    class _FakeOrigError(Exception):
        sqlstate = "23505"

        def __str__(self):
            return "duplicate key value violates unique constraint"

    exc = ProgrammingError(
        "INSERT INTO attachments (...) VALUES (...)",
        {},
        _FakeOrigError(),
    )

    assert classify_attachment_upload_schema_error(exc) is None


@pytest.mark.asyncio
async def test_repair_attachment_upload_schema_if_needed_repairs_entity_id_type_mismatch():
    executed_sql: list[str] = []

    class _FakeConn:
        def __init__(self):
            self.dialect = SimpleNamespace(name="postgresql")
            self._run_sync_calls = 0

        async def run_sync(self, fn):
            self._run_sync_calls += 1
            if self._run_sync_calls == 1:
                return (
                    AttachmentUploadSchemaIssue(
                        table="attachments",
                        column="entity_id",
                        reason="incompatible_type",
                        repairable=True,
                        expected_type="VARCHAR(50)",
                        actual_type="UUID",
                    ),
                )
            return ()

        async def execute(self, clause):
            executed_sql.append(str(clause))

    class _FakeBeginContext:
        def __init__(self, conn):
            self._conn = conn

        async def __aenter__(self):
            return self._conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeEngine:
        def __init__(self, conn):
            self._conn = conn

        def begin(self):
            return _FakeBeginContext(self._conn)

    result = await repair_attachment_upload_schema_if_needed(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
        engine_override=_FakeEngine(_FakeConn()),
    )

    assert result.repaired is True
    assert result.repair_attempted is True
    assert result.qualified_schema_elements == ("attachments.entity_id",)
    assert executed_sql[0] == "ALTER TABLE attachments ALTER COLUMN entity_id TYPE VARCHAR(50) USING entity_id::text"


@pytest.mark.asyncio
async def test_probe_attachment_upload_schema_reports_missing_columns(tmp_path):
    db_path = tmp_path / "probe-stale.db"
    _write_db(
        db_path,
        """
        CREATE TABLE attachments (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            mime_type TEXT NOT NULL
        );
        CREATE TABLE marketing_materials (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL
        );
        """,
    )

    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_async_engine(database_url, echo=False)
    try:
        result = await probe_attachment_upload_schema(engine_override=engine)
    finally:
        await engine.dispose()

    assert result.ok is False
    assert "attachments.vdr_document_id" in result.qualified_missing_columns
    assert "marketing_materials.source_mode" in result.qualified_missing_columns


def test_resolve_reload_enabled_defaults_false_on_windows():
    assert _resolve_reload_enabled(platform_name="nt", configured_value=None) is False


def test_resolve_reload_enabled_defaults_true_on_non_windows():
    assert _resolve_reload_enabled(platform_name="posix", configured_value=None) is True


def test_resolve_reload_enabled_honors_explicit_override():
    assert _resolve_reload_enabled(platform_name="nt", configured_value="true") is True
    assert _resolve_reload_enabled(platform_name="posix", configured_value="false") is False
