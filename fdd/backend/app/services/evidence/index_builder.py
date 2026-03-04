"""Evidence Index Builder — FDD-1401.

보고서 내 모든 Evidence를 인덱싱하고 참조 위치를 추적한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceLink, SourceType


@dataclass
class EvidenceReference:
    """Evidence 참조 위치."""

    section_id: str
    block_id: str
    row_index: int | None = None
    page_number: int | None = None


@dataclass
class EvidenceIndexEntry:
    """Evidence 인덱스 항목."""

    evidence_id: str
    source_type: str
    source_id: str
    source_detail: dict | None
    target_type: str
    target_id: str
    referenced_in: list[EvidenceReference] = field(default_factory=list)


@dataclass
class EvidenceIndex:
    """Evidence 인덱스 전체."""

    deal_id: str
    total_count: int
    by_source_type: dict[str, int]
    by_target_type: dict[str, int]
    entries: list[EvidenceIndexEntry]


def build_evidence_index(
    db: Session,
    deal_id: uuid.UUID,
    *,
    snapshot_id: uuid.UUID | None = None,
) -> EvidenceIndex:
    """Deal의 모든 EvidenceLink를 인덱싱한다."""
    stmt = select(EvidenceLink).where(EvidenceLink.deal_id == deal_id)
    if snapshot_id is not None:
        stmt = stmt.where(EvidenceLink.snapshot_id == snapshot_id)
    stmt = stmt.order_by(EvidenceLink.created_at.asc())

    links = list(db.scalars(stmt).all())

    by_source_type: dict[str, int] = {}
    by_target_type: dict[str, int] = {}
    entries: list[EvidenceIndexEntry] = []

    for link in links:
        src = (
            link.source_type.value
            if isinstance(link.source_type, SourceType)
            else str(link.source_type)
        )
        by_source_type[src] = by_source_type.get(src, 0) + 1
        by_target_type[link.target_type] = by_target_type.get(link.target_type, 0) + 1

        entries.append(
            EvidenceIndexEntry(
                evidence_id=str(link.id),
                source_type=src,
                source_id=link.source_id,
                source_detail=link.source_detail,
                target_type=link.target_type,
                target_id=str(link.target_id),
            )
        )

    return EvidenceIndex(
        deal_id=str(deal_id),
        total_count=len(entries),
        by_source_type=by_source_type,
        by_target_type=by_target_type,
        entries=entries,
    )


def map_evidence_to_report_sections(
    index: EvidenceIndex,
    section_mapping: dict[str, str],
) -> EvidenceIndex:
    """Report IR 섹션에 Evidence 참조를 매핑한다.

    section_mapping: target_type → section_id 매핑.
    예: {"qoe_adjustment": "section-qoe", "nwc_item": "section-nwc"}
    """
    for entry in index.entries:
        section_id = section_mapping.get(entry.target_type)
        if section_id:
            entry.referenced_in.append(
                EvidenceReference(
                    section_id=section_id,
                    block_id=f"block-{entry.target_type}-{entry.target_id[:8]}",
                )
            )
    return index


def get_evidence_coverage_stats(
    db: Session,
    deal_id: uuid.UUID,
) -> dict[str, object]:
    """Evidence 커버리지 통계를 반환한다."""
    total_stmt = (
        select(func.count())
        .select_from(EvidenceLink)
        .where(EvidenceLink.deal_id == deal_id)
    )
    total = db.scalar(total_stmt) or 0

    by_type_stmt = (
        select(EvidenceLink.target_type, func.count())
        .where(EvidenceLink.deal_id == deal_id)
        .group_by(EvidenceLink.target_type)
    )
    by_type = {row[0]: row[1] for row in db.execute(by_type_stmt).all()}

    by_source_stmt = (
        select(EvidenceLink.source_type, func.count())
        .where(EvidenceLink.deal_id == deal_id)
        .group_by(EvidenceLink.source_type)
    )
    by_source = {
        (row[0].value if isinstance(row[0], SourceType) else str(row[0])): row[1]
        for row in db.execute(by_source_stmt).all()
    }

    return {
        "deal_id": str(deal_id),
        "total_evidence_links": total,
        "by_target_type": by_type,
        "by_source_type": by_source,
    }
