from __future__ import annotations

import asyncio
import json
import logging

from alembic import command

from app.core.attachment_upload_runtime_diagnostics import (
    _build_alembic_config,
    build_attachment_upload_runtime_diagnostics,
)
from app.core.config import settings


def _resolve_target_head(diagnostics: dict[str, object]) -> str | None:
    migration = diagnostics.get("migration")
    if not isinstance(migration, dict):
        return None
    expected_heads = migration.get("expected_heads")
    if not isinstance(expected_heads, list) or len(expected_heads) != 1:
        return None
    head = expected_heads[0]
    return head if isinstance(head, str) and head else None


def _is_safe_stamp_candidate(diagnostics: dict[str, object]) -> bool:
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


async def reconcile_attachment_upload_migration_state(
    *,
    database_url: str | None,
    logger: logging.Logger | None = None,
) -> tuple[int, dict[str, object]]:
    active_logger = logger or logging.getLogger(__name__)
    before = await build_attachment_upload_runtime_diagnostics(
        database_url=database_url,
        logger=active_logger,
    )
    payload: dict[str, object] = {
        "before": before,
        "safe_stamp_candidate": _is_safe_stamp_candidate(before),
    }
    if not _is_safe_stamp_candidate(before):
        return 1, payload

    target_head = _resolve_target_head(before)
    if target_head is None:
        payload["error"] = "Unable to resolve a single expected Alembic head"
        return 1, payload

    payload["target_head"] = target_head
    try:
        command.stamp(_build_alembic_config(), target_head)
    except Exception as exc:
        payload["stamp_error"] = str(exc)
        return 1, payload

    after = await build_attachment_upload_runtime_diagnostics(
        database_url=database_url,
        logger=active_logger,
    )
    payload["after"] = after
    return (0 if after.get("overall_ok") is True else 1), payload


async def _run() -> int:
    exit_code, payload = await reconcile_attachment_upload_migration_state(
        database_url=settings.DATABASE_URL,
        logger=logging.getLogger(__name__),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
