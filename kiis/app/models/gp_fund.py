"""GP ↔ 펀드 연결 모델 (KVIC 자조합, 금감원 PEF)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class KVICFund(TimestampMixin, Base):
    """KVIC 모태펀드 자조합."""

    __tablename__ = "kvic_funds"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        comment="GP 운용사 (companies FK)",
    )
    fund_name: Mapped[str] = mapped_column(String(500), comment="자조합명")
    fund_size: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 0),
        nullable=True,
        comment="자조합 규모 (백만원)",
    )
    operator_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="운영사구분 (벤처투자회사, 신기술사, LLC 등)",
    )
    representative: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="대표자",
    )
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="연락처",
    )
    established_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="결성일",
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        comment="동기화 시각",
    )

    company: Mapped[Company] = relationship(back_populates="kvic_funds")  # noqa: F821


class PEFFund(TimestampMixin, Base):
    """금감원 기관전용 사모집합투자기구(PEF) 현황."""

    __tablename__ = "pef_funds"

    id: Mapped[int] = mapped_column(primary_key=True)
    pef_name: Mapped[str] = mapped_column(
        String(500),
        index=True,
        comment="PEF 명칭",
    )
    legal_basis: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="설립근거법률 (자본시장법 등)",
    )
    registration_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="등록일(설립일)",
    )
    total_commitment: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 0),
        nullable=True,
        comment="총약정액 (억원)",
    )
    # GP1 (주 GP) - 필수
    gp1_company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        comment="GP1 (주 업무집행사원)",
    )
    # GP2, GP3 - 선택 (공동 GP)
    gp2_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        comment="GP2 (공동 업무집행사원)",
    )
    gp3_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        comment="GP3 (공동 업무집행사원)",
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        comment="동기화 시각",
    )

    gp1_company: Mapped[Company] = relationship(  # noqa: F821
        foreign_keys=[gp1_company_id],
        back_populates="pef_funds_as_gp1",
    )
    gp2_company: Mapped[Company | None] = relationship(  # noqa: F821
        foreign_keys=[gp2_company_id],
        back_populates="pef_funds_as_gp2",
    )
    gp3_company: Mapped[Company | None] = relationship(  # noqa: F821
        foreign_keys=[gp3_company_id],
        back_populates="pef_funds_as_gp3",
    )
