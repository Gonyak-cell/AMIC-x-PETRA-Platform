"""Entity (법인) Pydantic 스키마."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.entity import EntityType


class EntityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    entity_type: EntityType = EntityType.TARGET
    parent_entity_id: uuid.UUID | None = None
    functional_currency: str = Field(default="KRW", max_length=10)
    ownership_pct: Decimal | None = Field(
        default=Decimal("100.0000"), ge=Decimal("0"), le=Decimal("100")
    )


class EntityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    functional_currency: str | None = Field(default=None, max_length=10)
    ownership_pct: Decimal | None = None
    is_active: bool | None = None


class EntityRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    parent_entity_id: uuid.UUID | None
    entity_type: EntityType
    name: str
    code: str
    functional_currency: str
    is_active: bool
    ownership_pct: Decimal | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
