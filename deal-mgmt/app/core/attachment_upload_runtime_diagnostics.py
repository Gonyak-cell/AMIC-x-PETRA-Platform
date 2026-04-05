from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.local_dev_schema_guard import AttachmentUploadSchemaIssue, probe_attachment_upload_schema

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ATTACHMENT_ENTITY_ID_TYPE = "character varying(50)"


@dataclass(frozen=True)
class AttachmentUploadMigrationState:
    ok: bool
    expected_heads: tuple[str, ...] = ()
    current_heads: tuple[str, ...] = ()
    managed: bool = True
    error: str | None = None


@dataclass(frozen=True)
class AttachmentEntityIdTypeState:
    ok: bool
    expected_type: str = EXPECTED_ATTACHMENT_ENTITY_ID_TYPE
    actual_type: str | None = None
    managed: bool = True
    error: str | None = None


@dataclass(frozen=True)
class AttachmentUploadMigrationReconcileResult:
    reconciled: bool
    attempted: bool
    safe_stamp_candidate: bool
    target_head: str | None = None
    before: dict[str, object] | None = None
    after: dict[str, object] | None = None
    error: str | None = None


def serialize_attachment_upload_schema_issue(issue: AttachmentUploadSchemaIssue) -> dict[str, object]:
    payload: dict[str, object] = {
        "table": issue.table,
        "column": issue.column,
        "reason": issue.reason,
        "repairable": issue.repairable,
    }
    if issue.expected_type is not None:
        payload["expected_type"] = issue.expected_type
    if issue.actual_type is not None:
        payload["actual_type"] = issue.actual_type
    return payload


def _is_sqlite_database_url(database_url: str | None) -> bool:
    if not database_url:
        return False
    try:
        return make_url(database_url).get_backend_name() == "sqlite"
    except Exception:
        return False


def _build_alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return config


@lru_cache(maxsize=1)
def _load_expected_heads() -> tuple[str, ...]:
    return tuple(sorted(ScriptDirectory.from_config(_build_alembic_config()).get_heads()))


def _load_current_heads(sync_conn) -> tuple[str, ...]:
    context = MigrationContext.configure(sync_conn)
    return tuple(sorted(context.get_current_heads()))


def _load_postgres_attachment_entity_id_type(sync_conn) -> str | None:
    query = text(
        """
        SELECT format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute AS a
        JOIN pg_class AS c ON c.oid = a.attrelid
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = current_schema()
          AND c.relname = 'attachments'
          AND a.attname = 'entity_id'
          AND a.attnum > 0
          AND NOT a.attisdropped
        """
    )
    return sync_conn.execute(query).scalar_one_or_none()


def _resolve_database_url(database_url: str | None, engine_override) -> str | None:
    if database_url:
        return database_url
    engine_url = getattr(engine_override, "url", None)
    return str(engine_url) if engine_url is not None else None


def _resolve_target_head(diagnostics: dict[str, object]) -> str | None:
    migration = diagnostics.get("migration")
    if not isinstance(migration, dict):
        return None
    expected_heads = migration.get("expected_heads")
    if not isinstance(expected_heads, list) or len(expected_heads) != 1:
        return None
    head = expected_heads[0]
    return head if isinstance(head, str) and head else None


def _is_safe_attachment_upload_migration_reconcile_candidate(diagnostics: dict[str, object]) -> bool:
    migration = diagnostics.get("migration")
    entity_id_type = diagnostics.get("attachment_entity_id_type")
    attachment_schema = diagnostics.get("attachment_upload_schema")
    if (
        not isinstance(migration, dict)
        or not isinstance(entity_id_type, dict)
        or not isinstance(attachment_schema, dict)
    ):
        return False

    return (
        migration.get("managed") is True
        and migration.get("current_heads") == ["092"]
        and bool(_resolve_target_head(diagnostics))
        and entity_id_type.get("ok") is True
        and attachment_schema.get("ok") is True
    )


async def probe_attachment_upload_migration_state(
    *,
    database_url: str | None = None,
    engine_override=None,
    logger: logging.Logger | None = None,
) -> AttachmentUploadMigrationState:
    from app.core.database import engine as default_engine

    active_logger = logger or logging.getLogger(__name__)
    active_engine = engine_override or default_engine
    effective_database_url = _resolve_database_url(database_url, active_engine)
    expected_heads = _load_expected_heads()

    if _is_sqlite_database_url(effective_database_url):
        return AttachmentUploadMigrationState(
            ok=True,
            expected_heads=expected_heads,
            current_heads=(),
            managed=False,
        )

    try:
        async with active_engine.begin() as conn:
            current_heads = await conn.run_sync(_load_current_heads)
    except Exception as exc:
        active_logger.exception("Attachment upload migration probe failed")
        return AttachmentUploadMigrationState(
            ok=False,
            expected_heads=expected_heads,
            current_heads=(),
            managed=True,
            error=str(exc),
        )

    return AttachmentUploadMigrationState(
        ok=bool(current_heads) and current_heads == expected_heads,
        expected_heads=expected_heads,
        current_heads=current_heads,
        managed=True,
    )


