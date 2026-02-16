"""Report Pydantic schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """보고서 생성 요청."""

    include_qoe: bool = Field(default=True, description="QoE 섹션 포함")
    include_nwc: bool = Field(default=True, description="NWC 섹션 포함")
    include_debt: bool = Field(default=True, description="Net Debt 섹션 포함")
    include_issues: bool = Field(default=True, description="Issue Log 포함")
    format: Literal["pptx", "docx", "json"] = Field(
        default="pptx", description="출력 형식 (pptx, docx, json)"
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
