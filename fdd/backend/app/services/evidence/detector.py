"""Evidence 누락 탐지기 — FDD-402.

산출물(target)에 대한 근거(evidence)가 누락되었는지 검사한다.
- 매핑(account_mapping)마다 최소 1개 이상의 TB/GL evidence 필요
- Tie-out 결과에 대해서는 evidence 없어도 허용 (자동 생성 결과)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.account_mapping import AccountMapping, MappingStatus
from app.models.evidence import EvidenceLink


@dataclass
class MissingEvidence:
    """누락된 근거 항목."""

    target_type: str
    target_id: uuid.UUID
    target_label: str
    reason: str


@dataclass
class DetectionResult:
    """누락 탐지 결과."""

    deal_id: uuid.UUID
    total_targets_checked: int = 0
    missing_count: int = 0
    missing: list[MissingEvidence] = field(default_factory=list)

    @property
    def coverage_percentage(self) -> float:
        if self.total_targets_checked == 0:
            return 100.0
        covered = self.total_targets_checked - self.missing_count
        return round(covered / self.total_targets_checked * 100, 2)


def detect_missing_evidence(
    db: Session,
    deal_id: uuid.UUID,
    *,
    check_approved_only: bool = True,
) -> DetectionResult:
    """APPROVED 매핑에 대한 evidence 누락을 탐지한다.

    Args:
        db: DB 세션.
        deal_id: 딜 ID.
        check_approved_only: True면 APPROVED 매핑만 검사.

    Returns:
        DetectionResult with missing evidence details.
    """
    result = DetectionResult(deal_id=deal_id)

    # 검사 대상 매핑 조회
    stmt = select(AccountMapping).where(AccountMapping.deal_id == deal_id)
    if check_approved_only:
        stmt = stmt.where(AccountMapping.status == MappingStatus.APPROVED)
    mappings = list(db.scalars(stmt))

    result.total_targets_checked = len(mappings)

    if not mappings:
        return result

    # 매핑 ID → evidence 개수 맵 일괄 조회
    mapping_ids = [m.id for m in mappings]
    evidence_counts_stmt = (
        select(EvidenceLink.target_id, func.count(EvidenceLink.id))
        .where(
            EvidenceLink.deal_id == deal_id,
            EvidenceLink.target_type == "account_mapping",
            EvidenceLink.target_id.in_(mapping_ids),
        )
        .group_by(EvidenceLink.target_id)
    )
    evidence_counts: dict[uuid.UUID, int] = dict(db.execute(evidence_counts_stmt).all())

    for mapping in mappings:
        count = evidence_counts.get(mapping.id, 0)
        if count == 0:
            result.missing_count += 1
            result.missing.append(
                MissingEvidence(
                    target_type="account_mapping",
                    target_id=mapping.id,
                    target_label=f"{mapping.source_account_code} → {mapping.target_line_item_code}",
                    reason="No evidence link found for approved mapping",
                )
            )

    return result
