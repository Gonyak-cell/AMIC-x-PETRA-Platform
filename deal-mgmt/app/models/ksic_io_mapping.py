"""KSIC(한국표준산업분류) ↔ I-O(산업연관표) 부문분류코드 매핑 테이블."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class KsicIoMapping(Base):
    """KSIC 코드와 산업연관표 I-O 코드 간의 N:M 매핑."""

    __tablename__ = "ksic_io_mappings"
    __table_args__ = (
        UniqueConstraint("io_code", "ksic_code", name="uq_ksic_io_mapping"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    io_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("io_sectors.code"),
        nullable=False,
        index=True,
    )
    io_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ksic_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    ksic_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
