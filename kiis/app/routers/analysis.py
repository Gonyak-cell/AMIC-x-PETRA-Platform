"""평판 분석 API 라우터"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PaginationParams, paginate
from app.models.company import Company
from app.models.reputation import ReputationScore
from app.schemas.analysis import (
    ReputationCalculateRequest,
    ReputationHistoryItem,
    ReputationHistoryResponse,
    ReputationListItem,
    ReputationListResponse,
    ReputationScoreResponse,
    ReputationThemeItem,
    ReputationThemeResponse,
)
from app.services.reputation_service import ReputationService
from app.services.reputation_themes import THEME_DISPLAY_NAMES, THEME_SENTIMENT

router = APIRouter()


def get_reputation_service() -> ReputationService:
    """평판 서비스 팩토리"""
    return ReputationService()


@router.get(
    "/reputation",
    response_model=ReputationListResponse,
    summary="평판 목록 조회",
)
async def list_reputations(
    status_tag: str | None = Query(None, description="상태 태그 필터 (rising/stable/risk)"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """기업 평판 목록을 조회한다."""
    query = select(
        ReputationScore.company_id,
        Company.corp_code,
        Company.corp_name,
        ReputationScore.total_score,
        ReputationScore.status_tag,
        ReputationScore.scored_at,
    ).join(Company, ReputationScore.company_id == Company.id)

    if status_tag:
        query = query.where(ReputationScore.status_tag == status_tag)

    query = query.order_by(ReputationScore.total_score.desc())
    rows, total = await paginate(db, query, pagination)

    items = [
        ReputationListItem(
            company_id=row.company_id,
            corp_code=row.corp_code,
            corp_name=row.corp_name,
            total_score=row.total_score,
            status_tag=row.status_tag,
            scored_at=row.scored_at,
        )
        for row in rows
    ]

    return ReputationListResponse(total=total, page=pagination.page, size=pagination.size, items=items)


@router.get(
    "/reputation/{corp_code}",
    response_model=ReputationScoreResponse,
    summary="기업 평판 조회",
)
async def get_reputation(
    corp_code: str,
    db: AsyncSession = Depends(get_db),
    service: ReputationService = Depends(get_reputation_service),
):
    """특정 기업의 현재 평판 지수를 조회한다."""
    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    reputation = await service.get_reputation(db, corp_code, company_id=company.id)

    if not reputation:
        raise HTTPException(
            status_code=404,
            detail=f"평판 정보가 없습니다. POST /reputation/{corp_code}/calculate로 계산하세요.",
        )

    return ReputationScoreResponse(
        company_id=reputation.company_id,
        corp_code=company.corp_code,
        corp_name=company.corp_name,
        trend_score=reputation.trend_score,
        news_score=reputation.news_score,
        performance_score=reputation.performance_score,
        total_score=reputation.total_score,
        status_tag=reputation.status_tag,
        scored_at=reputation.scored_at,
        news_count=reputation.news_count,
        exit_count=reputation.exit_count,
    )


@router.get(
    "/reputation/{corp_code}/history",
    response_model=ReputationHistoryResponse,
    summary="기업 평판 이력 조회",
)
async def get_reputation_history(
    corp_code: str,
    limit: int = Query(30, ge=1, le=365, description="조회 건수"),
    db: AsyncSession = Depends(get_db),
    service: ReputationService = Depends(get_reputation_service),
):
    """특정 기업의 평판 지수 시계열 이력을 조회한다."""
    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    history = await service.get_reputation_history(db, corp_code, limit, company_id=company.id)

    items = [
        ReputationHistoryItem(
            total_score=h.total_score,
            status_tag=h.status_tag,
            trend_score=h.trend_score,
            news_score=h.news_score,
            performance_score=h.performance_score,
            recorded_at=h.recorded_at,
        )
        for h in history
    ]

    return ReputationHistoryResponse(
        corp_code=company.corp_code,
        corp_name=company.corp_name,
        total=len(items),
        items=items,
    )


@router.post(
    "/reputation/{corp_code}/calculate",
    response_model=ReputationScoreResponse,
    summary="기업 평판 계산",
)
async def calculate_reputation(
    corp_code: str,
    request: ReputationCalculateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    service: ReputationService = Depends(get_reputation_service),
):
    """특정 기업의 평판 지수를 (재)계산한다."""
    if request is None:
        request = ReputationCalculateRequest()

    # 기업 조회
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    reputation = await service.calculate_reputation(
        db=db,
        corp_code=corp_code,
        months=request.months,
        save_history=request.save_history,
    )

    if not reputation:
        raise HTTPException(status_code=500, detail="평판 계산에 실패했습니다.")

    return ReputationScoreResponse(
        company_id=reputation.company_id,
        corp_code=company.corp_code,
        corp_name=company.corp_name,
        trend_score=reputation.trend_score,
        news_score=reputation.news_score,
        performance_score=reputation.performance_score,
        total_score=reputation.total_score,
        status_tag=reputation.status_tag,
        scored_at=reputation.scored_at,
        news_count=reputation.news_count,
        exit_count=reputation.exit_count,
    )


@router.get(
    "/reputation/{corp_code}/themes",
    response_model=ReputationThemeResponse,
    summary="테마별 평판 분석",
)
async def get_reputation_themes(
    corp_code: str,
    months: int = Query(6, ge=1, le=24, description="분석 기간 (개월)"),
    db: AsyncSession = Depends(get_db),
    service: ReputationService = Depends(get_reputation_service),
):
    """특정 기업의 테마별 뉴스 분포를 분석한다.

    reputation_themes 감성 사전 기반으로 각 뉴스 기사를 exit_ipo, mna, financial_risk 등
    테마 코드로 분류하여 건수를 반환한다. 리스크 부재 테마는 별도 알림 문구로 표시된다.
    """
    company_stmt = select(Company).where(Company.corp_code == corp_code)
    company_result = await db.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")

    classified = await service.classify_by_theme(db, company.id, months=months)
    theme_counts: dict[str, int] = classified["theme_counts"]

    themes = [
        ReputationThemeItem(
            theme_code=code,
            display_name=THEME_DISPLAY_NAMES.get(code, code),
            sentiment=THEME_SENTIMENT.get(code, "neutral"),
            count=theme_counts.get(code, 0),
        )
        for code in THEME_DISPLAY_NAMES
    ]

    return ReputationThemeResponse(
        corp_code=company.corp_code,
        corp_name=company.corp_name,
        period_months=months,
        themes=themes,
        risk_absence_notices=classified["risk_absence_notices"],
        total_articles=classified["total_articles"],
    )
