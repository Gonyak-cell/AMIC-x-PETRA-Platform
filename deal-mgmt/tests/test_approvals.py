"""Approval Requests API 테스트 — Phase 5A.

decide_approval은 JWT claims.email로 승인자를 식별한다.
conftest MOCK_CLAIMS.email = "test@example.com"
"""

from app.core.security import JWTClaims, get_jwt_claims
from app.main import app

# conftest MOCK_CLAIMS email
MOCK_EMAIL = "test@example.com"
APPROVER2_EMAIL = "approver2@example.com"

SAMPLE_APPROVAL = {
    "approval_type": "PHASE_ADVANCE",
    "title": "마케팅 단계 전환 승인",
    "description": "준비 단계 완료 후 마케팅 단계로 전환",
    "approvers": [
        {"email": MOCK_EMAIL, "role": "파트너"},
        {"email": APPROVER2_EMAIL, "role": "법무팀장"},
    ],
    "deadline": "2026-03-01",
}


def _set_claims(email: str) -> None:
    async def _override() -> JWTClaims:
        return JWTClaims(user_id="test-user-id", email=email, role="ADMIN")

    app.dependency_overrides[get_jwt_claims] = _override


def _restore_claims() -> None:
    from tests.conftest import _override_get_jwt_claims

    app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims


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
    assert data["approvers"][0]["email"] == MOCK_EMAIL
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
    """JWT claims.email이 승인자 이메일과 일치해야 승인 가능."""
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "STATUS_CHANGE",
            "title": "상태 변경 승인",
            "approvers": [{"email": MOCK_EMAIL, "role": "매니저"}],
        },
    )
    approval_id = create.json()["id"]

    resp = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={
            "email": MOCK_EMAIL,
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
        json={"email": MOCK_EMAIL, "decision": "APPROVED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING"  # 아직 2번째 승인 대기


async def test_approve_multi_approver_complete(client, transaction_id):
    """2명 모두 승인 → 상태 APPROVED (JWT claims 교체 필요)."""
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json=SAMPLE_APPROVAL,
    )
    approval_id = create.json()["id"]

    # 1번 승인자 (기본 JWT)
    await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"email": MOCK_EMAIL, "decision": "APPROVED"},
    )

    # 2번 승인자 (JWT claims 교체)
    _set_claims(APPROVER2_EMAIL)
    try:
        resp = await client.post(
            f"/api/v1/approvals/{approval_id}/decide",
            json={"email": APPROVER2_EMAIL, "decision": "APPROVED"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"
    finally:
        _restore_claims()


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
            "email": MOCK_EMAIL,
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
            "approvers": [{"email": MOCK_EMAIL, "role": "r"}],
        },
    )
    approval_id = create.json()["id"]

    # 승인 (JWT claims.email = MOCK_EMAIL = approver email)
    await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"email": MOCK_EMAIL, "decision": "APPROVED"},
    )

    # 취소 시도
    resp = await client.post(f"/api/v1/approvals/{approval_id}/cancel")
    assert resp.status_code == 400


# ── 404 ────────────────────────────────────────────────────
async def test_get_nonexistent_approval(client, transaction_id):
    resp = await client.get("/api/v1/approvals/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_decide_nonexistent_approval(client):
    resp = await client.post(
        "/api/v1/approvals/00000000-0000-0000-0000-000000000000/decide",
        json={"email": "a@b.com", "decision": "APPROVED"},
    )
    assert resp.status_code == 404


# ── 보안: body.email 스푸핑 방지 ─────────────────────────
async def test_decide_ignores_body_email(client, transaction_id):
    """body.email에 다른 사람 이메일을 넣어도 JWT claims.email 기준으로 동작."""
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "STATUS_CHANGE",
            "title": "보안 테스트",
            "approvers": [
                {"email": MOCK_EMAIL, "role": "본인"},
                {"email": "other@example.com", "role": "타인"},
            ],
        },
    )
    approval_id = create.json()["id"]

    # body.email에 타인 이메일을 넣어도, 서버는 JWT claims.email(test@example.com)로 매칭
    resp = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"email": "other@example.com", "decision": "APPROVED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # JWT 기준: test@example.com(MOCK_EMAIL)이 승인됨
    approver_statuses = {a["email"]: a["status"] for a in data["approvers"]}
    assert approver_statuses[MOCK_EMAIL] == "APPROVED"
    assert approver_statuses["other@example.com"] == "PENDING"


async def test_non_approver_cannot_decide(client, transaction_id):
    """승인자 목록에 없는 사용자는 결정 불가 → 403."""
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "DEAL_TERMS",
            "title": "권한 없는 사용자 테스트",
            "approvers": [{"email": "someone@else.com", "role": "외부"}],
        },
    )
    approval_id = create.json()["id"]

    # JWT claims.email(test@example.com)이 approvers에 없으므로 403
    resp = await client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "APPROVED"},
    )
    assert resp.status_code == 403
