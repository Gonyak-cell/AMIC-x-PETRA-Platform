"""포트폴리오 생존분석 API 라우터"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.company import Company
from app.schemas.portfolio import (
    PortfolioCompanyItem,
    PortfolioListResponse,
    PortfolioSummaryResponse,
    SurvivalCheckResponse,
    ValuationUpdateRequest,
    ValuationUpdateResponse,
)
from app.services.portfolio_service import PortfolioService

router = APIRouter()


def get_portfolio_service() -> PortfolioService:
    """포트폴리오 서비스 팩토리"""
    return PortfolioService()


@router.get(
    "/by-investor/{corp_code}",
    response_model=PortfolioListResponse,
    summary="투자사별 포트폴리오 목록",
)
async def get_portfolio_by_investor(
    corp_code: str,
    status: str | None = Query(None, description="생존 상태 필터 (active/audit_missing/dissolved/unicorn/unknown)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    db: AsyncSession = Depends(get_db),
    service: PortfolioService = Depends(get_portfolio_service),
):
    """특정 투자사의 포트폴리오 기업 목록을 조회한다."""
    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    items, total = await service.get_portfolio_by_investor(
        db=db,
        corp_code=corp_code,
        status=status,
        page=page,
        size=size,
    )

    return PortfolioListResponse(
        total=total,
        page=page,
        size=size,
        items=[PortfolioCompanyItem.model_validate(item) for item in items],
    )


@router.get(
    "/by-investor/{corp_code}/summary",
    response_model=PortfolioSummaryResponse,
    summary="투자사별 포트폴리오 요약",
)
async def get_portfolio_summary(
    corp_code: str,
    db: AsyncSession = Depends(get_db),
    service: PortfolioService = Depends(get_portfolio_service),
):
    """특정 투자사의 포트폴리오 생존 상태별 요약을 조회한다."""
    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    summary = await service.get_portfolio_summary(db=db, corp_code=corp_code)

    return PortfolioSummaryResponse(**summary)


@router.post(
    "/by-investor/{corp_code}/sync",
    summary="딜 데이터에서 포트폴리오 동기화",
    status_code=200,
)
async def sync_portfolio_from_deals(
    corp_code: str,
    db: AsyncSession = Depends(get_db),
    service: PortfolioService = Depends(get_portfolio_service),
):
    """투자사의 딜 데이터에서 포트폴리오 엔트리를 동기화한다."""
    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    synced_count = await service.sync_from_deals(db=db, investor_corp_code=corp_code)

    return {"synced_count": synced_count}


@router.post(
    "/{portfolio_id}/check-survival",
    response_model=SurvivalCheckResponse,
    summary="포트폴리오 기업 생존 확인",
)
async def check_portfolio_survival(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    service: PortfolioService = Depends(get_portfolio_service),
):
    """포트폴리오 기업의 생존 상태를 DART 공시를 통해 확인한다."""
    # 기존 상태 조회
    from app.models.portfolio import PortfolioCompany

    stmt = select(PortfolioCompany).where(PortfolioCompany.id == portfolio_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if not existing:
        raise HTTPException(status_code=404, detail=f"포트폴리오 엔트리를 찾을 수 없습니다: {portfolio_id}")

    previous_status = existing.survival_status

    portfolio = await service.check_survival(db=db, portfolio_id=portfolio_id)

    if not portfolio:
        raise HTTPException(status_code=404, detail=f"포트폴리오 엔트리를 찾을 수 없습니다: {portfolio_id}")

    return SurvivalCheckResponse(
        portfolio_id=portfolio.id,
        previous_status=previous_status,
        new_status=portfolio.survival_status,
        checked_at=portfolio.checked_at,
    )


@router.put(
    "/{portfolio_id}/valuation",
    response_model=ValuationUpdateResponse,
    summary="포트폴리오 기업가치 업데이트",
)
async def update_valuation(
    portfolio_id: int,
    request: ValuationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    service: PortfolioService = Depends(get_portfolio_service),
):
    """포트폴리오 기업의 추정 기업가치를 업데이트한다.

    기업가치 1조원 이상 시 자동으로 유니콘 상태로 전환된다.
    """
    portfolio, is_newly_unicorn = await service.update_valuation(
        db=db,
        portfolio_id=portfolio_id,
        valuation=request.estimated_valuation,
    )

    if not portfolio:
        raise HTTPException(status_code=404, detail=f"포트폴리오 엔트리를 찾을 수 없습니다: {portfolio_id}")

    return ValuationUpdateResponse(
        portfolio_id=portfolio.id,
        target_company_name=portfolio.target_company_name,
        estimated_valuation=portfolio.estimated_valuation,
        is_unicorn=portfolio.is_unicorn,
        is_newly_unicorn=is_newly_unicorn,
        survival_status=portfolio.survival_status,
    )
