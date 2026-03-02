"""VDR Internal API 테스트 — IM 백엔드 전용 내부 API."""

import uuid

import pytest

from app.core.config import settings


def _make_internal_key_header() -> dict[str, str]:
    """테스트용 내부 API 키 헤더 생성."""
    key = getattr(settings, "INTERNAL_SERVICE_KEY", "")
    if not key:
        pytest.skip("INTERNAL_SERVICE_KEY 미설정")
    return {"X-Internal-Key": key}


# ── List parseable documents ──────────────────────────────
async def test_internal_list_without_key(client, transaction_id):
    """인증 키 없이 호출하면 401 또는 403."""
    resp = await client.get(f"/api/v1/internal/vdr/transactions/{transaction_id}/documents")
    assert resp.status_code in (401, 403, 503)


async def test_internal_list_with_wrong_key(client, transaction_id):
    """잘못된 키로 호출하면 401, 403, 또는 503 (키 미설정)."""
    resp = await client.get(
        f"/api/v1/internal/vdr/transactions/{transaction_id}/documents",
        headers={"X-Internal-Key": "wrong-key"},
    )
    assert resp.status_code in (401, 403, 503)


async def test_internal_list_folders_without_key(client, transaction_id):
    """폴더 목록 — 키 없으면 인증 실패."""
    resp = await client.get(f"/api/v1/internal/vdr/transactions/{transaction_id}/folders")
    assert resp.status_code in (401, 403, 503)


# ── Nonexistent document ─────────────────────────────────
async def test_internal_metadata_nonexistent(client, transaction_id):
    """존재하지 않는 문서 메타데이터 → 404."""
    key = getattr(settings, "INTERNAL_SERVICE_KEY", "")
    if not key:
        pytest.skip("INTERNAL_SERVICE_KEY 미설정")
    fake_doc = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/internal/vdr/transactions/{transaction_id}/documents/{fake_doc}/metadata",
        headers={"X-Internal-Key": key},
    )
    assert resp.status_code == 404
