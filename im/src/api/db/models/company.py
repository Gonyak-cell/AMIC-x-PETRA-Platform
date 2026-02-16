"""Company ORM 모델 (T-I04).

> 마지막 수정: 2026-02-10 16:29:08

DART에서 수집한 기업 정보를 캐싱하여 저장한다.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.api.db.base import Base


class Company(Base):
    """기업 정보 모델."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    corp_code: Mapped[str] = mapped_column(
        String(8),
        unique=True,
        nullable=False,
        index=True,
    )
    corp_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    corp_name_en: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    stock_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )
    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    homepage_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # 캐시 데이터 (JSONB)
    dart_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
    )
    financial_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
    )
    brand_assets: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
    )

    # Celery 태스크 추적
    fetch_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    fetch_status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
    )

    # 캐시 TTL
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cache_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
