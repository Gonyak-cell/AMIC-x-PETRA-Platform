import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.local_dev_schema_guard import (
    guard_local_sqlite_database_url,
    repair_attachment_processing_schema_if_needed,
)
from app.main import (
    _bootstrap_attachment_processing_schema_for_startup,
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

    assert {"processing_status", "processing_error"} <= attachments_columns
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
            mime_type TEXT NOT NULL,
            vdr_document_id TEXT
        );
        INSERT INTO attachments (
            id,
            transaction_id,
            entity_type,
            entity_id,
            file_path,
            file_name,
            file_size_bytes,
            mime_type,
            vdr_document_id
        ) VALUES (
            'att-1',
            'txn-1',
            'MARKETING_MATERIAL',
            'mat-1',
            '/tmp/uploaded.pdf',
            'uploaded.pdf',
            123,
            'application/pdf',
            NULL
        );
        """,
    )

    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_async_engine(database_url, echo=False)
    try:
        result = await repair_attachment_processing_schema_if_needed(
            database_url=database_url,
            engine_override=engine,
        )
    finally:
        await engine.dispose()

    assert result.repaired is True
    assert result.missing_columns == ("processing_error", "processing_status")

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT processing_status, processing_error FROM attachments WHERE id = 'att-1'").fetchall()
    finally:
        conn.close()

    assert rows == [("SKIPPED", None)]


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
            mime_type TEXT NOT NULL,
            vdr_document_id TEXT
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
    finally:
        conn.close()

    assert {"processing_status", "processing_error"} <= attachments_columns


def test_resolve_reload_enabled_defaults_false_on_windows():
    assert _resolve_reload_enabled(platform_name="nt", configured_value=None) is False


def test_resolve_reload_enabled_defaults_true_on_non_windows():
    assert _resolve_reload_enabled(platform_name="posix", configured_value=None) is True


def test_resolve_reload_enabled_honors_explicit_override():
    assert _resolve_reload_enabled(platform_name="nt", configured_value="true") is True
    assert _resolve_reload_enabled(platform_name="posix", configured_value="false") is False
