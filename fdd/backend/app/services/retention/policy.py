"""데이터 보존/파기 정책 — FDD-1703.

데이터 유형별 보존 기간 관리 + 만료 항목 파기.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog


class DataType(str, Enum):
    """보존 정책 대상 데이터 유형."""

    DEAL_COMPLETE = "deal_complete"
    DEAL_DRAFT = "deal_draft"
    AUDIT_LOG = "audit_log"
    UPLOAD_FILE = "upload_file"
    SESSION = "session"
    REPORT = "report"


# 보존 기간 정의
RETENTION_PERIODS: dict[DataType, timedelta] = {
    DataType.DEAL_COMPLETE: timedelta(days=365 * 7),
    DataType.DEAL_DRAFT: timedelta(days=90),
    DataType.AUDIT_LOG: timedelta(days=365 * 7),
    DataType.UPLOAD_FILE: timedelta(days=365),
    DataType.SESSION: timedelta(days=30),
    DataType.REPORT: timedelta(days=365 * 2),
}


@dataclass
class PurgeResult:
    """파기 결과."""

    data_type: DataType
    purged_count: int
    dry_run: bool
    cutoff_date: datetime
    errors: list[str] = field(default_factory=list)


class RetentionPolicy:
    """데이터 보존/파기 정책 관리."""

    def __init__(self, db: Session):
        self.db = db

    def get_expiry_date(self, data_type: DataType, from_date: datetime | None = None) -> datetime:
        """데이터 유형에 대한 만료일을 계산한다."""
        base = from_date or datetime.utcnow()
        period = RETENTION_PERIODS[data_type]
        return base + period

    def get_retention_period(self, data_type: DataType) -> timedelta:
        """데이터 유형의 보존 기간을 반환한다."""
        return RETENTION_PERIODS[data_type]

    def count_expired_audit_logs(self, cutoff: datetime | None = None) -> int:
        """만료된 감사 로그 수를 조회한다."""
        if cutoff is None:
            cutoff = datetime.utcnow()
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.expires_at.isnot(None), AuditLog.expires_at <= cutoff)
        )
        return self.db.scalar(stmt) or 0

    def purge_expired_audit_logs(
        self, *, dry_run: bool = True, cutoff: datetime | None = None
    ) -> PurgeResult:
        """만료된 감사 로그를 파기한다."""
        if cutoff is None:
            cutoff = datetime.utcnow()

        count = self.count_expired_audit_logs(cutoff)

        if not dry_run and count > 0:
            # 파기 전 로그 기록
            purge_log = AuditLog(
                entity_type="audit_log",
                entity_id=uuid.uuid4(),
                action=AuditAction.PURGE,
                actor="system:retention",
                new_value={"purged_count": count, "cutoff": cutoff.isoformat()},
            )
            self.db.add(purge_log)

            stmt = delete(AuditLog).where(
                AuditLog.expires_at.isnot(None), AuditLog.expires_at <= cutoff
            )
            self.db.execute(stmt)
            self.db.commit()

        return PurgeResult(
            data_type=DataType.AUDIT_LOG,
            purged_count=count,
            dry_run=dry_run,
            cutoff_date=cutoff,
        )

    def set_audit_log_expiry(
        self, *, data_type: DataType = DataType.AUDIT_LOG
    ) -> int:
        """expires_at이 NULL인 감사 로그에 만료일을 설정한다."""
        period = RETENTION_PERIODS[data_type]
        stmt = (
            update(AuditLog)
            .where(AuditLog.expires_at.is_(None))
            .values(expires_at=AuditLog.created_at + period)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount  # type: ignore[return-value]

    def get_retention_summary(self) -> dict[str, object]:
        """보존 정책 요약 정보를 반환한다."""
        total = self.db.scalar(select(func.count()).select_from(AuditLog)) or 0
        with_expiry = (
            self.db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.expires_at.isnot(None))
            )
            or 0
        )
        expired = self.count_expired_audit_logs()

        return {
            "policies": {
                dt.value: {
                    "retention_days": RETENTION_PERIODS[dt].days,
                    "description": dt.value,
                }
                for dt in DataType
            },
            "audit_logs": {
                "total": total,
                "with_expiry": with_expiry,
                "without_expiry": total - with_expiry,
                "expired": expired,
            },
        }
