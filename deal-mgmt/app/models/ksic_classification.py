"""KSIC(한국표준산업분류) 4계층 분류 참조 테이블."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class KsicClassification(Base):
    """KSIC 산업분류 (대→중→소→기본 4계층).

    industry_classification.csv에서 로드. 305개 기본분류 코드.
    참조 전용 — FK 연결 없음 (매핑 테이블 KSIC 코드와 자릿수 불일치).
    """

    __tablename__ = "ksic_classifications"

    basic_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    basic_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sub_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sub_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mid_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mid_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    large_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    large_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
