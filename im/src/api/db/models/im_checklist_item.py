"""IM 체크리스트 아이템 ORM 모델.

VDR에서 자동 추출된 개별 데이터 필드를 나타낸다.
체크리스트당 50~100개 아이템이 생성되며, 사용자가 각 필드를
검수(확인/수정/누락 표시)한다.

IMChecklist N:1 관계 — 하나의 체크리스트에 여러 아이템.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.db.base import Base

if TYPE_CHECKING:
    from src.api.db.models.im_checklist import IMChecklist


class ChecklistItemStatus(str, enum.Enum):
    """체크리스트 아이템 상태."""

    EXTRACTED = "EXTRACTED"  # 자동 추출 완료
    CONFIRMED = "CONFIRMED"  # 사용자 확인 (변경 없이 승인)
    MODIFIED = "MODIFIED"  # 사용자가 값을 수정함
    MISSING = "MISSING"  # 추출 실패 — 사용자 직접 입력 필요
    NOT_APPLICABLE = "NOT_APPLICABLE"  # 해당 없음


class ChecklistItemCategory(str, enum.Enum):
    """체크리스트 아이템 카테고리."""

    FINANCIAL = "FINANCIAL"
    COMPANY = "COMPANY"
    MARKET = "MARKET"
    DEAL = "DEAL"
    MANAGEMENT = "MANAGEMENT"
    SHAREHOLDERS = "SHAREHOLDERS"


class ChecklistItemFieldType(str, enum.Enum):
    """체크리스트 아이템 필드 타입."""

    TEXT = "text"
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    DATE = "date"
    LIST = "list"


class IMChecklistItem(Base):
    """IM 체크리스트 개별 아이템 모델.

    VDR 문서에서 자동 추출된 단일 데이터 필드를 나타낸다.
    사용자가 추출값을 검수하고, 필요 시 수정하여 확정한다.
    """

    __tablename__ = "im_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("im_checklists.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 분류
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    field_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    field_label: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    field_type: Mapped[str] = mapped_column(
        String(20),
        default=ChecklistItemFieldType.TEXT.value,
    )

    # 값
    extracted_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    confirmed_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # VDR 소스 추적
    source_vdr_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )
    source_vdr_doc_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    source_location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # 상태
    status: Mapped[str] = mapped_column(
        String(20),
        default=ChecklistItemStatus.EXTRACTED.value,
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # 정렬/메타
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    fiscal_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    checklist: Mapped[IMChecklist] = relationship(
        back_populates="items",
    )

    __table_args__ = (
        UniqueConstraint(
            "checklist_id", "field_key", "fiscal_year",
            name="uq_im_checklist_items_checklist_field_year",
        ),
        Index("ix_im_checklist_items_checklist_category", "checklist_id", "category"),
    )

    @property
    def effective_value(self) -> str | None:
        """확정값이 있으면 확정값, 없으면 추출값을 반환한다."""
        return self.confirmed_value if self.confirmed_value is not None else self.extracted_value
