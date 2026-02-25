"""한국 M&A 인허가 Static Knowledge Base.

업종별 인허가 요건을 구조화된 데이터로 관리한다.
KB에 없는 업종은 LLM 보강 (Phase 3)에서 처리한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PermitKBEntry:
    """KB 인허가 항목."""
    industry_code: str
    industry_label: str
    permit_name: str
    regulatory_body: str
    legal_basis: str
    filing_type: str          # CHANGE_NOTIFICATION | CHANGE_APPROVAL | NEW_REGISTRATION | RENEWAL
    timing_type: str          # PRE_FILING | POST_FILING | BOTH
    pre_filing_days: int | None = None
    post_filing_days: int | None = None
    required_documents: list[str] = field(default_factory=list)
    deal_structure_filter: list[str] | None = None
    threshold_value: float | None = None
    notes: str | None = None


# ── 업종 분류 체계 ───────────────────────────────────────────

INDUSTRY_OPTIONS: list[dict[str, str | list[str]]] = [
    {"code": "FINANCE", "label": "금융업", "sub_categories": [
        "FINANCE_BANK", "FINANCE_INSURANCE", "FINANCE_SECURITIES", "FINANCE_CREDIT",
    ]},
    {"code": "TELECOM", "label": "통신업", "sub_categories": [
        "TELECOM_BASIC", "TELECOM_VALUE_ADDED",
    ]},
    {"code": "CONSTRUCTION", "label": "건설업", "sub_categories": ["CONSTRUCTION_GENERAL"]},
    {"code": "HEALTHCARE", "label": "의료업", "sub_categories": ["HEALTHCARE_HOSPITAL", "HEALTHCARE_PHARMACY"]},
    {"code": "FOOD", "label": "식품업", "sub_categories": ["FOOD_MANUFACTURING", "FOOD_RESTAURANT"]},
    {"code": "ENVIRONMENT", "label": "환경업", "sub_categories": ["ENVIRONMENT_WASTE", "ENVIRONMENT_WATER"]},
    {"code": "ENERGY", "label": "에너지업", "sub_categories": ["ENERGY_POWER", "ENERGY_GAS"]},
    {"code": "BROADCASTING", "label": "방송업", "sub_categories": ["BROADCASTING_TV", "BROADCASTING_CABLE"]},
    {"code": "TRANSPORT", "label": "운송업", "sub_categories": ["TRANSPORT_FREIGHT", "TRANSPORT_PASSENGER"]},
    {"code": "EDUCATION", "label": "교육업", "sub_categories": ["EDUCATION_SCHOOL", "EDUCATION_ACADEMY"]},
    {"code": "MANUFACTURING", "label": "제조업", "sub_categories": ["MANUFACTURING_GENERAL"]},
    {"code": "IT", "label": "IT/소프트웨어", "sub_categories": ["IT_GENERAL"]},
]

# 업종 코드 → 상위 코드 역매핑
_SUBCAT_TO_PARENT: dict[str, str] = {}
for opt in INDUSTRY_OPTIONS:
    for sub in opt.get("sub_categories", []):
        _SUBCAT_TO_PARENT[sub] = opt["code"]


# ── Knowledge Base 데이터 ────────────────────────────────────

PERMIT_KB: list[PermitKBEntry] = [
    # ═══ 공통 (모든 거래에 적용 가능) ═══
    PermitKBEntry(
        industry_code="UNIVERSAL_ANTITRUST",
        industry_label="공통",
        permit_name="공정거래위원회 기업결합 신고",
        regulatory_body="공정거래위원회",
        legal_basis="독점규제 및 공정거래에 관한 법률 제11조",
        filing_type="CHANGE_NOTIFICATION",
        timing_type="PRE_FILING",
        pre_filing_days=30,
        required_documents=[
            "기업결합신고서",
            "주식양수도계약서 사본",
            "양 당사자 최근 사업보고서",
            "시장점유율 관련 자료",
            "결합 당사자 주주명부",
        ],
        threshold_value=30_000_000_000,
        notes="자산총액 또는 매출액 300억원 이상인 회사 간 결합 시 해당. 간이신고 요건 별도 확인 필요.",
    ),
    PermitKBEntry(
        industry_code="UNIVERSAL_FDI",
        industry_label="공통",
        permit_name="외국인투자 신고",
        regulatory_body="산업통상자원부 / KOTRA",
        legal_basis="외국인투자촉진법 제5조",
        filing_type="CHANGE_NOTIFICATION",
        timing_type="BOTH",
        pre_filing_days=None,
        post_filing_days=60,
        required_documents=[
            "외국인투자신고서",
            "주식양수도계약서 사본",
            "투자자 신분 증명 서류",
            "법인등기부등본",
            "사업자등록증 사본",
        ],
        notes="[주의] 외국인 투자자가 관여하는 거래에만 해당합니다. 외국인이 국내 기업 주식 10% 이상 취득 시 적용. 국방·방송 등 제한 업종은 사전 허가 필요.",
    ),

    # ═══ 금융업 ═══
    PermitKBEntry(
        industry_code="FINANCE_BANK",
        industry_label="금융업(은행)",
        permit_name="은행 대주주 적격성 심사",
        regulatory_body="금융위원회",
        legal_basis="은행법 제15조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=60,
        required_documents=[
            "대주주 변경승인 신청서",
            "인수자 재무제표 (3개년)",
            "인수자 이력서 및 경력 증명",
            "자금 출처 증빙",
            "인수 후 경영계획서",
            "주식양수도계약서 사본",
        ],
        deal_structure_filter=["SHARE_ACQUISITION", "MERGER"],
        notes="의결권 10% 이상 주식 취득 시. 심사 소요 약 3~6개월.",
    ),
    PermitKBEntry(
        industry_code="FINANCE_INSURANCE",
        industry_label="금융업(보험)",
        permit_name="보험회사 대주주 변경 승인",
        regulatory_body="금융위원회",
        legal_basis="보험업법 제13조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=60,
        required_documents=[
            "대주주 변경승인 신청서",
            "인수자 재무제표 (3개년)",
            "자금 출처 증빙",
            "인수 후 경영계획서",
            "주식양수도계약서 사본",
        ],
        deal_structure_filter=["SHARE_ACQUISITION", "MERGER"],
        notes="의결권 10% 이상 주식 취득 시.",
    ),
    PermitKBEntry(
        industry_code="FINANCE_SECURITIES",
        industry_label="금융업(증권)",
        permit_name="금융투자업 대주주 변경 승인",
        regulatory_body="금융위원회",
        legal_basis="자본시장과 금융투자업에 관한 법률 제12조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=60,
        required_documents=[
            "대주주 변경승인 신청서",
            "인수자 재무제표 (3개년)",
            "자금 출처 증빙",
            "인수 후 경영계획서",
            "주식양수도계약서 사본",
        ],
        deal_structure_filter=["SHARE_ACQUISITION", "MERGER"],
        notes="의결권 10% 이상 주식 취득 시.",
    ),
    PermitKBEntry(
        industry_code="FINANCE_CREDIT",
        industry_label="금융업(여신전문)",
        permit_name="여신전문금융업 대주주 변경 승인",
        regulatory_body="금융위원회",
        legal_basis="여신전문금융업법 제6조의3",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=60,
        required_documents=[
            "대주주 변경승인 신청서",
            "인수자 재무제표 (3개년)",
            "자금 출처 증빙",
            "인수 후 경영계획서",
            "주식양수도계약서 사본",
        ],
        deal_structure_filter=["SHARE_ACQUISITION", "MERGER"],
        notes="의결권 10% 이상 주식 취득 시.",
    ),

    # ═══ 통신업 ═══
    PermitKBEntry(
        industry_code="TELECOM_BASIC",
        industry_label="통신업(기간통신)",
        permit_name="기간통신사업자 지위 승계 인가",
        regulatory_body="과학기술정보통신부",
        legal_basis="전기통신사업법 제18조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=90,
        required_documents=[
            "지위승계 인가 신청서",
            "양수도계약서 사본",
            "사업계획서",
            "재무제표",
            "기술인력 현황",
        ],
        deal_structure_filter=["SHARE_ACQUISITION", "MERGER", "ASSET_ACQUISITION"],
        notes="기간통신사업 허가를 받은 법인의 지배주주 변경 시.",
    ),
    PermitKBEntry(
        industry_code="TELECOM_VALUE_ADDED",
        industry_label="통신업(부가통신)",
        permit_name="부가통신사업 변경신고",
        regulatory_body="과학기술정보통신부",
        legal_basis="전기통신사업법 제22조",
        filing_type="CHANGE_NOTIFICATION",
        timing_type="POST_FILING",
        post_filing_days=14,
        required_documents=[
            "변경신고서",
            "법인등기부등본 (변경 후)",
            "주식양수도계약서 사본",
        ],
        notes="부가통신사업 신고 업체의 대표자/법인명 변경 시.",
    ),

    # ═══ 건설업 ═══
    PermitKBEntry(
        industry_code="CONSTRUCTION_GENERAL",
        industry_label="건설업",
        permit_name="건설업 변경신고",
        regulatory_body="국토교통부 / 시·도지사",
        legal_basis="건설산업기본법 제16조",
        filing_type="CHANGE_NOTIFICATION",
        timing_type="POST_FILING",
        post_filing_days=30,
        required_documents=[
            "건설업 변경신고서",
            "법인등기부등본 (변경 후)",
            "주식양수도계약서 사본",
            "기술인력 보유 현황",
            "재무제표",
        ],
        notes="건설업 등록 사항 변경(대표자, 법인명, 대주주 등) 시 30일 이내 신고.",
    ),

    # ═══ 의료업 ═══
    PermitKBEntry(
        industry_code="HEALTHCARE_HOSPITAL",
        industry_label="의료업(병원)",
        permit_name="의료기관 개설허가 변경",
        regulatory_body="보건복지부 / 시·도지사",
        legal_basis="의료법 제33조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=30,
        required_documents=[
            "개설허가 변경 신청서",
            "양도양수 계약서",
            "의료인 면허증 사본",
            "시설·장비 현황",
        ],
        deal_structure_filter=["ASSET_ACQUISITION", "MERGER"],
        notes="의료법인의 경우 법인 정관 변경 인가도 필요. 비영리법인 특수성 주의.",
    ),
    PermitKBEntry(
        industry_code="HEALTHCARE_PHARMACY",
        industry_label="의료업(약국/의약품)",
        permit_name="의약품 제조업·판매업 변경 허가",
        regulatory_body="식품의약품안전처",
        legal_basis="약사법 제31조, 제44조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=30,
        required_documents=[
            "변경허가 신청서",
            "양도양수 계약서",
            "제조·판매 시설 현황",
            "품질관리자 자격 증명",
        ],
    ),

    # ═══ 식품업 ═══
    PermitKBEntry(
        industry_code="FOOD_MANUFACTURING",
        industry_label="식품업(제조)",
        permit_name="식품영업 변경신고",
        regulatory_body="식품의약품안전처 / 시·군·구",
        legal_basis="식품위생법 제37조",
        filing_type="CHANGE_NOTIFICATION",
        timing_type="POST_FILING",
        post_filing_days=14,
        required_documents=[
            "영업 변경신고서",
            "영업허가증 원본",
            "양도양수 계약서",
            "법인등기부등본 (변경 후)",
        ],
        notes="영업자 지위 승계(양도양수) 시 14일 이내 신고.",
    ),

    # ═══ 환경업 ═══
    PermitKBEntry(
        industry_code="ENVIRONMENT_WASTE",
        industry_label="환경업(폐기물)",
        permit_name="폐기물 처리업 변경 허가",
        regulatory_body="환경부 / 시·도지사",
        legal_basis="폐기물관리법 제25조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=30,
        required_documents=[
            "변경허가 신청서",
            "양도양수 계약서",
            "시설·장비 현황",
            "기술인력 현황",
            "환경영향평가서 (해당 시)",
        ],
    ),

    # ═══ 에너지업 ═══
    PermitKBEntry(
        industry_code="ENERGY_POWER",
        industry_label="에너지업(발전)",
        permit_name="발전사업 변경 허가",
        regulatory_body="산업통상자원부",
        legal_basis="전기사업법 제7조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=60,
        required_documents=[
            "변경허가 신청서",
            "양도양수 계약서",
            "사업계획서",
            "재무제표",
            "발전설비 현황",
        ],
        notes="발전사업 허가 사항 변경 시. 신재생에너지 발전은 별도 규정.",
    ),

    # ═══ 방송업 ═══
    PermitKBEntry(
        industry_code="BROADCASTING_TV",
        industry_label="방송업",
        permit_name="방송사업 변경 승인",
        regulatory_body="방송통신위원회 / 과학기술정보통신부",
        legal_basis="방송법 제15조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=90,
        required_documents=[
            "변경승인 신청서",
            "주식양수도 계약서",
            "인수자 재무제표",
            "편성계획서",
            "지배구조 변경 계획",
        ],
        deal_structure_filter=["SHARE_ACQUISITION", "MERGER"],
        notes="종합편성·보도전문 채널은 대주주 적격성 심사 포함. 소유제한 규정 확인 필요.",
    ),

    # ═══ 운송업 ═══
    PermitKBEntry(
        industry_code="TRANSPORT_FREIGHT",
        industry_label="운송업(화물)",
        permit_name="화물자동차 운송사업 양도양수 인가",
        regulatory_body="국토교통부 / 시·도지사",
        legal_basis="화물자동차 운수사업법 제12조",
        filing_type="CHANGE_APPROVAL",
        timing_type="PRE_FILING",
        pre_filing_days=30,
        required_documents=[
            "양도양수 인가 신청서",
            "양도양수 계약서",
            "차량 현황",
            "사업계획서",
        ],
    ),
]


def lookup_permits(
    business_types: list[str],
    deal_structure: str | None = None,
    deal_value: float | None = None,
) -> list[PermitKBEntry]:
    """업종 코드 목록으로 해당 인허가 항목을 조회한다.

    1. UNIVERSAL_* 항목은 threshold_value 조건 충족 시 항상 포함
    2. 업종 코드 직접 매칭
    3. deal_structure 필터 적용
    """
    results: list[PermitKBEntry] = []
    seen: set[str] = set()

    for entry in PERMIT_KB:
        key = f"{entry.industry_code}:{entry.permit_name}"
        if key in seen:
            continue

        # 1) 공통 항목
        if entry.industry_code.startswith("UNIVERSAL_"):
            if entry.threshold_value and deal_value and deal_value < entry.threshold_value:
                continue
            seen.add(key)
            results.append(entry)
            continue

        # 2) 업종 매칭
        if entry.industry_code not in business_types:
            continue

        # 3) deal_structure 필터
        if entry.deal_structure_filter and deal_structure:
            if deal_structure not in entry.deal_structure_filter:
                continue

        seen.add(key)
        results.append(entry)

    return results


def get_all_industry_options() -> list[dict]:
    """프론트엔드에서 사용할 업종 목록을 반환한다."""
    return INDUSTRY_OPTIONS
