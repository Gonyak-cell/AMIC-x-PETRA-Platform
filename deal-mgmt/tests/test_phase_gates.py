"""Phase Gate Validator 단위 테스트.

각 gate validator가 조건 충족/미충족에서 올바른 결과를 반환하는지,
gate 미충족 시 advance가 차단되는지 검증한다.
"""

from httpx import AsyncClient

# 전제 조건을 모두 충족하는 거래 데이터
FULL_TXN = {
    "name": "게이트 테스트",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_active_txn(client: AsyncClient) -> str:
    """ACTIVE 상태 거래 생성 헬퍼."""
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    return txn_id


async def _advance_to(client: AsyncClient, txn_id: str, target_phase: str) -> None:
    """지정 단계까지 순차 진행 (게이트 시드 데이터 포함)."""
    phase_order = [
        "ENGAGEMENT",
        "PREPARATION",
        "MARKETING",
        "BIDDING",
        "MAIN_DUE_DILIGENCE",
        "NEGOTIATION",
        "CLOSING",
        "POST_CLOSING",
    ]
    # 현재 phase 확인
    resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
    current = resp.json()["current_phase"]
    current_idx = phase_order.index(current)
    target_idx = phase_order.index(target_phase)

    for i in range(current_idx, target_idx):
        next_phase = phase_order[i + 1]
        # 게이트 시드 데이터 추가
        await _seed_gate_data(client, txn_id, next_phase)
        body: dict = {"to_phase": next_phase}
        # 빈 체크리스트 acknowledgement (DD 0건, Closing 0건 대응)
        if next_phase == "NEGOTIATION":
            body["acknowledgements"] = {"dd_completion": True}
        elif next_phase == "CLOSING":
            body["acknowledgements"] = {"closing_checklist": True}
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json=body,
        )
        assert resp.status_code == 200, f"Advance to {next_phase} failed: {resp.text}"


async def _seed_gate_data(client: AsyncClient, txn_id: str, target_phase: str) -> None:
    """target_phase 진입에 필요한 시드 데이터를 생성한다."""
    if target_phase == "BIDDING":
        await _seed_bidding_gate(client, txn_id)
    elif target_phase == "MAIN_DUE_DILIGENCE":
        await _seed_dd_gate(client, txn_id)
    elif target_phase == "NEGOTIATION":
        # DD 항목 0개 → non-blocking, 별도 시드 불필요
        pass
    elif target_phase == "CLOSING":
        await _seed_closing_gate(client, txn_id)


async def _seed_bidding_gate(client: AsyncClient, txn_id: str) -> None:
    """BIDDING 진입: short list buyer + NDA 체결."""
    # buyer 생성 (TIER_1 → is_short_listed=True 자동 동기화)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={
            "company_name": "게이트 테스트 매수자",
            "buyer_type": "STRATEGIC",
            "tier": "TIER_1",
        },
    )
    assert resp.status_code == 201
    buyer_id = resp.json()["id"]

    # buyer status: IDENTIFIED → CONTACTED → NDA_SIGNED (전이 규칙 준수)
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
        json={"status": "CONTACTED"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
        json={"status": "NDA_SIGNED"},
    )


async def _seed_dd_gate(client: AsyncClient, txn_id: str) -> None:
    """MAIN_DD 진입: 유효 입찰 1건."""
    # buyer가 필요 (bid는 buyer_candidate_id 필수)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers")
    buyers = resp.json()["items"]
    if not buyers:
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/buyers",
            json={"company_name": "입찰자", "buyer_type": "FINANCIAL_SPONSOR"},
        )
        buyer_id = resp.json()["id"]
    else:
        buyer_id = buyers[0]["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={
            "buyer_candidate_id": buyer_id,
            "bid_type": "IOI",
            "amount": 5000000000,
        },
    )
    assert resp.status_code == 201


async def _seed_closing_gate(client: AsyncClient, txn_id: str) -> None:
    """CLOSING 진입: SPA 계약 1건 + 기존 Closing 체크리스트 전체 COMPLETED."""
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={
            "contract_type": "SPA",
            "title": "주식양수도계약서",
        },
    )
    assert resp.status_code == 201

    # 표준 Closing 체크리스트(bootstrap 자동 생성)를 전부 COMPLETED 처리
    resp = await client.get(f"/api/v1/transactions/{txn_id}/closing")
    for item in resp.json():
        if item["status"] != "COMPLETED":
            await client.patch(
                f"/api/v1/transactions/{txn_id}/closing/{item['id']}",
                json={"status": "COMPLETED"},
            )


# ── BIDDING Gate Tests ───────────────────────────────────────