async def probe_attachment_entity_id_type_state(
    *,
    database_url: str | None = None,
    engine_override=None,
    logger: logging.Logger | None = None,
) -> AttachmentEntityIdTypeState:
    from app.core.database import engine as default_engine

    active_logger = logger or logging.getLogger(__name__)
    active_engine = engine_override or default_engine
    effective_database_url = _resolve_database_url(database_url, active_engine)

    if _is_sqlite_database_url(effective_database_url):
        return AttachmentEntityIdTypeState(ok=True, managed=False)

    try:
        async with active_engine.begin() as conn:
            actual_type = await conn.run_sync(_load_postgres_attachment_entity_id_type)
    except Exception as exc:
        active_logger.exception("Attachment entity_id type probe failed")
        return AttachmentEntityIdTypeState(
            ok=False,
            managed=True,
            error=str(exc),
        )

    if actual_type is None:
        return AttachmentEntityIdTypeState(
            ok=False,
            managed=True,
            error="attachments.entity_id column was not found",
        )

    normalized_type = actual_type.strip().lower()
    return AttachmentEntityIdTypeState(
        ok=normalized_type == EXPECTED_ATTACHMENT_ENTITY_ID_TYPE,
        actual_type=actual_type,
        managed=True,
    )


async def build_attachment_upload_runtime_diagnostics(
    *,
    database_url: str | None = None,
    engine_override=None,
    logger: logging.Logger | None = None,
) -> dict[str, object]:
    migration_state = await probe_attachment_upload_migration_state(
        database_url=database_url,
        engine_override=engine_override,
        logger=logger,
    )
    entity_id_type_state = await probe_attachment_entity_id_type_state(
        database_url=database_url,
        engine_override=engine_override,
        logger=logger,
    )
    schema_result = await probe_attachment_upload_schema(
        engine_override=engine_override,
        logger=logger,
    )
    return {
        "service": "deal-mgmt",
        "overall_ok": migration_state.ok and entity_id_type_state.ok and schema_result.ok,
        "migration": {
            "ok": migration_state.ok,
            "managed": migration_state.managed,
            "expected_heads": list(migration_state.expected_heads),
            "current_heads": list(migration_state.current_heads),
            "error": migration_state.error,
        },
        "attachment_entity_id_type": {
            "ok": entity_id_type_state.ok,
            "managed": entity_id_type_state.managed,
            "expected_type": entity_id_type_state.expected_type,
            "actual_type": entity_id_type_state.actual_type,
            "error": entity_id_type_state.error,
        },
        "attachment_upload_schema": {
            "ok": schema_result.ok,
            "issues": [serialize_attachment_upload_schema_issue(issue) for issue in schema_result.issues],
        },
    }


async def reconcile_attachment_upload_migration_state(
    *,
    database_url: str | None = None,
    engine_override=None,
    logger: logging.Logger | None = None,
) -> AttachmentUploadMigrationReconcileResult:
    diagnostics = await build_attachment_upload_runtime_diagnostics(
        database_url=database_url,
        engine_override=engine_override,
        logger=logger,
    )
    safe_stamp_candidate = _is_safe_attachment_upload_migration_reconcile_candidate(diagnostics)
    if not safe_stamp_candidate:
        return AttachmentUploadMigrationReconcileResult(
            reconciled=False,
            attempted=False,
            safe_stamp_candidate=False,
            before=diagnostics,
        )

    target_head = _resolve_target_head(diagnostics)
    if target_head is None:
        return AttachmentUploadMigrationReconcileResult(
            reconciled=False,
            attempted=False,
            safe_stamp_candidate=True,
            before=diagnostics,
            error="Unable to resolve a single expected Alembic head",
        )

    try:
        await asyncio.to_thread(command.stamp, _build_alembic_config(), target_head)
    except Exception as exc:
        return AttachmentUploadMigrationReconcileResult(
            reconciled=False,
            attempted=True,
            safe_stamp_candidate=True,
            target_head=target_head,
            before=diagnostics,
            error=str(exc),
        )

    after = await build_attachment_upload_runtime_diagnostics(
        database_url=database_url,
        engine_override=engine_override,
        logger=logger,
    )
    return AttachmentUploadMigrationReconcileResult(
        reconciled=after.get("overall_ok") is True,
        attempted=True,
        safe_stamp_candidate=True,
        target_head=target_head,
        before=diagnostics,
        after=after,
    )
