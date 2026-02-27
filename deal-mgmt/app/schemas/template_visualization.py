"""템플릿 시각화 요청/응답 Pydantic 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ChartSeriesData(BaseModel):
    """차트 시리즈 데이터."""

    name: str = ""
    values: list[float | None]


class ChartReplacement(BaseModel):
    """차트 데이터 교체 지시."""

    shape_name: str = Field(..., description="차트 shape의 이름")
    categories: list[str]
    series: list[ChartSeriesData]
    scale_factor: float = Field(1.0, description="값 스케일링 (0.001=원→천원)")
    number_format: str = '#,##0;(#,##0);"-"'


class TableReplacement(BaseModel):
    """테이블 데이터 교체 지시."""

    shape_name: str = Field(..., description="테이블 shape의 이름")
    headers: list[str] | None = Field(None, description="헤더 라벨. None이면 기존 유지")
    rows: list[list[str | float | None]]
    split_across_slides: bool = Field(False, description="행 초과 시 슬라이드 분할")
    max_rows: int = Field(20, ge=5, le=50)


# Base64 이미지 최대 크기 (10MB)
_MAX_BASE64_LENGTH = 10_485_760


class ImageReplacement(BaseModel):
    """이미지 교체 지시."""

    shape_name: str | None = Field(None, description="단일 이미지 shape 이름")
    grid_prefix: str | None = Field(None, description="그리드 접두사")
    source_base64: str | None = Field(None, max_length=_MAX_BASE64_LENGTH, description="단일 이미지 Base64")
    sources_base64: list[str] = Field(default_factory=list, description="그리드 이미지 Base64 리스트")


class TextReplacement(BaseModel):
    """텍스트 교체 지시."""

    shape_name: str | None = None
    prefix: str | None = None
    mode: Literal["replace", "placeholder", "timeline"] = Field(
        "replace", description="텍스트 교체 모드"
    )
    texts: list[str] = Field(default_factory=list)
    replacements: dict[str, str] = Field(default_factory=dict)
    items: list[dict[str, str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mode_fields(self) -> TextReplacement:
        """mode에 따른 필수 필드 검증."""
        if self.mode == "replace":
            if not self.texts:
                msg = "mode='replace'일 때 texts는 필수입니다."
                raise ValueError(msg)
            if not self.shape_name:
                msg = "mode='replace'일 때 shape_name은 필수입니다."
                raise ValueError(msg)
        elif self.mode == "placeholder":
            if not self.replacements:
                msg = "mode='placeholder'일 때 replacements는 필수입니다."
                raise ValueError(msg)
            if not self.shape_name:
                msg = "mode='placeholder'일 때 shape_name은 필수입니다."
                raise ValueError(msg)
        elif self.mode == "timeline":
            if not self.items:
                msg = "mode='timeline'일 때 items는 필수입니다."
                raise ValueError(msg)
            if not self.prefix:
                msg = "mode='timeline'일 때 prefix는 필수입니다."
                raise ValueError(msg)
        return self


class SlideInstruction(BaseModel):
    """슬라이드별 시각화 지시."""

    slide_index: int = Field(..., ge=0)
    charts: list[ChartReplacement] = Field(default_factory=list)
    tables: list[TableReplacement] = Field(default_factory=list)
    images: list[ImageReplacement] = Field(default_factory=list)
    texts: list[TextReplacement] = Field(default_factory=list)


class TemplateVisualizationRequest(BaseModel):
    """템플릿 시각화 요청 스키마."""

    template_path: str = Field(..., description="입력 템플릿 PPTX 파일 경로")
    slides: list[SlideInstruction]


class TemplateVisualizationResponse(BaseModel):
    """템플릿 시각화 응답 스키마."""

    output_path: str
    charts_updated: int
    tables_updated: int
    images_placed: int
    texts_replaced: int
    slides_added: int
    errors: list[str]
