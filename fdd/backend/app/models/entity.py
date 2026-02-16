"""엔티티(법인) 모델 — Sprint 16 (멀티 엔티티 지원).

Deal 하위의 법인 구조를 관리한다.
단일 법인 딜에서는 기본 TARGET 엔티티 하나만 존재.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EntityType(str, enum.Enum):
    """엔티티 유형."""

    TARGET = "TARGET"  # 인수 대상 (딜당 1개)
    SUBSIDIARY = "SUBSIDIARY"  # 자회사
    SPV = "SPV"  # 특수목적법인
    CONSOLIDATED = "CONSOLIDATED"  # 연결 기준 (가상 엔티티)


class Entity(Base):
    """딜 하위 법인.

    멀티 엔티티 딜에서 각 법인(자회사/SPV)을 나타낸다.
    parent_entity_id를 통해 1-depth 계층 구조를 지원.
    """

    __tablename__ = "entity"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="SET NULL"),
        nullable=True,
        comment="상위 엔티티 (TARGET의 경우 NULL)",
    )
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType),
        nullable=False,
        default=EntityType.TARGET,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="법인명")
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="법인 코드 (딜 내 고유)"
    )
    functional_currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="KRW", comment="기능통화"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ownership_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 4),
        nullable=True,
        comment="지분율 (100.0000 = 100%)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    parent: Mapped["Entity | None"] = relationship(
        remote_side=[id], foreign_keys=[parent_entity_id]
    )
    children: Mapped[list["Entity"]] = relationship(
        foreign_keys=[parent_entity_id],
    )

    __table_args__ = (
        Index("ix_entity_deal", "deal_id"),
        UniqueConstraint("deal_id", "code", name="uq_entity_deal_code"),
    )
