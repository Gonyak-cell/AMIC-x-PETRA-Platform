"""Deal Notes API 테스트 — Phase 5A."""



# ── Create ─────────────────────────────────────────────────
async def test_create_note(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "첫 번째 코멘트입니다.", "note_type": "COMMENT"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "첫 번째 코멘트입니다."
    assert data["note_type"] == "COMMENT"
    assert data["is_pinned"] is False
    assert data["parent_id"] is None


async def test_create_decision_note(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={
            "content": "LOI 수락 결정",
            "note_type": "DECISION",
            "is_pinned": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["note_type"] == "DECISION"
    assert data["is_pinned"] is True


async def test_create_note_with_mentions(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={
            "content": "검토 부탁드립니다",
            "note_type": "QUESTION",
            "mentions": ["user1@example.com", "user2@example.com"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mentions"] == ["user1@example.com", "user2@example.com"]


# ── List ───────────────────────────────────────────────────
async def test_list_notes(client, transaction_id):
    # 노트 2개 생성
    await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "노트 1", "note_type": "COMMENT"},
    )
    await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "노트 2", "note_type": "QUESTION"},
    )

    resp = await client.get(f"/api/v1/transactions/{transaction_id}/notes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_list_notes_filter_by_type(client, transaction_id):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "코멘트", "note_type": "COMMENT"},
    )
    await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "질문", "note_type": "QUESTION"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/notes",
        params={"note_type": "QUESTION"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["note_type"] == "QUESTION"


async def test_list_pinned_only(client, transaction_id):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "일반", "note_type": "COMMENT"},
    )
    await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "고정", "note_type": "DECISION", "is_pinned": True},
    )

    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/notes",
        params={"pinned_only": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["is_pinned"] is True


# ── Thread (Replies) ────────────────────────────────────────
async def test_create_reply(client, transaction_id):
    # 부모 노트 생성
    parent = await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "원본 노트", "note_type": "COMMENT"},
    )
    parent_id = parent.json()["id"]

    # 답글 생성
    reply = await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "답글입니다", "note_type": "COMMENT", "parent_id": parent_id},
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == parent_id


async def test_list_replies(client, transaction_id):
    parent = await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "원본", "note_type": "COMMENT"},
    )
    parent_id = parent.json()["id"]

    await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "답글 1", "note_type": "COMMENT", "parent_id": parent_id},
    )
    await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "답글 2", "note_type": "COMMENT", "parent_id": parent_id},
    )

    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/notes/{parent_id}/replies"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


# ── Update ─────────────────────────────────────────────────
async def test_update_note(client, transaction_id):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "원본 내용", "note_type": "COMMENT"},
    )
    note_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/notes/{note_id}",
        json={"content": "수정된 내용", "is_pinned": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "수정된 내용"
    assert data["is_pinned"] is True


# ── Delete ─────────────────────────────────────────────────
async def test_delete_note(client, transaction_id):
    create = await client.post(
        f"/api/v1/transactions/{transaction_id}/notes",
        json={"content": "삭제 대상", "note_type": "COMMENT"},
    )
    note_id = create.json()["id"]

    resp = await client.delete(
        f"/api/v1/transactions/{transaction_id}/notes/{note_id}"
    )
    assert resp.status_code == 204

    # 삭제 확인
    get_resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/notes/{note_id}"
    )
    assert get_resp.status_code == 404


# ── 404 ────────────────────────────────────────────────────
async def test_get_nonexistent_note(client, transaction_id):
    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/notes/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404
