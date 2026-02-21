"""Compliance Checklist API 테스트."""

import pytest

SAMPLE_TXN = {
    "name": "컴플라이언스 테스트",
    "code_name": "COMP-001",
    "side": "SELL",
    "target_company_name": "컴플기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    return resp.json()["id"]


# ── Create ─────────────────────────────────────────────────
async def test_create_compliance(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={
            "category": "ANTITRUST",
            "requirement": "공정위 기업결합 신고",
            "jurisdiction": "대한민국",
            "regulatory_body": "공정거래위원회",
            "assignee_email": "legal@example.com",
            "due_date": "2026-06-01",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "ANTITRUST"
    assert data["requirement"] == "공정위 기업결합 신고"
    assert data["jurisdiction"] == "대한민국"
    assert data["status"] == "NOT_STARTED"


async def test_create_multiple_categories(client):
    txn_id = await _create_txn(client)
    for cat, req in [
        ("ANTITRUST", "기업결합 신고"),
        ("FOREIGN_INVESTMENT", "외국인 투자 신고"),
        ("SECURITIES", "증권 신고서 제출"),
        ("DATA_PRIVACY", "개인정보 이전 동의"),
    ]:
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/compliance",
            json={"category": cat, "requirement": req},
        )
        assert resp.status_code == 201


# ── List / Filter ──────────────────────────────────────────
async def test_list_compliance(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "ANTITRUST", "requirement": "항목 1"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "SECURITIES", "requirement": "항목 2"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/compliance")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_compliance_filter_category(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "ANTITRUST", "requirement": "독점 규제"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "TAX", "requirement": "세무 검토"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/compliance", params={"category": "ANTITRUST"})
    assert len(resp.json()) == 1
    assert resp.json()[0]["category"] == "ANTITRUST"


async def test_list_compliance_filter_status(client):
    txn_id = await _create_txn(client)
    item_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "ANTITRUST", "requirement": "승인됨"},
    )
    item_id = item_resp.json()["id"]
    await client.patch(
        f"/api/v1/transactions/{txn_id}/compliance/{item_id}",
        json={"status": "APPROVED"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "ANTITRUST", "requirement": "미시작"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/compliance", params={"status": "APPROVED"})
    assert len(resp.json()) == 1


# ── Get ─────────────────────────────────────────────────
async def test_get_compliance(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "DATA_PRIVACY", "requirement": "GDPR 검토"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/compliance/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["requirement"] == "GDPR 검토"


# ── Update ─────────────────────────────────────────────────
async def test_update_compliance_status(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "ANTITRUST", "requirement": "기업결합 신고"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/compliance/{item_id}",
        json={"status": "IN_REVIEW", "filing_reference": "FTC-2026-12345"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_REVIEW"
    assert resp.json()["filing_reference"] == "FTC-2026-12345"


async def test_update_compliance_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/compliance/{fake_id}",
        json={"status": "APPROVED"},
    )
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────
async def test_delete_compliance(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "SANCTIONS", "requirement": "제재 목록 확인"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/compliance/{item_id}")
    assert resp.status_code == 204


# ── Summary ────────────────────────────────────────────────
async def test_compliance_summary(client):
    txn_id = await _create_txn(client)

    # ANTITRUST: 2개 (1 approved, 1 flagged)
    a1 = await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "ANTITRUST", "requirement": "기업결합 신고"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/compliance/{a1.json()['id']}",
        json={"status": "APPROVED"},
    )
    a2 = await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "ANTITRUST", "requirement": "경쟁제한 우려", "due_date": "2020-01-01"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/compliance/{a2.json()['id']}",
        json={"status": "FLAGGED"},
    )

    # DATA_PRIVACY: 1개 (not started)
    await client.post(
        f"/api/v1/transactions/{txn_id}/compliance",
        json={"category": "DATA_PRIVACY", "requirement": "개인정보 이전"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/compliance/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["flagged_count"] == 1
    assert data["overdue_count"] == 1  # a2 has due_date 2020-01-01, flagged → overdue
    assert data["compliance_rate"] == pytest.approx(33.3, abs=0.1)  # 1/3 approved

    anti = next(c for c in data["by_category"] if c["category"] == "ANTITRUST")
    assert anti["total"] == 2
    assert anti["approved"] == 1
    assert anti["flagged"] == 1
