"""8단계 워크플로우 상태 머신 API 테스트."""

# 전제 조건을 모두 충족하는 거래 데이터
FULL_TXN = {
    "name": "워크플로우 테스트",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
    "deal_captain_email": "captain@example.com",
    "industry": "Tech",
    "deal_structure": "SHARE_ACQUISITION",
    "estimated_deal_value": 1000000000,
}


async def _create_active_txn(client) -> str:
    """ACTIVE 상태의 거래를 생성하는 헬퍼."""
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]
    # DRAFT → ACTIVE
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    return txn_id


# ── Phase Status ───────────────────────────────────────────
async def test_phase_status_initial(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_phase"] == "ENGAGEMENT"
    assert data["next_phase"] == "PREPARATION"
    assert data["previous_phase"] is None


async def test_phase_status_fields(client):
    """phase-status 응답에 필수 필드 포함 확인."""
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "all_met" in data
    assert "can_advance" in data
    for prereq in data["prerequisites"]:
        assert "field" in prereq
        assert "label" in prereq
        assert "satisfied" in prereq


# ── Status Change ──────────────────────────────────────────
async def test_status_draft_to_active(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"


async def test_status_draft_to_terminated(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "TERMINATED", "reason": "딜 취소"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "TERMINATED"


async def test_status_invalid_transition(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    # DRAFT → COMPLETED (불가)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "COMPLETED"},
    )
    assert resp.status_code == 422


async def test_status_active_to_on_hold(client):
    txn_id = await _create_active_txn(client)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ON_HOLD", "reason": "고객 요청"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ON_HOLD"


async def test_status_on_hold_to_active(client):
    txn_id = await _create_active_txn(client)

    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ON_HOLD"},
    )
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"


async def test_status_completed_is_terminal(client):
    txn_id = await _create_active_txn(client)

    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "COMPLETED"},
    )
    # COMPLETED → ACTIVE (불가)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    assert resp.status_code == 422


# ── Phase Advance ──────────────────────────────────────────
async def test_advance_engagement_to_preparation(client):
    txn_id = await _create_active_txn(client)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "PREPARATION"},
    )
    assert resp.status_code == 200
    assert resp.json()["phase"] == "PREPARATION"


async def test_advance_skip_phase_fails(client):
    txn_id = await _create_active_txn(client)

    # ENGAGEMENT → MARKETING (2단계 건너뛰기 — 불가)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "MARKETING"},
    )
    assert resp.status_code == 422


async def test_advance_requires_active_status(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    # DRAFT 상태에서 advance 시도
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "PREPARATION"},
    )
    assert resp.status_code == 422


# ── Phase Rollback ─────────────────────────────────────────
async def test_rollback_phase(client):
    txn_id = await _create_active_txn(client)

    # ENGAGEMENT → PREPARATION
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "PREPARATION"},
    )
    # PREPARATION → ENGAGEMENT (롤백)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "ENGAGEMENT"},
    )
    assert resp.status_code == 200
    assert resp.json()["phase"] == "ENGAGEMENT"


# ── Multi-phase Advance ───────────────────────────────────
async def _seed_gate_data_for_phase(client, txn_id: str, target_phase: str) -> None:
    """target_phase 진입에 필요한 최소 시드 데이터를 생성한다."""
    if target_phase == "BIDDING":
        # Short List buyer + NDA
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/buyers",
            json={"company_name": "시드 매수자", "buyer_type": "STRATEGIC", "tier": "TIER_1"},
        )
        buyer_id = resp.json()["id"]
        # IDENTIFIED → CONTACTED → NDA_SIGNED (전이 규칙 준수)
        await client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
            json={"status": "CONTACTED"},
        )
        await client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
            json={"status": "NDA_SIGNED"},
        )
    elif target_phase == "MAIN_DUE_DILIGENCE":
        # 유효 입찰 1건
        resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers")
        buyer_id = resp.json()["items"][0]["id"]
        await client.post(
            f"/api/v1/transactions/{txn_id}/bids",
            json={"buyer_candidate_id": buyer_id, "bid_type": "IOI", "amount": 5000000000},
        )
    elif target_phase == "CLOSING":
        # SPA 계약 1건 + Closing 체크리스트 전체 COMPLETED
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


async def test_advance_through_multiple_phases(client):
    txn_id = await _create_active_txn(client)

    phases = [
        "PREPARATION",
        "MARKETING",
        "BIDDING",
        "MAIN_DUE_DILIGENCE",
        "NEGOTIATION",
        "CLOSING",
        "POST_CLOSING",
    ]
    for phase in phases:
        await _seed_gate_data_for_phase(client, txn_id, phase)
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": phase},
        )
        assert resp.status_code == 200, f"Advance to {phase} failed: {resp.text}"
        assert resp.json()["phase"] == phase


# ── 전제 조건 충족 시 all_met=True ──────────────────────
async def test_full_prerequisites_all_met(client):
    """모든 전제 조건 충족 시 all_met=True."""
    txn_id = await _create_active_txn(client)

    # ENGAGEMENT → PREPARATION
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "PREPARATION"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["all_met"] is True
    assert data["can_advance"] is True


# ── Milestone Upload (entity_id string 허용) ────────────
async def test_milestone_upload(client):
    """마일스톤 문서를 entity_type=MILESTONE, entity_id=문자열로 업로드."""
    txn_id = await _create_active_txn(client)

    import io

    pdf_bytes = b"%PDF-1.4 test content"
    files = {"file": ("mou.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {
        "entity_type": "MILESTONE",
        "entity_id": "MOU_SIGNED",
        "description": "Executed MOU",
    }
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/attachments",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["entity_type"] == "MILESTONE"
    assert body["entity_id"] == "MOU_SIGNED"


async def test_milestone_list_filter(client):
    """마일스톤 첨부파일을 entity_id 문자열로 필터 조회."""
    txn_id = await _create_active_txn(client)

    import io

    pdf_bytes = b"%PDF-1.4 test content"
    files = {"file": ("spa.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {
        "entity_type": "MILESTONE",
        "entity_id": "SIGNING",
        "description": "Executed SPA",
    }
    await client.post(
        f"/api/v1/transactions/{txn_id}/attachments",
        files=files,
        data=data,
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/attachments",
        params={"entity_type": "MILESTONE", "entity_id": "SIGNING"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert items[0]["entity_id"] == "SIGNING"


async def test_unsupported_phase_returns_422(client):
    """deprecated 단계(MOU_SIGNED) 거래의 phase-status 조회 시 422."""
    # 이 테스트는 workflow_engine의 방어 코드를 검증함.
    # DB에 직접 MOU_SIGNED를 설정할 수 없으므로 잘못된 단계 전환 시도로 확인.
    txn_id = await _create_active_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "MOU_SIGNED"},
    )
    # MOU_SIGNED는 _PHASE_ORDER에 없으므로 422 (잘못된 단계)
    assert resp.status_code == 422


async def test_magic_bytes_mismatch_rejected(client):
    """확장자와 매직바이트가 불일치하면 400."""
    txn_id = await _create_active_txn(client)

    import io

    # PNG 매직바이트를 가진 파일을 .pdf 확장자로 업로드
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
    files = {"file": ("fake.pdf", io.BytesIO(png_header), "application/pdf")}
    data = {"entity_type": "MILESTONE", "entity_id": "MOU_SIGNED"}
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/attachments",
        files=files,
        data=data,
    )
    assert resp.status_code == 400
    assert "일치하지 않습니다" in resp.json()["detail"]
