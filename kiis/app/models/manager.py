"""심사역 이동 추적 모델

Key Man(심사역)의 소속 변경 이벤트를 감지하고 이력을 관리한다.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MovementType(StrEnum):
    """이동 유형"""

    TRANSFER = "transfer"  # 이직 (소속 변경)
    RESIGNATION = "resignation"  # 사임/퇴사
    APPOINTMENT = "appointment"  # 신규 임명


# 이동 유형 표시명 매핑
MOVEMENT_TYPE_DISPLAY_NAMES = {
    MovementType.TRANSFER: "이직",
    MovementType.RESIGNATION: "사임",
    MovementType.APPOINTMENT: "신규 임명",
}


class ManagerMovement(TimestampMixin, Base):
    """심사역 이동 이력 모델"""

    __tablename__ = "manager_movements"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 심사역 정보
    manager_name: Mapped[str] = mapped_column(String(100), index=True, comment="심사역 이름")

    # 이전 소속
    from_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="이전 소속 기업 ID",
    )
    from_company_name: Mapped[str | None] = mapped_column(String(300), comment="이전 소속 기업명")
    from_fund_id: Mapped[int | None] = mapped_column(
        ForeignKey("funds.id", ondelete="SET NULL"),
        comment="이전 소속 펀드 ID",
    )

    # 새 소속
    to_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        comment="새 소속 기업 ID",
    )
    to_company_name: Mapped[str | None] = mapped_column(String(300), comment="새 소속 기업명")
    to_fund_id: Mapped[int | None] = mapped_column(
        ForeignKey("funds.id", ondelete="SET NULL"),
        comment="새 소속 펀드 ID",
    )

    # 이동 상세
    movement_type: Mapped[str] = mapped_column(
        String(20), index=True, comment="이동 유형 (transfer/resignation/appointment)"
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="감지 일시")
    source: Mapped[str | None] = mapped_column(String(50), comment="감지 출처 (kofia/news)")
    notes: Mapped[str | None] = mapped_column(Text, comment="비고")

    # 관계
    from_company: Mapped["Company | None"] = relationship(  # noqa: F821
        foreign_keys=[from_company_id]
    )
    to_company: Mapped["Company | None"] = relationship(  # noqa: F821
        foreign_keys=[to_company_id]
    )
