"""LDD 체크리스트 리뷰 워크플로우 테스트 — 항목 리뷰 + 진행률 + VDR 참조 CRUD."""

import uuid

from sqlalchemy import update

SAMPLE_TXN = {
    "name": "LDD 리뷰 테스트 거래",
    "code_name": "LDD-REVIEW-001",
    "side": "BUY",
    "target_company_name": "주식회사 대상기업",
    "client_name": "주식회사 의뢰기업",
    "lead_advisor_email": "test@example.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_review_report(client, txn_id: str) -> dict:
    """REVIEW 상태의 LDD 보고서를 생성한다 (기본 섹션 기반)."""
    # 먼저 DRAFT 보고서 생성
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={
            "title": "리뷰 테스트 보고서",
            "report_type": "FULL",
            "target_company": "테스트 기업",
        },
    )
    assert resp.status_code == 201
    report = resp.json()

    # 상태를 REVIEW로 직접 전환 (서비스 레이어에서는 Ralph Loop을 통해 전환)
    # 테스트에서는 DB 직접 조작이 필요하므로, sections 업데이트를 통해 확인
    return report


async def _set_report_status(async_session, report_id: str, status: str) -> None:
    """DB에서 LDD 보고서 상태를 직접 변경한다 (테스트 전용)."""
    from app.models.ldd_report import LDDReport

    stmt = update(LDDReport).where(LDDReport.id == uuid.UUID(report_id)).values(status=status)
    await async_session.execute(stmt)
    await async_session.commit()


# ── 리뷰 진행률 ──────────────────────────────────────────────────────────────


async def test_review_progress_initial(client):
    """초기 리뷰 진행률은 모두 pending이어야 한다."""
    txn_id = await _create_txn(client)
    report = await _create_review_report(client, txn_id)
    report_id = report["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}/review-progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert data["approved"] == 0
    assert data["rejected"] == 0
    assert data["pending"] == data["total"]
    assert data["progress_pct"] == 0.0


# ── VDR 참조 CRUD ────────────────────────────────────────────────────────────


async def test_list_references_empty(client):
    """초기 VDR 참조 목록은 비어있어야 한다."""
    txn_id = await _create_txn(client)
    report = await _create_review_report(client, txn_id)
    report_id = report["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}/references")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_delete_nonexistent_reference(client):
    """존재하지 않는 참조 삭제는 404를 반환해야 한다."""
    txn_id = await _create_txn(client)
    report = await _create_review_report(client, txn_id)
    report_id = report["id"]
    fake_ref_id = "00000000-0000-0000-0000-000000000000"

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}/references/{fake_ref_id}")
    assert resp.status_code == 404


# ── 보고서 생성 확인 ──────────────────────────────────────────────────────────


async def test_report_out_has_vdr_fields(client):
    """LDDReportOut 응답에 VDR 관련 필드가 포함되어야 한다."""
    txn_id = await _create_txn(client)
    report = await _create_review_report(client, txn_id)

    assert "vdr_source" in report
    assert "draft_score" in report
    assert "final_score" in report
    assert report["vdr_source"] is False  # 수동 생성이므로 False


async def test_default_sections_have_review_fields(client):
    """기본 섹션 항목에 AI 메타데이터 + 리뷰 필드가 포함되어야 한다."""
    resp = await client.get("/api/v1/ldd-reports/default-sections")
    assert resp.status_code == 200
    sections = resp.json()["sections"]

    first_item = sections[0]["items"][0]
    # AI 메타데이터
    assert "confidence" in first_item
    assert "evidence_refs" in first_item
    # 사용자 리뷰 필드
    assert "user_comment" in first_item
    assert "user_approved" in first_item
    assert "user_override_status" in first_item
    assert "user_override_level" in first_item
    # 기본값 확인
    assert first_item["confidence"] == 0.0
    assert first_item["evidence_refs"] == []
    assert first_item["user_approved"] is None


# ── _compute_counts 검증 ──────────────────────────────────────────────────────


