"""LDD(법률실사) 보고서 API 테스트 — CRUD + 렌더링."""

SAMPLE_TXN = {
    "name": "LDD 테스트 거래",
    "deal_type": "SE",
    "side": "BUY",
    "target_company_name": "주식회사 대상기업",
    "client_name": "주식회사 의뢰기업",
    "lead_advisor_email": "test@example.com",  # conftest.py MOCK_CLAIMS email과 일치
}

SAMPLE_SECTIONS = [
    {
        "section_type": "GOVERNANCE",
        "title": "1. 기업 일반 및 지배구조",
        "items": [
            {
                "item_id": "CORP-01",
                "name": "설립/등기/정관 검토",
                "deal_type": "SE",
                "status": "OK",
                "issue_level": None,
                "risk_color": "",
                "description": "",
                "deal_impact": "",
                "recommendation": "",
                "rfi_required": False,
                "rfi_number": "",
            },
            {
                "item_id": "CORP-02",
                "name": "이사회 의사록 검토",
                "deal_type": "SE",
                "status": "ISSUE",
                "issue_level": "HIGH",
                "risk_color": "AMBER",
                "description": "최근 2년간 이사회 의사록 일부 누락 확인",
                "deal_impact": "계약 유효성 분쟁 가능성",
                "recommendation": "누락된 의사록 재작성 또는 진술보장 조항 포함",
                "rfi_required": True,
                "rfi_number": "CORP-002",
            },
        ],
    },
    {
        "section_type": "TAX",
        "title": "9. 조세",
        "items": [
            {
                "item_id": "TAX-01",
                "name": "최근 3년 세무신고 적정성",
                "deal_type": "SE",
                "status": "ISSUE",
                "issue_level": "CRITICAL",
                "risk_color": "RED",
                "description": "법인세 신고 누락 및 가산세 부과 이력 확인",
                "deal_impact": "미지급 세금 약 5억원 추정 — 거래가격 조정 필요",
                "recommendation": "세무사 확인 후 거래가격에서 차감 처리",
                "rfi_required": True,
                "rfi_number": "TAX-001",
            },
        ],
    },
]


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    return resp.json()["id"]


# ── 기본 섹션 조회 ────────────────────────────────────────────────────────────


async def test_get_default_sections(client):
    """기본 DDRL 10개 섹션 구조를 반환해야 한다."""
    resp = await client.get("/api/v1/ldd-reports/default-sections")
    assert resp.status_code == 200
    data = resp.json()
    assert "sections" in data
    sections = data["sections"]
    assert len(sections) == 10, f"Expected 10 sections, got {len(sections)}"

    # 필수 섹션 유형 확인
    types = {s["section_type"] for s in sections}
    assert "GOVERNANCE" in types
    assert "CAPITAL" in types
    assert "TAX" in types
    assert "DATA_IT" in types


# ── 생성 ─────────────────────────────────────────────────────────────────────


async def test_create_full_ldd_report_with_default_sections(client):
    """기본 섹션으로 FULL LDD 보고서를 생성해야 한다."""
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={
            "title": "프로젝트 테스트 법률실사보고서",
            "report_type": "FULL",
            "target_company": "주식회사 대상기업",
            "dd_period": "2026-03-01 ~ 2026-03-31",
            "law_firm": "법무법인 테스트",
            "prepared_by": "홍길동 변호사",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["report_type"] == "FULL"
    assert data["title"] == "프로젝트 테스트 법률실사보고서"
    assert data["target_company"] == "주식회사 대상기업"
    assert data["transaction_id"] == txn_id
    assert data["status"] in ("READY", "FAILED", "GENERATING")  # 렌더링 결과
    assert data["id"] is not None
    # 기본 섹션 적용 확인
    assert data["total_items"] > 0


async def test_create_redflag_ldd_report(client):
    """REDFLAG 유형 보고서를 생성해야 한다."""
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={
            "title": "Redflag DD — 대상기업",
            "report_type": "REDFLAG",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_type"] == "REDFLAG"


async def test_create_ldd_report_with_custom_sections(client):
    """커스텀 섹션으로 LDD 보고서를 생성하고 이슈 카운트가 올바른지 확인한다."""
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={
            "title": "이슈 포함 LDD 보고서",
            "report_type": "FULL",
            "sections": SAMPLE_SECTIONS,
        },
    )
    assert resp.status_code == 201
    data = resp.json()

    # 이슈 카운트 검증: ISSUE 2건 (HIGH 1 + CRITICAL 1)
    assert data["issue_count"] == 2, f"Expected 2 issues, got {data['issue_count']}"
    assert data["red_count"] == 1, "CRITICAL(TAX-01) → Red 1건"
    assert data["amber_count"] == 1, "HIGH(CORP-02) → Amber 1건"
    assert data["rfi_count"] == 2, "RFI 요청 2건"


async def test_create_ldd_report_invalid_txn(client):
    """존재하지 않는 거래에 대한 생성 요청은 404를 반환해야 한다."""
    fake_txn = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/v1/transactions/{fake_txn}/ldd-reports",
        json={"title": "없는 거래", "report_type": "FULL"},
    )
    assert resp.status_code == 404


