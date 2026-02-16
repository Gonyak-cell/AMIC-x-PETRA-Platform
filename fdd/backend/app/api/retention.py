"""Data Retention API — FDD-1703.

보존 정책 조회 + 만료 항목 파기.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.services.retention.policy import RetentionPolicy

router = APIRouter(tags=["retention"])


@router.get("/retention/summary")
def get_retention_summary(
    current_user: CurrentUser = require_permission(Permission.AUDIT_VIEW),
    db: Session = Depends(get_db),
) -> dict:
    """보존 정책 요약 및 현재 상태를 반환한다."""
    policy = RetentionPolicy(db)
    return policy.get_retention_summary()


@router.post("/retention/purge/audit-logs")
def purge_expired_audit_logs(
    dry_run: bool = Query(default=True, description="True이면 실제 삭제하지 않음"),
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
) -> dict:
    """만료된 감사 로그를 파기한다."""
    policy = RetentionPolicy(db)
    result = policy.purge_expired_audit_logs(dry_run=dry_run)
    return {
        "data_type": result.data_type.value,
        "purged_count": result.purged_count,
        "dry_run": result.dry_run,
        "cutoff_date": result.cutoff_date.isoformat(),
    }


@router.post("/retention/set-expiry/audit-logs")
def set_audit_log_expiry(
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
) -> dict:
    """expires_at이 설정되지 않은 감사 로그에 만료일을 설정한다."""
    policy = RetentionPolicy(db)
    updated_count = policy.set_audit_log_expiry()
    return {"updated_count": updated_count}
