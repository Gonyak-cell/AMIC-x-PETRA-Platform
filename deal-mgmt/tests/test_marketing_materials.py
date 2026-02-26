"""마케팅 자료 API 테스트 (TM / DM / IM PPTX)."""

import pytest

SAMPLE_TXN = {
    "name": "마케팅자료 테스트 거래",
    "code_name": "MKTING-001",
    "side": "SELL",
    "target_company_name": "테스트 대상기업",
    "client_name": "테스트 의뢰기업",
    "lead_advisor_email": "test@example.com",
}

TM_BODY = {
    "doc_type": "TM",
    "title": "Project Alpha — Teaser Memo",
    "project_code": "ALPHA",
}

DM_BODY = {
    "doc_type": "DM",
    "title": "Project Alpha — Discussion Memo (가격 협의)",
    "project_code": "ALPHA",
}

IM_BODY = {
    "doc_type": "IM",
    "title": "Project Alpha — Information Memorandum",
    "project_code": "ALPHA",
}

CUSTOM_CONTENT = {
    "project_name": "PROJECT ALPHA",
    "memo_type": "Teaser Memo",
    "date": "March 2026",
    "company_name": "주식회사 페트라브릿지파트너스",
    "disclaimer": "본 자료는 기밀입니다.",
    "contact": "AMIC × PETRA",
    "slides": [
        {
            "layout": "MAIN",
            "title": "Investment Highlights",
            "body": [
                {
                    "type": "bullet",
                    "items": ["강점 1", "강점 2", "강점 3"],
                }
            ],
        }
    ],
}


@pytest.fixture
async def _txn(client):
    """테스트용 거래 생성 — conftest JWT 이메일과 일치."""
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
            "code_name": "MKTING-002",
            "name": "격리 테스트 거래",
            "lead_advisor_email": "test@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_list_marketing_materials_empty(client, _txn):
    """빈 마케팅 자료 목록 조회."""
    txn_id = _txn["id"]
    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_tm(client, _txn):
    """TM 생성 — GENERATING 상태로 즉시 반환."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "TM"
    assert data["title"] == TM_BODY["title"]
    assert data["project_code"] == "ALPHA"
    assert data["status"] == "GENERATING"
    assert data["transaction_id"] == txn_id


@pytest.mark.asyncio
async def test_create_dm(client, _txn):
    """DM 생성."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=DM_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "DM"


@pytest.mark.asyncio
async def test_create_im(client, _txn):
    """IM 생성."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=IM_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "IM"


@pytest.mark.asyncio
async def test_create_with_custom_content(client, _txn):
    """커스텀 콘텐츠 파라미터로 TM 생성."""
    txn_id = _txn["id"]
    body = {**TM_BODY, "parameters": CUSTOM_CONTENT}
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=body,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["parameters"] is not None


@pytest.mark.asyncio
async def test_get_marketing_material(client, _txn):
    """단건 조회."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == mat_id


@pytest.mark.asyncio
async def test_get_marketing_material_not_found(client, _txn):
    """존재하지 않는 자료 조회 — 404."""
    txn_id = _txn["id"]
    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_marketing_materials(client, _txn):
    """생성 후 목록 조회."""
    txn_id = _txn["id"]
    await client.post(f"/api/v1/transactions/{txn_id}/marketing-materials", json=TM_BODY)
    await client.post(f"/api/v1/transactions/{txn_id}/marketing-materials", json=DM_BODY)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_update_distribution(client, _txn):
    """배포 대상 목록 업데이트."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    dist_body = {
        "distributed_to": ["A투자사", "B펀드", "c@example.com"],
        "distributed_at": "2026-03-01T09:00:00+09:00",
    }
    resp = await client.put(
        f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}/distribute",
        json=dist_body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["distributed_to"]) == set(dist_body["distributed_to"])
    assert data["distributed_at"] == dist_body["distributed_at"]


@pytest.mark.asyncio
async def test_delete_marketing_material(client, _txn):
    """자료 삭제 — 204."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_download_not_ready(client, _txn):
    """GENERATING 상태 자료 다운로드 시도 — 409."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}/download")
    # GENERATING 상태이므로 409
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cross_transaction_isolation(client, _txn, _other_txn):
    """다른 거래의 자료는 접근 불가 — 404."""
    txn_id = _txn["id"]
    other_txn_id = _other_txn["id"]

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    # 다른 거래 ID로 접근
    resp = await client.get(f"/api/v1/transactions/{other_txn_id}/marketing-materials/{mat_id}")
    assert resp.status_code == 404
