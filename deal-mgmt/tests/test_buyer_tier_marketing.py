"""Buyer Tier + Marketing Log + VDR Categorization 테스트."""

SAMPLE_TXN = {
    "name": "프로젝트 에코",
    "deal_type": "MA",
    "side": "SELL",
    "target_company_name": "에코기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}

SAMPLE_BUYER = {
    "company_name": "삼성물산",
    "contact_name": "이매수",
    "contact_email": "lee@samsung.com",
    "contact_phone": "010-0000-0000",
    "buyer_type": "STRATEGIC",
}


async def _create_txn(client, **overrides) -> str:
    body = {**SAMPLE_TXN, **overrides}
    resp = await client.post("/api/v1/transactions", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _add_buyer(client, txn_id: str, **overrides) -> dict:
    body = {**SAMPLE_BUYER, **overrides}
    resp = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=body)
    assert resp.status_code == 201
    return resp.json()


# ── Tier CRUD ─────────────────────────────────────────────


async def test_buyer_tier_defaults_to_null(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    assert buyer["tier"] is None
    assert buyer["corp_code"] is None


async def test_set_buyer_tier(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "TIER_1"},
    )
    assert resp.status_code == 200
    assert resp.json()["tier"] == "TIER_1"


async def test_set_buyer_corp_code(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"corp_code": "00126380"},
    )
    assert resp.status_code == 200
    assert resp.json()["corp_code"] == "00126380"


