"""Financial Model Service — CRUD + VDR 추출 + 체크리스트 자동 생성 + Excel 생성."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import (
    FinancialModelStatus,
    FinancialModelType,
    FMChecklistCategory,
    FMChecklistItemStatus,
    FMChecklistStatus,
)
from app.models.financial_model import FinancialModel, FMChecklist, FMChecklistItem
from app.schemas.financial_model import FinancialModelCreate
from app.services.evidence_store_service import (
    build_document_chunk_lookup,
    build_platform_evidence_records,
    delete_platform_evidence_records,
    replace_platform_evidence_records,
)
from app.services.text_extraction_service import TextExtractionService
from app.services.vdr_routing_service import get_routing_override_map
from app.services.workstream_router_service import (
    FDD_WORKSTREAM,
    VALUATION_WORKSTREAM,
    build_workstream_routing_summary,
    is_source_allowed_for_any_workstream,
    route_vdr_sources,
)

# 상태 전이 불가 상태 (진행 중인 작업이 있음)
_BUSY_STATUSES = frozenset({FinancialModelStatus.GENERATING, FinancialModelStatus.FINALIZING})

logger = logging.getLogger(__name__)

FM_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "generated" / "financial_models"
FM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# error_message 잘림 길이 통일
MAX_ERROR_LEN = 1000

# ── 체크리스트 필드 레지스트리 (카테고리별 기본 항목) ──────────────────────


FM_FIELD_REGISTRY: list[dict] = [
    # Revenue & Growth
    {
        "category": FMChecklistCategory.REVENUE_FORECAST,
        "title": "매출액 실적 (최근 3~5년)",
        "field_type": "currency",
        "unit": "KRW",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.REVENUE_FORECAST,
        "title": "세그먼트별 매출 비중",
        "field_type": "percentage",
        "unit": "%",
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.GROWTH_ASSUMPTIONS,
        "title": "매출 성장률 가정 (향후 5년)",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.GROWTH_ASSUMPTIONS,
        "title": "시장 성장률 참조치",
        "field_type": "percentage",
        "unit": "%",
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.VOLUME_PRICE_MIX,
        "title": "물량 성장 vs 단가 상승 구분",
        "field_type": "text",
        "unit": None,
        "severity": "MEDIUM",
    },
    # Cost Structure
    {
        "category": FMChecklistCategory.COGS_FORECAST,
        "title": "매출원가율 실적/가정",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.COGS_FORECAST,
        "title": "원재료비 비중 및 추세",
        "field_type": "percentage",
        "unit": "%",
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.SGA_FORECAST,
        "title": "판관비율 실적/가정",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.SGA_FORECAST,
        "title": "인건비 비중",
        "field_type": "percentage",
        "unit": "%",
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.DEPRECIATION_AMORT,
        "title": "감가상각비 추정 방법",
        "field_type": "text",
        "unit": None,
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.CAPEX_FORECAST,
        "title": "CAPEX 가정 (매출 대비 %)",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    # Working Capital & Cash Flow
    {
        "category": FMChecklistCategory.NWC_ASSUMPTIONS,
        "title": "매출채권 회전일수 (DSO)",
        "field_type": "number",
        "unit": "일",
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.NWC_ASSUMPTIONS,
        "title": "재고자산 회전일수 (DIO)",
        "field_type": "number",
        "unit": "일",
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.NWC_ASSUMPTIONS,
        "title": "매입채무 회전일수 (DPO)",
        "field_type": "number",
        "unit": "일",
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.FCF_DERIVATION,
        "title": "Free Cash Flow 도출 방식",
        "field_type": "text",
        "unit": None,
        "severity": "HIGH",
    },
    # Capital Structure & WACC
    {
        "category": FMChecklistCategory.FM_DEBT_SCHEDULE,
        "title": "차입금 구조 (이자율, 만기)",
        "field_type": "text",
        "unit": None,
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.WACC_COMPONENTS,
        "title": "무위험이자율 (Rf)",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.WACC_COMPONENTS,
        "title": "시장리스크프리미엄 (MRP)",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.WACC_COMPONENTS,
        "title": "Beta (Unlevered / Levered)",
        "field_type": "number",
        "unit": "x",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.WACC_COMPONENTS,
        "title": "세전 타인자본비용 (Kd pre-tax)",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.WACC_COMPONENTS,
        "title": "자기자본비용 (Ke)",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.WACC_COMPONENTS,
        "title": "목표 자본구조 (D/E)",
        "field_type": "percentage",
        "unit": "%",
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.TAX_RATE,
        "title": "유효법인세율 가정",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    # Valuation
    {
        "category": FMChecklistCategory.DCF_PARAMETERS,
        "title": "Terminal Growth Rate",
        "field_type": "percentage",
        "unit": "%",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.DCF_PARAMETERS,
        "title": "Exit Multiple (EV/EBITDA)",
        "field_type": "number",
        "unit": "x",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.TRADING_MULTIPLES,
        "title": "비교기업 리스트 (GPCM)",
        "field_type": "text",
        "unit": None,
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.TRADING_MULTIPLES,
        "title": "적용 멀티플 (EV/EBITDA median)",
        "field_type": "number",
        "unit": "x",
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.TRANSACTION_MULTIPLES,
        "title": "선례거래 리스트 (GTM)",
        "field_type": "text",
        "unit": None,
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.TRANSACTION_MULTIPLES,
        "title": "적용 멀티플 (GTM median)",
        "field_type": "number",
        "unit": "x",
        "severity": "MEDIUM",
    },
    # Scenarios & Sensitivity
    {
        "category": FMChecklistCategory.BASE_SCENARIO,
        "title": "Base Case 핵심 파라미터 요약",
        "field_type": "text",
        "unit": None,
        "severity": "HIGH",
    },
    {
        "category": FMChecklistCategory.UPSIDE_SCENARIO,
        "title": "Upside Case 주요 차이점",
        "field_type": "text",
        "unit": None,
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.DOWNSIDE_SCENARIO,
        "title": "Downside Case 주요 차이점",
        "field_type": "text",
        "unit": None,
        "severity": "MEDIUM",
    },
    {
        "category": FMChecklistCategory.SENSITIVITY_MATRIX,
        "title": "민감도 분석 축 (WACC × Exit Multiple)",
        "field_type": "text",
        "unit": None,
        "severity": "MEDIUM",
    },
]

_VALUATION_CATEGORIES = frozenset(
    {
        FMChecklistCategory.WACC_COMPONENTS,
        FMChecklistCategory.DCF_PARAMETERS,
        FMChecklistCategory.TRADING_MULTIPLES,
        FMChecklistCategory.TRANSACTION_MULTIPLES,
        FMChecklistCategory.BASE_SCENARIO,
        FMChecklistCategory.UPSIDE_SCENARIO,
        FMChecklistCategory.DOWNSIDE_SCENARIO,
        FMChecklistCategory.SENSITIVITY_MATRIX,
    }
)


def _get_financial_model_target_workstreams(model_type: FinancialModelType) -> tuple[str, ...]:
    if model_type in {
        FinancialModelType.DCF,
        FinancialModelType.FULL,
    }:
        return (FDD_WORKSTREAM, VALUATION_WORKSTREAM)
    if model_type in {
        FinancialModelType.COMPS,
        FinancialModelType.TRANSACTION_COMPS,
    }:
        return (VALUATION_WORKSTREAM,)
    return (FDD_WORKSTREAM,)


def _build_financial_model_keywords(item: FMChecklistItem) -> list[str]:
    raw = " ".join(
        filter(
            None,
            [
                item.title,
                item.description,
                str(item.category.value).replace("_", " "),
            ],
        )
    ).lower()
    tokens = re.findall(r"[a-z0-9/%.+-]+|[가-힣]{2,}", raw)
    keywords: list[str] = []
    for token in tokens:
        cleaned = token.strip("()[]{}.,:;")
        if len(cleaned) < 2 or cleaned.isdigit():
            continue
        if cleaned not in keywords:
            keywords.append(cleaned)
    return keywords[:12]


def _iter_financial_model_chunks(routed_source: Any) -> list[dict[str, Any]]:
    metadata = routed_source.source.parsed.metadata or {}
    chunks = list(metadata.get("chunks") or [])
    if chunks:
        return chunks

    text = (routed_source.source.parsed.text or "").strip()
    if not text:
        return []
    return [{"chunk_id": None, "locator_type": "document", "ordinal": 1, "text": text[:1000]}]


def _format_financial_model_source_location(chunk: dict[str, Any]) -> str | None:
    if chunk.get("page") is not None:
        return f"Page {chunk['page']}"
    if chunk.get("sheet") is not None and chunk.get("row") is not None:
        return f"Sheet {chunk['sheet']} Row {chunk['row']}"
    if chunk.get("paragraph") is not None:
        return f"Paragraph {chunk['paragraph']}"
    if chunk.get("ordinal") is not None:
        return f"Chunk {chunk['ordinal']}"
    return None


def _extract_candidate_value(text: str, field_type: str | None, unit: str | None) -> str | None:
    normalized = " ".join(text.split())
    if not normalized:
        return None

    if field_type == "percentage":
        match = re.search(r"(-?\d+(?:[.,]\d+)?)\s*%", normalized)
        if match:
            return f"{match.group(1).replace(',', '')}%"
        return None

    if field_type == "number":
        if unit == "x":
            match = re.search(r"(-?\d+(?:[.,]\d+)?)\s*x", normalized, re.IGNORECASE)
            if match:
                return f"{match.group(1).replace(',', '')}x"
        if unit == "일":
            match = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:일|days?)", normalized, re.IGNORECASE)
            if match:
                return match.group(1).replace(",", "")
        match = re.search(r"(-?\d[\d,]*(?:\.\d+)?)", normalized)
        if match:
            return match.group(1).replace(",", "")
        return None

    if field_type == "currency":
        match = re.search(r"(?:₩|krw|원)?\s*(-?\d[\d,]*(?:\.\d+)?)", normalized, re.IGNORECASE)
        if match:
            return match.group(1).replace(",", "")
        return None

    if field_type == "text":
        return normalized[:180]

    return None


def _select_financial_model_source_match(
    item: FMChecklistItem,
    routed_sources: list[Any],
) -> tuple[Any, dict[str, Any], int] | None:
    keywords = _build_financial_model_keywords(item)
    preferred_workstreams = (
        {VALUATION_WORKSTREAM} if item.category in _VALUATION_CATEGORIES else {FDD_WORKSTREAM}
    )

    best_match: tuple[Any, dict[str, Any], int] | None = None
    best_score = 0
    for routed in routed_sources:
        document_name = routed.source.original_name.lower()
        for chunk in _iter_financial_model_chunks(routed):
            text = str(chunk.get("text", "") or "")
            if not text and not document_name:
                continue
            haystack = f"{document_name}\n{text}".lower()
            score = sum(4 if len(keyword) >= 4 else 2 for keyword in keywords if keyword in haystack)
            score += int(routed.confidence * 3)
            if routed.primary_workstream in preferred_workstreams:
                score += 4
            if routed.requires_manual_review:
                score -= 1
            if score > best_score:
                best_score = score
                best_match = (routed, chunk, score)

    if best_score < 5:
        return None
    return best_match


def _seed_financial_model_checklist_from_sources(
    checklist_items: list[FMChecklistItem],
    routed_sources: list[Any],
) -> int:
    seeded_count = 0
    for item in checklist_items:
        match = _select_financial_model_source_match(item, routed_sources)
        if match is None:
            continue

        routed, chunk, score = match
        snippet = str(chunk.get("text", "") or "").strip()[:500]
        if not snippet:
            continue

        candidate_value = _extract_candidate_value(snippet, item.field_type, item.unit)
        item.auto_finding = snippet
        if candidate_value:
            item.auto_value = candidate_value
        elif item.field_type == "text":
            item.auto_value = snippet[:180]

        item.source_vdr_doc_id = routed.source.vdr_document_id
        item.source_vdr_doc_name = routed.source.original_name
        item.source_location = _format_financial_model_source_location(chunk)
        item.confidence = round(min(0.99, max(0.35, routed.confidence * min(1.0, score / 12.0))), 2)
        metadata = dict(item.extra_metadata or {})
        metadata.update(
            {
                "workstream_tags": list(routed.workstream_tags),
                "primary_workstream": routed.primary_workstream,
                "routing_confidence": routed.confidence,
                "requires_manual_review": routed.requires_manual_review,
                "routing_reasons": list(routed.reasons),
                "chunk_id": chunk.get("chunk_id"),
            }
        )
        item.extra_metadata = metadata
        seeded_count += 1

    return seeded_count


def _build_financial_model_source_routing(
    routed_sources: list[Any],
    target_workstreams: tuple[str, ...],
) -> dict[str, Any]:
    summary = build_workstream_routing_summary(routed_sources)
    included_ids = {
        str(routed.source.vdr_document_id)
        for routed in routed_sources
        if is_source_allowed_for_any_workstream(routed, target_workstreams)
    }
    summary["summary"]["target_workstreams"] = list(target_workstreams)
    summary["summary"]["included_for_financial_model"] = len(included_ids)
    summary["summary"]["excluded_from_financial_model"] = len(routed_sources) - len(included_ids)
    for document in summary["documents"]:
        document["include_for_financial_model"] = document["document_id"] in included_ids
    return summary


def _build_financial_model_evidence_records(
    fm: FinancialModel,
    checklist: FMChecklist,
) -> list[dict[str, Any]]:
    analysis_phase = "FINAL" if checklist.status == FMChecklistStatus.FINALIZED else "DRAFT"
    records: list[dict[str, Any]] = []

    for ordinal, item in enumerate(checklist.items, start=1):
        if not item.source_vdr_doc_id or not item.source_vdr_doc_name:
            continue

        metadata = dict(item.extra_metadata or {})
        item_workstream = VALUATION_WORKSTREAM if item.category in _VALUATION_CATEGORIES else FDD_WORKSTREAM
        workstream_tags = [str(tag) for tag in (metadata.get("workstream_tags") or [])]
        primary_workstream = str(metadata.get("primary_workstream") or "") or None
        chunk_id = str(metadata.get("chunk_id") or "") or None
        snippet = (item.user_correction or item.auto_finding or item.description or "").strip() or None
        source_location = item.source_location

        is_foreign_workstream = bool(workstream_tags) and item_workstream not in workstream_tags
        locator: dict[str, Any] = {}
        if chunk_id:
            locator["chunk_id"] = chunk_id
        if source_location:
            locator["source_location"] = source_location

        records.append(
            {
                "workstream": item_workstream,
                "section_type": str(item.category.value),
                "item_id": str(item.id),
                "vdr_document_id": item.source_vdr_doc_id,
                "reference_label": item.source_vdr_doc_name,
                "original_name": item.source_vdr_doc_name,
                "primary_workstream": primary_workstream,
                "workstream_tags": workstream_tags,
                "evidence_kind": "VALUATION_SUPPORT" if item_workstream == VALUATION_WORKSTREAM else "FINANCIAL_SUPPORT",
                "directness": "INDIRECT",
                "confidence": float(item.confidence or 0.0),
                "relevance_score": float(item.confidence or 0.0),
                "source_page": source_location,
                "source_snippet": snippet,
                "evidence_locator": locator or None,
                "requires_manual_review": bool(metadata.get("requires_manual_review")),
                "is_foreign_workstream": is_foreign_workstream,
                "is_unresolved_reference": False,
                "used_in_draft": analysis_phase == "DRAFT",
                "used_in_final": analysis_phase == "FINAL",
                "analysis_phase": analysis_phase,
                "ordinal": ordinal,
                "chunk_id": chunk_id,
            }
        )

    return records


async def _persist_financial_model_evidence_records(
    db: AsyncSession,
    fm: FinancialModel,
    checklist: FMChecklist,
) -> int:
    evidence_records = _build_financial_model_evidence_records(fm, checklist)
    document_ids = [
        uuid.UUID(str(record["vdr_document_id"]))
        for record in evidence_records
        if record.get("vdr_document_id")
    ]
    chunk_lookup = await build_document_chunk_lookup(db, vdr_document_ids=document_ids)
    platform_records = build_platform_evidence_records(
        transaction_id=fm.transaction_id,
        artifact_type="FINANCIAL_MODEL",
        artifact_id=fm.id,
        workstream=VALUATION_WORKSTREAM if fm.model_type == FinancialModelType.DCF else FDD_WORKSTREAM,
        source_records=evidence_records,
        document_chunk_lookup=chunk_lookup,
    )
    await replace_platform_evidence_records(
        db,
        artifact_type="FINANCIAL_MODEL",
        artifact_id=fm.id,
        records=platform_records,
    )
    return len(platform_records)


# ── CRUD ──────────────────────────────────────────────────────────────────


async def list_financial_models(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[FinancialModel]:
    """거래의 재무모델 목록을 조회한다."""
    stmt = (
        select(FinancialModel)
        .where(FinancialModel.transaction_id == transaction_id)
        .order_by(FinancialModel.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_financial_model(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> FinancialModel:
    """재무모델을 조회한다."""
    stmt = select(FinancialModel).where(FinancialModel.id == fm_id, FinancialModel.transaction_id == transaction_id)
    fm = (await db.execute(stmt)).scalar_one_or_none()
    if fm is None:
        raise DocumentNotFoundError(f"FinancialModel {fm_id}")
    return fm


async def create_financial_model(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: FinancialModelCreate,
    actor_email: str,
) -> FinancialModel:
    """재무모델을 생성하고, VDR 기반 체크리스트를 자동 생성한다."""
    fm = FinancialModel(
        transaction_id=transaction_id,
        model_type=body.model_type,
        title=body.title,
        parameters=body.parameters,
        vdr_document_ids=body.vdr_document_ids,
        status=FinancialModelStatus.GENERATING,
        created_by_email=actor_email,
    )
    db.add(fm)
    await db.flush()

    # 체크리스트 자동 생성 (필드 레지스트리 기반)
    checklist = FMChecklist(
        financial_model_id=fm.id,
        status=FMChecklistStatus.PENDING_REVIEW,
    )
    db.add(checklist)
    await db.flush()

    for idx, field_def in enumerate(FM_FIELD_REGISTRY):
        item = FMChecklistItem(
            checklist_id=checklist.id,
            category=field_def["category"],
            order_index=idx,
            title=field_def["title"],
            description=f"{field_def['title']} — 자동 추출 또는 사용자 입력 필요",
            field_type=field_def["field_type"],
            unit=field_def["unit"],
            severity=field_def["severity"],
            status=FMChecklistItemStatus.AUTO_GENERATED,
        )
        db.add(item)

    # 상태를 PENDING_REVIEW로 전환 (VDR 추출은 백그라운드)
    fm.status = FinancialModelStatus.PENDING_REVIEW
    await db.commit()
    await db.refresh(fm)

    # VDR 추출 + Ralph Loop Pass 1은 Celery 태스크로 실행
    if body.vdr_document_ids and body.enable_ralph_loop:
        from app.tasks.fm_tasks import run_vdr_extraction_and_ralph_task

        run_vdr_extraction_and_ralph_task.delay(
            fm_id=str(fm.id),
            transaction_id=str(transaction_id),
            vdr_document_ids=body.vdr_document_ids,
            model_type=body.model_type,
            ralph_max_iterations=body.ralph_max_iterations,
            ralph_max_cost_usd=body.ralph_max_cost_usd,
        )

    return fm


async def delete_financial_model(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> None:
    """재무모델을 삭제한다."""
    fm = await get_financial_model(db, fm_id, transaction_id)
    await delete_platform_evidence_records(
        db,
        artifact_type="FINANCIAL_MODEL",
        artifact_id=fm.id,
    )
    await db.delete(fm)
    await db.commit()


async def regenerate_financial_model(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> FinancialModel:
    """재무모델을 재생성한다.

    GENERATING/FINALIZING 상태에서는 재생성 불가 (진행 중인 태스크와 충돌 방지).
    """
    fm = await get_financial_model(db, fm_id, transaction_id)

    if fm.status in _BUSY_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot regenerate: model is currently {fm.status.value}",
        )

    fm.status = FinancialModelStatus.GENERATING
    fm.version += 1
    fm.error_message = None
    fm.file_path = None
    fm.file_name = None
    fm.file_size_bytes = None
    fm.ralph_score = None
    await db.commit()
    await db.refresh(fm)

    # VDR 기반 Ralph Loop 재실행 트리거
    if fm.vdr_document_ids:
        from app.tasks.fm_tasks import run_vdr_extraction_and_ralph_task

        run_vdr_extraction_and_ralph_task.delay(
            fm_id=str(fm.id),
            transaction_id=str(transaction_id),
            vdr_document_ids=fm.vdr_document_ids,
            model_type=fm.model_type,
        )
    else:
        # VDR 없으면 즉시 PENDING_REVIEW
        fm.status = FinancialModelStatus.PENDING_REVIEW
        await db.commit()
        await db.refresh(fm)

    return fm


async def reset_stuck_model(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
    *,
    actor_email: str = "",
) -> FinancialModel:
    """GENERATING/FINALIZING 상태에서 멈춘 재무모델을 PENDING_REVIEW로 리셋한다."""
    fm = await get_financial_model(db, fm_id, transaction_id)

    if fm.status not in _BUSY_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"리셋 불가: 현재 상태가 {fm.status.value}입니다 (GENERATING 또는 FINALIZING만 리셋 가능)",
        )

    old_status = fm.status.value
    fm.status = FinancialModelStatus.PENDING_REVIEW
    fm.error_message = "관리자에 의해 수동 리셋됨"

    from app.models.enums import AuditAction
    from app.services import audit_service

    await audit_service.record(
        db,
        entity_type="FinancialModel",
        entity_id=fm.id,
        action=AuditAction.UPDATE,
        actor_email=actor_email,
        new_value={"action": "manual_reset", "old_status": old_status, "new_status": "PENDING_REVIEW"},
    )
    await db.commit()
    await db.refresh(fm)
    return fm


# ── Background Tasks ─────────────────────────────────────────────────────


async def sync_financial_model_evidence(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> int:
    await db.flush()

    stmt = (
        select(FinancialModel)
        .where(FinancialModel.id == fm_id, FinancialModel.transaction_id == transaction_id)
        .options(joinedload(FinancialModel.checklist).joinedload(FMChecklist.items))
    )
    fm = (await db.execute(stmt)).unique().scalar_one_or_none()
    if fm is None:
        raise DocumentNotFoundError(f"FinancialModel {fm_id}")

    if fm.checklist is None:
        await replace_platform_evidence_records(
            db,
            artifact_type="FINANCIAL_MODEL",
            artifact_id=fm.id,
            records=[],
        )
        return 0

    return await _persist_financial_model_evidence_records(db, fm, fm.checklist)


async def _run_vdr_extraction_and_ralph(
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
    vdr_document_ids: list[str],
    model_type: FinancialModelType,
    ralph_max_iterations: int = 2,
    ralph_max_cost_usd: float = 15.0,
) -> None:
    """VDR 문서에서 재무 데이터를 추출하고 Ralph Loop Pass 1로 초안 Excel을 생성한다."""
    from app.core.database import async_session_factory
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.excel_gate import ExcelProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.excel_generator import RalphExcelGenerator
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd
    from app.services.fm_checklist_service import FMChecklistService

    logger.info(
        "Background: VDR extraction + Ralph Pass 1 for FM %s (txn=%s, vdr_docs=%d, type=%s)",
        fm_id,
        transaction_id,
        len(vdr_document_ids),
        model_type,
    )

    try:
        async with async_session_factory() as db:
            fm = await get_financial_model(db, fm_id, transaction_id)

            # 멱등성 가드: 이미 완료/실패 또는 다른 단계 진행 중이면 스킵
            if fm.status not in (
                FinancialModelStatus.GENERATING,
                FinancialModelStatus.PENDING_REVIEW,
            ):
                logger.warning(
                    "FM %s skipping Pass 1: unexpected status %s",
                    fm_id,
                    fm.status,
                )
                return

            # 1. 체크리스트에서 auto_value 추출
            svc = FMChecklistService(db)
            checklist = await svc.get_checklist(fm_id)
            parameters = dict(fm.parameters or {})
            target_workstreams = _get_financial_model_target_workstreams(fm.model_type)

            selected_doc_ids: list[uuid.UUID] = []
            for raw_doc_id in vdr_document_ids:
                try:
                    selected_doc_ids.append(uuid.UUID(str(raw_doc_id)))
                except (TypeError, ValueError):
                    logger.warning("Skipping invalid FM VDR document id: %s", raw_doc_id)

            if selected_doc_ids:
                source_files = await TextExtractionService().extract_from_vdr_documents(
                    db,
                    transaction_id,
                    document_ids=selected_doc_ids,
                )
                if source_files:
                    routing_overrides = await get_routing_override_map(
                        db,
                        transaction_id,
                        document_ids=selected_doc_ids,
                    )
                    routed_sources = route_vdr_sources(source_files, overrides=routing_overrides)
                    relevant_routed_sources = [
                        routed
                        for routed in routed_sources
                        if is_source_allowed_for_any_workstream(routed, target_workstreams)
                    ]
                    parameters["source_routing"] = _build_financial_model_source_routing(
                        routed_sources,
                        target_workstreams,
                    )
                    parameters["financial_model_workstreams"] = list(target_workstreams)
                    parameters["seeded_checklist_items"] = _seed_financial_model_checklist_from_sources(
                        checklist.items,
                        relevant_routed_sources,
                    )
                    fm.parameters = parameters
            await db.flush()
            await _persist_financial_model_evidence_records(db, fm, checklist)

            checklist_values: dict[str, str] = {}
            for item in checklist.items:
                if item.auto_value:
                    checklist_values[item.title] = item.auto_value

            # 2. Ralph Loop 구성
            generator: RalphExcelGenerator | None = None
            generator = RalphExcelGenerator(
                model_type=fm.model_type,
                title=fm.title,
                checklist_values=checklist_values,
                parameters=fm.parameters,
            )
            gates = [
                ExcelProgrammaticGate(),
                LLMJudgeGate(doc_type="excel"),  # LLM 미연결 시 fallback 사용
            ]
            prd = load_prd("financial_model")
            config = LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=ralph_max_iterations,
                    max_cost_usd=ralph_max_cost_usd,
                ),
                output_dir=str(FM_OUTPUT_DIR / str(transaction_id)),
            )

            # 3. Ralph Loop Pass 1 실행
            orchestrator = RalphLoopOrchestrator(generator, gates, prd, config)
            result = await orchestrator.run({"checklist_values": checklist_values})

            # 4. FM 상태 업데이트
            fm.ralph_session_id = result.session_id
            fm.ralph_score = result.final_score
            fm.status = FinancialModelStatus.PENDING_REVIEW
            if result.output_path:
                fm.file_path = result.output_path
                fm.file_name = Path(result.output_path).name
            await db.commit()

            logger.info(
                "FM %s Ralph Pass 1 완료: score=%.2f, iterations=%d",
                fm_id,
                result.final_score,
                result.total_iterations,
            )

    except Exception as e:
        logger.error("FM %s Ralph Pass 1 FAILED: %s", fm_id, e, exc_info=True)
        # 에러 시에도 PENDING_REVIEW로 전환 (체크리스트 리뷰는 가능)
        try:
            async with async_session_factory() as db:
                fm = await get_financial_model(db, fm_id, transaction_id)
                fm.status = FinancialModelStatus.PENDING_REVIEW
                fm.error_message = f"Ralph Pass 1 실패 (체크리스트 리뷰 가능): {str(e)[:MAX_ERROR_LEN]}"
                await db.commit()
        except Exception:
            logger.error("Failed to update FM status after Ralph Pass 1 failure", exc_info=True)
    finally:
        if generator is not None:
            generator.cleanup()


async def run_finalize_and_generate(
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> None:
    """Finalize → Ralph Loop Pass 2 → 최종 Excel 생성.

    체크리스트 confirmed_value(user_value 우선) 기반으로
    Ralph Loop Pass 2를 실행하고, FinancialModel 상태를 READY로 전환한다.
    Ralph Loop 실패 시 직접 FinancialModelBuilder로 fallback 생성.
    """
    from app.core.database import async_session_factory
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.excel_gate import ExcelProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.excel_generator import RalphExcelGenerator
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd
    from app.services.fm_checklist_service import FMChecklistService

    logger.info(
        "Background: Finalize + Ralph Pass 2 for FM %s (txn=%s)",
        fm_id,
        transaction_id,
    )

    try:
        async with async_session_factory() as db:
            fm = await get_financial_model(db, fm_id, transaction_id)

            # 멱등성 가드: FINALIZING 상태가 아니면 스킵
            if fm.status != FinancialModelStatus.FINALIZING:
                logger.warning(
                    "FM %s skipping Pass 2: expected FINALIZING, got %s",
                    fm_id,
                    fm.status,
                )
                return

            svc = FMChecklistService(db)
            checklist = await svc.get_checklist(fm_id)

            # 체크리스트 항목에서 confirmed 값 추출 (user_value 우선)
            checklist_values: dict[str, str] = {}
            for item in checklist.items:
                val = item.user_value or item.auto_value or ""
                if val:
                    checklist_values[item.title] = val

            file_name = f"{fm.title.replace(' ', '_')}_v{fm.version}.xlsx"
            output_dir = str(FM_OUTPUT_DIR / str(transaction_id))

            # Ralph Loop Pass 2 (최종)
            generator: RalphExcelGenerator | None = None
            generator = RalphExcelGenerator(
                model_type=fm.model_type,
                title=fm.title,
                checklist_values=checklist_values,
                parameters=fm.parameters,
            )
            gates = [
                ExcelProgrammaticGate(),
                LLMJudgeGate(doc_type="excel"),
            ]
            prd = load_prd("financial_model")
            config = LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=3,
                    max_cost_usd=20.0,
                ),
                output_dir=output_dir,
            )

            orchestrator = RalphLoopOrchestrator(generator, gates, prd, config)
            result = await orchestrator.run({"checklist_values": checklist_values})

            # 최종 파일 경로 결정
            output_path = result.output_path
            if not output_path:
                # Ralph Loop 실패 시 직접 빌드 (fallback)
                from app.excel.model_builder import FinancialModelBuilder

                logger.warning("FM %s Ralph Pass 2 output 없음 — fallback 빌드", fm_id)
                path = Path(output_dir) / file_name
                path.parent.mkdir(parents=True, exist_ok=True)
                builder = FinancialModelBuilder(
                    model_type=fm.model_type,
                    title=fm.title,
                    checklist_values=checklist_values,
                    parameters=fm.parameters,
                )
                output_path = str(builder.save(path))

            # 품질 게이트 실행 (Finalize 단계)
            try:
                from app.ralph.gates.excel_gate import ExcelProgrammaticGate as _EGate

                _gate = _EGate()
                _gate_result = await _gate.evaluate(
                    output_path,
                    prd_section={"model_type": fm.model_type},
                )

                fm.quality_report = {
                    "dimensions": [
                        {"name": d.name, "label": d.label, "score": d.score, "weight": d.weight}
                        for d in _gate_result.dimensions
                    ],
                    "issues": _gate_result.issues,
                    "critical_flags": _gate_result.critical_flags,
                    "weighted_score": _gate_result.weighted_score,
                }

                if _gate_result.critical_flags:
                    fm.status = FinancialModelStatus.PENDING_REVIEW
                    fm.quality_status = "FAIL"
                    fm.error_message = f"품질 게이트 미통과: {_gate_result.critical_flags}"
                else:
                    fm.status = FinancialModelStatus.READY
                    fm.quality_status = "PASS" if _gate_result.weighted_score >= 3.5 else "CONDITIONAL"
                    fm.error_message = None
            except Exception as _gate_exc:
                logger.warning("FM %s 품질 게이트 실행 실패: %s", fm_id, _gate_exc)
                fm.status = FinancialModelStatus.FAILED
                fm.quality_status = "FAIL"
                fm.error_message = f"품질 게이트 실행 실패: {_gate_exc}"

            # FM 파일 정보 업데이트
            fm.file_path = output_path
            fm.file_name = file_name
            fm.file_size_bytes = Path(output_path).stat().st_size
            fm.ralph_score = result.final_score
            await db.commit()

            logger.info(
                "FM %s finalized: %s (%.1f KB, score=%.2f)",
                fm_id,
                file_name,
                fm.file_size_bytes / 1024,
                result.final_score,
            )

    except Exception as e:
        logger.error("FM %s finalize FAILED: %s", fm_id, e, exc_info=True)
        try:
            async with async_session_factory() as db:
                fm = await get_financial_model(db, fm_id, transaction_id)
                fm.status = FinancialModelStatus.FAILED
                fm.error_message = str(e)[:MAX_ERROR_LEN]
                await db.commit()
        except Exception:
            logger.error("Failed to update FM status to FAILED", exc_info=True)
    finally:
        if generator is not None:
            generator.cleanup()
