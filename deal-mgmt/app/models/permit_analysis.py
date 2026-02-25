"""거래별 인허가 분석 결과."""

import uuid

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import PermitAnalysisStatus


class PermitAnalysis(Base, TimestampMixin):
    """거래별 인허가 분석 — 한 거래에 하나."""

    __tablename__ = "permit_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    status: Mapped[PermitAnalysisStatus] = mapped_column(
        Enum(PermitAnalysisStatus), nullable=False, default=PermitAnalysisStatus.PENDING,
    )
    # 입력 데이터
    business_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    existing_permits: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # 분석 메타
    analysis_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_cost_usd: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    analysis_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
