import sqlite3
from pathlib import Path

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


def test_resolve_reload_enabled_defaults_false_on_windows():
    assert _resolve_reload_enabled(platform_name="nt", configured_value=None) is False


def test_resolve_reload_enabled_defaults_true_on_non_windows():
    assert _resolve_reload_enabled(platform_name="posix", configured_value=None) is True


def test_resolve_reload_enabled_honors_explicit_override():
    assert _resolve_reload_enabled(platform_name="nt", configured_value="true") is True
    assert _resolve_reload_enabled(platform_name="posix", configured_value="false") is False
