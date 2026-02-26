"""LDD(법률실사) 보고서 Pydantic 스키마 및 기본 섹션 구조."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import (
    LDDIssueLevel,
    LDDItemStatus,
    LDDReportStatus,
    LDDReportType,
    LDDSectionType,
)

# ── 항목(Item) 스키마 ─────────────────────────────────────────────────────────

class LDDItem(BaseModel):
    """DDRL 체크리스트 개별 항목 — Finding 기재 형식 반영."""

    item_id: str = ""                   # 고유 식별자 (예: CORP-01)
    name: str = ""                      # 항목명
    status: LDDItemStatus = LDDItemStatus.PENDING
    issue_level: LDDIssueLevel | None = None   # ISSUE인 경우 필수
    risk_color: str = ""                # RED | AMBER | GREEN (자동 계산)
    description: str = ""              # 발견 사항 (사실관계, 관련 문서)
    deal_impact: str = ""              # 거래에 미치는 영향 (가격/구조/일정)
    recommendation: str = ""           # 권고사항 (계약 반영, 추가 실사)
    rfi_required: bool = False         # 추가 자료 요청 여부
    rfi_number: str = ""               # RFI 번호 (예: CORP-001, CONTRACT-015)

    # AI 분석 메타데이터
    confidence: float = 0.0                                  # AI 신뢰도 0.0~1.0
    evidence_refs: list[str] = Field(default_factory=list)   # VDR document ID 목록

    # 사용자 리뷰 필드
    user_comment: str = ""                                   # 리뷰어 코멘트
    user_approved: bool | None = None                        # True=승인, False=반려, None=미검토
    user_override_status: str | None = None                  # 사용자가 직접 변경한 status
    user_override_level: str | None = None                   # 사용자가 직접 변경한 issue_level


# ── 섹션(Section) 스키마 ──────────────────────────────────────────────────────

class LDDSection(BaseModel):
    """DDRL 10개 섹션 중 하나."""

    section_type: LDDSectionType
    title: str
    items: list[LDDItem] = Field(default_factory=list)


# ── 요청/응답 스키마 ──────────────────────────────────────────────────────────

def _validate_issue_items(sections: list[LDDSection]) -> None:
    """ISSUE 상태 항목의 issue_level 필수 검증."""
    for section in sections:
        for item in section.items:
            if item.status == LDDItemStatus.ISSUE and item.issue_level is None:
                raise ValueError(
                    f"항목 '{item.name}' (ID: {item.item_id})는 "
                    f"ISSUE 상태일 때 issue_level(CRITICAL/HIGH/MEDIUM/LOW)이 필수입니다"
                )


class LDDReportCreate(BaseModel):
    """LDD 보고서 생성 요청."""

    title: str = Field(..., max_length=300)
    report_type: LDDReportType = LDDReportType.FULL
    deal_type: str = Field("", description="거래유형 (STOCK_ACQUISITION, REAL_ESTATE, IPO 등). 빈 문자열이면 기본 10개 섹션 사용.")
    target_company: str | None = Field(None, max_length=200)
    dd_period: str | None = Field(None, max_length=100)
    law_firm: str | None = Field(None, max_length=200)
    prepared_by: str | None = Field(None, max_length=200)
    sections: list[LDDSection] | None = None  # None이면 deal_type 템플릿 또는 DEFAULT_LDD_SECTIONS 사용

    @model_validator(mode="after")
    def validate_issue_items(self) -> LDDReportCreate:
        if self.sections:
            _validate_issue_items(self.sections)
        return self


class LDDReportCreateAuto(BaseModel):
    """Ralph Loop 기반 LDD 보고서 자동 생성 요청."""

    title: str = Field(..., max_length=300)
    report_type: LDDReportType = LDDReportType.FULL
    target_company: str | None = Field(None, max_length=200)
    dd_period: str | None = Field(None, max_length=100)
    law_firm: str | None = Field(None, max_length=200)
    prepared_by: str | None = Field(None, max_length=200)
    source_dir: str = Field(..., description="실사자료 폴더 경로")
    max_iterations: int = Field(3, ge=1, le=10)
    max_cost_usd: float = Field(20.0, ge=1.0, le=100.0)


class LDDSectionsUpdate(BaseModel):
    """섹션 데이터 업데이트 요청."""

    sections: list[LDDSection]

    @model_validator(mode="after")
    def validate_issue_items(self) -> LDDSectionsUpdate:
        _validate_issue_items(self.sections)
        return self


class LDDReportOut(BaseModel):
    """LDD 보고서 응답 스키마."""

    id: uuid.UUID
    transaction_id: uuid.UUID
    report_type: LDDReportType
    deal_type: str | None = None
    template_type: str | None = None
    title: str
    status: LDDReportStatus
    target_company: str | None
    dd_period: str | None
    law_firm: str | None
    prepared_by: str | None
    sections: list | None  # raw JSON — 프론트에서 LDDSection[]으로 파싱
    total_items: int
    issue_count: int
    red_count: int
    amber_count: int
    green_count: int
    ok_count: int
    na_count: int
    pending_count: int
    rfi_count: int
    template_version: str | None
    file_name: str | None
    file_size_bytes: int | None
    error_message: str | None
    created_by_email: str | None
    # VDR 연동 + Ralph Loop 2회 적용
    vdr_source: bool = False
    draft_score: float | None = None
    final_score: float | None = None
    analysis_started_at: datetime | None = None
    analysis_completed_at: datetime | None = None
    review_started_at: datetime | None = None
    review_completed_at: datetime | None = None
    finalize_started_at: datetime | None = None
    finalize_completed_at: datetime | None = None
    # 멀티 LLM 파이프라인 결과
    dual_risk_summary: dict | None = None
    gap_detection: dict | None = None
    jurisdiction_analysis: dict | None = None
    narrative_sections: dict | None = None
    legal_citations: dict | None = None
    appendices: dict | None = None
    qa_result: dict | None = None
    pipeline_stages: list[dict] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── VDR 기반 생성 / 리뷰 / Finalize 스키마 ─────────────────────────────────


class LDDReportCreateFromVdr(BaseModel):
    """VDR 기반 LDD 보고서 자동 생성 요청.

    VDR에 업로드된 문서를 분석 소스로 활용하여
    Ralph Loop #1로 초안을 생성한다.
    """

    title: str = Field(..., max_length=300)
    report_type: LDDReportType = LDDReportType.FULL
    target_company: str | None = Field(None, max_length=200)
    dd_period: str | None = Field(None, max_length=100)
    law_firm: str | None = Field(None, max_length=200)
    prepared_by: str | None = Field(None, max_length=200)
    folder_ids: list[uuid.UUID] | None = None  # None이면 전체 VDR 폴더 분석
    draft_max_iterations: int = Field(3, ge=1, le=10)
    final_max_iterations: int = Field(3, ge=1, le=10)
    max_cost_usd: float = Field(30.0, ge=1.0, le=200.0)
    # 멀티 LLM 파이프라인 옵션
    use_multi_llm: bool | None = None      # None=서버 설정 따름, True/False=강제
    is_cross_border: bool = False           # 크로스보더 거래 여부 (Stage 5 활성화)
    deal_type: str = Field("", description="거래유형 (STOCK_ACQUISITION, REAL_ESTATE, IPO, CORPORATE_SPLIT, PREFERRED_STOCK, ASSET_ACQUISITION). 빈 문자열이면 기본 10개 섹션 사용.")
    industry: str = ""                      # 대상 산업 (식품, IT, 금융)


class LDDItemReview(BaseModel):
    """개별 항목 리뷰 요청."""

    item_id: str = Field(..., description="DDRL 항목 ID (예: CORP-01)")
    user_approved: bool
    user_comment: str = ""
    user_override_status: str | None = Field(
        None, description="사용자가 status를 직접 변경 (OK/ISSUE/NA/PENDING)"
    )
    user_override_level: str | None = Field(
        None, description="사용자가 issue_level을 직접 변경 (CRITICAL/HIGH/MEDIUM/LOW)"
    )

    @model_validator(mode="after")
    def validate_override(self) -> LDDItemReview:
        if self.user_override_status == "ISSUE" and not self.user_override_level:
            raise ValueError("status를 ISSUE로 변경 시 issue_level 지정이 필요합니다")
        return self


class LDDBulkReview(BaseModel):
    """여러 항목 일괄 리뷰 요청."""

    items: list[LDDItemReview] = Field(..., min_length=1)


class LDDFinalizeRequest(BaseModel):
    """리뷰 완료 → Ralph Loop #2 최종 Refine 요청."""

    max_iterations: int = Field(3, ge=1, le=10)
    max_cost_usd: float = Field(15.0, ge=1.0, le=100.0)


