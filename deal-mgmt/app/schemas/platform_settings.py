"""플랫폼 전역 설정 스키마."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import TableStyleTheme


class PlatformSettingsResponse(BaseModel):
    """설정 조회 응답."""

    model_config = ConfigDict(from_attributes=True)

    site_name: str
    contact_email: str | None = None
    table_style: str


class PlatformSettingsUpdate(BaseModel):
    """설정 업데이트 요청 (partial update)."""

    site_name: str | None = None
    contact_email: str | None = None
    legal_terms: str | None = None
    privacy_policy: str | None = None
    table_style: str | None = None

    @field_validator("table_style")
    @classmethod
    def validate_table_style(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {t.value for t in TableStyleTheme}
        if v not in valid:
            msg = f"유효하지 않은 테이블 스타일입니다: {v}"
            raise ValueError(msg)
        return v
