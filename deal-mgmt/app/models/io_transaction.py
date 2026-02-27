"""투입산출표(I-O Table) 총거래 팩트 테이블 — 행렬을 평탄화한 구조."""

from __future__ import annotations

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IOTransaction(Base):
    """산업 간 거래 관계 — source(공급) → target(수요) 방향."""

    __tablename__ = "io_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_io_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_io_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_io_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    target_io_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transaction_value: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
