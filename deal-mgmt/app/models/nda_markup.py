"""NDA 마크업 버전 관리 — 파일 업로드 + 일자별 버전 추적."""

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NdaMarkup(Base, TimestampMixin):
    """NDA 마크업 버전 — 협상 단계 NDA 문서 버전 관리."""

    __tablename__ = "nda_markups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nda_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ndas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 버전 관리
    version_label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "v2 - 매수인 수정본"
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_date: Mapped[str] = mapped_column(String(10), nullable=False)  # "YYYY-MM-DD"
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

    # Redline 메타데이터
    redline_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    redline_issues_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("nda_markups.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
