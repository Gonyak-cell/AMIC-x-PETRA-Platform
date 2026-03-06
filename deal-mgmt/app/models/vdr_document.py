"""VDR 문서 모델 — M&A 실사 자료실 파일 메타데이터 관리."""

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import VdrClassificationStatus, VdrDocumentStatus


class VdrDocument(Base, TimestampMixin):
    """VDR에 업로드된 문서 메타데이터.

    실제 파일은 서버 디스크(또는 향후 S3)에 저장하고,
    이 테이블은 메타데이터만 관리한다.
    """

    __tablename__ = "vdr_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    folder_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("vdr_folders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── 파일 메타데이터 ───────────────────────────────
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/octet-stream")
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── 상태 ──────────────────────────────────────────
    status: Mapped[VdrDocumentStatus] = mapped_column(
        Enum(VdrDocumentStatus), nullable=False, default=VdrDocumentStatus.ACTIVE
    )

    # ── 자동 분류 ─────────────────────────────────────
    classification_status: Mapped[VdrClassificationStatus | None] = mapped_column(
        Enum(VdrClassificationStatus), nullable=True, default=None
    )
    classification_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manual_review_needed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    # ── 설명 ──────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 업로더 ────────────────────────────────────────
    uploaded_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
