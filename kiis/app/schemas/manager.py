"""심사역 이동 추적 스키마"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ManagerMovementItem(BaseModel):
    """심사역 이동 상세 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    manager_name: str = Field(..., description="심사역 이름")
    from_company_id: int | None = Field(None, description="이전 소속 기업 ID")
    from_company_name: str | None = Field(None, description="이전 소속 기업명")
    from_fund_id: int | None = Field(None, description="이전 소속 펀드 ID")
    to_company_id: int | None = Field(None, description="새 소속 기업 ID")
    to_company_name: str | None = Field(None, description="새 소속 기업명")
    to_fund_id: int | None = Field(None, description="새 소속 펀드 ID")
    movement_type: str = Field(..., description="이동 유형 (transfer/resignation/appointment)")
    detected_at: datetime = Field(..., description="감지 일시")
    source: str | None = Field(None, description="감지 출처 (kofia/news)")
    notes: str | None = Field(None, description="비고")


class ManagerMovementListResponse(BaseModel):
    """심사역 이동 목록 응답"""

    total: int = Field(..., description="총 건수")
    page: int = Field(..., description="페이지 번호")
    size: int = Field(..., description="페이지 크기")
    items: list[ManagerMovementItem] = Field(default_factory=list, description="이동 이력 목록")


class ManagerDealItem(BaseModel):
    """심사역 관여 딜 간략 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    target_company: str = Field(..., description="피투자사명")
    amount_display: str | None = Field(None, description="투자 금액 표시용")
    round_stage: str | None = Field(None, description="투자 단계")
    sector: str | None = Field(None, description="투자 섹터")


class ManagerProfileResponse(BaseModel):
    """심사역 프로필 응답"""

    manager_name: str = Field(..., description="심사역 이름")
    current_company: str | None = Field(None, description="현 소속 기업명")
    current_fund: str | None = Field(None, description="현 소속 펀드명")
    specialty_sectors: list[str] = Field(default_factory=list, description="전문 섹터 목록")
    career_years: int | None = Field(None, description="경력 년수")
    total_deals_involved: int = Field(0, description="관여 딜 수")
    movements: list[ManagerMovementItem] = Field(default_factory=list, description="이동 이력")
    deals: list[ManagerDealItem] = Field(default_factory=list, description="관여 딜 목록")


class ManagerTrackResponse(BaseModel):
    """심사역 이동 스캔 결과"""

    scanned_count: int = Field(..., description="스캔된 심사역 수")
    new_movements_count: int = Field(..., description="신규 감지 이동 수")
    movements: list[ManagerMovementItem] = Field(default_factory=list, description="신규 이동 이력")
