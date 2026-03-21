"""VDR 문서 텍스트 추출 결과 캐시 모델."""

import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class VdrTextCache(Base, TimestampMixin):
    """VDR 문서에서 추출한 텍스트를 캐싱하는 테이블.

    sha256_hash로 원본 파일 변경 여부를 감지하여 캐시 무효화한다.
    동일 문서는 재추출 없이 캐시된 결과를 반환한다.
    """

    __tablename__ = "vdr_text_caches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vdr_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("vdr_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, docx, xlsx
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    tables_json: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    chunks_json: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    ddrl_sections: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
