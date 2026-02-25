"""User ORM 모델 (T-I04).

> 마지막 수정: 2026-02-10 16:29:08

사용자 계정 및 인증 정보를 저장한다.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.db.base import Base

if TYPE_CHECKING:
    from src.api.db.models.api_key import APIKey
    from src.api.db.models.document import Document


class User(Base):
    """사용자 모델."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="USER",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    documents: Mapped[list[Document]] = relationship(
        back_populates="owner",
        lazy="selectin",
    )
    api_keys: Mapped[list[APIKey]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
