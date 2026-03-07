"""범용 첨부파일 모델 — 모든 탭의 외부 자료 업로드 지원."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Attachment(Base, TimestampMixin):
    """거래 내 엔티티에 첨부된 외부 파일.

    entity_type + entity_id 조합으로 특정 레코드에 바인딩하거나,
    entity_id 없이 탭 레벨(entity_type만)에 첨부할 수 있다.
    """

    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── 다형성 참조 ───────────────────────────────────────
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # ── 파일 메타데이터 ───────────────────────────────────
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/octet-stream")

    # ── VDR 연동 ─────────────────────────────────────────
    vdr_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vdr_documents.id", ondelete="SET NULL"), nullable=True
    )

    # ── 메타 ──────────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
