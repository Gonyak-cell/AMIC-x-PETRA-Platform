"""Entity (법인) API — Sprint 16."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.deal import Deal
from app.models.entity import Entity
from app.schemas.entity import EntityCreate, EntityRead, EntityUpdate

router = APIRouter(
    prefix="/deals/{deal_id}/entities",
    tags=["entities"],
)


def _get_deal_or_404(db: Session, deal_id: uuid.UUID) -> Deal:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/", response_model=EntityRead, status_code=201)
def create_entity(
    deal_id: uuid.UUID,
    body: EntityCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """딜에 엔티티(법인)를 추가한다."""
    _get_deal_or_404(db, deal_id)

    # code 중복 확인
    existing = db.scalar(
        select(Entity).where(
            Entity.deal_id == deal_id,
            Entity.code == body.code,
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Entity code '{body.code}' already exists in this deal",
        )

    entity = Entity(
        deal_id=deal_id,
        parent_entity_id=body.parent_entity_id,
        entity_type=body.entity_type,
        name=body.name,
        code=body.code,
        functional_currency=body.functional_currency,
        ownership_pct=body.ownership_pct,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.get("/", response_model=list[EntityRead])
def list_entities(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """딜의 엔티티 목록을 조회한다."""
    _get_deal_or_404(db, deal_id)
    stmt = (
        select(Entity)
        .where(Entity.deal_id == deal_id, Entity.is_active.is_(True))
        .order_by(Entity.entity_type, Entity.code)
    )
    return list(db.scalars(stmt).all())


@router.get("/{entity_id}", response_model=EntityRead)
def get_entity(
    deal_id: uuid.UUID,
    entity_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """엔티티 단건 조회."""
    entity = db.get(Entity, entity_id)
    if entity is None or entity.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.put("/{entity_id}", response_model=EntityRead)
def update_entity(
    deal_id: uuid.UUID,
    entity_id: uuid.UUID,
    body: EntityUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """엔티티 수정."""
    entity = db.get(Entity, entity_id)
    if entity is None or entity.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    _UPDATABLE_FIELDS = {"name", "functional_currency", "ownership_pct", "is_active"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field not in _UPDATABLE_FIELDS:
            continue
        setattr(entity, field, value)

    db.commit()
    db.refresh(entity)
    return entity


@router.delete("/{entity_id}", status_code=204)
def delete_entity(
    deal_id: uuid.UUID,
    entity_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """엔티티 비활성화 (soft delete)."""
    entity = db.get(Entity, entity_id)
    if entity is None or entity.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity.is_active = False
    db.commit()
