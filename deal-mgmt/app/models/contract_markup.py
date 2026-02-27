"""계약 마크업 버전 관리 — 파일 업로드 지원."""

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ContractMarkup(Base, TimestampMixin):
    """계약 마크업 버전 — 협상 단계 계약서 버전 관리."""

    __tablename__ = "contract_markups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meeting_logs.id", ondelete="SET NULL"),
        nullable=True,
    )

    version_label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "v3 - 매수인 마크업"
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_party: Mapped[str | None] = mapped_column(String(200), nullable=True)
    markup_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "draft"/"1st"/"2nd"/"final"

    # 파일
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 변경 요약
    changes_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_changes: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )  # 구조화된 변경 목록

    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
