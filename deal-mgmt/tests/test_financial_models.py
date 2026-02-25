"""재무모델 API + 체크리스트 테스트."""

import pytest

SAMPLE_TXN = {
    "name": "재무모델 테스트 거래",
    "code_name": "FM-001",
    "side": "SELL",
    "target_company_name": "테스트 대상기업",
    "client_name": "테스트 의뢰기업",
    "lead_advisor_email": "test@example.com",
}

DCF_BODY = {
    "model_type": "DCF",
    "title": "Project Alpha — DCF Valuation",
}

LBO_BODY = {
    "model_type": "LBO",
    "title": "Project Alpha — LBO Analysis",
}

FULL_BODY = {
    "model_type": "FULL",
    "title": "Project Alpha — Full Financial Model",
    "vdr_document_ids": ["doc-001", "doc-002"],
    "parameters": {"discount_rate": 0.1, "terminal_growth": 0.02},
}


@pytest.fixture
async def _txn(client):
    """테스트용 거래 생성."""
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def _other_txn(client):
    """격리 테스트용 두 번째 거래."""
    resp = await client.post(
        "/api/v1/transactions",
        json={
            **SAMPLE_TXN,
            "code_name": "FM-002",
            "name": "격리 테스트 거래",
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ── 모델 CRUD ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_financial_models_empty(client, _txn):
    """빈 재무모델 목록 조회."""
    txn_id = _txn["id"]
    resp = await client.get(f"/api/v1/transactions/{txn_id}/financial-models")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_dcf_model(client, _txn):
    """DCF 모델 생성 — PENDING_REVIEW 상태."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_type"] == "DCF"
    assert data["title"] == DCF_BODY["title"]
    assert data["status"] == "PENDING_REVIEW"
    assert data["transaction_id"] == txn_id
    assert data["version"] == 1


@pytest.mark.asyncio
async def test_create_lbo_model(client, _txn):
    """LBO 모델 생성."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=LBO_BODY,
    )
    assert resp.status_code == 201
    assert resp.json()["model_type"] == "LBO"


@pytest.mark.asyncio
async def test_create_full_model_with_params(client, _txn):
    """파라미터 + VDR 문서 ID 포함 FULL 모델 생성."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=FULL_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_type"] == "FULL"
    assert data["parameters"] is not None
    assert data["vdr_document_ids"] == ["doc-001", "doc-002"]


@pytest.mark.asyncio
async def test_get_financial_model(client, _txn):
    """단건 조회."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == fm_id


@pytest.mark.asyncio
async def test_get_financial_model_not_found(client, _txn):
    """존재하지 않는 모델 — 404."""
    txn_id = _txn["id"]
    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_financial_models(client, _txn):
    """생성 후 목록 조회."""
    txn_id = _txn["id"]
    await client.post(f"/api/v1/transactions/{txn_id}/financial-models", json=DCF_BODY)
    await client.post(f"/api/v1/transactions/{txn_id}/financial-models", json=LBO_BODY)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/financial-models")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_delete_financial_model(client, _txn):
    """모델 삭제 — 204."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}"
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}"
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_financial_model(client, _txn):
    """모델 재생성 — 버전 증가."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]
    assert create_resp.json()["version"] == 1

    regen_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/regenerate"
    )
    assert regen_resp.status_code == 200
    data = regen_resp.json()
    assert data["version"] == 2
    # VDR doc 없으면 즉시 PENDING_REVIEW (VDR 있으면 GENERATING → Celery 태스크)
    assert data["status"] == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_download_not_ready(client, _txn):
    """PENDING_REVIEW 상태 모델 다운로드 시도 — 404."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/download"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cross_transaction_isolation(client, _txn, _other_txn):
    """다른 거래의 모델에 접근 불가 — 404."""
    txn_id = _txn["id"]
    other_txn_id = _other_txn["id"]

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/transactions/{other_txn_id}/financial-models/{fm_id}"
    )
    assert resp.status_code == 404


# ── 체크리스트 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checklist_auto_created(client, _txn):
    """모델 생성 시 체크리스트가 자동 생성된다."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PENDING_REVIEW"
    assert data["total_items"] == 33  # FM_FIELD_REGISTRY 항목 수
    assert data["pending_count"] == 33  # 모두 AUTO_GENERATED
    assert len(data["items"]) == 33


