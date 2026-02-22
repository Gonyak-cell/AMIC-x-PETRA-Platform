"""어닝아웃 마일스톤 라우터 테스트."""

from httpx import AsyncClient


async def test_create_earnout(client: AsyncClient, transaction_id: str):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/earnout",
        json={
            "title": "2026 매출 달성",
            "metric": "REVENUE",
            "target_value": 5000000000,
            "currency": "KRW",
            "measurement_start": "2026-01-01",
            "measurement_end": "2026-12-31",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "2026 매출 달성"
    assert data["metric"] == "REVENUE"
    assert float(data["target_value"]) == 5000000000
    assert data["status"] == "PENDING"


async def test_create_earnout_minimal(client: AsyncClient, transaction_id: str):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/earnout",
        json={
            "title": "EBITDA 조건",
            "metric": "EBITDA",
            "target_value": 1000000000,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["currency"] == "KRW"


async def test_list_earnout(client: AsyncClient, transaction_id: str):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/earnout",
        json={"title": "고객 수", "metric": "CUSTOMER_COUNT", "target_value": 1000},
    )
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/earnout")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_update_earnout_status(client: AsyncClient, transaction_id: str):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/earnout",
        json={"title": "순이익", "metric": "NET_INCOME", "target_value": 500000000},
    )
    ms_id = create.json()["id"]
    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/earnout/{ms_id}",
        json={"status": "MEASUREMENT_PERIOD"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "MEASUREMENT_PERIOD"


async def test_update_earnout_actual(client: AsyncClient, transaction_id: str):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/earnout",
        json={"title": "운전자본", "metric": "WORKING_CAPITAL", "target_value": 2000000000},
    )
    ms_id = create.json()["id"]
    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/earnout/{ms_id}",
        json={
            "actual_value": 2500000000,
            "status": "ACHIEVED",
            "payment_amount": 300000000,
            "payment_date": "2027-03-15",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACHIEVED"
    assert float(data["actual_value"]) == 2500000000
    assert float(data["payment_amount"]) == 300000000


async def test_update_earnout_404(client: AsyncClient, transaction_id: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/earnout/{fake_id}",
        json={"status": "ACHIEVED"},
    )
    assert resp.status_code == 404


async def test_delete_earnout(client: AsyncClient, transaction_id: str):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/earnout",
        json={"title": "삭제 대상", "metric": "OTHER", "target_value": 100},
    )
    ms_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/transactions/{transaction_id}/earnout/{ms_id}")
    assert resp.status_code == 204


async def test_earnout_summary(client: AsyncClient, transaction_id: str):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/earnout",
        json={"title": "매출 1", "metric": "REVENUE", "target_value": 1000000000},
    )
    ms2 = await client.post(
        f"/api/v1/transactions/{transaction_id}/earnout",
        json={
            "title": "매출 2",
            "metric": "REVENUE",
            "target_value": 2000000000,
            "payment_amount": 500000000,
        },
    )
    await client.patch(
        f"/api/v1/transactions/{transaction_id}/earnout/{ms2.json()['id']}",
        json={"actual_value": 2500000000, "status": "ACHIEVED"},
    )

    resp = await client.get(f"/api/v1/transactions/{transaction_id}/earnout/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert float(data["total_target"]) >= 3000000000


async def test_earnout_summary_empty(client: AsyncClient, transaction_id: str):
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/earnout/summary")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 0
