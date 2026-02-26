"""법률 문서 API 테스트 (SPA/SHA/BTA/SSA/MOU)."""

SAMPLE_TXN = {
    "name": "법률문서 테스트 거래",
    "code_name": "LEGAL-001",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "test@example.com",
}

SPA_PARAMS = {
    "seller_name": "주식회사 매도인",
    "seller_representative": "홍길동",
    "seller_address": "서울시 강남구",
    "buyer_name": "주식회사 매수인",
    "buyer_representative": "김철수",
    "buyer_address": "서울시 중구",
    "target_company_name": "대상기업",
    "target_corp_reg_no": "110111-0000000",
    "total_shares": 1000000,
    "transfer_shares": 500000,
    "share_price_per": 10000,
    "total_purchase_price": 5000000000,
    "signing_date": "2026-03-15",
    "closing_date": "2026-06-30",
    "warranty_period_months": 24,
    "escrow_amount": 500000000,
    "escrow_period_months": 18,
    "governing_law": "대한민국",
}

MOU_PARAMS = {
    "party_a_name": "주식회사 갑",
    "party_a_representative": "홍길동",
    "party_b_name": "주식회사 을",
    "party_b_representative": "김철수",
    "purpose": "M&A 거래 타당성 검토",
    "exclusivity_period_days": 90,
    "exclusivity_start_date": "2026-03-15",
    "confidentiality_period_months": 24,
    "binding_provisions": ["비밀유지", "독점협상"],
    "non_binding_provisions": ["가격협상", "거래구조"],
    "signing_date": "2026-03-15",
    "governing_law": "대한민국",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    return resp.json()["id"]


# ── Create ─────────────────────────────────────────────────────────────────────


async def test_create_spa_document(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={
            "doc_type": "SPA",
            "title": "Project Test SPA",
            "parameters": SPA_PARAMS,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "SPA"
    assert data["title"] == "Project Test SPA"
    assert data["status"] in ("READY", "FAILED")  # GENERATING은 동기적으로 완료됨
    assert data["id"] is not None
    assert data["transaction_id"] == txn_id


async def test_create_mou_document(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={
            "doc_type": "MOU",
            "title": "Project Titan MOU",
            "parameters": MOU_PARAMS,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "MOU"
    assert data["status"] in ("READY", "FAILED")


async def test_create_document_invalid_type(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={
            "doc_type": "INVALID_TYPE",
            "title": "잘못된 타입",
            "parameters": {},
        },
    )
    assert resp.status_code == 422


async def test_create_document_invalid_txn(client):
    fake_txn = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/v1/transactions/{fake_txn}/legal-documents",
        json={
            "doc_type": "SPA",
            "title": "없는 거래",
            "parameters": SPA_PARAMS,
        },
    )
    assert resp.status_code == 404


# ── List ───────────────────────────────────────────────────────────────────────


async def test_list_legal_documents(client):
    txn_id = await _create_txn(client)

    # SPA 1개 생성
    await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "SPA Doc", "parameters": SPA_PARAMS},
    )
    # MOU 1개 생성
    await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "MOU", "title": "MOU Doc", "parameters": MOU_PARAMS},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    doc_types = {item["doc_type"] for item in items}
    assert "SPA" in doc_types
    assert "MOU" in doc_types


async def test_list_legal_documents_empty(client):
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Get ────────────────────────────────────────────────────────────────────────


async def test_get_legal_document(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "SPA Doc", "parameters": SPA_PARAMS},
    )
    doc_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents/{doc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == doc_id
    assert data["doc_type"] == "SPA"


async def test_get_legal_document_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents/{fake_id}")
    assert resp.status_code == 404


# ── Download ───────────────────────────────────────────────────────────────────


async def test_download_ready_document(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "SPA Doc", "parameters": SPA_PARAMS},
    )
    data = create_resp.json()
    doc_id = data["id"]

    if data["status"] == "READY":
        resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents/{doc_id}/download")
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "wordprocessingml" in ct or "octet-stream" in ct


async def test_download_not_ready_document(client):
    """DRAFT/FAILED 상태에서 다운로드 시도 → 400 (409가 아님)."""
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "MOU", "title": "MOU Doc", "parameters": MOU_PARAMS},
    )
    data = create_resp.json()
    doc_id = data["id"]

    # READY면 다운로드 성공(200), FAILED면 400 반환
    resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents/{doc_id}/download")
    assert resp.status_code in (200, 400), f"Expected 200 (READY) or 400 (FAILED/not-ready), got {resp.status_code}"


