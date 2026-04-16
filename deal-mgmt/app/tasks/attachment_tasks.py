from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

PROCESSING_PENDING = "PENDING"
PROCESSING_RUNNING = "RUNNING"
PROCESSING_SYNCED = "SYNCED"
PROCESSING_FAILED = "FAILED"
PROCESSING_SKIPPED = "SKIPPED"
STALE_PENDING_MINUTES = 10


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()


async def _update_attachment_state(
    attachment_id: uuid.UUID,
    *,
    status: str,
    error: str | None,
) -> None:
    from app.core.database import async_session_factory
    from app.models.attachment import Attachment

    async with async_session_factory() as db:
        attachment = await db.get(Attachment, attachment_id)
        if attachment is None:
            return
        attachment.processing_status = status
        attachment.processing_error = error
        await db.commit()


async def _process_attachment_once(attachment_id: uuid.UUID, *, raise_on_error: bool = False) -> None:
    from app.core.database import async_session_factory
    from app.models.attachment import Attachment
    from app.services.attachment_vdr_bridge import sync_attachment_to_vdr

    async with async_session_factory() as db:
        attachment = await db.get(Attachment, attachment_id)
        if attachment is None:
            logger.warning("Attachment processing skipped because attachment was not found: %s", attachment_id)
            return
        if attachment.processing_status == PROCESSING_SKIPPED:
            return
        if attachment.processing_status == PROCESSING_SYNCED and attachment.vdr_document_id is not None:
            return

        attachment.processing_status = PROCESSING_RUNNING
        attachment.processing_error = None
        await db.commit()
        try:
            await db.refresh(attachment)
        except Exception:
            logger.warning(
                "Attachment refresh failed before processing; continuing with committed instance: %s",
                attachment_id,
                exc_info=True,
            )

        try:
            result = await sync_attachment_to_vdr(
                db,
                attachment.transaction_id,
                attachment,
                Path(attachment.file_path),
            )
            if result is None or attachment.vdr_document_id is None:
                raise RuntimeError("Attachment VDR sync did not produce a linked document.")
        except Exception as exc:
            attachment = await db.get(Attachment, attachment_id)
            if attachment is not None:
                attachment.processing_status = PROCESSING_FAILED
                attachment.processing_error = str(exc)
                await db.commit()
            if raise_on_error:
                raise
            logger.exception("Attachment processing failed: %s", attachment_id)
            return

        attachment = await db.get(Attachment, attachment_id)
        if attachment is None:
            return
        attachment.processing_status = PROCESSING_SYNCED
        attachment.processing_error = None
        await db.commit()


@celery_app.task(
    name="deal_mgmt.attachments.process",
    bind=True,
    acks_late=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=300,
)
def process_attachment_task(self, attachment_id: str) -> None:
    parsed_attachment_id = uuid.UUID(attachment_id)

    try:
        _run_async(_process_attachment_once(parsed_attachment_id, raise_on_error=True))
    except SoftTimeLimitExceeded as exc:
        logger.warning("Attachment processing soft time limit exceeded: %s", attachment_id)
        _run_async(
            _update_attachment_state(
                parsed_attachment_id,
                status=PROCESSING_FAILED,
                error="Attachment post-processing timed out.",
            )
        )
        raise exc
    except Exception as exc:
        logger.exception("Attachment processing failed: %s", attachment_id)
        exhausted = self.request.retries >= self.max_retries
        _run_async(
            _update_attachment_state(
                parsed_attachment_id,
                status=PROCESSING_FAILED if exhausted else PROCESSING_PENDING,
                error=str(exc),
            )
        )
        if not exhausted:
            raise self.retry(exc=exc, countdown=60)


async def _requeue_stale_pending_attachments() -> None:
    from app.core.database import async_session_factory
    from app.models.attachment import Attachment

    cutoff = datetime.now(UTC) - timedelta(minutes=STALE_PENDING_MINUTES)

    async with async_session_factory() as db:
        result = await db.execute(
            select(Attachment.id).where(
                Attachment.processing_status == PROCESSING_PENDING,
                Attachment.vdr_document_id.is_(None),
                Attachment.updated_at < cutoff,
            )
        )
        attachment_ids = [row[0] for row in result.all()]

    for attachment_id in attachment_ids:
        try:
            process_attachment_task.delay(str(attachment_id))
        except Exception:
            logger.exception("Failed to requeue stale pending attachment: %s", attachment_id)


@celery_app.task(
    name="deal_mgmt.attachments.requeue_pending",
    bind=True,
    acks_late=True,
    max_retries=1,
    default_retry_delay=60,
)
def requeue_pending_attachment_processing_task(self) -> None:
    try:
        _run_async(_requeue_stale_pending_attachments())
    except Exception as exc:
        logger.exception("Failed to requeue pending attachment processing")
        raise self.retry(exc=exc, countdown=60)
