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
    reconcile_attachment_upload_migration_state,
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


def _load_revision_093_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "093_backfill_tm_materials_and_extraction_flags.py"
    )
    spec = importlib.util.spec_from_file_location("revision_093_tm_backfill", module_path)
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


@pytest.mark.asyncio
async def test_reconcile_attachment_upload_migration_state_stamps_safe_092_candidate(
    monkeypatch: pytest.MonkeyPatch,
):
    before = {
        "overall_ok": False,
        "migration": {
            "ok": False,
            "managed": True,
            "expected_heads": ["095"],
            "current_heads": ["092"],
            "error": None,
        },
        "attachment_entity_id_type": {
            "ok": True,
            "managed": True,
            "expected_type": "character varying(50)",
            "actual_type": "character varying(50)",
            "error": None,
        },
        "attachment_upload_schema": {
            "ok": True,
            "issues": [],
        },
    }
    after = {
        "overall_ok": True,
        "migration": {
            "ok": True,
            "managed": True,
            "expected_heads": ["095"],
            "current_heads": ["095"],
            "error": None,
        },
        "attachment_entity_id_type": {
            "ok": True,
            "managed": True,
            "expected_type": "character varying(50)",
            "actual_type": "character varying(50)",
            "error": None,
        },
        "attachment_upload_schema": {
            "ok": True,
            "issues": [],
        },
    }
    diagnostics_queue = [before, after]
    stamp_calls: list[tuple[object, str]] = []
    to_thread_calls: list[tuple[object, tuple[object, ...]]] = []

    async def _fake_build_attachment_upload_runtime_diagnostics(**kwargs):
        return diagnostics_queue.pop(0)

    async def _fake_to_thread(func, *args):
        to_thread_calls.append((func, args))
        return func(*args)

    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.build_attachment_upload_runtime_diagnostics",
        _fake_build_attachment_upload_runtime_diagnostics,
    )
    monkeypatch.setattr("app.core.attachment_upload_runtime_diagnostics.asyncio.to_thread", _fake_to_thread)
    monkeypatch.setattr("app.core.attachment_upload_runtime_diagnostics._build_alembic_config", lambda: "fake-config")
    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.command.stamp",
        lambda config, head: stamp_calls.append((config, head)),
    )

    result = await reconcile_attachment_upload_migration_state(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
    )

    assert result.reconciled is True
    assert result.attempted is True
    assert stamp_calls == [("fake-config", "095")]
    assert len(to_thread_calls) == 1
    assert result.safe_stamp_candidate is True
    assert result.target_head == "095"
    assert result.after == after


@pytest.mark.asyncio
async def test_reconcile_attachment_upload_migration_state_refuses_non_092_candidate(
    monkeypatch: pytest.MonkeyPatch,
):
    before = {
        "overall_ok": False,
        "migration": {
            "ok": False,
            "managed": True,
            "expected_heads": ["095"],
            "current_heads": ["091"],
            "error": None,
        },
        "attachment_entity_id_type": {
            "ok": True,
            "managed": True,
            "expected_type": "character varying(50)",
            "actual_type": "character varying(50)",
            "error": None,
        },
        "attachment_upload_schema": {
            "ok": True,
            "issues": [],
        },
    }
    stamp_calls: list[tuple[object, str]] = []

    async def _fake_build_attachment_upload_runtime_diagnostics(**kwargs):
        return before

    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.build_attachment_upload_runtime_diagnostics",
        _fake_build_attachment_upload_runtime_diagnostics,
    )
    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.command.stamp",
        lambda config, head: stamp_calls.append((config, head)),
    )

    result = await reconcile_attachment_upload_migration_state(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
    )

    assert result.reconciled is False
    assert result.attempted is False
    assert stamp_calls == []
    assert result.safe_stamp_candidate is False
    assert result.before == before


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


def test_revision_095_upgrade_normalizes_text_entity_id(monkeypatch: pytest.MonkeyPatch):
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
            return _FakeResult("text")

    monkeypatch.setattr(revision.op, "get_bind", lambda: _FakeBind())
    monkeypatch.setattr(revision.op, "execute", lambda clause: executed_sql.append(str(clause)))

    revision.upgrade()

    assert executed_sql == ["ALTER TABLE attachments ALTER COLUMN entity_id TYPE VARCHAR(50) USING entity_id::text"]


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
            return _FakeResult("jsonb")

    monkeypatch.setattr(revision.op, "get_bind", lambda: _FakeBind())

    with pytest.raises(RuntimeError, match=r"Unexpected attachments\.entity_id database type"):
        revision.upgrade()


def test_revision_093_upgrade_skips_existing_auto_apply_signed_at(monkeypatch: pytest.MonkeyPatch):
    revision = _load_revision_093_module()
    add_column_calls: list[tuple[str, str]] = []
    alter_column_calls: list[tuple[str, str]] = []
    executed_sql: list[str] = []

    class _FakeScalarResult:
        def __iter__(self):
            return iter(())

        def scalars(self):
            return iter(())

    class _FakeMappingsResult:
        def scalars(self):
            return iter(())

        def mappings(self):
            return iter(())

    class _FakeBind:
        def execute(self, clause):
            text_clause = str(clause)
            executed_sql.append(text_clause)
            if "SELECT marketing_materials.attachment_id" in text_clause:
                return _FakeScalarResult()
            return _FakeMappingsResult()

    class _FakeInspector:
        def get_columns(self, table_name):
            if table_name == "document_extractions":
                return [{"name": "auto_apply_signed_at"}]
            raise AssertionError(f"Unexpected table lookup: {table_name}")

    monkeypatch.setattr(revision.op, "get_bind", lambda: _FakeBind())
    monkeypatch.setattr(revision.sa, "inspect", lambda bind: _FakeInspector())
    monkeypatch.setattr(
        revision.op,
        "add_column",
        lambda table_name, column: add_column_calls.append((table_name, column.name)),
    )
    monkeypatch.setattr(
        revision.op,
        "alter_column",
        lambda table_name, column_name, **kwargs: alter_column_calls.append((table_name, column_name)),
    )

    revision.upgrade()

    assert add_column_calls == []
    assert alter_column_calls == []
    assert len(executed_sql) == 3
    assert "SELECT marketing_materials.attachment_id" in executed_sql[0]
    assert "SELECT transactions.id" in executed_sql[1]
    assert "SELECT attachments.id, attachments.transaction_id" in executed_sql[2]
