"""HTTP tests for document extraction routes."""

import asyncio
import time
import uuid

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VdrDocumentStatus, VdrFolderCategory
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder

pytestmark = pytest.mark.anyio


async def _create_txn(client) -> str:
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "Extraction Test Transaction",
            "deal_type": "SE",
            "side": "SELL",
            "target_company_name": "Target",
            "client_name": "Client",
            "lead_advisor_email": "advisor@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_vdr_doc(async_session: AsyncSession, txn_id: str) -> str:
    txn_uuid = uuid.UUID(txn_id)
    folder = VdrFolder(
        transaction_id=txn_uuid,
        name="Test Folder",
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


async def test_list_extractions_empty(client):
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/extractions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_get_extraction_nonexistent(client):
    txn_id = await _create_txn(client)
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/transactions/{txn_id}/extractions/{fake_id}")
    assert resp.status_code == 404


async def test_extraction_invalid_txn(client):
    fake_txn = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/transactions/{fake_txn}/extractions")
    assert resp.status_code == 404


async def test_batch_extraction_empty_list(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/extractions/batch",
        json={"vdr_document_ids": []},
    )
    assert resp.status_code in (400, 422)


async def test_create_extraction_does_not_block_on_slow_celery_dispatch(
    client,
    async_session: AsyncSession,
    monkeypatch,
):
    from app.routers import document_extraction as router

    txn_id = await _create_txn(client)
    vdr_document_id = await _create_vdr_doc(async_session, txn_id)

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setattr(router.settings, "DEBUG", False)
    monkeypatch.setattr(router.settings, "AUTH_ENABLED", True)

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
            "target_model": "nda",
            "target_id": str(uuid.uuid4()),
            "auto_apply_signed_at": True,
        },
    )
    elapsed = time.perf_counter() - started

    assert resp.status_code == 202
    assert elapsed < 0.5

    await asyncio.sleep(0.7)


async def test_dispatch_extraction_uses_inline_fallback_in_local_env(monkeypatch):
    from app.routers import document_extraction as router

    monkeypatch.setenv("ENV", "local")
    monkeypatch.setattr(router.settings, "DEBUG", False)
    monkeypatch.setattr(router.settings, "AUTH_ENABLED", True)

    dispatched = False

    async def fake_dispatch(*args, **kwargs):
        nonlocal dispatched
        dispatched = True

    monkeypatch.setattr(router, "_dispatch_celery_best_effort", fake_dispatch)

    background_tasks = BackgroundTasks()
    await router._dispatch_extraction(uuid.uuid4(), background_tasks)

    assert len(background_tasks.tasks) == 1
    assert dispatched is False


async def test_dispatch_extraction_uses_celery_only_in_production(monkeypatch):
    from app.routers import document_extraction as router

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setattr(router.settings, "DEBUG", False)
    monkeypatch.setattr(router.settings, "AUTH_ENABLED", True)

    dispatched: list[uuid.UUID] = []

    async def fake_dispatch(extraction_id):
        dispatched.append(extraction_id)

    monkeypatch.setattr(router, "_dispatch_celery_best_effort", fake_dispatch)

    background_tasks = BackgroundTasks()
    extraction_id = uuid.uuid4()
    await router._dispatch_extraction(extraction_id, background_tasks)
    await asyncio.sleep(0)

    assert background_tasks.tasks == []
    assert dispatched == [extraction_id]
