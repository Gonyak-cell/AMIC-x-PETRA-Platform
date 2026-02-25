"""Report Pydantic schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class RalphConfigRequest(BaseModel):
    """Ralph Loop 설정 요청."""

    max_iterations_per_section: int = Field(default=3, ge=1, le=5)
    max_cost_usd: float = Field(default=20.0, ge=1.0, le=50.0)
    pass_threshold: float = Field(default=4.0, ge=3.0, le=5.0)


class ReportGenerateRequest(BaseModel):
    """보고서 생성 요청."""

    include_qoe: bool = Field(default=True, description="QoE 섹션 포함")
    include_nwc: bool = Field(default=True, description="NWC 섹션 포함")
    include_debt: bool = Field(default=True, description="Net Debt 섹션 포함")
    include_issues: bool = Field(default=True, description="Issue Log 포함")
    include_financial_statements: bool = Field(
        default=True, description="재무제표(IS/BS/CF) 시트 포함"
    )
    include_trends: bool = Field(
        default=True, description="다기간 트렌드 분석 시트 포함"
    )
    include_sales_analysis: bool = Field(
        default=True, description="매출/원가 상세 분석 시트 포함"
    )
    format: Literal["pptx", "docx", "xlsx", "json"] = Field(
        default="pptx", description="출력 형식 (pptx, docx, xlsx, json)"
    )
    checklist_id: str | None = Field(
        default=None,
        description="체크리스트 ID — 지정 시 체크리스트 수정사항이 반영된 Refined Report IR 사용",
    )
    ralph_enabled: bool = Field(
        default=False,
        description="Ralph Loop AI 품질 개선 활성화 (Pass 1: Draft Refinement)",
    )
    ralph_config: RalphConfigRequest | None = Field(
        default=None,
        description="Ralph Loop 설정 (미지정 시 기본값 사용)",
    )
    qa_enabled: bool = Field(
        default=False,
        description="레포트 QA 활성화. True이면 생성된 레포트를 독립 LLM으로 팩트체크.",
    )


class ReportPreviewResponse(BaseModel):
    """보고서 미리보기 응답."""

    deal_id: str
    deal_name: str
    sections_count: int
    sections: list[dict]

    model_config = {"from_attributes": True}


class ReportMetadataResponse(BaseModel):
    """보고서 메타데이터 응답."""

    deal_id: str
    deal_name: str
    generated_at: str
    version: str
    engine_versions: dict[str, str]

    model_config = {"from_attributes": True}
