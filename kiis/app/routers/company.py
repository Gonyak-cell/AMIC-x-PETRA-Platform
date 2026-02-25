from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginationParams, paginate
from app.models.company import Company
from app.schemas.company import CompanyItem, CompanyListItem, CompanyListResponse

router = APIRouter()


@router.get("", response_model=CompanyListResponse, summary="기업 목록 조회")
async def list_companies(
    search: str | None = Query(None, description="기업명 검색어"),
    corp_cls: str | None = Query(None, description="법인구분 (Y/K/N/E)"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """통합 기업 목록을 조회한다.

    기업명 검색, 법인구분 필터를 적용할 수 있다.
    """
    query = select(Company)

    if search:
        query = query.where(Company.corp_name.contains(search))
    if corp_cls:
        query = query.where(Company.corp_cls == corp_cls)

    query = query.order_by(Company.corp_name)
    rows, total = await paginate(db, query, pagination)

    items = [CompanyListItem.model_validate(row[0]) for row in rows]
    return CompanyListResponse(total=total, page=pagination.page, size=pagination.size, items=items)


@router.get("/{corp_code}", response_model=CompanyItem, summary="기업 상세 조회")
async def get_company(
    corp_code: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 기업의 상세 정보를 조회한다."""

    result = await db.execute(select(Company).where(Company.corp_code == corp_code))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    return CompanyItem.model_validate(company)
