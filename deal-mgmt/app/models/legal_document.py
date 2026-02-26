"""법률 문서 모델 — docxtpl 기반 .docx 생성 및 관리."""

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import LegalDocStatus, LegalDocType


class LegalDocument(Base, TimestampMixin):
    """거래에 귀속되는 법률 문서 — SPA/SHA/BTA/SSA/MOU 5종."""

    __tablename__ = "legal_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type: Mapped[LegalDocType] = mapped_column(Enum(LegalDocType), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[LegalDocStatus] = mapped_column(Enum(LegalDocStatus), nullable=False, default=LegalDocStatus.DRAFT)
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    template_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
