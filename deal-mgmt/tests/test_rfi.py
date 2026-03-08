"""RFI V2 API 테스트 — 질의 원장 + 스레드 이력 기반."""

SAMPLE_TXN = {
    "name": "RFI 테스트 거래",
    "deal_type": "MA",
    "side": "SELL",
    "target_company_name": "RFI대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_item(client, txn_id: str, **kwargs) -> dict:
    payload = {
        "category": "FINANCIAL",
        "question_text": "최근 3개년 감사보고서를 제공해 주세요.",
        "priority": "MEDIUM",
        **kwargs,
    }
    resp = await client.post(f"/api/v1/transactions/{txn_id}/rfi/items", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── Item CRUD ──────────────────────────────────────────────


async def test_create_item(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    assert item["category"] == "FINANCIAL"
    assert item["current_status"] == "OPEN"
    assert item["priority"] == "MEDIUM"
    assert item["item_number"].startswith("RFI-")
    assert item["version"] == 0
    assert item["is_deleted"] is False


async def test_list_items(client):
    txn_id = await _create_txn(client)
    await _create_item(client, txn_id, question_text="질문1")
    await _create_item(client, txn_id, category="LEGAL", question_text="소송 이력")

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfi/items")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_items_filter_category(client):
    txn_id = await _create_txn(client)
    await _create_item(client, txn_id, category="FINANCIAL", question_text="재무 질문")
    await _create_item(client, txn_id, category="LEGAL", question_text="법률 질문")

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/rfi/items",
        params={"category": "FINANCIAL"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["category"] == "FINANCIAL"


async def test_list_items_filter_status(client):
    txn_id = await _create_txn(client)
    await _create_item(client, txn_id)

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/rfi/items",
        params={"status": "OPEN"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_item_detail(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_text"] == "최근 3개년 감사보고서를 제공해 주세요."
    assert data["threads"] == []
    assert data["attachments"] == []


async def test_update_item(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}",
        json={"priority": "HIGH", "version": item["version"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] == "HIGH"
    assert data["version"] == item["version"] + 1


async def test_update_item_optimistic_lock_conflict(client):
    """낙관적 락 충돌 시 409."""
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    # 첫 번째 수정 성공
    resp1 = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}",
        json={"priority": "HIGH", "version": item["version"]},
    )
    assert resp1.status_code == 200

    # 같은 버전으로 다시 수정 시도 → 409
    resp2 = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}",
        json={"priority": "LOW", "version": item["version"]},
    )
    assert resp2.status_code == 409


async def test_delete_item(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}")
    assert resp.status_code == 204

    # 삭제 후 목록에서 안 보임
    resp2 = await client.get(f"/api/v1/transactions/{txn_id}/rfi/items")
    assert len(resp2.json()) == 0


async def test_delete_non_open_item_fails(client):
    """OPEN이 아닌 상태의 아이템 삭제 시 400."""
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    # CLOSED로 전환
    await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/close",
        params={"version": item["version"]},
    )

    # 삭제 시도 → 400
    resp = await client.delete(f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}")
    assert resp.status_code == 400


# ── Batch Create ──────────────────────────────────────────


async def test_batch_create_items(client):
    txn_id = await _create_txn(client)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfi/items/batch",
        json={
            "items": [
                {"category": "FINANCIAL", "question_text": "감사보고서"},
                {"category": "TAX", "question_text": "세무 신고 내역"},
                {"category": "LEGAL", "question_text": "소송 이력", "priority": "HIGH"},
            ]
        },
    )
    assert resp.status_code == 201
    items = resp.json()
    assert len(items) == 3
    assert items[2]["priority"] == "HIGH"


# ── Close Item ────────────────────────────────────────────


async def test_close_item(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/close",
        params={"version": item["version"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_status"] == "CLOSED"
    assert data["version"] == item["version"] + 1


async def test_close_item_version_conflict(client):
    """잘못된 버전으로 close 시도 → 409."""
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/close",
        params={"version": 999},
    )
    assert resp.status_code == 409


# ── Thread CRUD ──────────────────────────────────────────


async def test_create_thread(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/threads",
        json={"content_text": "감사보고서 첨부합니다.", "is_published": True},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content_text"] == "감사보고서 첨부합니다."
    assert data["round_num"] == 1
    assert data["is_published"] is True


async def test_list_threads(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    # 스레드 2개 생성
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/threads",
        json={"content_text": "1차 답변"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/threads",
        json={"content_text": "2차 답변"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/threads")
    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 2
    assert threads[0]["round_num"] == 1
    assert threads[1]["round_num"] == 2


async def test_thread_on_closed_item_fails(client):
    """CLOSED 상태에서 스레드 추가 시 400."""
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    # 마감
    await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/close",
        params={"version": item["version"]},
    )

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/threads",
        json={"content_text": "추가 답변"},
    )
    assert resp.status_code == 400


async def test_update_thread_publish(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id)

    # 임시 저장 (is_published=False)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/threads",
        json={"content_text": "임시 저장 답변", "is_published": False},
    )
    thread = resp.json()
    assert thread["is_published"] is False

    # 게시 전환
    resp2 = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{item['id']}/threads/{thread['id']}",
        json={"is_published": True},
    )
    assert resp2.status_code == 200
    assert resp2.json()["is_published"] is True


# ── Dashboard ────────────────────────────────────────────


async def test_dashboard(client):
    txn_id = await _create_txn(client)
    await _create_item(client, txn_id, category="FINANCIAL", question_text="재무 질문")
    await _create_item(client, txn_id, category="LEGAL", question_text="법률 질문")

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfi/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 2
    assert data["status_counts"]["OPEN"] == 2
    assert len(data["category_breakdown"]) == 2


async def test_dashboard_empty(client):
    txn_id = await _create_txn(client)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfi/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 0


# ── 404 ──────────────────────────────────────────────────


async def test_get_item_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfi/items/{fake_id}")
    assert resp.status_code == 404


async def test_update_item_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfi/items/{fake_id}",
        json={"priority": "HIGH", "version": 0},
    )
    assert resp.status_code == 404


# ── Search ───────────────────────────────────────────────


async def test_search_items(client):
    txn_id = await _create_txn(client)
    await _create_item(client, txn_id, question_text="감사보고서를 제공하세요")
    await _create_item(client, txn_id, question_text="소송 이력을 알려주세요")

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/rfi/items",
        params={"search": "감사보고서"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert "감사보고서" in resp.json()[0]["question_text"]


# ── Internal Memo ────────────────────────────────────────


async def test_create_item_with_internal_memo(client):
    txn_id = await _create_txn(client)
    item = await _create_item(client, txn_id, internal_memo="자문사 전용 메모입니다.")

    assert item["internal_memo"] == "자문사 전용 메모입니다."
