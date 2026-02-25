"""마케팅 자료 스키마 — TM / DM / IM."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MarketingDocStatus, MarketingDocType


class MarketingMaterialCreate(BaseModel):
    """마케팅 자료 생성 요청 스키마."""

    doc_type: MarketingDocType
    title: str = Field(..., min_length=1, max_length=300)
    project_code: str | None = Field(None, max_length=100,
                                     description="프로젝트 코드명 (예: ALPHA). 없으면 transaction에서 자동 생성.")
    parameters: dict | None = Field(None,
                                    description="memo_generator content JSON. 없으면 기본 템플릿 사용.")
    enable_ralph_loop: bool = Field(False,
                                    description="Ralph Loop 품질 강화 모드 활성화")
    ralph_max_iterations: int = Field(3, ge=1, le=10,
                                      description="Ralph Loop 최대 반복 횟수")
    ralph_max_cost_usd: float = Field(10.0, ge=1.0, le=50.0,
                                       description="Ralph Loop 최대 비용 (USD)")


class DistributionUpdate(BaseModel):
    """배포 대상 목록 업데이트 스키마."""

    distributed_to: list[str] = Field(..., description="배포 대상 회사명 또는 이메일 목록")
    distributed_at: str | None = Field(None, description="배포 일시 (ISO 8601). 없으면 현재 시각.")


class MarketingMaterialOut(BaseModel):
    """마케팅 자료 응답 스키마."""

    id: uuid.UUID
    transaction_id: uuid.UUID
    doc_type: MarketingDocType
    title: str
    project_code: str | None
    status: MarketingDocStatus
    error_message: str | None
    parameters: dict | None
    file_path: str | None
    file_name: str | None
    file_size_bytes: int | None
    distributed_to: list | None
    distributed_at: str | None
    created_by_email: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