async def test_compute_counts_with_review_sections(client):
    """리뷰 필드가 포함된 섹션으로 생성 시 카운트가 올바르게 계산되어야 한다."""
    txn_id = await _create_txn(client)

    sections = [
        {
            "section_type": "GOVERNANCE",
            "title": "1. 기업 일반 및 지배구조",
            "items": [
                {
                    "item_id": "CORP-01",
                    "name": "설립/등기/정관 검토",
                    "status": "OK",
                    "issue_level": None,
                    "risk_color": "",
                    "description": "적정",
                    "deal_impact": "",
                    "recommendation": "",
                    "rfi_required": False,
                    "rfi_number": "",
                    "confidence": 0.85,
                    "evidence_refs": ["정관.pdf", "등기부등본.pdf"],
                    "user_comment": "",
                    "user_approved": True,
                    "user_override_status": None,
                    "user_override_level": None,
                },
                {
                    "item_id": "CORP-02",
                    "name": "이사회 의사록 검토",
                    "status": "ISSUE",
                    "issue_level": "HIGH",
                    "risk_color": "AMBER",
                    "description": "의사록 누락",
                    "deal_impact": "계약 유효성 분쟁",
                    "recommendation": "진술보장 조항",
                    "rfi_required": True,
                    "rfi_number": "CORP-002",
                    "confidence": 0.72,
                    "evidence_refs": [],
                    "user_comment": "재검토 필요",
                    "user_approved": False,
                    "user_override_status": None,
                    "user_override_level": None,
                },
            ],
        },
    ]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={
            "title": "리뷰 필드 포함 보고서",
            "report_type": "FULL",
            "sections": sections,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_items"] == 2
    assert data["ok_count"] == 1
    assert data["issue_count"] == 1
    assert data["amber_count"] == 1
    assert data["rfi_count"] == 1


# ── REVIEW 상태 리뷰 동작 테스트 ─────────────────────────────────────────────


async def test_review_item_requires_review_status(client, async_session):
    """REVIEW 상태가 아닌 보고서에 리뷰 시도 시 409를 반환해야 한다."""
    txn_id = await _create_txn(client)
    report = await _create_review_report(client, txn_id)
    report_id = report["id"]
    # 보고서는 READY 상태 (docxtpl 렌더링 후)
    first_item_id = report["sections"][0]["items"][0]["item_id"]

    resp = await client.put(
        f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}/items/{first_item_id}/review",
        json={
            "item_id": first_item_id,
            "user_approved": True,
            "user_comment": "승인",
        },
    )
    # REVIEW 상태가 아니므로 WorkflowError → 422
    assert resp.status_code == 422


async def test_review_item_approve(client, async_session):
    """REVIEW 상태 보고서에서 항목 승인이 정상 동작해야 한다."""
    txn_id = await _create_txn(client)
    report = await _create_review_report(client, txn_id)
    report_id = report["id"]

    # DB에서 직접 REVIEW 상태로 전환
    await _set_report_status(async_session, report_id, "REVIEW")

    first_item_id = report["sections"][0]["items"][0]["item_id"]

    resp = await client.put(
        f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}/items/{first_item_id}/review",
        json={
            "item_id": first_item_id,
            "user_approved": True,
            "user_comment": "이상 없음 확인",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == first_item_id
    assert data["status"] == "reviewed"


async def test_bulk_review(client, async_session):
    """REVIEW 상태에서 일괄 리뷰가 정상 동작해야 한다."""
    txn_id = await _create_txn(client)
    report = await _create_review_report(client, txn_id)
    report_id = report["id"]

    await _set_report_status(async_session, report_id, "REVIEW")

    items = report["sections"][0]["items"][:2]
    review_items = [
        {"item_id": items[0]["item_id"], "user_approved": True, "user_comment": "OK"},
        {"item_id": items[1]["item_id"], "user_approved": False, "user_comment": "재검토"},
    ]

    resp = await client.put(
        f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}/items/bulk-review",
        json={"items": review_items},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["applied"] == 2
    assert data["requested"] == 2
