"""Tests for generic attachment upload APIs."""

from __future__ import annotations

import io
import uuid
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.models.attachment import Attachment
from app.models.enums import VdrClassificationStatus, VdrDocumentStatus, VdrFolderCategory
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.routers import attachments as attachments_router

pytestmark = pytest.mark.anyio

BASE = "/api/v1/transactions"

_MAGIC_BY_EXT: dict[str, bytes] = {
    ".pdf": b"%PDF-1.4 fake content",
    ".docx": b"PK\x03\x04 fake docx content",
    ".xlsx": b"PK\x03\x04 fake xlsx content",
    ".pptx": b"PK\x03\x04 fake pptx content",
    ".zip": b"PK\x03\x04 fake zip content",
    ".png": b"\x89PNG\r\n\x1a\n fake png content",
    ".jpg": b"\xff\xd8\xff\xe0 fake jpg content",
    ".txt": b"fake text content",
    ".csv": b"col1,col2\nval1,val2",
}


async def _upload(client: AsyncClient, txn_id: str, **overrides):
    data = {
        "entity_type": overrides.get("entity_type", "NDA"),
    }
    if "entity_id" in overrides:
        data["entity_id"] = overrides["entity_id"]
    if "description" in overrides:
        data["description"] = overrides["description"]

    filename = overrides.get("filename", "test.pdf")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    default_content = _MAGIC_BY_EXT.get(ext, b"%PDF-1.4 fallback content")
    content = overrides.get("content", default_content)
    files = {"file": (filename, io.BytesIO(content), "application/octet-stream")}

    return await client.post(f"{BASE}/{txn_id}/attachments", data=data, files=files)


async def test_upload_success(client: AsyncClient, transaction_id: str):
    resp = await _upload(client, transaction_id)

    assert resp.status_code == 201
    body = resp.json()
    assert body["entity_type"] == "NDA"
    assert body["file_name"] == "test.pdf"
    assert body["file_size_bytes"] > 0
    assert body["uploaded_by_email"] == "test@example.com"
    assert body["transaction_id"] == transaction_id
    assert body["processing_status"] in {"PENDING", "SKIPPED", "FAILED"}
    assert "processing_error" in body


async def test_upload_binds_attachment_to_entity_scope(
    client: AsyncClient,
    transaction_id: str,
):
    resp = await _upload(
        client,
        transaction_id,
        entity_type="NDA",
        entity_id="nda-1",
        filename="buyer-nda.pdf",
    )

    assert resp.status_code == 201
    assert resp.json()["entity_id"] == "nda-1"


async def test_upload_with_description(client: AsyncClient, transaction_id: str):
    resp = await _upload(client, transaction_id, description="NDA 초안")
    assert resp.status_code == 201
    assert resp.json()["description"] == "NDA 초안"