# ── 목록/단건 조회 ────────────────────────────────────────────────────────────


async def test_list_ldd_reports(client):
    """보고서 목록을 반환해야 한다."""
    txn_id = await _create_txn(client)

    # 2개 생성
    for i in range(2):
        await client.post(
            f"/api/v1/transactions/{txn_id}/ldd-reports",
            json={"title": f"테스트 LDD {i + 1}", "report_type": "FULL"},
        )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/ldd-reports")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_get_ldd_report(client):
    """단건 조회가 올바르게 작동해야 한다."""
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={"title": "단건 조회 테스트", "report_type": "FULL"},
    )
    report_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == report_id


# ── 섹션 수정 ─────────────────────────────────────────────────────────────────


async def test_update_ldd_sections(client):
    """섹션 수정 후 이슈 카운트가 재계산되어야 한다."""
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={"title": "섹션 수정 테스트", "report_type": "FULL"},
    )
    report_id = create_resp.json()["id"]
    original_issue_count = create_resp.json()["issue_count"]
    assert original_issue_count == 0, "초기 상태는 이슈 없음"

    # ISSUE 항목 추가 후 수정
    resp = await client.put(
        f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}/sections",
        json={"sections": SAMPLE_SECTIONS},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["issue_count"] == 2
    assert data["red_count"] == 1
    assert data["amber_count"] == 1


# ── 재생성 ────────────────────────────────────────────────────────────────────


async def test_regenerate_ldd_report(client):
    """보고서 재생성이 올바르게 작동해야 한다."""
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={"title": "재생성 테스트", "report_type": "FULL"},
    )
    report_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}/regenerate")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("READY", "FAILED", "GENERATING")


# ── 삭제 ─────────────────────────────────────────────────────────────────────


async def test_delete_ldd_report(client):
    """보고서 삭제 후 목록에서 제거되어야 한다."""
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={"title": "삭제 테스트", "report_type": "FULL"},
    )
    report_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/transactions/{txn_id}/ldd-reports/{report_id}")
    assert del_resp.status_code == 204

    # 목록에서 없어졌는지 확인
    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/ldd-reports")
    assert all(r["id"] != report_id for r in list_resp.json())


async def test_delete_nonexistent_report(client):
    """존재하지 않는 보고서 삭제는 404를 반환해야 한다."""
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/transactions/{txn_id}/ldd-reports/{fake_id}")
    assert resp.status_code == 404


# ── 리스크 색상 자동 계산 ─────────────────────────────────────────────────────


async def test_risk_color_auto_calculation(client):
    """이슈레벨에 따라 risk_color가 자동으로 계산되어야 한다."""
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ldd-reports",
        json={
            "title": "Risk Color 테스트",
            "report_type": "FULL",
            "sections": SAMPLE_SECTIONS,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    sections = data["sections"]

    # CORP-02 (HIGH) → AMBER
    governance_sec = next(s for s in sections if s["section_type"] == "GOVERNANCE")
    corp_02 = next(i for i in governance_sec["items"] if i["item_id"] == "CORP-02")
    assert corp_02["risk_color"] == "AMBER"

    # TAX-01 (CRITICAL) → RED
    tax_sec = next(s for s in sections if s["section_type"] == "TAX")
    tax_01 = next(i for i in tax_sec["items"] if i["item_id"] == "TAX-01")
    assert tax_01["risk_color"] == "RED"
