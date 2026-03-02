"""재무모델 + 체크리스트 모델 — VDR 기반 자동 생성 + 사용자 리뷰 + Ralph Loop."""

import uuid

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    FinancialModelStatus,
    FinancialModelType,
    FMChecklistCategory,
    FMChecklistItemStatus,
    FMChecklistSeverity,
    FMChecklistStatus,
)

# ── FinancialModel ────────────────────────────────────────────────────────


class FinancialModel(Base, TimestampMixin):
    """거래에 귀속되는 재무모델 — DCF / LBO / COMPS / PROJECTION / FULL.

    VDR 재무 자료에서 추출한 데이터를 기반으로 체크리스트 → Excel 워크북을 생성한다.
    Ralph Loop 2회 반복으로 품질을 최대화한다.
    """

    __tablename__ = "financial_models"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── 모델 기본 정보 ─────────────────────────────────────────
    model_type: Mapped[FinancialModelType] = mapped_column(Enum(FinancialModelType), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── 상태 ───────────────────────────────────────────────────
    status: Mapped[FinancialModelStatus] = mapped_column(
        Enum(FinancialModelStatus), nullable=False, default=FinancialModelStatus.DRAFT
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 입력 파라미터 (가정값, 시나리오 등) ─────────────────────
    parameters: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    vdr_document_ids: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )  # 소스 VDR 문서 ID 목록

    # ── 생성된 파일 정보 ───────────────────────────────────────
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Ralph Loop 결과 ───────────────────────────────────────
    ralph_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("ralph_sessions.id", ondelete="SET NULL"), nullable=True
    )
    ralph_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 생성자 ─────────────────────────────────────────────────
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Relationships ──────────────────────────────────────────
    checklist: Mapped["FMChecklist | None"] = relationship(
        back_populates="financial_model",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (Index("ix_fm_txn_type_status", "transaction_id", "model_type", "status"),)


# ── FMChecklist ───────────────────────────────────────────────────────────


class FMChecklist(Base):
    """재무모델별 체크리스트.

    VDR 추출 후 생성되며, 사용자 리뷰 → Finalize 후 최종 Excel에 반영.
    FDD의 FddChecklist 패턴을 따른다.
    """

    __tablename__ = "fm_checklists"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    financial_model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("financial_models.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[FMChecklistStatus] = mapped_column(
        Enum(FMChecklistStatus), nullable=False, default=FMChecklistStatus.GENERATING
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────
    financial_model: Mapped["FinancialModel"] = relationship(back_populates="checklist")
    items: Mapped[list["FMChecklistItem"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="FMChecklistItem.order_index",
    )

    __table_args__ = (
        Index("ix_fm_checklist_model", "financial_model_id"),
        Index("ix_fm_checklist_status", "status"),
    )


# ── FMChecklistItem ───────────────────────────────────────────────────────


class FMChecklistItem(Base):
    """개별 재무모델 체크리스트 항목.

    auto_finding + auto_value (자동 추출)와
    user_correction + user_value (사용자 수정)를 분리 저장.
    FDD의 FddChecklistItem 패턴을 따른다.
    """

    __tablename__ = "fm_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("fm_checklists.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[FMChecklistCategory] = mapped_column(Enum(FMChecklistCategory), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── 자동 추출 결과 ─────────────────────────────────────────
    auto_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_value: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 문자열 (비율, 금액, 배수 등)

    # ── 사용자 수정 ────────────────────────────────────────────
    user_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_value: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── 메타 ───────────────────────────────────────────────────
    status: Mapped[FMChecklistItemStatus] = mapped_column(
        Enum(FMChecklistItemStatus), nullable=False, default=FMChecklistItemStatus.AUTO_GENERATED
    )
    severity: Mapped[FMChecklistSeverity | None] = mapped_column(Enum(FMChecklistSeverity), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # %, x, KRW, USD 등
    field_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # text, number, currency, percentage
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0 ~ 1.0

    # ── VDR 소스 추적 ──────────────────────────────────────────
    source_vdr_doc_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source_vdr_doc_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_location: Mapped[str | None] = mapped_column(String(200), nullable=True)  # sheet:row, page:line 등

    # ── 리뷰 기록 ─────────────────────────────────────────────
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────
    checklist: Mapped["FMChecklist"] = relationship(back_populates="items")

    __table_args__ = (
        Index("ix_fm_cl_item_checklist", "checklist_id"),
        Index("ix_fm_cl_item_category", "category"),
    )
