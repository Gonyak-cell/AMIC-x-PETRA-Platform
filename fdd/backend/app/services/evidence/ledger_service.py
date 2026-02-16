"""Evidence Ledger 서비스 — FDD-401.

EvidenceLink CRUD + 산출물별 근거 조회.
엔진 함수가 반환한 evidence 목록을 일괄 저장하고,
산출물(target) 또는 원본(source) 기준으로 조회한다.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog
from app.models.evidence import EvidenceLink, SourceType
from app.schemas.evidence import EvidenceLinkCreate


def create_evidence_link(
    db: Session,
    deal_id: uuid.UUID,
    link_data: EvidenceLinkCreate,
) -> EvidenceLink:
    """단일 EvidenceLink를 생성한다."""
    link = EvidenceLink(
        deal_id=deal_id,
        target_type=link_data.target_type,
        target_id=link_data.target_id,
        source_type=link_data.source_type,
        source_id=link_data.source_id,
        source_detail=link_data.source_detail,
        transaction_id=link_data.transaction_id,
        filter_hash=link_data.filter_hash,
        engine_version=link_data.engine_version,
        snapshot_id=link_data.snapshot_id,
    )
    db.add(link)
    db.flush()

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="evidence_link",
            entity_id=link.id,
            action=AuditAction.CREATE,
            actor="system",
            new_value={
                "target_type": link.target_type,
                "target_id": str(link.target_id),
                "source_type": link.source_type.value,
                "source_id": link.source_id,
            },
        )
    )
    db.commit()
    return link


def bulk_create_evidence_links(
    db: Session,
    deal_id: uuid.UUID,
    links_data: list[EvidenceLinkCreate],
) -> list[EvidenceLink]:
    """EvidenceLink를 일괄 생성한다 (엔진 함수 결과 저장용)."""
    created: list[EvidenceLink] = []

    for link_data in links_data:
        link = EvidenceLink(
            deal_id=deal_id,
            target_type=link_data.target_type,
            target_id=link_data.target_id,
            source_type=link_data.source_type,
            source_id=link_data.source_id,
            source_detail=link_data.source_detail,
            transaction_id=link_data.transaction_id,
            filter_hash=link_data.filter_hash,
            engine_version=link_data.engine_version,
            snapshot_id=link_data.snapshot_id,
        )
        db.add(link)
        created.append(link)

    db.flush()

    for link in created:
        db.add(
            AuditLog(
                deal_id=deal_id,
                entity_type="evidence_link",
                entity_id=link.id,
                action=AuditAction.CREATE,
                actor="system",
                new_value={
                    "target_type": link.target_type,
                    "source_type": link.source_type.value,
                },
            )
        )

    db.commit()
    return created


def list_evidence_links(
    db: Session,
    deal_id: uuid.UUID,
    *,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    source_type: SourceType | None = None,
    snapshot_id: uuid.UUID | None = None,
) -> list[EvidenceLink]:
    """EvidenceLink를 조건별로 조회한다."""
    stmt = select(EvidenceLink).where(EvidenceLink.deal_id == deal_id)

    if target_type is not None:
        stmt = stmt.where(EvidenceLink.target_type == target_type)
    if target_id is not None:
        stmt = stmt.where(EvidenceLink.target_id == target_id)
    if source_type is not None:
        stmt = stmt.where(EvidenceLink.source_type == source_type)
    if snapshot_id is not None:
        stmt = stmt.where(EvidenceLink.snapshot_id == snapshot_id)

    stmt = stmt.order_by(EvidenceLink.created_at.desc())
    return list(db.scalars(stmt).all())


def get_evidence_link(
    db: Session,
    link_id: uuid.UUID,
) -> EvidenceLink | None:
    """ID로 단일 EvidenceLink를 조회한다."""
    return db.get(EvidenceLink, link_id)


def delete_evidence_link(
    db: Session,
    link: EvidenceLink,
) -> None:
    """EvidenceLink를 삭제한다."""
    db.delete(link)
    db.commit()
