"""Company 관련 엔드포인트 (T-I17).

> 마지막 수정: 2026-02-10 23:30:00

POST /api/v1/companies — DART 데이터 수집 시작
GET  /api/v1/companies/{corp_code} — 캐시된 데이터 조회
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.schemas.companies import CompanyRequest, CompanyResponse
from src.api.services.company_service import CompanyService

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=202,
    summary="기업 데이터 수집 시작",
    description="DART API에서 기업 데이터를 수집하고 캐시한다 (비동기).",
)
async def fetch_company_data(
    request: CompanyRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    """DART에서 기업 데이터를 수집하는 Celery 태스크를 시작한다."""
    service = CompanyService(session)
    company = await service.fetch_company(request.corp_code)
    return CompanyResponse.model_validate(company)


@router.get(
    "/{corp_code}",
    response_model=CompanyResponse,
    summary="기업 데이터 조회",
    description="캐시된 기업 데이터를 반환한다. 캐시 만료 시 자동 재수집.",
)
async def get_company_data(
    corp_code: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    """캐시된 기업 데이터를 조회한다."""
    service = CompanyService(session)
    company = await service.get_company(corp_code)
    return CompanyResponse.model_validate(company)
