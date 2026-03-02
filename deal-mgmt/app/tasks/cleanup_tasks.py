"""고아 blob 정리 태스크 — 소프트 삭제된 VDR 문서의 blob을 주기적으로 삭제."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# 삭제 후 보존 기간 (일)
_RETENTION_DAYS = 7
# 배치당 최대 처리 건수
_BATCH_SIZE = 100


def _run_async(coro):  # type: ignore[no-untyped-def]
    """celery worker에서 코루틴 실행 (fm_tasks 패턴 재사용)."""
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()


@celery_app.task(name="deal_mgmt.cleanup_orphan_blobs", soft_time_limit=300)
def cleanup_orphan_blobs_task() -> dict[str, int]:
    """7일 이상 DELETED 상태인 VDR 문서의 blob을 삭제한다."""
    return _run_async(_cleanup())


async def _cleanup() -> dict[str, int]:
    from sqlalchemy import select

    from app.core.blob_storage import blob_client
    from app.core.database import async_session_factory
    from app.models.vdr_document import VdrDocument

    await blob_client.ensure_initialized()

    cutoff = datetime.now(UTC) - timedelta(days=_RETENTION_DAYS)
    deleted_count = 0
    failed_count = 0

    async with async_session_factory() as db:
        q = (
            select(VdrDocument)
            .where(
                VdrDocument.status == "DELETED",
                VdrDocument.updated_at < cutoff,
            )
            .limit(_BATCH_SIZE)
        )
        result = await db.execute(q)
        docs = list(result.scalars().all())

        for doc in docs:
            try:
                await blob_client.delete_blob(doc.file_path)
                await db.delete(doc)
                deleted_count += 1
            except Exception:
                logger.warning("고아 blob 삭제 실패: %s", doc.file_path, exc_info=True)
                failed_count += 1

        if deleted_count > 0:
            await db.commit()

    logger.info("고아 blob 정리 완료: deleted=%d, failed=%d", deleted_count, failed_count)
    return {"deleted": deleted_count, "failed": failed_count}
