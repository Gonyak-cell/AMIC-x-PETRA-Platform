"""Document Extraction HTTP API 테스트 — 엔드포인트 수준 검증."""

import asyncio
import time
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VdrDocumentStatus, VdrFolderCategory
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder

pytestmark = pytest.mark.anyio


async def _create_txn(client) -> str:
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "추출 테스트 거래",
            "deal_type": "SE",
            "side": "SELL",
            "target_company_name": "기업",
            "client_name": "고객",
            "lead_advisor_email": "advisor@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_vdr_doc(async_session: AsyncSession, txn_id: str) -> str:
    txn_uuid = uuid.UUID(txn_id)
    folder = VdrFolder(
        transaction_id=txn_uuid,
        name="테스트 폴더",
        category=VdrFolderCategory.LEGAL,
        is_required=False,
    )
    async_session.add(folder)
    await async_session.flush()

    document = VdrDocument(
        transaction_id=txn_uuid,
        folder_id=folder.id,
        original_name="nda.pdf",
        stored_name="nda.pdf",
        file_path="/tmp/nda.pdf",
        file_size_bytes=128,
        mime_type="application/pdf",
        status=VdrDocumentStatus.ACTIVE,
    )
    async_session.add(document)
    await async_session.commit()
    return str(document.id)


# ── List extractions ─────────────────────────────────────
async def test_list_extractions_empty(client):
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/extractions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


# ── Get extraction — 존재하지 않는 추출 ──────────────────
async def test_get_extraction_nonexistent(client):
    txn_id = await _create_txn(client)
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/transactions/{txn_id}/extractions/{fake_id}")
    assert resp.status_code == 404


# ── 잘못된 거래 ID ───────────────────────────────────────
async def test_extraction_invalid_txn(client):
    fake_txn = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/transactions/{fake_txn}/extractions")
    assert resp.status_code == 404


# ── Batch extraction — 빈 리스트 ─────────────────────────
async def test_batch_extraction_empty_list(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/extractions/batch",
        json={"vdr_document_ids": []},
    )
    # 빈 리스트는 400 또는 422
    assert resp.status_code in (400, 422)


async def test_create_extraction_does_not_block_on_slow_celery_dispatch(
    client,
    async_session: AsyncSession,
    monkeypatch,
):
    txn_id = await _create_txn(client)
    vdr_document_id = await _create_vdr_doc(async_session, txn_id)

    async def noop_sync_fallback(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.routers.document_extraction._run_sync_fallback",
        noop_sync_fallback,
    )

    from app.tasks.extraction_tasks import run_extraction_task

    def slow_delay(*args, **kwargs):
        time.sleep(0.6)

    monkeypatch.setattr(run_extraction_task, "delay", slow_delay)

    started = time.perf_counter()
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/extractions",
        json={
            "vdr_document_id": vdr_document_id,
            "doc_category_hint": "NDA",
        },
    )
    elapsed = time.perf_counter() - started

    assert resp.status_code == 202
    assert elapsed < 0.5

    await asyncio.sleep(0.7)
