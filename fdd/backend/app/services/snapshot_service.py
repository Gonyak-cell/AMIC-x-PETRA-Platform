"""Deal snapshot creation and management.

A snapshot captures the state of a deal at a point in time:
- Which definition version was used
- What input data was available (input_hash)
- What engine version produced the results
- The hash of all outputs (result_hash) for reproducibility verification
"""

import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit import AuditAction, AuditLog
from app.models.deal import DealDefinition, DealSnapshot, SnapshotStatus
from app.utils.hashing import combine_hashes


def _audit_snapshot(
    db: Session,
    snapshot: DealSnapshot,
    action: AuditAction,
    old_status: str | None = None,
) -> None:
    """Record an audit log entry for snapshot lifecycle events."""
    db.flush()
    old_value = {"status": old_status} if old_status else None
    new_value = {"status": snapshot.status.value}
    log = AuditLog(
        deal_id=snapshot.deal_id,
        entity_type="DealSnapshot",
        entity_id=snapshot.id,
        action=action,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log)


def create_snapshot(
    db: Session,
    deal_id: uuid.UUID,
    definition_version_id: uuid.UUID,
) -> DealSnapshot:
    """Create a new execution snapshot for a deal.

    For MVP, the input_hash is computed from the definition hash only.
    In later sprints, upload file hashes will also be included.
    """
    definition = db.get(DealDefinition, definition_version_id)
    if definition is None:
        raise ValueError(f"Definition {definition_version_id} not found")
    if definition.deal_id != deal_id:
        raise ValueError("Definition does not belong to this deal")

    # For now, input_hash is based on definition hash only.
    # Sprint 2+ will add upload file hashes.
    input_hash = combine_hashes(definition.hash)

    snapshot = DealSnapshot(
        deal_id=deal_id,
        definition_version_id=definition_version_id,
        engine_version=settings.engine_version,
        input_hash=input_hash,
        status=SnapshotStatus.RUNNING,
    )
    db.add(snapshot)
    _audit_snapshot(db, snapshot, AuditAction.CREATE)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def complete_snapshot(
    db: Session,
    snapshot_id: uuid.UUID,
    result_hash: str,
) -> DealSnapshot:
    """Mark a snapshot as successfully completed with its result hash."""
    snapshot = db.get(DealSnapshot, snapshot_id)
    if snapshot is None:
        raise ValueError(f"Snapshot {snapshot_id} not found")

    old_status = snapshot.status.value
    snapshot.result_hash = result_hash
    snapshot.status = SnapshotStatus.SUCCESS
    _audit_snapshot(db, snapshot, AuditAction.UPDATE, old_status=old_status)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def fail_snapshot(
    db: Session,
    snapshot_id: uuid.UUID,
) -> DealSnapshot:
    """Mark a snapshot as failed."""
    snapshot = db.get(DealSnapshot, snapshot_id)
    if snapshot is None:
        raise ValueError(f"Snapshot {snapshot_id} not found")

    old_status = snapshot.status.value
    snapshot.status = SnapshotStatus.FAILED
    _audit_snapshot(db, snapshot, AuditAction.UPDATE, old_status=old_status)
    db.commit()
    db.refresh(snapshot)
    return snapshot
