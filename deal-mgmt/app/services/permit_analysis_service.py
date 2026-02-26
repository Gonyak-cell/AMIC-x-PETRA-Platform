"""인허가 분석 서비스 — KB 기반 분석 (Phase 1 MVP)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    PermitAnalysisStatus,
    PermitFilingType,
    PermitRequirementStatus,
    PermitTimingType,
)
from app.models.permit_analysis import PermitAnalysis
from app.models.permit_requirement import PermitRequirement
from app.models.transaction import Transaction
from app.services.permit_knowledge_base import PermitKBEntry, lookup_permits


async def get_analysis(db: AsyncSession, txn_id: uuid.UUID) -> PermitAnalysis | None:
    """거래의 인허가 분석 결과를 조회한다."""
    q = select(PermitAnalysis).where(PermitAnalysis.transaction_id == txn_id)
    return (await db.execute(q)).scalar_one_or_none()


async def get_requirements(db: AsyncSession, txn_id: uuid.UUID) -> list[PermitRequirement]:
    """거래의 인허가 요건 목록을 조회한다."""
    q = (
        select(PermitRequirement)
        .where(PermitRequirement.transaction_id == txn_id)
        .order_by(PermitRequirement.sort_order, PermitRequirement.created_at)
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_requirement(
    db: AsyncSession,
    txn_id: uuid.UUID,
    req_id: uuid.UUID,
) -> PermitRequirement | None:
    """단일 인허가 요건을 조회한다."""
    q = select(PermitRequirement).where(
        PermitRequirement.id == req_id,
        PermitRequirement.transaction_id == txn_id,
    )
    return (await db.execute(q)).scalar_one_or_none()


def _calculate_deadline(
    target_close_date: str | None,
    timing_type: str,
    pre_days: int | None,
    post_days: int | None,
) -> str | None:
    """target_close_date 기반으로 마감일을 계산한다."""
    if not target_close_date:
        return None
    try:
        close = date.fromisoformat(target_close_date)
    except ValueError:
        return None

    if timing_type == "PRE_FILING" and pre_days:
        deadline = close - timedelta(days=pre_days)
        return deadline.isoformat()
    elif timing_type == "POST_FILING" and post_days:
        deadline = close + timedelta(days=post_days)
        return deadline.isoformat()
    elif timing_type == "BOTH":
        # 사전 기한이 있으면 사전 우선, 없으면 사후
        if pre_days:
            return (close - timedelta(days=pre_days)).isoformat()
        elif post_days:
            return (close + timedelta(days=post_days)).isoformat()
    return None


def _kb_entry_to_requirement(
    entry: PermitKBEntry,
    analysis_id: uuid.UUID,
    txn_id: uuid.UUID,
    target_close_date: str | None,
    order: int,
) -> PermitRequirement:
    """KB 항목을 PermitRequirement 모델로 변환한다."""
    deadline = _calculate_deadline(
        target_close_date,
        entry.timing_type,
        entry.pre_filing_days,
        entry.post_filing_days,
    )
    return PermitRequirement(
        analysis_id=analysis_id,
        transaction_id=txn_id,
        permit_name=entry.permit_name,
        regulatory_body=entry.regulatory_body,
        legal_basis=entry.legal_basis,
        filing_type=PermitFilingType(entry.filing_type),
        timing_type=PermitTimingType(entry.timing_type),
        pre_filing_deadline_days=entry.pre_filing_days,
        post_filing_deadline_days=entry.post_filing_days,
        calculated_deadline=deadline,
        required_documents=[{"name": doc} for doc in entry.required_documents],
        status=PermitRequirementStatus.IDENTIFIED,
        source="KB",
        confidence=1.0,
        notes=entry.notes,
        sort_order=order,
    )


async def analyze_permits(
    db: AsyncSession,
    txn: Transaction,
    business_types: list[str],
    existing_permits: list[dict],
    actor_email: str | None = None,
) -> PermitAnalysis:
    """인허가 분석을 실행한다 (KB 기반).

    1. 기존 분석이 있으면 삭제 후 재생성
    2. KB 매칭
    3. 기한 계산
    4. PermitRequirement 레코드 생성
    """
    # 기존 분석 삭제 (재분석 지원)
    existing = await get_analysis(db, txn.id)
    if existing:
        await db.delete(existing)
        await db.flush()

    # PermitAnalysis 생성
    analysis = PermitAnalysis(
        transaction_id=txn.id,
        status=PermitAnalysisStatus.ANALYZING,
        business_types=business_types,
        existing_permits=existing_permits,
        analysis_method="KB_ONLY",
        analyzed_by_email=actor_email,
    )
    db.add(analysis)
    await db.flush()

    # KB 조회
    deal_structure = txn.deal_structure
    deal_value = txn.estimated_deal_value
    target_close_date = txn.target_close_date

    kb_results = lookup_permits(
        business_types=business_types,
        deal_structure=deal_structure,
        deal_value=float(deal_value) if deal_value else None,
    )

    # PermitRequirement 생성
    for i, entry in enumerate(kb_results):
        req = _kb_entry_to_requirement(entry, analysis.id, txn.id, target_close_date, i)
        db.add(req)

    # KB 미지원 업종 경고
    kb_industry_codes = {e.industry_code for e in kb_results if not e.industry_code.startswith("UNIVERSAL_")}
    unsupported = [bt for bt in business_types if bt not in kb_industry_codes]
    notes_parts: list[str] = []
    if unsupported:
        notes_parts.append(f"KB 미지원 업종 (UNIVERSAL 항목만 적용됨): {', '.join(unsupported)}")
    if notes_parts:
        analysis.analysis_notes = "; ".join(notes_parts)

    analysis.status = PermitAnalysisStatus.COMPLETED
    await db.flush()
    return analysis


async def add_manual_requirement(
    db: AsyncSession,
    txn_id: uuid.UUID,
    analysis_id: uuid.UUID,
    data: dict,
    target_close_date: str | None = None,
) -> PermitRequirement:
    """인허가 요건을 수동으로 추가한다."""
    deadline = _calculate_deadline(
        target_close_date,
        data["timing_type"],
        data.get("pre_filing_deadline_days"),
        data.get("post_filing_deadline_days"),
    )
    req = PermitRequirement(
        analysis_id=analysis_id,
        transaction_id=txn_id,
        calculated_deadline=deadline,
        source="MANUAL",
        confidence=1.0,
        status=PermitRequirementStatus.IDENTIFIED,
        sort_order=99,
        filing_type=PermitFilingType(data["filing_type"]),
        timing_type=PermitTimingType(data["timing_type"]),
        permit_name=data["permit_name"],
        regulatory_body=data["regulatory_body"],
        legal_basis=data.get("legal_basis"),
        pre_filing_deadline_days=data.get("pre_filing_deadline_days"),
        post_filing_deadline_days=data.get("post_filing_deadline_days"),
        required_documents=data.get("required_documents"),
        notes=data.get("notes"),
    )
    db.add(req)
    await db.flush()
    return req


async def recalculate_deadlines(
    db: AsyncSession,
    txn_id: uuid.UUID,
    new_target_close_date: str,
) -> list[PermitRequirement]:
    """Closing 예정일 변경 시 모든 인허가 기한을 재계산한다."""
    requirements = await get_requirements(db, txn_id)
    for req in requirements:
        req.calculated_deadline = _calculate_deadline(
            new_target_close_date,
            req.timing_type.value,
            req.pre_filing_deadline_days,
            req.post_filing_deadline_days,
        )
    await db.flush()
    return requirements
