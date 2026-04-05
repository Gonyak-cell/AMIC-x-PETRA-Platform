from __future__ import annotations

import asyncio
import json
import logging

from app.core.attachment_upload_runtime_diagnostics import (
    AttachmentUploadMigrationReconcileResult,
    reconcile_attachment_upload_migration_state,
)
from app.core.config import settings


def _serialize_reconcile_result(result: AttachmentUploadMigrationReconcileResult) -> dict[str, object]:
    payload: dict[str, object] = {
        "safe_stamp_candidate": result.safe_stamp_candidate,
        "attempted": result.attempted,
        "reconciled": result.reconciled,
    }
    if result.target_head is not None:
        payload["target_head"] = result.target_head
    if result.before is not None:
        payload["before"] = result.before
    if result.after is not None:
        payload["after"] = result.after
    if result.error is not None:
        payload["error"] = result.error
    return payload


async def _run() -> int:
    result = await reconcile_attachment_upload_migration_state(
        database_url=settings.DATABASE_URL,
        logger=logging.getLogger(__name__),
    )
    print(json.dumps(_serialize_reconcile_result(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.reconciled else 1


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
