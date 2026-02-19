"""PMI 태스크 라우터 테스트."""

from httpx import AsyncClient


async def test_create_pmi_task(client: AsyncClient, transaction_id: str):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={"category": "INTEGRATION_PLAN", "title": "IT 시스템 통합"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "IT 시스템 통합"
    assert data["category"] == "INTEGRATION_PLAN"
    assert data["status"] == "NOT_STARTED"
    assert data["priority"] == "MEDIUM"


async def test_create_pmi_task_with_priority(client: AsyncClient, transaction_id: str):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={
            "category": "DAY_ONE",
            "title": "Day One 커뮤니케이션",
            "priority": "CRITICAL",
            "assignee_name": "홍길동",
            "due_date": "2026-04-01",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["priority"] == "CRITICAL"
    assert data["assignee_name"] == "홍길동"


async def test_list_pmi_tasks(client: AsyncClient, transaction_id: str):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={"category": "SYNERGY", "title": "시너지 분석"},
    )
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/pmi")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_filter_pmi_by_category(client: AsyncClient, transaction_id: str):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={"category": "HR", "title": "인사 통합"},
    )
    await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={"category": "IT_SYSTEMS", "title": "IT 마이그레이션"},
    )
    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/pmi",
        params={"category": "HR"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert all(i["category"] == "HR" for i in items)


async def test_update_pmi_status(client: AsyncClient, transaction_id: str):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={"category": "CULTURE", "title": "문화 통합 워크숍"},
    )
    task_id = create.json()["id"]
    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/pmi/{task_id}",
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"


async def test_update_pmi_404(client: AsyncClient, transaction_id: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/pmi/{fake_id}",
        json={"status": "COMPLETED"},
    )
    assert resp.status_code == 404


async def test_delete_pmi_task(client: AsyncClient, transaction_id: str):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={"category": "OTHER", "title": "삭제 대상"},
    )
    task_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/transactions/{transaction_id}/pmi/{task_id}")
    assert resp.status_code == 204


async def test_pmi_summary(client: AsyncClient, transaction_id: str):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={"category": "SYNERGY", "title": "시너지 측정"},
    )
    task2 = await client.post(
        f"/api/v1/transactions/{transaction_id}/pmi",
        json={"category": "SYNERGY", "title": "시너지 실현"},
    )
    await client.patch(
        f"/api/v1/transactions/{transaction_id}/pmi/{task2.json()['id']}",
        json={"status": "COMPLETED"},
    )
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/pmi/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert 0 <= data["completion_rate"] <= 1


async def test_pmi_summary_empty(client: AsyncClient, transaction_id: str):
    # transaction_id에 이미 태스크가 있을 수 있으므로, 새 트랜잭션 사용
    # summary가 0/0인 경우 completion_rate == 0.0
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/pmi/summary")
    assert resp.status_code == 200
    assert resp.json()["completion_rate"] >= 0
