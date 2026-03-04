"""IM 체크리스트 ORM 모델.

VDR 기반 IM 생성 워크플로우에서 자동 추출된 데이터 필드를
사용자가 검수/확정하는 체크리스트를 저장한다.

Document 1:1 관계 — 문서당 하나의 체크리스트.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.db.base import Base

if TYPE_CHECKING:
    from src.api.db.models.document import Document
    from src.api.db.models.im_checklist_item import IMChecklistItem


class ChecklistStatus(str, enum.Enum):
    """체크리스트 상태."""

    EXTRACTING = "EXTRACTING"  # VDR 문서 파싱 중
    REVIEW = "REVIEW"  # 사용자 검수 대기
    CONFIRMED = "CONFIRMED"  # 사용자 확정 완료
    GENERATING = "GENERATING"  # IM 생성 중
    COMPLETED = "COMPLETED"  # IM 생성 완료
    FAILED = "FAILED"  # 처리 실패


class IMChecklist(Base):
    """IM 체크리스트 모델.

    VDR 문서에서 자동 추출된 데이터 필드 목록을 관리하며,
    사용자가 각 필드를 검수/수정/확정한다.
    """

    __tablename__ = "im_checklists"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
        index=True,
    )

    # VDR 관련
    vdr_document_ids: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )

    # 상태
    status: Mapped[str] = mapped_column(
        String(20),
        default=ChecklistStatus.EXTRACTING.value,
        index=True,
    )

    # 집계
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_items: Mapped[int] = mapped_column(Integer, default=0)
    missing_items: Mapped[int] = mapped_column(Integer, default=0)

    # 파서 원시 출력 (디버깅/감사용)
    raw_extraction: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )

    # Celery 태스크 추적
    extraction_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    generation_task_id: Mapped[str | None] = mapped_column(
        String(255),
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
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    document: Mapped[Document] = relationship(
        back_populates="checklist",
    )
    items: Mapped[list[IMChecklistItem]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="IMChecklistItem.sort_order",
    )

    # document_id는 unique=True, status는 index=True로 이미 인덱스 생성됨
    __table_args__: tuple = ()

    def update_counts(self) -> None:
        """아이템 상태별 집계를 갱신한다."""
        self.total_items = len(self.items)
        self.confirmed_items = sum(
            1 for item in self.items if item.status in ("CONFIRMED", "MODIFIED")
        )
        self.missing_items = sum(1 for item in self.items if item.status == "MISSING")
