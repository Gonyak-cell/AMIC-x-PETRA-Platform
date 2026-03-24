"""마케팅 자료 모델 — TM / DM / IM PPTX 생성 및 배포 관리."""

import uuid

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import MarketingDocStatus, MarketingDocType, MarketingMaterialSourceMode


class MarketingMaterial(Base, TimestampMixin):
    """거래에 귀속되는 마케팅 자료 — TM(Teaser) / DM(Discussion) / IM 3종.

    모든 유형은 memo_generator.py 기반 PPTX로 생성된다.
    """

    __tablename__ = "marketing_materials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── 문서 기본 정보 ─────────────────────────────────────────
    doc_type: Mapped[MarketingDocType] = mapped_column(Enum(MarketingDocType), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)  # TM/DM/IM 코드명 (ALPHA 등)

    # ── 상태 ───────────────────────────────────────────────────
    status: Mapped[MarketingDocStatus] = mapped_column(
        Enum(MarketingDocStatus), nullable=False, default=MarketingDocStatus.DRAFT
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MarketingMaterialSourceMode.GENERATED.value,
    )
    attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("attachments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── 콘텐츠 파라미터 (memo_generator content JSON) ───────────
    parameters: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # ── 생성된 파일 정보 ───────────────────────────────────────
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── 품질 검증 결과 ───────────────────────────────────────
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_issues: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    slide_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── 배포 추적 ──────────────────────────────────────────────
    distributed_to: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )  # ["회사명/이메일", ...]
    distributed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ISO datetime string

    # ── 생성자 ─────────────────────────────────────────────────
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
