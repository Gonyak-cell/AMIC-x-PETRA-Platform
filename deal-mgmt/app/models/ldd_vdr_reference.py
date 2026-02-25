"""LDD 체크리스트 항목 ↔ VDR 소스 문서 링크 모델."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LddVdrReference(Base, TimestampMixin):
    """LDD 보고서의 개별 항목과 근거 VDR 문서를 연결하는 N:M 링크 테이블.

    각 체크리스트 항목(item_id)이 어느 VDR 문서를 근거로 분석되었는지 추적한다.
    AI 분석 시 자동 생성되고, 사용자가 수동으로 추가/삭제할 수도 있다.
    """

    __tablename__ = "ldd_vdr_references"
    __table_args__ = (
        UniqueConstraint("ldd_report_id", "item_id", "vdr_document_id", name="uq_ldd_vdr_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ldd_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ldd_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[str] = mapped_column(String(30), nullable=False)  # DDRL 항목 ID (CORP-01 등)
    vdr_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vdr_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    section_type: Mapped[str] = mapped_column(String(30), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_snippet: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