async def test_upload_engagement_succeeds_even_if_refresh_fails(
    client: AsyncClient,
    transaction_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    original_refresh = attachments_router.AsyncSession.refresh

    async def flaky_refresh(self, instance, *args, **kwargs):
        if isinstance(instance, Attachment):
            raise RuntimeError("attachment refresh failed after commit")
        return await original_refresh(self, instance, *args, **kwargs)

    monkeypatch.setattr(attachments_router.AsyncSession, "refresh", flaky_refresh)

    resp = await _upload(
        client,
        transaction_id,
        entity_type="ENGAGEMENT",
        filename="engagement.pdf",
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["entity_type"] == "ENGAGEMENT"
    assert body["file_name"] == "engagement.pdf"

    list_resp = await client.get(
        f"{BASE}/{transaction_id}/attachments?entity_type=ENGAGEMENT",
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1


async def test_upload_enqueue_failure_does_not_fail_the_request(
    client: AsyncClient,
    transaction_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    delay_mock = MagicMock(side_effect=RuntimeError("queue down"))
    monkeypatch.setattr(attachments_router.process_attachment_task, "delay", delay_mock)

    resp = await _upload(client, transaction_id, entity_type="NDA")

    assert resp.status_code == 201
    body = resp.json()
    assert body["processing_status"] == "FAILED"
    assert "queue down" in (body["processing_error"] or "")


async def test_retry_processing_requeues_failed_attachment(
    client: AsyncClient,
    transaction_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    initial_delay = MagicMock(side_effect=RuntimeError("queue down"))
    monkeypatch.setattr(attachments_router.process_attachment_task, "delay", initial_delay)

    upload_resp = await _upload(client, transaction_id, entity_type="NDA")
    assert upload_resp.status_code == 201
    attachment_id = upload_resp.json()["id"]

    retry_delay = MagicMock()
    monkeypatch.setattr(attachments_router.process_attachment_task, "delay", retry_delay)

    retry_resp = await client.post(
        f"{BASE}/{transaction_id}/attachments/{attachment_id}/retry-processing",
    )

    assert retry_resp.status_code == 200
    body = retry_resp.json()
    assert body["processing_status"] == "PENDING"
    assert body["processing_error"] is None
    retry_delay.assert_called_once_with(attachment_id)


async def test_upload_invalid_entity_type(client: AsyncClient, transaction_id: str):
    resp = await _upload(client, transaction_id, entity_type="INVALID_TYPE")
    assert resp.status_code == 400
    assert "Invalid entity_type" in resp.json()["detail"]


async def test_upload_disallowed_extension(client: AsyncClient, transaction_id: str):
    resp = await _upload(client, transaction_id, filename="malware.exe")
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


async def test_upload_file_too_large(client: AsyncClient, transaction_id: str):
    large_content = b"x" * (50 * 1024 * 1024 + 1)
    resp = await _upload(client, transaction_id, content=large_content)
    assert resp.status_code == 413


async def test_list_all(client: AsyncClient, transaction_id: str):
    await _upload(client, transaction_id, entity_type="NDA")
    await _upload(client, transaction_id, entity_type="BID", filename="bid.docx")

    resp = await client.get(f"{BASE}/{transaction_id}/attachments")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_list_filter_entity_type(client: AsyncClient, transaction_id: str):
    await _upload(client, transaction_id, entity_type="NDA")
    await _upload(client, transaction_id, entity_type="BID", filename="bid.docx")

    resp = await client.get(f"{BASE}/{transaction_id}/attachments?entity_type=NDA")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["entity_type"] == "NDA"


async def test_list_marketing_material_attachments_normalizes_legacy_blank_status(
    client: AsyncClient,
    transaction_id: str,
    async_session,
):
    attachment = Attachment(
        transaction_id=uuid.UUID(transaction_id),
        entity_type="MARKETING_MATERIAL",
        entity_id="TM",
        file_path="/tmp/tm.pdf",
        file_name="tm.pdf",
        file_size_bytes=10,
        mime_type="application/pdf",
        uploaded_by_email="test@example.com",
    )
    async_session.add(attachment)
    await async_session.commit()

    await async_session.execute(
        text("UPDATE attachments SET processing_status = '' WHERE id = :attachment_id"),
        {"attachment_id": attachment.id.hex},
    )
    await async_session.commit()
    async_session.expire_all()

    resp = await client.get(
        f"{BASE}/{transaction_id}/attachments?entity_type=MARKETING_MATERIAL&entity_id=TM"
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["processing_status"] == "SKIPPED"


async def test_list_nda_attachments_normalizes_invalid_status_to_pending(
    client: AsyncClient,
    transaction_id: str,
    async_session,
):
    attachment = Attachment(
        transaction_id=uuid.UUID(transaction_id),
        entity_type="NDA",
        entity_id="nda-1",
        file_path="/tmp/nda.pdf",
        file_name="nda.pdf",
        file_size_bytes=10,
        mime_type="application/pdf",
        uploaded_by_email="test@example.com",
    )
    async_session.add(attachment)
    await async_session.commit()

    await async_session.execute(
        text("UPDATE attachments SET processing_status = 'BROKEN' WHERE id = :attachment_id"),
        {"attachment_id": attachment.id.hex},
    )
    await async_session.commit()
    async_session.expire_all()

    resp = await client.get(f"{BASE}/{transaction_id}/attachments?entity_type=NDA&entity_id=nda-1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["processing_status"] == "PENDING"


async def test_list_attachments_normalizes_synced_state_from_linked_vdr_document(
    client: AsyncClient,
    transaction_id: str,
    async_session,
):
    folder = VdrFolder(
        transaction_id=uuid.UUID(transaction_id),
        parent_id=None,
        name="TM",
        category=VdrFolderCategory.COMMERCIAL,
        order_index=0,
        is_required=False,
        description=None,
    )
    async_session.add(folder)
    await async_session.flush()

    document = VdrDocument(
        transaction_id=uuid.UUID(transaction_id),
        folder_id=folder.id,
        original_name="tm.pdf",
        stored_name="tm.pdf",
        file_path="/tmp/tm.pdf",
        file_size_bytes=10,
        mime_type="application/pdf",
        status=VdrDocumentStatus.ACTIVE,
        classification_status=VdrClassificationStatus.DIRECT,
        uploaded_by_email="test@example.com",
    )
    async_session.add(document)
    await async_session.flush()
    document_id = document.id

    attachment = Attachment(
        transaction_id=uuid.UUID(transaction_id),
        entity_type="MARKETING_MATERIAL",
        entity_id="TM",
        file_path="/tmp/tm.pdf",
        file_name="tm.pdf",
        file_size_bytes=10,
        mime_type="application/pdf",
        uploaded_by_email="test@example.com",
        vdr_document_id=document_id,
    )
    async_session.add(attachment)
    await async_session.commit()

    await async_session.execute(
        text("UPDATE attachments SET processing_status = 'BROKEN' WHERE id = :attachment_id"),
        {"attachment_id": attachment.id.hex},
    )
    await async_session.commit()
    async_session.expire_all()

    resp = await client.get(
        f"{BASE}/{transaction_id}/attachments?entity_type=MARKETING_MATERIAL&entity_id=TM"
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["processing_status"] == "SYNCED"
    assert body["items"][0]["vdr_sync"]["vdr_document_id"] == str(document_id)


def test_serialize_attachment_out_normalizes_none_processing_state_for_marketing_material():
    attachment = Attachment(
        id=uuid.uuid4(),
        transaction_id=uuid.uuid4(),
        entity_type="MARKETING_MATERIAL",
        entity_id="TM",
        file_path="/tmp/tm.pdf",
        file_name="tm.pdf",
        file_size_bytes=10,
        mime_type="application/pdf",
        uploaded_by_email="test@example.com",
    )
    attachment.__dict__["processing_status"] = None
    attachment.__dict__["processing_error"] = {"unexpected": "shape"}

    serialized = attachments_router._serialize_attachment_out(attachment)

    assert serialized.processing_status == "SKIPPED"
    assert serialized.processing_error is None


async def test_download(client: AsyncClient, transaction_id: str):
    pdf_content = b"%PDF-1.4 hello world pdf"
    upload_resp = await _upload(client, transaction_id, content=pdf_content)
    attachment_id = upload_resp.json()["id"]

    resp = await client.get(
        f"{BASE}/{transaction_id}/attachments/{attachment_id}/download",
    )
    assert resp.status_code == 200
    assert b"hello world pdf" in resp.content


async def test_delete(client: AsyncClient, transaction_id: str):
    upload_resp = await _upload(client, transaction_id)
    attachment_id = upload_resp.json()["id"]

    resp = await client.delete(
        f"{BASE}/{transaction_id}/attachments/{attachment_id}",
    )
    assert resp.status_code == 204

    list_resp = await client.get(f"{BASE}/{transaction_id}/attachments")
    assert list_resp.json()["total"] == 0


async def test_delete_nonexistent(client: AsyncClient, transaction_id: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"{BASE}/{transaction_id}/attachments/{fake_id}")
    assert resp.status_code == 404
