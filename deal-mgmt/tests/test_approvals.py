"""Approval Requests API 테스트 — Phase 5A."""

import pytest


SAMPLE_APPROVAL = {
    "approval_type": "PHASE_ADVANCE",
    "title": "마케팅 단계 전환 승인",
    "description": "준비 단계 완료 후 마케팅 단계로 전환",
    "approvers": [
        {"email": "approver1@example.com", "role": "파트너"},
        {"email": "approver2@example.com", "role": "법무팀장"},
    ],
    "deadline": "2026-03-01",
}


# ── Create ─────────────────────────────────────────────────
async def test_create_approval(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "마케팅 단계 전환 승인"
    assert data["approval_type"] == "PHASE_ADVANCE"
    assert data["status"] == "PENDING"
    assert len(data["approvers"]) == 2
    assert data["approvers"][0]["email"] == "approver1@example.com"
    assert data["approvers"][0]["status"] == "PENDING"
    assert data["deadline"] == "2026-03-01"


async def test_create_approval_minimal(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "CONTRACT_SIGN",
            "title": "SPA 체결 승인",
            "approvers": [{"email": "boss@example.com", "role": "대표"}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["approval_type"] == "CONTRACT_SIGN"
    assert data["description"] is None
    assert data["deadline"] is None


# ── List ───────────────────────────────────────────────────
async def test_list_approvals(client, transaction_id):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )
    await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "DEAL_TERMS",
            "title": "거래 조건 승인",
            "approvers": [{"email": "cfo@example.com", "role": "CFO"}],
        },
    )

    resp = await client.get(f"/api/v1/transactions/{transaction_id}/approvals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


async def test_list_approvals_filter_by_type(client, transaction_id):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )
    await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "DEAL_TERMS",
            "title": "조건 승인",
            "approvers": [{"email": "a@b.com", "role": "role"}],
        },
    )

    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/approvals",
        params={"approval_type": "DEAL_TERMS"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["approval_type"] == "DEAL_TERMS"


# ── Summary ──────────────────────────────────────────────
async def test_approval_summary(client, transaction_id):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )

    resp = await client.get(f"/api/v1/transactions/{transaction_id}/approvals/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["pending"] == 1
    assert data["approved"] == 0
    assert data["rejected"] == 0


# ── Decide (Approve) ────────────────────────────────────────
async def test_approve_single_approver(client, transaction_id):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "STATUS_CHANGE",
            "title": "상태 변경 승인",
            "approvers": [{"email": "approver@example.com", "role": "매니저"}],
        },
    )
    approval_id = create.json()["id"]

    resp = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "email": "approver@example.com",
            "decision": "APPROVED",
            "comment": "승인합니다.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"
    assert data["approvers"][0]["status"] == "APPROVED"
    assert data["approvers"][0]["comment"] == "승인합니다."


async def test_approve_multi_approver_partial(client, transaction_id):
    """2명 중 1명만 승인 → 상태 PENDING 유지."""
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )
    approval_id = create.json()["id"]

    resp = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"email": "approver1@example.com", "decision": "APPROVED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING"  # 아직 2번째 승인 대기


async def test_approve_multi_approver_complete(client, transaction_id):
    """2명 모두 승인 → 상태 APPROVED."""
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )
    approval_id = create.json()["id"]

    await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"email": "approver1@example.com", "decision": "APPROVED"},
    )
    resp = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"email": "approver2@example.com", "decision": "APPROVED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


# ── Decide (Reject) ─────────────────────────────────────────
async def test_reject_approval(client, transaction_id):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )
    approval_id = create.json()["id"]

    resp = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "email": "approver1@example.com",
            "decision": "REJECTED",
            "comment": "보완 필요합니다.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REJECTED"


# ── Cancel ───────────────────────────────────────────────────
async def test_cancel_approval(client, transaction_id):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )
    approval_id = create.json()["id"]

    resp = await client.post(f"/api/v1/approvals/{approval_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


async def test_cancel_already_decided(client, transaction_id):
    """이미 결정된 승인은 취소 불가."""
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "DEAL_TERMS",
            "title": "테스트",
            "approvers": [{"email": "a@b.com", "role": "r"}],
        },
    )
    approval_id = create.json()["id"]

    # 승인
    await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"email": "a@b.com", "decision": "APPROVED"},
    )

    # 취소 시도
    resp = await client.post(f"/api/v1/approvals/{approval_id}/cancel")
    assert resp.status_code == 400


# ── 404 ────────────────────────────────────────────────────
async def test_get_nonexistent_approval(client, transaction_id):
    resp = await client.get(
        f"/api/v1/approvals/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


async def test_decide_nonexistent_approval(client):
    resp = await client.post(
        "/api/v1/approvals/00000000-0000-0000-0000-000000000000/decide",
        json={"email": "a@b.com", "decision": "APPROVED"},
    )
    assert resp.status_code == 404
