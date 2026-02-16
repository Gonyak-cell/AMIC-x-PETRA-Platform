"""제재 경중 분류 모델

DART 제재 내역을 경중별(주의/경고/위험)로 분류하여 저장한다.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SanctionSeverity(StrEnum):
    """제재 경중 등급"""

    CAUTION = "caution"  # 주의 (과태료, 행정착오 등)
    WARNING = "warning"  # 경고 (위반, 미공시 등)
    CRITICAL = "critical"  # 위험 (횡령, 배임, 사기 등)


class SanctionCategory(StrEnum):
    """제재 유형 분류"""

    ADMINISTRATIVE = "administrative"  # 행정 처분
    DISCLOSURE = "disclosure"  # 공시 관련
    FRAUD = "fraud"  # 사기/부정
    EMBEZZLEMENT = "embezzlement"  # 횡령/배임
    OTHER = "other"  # 기타


class ClassifiedSanction(TimestampMixin, Base):
    """분류된 제재 내역 모델"""

    __tablename__ = "classified_sanctions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 기업 연결
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        comment="기업 ID",
    )
    corp_code: Mapped[str] = mapped_column(String(20), index=True, comment="DART 고유번호")

    # 원본 제재 정보
    sanctions_type: Mapped[str] = mapped_column(String(200), comment="제재유형")
    sanctions_detail: Mapped[str | None] = mapped_column(Text, comment="제재내용")
    sanctions_date: Mapped[str | None] = mapped_column(String(20), comment="제재일자")
    sanctions_agency: Mapped[str | None] = mapped_column(String(100), comment="제재기관")

    # 분류 결과
    severity: Mapped[str] = mapped_column(String(20), index=True, comment="경중 등급 (caution/warning/critical)")
    severity_reason: Mapped[str | None] = mapped_column(Text, comment="경중 분류 근거")
    category: Mapped[str | None] = mapped_column(
        String(50), comment="제재 유형 분류 (administrative/disclosure/fraud/embezzlement/other)"
    )
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="분류 시각")

    # 관계
    company: Mapped["Company"] = relationship()  # noqa: F821
