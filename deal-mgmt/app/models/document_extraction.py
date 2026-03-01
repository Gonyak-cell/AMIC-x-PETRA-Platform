"""문서 AI 추출 모델 — VDR 업로드 문서의 자동 분류/데이터 추출 작업 추적."""

import uuid

from sqlalchemy import JSON, Enum, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import DocExtractionCategory, ExtractionStatus


class DocumentExtraction(Base, TimestampMixin):
    """VDR 문서에서 AI로 추출한 데이터 작업 레코드.

    워크플로우: PENDING → CLASSIFYING → EXTRACTING → COMPLETED → CONFIRMED
                                                  ↘ FAILED
    """

    __tablename__ = "document_extractions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vdr_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("vdr_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── 분류 결과 ────────────────────────────────────────
    doc_category: Mapped[DocExtractionCategory | None] = mapped_column(Enum(DocExtractionCategory), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 작업 상태 ────────────────────────────────────────
    status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus),
        nullable=False,
        default=ExtractionStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 추출 결과 (JSON) ────────────────────────────────
    extracted_data: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # ── 매핑 대상 ────────────────────────────────────────
    target_model: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "nda", "bid", "contract", "transaction"
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # ── 비용 추적 ────────────────────────────────────────
    llm_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── 사용자 검토 ──────────────────────────────────────
    reviewed_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
