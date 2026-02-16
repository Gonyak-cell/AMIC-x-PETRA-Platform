import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.db_types import JsonbColumn


class SourceType(str, enum.Enum):
    """근거 출처 유형."""

    FILE = "FILE"  # 업로드 파일 전체
    TB = "TB"  # Trial Balance 행
    GL = "GL"  # General Ledger 전표
    PDF = "PDF"  # PDF 페이지/좌표


class EvidenceLink(Base):
    """근거추적 다형 연관(polymorphic association) 모델.

    target_type/target_id → 산출물(QoE 조정행, NWC 항목, Debt 항목, Claim 등)
    source_type/source_id/source_detail → 원본 데이터 위치
    """

    __tablename__ = "evidence_link"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Target (산출물 쪽) ────────────────────────────────
    target_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="산출물 유형: qoe_adjustment, nwc_item, debt_item, claim 등",
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="산출물 레코드 PK"
    )

    # ── Source (원본 쪽) ──────────────────────────────────
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType), nullable=False, comment="원본 유형: FILE, TB, GL, PDF"
    )
    source_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="원본 식별자 (파일 UUID, 전표번호 등)"
    )
    source_detail: Mapped[dict | None] = mapped_column(
        JsonbColumn,
        nullable=True,
        comment="세부 위치: {sheet, page, row, line, cell, coordinates, ...}",
    )

    # ── Traceability ──────────────────────────────────────
    transaction_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="GL 전표 참조 ID"
    )
    filter_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="근거 도출에 사용된 필터 해시"
    )
    engine_version: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="근거 생성 엔진 버전"
    )

    # ── Relations ─────────────────────────────────────────
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deal.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal_snapshot.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Timestamps ────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Indexes ───────────────────────────────────────────
    __table_args__ = (
        Index("ix_evidence_link_target", "target_type", "target_id"),
        Index("ix_evidence_link_source", "source_type", "source_id"),
        Index("ix_evidence_link_deal", "deal_id"),
        Index("ix_evidence_link_snapshot", "snapshot_id"),
    )