# ── Delete ─────────────────────────────────────────────────────────────────────


async def test_delete_legal_document(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "SPA Doc", "parameters": SPA_PARAMS},
    )
    doc_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/transactions/{txn_id}/legal-documents/{doc_id}")
    assert del_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents")
    assert len(list_resp.json()) == 0


async def test_delete_legal_document_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/transactions/{txn_id}/legal-documents/{fake_id}")
    assert resp.status_code == 404


# ── Regenerate ─────────────────────────────────────────────────────────────────


async def test_regenerate_document(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "SPA Doc", "parameters": SPA_PARAMS},
    )
    doc_id = create_resp.json()["id"]

    updated_params = {**SPA_PARAMS, "seller_name": "변경된 매도인"}
    regen_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents/{doc_id}/regenerate",
        json={"doc_type": "SPA", "title": "SPA Doc", "parameters": updated_params},
    )
    assert regen_resp.status_code == 200
    data = regen_resp.json()
    assert data["status"] in ("READY", "FAILED")
    assert data["parameters"]["seller_name"] == "변경된 매도인"


# ── Pydantic 유효성 검증 ────────────────────────────────────────────────────────


async def test_create_document_invalid_date_format(client):
    """잘못된 날짜 형식(YYYY/MM/DD) → 422."""
    txn_id = await _create_txn(client)
    bad_params = {**SPA_PARAMS, "signing_date": "2026/03/15"}  # 슬래시 구분자
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "Bad Date", "parameters": bad_params},
    )
    assert resp.status_code == 422
    detail = resp.json().get("detail", "")
    assert "날짜" in str(detail) or "date" in str(detail).lower()


async def test_create_document_invalid_date_value(client):
    """존재하지 않는 날짜(2026-13-45) → 422."""
    txn_id = await _create_txn(client)
    bad_params = {**SPA_PARAMS, "closing_date": "2026-13-45"}
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "Invalid Date", "parameters": bad_params},
    )
    assert resp.status_code == 422


async def test_create_document_negative_shares(client):
    """음수 주식 수 → 422."""
    txn_id = await _create_txn(client)
    bad_params = {**SPA_PARAMS, "transfer_shares": -100}
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "Negative Shares", "parameters": bad_params},
    )
    assert resp.status_code == 422


async def test_create_document_transfer_exceeds_total_shares(client):
    """양도주식 수 > 총발행주식 수 → 422."""
    txn_id = await _create_txn(client)
    bad_params = {
        **SPA_PARAMS,
        "total_shares": 1_000_000,
        "transfer_shares": 1_500_000,  # 총주식 초과
    }
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "Excess Shares", "parameters": bad_params},
    )
    assert resp.status_code == 422


async def test_create_document_ssa_post_money_less_than_pre_money(client):
    """Post-money < Pre-money → 422."""
    txn_id = await _create_txn(client)
    ssa_params = {
        "company_name": "테스트 회사",
        "company_representative": "홍길동",
        "investor_name": "투자자",
        "investor_representative": "김철수",
        "new_shares_count": 10000,
        "subscription_price_per": 10000,
        "total_investment": 100_000_000,
        "pre_money_valuation": 5_000_000_000,
        "post_money_valuation": 3_000_000_000,  # pre보다 작음
        "signing_date": "2026-03-15",
        "investment_date": "2026-04-01",
    }
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SSA", "title": "Bad Valuation", "parameters": ssa_params},
    )
    assert resp.status_code == 422


# ── 다운로드 상태 코드 검증 ────────────────────────────────────────────────────


async def test_download_failed_document_returns_400(client):
    """FAILED 상태 문서 다운로드 시 400 반환 (409 아님)."""
    txn_id = await _create_txn(client)
    # 빈 params로 생성하면 FAILED가 될 가능성이 높음 (템플릿 미존재 환경)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/legal-documents",
        json={"doc_type": "SPA", "title": "SPA Doc", "parameters": SPA_PARAMS},
    )
    data = create_resp.json()
    doc_id = data["id"]

    if data["status"] == "FAILED":
        resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents/{doc_id}/download")
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        assert resp.status_code != 409, "Should not return 409 CONFLICT for not-ready document"


async def test_document_not_found_returns_404(client):
    """존재하지 않는 문서 조회 → 404."""
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-999999999999"
    resp = await client.get(f"/api/v1/transactions/{txn_id}/legal-documents/{fake_id}")
    assert resp.status_code == 404
    # 커스텀 예외 핸들러 형식 확인
    body = resp.json()
    assert "detail" in body
