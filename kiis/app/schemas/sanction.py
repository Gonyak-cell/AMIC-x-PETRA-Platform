"""제재 분류 스키마"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClassifiedSanctionItem(BaseModel):
    """분류된 제재 상세 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int = Field(..., description="기업 ID")
    corp_code: str = Field(..., description="DART 고유번호")
    sanctions_type: str = Field(..., description="제재유형")
    sanctions_detail: str | None = Field(None, description="제재내용")
    sanctions_date: str | None = Field(None, description="제재일자")
    sanctions_agency: str | None = Field(None, description="제재기관")
    severity: str = Field(..., description="경중 등급 (caution/warning/critical)")
    severity_reason: str | None = Field(None, description="경중 분류 근거")
    category: str | None = Field(None, description="제재 유형 분류")
    classified_at: datetime | None = Field(None, description="분류 시각")


class ClassifiedSanctionListItem(BaseModel):
    """분류된 제재 목록 아이템 (간략)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    corp_code: str
    sanctions_type: str
    severity: str
    category: str | None
    sanctions_date: str | None


class ClassifiedSanctionListResponse(BaseModel):
    """분류된 제재 목록 응답 (페이지네이션)"""

    total: int = Field(..., description="총 건수")
    page: int = Field(..., description="페이지 번호")
    size: int = Field(..., description="페이지 크기")
    items: list[ClassifiedSanctionListItem] = Field(default_factory=list, description="제재 목록")


class SanctionSummaryResponse(BaseModel):
    """제재 요약 응답"""

    total: int = Field(..., description="총 제재 건수")
    caution_count: int = Field(0, description="주의 건수")
    warning_count: int = Field(0, description="경고 건수")
    critical_count: int = Field(0, description="위험 건수")


class SanctionClassifyResponse(BaseModel):
    """제재 분류 실행 응답"""

    corp_code: str = Field(..., description="DART 고유번호")
    classified_count: int = Field(..., description="분류된 건수")
    items: list[ClassifiedSanctionItem] = Field(default_factory=list, description="분류된 제재 목록")
