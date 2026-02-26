"""법률 문서 Pydantic 스키마."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.models.enums import LegalDocStatus, LegalDocType

# ── 공통 유효성 헬퍼 ──────────────────────────────────────────────────────────

def _validate_date_str(v: object) -> str:
    """날짜 형식(YYYY-MM-DD) 및 실제 날짜 유효성 검증."""
    if not isinstance(v, str) or not v.strip():
        return str(v) if v else ""
    v = v.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        raise ValueError("날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요 (예: 2026-03-15)")
    year, month, day = map(int, v.split("-"))
    try:
        date(year, month, day)
    except ValueError as e:
        raise ValueError(f"유효하지 않은 날짜입니다: {e}") from e
    return v


# 재사용 가능한 날짜 어노테이션 (빈 문자열 허용)
DateStr = Annotated[str, BeforeValidator(_validate_date_str)]


# ── 응답 스키마 ───────────────────────────────────────────────────────────────

class LegalDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    doc_type: LegalDocType
    title: str
    status: LegalDocStatus
    parameters: dict[str, Any] | None = None
    template_version: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    error_message: str | None = None
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


# ── 생성 스키마 ───────────────────────────────────────────────────────────────

class LegalDocumentCreate(BaseModel):
    doc_type: LegalDocType
    title: str = Field(..., min_length=1, max_length=300)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_parameters_by_type(self) -> LegalDocumentCreate:
        """doc_type에 맞는 파라미터 스키마로 유효성 검증."""
        schema_map: dict[LegalDocType, type[BaseModel]] = {
            LegalDocType.SPA: SPAParameters,
            LegalDocType.SHA: SHAParameters,
            LegalDocType.BTA: BTAParameters,
            LegalDocType.SSA: SSAParameters,
            LegalDocType.MOU: MOUParameters,
        }
        schema = schema_map.get(self.doc_type)
        if schema and self.parameters:
            schema.model_validate(self.parameters)
        return self


# ── 타입별 파라미터 스키마 ────────────────────────────────────────────────────

class SPAParameters(BaseModel):
    """주식매매계약 (Stock Purchase Agreement) 파라미터."""

    seller_name: str = Field(..., description="매도인명")
    seller_representative: str = Field(..., description="매도인 대표이사")
    seller_address: str = Field("", description="매도인 주소")
    buyer_name: str = Field(..., description="매수인명")
    buyer_representative: str = Field(..., description="매수인 대표이사")
    buyer_address: str = Field("", description="매수인 주소")
    target_company_name: str = Field(..., description="대상회사명")
    target_corp_reg_no: str = Field("", description="대상회사 법인등록번호")
    total_shares: int = Field(0, ge=0, description="발행주식 총수")
    transfer_shares: int = Field(0, ge=0, description="양도 주식 수")
    share_price_per: int = Field(0, ge=0, description="주당 양도가격 (원)")
    total_purchase_price: int = Field(0, ge=0, description="총 양도대금 (원)")
    signing_date: DateStr = Field("", description="계약 체결일 (YYYY-MM-DD)")
    closing_date: DateStr = Field("", description="거래 종결일 (YYYY-MM-DD)")
    warranty_period_months: int = Field(24, ge=0, description="진술보장 기간 (개월)")
    escrow_amount: int = Field(0, ge=0, description="에스크로 금액 (원)")
    escrow_period_months: int = Field(18, ge=0, description="에스크로 유지 기간 (개월)")
    governing_law: str = Field("대한민국", description="준거법")

    @model_validator(mode="after")
    def validate_transfer_not_exceed_total(self) -> SPAParameters:
        if self.total_shares > 0 and self.transfer_shares > self.total_shares:
            raise ValueError(
                f"양도주식 수({self.transfer_shares:,})는 "
                f"총발행주식 수({self.total_shares:,})를 초과할 수 없습니다"
            )
        return self


class SHAParameters(BaseModel):
    """주주간계약 (Shareholders Agreement) 파라미터."""

    company_name: str = Field(..., description="회사명")
    shareholders: list[dict[str, Any]] = Field(
        default_factory=list,
        description="주주 목록: [{name, shares, pct}]",
    )
    board_seats_total: int = Field(3, ge=1, description="이사회 총 의석수")
    board_seats_by_shareholder: list[dict[str, Any]] = Field(
        default_factory=list,
        description="주주별 이사 지명권: [{shareholder, seats}]",
    )
    rofr_included: bool = Field(True, description="우선매수권 포함 여부")
    drag_along_included: bool = Field(True, description="동반매각권 포함 여부")
    tag_along_included: bool = Field(True, description="동반참여권 포함 여부")
    lock_up_months: int = Field(24, ge=0, description="락업 기간 (개월)")
    non_compete_months: int = Field(36, ge=0, description="경업금지 기간 (개월)")
    dividend_policy: str = Field("", description="배당 정책")
    signing_date: DateStr = Field("", description="계약 체결일 (YYYY-MM-DD)")
    governing_law: str = Field("대한민국", description="준거법")


class BTAParameters(BaseModel):
    """영업양수도계약 (Business Transfer Agreement) 파라미터."""

    transferor_name: str = Field(..., description="양도인명")
    transferor_representative: str = Field(..., description="양도인 대표이사")
    transferee_name: str = Field(..., description="양수인명")
    transferee_representative: str = Field(..., description="양수인 대표이사")
    business_description: str = Field(..., description="양도대상 사업 내용")
    transferred_assets: list[str] = Field(default_factory=list, description="이전 자산 목록")
    excluded_assets: list[str] = Field(default_factory=list, description="제외 자산 목록")
    transferred_liabilities: list[str] = Field(default_factory=list, description="인수 부채 목록")
    total_consideration: int = Field(0, ge=0, description="양도 대금 (원)")
    signing_date: DateStr = Field("", description="계약 체결일 (YYYY-MM-DD)")
    closing_date: DateStr = Field("", description="양도 실행일 (YYYY-MM-DD)")
    employee_transfer: bool = Field(True, description="직원 이전 여부")
    employee_count: int = Field(0, ge=0, description="이전 직원 수")
    governing_law: str = Field("대한민국", description="준거법")


class SSAParameters(BaseModel):
    """신주인수계약 (Share Subscription Agreement) 파라미터."""

    company_name: str = Field(..., description="발행 회사명")
    company_representative: str = Field(..., description="회사 대표이사")
    investor_name: str = Field(..., description="인수인명")
    investor_representative: str = Field(..., description="인수인 대표이사")
    new_shares_count: int = Field(0, ge=0, description="발행 신주 수")
    subscription_price_per: int = Field(0, ge=0, description="주당 인수가액 (원)")
    total_investment: int = Field(0, ge=0, description="총 인수대금 (원)")
    share_class: str = Field("보통주", description="주식 종류")
    pre_money_valuation: int = Field(0, ge=0, description="Pre-money 기업가치 (원)")
    post_money_valuation: int = Field(0, ge=0, description="Post-money 기업가치 (원)")
    anti_dilution: str = Field("broad_based_weighted_average", description="희석방지 조항 방식")
    liquidation_preference_x: float = Field(1.0, ge=0.0, description="청산우선권 배수")
    board_seats: int = Field(1, ge=0, description="이사 지명권 수")
    signing_date: DateStr = Field("", description="계약 체결일 (YYYY-MM-DD)")
    investment_date: DateStr = Field("", description="납입 기일 (YYYY-MM-DD)")
    use_of_proceeds: str = Field("", description="자금 사용 목적")
    governing_law: str = Field("대한민국", description="준거법")

    @model_validator(mode="after")
    def validate_post_money_ge_pre_money(self) -> SSAParameters:
        if self.pre_money_valuation > 0 and self.post_money_valuation > 0:
            if self.post_money_valuation < self.pre_money_valuation:
                raise ValueError(
                    f"Post-money 기업가치({self.post_money_valuation:,})는 "
                    f"Pre-money 기업가치({self.pre_money_valuation:,}) 이상이어야 합니다"
                )
        return self


class MOUParameters(BaseModel):
    """양해각서 (Memorandum of Understanding) 파라미터."""

    party_a_name: str = Field(..., description="당사자 갑 (회사명)")
    party_a_representative: str = Field(..., description="갑 대표이사")
    party_b_name: str = Field(..., description="당사자 을 (회사명)")
    party_b_representative: str = Field(..., description="을 대표이사")
    purpose: str = Field(..., description="양해각서 목적")
    exclusivity_period_days: int = Field(90, ge=0, description="독점협상기간 (일)")
    exclusivity_start_date: DateStr = Field("", description="독점협상 시작일 (YYYY-MM-DD)")
    confidentiality_period_months: int = Field(24, ge=0, description="비밀유지 기간 (개월)")
    binding_provisions: list[str] = Field(
        default_factory=lambda: ["비밀유지", "독점협상"],
        description="구속력 있는 조항 목록",
    )
    non_binding_provisions: list[str] = Field(
        default_factory=lambda: ["가격협상", "거래구조"],
        description="비구속적 조항 목록",
    )
    signing_date: DateStr = Field("", description="양해각서 체결일 (YYYY-MM-DD)")
    governing_law: str = Field("대한민국", description="준거법")
