"""Issue 서비스 — Sprint 6.

이상치 탐지 실행, 이슈 CRUD, 요약 통계 등.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.engines.anomaly_engine import (
    ENGINE_VERSION,
    ANOMALY_SCORE_THRESHOLD,
    AnomalyScoreResult,
    analyze_entries_for_anomalies,
)
from app.models.audit import AuditAction, AuditLog
from app.models.issue import (
    Issue,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    severity_from_risk_score,
)
from app.models.journal_entry import JournalEntry
from app.schemas.issue import (
    AnomalyDetectionResponse,
    IssueCreate,
    IssueSummary,
    IssueUpdate,
)

logger = get_logger(__name__)


# ── Internal Helpers ─────────────────────────────────────


def _get_gl_entries(
    db: Session,
    deal_id: uuid.UUID,
) -> list[dict]:
    """GL 전표를 dict 리스트로 조회."""
    entries = list(
        db.scalars(
            select(JournalEntry).where(
                JournalEntry.deal_id == deal_id,
                JournalEntry.source_type == "GL",
            )
        )
    )
    return [
        {
            "entry_id": str(e.id),
            "amount": str(e.amount) if e.amount else "0",
            "category": e.category or "UNCATEGORIZED",
            "entry_date": str(e.entry_date) if e.entry_date else "",
            "description": e.description or "",
            "account_name": e.account_name or "",
            "account_code": e.account_code or "",
        }
        for e in entries
    ]


def _get_total_revenue(db: Session, deal_id: uuid.UUID) -> Decimal:
    """TB에서 매출 합계 조회."""
    result = db.scalar(
        select(func.sum(JournalEntry.balance)).where(
            JournalEntry.deal_id == deal_id,
            JournalEntry.source_type == "TB",
            JournalEntry.category == "REVENUE",
        )
    )
    return abs(Decimal(str(result))) if result else Decimal("0")


# ── Anomaly Detection ────────────────────────────────────


def run_anomaly_detection(
    db: Session,
    deal_id: uuid.UUID,
    snapshot_id: uuid.UUID | None = None,
    threshold: Decimal = ANOMALY_SCORE_THRESHOLD,
) -> AnomalyDetectionResponse:
    """이상치 탐지를 실행하고 Issue를 생성한다.

    Args:
        db: DB 세션
        deal_id: Deal ID
        snapshot_id: 스냅샷 ID (선택)
        threshold: 이상치 판정 임계값 (기본 50)

    Returns:
        탐지 결과 요약
    """
    logger.info(
        f"Starting anomaly detection: deal_id={deal_id}, threshold={threshold}"
    )

    # GL 전표 조회
    gl_entries = _get_gl_entries(db, deal_id)
    if not gl_entries:
        logger.warning(f"No GL entries found for deal: deal_id={deal_id}")
        return AnomalyDetectionResponse(
            detected_count=0,
            issues_created=0,
            engine_version=ENGINE_VERSION,
            threshold_used=threshold,
        )

    # 매출 조회 (금액 비율 분석용)
    revenue = _get_total_revenue(db, deal_id)

    # 엔진 호출
    anomaly_results, evidence_links = analyze_entries_for_anomalies(
        entries=gl_entries,
        revenue=revenue,
    )

    # threshold 이상인 결과만 필터
    filtered = [r for r in anomaly_results if r.risk_score >= threshold]
    detected_count = len(filtered)

    # 기존 OPEN 상태 이슈와 중복 체크
    existing_source_ids = set(
        db.scalars(
            select(Issue.source_id).where(
                Issue.deal_id == deal_id,
                Issue.category == IssueCategory.ANOMALY,
                Issue.status == IssueStatus.OPEN,
            )
        )
    )

    # 이슈 생성
    issues_created = 0
    for result in filtered:
        if result.entry_id in existing_source_ids:
            continue  # 이미 열린 이슈 존재

        issue = Issue(
            deal_id=deal_id,
            snapshot_id=snapshot_id,
            category=IssueCategory.ANOMALY,
            severity=severity_from_risk_score(result.risk_score),
            status=IssueStatus.OPEN,
            title=_generate_issue_title(result),
            description=_generate_issue_description(result),
            risk_score=result.risk_score,
            source_type="GL",
            source_id=result.entry_id,
            source_detail=result.entry_data,
            detection_method="composite",
            detection_factors=[
                {
                    "factor_type": f.factor_type,
                    "score_contribution": str(f.score_contribution),
                    "raw_score": str(f.raw_score),
                    "description": f.description,
                }
                for f in result.risk_factors
            ],
            engine_version=ENGINE_VERSION,
        )
        db.add(issue)
        issues_created += 1

    db.flush()

    # Audit log
    db.add(
        AuditLog(
            entity_type="anomaly_detection",
            entity_id=deal_id,
            action=AuditAction.CREATE,
            actor="system",
            new_value={
                "detected_count": detected_count,
                "issues_created": issues_created,
                "threshold": str(threshold),
            },
        )
    )

    db.commit()

    logger.info(
        f"Anomaly detection completed: deal_id={deal_id}, "
        f"detected={detected_count}, issues_created={issues_created}"
    )

    return AnomalyDetectionResponse(
        detected_count=detected_count,
        issues_created=issues_created,
        engine_version=ENGINE_VERSION,
        threshold_used=threshold,
    )


def _generate_issue_title(result: AnomalyScoreResult) -> str:
    """이슈 제목 생성."""
    factors = [f.factor_type for f in result.risk_factors]
    factor_str = ", ".join(factors[:2]) if factors else "unknown"
    return f"[{result.risk_score:.0f}점] 이상치 감지 ({factor_str})"


def _generate_issue_description(result: AnomalyScoreResult) -> str:
    """이슈 설명 생성."""
    lines = [
        f"전표 ID: {result.entry_id}",
        f"리스크 점수: {result.risk_score:.2f}/100",
        "",
        "탐지 요인:",
    ]
    for f in result.risk_factors:
        lines.append(f"- [{f.factor_type}] {f.description} (기여도: {f.score_contribution:.2f})")

    if result.entry_data:
        lines.append("")
        lines.append("전표 정보:")
        if result.entry_data.get("amount"):
            lines.append(f"- 금액: {result.entry_data['amount']}")
        if result.entry_data.get("entry_date"):
            lines.append(f"- 일자: {result.entry_data['entry_date']}")
        if result.entry_data.get("description"):
            lines.append(f"- 적요: {result.entry_data['description']}")

    return "\n".join(lines)


def create_issues_from_anomalies(
    db: Session,
    deal_id: uuid.UUID,
    anomaly_results: list[AnomalyScoreResult],
    snapshot_id: uuid.UUID | None = None,
) -> list[Issue]:
    """탐지 결과를 Issue로 변환 (외부 호출용)."""
    issues = []
    for result in anomaly_results:
        if not result.is_anomaly:
            continue

        issue = Issue(
            deal_id=deal_id,
            snapshot_id=snapshot_id,
            category=IssueCategory.ANOMALY,
            severity=severity_from_risk_score(result.risk_score),
            status=IssueStatus.OPEN,
            title=_generate_issue_title(result),
            description=_generate_issue_description(result),
            risk_score=result.risk_score,
            source_type="GL",
            source_id=result.entry_id,
            source_detail=result.entry_data,
            detection_method="composite",
            detection_factors=[
                {
                    "factor_type": f.factor_type,
                    "score_contribution": str(f.score_contribution),
                    "raw_score": str(f.raw_score),
                    "description": f.description,
                }
                for f in result.risk_factors
            ],
            engine_version=ENGINE_VERSION,
        )
        db.add(issue)
        issues.append(issue)

    return issues


# ── Issue CRUD ────────────────────────────────────────────


def create_issue(
    db: Session,
    deal_id: uuid.UUID,
    data: IssueCreate,
) -> Issue:
    """수동 이슈 생성."""
    issue = Issue(
        deal_id=deal_id,
        category=data.category,
        severity=data.severity,
        status=IssueStatus.OPEN,
        title=data.title,
        description=data.description,
        source_type=data.source_type,
        source_id=data.source_id,
        source_detail=data.source_detail,
        detection_method=data.detection_method,
    )
    db.add(issue)
    db.flush()

    db.add(
        AuditLog(
            entity_type="issue",
            entity_id=issue.id,
            action=AuditAction.CREATE,
            actor="user",
            new_value={"title": data.title, "category": data.category.value},
        )
    )

    db.commit()
    db.refresh(issue)
    return issue


def get_issue(db: Session, issue_id: uuid.UUID) -> Issue:
    """이슈 상세 조회."""
    issue = db.get(Issue, issue_id)
    if not issue:
        raise NotFoundError(resource="Issue", resource_id=str(issue_id))
    return issue


def get_issues(
    db: Session,
    deal_id: uuid.UUID,
    severity: IssueSeverity | None = None,
    status: IssueStatus | None = None,
    category: IssueCategory | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Issue], int]:
    """필터 조건으로 이슈 목록 조회."""
    query = select(Issue).where(Issue.deal_id == deal_id)

    if severity:
        query = query.where(Issue.severity == severity)
    if status:
        query = query.where(Issue.status == status)
    if category:
        query = query.where(Issue.category == category)

    # 총 개수
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    # 페이지네이션
    query = query.order_by(Issue.risk_score.desc().nullslast(), Issue.created_at.desc())
    query = query.limit(limit).offset(offset)

    issues = list(db.scalars(query))
    return issues, total


def update_issue_status(
    db: Session,
    issue_id: uuid.UUID,
    data: IssueUpdate,
) -> Issue:
    """이슈 상태 변경."""
    issue = get_issue(db, issue_id)
    old_status = issue.status

    issue.status = data.status

    if data.status in (IssueStatus.RESOLVED, IssueStatus.FALSE_POSITIVE):
        issue.resolved_by = data.resolved_by
        issue.resolution_note = data.resolution_note
        issue.resolved_at = datetime.now(UTC)
    elif data.resolution_note:
        issue.resolution_note = data.resolution_note

    db.add(
        AuditLog(
            entity_type="issue",
            entity_id=issue_id,
            action=AuditAction.UPDATE,
            actor=data.resolved_by or "user",
            old_value={"status": old_status.value},
            new_value={"status": data.status.value},
        )
    )

    db.commit()
    db.refresh(issue)
    return issue


def get_issue_summary(db: Session, deal_id: uuid.UUID) -> IssueSummary:
    """이슈 요약 통계."""
    issues = list(
        db.scalars(
            select(Issue).where(Issue.deal_id == deal_id)
        )
    )

    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}

    for issue in issues:
        sev = issue.severity.value
        stat = issue.status.value
        cat = issue.category.value

        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_status[stat] = by_status.get(stat, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1

    return IssueSummary(
        total=len(issues),
        by_severity=by_severity,
        by_status=by_status,
        by_category=by_category,
    )
