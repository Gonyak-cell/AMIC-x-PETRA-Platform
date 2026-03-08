"""문서 원장 — 범용 문서 버전 관리 시스템(VCS) 최상위 엔티티."""

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import DocumentType


class DocumentMaster(Base, TimestampMixin):
    """문서 원장 — 계약서/NDA/RFI 등의 논리적 묶음 단위로 고유 ID를 발급한다."""

    __tablename__ = "document_masters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False, index=True)
    doc_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 기존 모델 연결 (옵션 FK — 병행 운영)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    nda_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ndas.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # relationships
    revisions: Mapped[list["DocumentRevision"]] = relationship(  # noqa: F821
        "DocumentRevision",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DocumentRevision.revision_number",
    )
