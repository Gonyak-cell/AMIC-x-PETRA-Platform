"""IO(산업연관표) 부문분류 마스터 — 380개 기본부문 코드."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IOSector(Base):
    """산업연관표 기본부문(4자리) 마스터 — transaction_table.csv에서 추출."""

    __tablename__ = "io_sectors"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
