"""RFI V2 질의 원장 모델 — insert-only 스레드 이력 기반."""

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import RFICategoryV2, RFIItemStatusV2, RFIPriority


class RFIItemV2(Base, TimestampMixin):
    """RFI 질의 원장 — 카테고리별 질문 + 상태 추적 + 낙관적 락."""

    __tablename__ = "rfi_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 표시용 번호 (RFI-2026-001)
    item_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # 질문
    category: Mapped[RFICategoryV2] = mapped_column(Enum(RFICategoryV2), nullable=False)
    priority: Mapped[RFIPriority] = mapped_column(Enum(RFIPriority), nullable=False, default=RFIPriority.MEDIUM)
    target_doc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    current_status: Mapped[RFIItemStatusV2] = mapped_column(
        Enum(RFIItemStatusV2), nullable=False, default=RFIItemStatusV2.OPEN
    )

    # 자문사 전용 메모 (TARGET에 비노출)
    internal_memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 보고서 목차 매핑 (QoE, NWC, Contingent_Liabilities 등)
    report_section_tag: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 담당 & 기한
    assignee_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 낙관적 락 (Optimistic Lock) — 동시성 제어
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 소프트 삭제
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 관계
    threads: Mapped[list["RFIThread"]] = relationship(  # noqa: F821
        "RFIThread",
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RFIThread.round_num",
    )
    attachments: Mapped[list["RFIAttachment"]] = relationship(  # noqa: F821
        "RFIAttachment",
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="RFIAttachment.item_id",
    )
