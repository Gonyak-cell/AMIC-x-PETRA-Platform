from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.attachment_upload_runtime_diagnostics import (
    AttachmentEntityIdTypeState,
    AttachmentUploadMigrationState,
    build_attachment_upload_runtime_diagnostics,
    probe_attachment_upload_migration_state,
)
from app.core.local_dev_schema_guard import AttachmentUploadSchemaIssue, AttachmentUploadSchemaRepairResult


def _load_revision_095_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "migrations" / "versions" / "095_repair_attachment_entity_id_type.py"
    )
    spec = importlib.util.spec_from_file_location("revision_095_attachment_entity_id_type", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeBeginContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, conn, *, url: str):
        self._conn = conn
        self.url = url

    def begin(self):
        return _FakeBeginContext(self._conn)


@pytest.mark.asyncio
async def test_probe_attachment_upload_migration_state_treats_sqlite_as_unmanaged_ok():
    result = await probe_attachment_upload_migration_state(
        database_url="sqlite+aiosqlite:///:memory:",
        engine_override=SimpleNamespace(url="sqlite+aiosqlite:///:memory:"),
    )

    assert result.ok is True
    assert result.managed is False
    assert result.current_heads == ()
    assert result.expected_heads == ("095",)


@pytest.mark.asyncio
async def test_probe_attachment_upload_migration_state_detects_head_mismatch(monkeypatch: pytest.MonkeyPatch):
    class _FakeConn:
        async def run_sync(self, fn):
            return ("094",)

    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics._load_expected_heads",
        lambda: ("095",),
    )

    result = await probe_attachment_upload_migration_state(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
        engine_override=_FakeEngine(
            _FakeConn(),
            url="postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
        ),
    )

    assert result.ok is False
    assert result.managed is True
    assert result.expected_heads == ("095",)
    assert result.current_heads == ("094",)


@pytest.mark.asyncio
async def test_build_attachment_upload_runtime_diagnostics_includes_entity_id_type_details(
    monkeypatch: pytest.MonkeyPatch,
):
    async def _probe_migration(**kwargs):
        return AttachmentUploadMigrationState(
            ok=False,
            expected_heads=("095",),
            current_heads=("094",),
            managed=True,
        )

    async def _probe_entity_type(**kwargs):
        return AttachmentEntityIdTypeState(
            ok=False,
            actual_type="uuid",
            managed=True,
        )

    async def _probe_schema(**kwargs):
        return AttachmentUploadSchemaRepairResult(
            issues=(
                AttachmentUploadSchemaIssue(
                    table="attachments",
                    column="entity_id",
                    reason="incompatible_type",
                    repairable=True,
                    expected_type="VARCHAR(50)",
                    actual_type="UUID",
                ),
            ),
            repaired=False,
            repair_attempted=False,
        )

    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.probe_attachment_upload_migration_state",
        _probe_migration,
    )
    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.probe_attachment_entity_id_type_state",
        _probe_entity_type,
    )
    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.probe_attachment_upload_schema",
        _probe_schema,
    )

    diagnostics = await build_attachment_upload_runtime_diagnostics(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
    )

    assert diagnostics["overall_ok"] is False
    assert diagnostics["migration"] == {
        "ok": False,
        "managed": True,
        "expected_heads": ["095"],
        "current_heads": ["094"],
        "error": None,
    }
    assert diagnostics["attachment_entity_id_type"] == {
        "ok": False,
        "managed": True,
        "expected_type": "character varying(50)",
        "actual_type": "uuid",
        "error": None,
    }
    assert diagnostics["attachment_upload_schema"] == {
        "ok": False,
        "issues": [
            {
                "table": "attachments",
                "column": "entity_id",
                "reason": "incompatible_type",
                "repairable": True,
                "expected_type": "VARCHAR(50)",
                "actual_type": "UUID",
            }
        ],
    }


def test_revision_095_upgrades_uuid_entity_id_to_varchar(monkeypatch: pytest.MonkeyPatch):
    revision = _load_revision_095_module()
    executed_sql: list[str] = []

    class _FakeResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _FakeBind:
        dialect = SimpleNamespace(name="postgresql")

        def execute(self, clause):
            return _FakeResult("uuid")

    monkeypatch.setattr(revision.op, "get_bind", lambda: _FakeBind())
    monkeypatch.setattr(revision.op, "execute", lambda clause: executed_sql.append(str(clause)))

    revision.upgrade()

    assert executed_sql == ["ALTER TABLE attachments ALTER COLUMN entity_id TYPE VARCHAR(50) USING entity_id::text"]


def test_revision_095_upgrade_noops_for_varchar_entity_id(monkeypatch: pytest.MonkeyPatch):
    revision = _load_revision_095_module()
    executed_sql: list[str] = []

    class _FakeResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _FakeBind:
        dialect = SimpleNamespace(name="postgresql")

        def execute(self, clause):
            return _FakeResult("character varying(50)")

    monkeypatch.setattr(revision.op, "get_bind", lambda: _FakeBind())
    monkeypatch.setattr(revision.op, "execute", lambda clause: executed_sql.append(str(clause)))

    revision.upgrade()

    assert executed_sql == []


def test_revision_095_upgrade_rejects_unexpected_entity_id_type(monkeypatch: pytest.MonkeyPatch):
    revision = _load_revision_095_module()

    class _FakeResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _FakeBind:
        dialect = SimpleNamespace(name="postgresql")

        def execute(self, clause):
            return _FakeResult("text")

    monkeypatch.setattr(revision.op, "get_bind", lambda: _FakeBind())

    with pytest.raises(RuntimeError, match=r"Unexpected attachments\.entity_id database type"):
        revision.upgrade()
