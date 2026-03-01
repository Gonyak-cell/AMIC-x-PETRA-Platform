"""플랫폼 전역 설정 서비스."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_settings import PlatformSettings

logger = logging.getLogger(__name__)


async def get_or_create_settings(db: AsyncSession) -> PlatformSettings:
    """싱글턴 설정 레코드를 조회하거나, 없으면 기본값으로 생성.

    동시 요청으로 인한 PK 충돌 시 재조회로 안전하게 처리한다.
    """
    result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
        try:
            settings = PlatformSettings(id=1)
            db.add(settings)
            await db.flush()
        except IntegrityError:
            logger.info("PlatformSettings 동시 생성 충돌 — 기존 레코드 재조회")
            await db.rollback()
            result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
            settings = result.scalar_one()
    return settings
