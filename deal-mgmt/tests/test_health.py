"""Health check 엔드포인트 테스트."""


async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "deal-mgmt"
    assert "ocr" in data
    assert "available" in data["ocr"]
