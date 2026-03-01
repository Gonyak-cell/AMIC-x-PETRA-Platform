"""플랫폼 전역 설정 API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims, require_role
from app.models.enums import AuditAction
from app.models.platform_settings import PlatformSettings
from app.schemas.platform_settings import (
    PlatformSettingsResponse,
    PlatformSettingsUpdate,
)
from app.services import audit_service
from app.services.platform_settings_service import get_or_create_settings

router = APIRouter(tags=["Admin Settings"])

_ALLOWED_UPDATE_FIELDS = frozenset({"site_name", "contact_email", "legal_terms", "privacy_policy", "table_style"})
_SETTINGS_AUDIT_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "platform-settings-singleton")


@router.get("/settings", response_model=PlatformSettingsResponse)
async def get_platform_settings(
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
) -> PlatformSettings:
    """현재 플랫폼 설정 조회."""
    return await get_or_create_settings(db)


@router.put("/admin/settings", response_model=PlatformSettingsResponse)
async def update_platform_settings(
    body: PlatformSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(require_role("ADMIN")),
) -> PlatformSettings:
    """플랫폼 설정 업데이트 (ADMIN 전용)."""
    settings = await get_or_create_settings(db)

    update_data = {
        k: v for k, v in body.model_dump(exclude_unset=True).items() if k in _ALLOWED_UPDATE_FIELDS and v is not None
    }
    old_values = {f: getattr(settings, f) for f in update_data}
    for field, value in update_data.items():
        setattr(settings, field, value)

    if update_data:
        await audit_service.record(
            db,
            entity_type="PlatformSettings",
            entity_id=_SETTINGS_AUDIT_UUID,
            action=AuditAction.UPDATE,
            actor_email=_claims.email,
            old_value=old_values,
            new_value=update_data,
        )

    await db.commit()
    await db.refresh(settings)
    return settings
