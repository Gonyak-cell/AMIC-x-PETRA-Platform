"""워치리스트 및 알림 이력 모델"""

import enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AlertType(enum.StrEnum):
    """알림 유형"""

    NEW_DISCLOSURE = "new_disclosure"
    REPUTATION_CHANGE = "reputation_change"
    MANAGER_MOVEMENT = "manager_movement"
    NEW_DEAL = "new_deal"
    SANCTION = "sanction"


class Watchlist(TimestampMixin, Base):
    """관심 기업 워치리스트 모델

    사용자가 관심 등록한 기업 목록을 관리한다.
    동일 사용자-기업 조합은 유니크 제약으로 중복을 방지한다.
    """

    __tablename__ = "watchlists"
    __table_args__ = (UniqueConstraint("user_id", "company_id", name="uq_user_company"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, comment="사용자 ID"
    )
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, comment="기업 ID"
    )
    alert_types: Mapped[str | None] = mapped_column(Text, comment="알림 유형 (JSON array)")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성 상태")


class AlertHistory(TimestampMixin, Base):
    """알림 이력 모델

    사용자에게 발송된 알림 기록을 저장한다.
    """

    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, comment="사용자 ID"
    )
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), index=True, comment="기업 ID"
    )
    alert_type: Mapped[str] = mapped_column(String(50), comment="알림 유형")
    title: Mapped[str] = mapped_column(String(300), comment="알림 제목")
    message: Mapped[str | None] = mapped_column(Text, comment="알림 내용")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True, comment="읽음 여부")
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="참조 레코드 ID")
    reference_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="참조 유형 (disclosure/deal/...)"
    )
