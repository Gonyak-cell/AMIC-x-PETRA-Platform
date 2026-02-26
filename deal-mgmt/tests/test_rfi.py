"""RFI API 테스트."""

SAMPLE_TXN = {
    "name": "RFI 테스트 거래",
    "code_name": "RFI-001",
    "side": "SELL",
    "target_company_name": "RFI대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_rfi(client, txn_id: str, **kwargs) -> dict:
    payload = {"title": "1차 RFI", "round_number": 1, **kwargs}
    resp = await client.post(f"/api/v1/transactions/{txn_id}/rfis", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _add_item(client, txn_id: str, rfi_id: str, **kwargs) -> dict:
    payload = {"category": "FINANCIAL", "question": "최근 3개년 감사보고서를 제공해 주세요.", **kwargs}
    resp = await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi_id}/items", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── RFI CRUD ───────────────────────────────────────────────


async def test_create_rfi(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id, title="1차 RFI", description="테스트 설명")
    assert rfi["title"] == "1차 RFI"
    assert rfi["status"] == "DRAFT"
    assert rfi["round_number"] == 1
    assert rfi["total_items"] == 0


async def test_list_rfis(client):
    txn_id = await _create_txn(client)
    await _create_rfi(client, txn_id, title="1차 RFI")
    await _create_rfi(client, txn_id, title="2차 RFI", round_number=2)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfis")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_rfis_filter_status(client):
    txn_id = await _create_txn(client)
    await _create_rfi(client, txn_id, title="DRAFT RFI")

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfis", params={"status": "DRAFT"})
    assert len(resp.json()) == 1


async def test_get_rfi_detail(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    await _add_item(client, txn_id, rfi["id"])

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "1차 RFI"
    assert len(data["items"]) == 1


async def test_update_rfi(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}",
        json={"title": "수정된 RFI", "recipient_name": "홍길동"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "수정된 RFI"
    assert resp.json()["recipient_name"] == "홍길동"


async def test_delete_rfi_draft(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}")
    assert resp.status_code == 204


async def test_delete_rfi_non_draft_fails(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    # 아이템 추가 후 발송
    await _add_item(client, txn_id, rfi["id"])
    await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/send")

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}")
    assert resp.status_code == 400


# ── RFI 워크플로우 ─────────────────────────────────────────


async def test_send_rfi(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    await _add_item(client, txn_id, rfi["id"])

    resp = await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/send")
    assert resp.status_code == 200
    assert resp.json()["status"] == "SENT"
    assert resp.json()["sent_at"] is not None


async def test_send_rfi_without_items_fails(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)

    resp = await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/send")
    assert resp.status_code == 400


async def test_close_rfi(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    await _add_item(client, txn_id, rfi["id"])
    await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/send")

    resp = await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/close")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLOSED"


async def test_extend_deadline(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id, due_date="2026-03-01")

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/extend-deadline",
        json={"due_date": "2026-04-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["due_date"] == "2026-04-01"


# ── RFI Item CRUD ──────────────────────────────────────────


async def test_create_rfi_item(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])

    assert item["category"] == "FINANCIAL"
    assert item["status"] == "PENDING"
    assert item["question_number"] == 1
    assert item["priority"] == "MEDIUM"


async def test_batch_create_items(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/batch",
        json={
            "items": [
                {"category": "FINANCIAL", "question": "감사보고서"},
                {"category": "TAX", "question": "세무 신고 내역"},
                {"category": "LEGAL", "question": "소송 이력", "priority": "HIGH"},
            ]
        },
    )
    assert resp.status_code == 201
    items = resp.json()
    assert len(items) == 3
    assert items[0]["question_number"] == 1
    assert items[1]["question_number"] == 2
    assert items[2]["question_number"] == 3
    assert items[2]["priority"] == "HIGH"


async def test_list_rfi_items_filter(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    await _add_item(client, txn_id, rfi["id"], category="FINANCIAL")
    await _add_item(client, txn_id, rfi["id"], category="LEGAL", question="소송 이력")

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items",
        params={"category": "FINANCIAL"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_update_rfi_item(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}",
        json={"priority": "HIGH", "notes": "긴급 요청"},
    )
    assert resp.status_code == 200
    assert resp.json()["priority"] == "HIGH"
    assert resp.json()["notes"] == "긴급 요청"


async def test_delete_rfi_item(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}")
    assert resp.status_code == 204


# ── 응답 / 검토 ───────────────────────────────────────────


async def test_respond_to_item(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/respond",
        json={"response": "감사보고서 첨부합니다."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RESPONDED"
    assert data["response"] == "감사보고서 첨부합니다."
    assert data["responded_at"] is not None


async def test_review_item_accepted(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/respond",
        json={"response": "답변입니다."},
    )

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/review",
        json={"status": "ACCEPTED", "reviewer_comment": "확인 완료"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"
    assert resp.json()["reviewer_comment"] == "확인 완료"


async def test_review_item_clarification_needed(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/respond",
        json={"response": "불명확한 답변"},
    )

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/review",
        json={
            "status": "CLARIFICATION_NEEDED",
            "reviewer_comment": "추가 설명 필요",
            "follow_up_question": "3개년 데이터가 아닌 2개년만 있습니다. 확인 부탁드립니다.",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLARIFICATION_NEEDED"
    assert resp.json()["follow_up_question"] is not None


# ── 카운트 자동 갱신 + 상태 자동 전환 ─────────────────────


async def test_rfi_counts_auto_update(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item1 = await _add_item(client, txn_id, rfi["id"], question="질문1")
    item2 = await _add_item(client, txn_id, rfi["id"], question="질문2")  # noqa: F841

    # RFI 상세 확인 — 2개 항목
    detail = (await client.get(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}")).json()
    assert detail["total_items"] == 2
    assert detail["responded_items"] == 0

    # 1개 응답 → PARTIALLY_RESPONDED
    await _add_item(client, txn_id, rfi["id"])  # 발송 위해 추가
    await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/send")
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item1['id']}/respond",
        json={"response": "답변1"},
    )

    rfi_data = (await client.get(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}")).json()
    assert rfi_data["responded_items"] == 1
    assert rfi_data["status"] == "PARTIALLY_RESPONDED"


async def test_rfi_fully_responded_auto_transition(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])

    # 발송 → 응답
    await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/send")
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/respond",
        json={"response": "답변"},
    )

    rfi_data = (await client.get(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}")).json()
    assert rfi_data["status"] == "FULLY_RESPONDED"
    assert rfi_data["responded_items"] == 1
    assert rfi_data["total_items"] == 1


# ── Summary ────────────────────────────────────────────────


async def test_rfi_summary(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item1 = await _add_item(client, txn_id, rfi["id"], category="FINANCIAL", question="재무 질문")
    item2 = await _add_item(client, txn_id, rfi["id"], category="LEGAL", question="법률 질문")  # noqa: F841

    # 1개 응답
    await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/send")
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item1['id']}/respond",
        json={"response": "답변"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfis/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rfis"] == 1
    assert data["total_items"] == 2
    assert data["responded_items"] == 1
    assert data["overall_response_pct"] == 50.0


# ── DD 체크리스트 기반 자동 생성 ───────────────────────────


async def test_generate_from_dd(client):
    txn_id = await _create_txn(client)

    # DD 체크리스트 항목 추가 (NOT_STARTED)
    await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "FDD_FINANCIAL_STATEMENTS", "title": "재무제표 수집"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/dd-checklist",
        json={"workstream": "LDD_CORPORATE", "title": "소송 이력 조사"},
    )

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/generate-from-dd",
        json={"title": "DD 기반 자동 RFI"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["items_created"] == 2

    # 생성된 RFI 확인
    detail = (await client.get(f"/api/v1/transactions/{txn_id}/rfis/{data['rfi_id']}")).json()
    assert detail["title"] == "DD 기반 자동 RFI"
    assert len(detail["items"]) == 2
    # FDD → FINANCIAL, LDD → LEGAL
    categories = {item["category"] for item in detail["items"]}
    assert "FINANCIAL" in categories
    assert "LEGAL" in categories


# ── 404 ────────────────────────────────────────────────────


async def test_get_rfi_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/transactions/{txn_id}/rfis/{fake_id}")
    assert resp.status_code == 404


async def test_update_rfi_item_404(client):
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{fake_id}",
        json={"priority": "HIGH"},
    )
    assert resp.status_code == 404


# ── BE-WF-01: DRAFT→CLOSED 직접 전환 차단 ───────────────


async def test_close_rfi_from_draft_fails(client):
    """DRAFT 상태의 RFI를 직접 CLOSED로 전환하면 400."""
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)

    resp = await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/close")
    assert resp.status_code == 400
    assert "DRAFT" in resp.json()["detail"]


# ── BE-WF-02: ACCEPTED 아이템 재응답 차단 ────────────────


async def test_respond_to_accepted_item_fails(client):
    """ACCEPTED 상태의 아이템에 재응답하면 400."""
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])

    # 응답 → 리뷰(ACCEPTED)
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/respond",
        json={"response": "답변"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/review",
        json={"status": "ACCEPTED"},
    )

    # 재응답 시도
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/respond",
        json={"response": "다시 답변"},
    )
    assert resp.status_code == 400
    assert "ACCEPTED" in resp.json()["detail"]


# ── BE-WF-03: PENDING 아이템 직접 리뷰 차단 ──────────────


async def test_review_pending_item_fails(client):
    """응답 없는 PENDING 아이템을 리뷰하면 400."""
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/review",
        json={"status": "ACCEPTED"},
    )
    assert resp.status_code == 400
    assert "PENDING" in resp.json()["detail"]


# ── BE-WF-04: CLARIFICATION_NEEDED → 재응답 → FULLY_RESPONDED ───


async def test_clarification_rerespond_flow(client):
    """CLARIFICATION_NEEDED 후 재응답 → RESPONDED로 전환 가능."""
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)
    item = await _add_item(client, txn_id, rfi["id"])

    # 발송 → 응답 → CLARIFICATION_NEEDED
    await client.post(f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/send")
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/respond",
        json={"response": "첫 번째 답변"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/review",
        json={"status": "CLARIFICATION_NEEDED", "follow_up_question": "추가 설명 필요"},
    )

    # 재응답
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/items/{item['id']}/respond",
        json={"response": "보완된 답변"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESPONDED"


# ── BE-WF-05: extend_deadline 과거 날짜 차단 ─────────────


async def test_extend_deadline_past_date_fails(client):
    """과거 날짜로 마감일 연장 시 400."""
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id, due_date="2026-12-01")

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/extend-deadline",
        json={"due_date": "2020-01-01"},
    )
    assert resp.status_code == 400
    assert "과거" in resp.json()["detail"]


async def test_extend_deadline_earlier_than_current_fails(client):
    """기존 마감일보다 이전 날짜로 연장 시 400."""
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id, due_date="2027-06-01")

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/extend-deadline",
        json={"due_date": "2027-05-01"},
    )
    assert resp.status_code == 400
    assert "기존 마감일" in resp.json()["detail"]


# ── BE-DATA-01: 잘못된 날짜 형식 검증 ────────────────────


async def test_create_rfi_invalid_date_fails(client):
    """잘못된 날짜 형식으로 RFI 생성 시 422."""
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis",
        json={"title": "테스트", "due_date": "1234567890"},
    )
    assert resp.status_code == 422


# ── BE-DATA-05: RFIUpdate에서 status 직접 변경 불가 ───────


async def test_update_rfi_status_field_ignored(client):
    """PATCH에서 status 필드는 무시된다 (스키마에서 제거됨)."""
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}",
        json={"title": "수정됨", "status": "CLOSED"},
    )
    # status가 스키마에 없으므로 무시되고 200 반환 (extra='ignore' 기본)
    assert resp.status_code == 200
    assert resp.json()["status"] == "DRAFT"


# ── BE-SEC-02: 잘못된 파일 확장자 업로드 차단 ────────────


async def test_import_invalid_extension_fails(client):
    """Excel이 아닌 파일 업로드 시 400."""
    txn_id = await _create_txn(client)
    rfi = await _create_rfi(client, txn_id)

    import io

    fake_file = io.BytesIO(b"not an excel file")
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/rfis/{rfi['id']}/import",
        files={"file": ("test.txt", fake_file, "text/plain")},
    )
    assert resp.status_code == 400
    assert "Excel" in resp.json()["detail"]