async def test_tier_filter(client):
    txn_id = await _create_txn(client)
    b1 = await _add_buyer(client, txn_id, company_name="A사")
    b2 = await _add_buyer(client, txn_id, company_name="B사")
    b3 = await _add_buyer(client, txn_id, company_name="C사")

    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}",
        json={"tier": "TIER_1"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b2['id']}",
        json={"tier": "TIER_2"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b3['id']}",
        json={"tier": "NOT_TARGET"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/buyers",
        params={"tier": "TIER_1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["company_name"] == "A사"


async def test_buyer_summary_by_tier(client):
    txn_id = await _create_txn(client)
    b1 = await _add_buyer(client, txn_id, company_name="A사")
    b2 = await _add_buyer(client, txn_id, company_name="B사")

    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}",
        json={"tier": "TIER_1"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b2['id']}",
        json={"tier": "TIER_1"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_tier"]["TIER_1"] == 2


# ── Marketing Log CRUD ────────────────────────────────────


async def test_create_marketing_log(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={
            "stage": "IDENTIFIED",
            "log_date": "2026-03-01",
            "content": "초기 식별 완료",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["stage"] == "IDENTIFIED"
    assert data["log_date"] == "2026-03-01"
    assert data["content"] == "초기 식별 완료"
    assert data["buyer_id"] == buyer["id"]
    assert data["transaction_id"] == txn_id


async def test_list_marketing_logs(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "IDENTIFIED", "log_date": "2026-03-01"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "EMAIL_SENT", "log_date": "2026-03-05"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_marketing_logs_filter_stage(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "IDENTIFIED", "log_date": "2026-03-01"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "EMAIL_SENT", "log_date": "2026-03-05"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        params={"stage": "EMAIL_SENT"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["stage"] == "EMAIL_SENT"


async def test_update_marketing_log(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "IDENTIFIED", "log_date": "2026-03-01"},
    )
    log_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs/{log_id}",
        json={"content": "수정된 내용", "stage": "PHONE_CALL"},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "수정된 내용"
    assert resp.json()["stage"] == "PHONE_CALL"


async def test_delete_marketing_log(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "IDENTIFIED", "log_date": "2026-03-01"},
    )
    log_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs/{log_id}",
    )
    assert resp.status_code == 204


async def test_delete_marketing_log_404(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    fake_log = "00000000-0000-0000-0000-000000000000"

    resp = await client.delete(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs/{fake_log}",
    )
    assert resp.status_code == 404


# ── Marketing Stage Summary ───────────────────────────────


async def test_marketing_stage_summary(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "IDENTIFIED", "log_date": "2026-03-01"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "EMAIL_SENT", "log_date": "2026-03-05"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={"stage": "EMAIL_SENT", "log_date": "2026-03-10"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-stage-summary",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["buyer_id"] == buyer["id"]
    # IDENTIFIED → latest=2026-03-01
    assert data["stages"]["IDENTIFIED"] == "2026-03-01"
    # EMAIL_SENT → latest=2026-03-10 (최신 날짜)
    assert data["stages"]["EMAIL_SENT"] == "2026-03-10"
    # 미완료 단계는 None
    assert data["stages"]["PHONE_CALL"] is None
    assert data["stages"]["NDA_SIGNED"] is None


async def test_marketing_stage_summary_empty(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-stage-summary",
    )
    assert resp.status_code == 200
    data = resp.json()
    # 모든 단계 None
    for stage_date in data["stages"].values():
        assert stage_date is None


# ── Short-List Marketing Overview ─────────────────────────


async def test_short_list_overview(client):
    txn_id = await _create_txn(client)
    b1 = await _add_buyer(client, txn_id, company_name="A사")
    b2 = await _add_buyer(client, txn_id, company_name="B사")
    b3 = await _add_buyer(client, txn_id, company_name="C사")

    # b1=TIER_1 + short-listed, b2=TIER_2 + short-listed, b3=NOT_TARGET
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}",
        json={"tier": "TIER_1", "is_short_listed": True},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b2['id']}",
        json={"tier": "TIER_2", "is_short_listed": True},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b3['id']}",
        json={"tier": "NOT_TARGET"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/short-list/marketing-overview",
    )
    assert resp.status_code == 200
    data = resp.json()
    # is_short_listed=False인 b3 제외 → 2건
    assert len(data) == 2
    buyer_ids = {item["buyer_id"] for item in data}
    assert b1["id"] in buyer_ids
    assert b2["id"] in buyer_ids
    assert b3["id"] not in buyer_ids


async def test_short_list_overview_empty(client):
    txn_id = await _create_txn(client)
    await _add_buyer(client, txn_id)

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/short-list/marketing-overview",
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_short_list_overview_with_marketing_data(client):
    """Short-List에 마케팅 로그가 있을 때 stage별 최신 일자 집계 검증."""
    txn_id = await _create_txn(client)
    b1 = await _add_buyer(client, txn_id, company_name="A사")
    b2 = await _add_buyer(client, txn_id, company_name="B사")

    # b1=TIER_1 + short-listed, b2=TIER_2 + short-listed
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}",
        json={"tier": "TIER_1", "is_short_listed": True},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b2['id']}",
        json={"tier": "TIER_2", "is_short_listed": True},
    )

    # b1에 마케팅 로그 2건 — IDENTIFIED(03-01), EMAIL_SENT(03-05, 03-10)
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}/marketing-logs",
        json={"stage": "IDENTIFIED", "log_date": "2026-03-01"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}/marketing-logs",
        json={"stage": "EMAIL_SENT", "log_date": "2026-03-05"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}/marketing-logs",
        json={"stage": "EMAIL_SENT", "log_date": "2026-03-10"},
    )

    # b2에 마케팅 로그 1건 — IDENTIFIED(03-02)
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{b2['id']}/marketing-logs",
        json={"stage": "IDENTIFIED", "log_date": "2026-03-02"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/short-list/marketing-overview",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # buyer_id별 stages 매핑
    by_buyer = {item["buyer_id"]: item["stages"] for item in data}

    # b1: IDENTIFIED=03-01, EMAIL_SENT=03-10 (최신), 나머지 None
    assert by_buyer[b1["id"]]["IDENTIFIED"] == "2026-03-01"
    assert by_buyer[b1["id"]]["EMAIL_SENT"] == "2026-03-10"
    assert by_buyer[b1["id"]]["PHONE_CALL"] is None

    # b2: IDENTIFIED=03-02, 나머지 None
    assert by_buyer[b2["id"]]["IDENTIFIED"] == "2026-03-02"
    assert by_buyer[b2["id"]]["EMAIL_SENT"] is None


# ── Excel Export ──────────────────────────────────────────


async def test_export_excel(client):
    txn_id = await _create_txn(client)
    await _add_buyer(client, txn_id)
    await _add_buyer(client, txn_id, company_name="SK텔레콤")

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/buyers/export-excel",
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(resp.content) > 0


# ── VDR Categorization ───────────────────────────────────


def test_vdr_categorization():
    from app.services.vdr_categorization_service import suggest_category

    assert suggest_category("2024_감사보고서_A사.pdf").value == "FINANCIAL"
    assert suggest_category("NDA_계약서_202603.docx").value == "LEGAL"
    assert suggest_category("법인세_신고서.pdf").value == "TAX"
    assert suggest_category("정관_최신.pdf").value == "CORPORATE"
    assert suggest_category("인사규정_2024.pdf").value == "HR"
    assert suggest_category("특허_등록증.pdf").value == "IP"
    assert suggest_category("시스템_아키텍처.pdf").value == "TECHNICAL"
    assert suggest_category("매출_현황.xlsx").value == "COMMERCIAL"
    assert suggest_category("부동산_감정평가서.pdf").value == "REAL_ESTATE"
    assert suggest_category("환경영향_평가서.pdf").value == "ENVIRONMENT"
    assert suggest_category("보험증권_사본.pdf").value == "INSURANCE"
    assert suggest_category("시장조사_보고서.pdf").value == "MARKET_RESEARCH"
    assert suggest_category("random_file.txt") is None
