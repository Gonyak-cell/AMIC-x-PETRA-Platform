import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(TimestampMixin, Base):
    """사용자 모델"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="사용자명")
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, comment="이메일")
    hashed_password: Mapped[str] = mapped_column(String(255), comment="해시된 비밀번호")
    role: Mapped[str] = mapped_column(String(20), default=UserRole.VIEWER, comment="역할 (admin/analyst/viewer)")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성 상태")
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="마지막 로그인"
    )
