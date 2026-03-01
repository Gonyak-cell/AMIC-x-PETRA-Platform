from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class GPRegistryItem(BaseModel):
    """공공데이터포털 자산운용사 정보 (금융통계 + 기본정보 조합)"""

    company_name: str = Field(..., description="운용사명")
    company_name_en: str = Field("", description="영문명")
    finance_company_code: str = Field("", description="금융회사코드")
    business_registration_no: str = Field("", description="사업자등록번호")
    corporation_registration_no: str = Field("", description="법인등록번호")
    established_date: str = Field("", description="설립일자")
    address: str = Field("", description="주소")
    phone: str = Field("", description="연락처")
    employee_count: int | None = Field(None, description="임직원수")
    capital: Decimal | None = Field(None, description="자본금 (백만원)")
    total_assets: Decimal | None = Field(None, description="총자산 (백만원)")
    aum: Decimal | None = Field(None, description="운용자산 AUM (백만원)")
    fund_count: int | None = Field(None, description="운용 펀드수")
    operating_revenue: Decimal | None = Field(None, description="영업수익 (백만원)")
    authorization_date: str = Field("", description="인가일자")
    data_date: str = Field("", description="데이터 기준일")
    source: str = Field("data.go.kr", description="데이터 출처")


class GPRegistryListResponse(BaseModel):
    """자산운용사 목록 응답"""

    total: int
    page: int
    size: int
    items: list[GPRegistryItem]


class GPSyncResponse(BaseModel):
    """GP 프로파일 동기화 결과 응답"""

    total_api_items: int = Field(0, description="API에서 조회된 GP 수")
    created: int = Field(0, description="신규 생성된 Company 수")
    updated: int = Field(0, description="GP 프로파일 업데이트된 Company 수")
    aliases_added: int = Field(0, description="자동 등록된 별칭 수")
    errors: list[str] = Field(default_factory=list, description="에러 발생 GP 목록")


# ──────────────────────────────────────────────
# FreeSIS 기관전용 사모펀드 GP
# ──────────────────────────────────────────────


class FreeSISGPItemResponse(BaseModel):
    """FreeSIS 기관전용 사모펀드 운용사 파싱 결과"""

    company_name: str = Field(..., description="운용사명")
    setting_balance: Decimal | None = Field(None, description="설정잔액 (백만원)")
    fund_count: int | None = Field(None, description="펀드수")
    fund_inflow: Decimal | None = Field(None, description="자금유입 (백만원)")
    fund_outflow: Decimal | None = Field(None, description="자금유출 (백만원)")
    reference_date: str | None = Field(None, description="기준일")


class FreeSISSyncResponse(BaseModel):
    """FreeSIS GP 동기화 결과 응답"""

    total_items: int = Field(0, description="파싱된 GP 수")
    created: int = Field(0, description="신규 생성된 Company 수")
    updated: int = Field(0, description="업데이트된 Company 수")
    matched_existing: int = Field(0, description="기존 Company와 매칭된 수")
    errors: list[str] = Field(default_factory=list, description="에러 발생 GP 목록")


# ──────────────────────────────────────────────
# KVIC 모태펀드 운용사정보
# ──────────────────────────────────────────────


class KVICFundOperatorResponse(BaseModel):
    """KVIC 모태펀드 자조합 운용사 파싱 결과"""

    fund_name: str = Field("", description="조합명")
    operator_name: str = Field(..., description="대표운용(영)사명")
    operator_type: str = Field("", description="운영사구분 (벤처투자회사, 신기술사, LLC 등)")
    representative: str = Field("", description="대표자")
    phone: str = Field("", description="연락처")
    fund_size: Decimal | None = Field(None, description="자조합 규모 (백만원)")
    established_date: str = Field("", description="결성일")


class KVICSyncResponse(BaseModel):
    """KVIC GP 동기화 결과 응답"""

    total_items: int = Field(0, description="파싱된 운용사 수")
    unique_operators: int = Field(0, description="고유 운용사 수 (중복 제거 후)")
    created: int = Field(0, description="신규 생성된 Company 수")
    updated: int = Field(0, description="업데이트된 Company 수")
    matched_existing: int = Field(0, description="기존 Company와 매칭된 수")
    errors: list[str] = Field(default_factory=list, description="에러 발생 운용사 목록")


