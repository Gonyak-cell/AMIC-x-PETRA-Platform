"""Dashboard API 테스트 — KPI 통계."""


async def test_dashboard_stats_empty(client):
    """거래 없는 상태에서 대시보드 통계 정상 응답."""
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_transactions"] == 0
    assert data["active_transactions"] == 0
    assert data["total_deal_value"] in (0, None)


async def test_dashboard_stats_with_transactions(client, transaction_id):
    """거래 생성 후 통계 반영 확인."""
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_transactions"] >= 1
    assert "by_phase" in data
    assert "by_status" in data
    assert "by_side" in data


async def test_dashboard_stats_by_phase_structure(client, transaction_id):
    """by_phase 필드가 올바른 구조를 갖는지 확인."""
    resp = await client.get("/api/v1/dashboard/stats")
    data = resp.json()
    assert isinstance(data["by_phase"], list)
    if data["by_phase"]:
        phase = data["by_phase"][0]
        assert "phase" in phase
        assert "count" in phase


async def test_dashboard_stats_recent_activity(client, transaction_id):
    """recent_activity_count 필드 존재 확인."""
    resp = await client.get("/api/v1/dashboard/stats")
    data = resp.json()
    assert "recent_activity_count" in data
    assert isinstance(data["recent_activity_count"], int)


async def test_docs_stats(client, transaction_id):
    """문서 통계 엔드포인트 정상 응답."""
    resp = await client.get("/api/v1/dashboard/docs-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
