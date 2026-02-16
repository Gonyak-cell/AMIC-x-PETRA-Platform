"""이슈 로그 모델 — Sprint 6 (FDD-504).

이상치 탐지, 데이터 품질, 매핑 문제 등을 추적하는 이슈 로그.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.db_types import JsonbColumn


# ── Enums ────────────────────────────────────────────────


class IssueSeverity(str, enum.Enum):
    """이슈 심각도 — risk_score 기반.

    - LOW: 30-50
    - MEDIUM: 50-70
    - HIGH: 70-85
    - CRITICAL: 85+
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueStatus(str, enum.Enum):
    """이슈 상태."""

    OPEN = "OPEN"  # 열림 (초기 상태)
    UNDER_REVIEW = "UNDER_REVIEW"  # 검토 중
    RESOLVED = "RESOLVED"  # 해결됨
    FALSE_POSITIVE = "FALSE_POSITIVE"  # 오탐
    ACKNOWLEDGED = "ACKNOWLEDGED"  # 인지함 (조치 불필요)


class IssueCategory(str, enum.Enum):
    """이슈 카테고리."""

    ANOMALY = "ANOMALY"  # 이상치 탐지
    DATA_QUALITY = "DATA_QUALITY"  # 데이터 품질 문제
    MAPPING = "MAPPING"  # 매핑 문제
    CALCULATION = "CALCULATION"  # 계산 오류
    AI_SUGGESTION = "AI_SUGGESTION"  # AI 제안


# ── Helper Functions ──────────────────────────────────────


def severity_from_risk_score(risk_score: Decimal) -> IssueSeverity:
    """risk_score를 IssueSeverity로 변환.

    - 85+: CRITICAL
    - 70-84: HIGH
    - 50-69: MEDIUM
    - 30-49: LOW (기본)
    """
    if risk_score >= Decimal("85"):
        return IssueSeverity.CRITICAL
    if risk_score >= Decimal("70"):
        return IssueSeverity.HIGH
    if risk_score >= Decimal("50"):
        return IssueSeverity.MEDIUM
    return IssueSeverity.LOW


# ── Models ───────────────────────────────────────────────


class Issue(Base):
    """이슈 로그 모델.

    이상치 탐지 결과, 데이터 품질 문제, 매핑 이슈 등을
    Deal 단위로 추적.
    """

    __tablename__ = "issue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal_snapshot.id", ondelete="SET NULL"),
        nullable=True,
        comment="관련 스냅샷 (있는 경우)",
    )

    # ── Classification ──
    category: Mapped[IssueCategory] = mapped_column(
        Enum(IssueCategory), nullable=False, comment="이슈 카테고리"
    )
    severity: Mapped[IssueSeverity] = mapped_column(
        Enum(IssueSeverity), nullable=False, comment="심각도"
    )
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus),
        nullable=False,
        default=IssueStatus.OPEN,
        comment="상태",
    )

    # ── Content ──
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="이슈 제목"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="이슈 상세 설명"
    )
    risk_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="리스크 점수 (0-100)"
    )

    # ── Source Reference ──
    source_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="소스 타입 (GL, TB, etc.)"
    )
    source_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="소스 ID (entry_id 등)"
    )
    source_detail: Mapped[dict[str, Any] | None] = mapped_column(
        JsonbColumn, nullable=True, comment="소스 상세 정보 (JSON)"
    )

    # ── Detection Metadata ──
    detection_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="탐지 방법: zscore, benford, timing, keyword, manual 등",
    )
    detection_factors: Mapped[list[dict] | None] = mapped_column(
        JsonbColumn, nullable=True, comment="탐지 요인 상세 (JSON)"
    )
    engine_version: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="엔진 버전"
    )

    # ── Resolution ──
    resolution_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="해결 메모"
    )
    resolved_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="해결자"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="해결 시각"
    )

    # ── Timestamps ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──
    deal: Mapped["Deal"] = relationship(back_populates="issues")  # noqa: F821

    __table_args__ = (
        Index("ix_issue_deal", "deal_id"),
        Index("ix_issue_severity", "severity"),
        Index("ix_issue_status", "status"),
        Index("ix_issue_category", "category"),
        Index("ix_issue_deal_status", "deal_id", "status"),
    )
