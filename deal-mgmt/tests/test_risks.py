"""Risk Register API 테스트."""

SAMPLE_TXN = {
    "name": "리스크 테스트",
    "code_name": "RISK-001",
    "side": "SELL",
    "target_company_name": "리스크기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    return resp.json()["id"]


# ── Create ─────────────────────────────────────────────────
async def test_create_risk(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={
            "category": "REGULATORY",
            "title": "공정위 기업결합 신고 필요",
            "severity": "HIGH",
            "likelihood": "MEDIUM",
            "owner_email": "legal@example.com",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "REGULATORY"
    assert data["title"] == "공정위 기업결합 신고 필요"
    assert data["severity"] == "HIGH"
    assert data["likelihood"] == "MEDIUM"
    assert data["status"] == "IDENTIFIED"
    # risk_score = 3 (HIGH) * 3 (MEDIUM) = 9.0
    assert data["risk_score"] == 9.0


async def test_create_critical_risk(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={
            "category": "LEGAL",
            "title": "소송 리스크",
            "severity": "CRITICAL",
            "likelihood": "VERY_HIGH",
        },
    )
    assert resp.status_code == 201
    # risk_score = 4 (CRITICAL) * 5 (VERY_HIGH) = 20.0
    assert resp.json()["risk_score"] == 20.0


# ── List / Filter ──────────────────────────────────────────
async def test_list_risks(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "REGULATORY", "title": "규제 리스크", "severity": "HIGH"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "FINANCIAL", "title": "재무 리스크", "severity": "LOW"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/risks")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_risks_filter_category(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "REGULATORY", "title": "규제 1"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "FINANCIAL", "title": "재무 1"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/risks", params={"category": "REGULATORY"})
    assert len(resp.json()) == 1
    assert resp.json()[0]["category"] == "REGULATORY"


async def test_list_risks_filter_severity(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "LEGAL", "title": "중요 리스크", "severity": "CRITICAL"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "LEGAL", "title": "경미한 리스크", "severity": "LOW"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/risks", params={"severity": "CRITICAL"})
    assert len(resp.json()) == 1
    assert resp.json()[0]["severity"] == "CRITICAL"


# ── Get ─────────────────────────────────────────────────
async def test_get_risk(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "TAX", "title": "세무 리스크"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/risks/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "세무 리스크"


# ── Update ─────────────────────────────────────────────────
async def test_update_risk_status(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "REGULATORY", "title": "규제 리스크"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/risks/{item_id}",
        json={"status": "MITIGATING", "mitigation_strategy": "법무팀 대응 중"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "MITIGATING"
    assert resp.json()["mitigation_strategy"] == "법무팀 대응 중"


async def test_update_risk_recalculate_score(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "FINANCIAL", "title": "재무 리스크", "severity": "LOW", "likelihood": "LOW"},
    )
    item_id = create_resp.json()["id"]
    # initial score = 1 * 2 = 2.0
    assert create_resp.json()["risk_score"] == 2.0

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/risks/{item_id}",
        json={"severity": "CRITICAL"},
    )
    # new score = 4 (CRITICAL) * 2 (LOW) = 8.0
    assert resp.json()["risk_score"] == 8.0


async def test_update_risk_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/risks/{fake_id}",
        json={"status": "CLOSED"},
    )
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────
async def test_delete_risk(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "OPERATIONAL", "title": "운영 리스크"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/risks/{item_id}")
    assert resp.status_code == 204


# ── Summary ────────────────────────────────────────────────
async def test_risk_summary(client):
    txn_id = await _create_txn(client)

    # REGULATORY: 2개 (CRITICAL, HIGH)
    await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "REGULATORY", "title": "기업결합 신고", "severity": "CRITICAL", "likelihood": "HIGH"},
    )
    r2 = await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "REGULATORY", "title": "외국인 투자 신고", "severity": "HIGH", "likelihood": "LOW"},
    )
    # 2번째를 MITIGATED로 변경
    await client.patch(
        f"/api/v1/transactions/{txn_id}/risks/{r2.json()['id']}",
        json={"status": "MITIGATED"},
    )

    # FINANCIAL: 1개 (MEDIUM)
    await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={"category": "FINANCIAL", "title": "밸류에이션 불확실성", "severity": "MEDIUM", "likelihood": "MEDIUM"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/risks/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["unmitigated_critical"] == 1  # CRITICAL + not MITIGATED/CLOSED
    assert data["avg_risk_score"] > 0

    reg = next(c for c in data["by_category"] if c["category"] == "REGULATORY")
    assert reg["total"] == 2
    assert reg["critical"] == 1
    assert reg["high"] == 1