# ──────────────────────────────────────────────
# GP 통합 조회 (Company 테이블 기반)
# ──────────────────────────────────────────────


class GPCompanyItem(BaseModel):
    """Company 테이블 기반 GP 통합 조회 결과"""

    id: int
    corp_name: str = Field(..., description="정식명칭")
    corp_name_eng: str | None = Field(None, description="영문명칭")
    corp_code: str | None = Field(None, description="DART 고유번호")
    finance_company_code: str | None = Field(None, description="금융회사코드")
    est_dt: str | None = Field(None, description="설립일")
    adres: str | None = Field(None, description="주소")
    phn_no: str | None = Field(None, description="연락처")
    gp_authorization_date: str | None = Field(None, description="인가일자")
    gp_aum: Decimal | None = Field(None, description="운용자산 AUM (백만원)")
    gp_fund_count: int | None = Field(None, description="운용 펀드수")
    gp_employee_count: int | None = Field(None, description="임직원수")
    sources: list[str] = Field(default_factory=list, description="데이터 소스 (freesis, kvic, public_data)")
    strategies: list[str] = Field(default_factory=list, description="전략 태그 (institutional_pef, kvic_fund)")
    gp_profile_synced_at: datetime | None = Field(None, description="마지막 동기화 시각")


class GPCompanyListResponse(BaseModel):
    """Company 테이블 기반 GP 통합 목록 응답"""

    total: int
    page: int
    size: int
    items: list[GPCompanyItem]
    data_reference_date: str | None = Field(None, description="데이터 기준일 (최신 동기화 시각 기준)")
    disclaimer: str = Field(
        default="본 데이터는 공공데이터포털, FreeSIS, KVIC 등 외부 소스에서 수집·동기화된 "
        "참고 정보이며, 실시간 정확성을 보장하지 않습니다. "
        "투자 판단의 근거로 사용하지 마십시오.",
        description="데이터 정확성 면책 고지",
    )


# ──────────────────────────────────────────────
# GP ↔ 펀드 연결 (KVIC 자조합, 금감원 PEF)
# ──────────────────────────────────────────────


class KVICFundItemResponse(BaseModel):
    """KVIC 자조합 응답"""

    id: int
    fund_name: str = Field(..., description="자조합명")
    fund_size: Decimal | None = Field(None, description="자조합 규모 (백만원)")
    operator_type: str | None = Field(None, description="운영사구분")
    established_date: str | None = Field(None, description="결성일")
    synced_at: datetime = Field(..., description="동기화 시각")


class PEFFundItemResponse(BaseModel):
    """금감원 PEF 현황 응답"""

    id: int
    pef_name: str = Field(..., description="PEF 명칭")
    legal_basis: str | None = Field(None, description="설립근거법률")
    registration_date: str | None = Field(None, description="등록일(설립일)")
    total_commitment: Decimal | None = Field(None, description="총약정액 (억원)")
    gp1_name: str = Field(..., description="GP1 (주 업무집행사원)")
    gp2_name: str | None = Field(None, description="GP2 (공동 업무집행사원)")
    gp3_name: str | None = Field(None, description="GP3 (공동 업무집행사원)")
    synced_at: datetime = Field(..., description="동기화 시각")


class GPCompanyDetailResponse(GPCompanyItem):
    """GP 운용사 상세 조회 응답 (자조합/PEF 포함)"""

    kvic_funds: list[KVICFundItemResponse] = Field(default_factory=list, description="KVIC 자조합 목록")
    pef_funds: list[PEFFundItemResponse] = Field(default_factory=list, description="GP1으로 참여하는 PEF 목록")


class FSSPEFSyncResponse(BaseModel):
    """금감원 PEF 동기화 결과 응답"""

    total_items: int = Field(0, description="파싱된 PEF 수")
    created: int = Field(0, description="생성된 PEF 수")
    matched_existing: int = Field(0, description="기존 Company와 매칭된 GP 수")
    new_companies: int = Field(0, description="GP 매칭 실패로 신규 생성된 Company 수")
    errors: list[str] = Field(default_factory=list, description="에러 발생 PEF 목록")
