"""IO 유발계수 팩트 테이블 — 생산유발계수 + 부가가치유발계수."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IOProductionInducement(Base):
    """생산유발계수 — source(투입) → target(산출) 계수."""

    __tablename__ = "io_production_inducements"
    __table_args__ = (
        UniqueConstraint(
            "source_io_code", "target_io_code", name="uq_prod_ind_src_tgt"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_io_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("io_sectors.code"),
        nullable=False,
        index=True,
    )
    target_io_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("io_sectors.code"),
        nullable=False,
        index=True,
    )
    coefficient: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)


class IOValueAddedInducement(Base):
    """부가가치유발계수 — source → target 계수."""

    __tablename__ = "io_value_added_inducements"
    __table_args__ = (
        UniqueConstraint(
            "source_io_code", "target_io_code", name="uq_va_ind_src_tgt"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_io_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("io_sectors.code"),
        nullable=False,
        index=True,
    )
    target_io_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("io_sectors.code"),
        nullable=False,
        index=True,
    )
    coefficient: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
