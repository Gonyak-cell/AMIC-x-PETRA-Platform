"""문서 리비전 — 동일 문서의 물리적 파일 버전을 SHA-256 해시로 관리한다."""

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import UploadSource


class DocumentRevision(Base, TimestampMixin):
    """문서 리비전 — 파일 업로드마다 새 리비전을 생성하고 해시로 중복을 차단한다."""

    __tablename__ = "document_revisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("document_masters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # 파일 메타데이터
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 업로드 메타데이터
    uploaded_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upload_source: Mapped[UploadSource] = mapped_column(Enum(UploadSource), nullable=False, default=UploadSource.MANUAL)
    changes_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 리비전 체인
    prev_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 기존 모델 역참조 (어떤 ContractMarkup/NdaMarkup에서 연동되었는지)
    source_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # relationships
    document: Mapped["DocumentMaster"] = relationship(  # noqa: F821
        "DocumentMaster", back_populates="revisions"
    )
