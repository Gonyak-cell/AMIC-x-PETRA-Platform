"""플랫폼 전역 설정 (싱글턴)."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import TableStyleTheme


class PlatformSettings(Base, TimestampMixin):
    """플랫폼 전역 설정. id=1 싱글턴으로 관리."""

    __tablename__ = "platform_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_platform_settings_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    site_name: Mapped[str] = mapped_column(String(200), default="AMIC Platform")
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    legal_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    privacy_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    table_style: Mapped[str] = mapped_column(String(50), default=TableStyleTheme.DEFAULT.value)
