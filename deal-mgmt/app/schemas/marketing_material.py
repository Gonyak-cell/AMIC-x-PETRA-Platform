"""마케팅 자료 스키마 — TM / DM / IM."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from app.models.enums import MarketingDocStatus, MarketingDocType


class MarketingMaterialCreate(BaseModel):
    """마케팅 자료 생성 요청 스키마."""

    doc_type: MarketingDocType
    title: str = Field(..., min_length=1, max_length=300)
    project_code: str | None = Field(
        None, max_length=100, description="프로젝트 코드명 (예: ALPHA). 없으면 transaction에서 자동 생성."
    )
    parameters: dict | None = Field(None, description="memo_generator content JSON. 없으면 기본 템플릿 사용.")
    enable_ralph_loop: bool = Field(False, description="Ralph Loop 품질 강화 모드 활성화")
    ralph_max_iterations: int = Field(3, ge=1, le=10, description="Ralph Loop 최대 반복 횟수")
    ralph_max_cost_usd: float = Field(10.0, ge=1.0, le=50.0, description="Ralph Loop 최대 비용 (USD)")


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
    quality_score: float | None = None
    quality_status: str | None = None
    quality_issues: list | None = None
    slide_count: int | None = None
    template_fingerprint: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pipeline_metrics(self) -> dict[str, int] | None:
        """parameters._metrics에서 성능 메트릭 추출."""
        if self.parameters and isinstance(self.parameters.get("_metrics"), dict):
            return self.parameters["_metrics"]
        return None

    distributed_to: list | None
    distributed_at: str | None
    created_by_email: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def distribution_eligible(self) -> bool:
        """PASS 상태만 배포 가능."""
        return self.quality_status == "PASS"

    model_config = {"from_attributes": True}


class MarketingMaterialSourceRoutingDocumentOut(BaseModel):
    document_id: uuid.UUID
    original_name: str
    folder_category: str
    ddrl_sections: list[str] = Field(default_factory=list)
    primary_workstream: str
    workstream_tags: list[str] = Field(default_factory=list)
    confidence: float
    requires_manual_review: bool
    reasons: list[str] = Field(default_factory=list)
    is_override: bool = False
    override_note: str | None = None
    reviewed_by_email: str | None = None
    reviewed_at: str | None = None
    include_for_marketing_material: bool = False


class MarketingMaterialSourceRoutingSummaryOut(BaseModel):
    total_documents: int
    included_for_marketing_material: int
    excluded_from_marketing_material: int
    manual_review_documents: int
    overridden_documents: int = 0
    by_primary_workstream: dict[str, int] = Field(default_factory=dict)
    target_workstreams: list[str] = Field(default_factory=list)


class MarketingMaterialSourceRoutingPreviewOut(BaseModel):
    version: str
    summary: MarketingMaterialSourceRoutingSummaryOut
    documents: list[MarketingMaterialSourceRoutingDocumentOut] = Field(default_factory=list)
