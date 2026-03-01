import uuid
from decimal import Decimal

from sqlalchemy import Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PefFundRegistry(Base, TimestampMixin):
    """기관전용 사모집합투자기구(PEF) 레지스트리.

    금융감독원 공시 기준 1,137건 PEF 데이터.
    FI 자동 추천 로직에서 총약정액 기준 필터링에 사용.
    """

    __tablename__ = "pef_fund_registry"
    __table_args__ = (
        Index("ix_pef_fund_registry_capital", "total_committed_capital"),
        Index("ix_pef_fund_registry_gp1", "gp1"),
        Index("ix_pef_fund_registry_gp2", "gp2"),
        Index("ix_pef_fund_registry_gp3", "gp3"),
        Index("ix_pef_fund_registry_pef_name", "pef_name"),
        Index("ix_pef_fund_registry_reg_date", "registration_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pef_name: Mapped[str] = mapped_column(String(300), nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registration_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gp1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gp2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gp3: Mapped[str | None] = mapped_column(String(200), nullable=True)
    total_committed_capital: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
