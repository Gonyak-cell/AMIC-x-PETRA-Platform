"""계약 마크업 버전 API 테스트."""

import io

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _create_contract(client: AsyncClient, txn_id: str) -> dict:
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={
            "contract_type": "SPA",
            "title": "주식매매계약서",
            "parties": ["매도인", "매수인"],
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def _upload_markup(client: AsyncClient, txn_id: str, contract_id: str, **overrides) -> dict:
    data = {
        "version_label": overrides.get("version_label", "v1 - 초안"),
        "source_party": overrides.get("source_party", "매도측"),
        "changes_summary": overrides.get("changes_summary", "초안 작성"),
    }
    files = {"file": ("SPA_v1.docx", io.BytesIO(b"fake docx content"), "application/octet-stream")}
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts/{contract_id}/markups",
        data=data,
        files=files,
    )
    assert resp.status_code == 201
    return resp.json()


async def test_upload_markup(client: AsyncClient, transaction_id: str):
    contract = await _create_contract(client, transaction_id)
    markup = await _upload_markup(client, transaction_id, contract["id"])
    assert markup["version_number"] == 1
    assert markup["version_label"] == "v1 - 초안"
    assert markup["file_name"] == "SPA_v1.docx"
    assert markup["file_size_bytes"] > 0


async def test_auto_increment_version(client: AsyncClient, transaction_id: str):
    contract = await _create_contract(client, transaction_id)
    m1 = await _upload_markup(client, transaction_id, contract["id"], version_label="v1")
    m2 = await _upload_markup(client, transaction_id, contract["id"], version_label="v2 - 매수인 마크업")
    assert m1["version_number"] == 1
    assert m2["version_number"] == 2


async def test_list_markups(client: AsyncClient, transaction_id: str):
    contract = await _create_contract(client, transaction_id)
    await _upload_markup(client, transaction_id, contract["id"], version_label="v1")
    await _upload_markup(client, transaction_id, contract["id"], version_label="v2")

    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/contracts/{contract['id']}/markups",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["items"][0]["version_number"] == 1
    assert body["items"][1]["version_number"] == 2


async def test_download_markup(client: AsyncClient, transaction_id: str):
    contract = await _create_contract(client, transaction_id)
    markup = await _upload_markup(client, transaction_id, contract["id"])

    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/contracts/{contract['id']}/markups/{markup['id']}/download",
    )
    assert resp.status_code == 200
    assert b"fake docx content" in resp.content


async def test_delete_markup(client: AsyncClient, transaction_id: str):
    contract = await _create_contract(client, transaction_id)
    markup = await _upload_markup(client, transaction_id, contract["id"])

    resp = await client.delete(
        f"/api/v1/transactions/{transaction_id}/contracts/{contract['id']}/markups/{markup['id']}",
    )
    assert resp.status_code == 204

    # 삭제 확인
    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/contracts/{contract['id']}/markups",
    )
    assert resp.json()["total"] == 0


async def test_404_nonexistent_contract(client: AsyncClient, transaction_id: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/contracts/{fake_id}/markups",
    )
    assert resp.status_code == 404