class TestBiddingGate:
    """MARKETING → BIDDING 게이트 검증."""

    async def test_bidding_blocked_without_short_list(self, client: AsyncClient):
        """Short List 매수자 없이 BIDDING 진입 시도 → 차단."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MARKETING")

        # 게이트 시드 없이 advance 시도
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "BIDDING"},
        )
        assert resp.status_code == 422

    async def test_bidding_gate_status_shows_unmet(self, client: AsyncClient):
        """MARKETING 단계에서 phase-status가 미충족 조건을 표시."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MARKETING")

        resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["all_met"] is False
        assert data["can_advance"] is False

        # prerequisites에 short_list_buyers, nda_or_distribution 존재
        fields = {p["field"] for p in data["prerequisites"]}
        assert "short_list_buyers" in fields
        assert "nda_or_distribution" in fields

        # gate_summary 존재
        assert data["gate_summary"] is not None
        assert "Short List" in data["gate_summary"]

    async def test_bidding_passes_with_seed(self, client: AsyncClient):
        """Short List + NDA 시드 후 BIDDING 진입 성공."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MARKETING")
        await _seed_bidding_gate(client, txn_id)

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "BIDDING"},
        )
        assert resp.status_code == 200
        assert resp.json()["phase"] == "BIDDING"

    async def test_bidding_current_value_displayed(self, client: AsyncClient):
        """Phase-status에서 current_value/target_value 표시 확인."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MARKETING")
        await _seed_bidding_gate(client, txn_id)

        resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
        data = resp.json()
        for prereq in data["prerequisites"]:
            if prereq["field"] == "short_list_buyers":
                assert prereq["satisfied"] is True
                assert "1명" in prereq["current_value"]
                assert prereq["target_value"] is not None


# ── MAIN_DUE_DILIGENCE Gate Tests ────────────────────────────


class TestDDGate:
    """BIDDING → MAIN_DUE_DILIGENCE 게이트 검증."""

    async def test_dd_blocked_without_bid(self, client: AsyncClient):
        """유효 입찰 없이 DD 진입 시도 → 차단."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "BIDDING")

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "MAIN_DUE_DILIGENCE"},
        )
        assert resp.status_code == 422

    async def test_dd_passes_with_bid(self, client: AsyncClient):
        """IOI 입찰 시드 후 DD 진입 성공."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "BIDDING")
        await _seed_dd_gate(client, txn_id)

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "MAIN_DUE_DILIGENCE"},
        )
        assert resp.status_code == 200
        assert resp.json()["phase"] == "MAIN_DUE_DILIGENCE"


# ── NEGOTIATION Gate Tests ───────────────────────────────────


class TestNegotiationGate:
    """DD → NEGOTIATION 게이트 검증 (DD 항목 0개 = non-blocking)."""

    async def test_negotiation_requires_ack_for_empty_dd(self, client: AsyncClient):
        """DD 체크리스트 0건: acknowledgement 없이 advance → 422."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MAIN_DUE_DILIGENCE")

        # phase-status에서 pending_acknowledgements 확인
        status_resp = await client.get(
            f"/api/v1/transactions/{txn_id}/workflow/phase-status",
        )
        assert status_resp.status_code == 200
        assert "dd_completion" in status_resp.json()["pending_acknowledgements"]

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "NEGOTIATION"},
        )
        assert resp.status_code == 422

    async def test_negotiation_passes_with_ack_for_empty_dd(self, client: AsyncClient):
        """DD 체크리스트 0건: acknowledgement 포함 시 통과."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MAIN_DUE_DILIGENCE")

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "NEGOTIATION", "acknowledgements": {"dd_completion": True}},
        )
        assert resp.status_code == 200
        assert resp.json()["phase"] == "NEGOTIATION"

    async def test_negotiation_blocked_with_incomplete_dd(self, client: AsyncClient):
        """DD 체크리스트 존재하나 미완료 시 차단."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MAIN_DUE_DILIGENCE")

        # DD 항목 생성 (NOT_STARTED 상태)
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/dd-checklist",
            json={
                "workstream": "FDD_FINANCIAL_STATEMENTS",
                "title": "재무제표 검토",
            },
        )
        assert resp.status_code == 201

        # 미완료 상태에서 advance 시도 → 차단 (1/1 = 0% < 80%)
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "NEGOTIATION"},
        )
        assert resp.status_code == 422

    async def test_negotiation_passes_with_completed_dd(self, client: AsyncClient):
        """DD 체크리스트 완료 후 통과."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MAIN_DUE_DILIGENCE")

        # DD 항목 생성
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/dd-checklist",
            json={
                "workstream": "FDD_FINANCIAL_STATEMENTS",
                "title": "재무제표 검토",
            },
        )
        item_id = resp.json()["id"]

        # COMPLETED로 변경
        await client.patch(
            f"/api/v1/transactions/{txn_id}/dd-checklist/{item_id}",
            json={"status": "COMPLETED"},
        )

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "NEGOTIATION"},
        )
        assert resp.status_code == 200
        assert resp.json()["phase"] == "NEGOTIATION"


