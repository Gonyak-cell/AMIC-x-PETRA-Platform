"""GP 로고 크롤링 관리 API"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.logo_service import LogoService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/crawl", summary="GP 로고 일괄 수집")
async def crawl_logos(
    force: bool = Query(False, description="기존 로고가 있어도 재수집"),
    limit: int = Query(50, ge=1, le=200, description="최대 수집 건수"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """hm_url이 있는 기업의 로고를 일괄 크롤링한다."""
    service = LogoService(db)
    try:
        return await service.crawl_batch(force=force, limit=limit)
    finally:
        await service.close()


@router.post("/crawl/{company_id}", summary="단일 기업 로고 수집")
async def crawl_single_logo(
    company_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool | None]:
    """특정 기업의 로고를 크롤링한다."""
    service = LogoService(db)
    try:
        success = await service.crawl_single(company_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"로고 수집 실패: company_id={company_id} (홈페이지 없음 또는 로고 미발견)",
            )

        from sqlalchemy import select

        from app.models.company import Company

        result = await db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        return {
            "success": True,
            "company_name": company.corp_name if company else None,
            "logo_url": company.logo_url if company else None,
            "logo_source": company.logo_source if company else None,
        }
    finally:
        await service.close()
