"""Document 관련 스키마 (T-I15).

> 마지막 수정: 2026-02-12 10:39:21

IM 문서 생성 요청/응답 Pydantic v2 스키마를 정의한다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


_VALID_IM_STYLES = {"TITAN", "COVENANT", "FULL", "CUSTOM"}

# 전용 산업 모듈이 등록된 산업
_SUPPORTED_INDUSTRIES = {
    "general", "tech", "manufacturing", "healthcare", "logistics", "financial_services",
}
# 전용 모듈 없이 GeneralModule로 폴백되는 산업 (프론트엔드에서 선택 가능)
_BASIC_INDUSTRIES = {"real_estate", "energy", "consumer"}
_ALL_VALID_INDUSTRIES = _SUPPORTED_INDUSTRIES | _BASIC_INDUSTRIES


class DocumentCreate(BaseModel):
    """IM 문서 생성 요청."""

    corp_code: str = Field(
        min_length=8, max_length=8, description="법인 코드 (8자리 숫자)"
    )
    project_name: str | None = Field(
        default=None, max_length=200, description="프로젝트명"
    )
    im_style: str = Field(
        default="FULL", description="IM 양식 (TITAN/COVENANT/FULL/CUSTOM)"
    )
    sections: list[str] = Field(
        default_factory=list, description="포함 섹션 리스트"
    )
    industry: str = Field(
        default="general", max_length=50, description="산업 분류"
    )
    webhook_url: str | None = Field(
        default=None, description="완료 시 호출할 웹훅 URL"
    )
    pdf_password: str | None = Field(
        default=None, min_length=4, description="PDF 암호 (최소 4자)"
    )

    @field_validator("corp_code")
    @classmethod
    def validate_corp_code(cls, v: str) -> str:
        """corp_code가 8자리 숫자인지 검증한다."""
        if not v.isdigit():
            raise ValueError("corp_code는 8자리 숫자여야 합니다")
        return v

    @field_validator("im_style")
    @classmethod
    def validate_im_style(cls, v: str) -> str:
        """im_style이 유효한 값인지 검증한다."""
        if v not in _VALID_IM_STYLES:
            raise ValueError(f"im_style은 {_VALID_IM_STYLES} 중 하나여야 합니다")
        return v

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: str) -> str:
        """industry가 유효한 산업 ID인지 검증한다."""
        if v and v not in _ALL_VALID_INDUSTRIES:
            raise ValueError(
                f"industry는 {sorted(_ALL_VALID_INDUSTRIES)} 중 하나여야 합니다"
            )
        return v


class DocumentResponse(BaseModel):
    """IM 문서 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    corp_code: str
    company_name: str
    project_name: str | None
    im_style: str
    sections: list[str]
    industry: str | None = None
    status: str
    progress_pct: int
    celery_task_id: str | None
    pptx_path: str | None
    pdf_path: str | None
    file_size_bytes: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class DocumentListResponse(BaseModel):
    """문서 목록 응답 (페이지네이션 포함)."""

    items: list[DocumentResponse]
    total: int
    offset: int
    limit: int
