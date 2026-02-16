from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyItem, CompanyListItem, CompanyListResponse

router = APIRouter()


@router.get("/", response_model=CompanyListResponse, summary="기업 목록 조회")
async def list_companies(
    search: str | None = Query(None, description="기업명 검색어"),
    corp_cls: str | None = Query(None, description="법인구분 (Y/K/N/E)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
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

    # 전체 건수
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 페이지네이션
    query = query.order_by(Company.corp_name).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    companies = result.scalars().all()

    items = [CompanyListItem.model_validate(c) for c in companies]
    return CompanyListResponse(total=total, page=page, size=size, items=items)


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