@pytest.mark.asyncio
async def test_checklist_items_have_categories(client, _txn):
    """체크리스트 항목이 올바른 카테고리를 가진다."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    items = resp.json()["items"]
    categories = {item["category"] for item in items}
    assert "REVENUE_FORECAST" in categories
    assert "WACC_COMPONENTS" in categories
    assert "DCF_PARAMETERS" in categories
    assert "SENSITIVITY_MATRIX" in categories


@pytest.mark.asyncio
async def test_update_checklist_item(client, _txn):
    """체크리스트 항목 수정 — CONFIRMED."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    cl_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    item_id = cl_resp.json()["items"][0]["id"]

    update_resp = await client.put(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist/items/{item_id}",
        json={
            "status": "CONFIRMED",
            "user_value": "150,000,000",
        },
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["status"] == "CONFIRMED"
    assert data["user_value"] == "150,000,000"
    assert data["reviewed_by"] is not None


@pytest.mark.asyncio
async def test_update_checklist_item_corrected(client, _txn):
    """체크리스트 항목 수정 — CORRECTED."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    cl_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    item_id = cl_resp.json()["items"][0]["id"]

    update_resp = await client.put(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist/items/{item_id}",
        json={
            "status": "CORRECTED",
            "user_correction": "실적 기준 3년만 사용",
            "user_value": "120,000,000",
        },
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["status"] == "CORRECTED"
    assert data["user_correction"] == "실적 기준 3년만 사용"


@pytest.mark.asyncio
async def test_bulk_update_checklist_items(client, _txn):
    """체크리스트 항목 일괄 수정."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    cl_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    cl_data = cl_resp.json()
    cl_id = cl_data["id"]
    items = cl_data["items"][:3]

    bulk_body = {
        "items": [
            {"item_id": items[0]["id"], "status": "CONFIRMED", "user_value": "100"},
            {"item_id": items[1]["id"], "status": "CONFIRMED", "user_value": "200"},
            {"item_id": items[2]["id"], "status": "FLAGGED"},
        ]
    }
    resp = await client.put(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist/{cl_id}/bulk-update",
        json=bulk_body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    statuses = {d["status"] for d in data}
    assert "CONFIRMED" in statuses
    assert "FLAGGED" in statuses


@pytest.mark.asyncio
async def test_finalize_checklist(client, _txn):
    """체크리스트 Finalize — FINALIZED 상태."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    cl_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    cl_id = cl_resp.json()["id"]

    finalize_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist/{cl_id}/finalize",
        json={"notes": "Base case assumptions confirmed"},
    )
    assert finalize_resp.status_code == 200
    data = finalize_resp.json()
    assert data["status"] == "FINALIZED"
    assert data["notes"] == "Base case assumptions confirmed"
    assert data["finalized_by"] is not None


@pytest.mark.asyncio
async def test_finalize_checklist_sets_model_status(client, _txn):
    """Finalize 후 모델 상태가 FINALIZING으로 변경된다."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    cl_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    cl_id = cl_resp.json()["id"]

    await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist/{cl_id}/finalize",
    )

    fm_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}"
    )
    assert fm_resp.status_code == 200
    assert fm_resp.json()["status"] == "FINALIZING"


@pytest.mark.asyncio
async def test_checklist_summary_after_updates(client, _txn):
    """항목 수정 후 summary 카운트가 정확하다."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    cl_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    items = cl_resp.json()["items"]

    # 3개 CONFIRMED, 1개 CORRECTED, 1개 FLAGGED
    for i in range(3):
        await client.put(
            f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist/items/{items[i]['id']}",
            json={"status": "CONFIRMED", "user_value": str(i * 100)},
        )
    await client.put(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist/items/{items[3]['id']}",
        json={"status": "CORRECTED", "user_correction": "수정", "user_value": "999"},
    )
    await client.put(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist/items/{items[4]['id']}",
        json={"status": "FLAGGED"},
    )

    # 체크리스트 다시 조회
    cl_resp2 = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    data = cl_resp2.json()
    assert data["confirmed_count"] == 3
    assert data["corrected_count"] == 1
    assert data["flagged_count"] == 1
    assert data["pending_count"] == 33 - 5  # 나머지 AUTO_GENERATED
    assert data["total_items"] == 33


@pytest.mark.asyncio
async def test_delete_model_cascades_checklist(client, _txn):
    """모델 삭제 시 체크리스트도 CASCADE 삭제된다."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/financial-models",
        json=DCF_BODY,
    )
    fm_id = create_resp.json()["id"]

    # 체크리스트 존재 확인
    cl_resp = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    assert cl_resp.status_code == 200

    # 모델 삭제
    await client.delete(f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}")

    # 체크리스트도 삭제됨
    cl_resp2 = await client.get(
        f"/api/v1/transactions/{txn_id}/financial-models/{fm_id}/checklist"
    )
    assert cl_resp2.status_code == 404
