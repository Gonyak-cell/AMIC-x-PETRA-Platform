"""Golden Path 통합 테스트 — 8단계 M&A 워크플로우 순차 진행.

하나의 Transaction이 ENGAGEMENT → POST_CLOSING까지 전체 라이프사이클을
순차적으로 통과하며, 각 게이트에서 차단(negative)→시드→통과(positive)를
검증한다. test_phase_gates.py의 개별 테스트와 달리, 이전 단계의 시드 데이터가
다음 단계에 누적되는 cross-gate 상호작용을 검증한다.
"""

import pytest
from httpx import AsyncClient

# 전제 조건을 모두 충족하는 거래 데이터
FULL_TXN = {
    "name": "Golden Path 통합 테스트",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_active_txn(client: AsyncClient) -> str:
    """ACTIVE 상태 거래 생성 헬퍼."""
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    assert resp.status_code == 201
    txn_id = resp.json()["id"]
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    return txn_id


async def _assert_phase(client: AsyncClient, txn_id: str, expected: str) -> None:
    """현재 단계가 expected인지 확인."""
    resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
    assert resp.status_code == 200
    assert resp.json()["current_phase"] == expected


async def _advance(
    client: AsyncClient,
    txn_id: str,
    to_phase: str,
    acknowledgements: dict[str, bool] | None = None,
) -> dict:
    """단계 전환 후 응답 반환."""
    body: dict = {"to_phase": to_phase}
    if acknowledgements:
        body["acknowledgements"] = acknowledgements
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json=body,
    )
    return {"status_code": resp.status_code, "body": resp.json()}


async def _get_phase_status(client: AsyncClient, txn_id: str) -> dict:
    """phase-status 조회."""
    resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
    assert resp.status_code == 200
    return resp.json()


# ── Golden Path: 전체 8단계 순차 진행 ─────────────────────────