# ── CLOSING Gate Tests ───────────────────────────────────────


class TestClosingGate:
    """NEGOTIATION → CLOSING 게이트 검증."""

    async def test_closing_blocked_without_contract(self, client: AsyncClient):
        """SPA/BTA 계약 없이 CLOSING 진입 시도 → 차단."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "NEGOTIATION")

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "CLOSING"},
        )
        assert resp.status_code == 422

    async def test_closing_passes_with_contract(self, client: AsyncClient):
        """SPA 계약 시드 후 CLOSING 진입 성공."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "NEGOTIATION")
        await _seed_closing_gate(client, txn_id)

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "CLOSING"},
        )
        assert resp.status_code == 200
        assert resp.json()["phase"] == "CLOSING"

    async def test_closing_blocked_with_incomplete_checklist(self, client: AsyncClient):
        """Closing 체크리스트 존재하나 미완료 시 차단."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "NEGOTIATION")

        # 계약 시드 (계약 gate는 통과)
        await _seed_closing_gate(client, txn_id)

        # Closing 체크리스트 생성 (PENDING 상태)
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/closing",
            json={
                "category": "LEGAL",
                "title": "최종 서명 확인",
            },
        )
        assert resp.status_code == 201

        # 미완료 체크리스트 → 차단
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "CLOSING"},
        )
        assert resp.status_code == 422

    async def test_closing_passes_with_completed_checklist(self, client: AsyncClient):
        """Closing 체크리스트 완료 후 통과."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "NEGOTIATION")
        await _seed_closing_gate(client, txn_id)

        # Closing 체크리스트 생성 + COMPLETED
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/closing",
            json={"category": "LEGAL", "title": "최종 서명 확인"},
        )
        item_id = resp.json()["id"]

        await client.patch(
            f"/api/v1/transactions/{txn_id}/closing/{item_id}",
            json={"status": "COMPLETED"},
        )

        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": "CLOSING"},
        )
        assert resp.status_code == 200
        assert resp.json()["phase"] == "CLOSING"


# ── Schema Extension Tests ───────────────────────────────────


class TestSchemaExtensions:
    """PhasePrerequisite 및 PhaseCompletionStatus 스키마 확장 검증."""

    async def test_gate_summary_present(self, client: AsyncClient):
        """MARKETING 단계에서 gate_summary가 응답에 포함."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MARKETING")

        resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
        data = resp.json()
        assert "gate_summary" in data
        assert data["gate_summary"] is not None

    async def test_current_target_value_in_prerequisites(self, client: AsyncClient):
        """prerequisites에 current_value, target_value 필드 포함."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MARKETING")

        resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
        data = resp.json()
        for prereq in data["prerequisites"]:
            assert "current_value" in prereq
            assert "target_value" in prereq

    async def test_no_gate_summary_for_early_phases(self, client: AsyncClient):
        """ENGAGEMENT 단계에서는 gate_summary가 None."""
        txn_id = await _create_active_txn(client)

        resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
        data = resp.json()
        # ENGAGEMENT → PREPARATION: gate validator 없음
        assert data["gate_summary"] is None

    async def test_requires_user_acknowledgement_true_when_acks_pending(self, client: AsyncClient):
        """DD 0건 + ack 미제출 → requires_user_acknowledgement=True."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MAIN_DUE_DILIGENCE")

        resp = await client.get(
            f"/api/v1/transactions/{txn_id}/workflow/phase-status",
        )
        assert resp.status_code == 200
        data = resp.json()
        # DD 0건이면 dd_completion ack 필요
        assert data["requires_user_acknowledgement"] is True
        assert len(data["pending_acknowledgements"]) > 0

    async def test_requires_user_acknowledgement_false_when_no_acks(self, client: AsyncClient):
        """MARKETING 단계 (ack 불필요) → requires_user_acknowledgement=False."""
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MARKETING")

        resp = await client.get(
            f"/api/v1/transactions/{txn_id}/workflow/phase-status",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_user_acknowledgement"] is False
        assert len(data["pending_acknowledgements"]) == 0

    async def test_requires_user_acknowledgement_false_for_early_phase(self, client: AsyncClient):
        """ENGAGEMENT 단계 (gate 없음) → requires_user_acknowledgement=False."""
        txn_id = await _create_active_txn(client)

        resp = await client.get(
            f"/api/v1/transactions/{txn_id}/workflow/phase-status",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_user_acknowledgement"] is False
