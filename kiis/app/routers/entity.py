from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.company import Company
from app.schemas.entity import (
    AliasCreateRequest,
    AliasItem,
    AliasListResponse,
    EntityResolveRequest,
    EntityResolveResponse,
)
from app.utils.entity_resolver import EntityResolver

router = APIRouter()
resolver = EntityResolver()


@router.post("/resolve", response_model=EntityResolveResponse, summary="기업명 Entity Resolution")
async def resolve_entity(
    request: EntityResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    """기업명(약칭, 정식명칭 등)을 정규 기업에 매핑한다.

    1) 별칭 사전 정확 매칭
    2) Company.corp_name 정규화 매칭
    3) 유사도 기반 후보 추출
    """
    result = await resolver.resolve(
        db=db,
        name=request.name,
        threshold=request.threshold,
        max_candidates=request.max_candidates,
    )
    return EntityResolveResponse(**result)


@router.post("/aliases", response_model=AliasItem, summary="별칭 등록", status_code=201)
async def create_alias(
    request: AliasCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """기업 별칭을 수동으로 등록한다."""
    # corp_code로 기업 조회
    stmt = select(Company).where(Company.corp_code == request.corp_code)
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {request.corp_code}")

    alias = await resolver.add_alias(
        db=db,
        alias_name=request.alias_name,
        company_id=company.id,
        is_manual=True,
    )

    return AliasItem(
        id=alias.id,
        alias_name=alias.alias_name,
        company_id=alias.company_id,
        is_manual=alias.is_manual,
        corp_code=company.corp_code,
        corp_name=company.corp_name,
    )


@router.get("/aliases", response_model=AliasListResponse, summary="별칭 목록 조회")
async def list_aliases(
    corp_code: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """등록된 별칭 목록을 조회한다."""
    company_id = None
    if corp_code:
        stmt = select(Company).where(Company.corp_code == corp_code)
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail=f"기업을 찾을 수 없습니다: {corp_code}")
        company_id = company.id

    aliases = await resolver.get_aliases(db=db, company_id=company_id)

    items = []
    for alias in aliases:
        company = alias.company
        items.append(
            AliasItem(
                id=alias.id,
                alias_name=alias.alias_name,
                company_id=alias.company_id,
                is_manual=alias.is_manual,
                corp_code=company.corp_code if company else None,
                corp_name=company.corp_name if company else None,
            )
        )

    return AliasListResponse(total=len(items), items=items)


@router.delete("/aliases/{alias_id}", summary="별칭 삭제", status_code=204)
async def delete_alias(
    alias_id: int,
    db: AsyncSession = Depends(get_db),
):
    """등록된 별칭을 삭제한다."""
    deleted = await resolver.delete_alias(db=db, alias_id=alias_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"별칭을 찾을 수 없습니다: {alias_id}")