class LDDReviewProgress(BaseModel):
    """리뷰 진행률 응답."""

    total: int
    approved: int
    rejected: int
    pending: int
    progress_pct: float


class LddVdrReferenceCreate(BaseModel):
    """VDR 참조 수동 추가 요청."""

    item_id: str = Field(..., max_length=30)
    vdr_document_id: uuid.UUID
    evidence_snippet: str | None = Field(None, max_length=500)
    page_reference: str | None = Field(None, max_length=50)


class LddVdrReferenceOut(BaseModel):
    """VDR 참조 응답."""

    id: uuid.UUID
    ldd_report_id: uuid.UUID
    item_id: str
    vdr_document_id: uuid.UUID | None
    section_type: str
    relevance_score: float
    evidence_snippet: str | None
    page_reference: str | None
    is_user_confirmed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── 기본 섹션 구조 (기재례 표준 — 10개 섹션) ──────────────────────────────────

def _make_item(item_id: str, name: str) -> dict:
    return {
        "item_id": item_id,
        "name": name,
        "status": "PENDING",
        "issue_level": None,
        "risk_color": "",
        "description": "",
        "deal_impact": "",
        "recommendation": "",
        "rfi_required": False,
        "rfi_number": "",
        "confidence": 0.0,
        "evidence_refs": [],
        "user_comment": "",
        "user_approved": None,
        "user_override_status": None,
        "user_override_level": None,
    }


