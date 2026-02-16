import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MappingConfidence(str, enum.Enum):
    """매핑 신뢰도."""

    HIGH = "HIGH"  # 정확 일치 또는 사용자 승인
    MEDIUM = "MEDIUM"  # 키워드/Fuzzy ≥70%
    LOW = "LOW"  # Fuzzy 50-69%
    UNMAPPED = "UNMAPPED"  # 매핑 불가


class MappingStatus(str, enum.Enum):
    """매핑 상태."""

    PROPOSED = "PROPOSED"  # 자동 제안
    APPROVED = "APPROVED"  # 사용자 승인
    REJECTED = "REJECTED"  # 사용자 거부
    MANUAL = "MANUAL"  # 수동 입력


class AccountMapping(Base):
    """계정 매핑 — FDD-302.

    원천 계정(TB account_code)을 표준 라인아이템(StandardLineItem.code)에 매핑.
    신뢰도 스코어 및 승인 워크플로 포함.
    """

    __tablename__ = "account_mapping"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Entity (multi-entity support) ──
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Source (원천 계정) ──
    source_account_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="TB 원본 계정코드"
    )
    source_account_name: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="TB 원본 계정명"
    )

    # ── Target (표준 라인아이템) ──
    target_line_item_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("standard_line_item.code"),
        nullable=False,
        comment="대상 표준 라인아이템 코드",
    )

    # ── 매핑 메타데이터 ──
    confidence: Mapped[MappingConfidence] = mapped_column(
        Enum(MappingConfidence), nullable=False, comment="매핑 신뢰도"
    )
    status: Mapped[MappingStatus] = mapped_column(
        Enum(MappingStatus),
        nullable=False,
        default=MappingStatus.PROPOSED,
        comment="매핑 상태",
    )
    match_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="매칭 점수 (0-100)"
    )
    algorithm: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="사용된 알고리즘 (exact/keyword/fuzzy/manual)",
    )

    # ── 영향 금액 ──
    affected_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="해당 계정 TB 잔액"
    )

    # ── 승인 워크플로 ──
    approved_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="승인자"
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="승인 시각"
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="거부 사유"
    )

    # ── Timestamps ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_account_mapping_deal", "deal_id"),
        Index("ix_account_mapping_source", "source_account_code"),
        Index("ix_account_mapping_status", "status"),
        Index(
            "uq_account_mapping_deal_source",
            "deal_id",
            "source_account_code",
            unique=True,
        ),
    )
