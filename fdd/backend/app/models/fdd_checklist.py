"""FDD 체크리스트 모델.

VDR 기반 자동 분석 후 사용자 검수/수정을 위한 체크리스트 시스템.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.db_types import JsonbColumn


# ── Enums ────────────────────────────────────────────────────────────────


class ChecklistStatus(str, enum.Enum):
    """체크리스트 전체 상태."""

    GENERATING = "GENERATING"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEWED = "REVIEWED"
    FINALIZED = "FINALIZED"


class ChecklistCategory(str, enum.Enum):
    """체크리스트 항목 카테고리 (표준 FDD 리뷰 영역)."""

    # QoE 관련
    REVENUE_RECOGNITION = "REVENUE_RECOGNITION"
    COGS_CLASSIFICATION = "COGS_CLASSIFICATION"
    SGA_ANALYSIS = "SGA_ANALYSIS"
    NON_RECURRING_ITEMS = "NON_RECURRING_ITEMS"
    RELATED_PARTY_TRANSACTIONS = "RELATED_PARTY_TRANSACTIONS"
    EBITDA_ADJUSTMENTS = "EBITDA_ADJUSTMENTS"
    # NWC 관련
    NWC_CLASSIFICATION = "NWC_CLASSIFICATION"
    AR_AGING = "AR_AGING"
    AP_AGING = "AP_AGING"
    INVENTORY_ANALYSIS = "INVENTORY_ANALYSIS"
    NWC_SEASONALITY = "NWC_SEASONALITY"
    # Net Debt 관련
    DEBT_SCHEDULE = "DEBT_SCHEDULE"
    DEBT_LIKE_ITEMS = "DEBT_LIKE_ITEMS"
    CASH_LIKE_ITEMS = "CASH_LIKE_ITEMS"
    LEASE_OBLIGATIONS = "LEASE_OBLIGATIONS"
    # 기타
    TAX_REVIEW = "TAX_REVIEW"
    CONTINGENT_LIABILITIES = "CONTINGENT_LIABILITIES"
    OFF_BALANCE_SHEET = "OFF_BALANCE_SHEET"


class ChecklistItemStatus(str, enum.Enum):
    """개별 체크리스트 항목 상태."""

    AUTO_GENERATED = "AUTO_GENERATED"
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    FLAGGED = "FLAGGED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ChecklistSeverity(str, enum.Enum):
    """체크리스트 항목 심각도."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# ── Models ───────────────────────────────────────────────────────────────


class FddChecklist(Base):
    """Deal별 FDD 체크리스트.

    자동 분석 후 생성되며, 사용자 리뷰 → Finalize 후 보고서에 반영.
    """

    __tablename__ = "fdd_checklist"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ChecklistStatus] = mapped_column(
        Enum(ChecklistStatus), nullable=False, default=ChecklistStatus.GENERATING
    )

    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finalized_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    items: Mapped[list["FddChecklistItem"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="FddChecklistItem.order_index",
    )

    __table_args__ = (
        Index("ix_fdd_checklist_deal", "deal_id"),
        Index("ix_fdd_checklist_status", "status"),
    )


class FddChecklistItem(Base):
    """개별 FDD 체크리스트 항목.

    자동 분석 결과(auto_finding, auto_amount)와
    사용자 수정(user_correction, user_amount)을 분리 저장.
    """

    __tablename__ = "fdd_checklist_item"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fdd_checklist.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[ChecklistCategory] = mapped_column(
        Enum(ChecklistCategory), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # 자동 분석 결과
    auto_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )

    # 사용자 수정
    user_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )

    # 상태 및 메타데이터
    status: Mapped[ChecklistItemStatus] = mapped_column(
        Enum(ChecklistItemStatus),
        nullable=False,
        default=ChecklistItemStatus.AUTO_GENERATED,
    )
    severity: Mapped[ChecklistSeverity | None] = mapped_column(
        Enum(ChecklistSeverity), nullable=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JsonbColumn, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    checklist: Mapped["FddChecklist"] = relationship(back_populates="items")
    vdr_links: Mapped[list["ChecklistItemVdrLink"]] = relationship(
        back_populates="checklist_item",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_fdd_checklist_item_checklist", "checklist_id"),
        Index("ix_fdd_checklist_item_category", "category"),
    )


class ChecklistItemVdrLink(Base):
    """체크리스트 항목 ↔ VDR 문서 연결.

    각 체크리스트 항목이 어떤 VDR 파일에서 도출되었는지 추적.
    """

    __tablename__ = "checklist_item_vdr_link"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    checklist_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fdd_checklist_item.id", ondelete="CASCADE"),
        nullable=False,
    )
    upload_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("upload_file.id", ondelete="SET NULL"),
        nullable=True,
    )
    vdr_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vdr_folder.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_link.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_detail: Mapped[dict | None] = mapped_column(
        JsonbColumn,
        nullable=True,
        comment="세부 위치: {sheet, row, cell, page, ...}",
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    checklist_item: Mapped["FddChecklistItem"] = relationship(
        back_populates="vdr_links"
    )

    __table_args__ = (
        Index("ix_checklist_vdr_item", "checklist_item_id"),
        Index("ix_checklist_vdr_upload", "upload_file_id"),
    )
