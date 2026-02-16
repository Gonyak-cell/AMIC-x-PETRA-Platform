"""평판 스코어링 모델

KIIS 평판 지수 = (트렌드 점수 × 0.3) + (뉴스 평판 × 0.4) + (성과 지표 × 0.3)
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReputationScore(TimestampMixin, Base):
    """기업 평판 점수 모델 (company당 1개의 현재 스냅샷)"""

    __tablename__ = "reputation_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        comment="기업 ID",
    )

    # 점수 (0.0 ~ 1.0, news_score는 -1.0 ~ 1.0)
    trend_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"), comment="트렌드 점수 (0.0~1.0)")
    news_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0"), comment="뉴스 평판 점수 (-1.0~1.0)"
    )
    performance_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0"), comment="성과 지표 점수 (0.0~1.0)"
    )
    total_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0"), comment="총합 평판 지수 (0.0~1.0)"
    )

    # 상태 태그
    status_tag: Mapped[str] = mapped_column(String(20), default="stable", comment="상태 태그 (rising/stable/risk)")

    # 산출 시각
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="점수 산출 시각")

    # 메타 정보
    news_count: Mapped[int] = mapped_column(default=0, comment="분석 뉴스 수")
    exit_count: Mapped[int] = mapped_column(default=0, comment="1년 내 엑시트 횟수")

    # 관계
    company: Mapped["Company"] = relationship(back_populates="reputation_score")  # noqa: F821


class ReputationHistory(TimestampMixin, Base):
    """평판 점수 변동 이력 모델 (시계열)"""

    __tablename__ = "reputation_history"
    __table_args__ = (Index("ix_reputation_history_company_recorded", "company_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        comment="기업 ID",
    )

    # 점수
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), comment="해당 시점 총합 평판 지수")
    status_tag: Mapped[str] = mapped_column(String(20), comment="해당 시점 상태 태그")
    trend_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), comment="트렌드 점수")
    news_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), comment="뉴스 점수")
    performance_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), comment="성과 점수")

    # 기록 시각
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, comment="기록 시각")

    # 관계
    company: Mapped["Company"] = relationship()  # noqa: F821
