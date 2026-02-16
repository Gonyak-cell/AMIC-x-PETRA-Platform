"""딜 소싱 API 라우터"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.company import Company
from app.schemas.deal import (
    DealExtractRequest,
    DealItem,
    DealListResponse,
    SectorAggregation,
    SectorAggregationResponse,
    StageAggregation,
    StageAggregationResponse,
    TrendResponse,
    YearlyTrend,
)
from app.services.deal_service import DealService

router = APIRouter()


def get_deal_service() -> DealService:
    """딜 서비스 팩토리"""
    return DealService()


@router.get(
    "/by-company/{corp_code}",
    response_model=DealListResponse,
    summary="운용사별 딜 목록",
)
async def get_deals_by_company(
    corp_code: str,
    years: int = Query(5, ge=1, le=10, description="조회 기간 (년)"),
    sector: str | None = Query(None, max_length=50, description="섹터 필터"),
    stage: str | None = Query(None, max_length=50, description="단계 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
    service: DealService = Depends(get_deal_service),
):
    """특정 운용사의 최근 N년 딜 목록을 조회한다."""
    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    deals, total = await service.get_deals_by_company(
        db=db,
        corp_code=corp_code,
        years=years,
        sector=sector,
        stage=stage,
        page=page,
        size=size,
    )

    items = [
        DealItem(
            id=deal.id,
            company_id=deal.company_id,
            investor_name=company.corp_name,
            target_company=deal.target_company,
            target_company_id=deal.target_company_id,
            amount=deal.amount,
            amount_display=deal.amount_display,
            round_stage=deal.round_stage,
            sector=deal.sector,
            deal_date=deal.deal_date,
            deal_year=deal.deal_year,
            source_url=deal.source_url,
            source_type=deal.source_type,
            is_lead_investor=deal.is_lead_investor,
        )
        for deal in deals
    ]

    return DealListResponse(total=total, page=page, size=size, items=items)


@router.get(
    "/by-sector",
    response_model=SectorAggregationResponse,
    summary="섹터별 딜 집계",
)
async def get_deals_by_sector(
    corp_code: str | None = Query(None, max_length=20, description="운용사 필터"),
    year: int | None = Query(None, description="연도 필터"),
    years: int | None = Query(None, ge=1, le=10, description="최근 N년 조회"),
    db: AsyncSession = Depends(get_db),
    service: DealService = Depends(get_deal_service),
):
    """섹터별 딜 집계를 조회한다."""
    min_year = datetime.now().year - years + 1 if years and not year else None
    aggregations = await service.aggregate_by_sector(db, corp_code, year, min_year)

    total_deals = sum(a["deal_count"] for a in aggregations)

    items = [
        SectorAggregation(
            sector=a["sector"],
            sector_name=a["sector_name"],
            deal_count=a["deal_count"],
            total_amount=a["total_amount"],
        )
        for a in aggregations
    ]

    return SectorAggregationResponse(total_deals=total_deals, items=items)


@router.get(
    "/by-stage",
    response_model=StageAggregationResponse,
    summary="투자 단계별 딜 집계",
)
async def get_deals_by_stage(
    corp_code: str | None = Query(None, max_length=20, description="운용사 필터"),
    year: int | None = Query(None, description="연도 필터"),
    years: int | None = Query(None, ge=1, le=10, description="최근 N년 조회"),
    db: AsyncSession = Depends(get_db),
    service: DealService = Depends(get_deal_service),
):
    """투자 단계별 딜 집계를 조회한다."""
    min_year = datetime.now().year - years + 1 if years and not year else None
    aggregations = await service.aggregate_by_stage(db, corp_code, year, min_year)

    total_deals = sum(a["deal_count"] for a in aggregations)

    items = [
        StageAggregation(
            stage=a["stage"],
            stage_name=a["stage_name"],
            deal_count=a["deal_count"],
            total_amount=a["total_amount"],
        )
        for a in aggregations
    ]

    return StageAggregationResponse(total_deals=total_deals, items=items)


@router.get(
    "/trends",
    response_model=TrendResponse,
    summary="연도별 투자 트렌드",
)
async def get_deal_trends(
    corp_code: str | None = Query(None, max_length=20, description="운용사 필터"),
    years: int = Query(5, ge=1, le=10, description="조회 기간 (년)"),
    db: AsyncSession = Depends(get_db),
    service: DealService = Depends(get_deal_service),
):
    """연도별 투자 트렌드를 조회한다."""
    # 기업명 조회 (필터가 있는 경우)
    corp_name = None
    if corp_code:
        company_stmt = select(Company).where(Company.corp_code == corp_code)
        company_result = await db.execute(company_stmt)
        company = company_result.scalar_one_or_none()
        if company:
            corp_name = company.corp_name

    trends = await service.get_yearly_trends(db, corp_code, years)

    items = [
        YearlyTrend(
            year=t["year"],
            deal_count=t["deal_count"],
            total_amount=t["total_amount"],
        )
        for t in trends
    ]

    return TrendResponse(corp_code=corp_code, corp_name=corp_name, items=items)


@router.post(
    "/extract",
    response_model=DealItem,
    summary="뉴스에서 딜 추출",
    status_code=201,
)
async def extract_deal_from_news(
    request: DealExtractRequest,
    db: AsyncSession = Depends(get_db),
    service: DealService = Depends(get_deal_service),
):
    """뉴스 기사에서 딜 정보를 추출하여 저장한다."""
    deal = await service.extract_deal_from_news(
        db=db,
        news_article_id=request.news_article_id,
        investor_corp_code=request.investor_corp_code,
    )

    if not deal:
        raise HTTPException(
            status_code=422,
            detail="뉴스에서 투자 정보를 추출할 수 없습니다 (금액 정보 없음)",
        )

    await db.commit()

    # 투자사명 조회
    investor_name = None
    if deal.company_id:
        company_stmt = select(Company).where(Company.id == deal.company_id)
        company_result = await db.execute(company_stmt)
        company = company_result.scalar_one_or_none()
        if company:
            investor_name = company.corp_name

    return DealItem(
        id=deal.id,
        company_id=deal.company_id,
        investor_name=investor_name,
        target_company=deal.target_company,
        target_company_id=deal.target_company_id,
        amount=deal.amount,
        amount_display=deal.amount_display,
        round_stage=deal.round_stage,
        sector=deal.sector,
        deal_date=deal.deal_date,
        deal_year=deal.deal_year,
        source_url=deal.source_url,
        source_type=deal.source_type,
        is_lead_investor=deal.is_lead_investor,
    )
