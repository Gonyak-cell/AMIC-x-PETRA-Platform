"""VDR Overview 라우터 — 전체 거래의 VDR 현황 조회."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.schemas.vdr import VdrOverviewItem
from app.services import vdr_service

router = APIRouter(
    prefix="/vdr",
    tags=["VDR"],
)


@router.get("/overview", response_model=list[VdrOverviewItem])
async def get_vdr_overview(
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """모든 거래의 VDR 현황을 조회한다 (ADMIN/MANAGER만 접근 가능)."""
    if claims.role not in ("ADMIN", "MANAGER"):
        raise HTTPException(status_code=403, detail="이 기능에 접근할 권한이 없습니다")
    return await vdr_service.get_all_vdr_overviews(db)
