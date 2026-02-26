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
    search: str | None = Query(None, description="검색어"),
    search_type: str = Query("name", description="검색 유형: name|stock_code|jurir_no|bizr_no"),
    corp_cls: str | None = Query(None, description="법인구분 (쉼표 구분 복수 가능: Y,K)"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """통합 기업 목록을 조회한다.

    검색 유형별 검색(기업명/종목코드/법인등록번호/사업자번호)과
    법인구분 필터(복수 선택 지원)를 적용할 수 있다.
    """
    query = select(Company)

    if search:
        search = search.strip()
        if search_type == "stock_code":
            query = query.where(Company.stock_code == search)
        elif search_type == "jurir_no":
            query = query.where(Company.jurir_no == search)
        elif search_type == "bizr_no":
            query = query.where(Company.bizr_no == search)
        else:
            # name (기본값): 기업명 부분 일치 검색
            query = query.where(Company.corp_name.contains(search))

    if corp_cls:
        cls_list = [c.strip() for c in corp_cls.split(",") if c.strip()]
        if len(cls_list) == 1:
            query = query.where(Company.corp_cls == cls_list[0])
        elif len(cls_list) > 1:
            query = query.where(Company.corp_cls.in_(cls_list))

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