@pytest.mark.asyncio
async def test_golden_path_full_lifecycle(client: AsyncClient):
    """ENGAGEMENT → POST_CLOSING 전체 라이프사이클.

    각 게이트에서:
    1. 시드 데이터 없이 advance → 422 (차단)
    2. phase-status에서 미충족 조건 확인
    3. 시드 데이터 추가
    4. advance → 200 (통과)
    """
    txn_id = await _create_active_txn(client)
    await _assert_phase(client, txn_id, "ENGAGEMENT")

    # ── Step 1: ENGAGEMENT → PREPARATION ──────────────────
    # (전제 조건: client_name + lead_advisor_email — 이미 FULL_TXN에 포함)
    status = await _get_phase_status(client, txn_id)
    assert status["all_met"] is True  # 필드 기반 조건 이미 충족
    assert status["can_advance"] is True

    result = await _advance(client, txn_id, "PREPARATION")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "PREPARATION"

    # ── Step 2: PREPARATION → MARKETING ───────────────────
    # (전제 조건: target_company_name — 이미 FULL_TXN에 포함)
    status = await _get_phase_status(client, txn_id)
    assert status["all_met"] is True

    result = await _advance(client, txn_id, "MARKETING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "MARKETING"

    # ── Step 3: MARKETING → BIDDING ───────────────────────
    # (게이트: short list buyer + NDA/배포)

    # 3a. 시드 없이 시도 → 차단
    result = await _advance(client, txn_id, "BIDDING")
    assert result["status_code"] == 422

    # 3b. phase-status에서 미충족 확인
    status = await _get_phase_status(client, txn_id)
    assert status["all_met"] is False
    assert status["can_advance"] is False
    fields = {p["field"] for p in status["prerequisites"]}
    assert "short_list_buyers" in fields
    assert "nda_or_distribution" in fields
    assert status["gate_summary"] is not None

    # 3c. 시드: TIER_1 buyer (→ short list) + NDA_SIGNED
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={"company_name": "전략적 매수자 A", "buyer_type": "STRATEGIC", "tier": "TIER_1"},
    )
    assert resp.status_code == 201
    buyer_a_id = resp.json()["id"]

    # IDENTIFIED → CONTACTED → NDA_SIGNED
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_a_id}",
        json={"status": "CONTACTED"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_a_id}",
        json={"status": "NDA_SIGNED"},
    )

    # 3d. advance → 성공
    result = await _advance(client, txn_id, "BIDDING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "BIDDING"

    # ── Step 4: BIDDING → MAIN_DUE_DILIGENCE ─────────────
    # (게이트: 유효 입찰 1건 이상)

    # 4a. 시드 없이 시도 → 차단
    result = await _advance(client, txn_id, "MAIN_DUE_DILIGENCE")
    assert result["status_code"] == 422

    # 4b. phase-status에서 미충족 확인
    status = await _get_phase_status(client, txn_id)
    assert status["all_met"] is False
    fields = {p["field"] for p in status["prerequisites"]}
    assert "valid_bids" in fields

    # 4c. 시드: IOI 입찰 (이전 단계에서 만든 buyer_a_id 재사용)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={
            "buyer_candidate_id": buyer_a_id,
            "bid_type": "IOI",
            "amount": 50_000_000_000,
        },
    )
    assert resp.status_code == 201

    # 4d. advance → 성공
    result = await _advance(client, txn_id, "MAIN_DUE_DILIGENCE")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "MAIN_DUE_DILIGENCE"

    # ── Step 5: MAIN_DUE_DILIGENCE → NEGOTIATION ─────────
    # (게이트: DD 완료율 80% 이상. 항목 0개 = non-blocking)

    # 5a. 항목 0개 → satisfied=True이나 acknowledgement 필요
    status = await _get_phase_status(client, txn_id)
    dd_prereq = next(p for p in status["prerequisites"] if p["field"] == "dd_completion")
    assert dd_prereq["satisfied"] is True  # 항목 없음 = 조건 자체는 충족
    assert dd_prereq["requires_acknowledgement"] is True  # 확인 필요
    assert "항목 없음" in dd_prereq["current_value"]
    assert "dd_completion" in status["pending_acknowledgements"]

    # ack 없이 advance → 422
    result = await _advance(client, txn_id, "NEGOTIATION")
    assert result["status_code"] == 422

    # 5b. DD 항목 추가 → 미완료 상태 → 차단되는지 확인
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FDD_FINANCIAL_STATEMENTS", "title": "재무제표 검토"},
    )
    assert resp.status_code == 201
    dd_item_1 = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "LDD_CORPORATE", "title": "법인 구조 검토"},
    )
    assert resp.status_code == 201
    dd_item_2 = resp.json()["id"]

    # 0/2 = 0% < 80% → 차단
    result = await _advance(client, txn_id, "NEGOTIATION")
    assert result["status_code"] == 422

    # 5c. DD 항목 완료 (2/2 = 100% ≥ 80%)
    await client.patch(
        f"/api/v1/transactions/{txn_id}/dd-checklist/{dd_item_1}",
        json={"status": "COMPLETED"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/dd-checklist/{dd_item_2}",
        json={"status": "NOT_APPLICABLE"},
    )

    # 5d. advance → 성공
    result = await _advance(client, txn_id, "NEGOTIATION")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "NEGOTIATION"

    # ── Step 6: NEGOTIATION → CLOSING ─────────────────────
    # (게이트: SPA/BTA 계약 + Closing 체크리스트 + 리스크/컴플라이언스)

    # 6a. 시드 없이 시도 → 차단
    result = await _advance(client, txn_id, "CLOSING")
    assert result["status_code"] == 422

    # 6b. phase-status에서 미충족 확인
    status = await _get_phase_status(client, txn_id)
    assert status["all_met"] is False
    fields = {p["field"] for p in status["prerequisites"]}
    assert "contracts" in fields

    # 6c. 시드: SPA 계약
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"contract_type": "SPA", "title": "주식양수도계약서 초안"},
    )
    assert resp.status_code == 201

    # 6d. 시드: 부트스트랩 Closing 체크리스트 전체 COMPLETED 처리
    resp = await client.get(f"/api/v1/transactions/{txn_id}/closing")
    assert resp.status_code == 200
    closing_items = resp.json()
    for item in closing_items:
        if item["status"] != "COMPLETED":
            await client.patch(
                f"/api/v1/transactions/{txn_id}/closing/{item['id']}",
                json={"status": "COMPLETED"},
            )

    # 6e. advance → 성공
    result = await _advance(client, txn_id, "CLOSING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "CLOSING"

    # ── Step 7: CLOSING → POST_CLOSING ────────────────────
    # (게이트 없음 — 직접 전환)
    result = await _advance(client, txn_id, "POST_CLOSING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "POST_CLOSING"

    # ── 최종 검증: POST_CLOSING 도달 ─────────────────────
    await _assert_phase(client, txn_id, "POST_CLOSING")

    # POST_CLOSING에서는 더 이상 전진 불가
    status = await _get_phase_status(client, txn_id)
    assert status["can_advance"] is False
    assert status["next_phase"] is None


# ── 보충 테스트: 롤백 후 재진입 ─────────────────────────────


@pytest.mark.asyncio
async def test_rollback_and_readvance(client: AsyncClient):
    """BIDDING → MARKETING 롤백 후, 기존 시드 데이터로 재진입 가능."""
    txn_id = await _create_active_txn(client)

    # ENGAGEMENT → PREPARATION → MARKETING
    await _advance(client, txn_id, "PREPARATION")
    await _advance(client, txn_id, "MARKETING")

    # 시드: short list buyer + NDA → BIDDING
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={"company_name": "롤백 테스트 매수자", "buyer_type": "STRATEGIC", "tier": "TIER_1"},
    )
    buyer_id = resp.json()["id"]
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
        json={"status": "CONTACTED"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
        json={"status": "NDA_SIGNED"},
    )

    result = await _advance(client, txn_id, "BIDDING")
    assert result["status_code"] == 200

    # 롤백: BIDDING → MARKETING
    result = await _advance(client, txn_id, "MARKETING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "MARKETING"

    # 기존 시드 데이터가 남아있으므로 재진입 가능
    result = await _advance(client, txn_id, "BIDDING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "BIDDING"


# ── 보충 테스트: Critical 리스크가 CLOSING 차단 ───────────────


@pytest.mark.asyncio
async def test_critical_risk_blocks_closing(client: AsyncClient):
    """Critical 리스크 미완화 시 CLOSING 진입 차단."""
    txn_id = await _create_active_txn(client)

    # NEGOTIATION까지 빠르게 진행
    await _advance(client, txn_id, "PREPARATION")
    await _advance(client, txn_id, "MARKETING")

    # BIDDING 시드
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={"company_name": "리스크 테스트 매수자", "buyer_type": "FINANCIAL_SPONSOR", "tier": "TIER_1"},
    )
    buyer_id = resp.json()["id"]
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
        json={"status": "CONTACTED"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
        json={"status": "NDA_SIGNED"},
    )
    await _advance(client, txn_id, "BIDDING")

    # DD 시드
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI", "amount": 10_000_000_000},
    )
    await _advance(client, txn_id, "MAIN_DUE_DILIGENCE")

    # NEGOTIATION 진입 (DD 0건 = acknowledgement 필요)
    await _advance(client, txn_id, "NEGOTIATION", acknowledgements={"dd_completion": True})

    # CLOSING 시드: 계약 + 체크리스트
    await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"contract_type": "SPA", "title": "SPA"},
    )
    resp = await client.get(f"/api/v1/transactions/{txn_id}/closing")
    for item in resp.json():
        if item["status"] != "COMPLETED":
            await client.patch(
                f"/api/v1/transactions/{txn_id}/closing/{item['id']}",
                json={"status": "COMPLETED"},
            )

    # Critical 리스크 추가 → 차단
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/risks",
        json={
            "title": "규제 승인 불확실성",
            "description": "공정위 기업결합 심사 결과 불확실",
            "severity": "CRITICAL",
            "category": "REGULATORY",
        },
    )
    assert resp.status_code == 201
    risk_id = resp.json()["id"]

    # CLOSING 차단 확인
    result = await _advance(client, txn_id, "CLOSING")
    assert result["status_code"] == 422

    status = await _get_phase_status(client, txn_id)
    risk_prereq = next(p for p in status["prerequisites"] if p["field"] == "critical_risks")
    assert risk_prereq["satisfied"] is False
    assert "1건" in risk_prereq["current_value"]

    # 리스크 완화 → 차단 해제
    await client.patch(
        f"/api/v1/transactions/{txn_id}/risks/{risk_id}",
        json={"status": "MITIGATED"},
    )

    result = await _advance(client, txn_id, "CLOSING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "CLOSING"


# ── 보충 테스트: Phase Gate current_value/target_value 누적 검증 ──


@pytest.mark.asyncio
async def test_phase_status_values_accumulate(client: AsyncClient):
    """여러 단계를 거치면서 current_value가 정확히 누적되는지 확인."""
    txn_id = await _create_active_txn(client)
    await _advance(client, txn_id, "PREPARATION")
    await _advance(client, txn_id, "MARKETING")

    # buyer 2명 추가 (둘 다 TIER_1 short list)
    for name in ["매수자 A", "매수자 B"]:
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/buyers",
            json={"company_name": name, "buyer_type": "STRATEGIC", "tier": "TIER_1"},
        )
        b_id = resp.json()["id"]
        await client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{b_id}",
            json={"status": "CONTACTED"},
        )
        await client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{b_id}",
            json={"status": "NDA_SIGNED"},
        )

    status = await _get_phase_status(client, txn_id)
    sl_prereq = next(p for p in status["prerequisites"] if p["field"] == "short_list_buyers")
    assert sl_prereq["satisfied"] is True
    assert "2명" in sl_prereq["current_value"]  # 누적 확인

    nda_prereq = next(p for p in status["prerequisites"] if p["field"] == "nda_or_distribution")
    assert nda_prereq["satisfied"] is True
    assert "NDA 2건" in nda_prereq["current_value"]  # 누적 확인
