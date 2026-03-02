"""범용 첨부파일 API 테스트."""

import io

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

BASE = "/api/v1/transactions"


# 확장자별 매직바이트 — _validate_magic_bytes 검증 통과용
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


async def _upload(client: AsyncClient, txn_id: str, **overrides) -> dict:
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

    resp = await client.post(f"{BASE}/{txn_id}/attachments", data=data, files=files)
    return resp


# ── 업로드 ────────────────────────────────────────────────


async def test_upload_success(client: AsyncClient, transaction_id: str):
    resp = await _upload(client, transaction_id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["entity_type"] == "NDA"
    assert body["file_name"] == "test.pdf"
    assert body["file_size_bytes"] > 0
    assert body["uploaded_by_email"] == "test@example.com"
    assert body["transaction_id"] == transaction_id


async def test_upload_with_description(client: AsyncClient, transaction_id: str):
    resp = await _upload(client, transaction_id, description="NDA 초안")
    assert resp.status_code == 201
    assert resp.json()["description"] == "NDA 초안"


async def test_upload_invalid_entity_type(client: AsyncClient, transaction_id: str):
    resp = await _upload(client, transaction_id, entity_type="INVALID_TYPE")
    assert resp.status_code == 400
    assert "유효하지 않은 entity_type" in resp.json()["detail"]


async def test_upload_disallowed_extension(client: AsyncClient, transaction_id: str):
    resp = await _upload(client, transaction_id, filename="malware.exe")
    assert resp.status_code == 400
    assert "허용되지 않는 파일 형식" in resp.json()["detail"]


async def test_upload_file_too_large(client: AsyncClient, transaction_id: str):
    large_content = b"x" * (50 * 1024 * 1024 + 1)  # 50MB + 1 byte
    resp = await _upload(client, transaction_id, content=large_content)
    assert resp.status_code == 413


# ── 목록 조회 ─────────────────────────────────────────────


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


# ── 다운로드 ──────────────────────────────────────────────


async def test_download(client: AsyncClient, transaction_id: str):
    pdf_content = b"%PDF-1.4 hello world pdf"
    upload_resp = await _upload(client, transaction_id, content=pdf_content)
    att_id = upload_resp.json()["id"]

    resp = await client.get(f"{BASE}/{transaction_id}/attachments/{att_id}/download")
    assert resp.status_code == 200
    assert b"hello world pdf" in resp.content


# ── 삭제 ──────────────────────────────────────────────────


async def test_delete(client: AsyncClient, transaction_id: str):
    upload_resp = await _upload(client, transaction_id)
    att_id = upload_resp.json()["id"]

    resp = await client.delete(f"{BASE}/{transaction_id}/attachments/{att_id}")
    assert resp.status_code == 204

    # 삭제 확인
    list_resp = await client.get(f"{BASE}/{transaction_id}/attachments")
    assert list_resp.json()["total"] == 0


async def test_delete_nonexistent(client: AsyncClient, transaction_id: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"{BASE}/{transaction_id}/attachments/{fake_id}")
    assert resp.status_code == 404
