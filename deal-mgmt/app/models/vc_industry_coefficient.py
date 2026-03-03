"""업종별 투입산출 계수 — MA_ValueChain_v7.xlsx Sheet 3 (1,574×1,574 희소 저장)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VcIndustryCoefficient(Base):
    """1,574개 세부 업종 간 투입산출 계수 (한국은행 2020 산업연관표).

    행(source) = 투입부문, 열(target) = 수요부문.
    - 전방연관(고객): source=타겟 업종 → coefficient 높은 target 업종
    - 후방연관(공급): target=타겟 업종 → coefficient 높은 source 업종

    계수 ≥ 0.001만 저장 (미미한 연관 제외).
    """

    __tablename__ = "vc_industry_coefficients"
    __table_args__ = (
        UniqueConstraint("source_industry", "target_industry", name="uq_vc_coeff_src_tgt"),
        Index("ix_vc_coeff_source", "source_industry"),
        Index("ix_vc_coeff_target", "target_industry"),
        Index("ix_vc_coeff_value", "coefficient"),
        Index("ix_vc_coeff_source_value", "source_industry", "coefficient"),
        Index("ix_vc_coeff_target_value", "target_industry", "coefficient"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_industry: Mapped[str] = mapped_column(String(300), nullable=False)
    target_industry: Mapped[str] = mapped_column(String(300), nullable=False)
    coefficient: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
