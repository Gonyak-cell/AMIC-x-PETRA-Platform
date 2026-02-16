"""Export service — Phase 5."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.export_record import ExportModule, ExportRecord, ExportStatus


def list_exports(
    db: Session,
    *,
    module: ExportModule | None = None,
    status: ExportStatus | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[ExportRecord], int]:
    """Return paginated export records with total count."""
    stmt = select(ExportRecord)
    count_stmt = select(func.count()).select_from(ExportRecord)

    if module is not None:
        stmt = stmt.where(ExportRecord.module == module)
        count_stmt = count_stmt.where(ExportRecord.module == module)
    if status is not None:
        stmt = stmt.where(ExportRecord.status == status)
        count_stmt = count_stmt.where(ExportRecord.status == status)

    total = db.scalar(count_stmt) or 0

    skip = (page - 1) * size
    stmt = stmt.order_by(ExportRecord.created_at.desc()).offset(skip).limit(size)
    items = list(db.scalars(stmt).all())

    return items, total


def get_export_by_id(db: Session, export_id: uuid.UUID) -> ExportRecord | None:
    """Get a single export record by ID."""
    return db.get(ExportRecord, export_id)


def get_exports_by_ids(
    db: Session, export_ids: list[uuid.UUID]
) -> list[ExportRecord]:
    """Get multiple export records by IDs."""
    stmt = select(ExportRecord).where(ExportRecord.id.in_(export_ids))
    return list(db.scalars(stmt).all())


def delete_export(db: Session, export_id: uuid.UUID) -> bool:
    """Delete an export record. Returns True if deleted, False if not found."""
    record = db.get(ExportRecord, export_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True
