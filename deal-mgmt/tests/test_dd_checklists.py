"""DD Checklist API 테스트."""

import pytest

SAMPLE_TXN = {
    "name": "DD 체크리스트 테스트",
    "code_name": "DD-001",
    "side": "SELL",
    "target_company_name": "DD기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    return resp.json()["id"]


# ── Create ─────────────────────────────────────────────────
async def test_create_checklist_item(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={
            "workstream": "FINANCIAL",
            "title": "최근 3개년 재무제표 수집",
            "assignee_email": "analyst@example.com",
            "due_date": "2026-04-01",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["workstream"] == "FINANCIAL"
    assert data["title"] == "최근 3개년 재무제표 수집"
    assert data["status"] == "NOT_STARTED"


async def test_create_multiple_workstreams(client):
    txn_id = await _create_txn(client)
    for ws, title in [
        ("FINANCIAL", "감사보고서 검토"),
        ("LEGAL", "소송 이력 조사"),
        ("TAX", "세무 조사 이력 확인"),
        ("COMMERCIAL", "시장점유율 분석"),
    ]:
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/dd-checklist",
            json={"workstream": ws, "title": title},
        )
        assert resp.status_code == 201


# ── List / Filter ──────────────────────────────────────────
async def test_list_checklist(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FINANCIAL", "title": "항목 1"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "LEGAL", "title": "항목 2"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/dd-checklist")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_checklist_filter_workstream(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FINANCIAL", "title": "재무 항목"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "LEGAL", "title": "법률 항목"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/dd-checklist", params={"workstream": "FINANCIAL"}
    )
    assert len(resp.json()) == 1
    assert resp.json()[0]["workstream"] == "FINANCIAL"


async def test_list_checklist_filter_status(client):
    txn_id = await _create_txn(client)
    item_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FINANCIAL", "title": "완료된 항목"},
    )
    item_id = item_resp.json()["id"]
    await client.patch(
        f"/api/v1/transactions/{txn_id}/dd-checklist/{item_id}",
        json={"status": "COMPLETED"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FINANCIAL", "title": "미완료 항목"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/dd-checklist", params={"status": "COMPLETED"}
    )
    assert len(resp.json()) == 1


# ── Update ─────────────────────────────────────────────────
async def test_update_checklist_status(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FINANCIAL", "title": "재무제표 검토"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/dd-checklist/{item_id}",
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"


async def test_update_checklist_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/dd-checklist/{fake_id}",
        json={"status": "COMPLETED"},
    )
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────
async def test_delete_checklist_item(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "TAX", "title": "세무 항목"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/dd-checklist/{item_id}")
    assert resp.status_code == 204


# ── Summary ────────────────────────────────────────────────
async def test_checklist_summary(client):
    txn_id = await _create_txn(client)

    # FINANCIAL: 2개 (1 completed, 1 in_progress)
    f1 = await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FINANCIAL", "title": "재무제표 검토"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/dd-checklist/{f1.json()['id']}",
        json={"status": "COMPLETED"},
    )
    f2 = await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FINANCIAL", "title": "세부 분석"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/dd-checklist/{f2.json()['id']}",
        json={"status": "IN_PROGRESS"},
    )

    # LEGAL: 1개 (not_started)
    await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "LEGAL", "title": "소송 이력"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/dd-checklist/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["overall_completion_pct"] == pytest.approx(33.3, abs=0.1)

    fin = next(w for w in data["by_workstream"] if w["workstream"] == "FINANCIAL")
    assert fin["total"] == 2
    assert fin["completed"] == 1
    assert fin["in_progress"] == 1

    leg = next(w for w in data["by_workstream"] if w["workstream"] == "LEGAL")
    assert leg["total"] == 1
    assert leg["not_started"] == 1
