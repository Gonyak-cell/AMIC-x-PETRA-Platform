import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.reits import REITs
from app.schemas.reits import REITsAssetListResponse, REITsDetailResponse, REITsListItem, REITsListResponse
from app.services.reits_service import REITsService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_reits_service() -> REITsService:
    return REITsService()


async def _fallback_reits_from_db(
    db: AsyncSession,
    reits_type: str | None,
    status: str | None,
    page: int,
    size: int,
) -> REITsListResponse:
    """외부 API 실패 시 로컬 DB에서 리츠 목록을 반환한다."""
    query = select(REITs)
    count_query = select(func.count(REITs.id))

    if reits_type:
        query = query.where(REITs.reits_type == reits_type)
        count_query = count_query.where(REITs.reits_type == reits_type)
    if status:
        query = query.where(REITs.status == status)
        count_query = count_query.where(REITs.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(query.offset(offset).limit(size))
    reits_list = result.scalars().all()

    items = [
        REITsListItem(
            reits_code=r.reits_code,
            reits_name=r.reits_name,
            reits_type=r.reits_type,
            management_company=r.management_company or "",
            total_assets=r.total_assets,
            real_estate_ratio=r.real_estate_ratio,
            has_asset_ratio_warning=r.has_asset_ratio_warning,
            status=r.status,
            is_listed=r.is_listed,
        )
        for r in reits_list
    ]
    return REITsListResponse(total=total, page=page, size=size, items=items)


@router.get("", response_model=REITsListResponse, summary="리츠 목록 조회")
async def list_reits(
    reits_type: str | None = Query(None, description="리츠 유형 (self_managed/entrusted)"),
    status: str | None = Query(None, description="상태 (authorized/operating/dissolved)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
    service: REITsService = Depends(get_reits_service),
):
    """리츠 목록을 조회한다.

    리츠 유형(자기관리/위탁관리), 상태(인가/영업/해산)로 필터링할 수 있다.
    부동산 자산 비율 70% 미달 리츠는 has_asset_ratio_warning=true로 표시된다.
    외부 API 실패 시 로컬 DB fallback을 사용한다.
    """
    try:
        items, total = await service.search_reits(
            reits_type=reits_type,
            status=status,
            page=page,
            size=size,
        )
        await service.close()
        return REITsListResponse(total=total, page=page, size=size, items=items)
    except Exception:
        logger.warning("REITs external API unavailable, falling back to local DB")
        await service.close()
        return await _fallback_reits_from_db(db, reits_type, status, page, size)


@router.get("/{reits_code}", response_model=REITsDetailResponse, summary="리츠 상세 정보")
async def get_reits(
    reits_code: str,
    service: REITsService = Depends(get_reits_service),
):
    """특정 리츠의 상세 정보를 조회한다. 보유 자산 목록을 포함한다."""
    result = await service.get_reits_detail(reits_code)
    await service.close()
    return result


@router.get("/{reits_code}/assets", response_model=REITsAssetListResponse, summary="리츠 자산 내역")
async def list_reits_assets(
    reits_code: str,
    service: REITsService = Depends(get_reits_service),
):
    """특정 리츠의 보유 자산 내역을 조회한다."""
    assets = await service.get_reits_assets(reits_code)
    await service.close()
    return REITsAssetListResponse(total=len(assets), items=assets)