DEFAULT_LDD_SECTIONS: list[dict] = [
    {
        "section_type": "GOVERNANCE",
        "title": "1. 기업 일반 및 지배구조",
        "items": [
            _make_item("CORP-01", "설립/등기/정관 검토"),
            _make_item("CORP-02", "이사회 의사록 검토"),
            _make_item("CORP-03", "주주명부 적정성"),
            _make_item("CORP-04", "임원 선임 및 등기"),
            _make_item("CORP-05", "자기거래/이해충돌"),
            _make_item("CORP-06", "자회사/관계사 현황"),
        ],
    },
    {
        "section_type": "CAPITAL",
        "title": "2. 자본구조 및 주주협약",
        "items": [
            _make_item("CAP-01", "발행주식 및 자본금 변동"),
            _make_item("CAP-02", "CB/BW/전환사채 조건"),
            _make_item("CAP-03", "스톡옵션/ESOP 현황"),
            _make_item("CAP-04", "우선주 내용 (환수권/의결권/배당)"),
            _make_item("CAP-05", "주주협약(SHA) 검토"),
            _make_item("CAP-06", "주식 양도제한 조항"),
        ],
    },
    {
        "section_type": "CONTRACTS",
        "title": "3. 주요 계약",
        "items": [
            _make_item("CONTRACT-01", "주요 고객계약 (종료조건/매출집중도)"),
            _make_item("CONTRACT-02", "주요 공급계약 (대체가능성)"),
            _make_item("CONTRACT-03", "금융계약 (변경통제조항)"),
            _make_item("CONTRACT-04", "Change of Control 조항 일제 확인"),
            _make_item("CONTRACT-05", "계약 위반/분쟁 가능성"),
            _make_item("CONTRACT-06", "라이선스 계약 (이전가능성)"),
        ],
    },
    {
        "section_type": "LITIGATION",
        "title": "4. 소송 및 분쟁",
        "items": [
            _make_item("LIT-01", "진행 중 민사 소송"),
            _make_item("LIT-02", "진행 중 형사/행정 절차"),
            _make_item("LIT-03", "행정제재 이력"),
            _make_item("LIT-04", "잠재적 분쟁 리스크"),
            _make_item("LIT-05", "규제기관 조사 이력"),
        ],
    },
    {
        "section_type": "LABOR",
        "title": "5. 인사 및 노무",
        "items": [
            _make_item("LABOR-01", "근로계약 및 취업규칙"),
            _make_item("LABOR-02", "노동조합 및 단체협약"),
            _make_item("LABOR-03", "퇴직급여 및 연금 적립"),
            _make_item("LABOR-04", "임원 보상 및 스톡옵션"),
            _make_item("LABOR-05", "노무 분쟁 이력"),
            _make_item("LABOR-06", "미지급 임금 및 보너스"),
        ],
    },
    {
        "section_type": "IP",
        "title": "6. 지식재산권",
        "items": [
            _make_item("IP-01", "특허/실용신안 유효성"),
            _make_item("IP-02", "상표/디자인권 현황"),
            _make_item("IP-03", "소프트웨어 라이선스 준수"),
            _make_item("IP-04", "제3자 IP 침해 가능성"),
            _make_item("IP-05", "직무발명 규정 및 보상 청구 위험"),
        ],
    },
    {
        "section_type": "REAL_ESTATE",
        "title": "7. 부동산 및 환경",
        "items": [
            _make_item("RE-01", "부동산 소유권 등기 및 하자"),
            _make_item("RE-02", "저당권/전세권 현황"),
            _make_item("RE-03", "임차계약 (종료 위험)"),
            _make_item("RE-04", "환경오염 이력 및 오염토양"),
            _make_item("RE-05", "지역지구 제한 (용도변경)"),
        ],
    },
    {
        "section_type": "PERMITS",
        "title": "8. 인허가 및 규제",
        "items": [
            _make_item("PERMIT-01", "영업허가/면허 유효성"),
            _make_item("PERMIT-02", "Change of Control 시 인허가 영향"),
            _make_item("PERMIT-03", "정부보조금/그랜트 조건 (회수 위험)"),
            _make_item("PERMIT-04", "공정거래 이슈"),
            _make_item("PERMIT-05", "해외 인허가 (기업결합신고 해당 시)"),
        ],
    },
    {
        "section_type": "TAX",
        "title": "9. 조세",
        "items": [
            _make_item("TAX-01", "최근 3년 세무신고 적정성"),
            _make_item("TAX-02", "법인세 과세표준 및 납부 이력"),
            _make_item("TAX-03", "부가가치세 신고/납부"),
            _make_item("TAX-04", "이전가격 (특수관계인 거래)"),
            _make_item("TAX-05", "미지급 세금/가산세/세무조사 진행"),
        ],
    },
    {
        "section_type": "DATA_IT",
        "title": "10. 개인정보 및 IT",
        "items": [
            _make_item("IT-01", "개인정보 처리 현황 (PIPA 준수)"),
            _make_item("IT-02", "정보보호 인증 (ISMS/ISO)"),
            _make_item("IT-03", "핵심 IT 시스템 현황"),
            _make_item("IT-04", "데이터 유출/보안사고 이력"),
        ],
    },
]
