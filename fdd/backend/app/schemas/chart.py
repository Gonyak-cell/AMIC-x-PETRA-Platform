"""Chart API Pydantic 스키마.

워터폴 차트 등 차트 생성 API의 요청/응답 스키마를 정의합니다.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class EBITDABridgeRequest(BaseModel):
    """EBITDA Bridge 워터폴 차트 생성 요청.

    Example:
        {
            "categories": ["Reported EBITDA", "일회성 조정", "비영업 조정", "Adjusted EBITDA"],
            "values": ["1000000000", "200000000", "-50000000", null],
            "title": "FY2025 EBITDA Bridge"
        }
    """

    categories: list[str] = Field(
        ...,
        min_length=2,
        max_length=20,
        description="x축 레이블 리스트 (최소 2개, 최대 20개)",
    )
    values: list[str | None] = Field(
        ...,
        min_length=2,
        max_length=20,
        description="각 항목의 금액 (문자열). 마지막 total은 null 가능",
    )
    title: str = Field(
        default="EBITDA Bridge",
        max_length=100,
        description="차트 제목",
    )

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: list[str | None]) -> list[str | None]:
        """금액 값이 유효한 숫자인지 검증."""
        for i, val in enumerate(v):
            if val is not None:
                try:
                    float(val)
                except ValueError as e:
                    raise ValueError(
                        f"values[{i}]가 유효한 숫자가 아닙니다: {val}"
                    ) from e
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "categories": [
                    "Reported EBITDA",
                    "일회성 비용",
                    "비영업 수익",
                    "Adjusted EBITDA",
                ],
                "values": ["1000000000", "200000000", "-50000000", None],
                "title": "FY2025 EBITDA Bridge",
            }
        }
    }


class GenericWaterfallRequest(BaseModel):
    """범용 워터폴 차트 생성 요청."""

    categories: list[str] = Field(
        ...,
        min_length=2,
        max_length=30,
        description="x축 레이블 리스트",
    )
    values: list[str | None] = Field(
        ...,
        min_length=2,
        max_length=30,
        description="각 항목의 값 (문자열). total 항목은 null 가능",
    )
    measures: list[Literal["absolute", "relative", "total"]] | None = Field(
        default=None,
        description="각 항목의 측정 타입. None이면 자동 결정 (첫 번째=absolute, 중간=relative, 마지막=total)",
    )
    title: str = Field(
        default="Waterfall Chart",
        max_length=100,
        description="차트 제목",
    )
    y_axis_title: str = Field(
        default="Value",
        max_length=50,
        description="y축 제목",
    )

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: list[str | None]) -> list[str | None]:
        """금액 값이 유효한 숫자인지 검증."""
        for i, val in enumerate(v):
            if val is not None:
                try:
                    float(val)
                except ValueError as e:
                    raise ValueError(
                        f"values[{i}]가 유효한 숫자가 아닙니다: {val}"
                    ) from e
        return v


class NWCBridgeRequest(BaseModel):
    """NWC Bridge 워터폴 차트 생성 요청."""

    categories: list[str] = Field(
        ...,
        min_length=2,
        description="NWC 구성 항목 (예: ['매출채권', '재고자산', '매입채무', ...])",
    )
    values: list[str | None] = Field(
        ...,
        min_length=2,
        description="각 항목의 금액",
    )
    title: str = Field(
        default="Net Working Capital Bridge",
        max_length=100,
    )

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: list[str | None]) -> list[str | None]:
        for i, val in enumerate(v):
            if val is not None:
                try:
                    float(val)
                except ValueError as e:
                    raise ValueError(
                        f"values[{i}]가 유효한 숫자가 아닙니다: {val}"
                    ) from e
        return v


class NetDebtBridgeRequest(BaseModel):
    """Net Debt Bridge 워터폴 차트 생성 요청."""

    categories: list[str] = Field(
        ...,
        min_length=2,
        description="Net Debt 구성 항목 (예: ['총 차입금', '현금 및 현금성 자산', 'Net Debt'])",
    )
    values: list[str | None] = Field(
        ...,
        min_length=2,
        description="각 항목의 금액",
    )
    title: str = Field(
        default="Net Debt Bridge",
        max_length=100,
    )

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: list[str | None]) -> list[str | None]:
        for i, val in enumerate(v):
            if val is not None:
                try:
                    float(val)
                except ValueError as e:
                    raise ValueError(
                        f"values[{i}]가 유효한 숫자가 아닙니다: {val}"
                    ) from e
        return v


class ChartExportFormat(BaseModel):
    """차트 내보내기 포맷 옵션."""

    format: Literal["png", "svg", "pdf"] = Field(
        default="png",
        description="출력 포맷",
    )
    width: int = Field(
        default=900,
        ge=400,
        le=1920,
        description="너비 (픽셀)",
    )
    height: int = Field(
        default=500,
        ge=300,
        le=1080,
        description="높이 (픽셀)",
    )
    scale: float = Field(
        default=2.0,
        ge=1.0,
        le=4.0,
        description="스케일 (DPI 조정, 2.0 = 300 DPI)",
    )
