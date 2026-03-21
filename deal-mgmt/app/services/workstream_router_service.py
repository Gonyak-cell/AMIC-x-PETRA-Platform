"""Shared VDR workstream router used by DD pipelines."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.enums import VdrFolderCategory
from app.services.text_extraction_service import VdrSourceFile

LDD_WORKSTREAM = "LDD"
FDD_WORKSTREAM = "FDD"
VALUATION_WORKSTREAM = "VALUATION"
COMMON_WORKSTREAM = "COMMON"

WORKSTREAMS: tuple[str, ...] = (
    LDD_WORKSTREAM,
    FDD_WORKSTREAM,
    VALUATION_WORKSTREAM,
    COMMON_WORKSTREAM,
)

_CATEGORY_WORKSTREAM_SCORES: dict[str, dict[str, int]] = {
    str(VdrFolderCategory.CORPORATE): {LDD_WORKSTREAM: 85},
    str(VdrFolderCategory.LEGAL): {LDD_WORKSTREAM: 90},
    str(VdrFolderCategory.HR): {LDD_WORKSTREAM: 75},
    str(VdrFolderCategory.TECHNICAL): {LDD_WORKSTREAM: 70, COMMON_WORKSTREAM: 25},
    str(VdrFolderCategory.REAL_ESTATE): {LDD_WORKSTREAM: 80},
    str(VdrFolderCategory.ENVIRONMENT): {LDD_WORKSTREAM: 80},
    str(VdrFolderCategory.IP): {LDD_WORKSTREAM: 80},
    str(VdrFolderCategory.INSURANCE): {LDD_WORKSTREAM: 65, COMMON_WORKSTREAM: 20},
    str(VdrFolderCategory.TAX): {LDD_WORKSTREAM: 65, FDD_WORKSTREAM: 65},
    str(VdrFolderCategory.FINANCIAL): {FDD_WORKSTREAM: 85, VALUATION_WORKSTREAM: 20},
    str(VdrFolderCategory.COMMERCIAL): {
        LDD_WORKSTREAM: 45,
        VALUATION_WORKSTREAM: 45,
        COMMON_WORKSTREAM: 25,
    },
    str(VdrFolderCategory.MARKET_RESEARCH): {
        VALUATION_WORKSTREAM: 85,
        COMMON_WORKSTREAM: 30,
    },
    str(VdrFolderCategory.CUSTOM): {COMMON_WORKSTREAM: 35},
}

_WORKSTREAM_KEYWORDS: dict[str, tuple[str, ...]] = {
    LDD_WORKSTREAM: (
        "agreement",
        "contract",
        "permit",
        "license",
        "lawsuit",
        "litigation",
        "judgment",
        "registry",
        "bylaws",
        "privacy",
        "shareholder",
        "governance",
        "compliance",
        "계약",
        "정관",
        "등기",
        "소송",
        "인허가",
        "허가",
        "개인정보",
    ),
    FDD_WORKSTREAM: (
        "financial",
        "statement",
        "ledger",
        "ebitda",
        "cash flow",
        "working capital",
        "budget",
        "forecast",
        "revenue",
        "profit",
        "balance sheet",
        "accounts receivable",
        "accounts payable",
        "재무",
        "매출",
        "영업이익",
        "자산",
        "부채",
        "운전자본",
        "현금흐름",
    ),
    VALUATION_WORKSTREAM: (
        "valuation",
        "dcf",
        "multiple",
        "peer",
        "market",
        "teaser",
        "information memorandum",
        "business plan",
        "projection",
        "terminal growth",
        "exit multiple",
        "peer group",
        "가치평가",
        "밸류에이션",
        "시장",
        "비교기업",
        "사업계획",
        "추정",
    ),
    COMMON_WORKSTREAM: (
        "presentation",
        "memo",
        "summary",
        "overview",
        "management",
        "meeting",
        "interview",
        "q&a",
        "qa",
        "deck",
        "briefing",
        "요약",
        "개요",
        "회의",
        "인터뷰",
        "발표",
        "메모",
    ),
}


@dataclass(frozen=True)
class WorkstreamRoutingOverride:
    primary_workstream: str
    workstream_tags: tuple[str, ...]
    override_note: str | None = None
    reviewed_by_email: str | None = None
    reviewed_at: datetime | None = None


@dataclass(frozen=True)
class RoutedWorkstreamSource:
    source: VdrSourceFile
    primary_workstream: str
    workstream_tags: tuple[str, ...]
    confidence: float
    reasons: tuple[str, ...]
    requires_manual_review: bool
    is_override: bool = False
    override_note: str | None = None
    reviewed_by_email: str | None = None
    reviewed_at: datetime | None = None


def validate_workstream(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in WORKSTREAMS:
        raise ValueError(f"Unsupported workstream: {value}")
    return normalized


def normalize_workstream_tags(
    primary_workstream: str,
    workstream_tags: tuple[str, ...] | list[str] | set[str] | None = None,
) -> tuple[str, ...]:
    primary = validate_workstream(primary_workstream)
    ordered: list[str] = [primary]
    for tag in workstream_tags or ():
        normalized = validate_workstream(tag)
        if normalized not in ordered:
            ordered.append(normalized)
    return tuple(ordered)


def route_vdr_sources(
    source_files: list[VdrSourceFile],
    *,
    min_confidence: float = 0.55,
    overrides: Mapping[Any, WorkstreamRoutingOverride | Mapping[str, Any]] | None = None,
) -> list[RoutedWorkstreamSource]:
    normalized_overrides = _normalize_override_map(overrides)
    return [
        _route_single_source(
            source,
            min_confidence=min_confidence,
            override=normalized_overrides.get(source.vdr_document_id)
            or normalized_overrides.get(str(source.vdr_document_id)),
        )
        for source in source_files
    ]


def build_workstream_routing_summary(
    routed_sources: list[RoutedWorkstreamSource],
    *,
    included_for: str | None = None,
    min_common_confidence: float = 0.55,
) -> dict[str, Any]:
    by_primary = Counter(routed.primary_workstream for routed in routed_sources)
    return {
        "version": "1.1",
        "summary": {
            "total_documents": len(routed_sources),
            "included_for_workstream": (
                sum(
                    1
                    for routed in routed_sources
                    if included_for and is_source_allowed_for_workstream(
                        routed,
                        included_for,
                        min_common_confidence=min_common_confidence,
                    )
                )
                if included_for
                else None
            ),
            "manual_review_documents": sum(1 for routed in routed_sources if routed.requires_manual_review),
            "overridden_documents": sum(1 for routed in routed_sources if routed.is_override),
            "by_primary_workstream": dict(by_primary),
        },
        "documents": [
            {
                "document_id": str(routed.source.vdr_document_id),
                "original_name": routed.source.original_name,
                "folder_category": str(routed.source.vdr_category),
                "ddrl_sections": list(routed.source.parsed.ddrl_sections or []),
                "primary_workstream": routed.primary_workstream,
                "workstream_tags": list(routed.workstream_tags),
                "confidence": routed.confidence,
                "requires_manual_review": routed.requires_manual_review,
                "reasons": list(routed.reasons),
                "is_override": routed.is_override,
                "override_note": routed.override_note,
                "reviewed_by_email": routed.reviewed_by_email,
                "reviewed_at": routed.reviewed_at.isoformat() if routed.reviewed_at else None,
            }
            for routed in routed_sources
        ],
    }


def filter_sources_for_workstream(
    routed_sources: list[RoutedWorkstreamSource],
    target_workstream: str,
    *,
    min_common_confidence: float = 0.55,
) -> list[VdrSourceFile]:
    return [
        routed.source
        for routed in routed_sources
        if is_source_allowed_for_workstream(
            routed,
            target_workstream,
            min_common_confidence=min_common_confidence,
        )
    ]


def filter_sources_for_workstreams(
    routed_sources: list[RoutedWorkstreamSource],
    target_workstreams: tuple[str, ...] | list[str] | set[str],
    *,
    min_common_confidence: float = 0.55,
) -> list[VdrSourceFile]:
    requested = tuple(dict.fromkeys(validate_workstream(tag) for tag in target_workstreams))
    return [
        routed.source
        for routed in routed_sources
        if is_source_allowed_for_any_workstream(
            routed,
            requested,
            min_common_confidence=min_common_confidence,
        )
    ]


def is_source_allowed_for_workstream(
    routed: RoutedWorkstreamSource,
    target_workstream: str,
    *,
    min_common_confidence: float = 0.55,
) -> bool:
    normalized_target = validate_workstream(target_workstream)
    if normalized_target in routed.workstream_tags:
        return True
    return COMMON_WORKSTREAM in routed.workstream_tags and routed.confidence >= min_common_confidence


def is_source_allowed_for_any_workstream(
    routed: RoutedWorkstreamSource,
    target_workstreams: tuple[str, ...] | list[str] | set[str],
    *,
    min_common_confidence: float = 0.55,
) -> bool:
    return any(
        is_source_allowed_for_workstream(
            routed,
            target_workstream,
            min_common_confidence=min_common_confidence,
        )
        for target_workstream in target_workstreams
    )


def _route_single_source(
    source: VdrSourceFile,
    *,
    min_confidence: float,
    override: WorkstreamRoutingOverride | None = None,
) -> RoutedWorkstreamSource:
    if override is not None:
        return RoutedWorkstreamSource(
            source=source,
            primary_workstream=override.primary_workstream,
            workstream_tags=override.workstream_tags,
            confidence=1.0,
            reasons=(f"manual_override:{override.primary_workstream}",),
            requires_manual_review=False,
            is_override=True,
            override_note=override.override_note,
            reviewed_by_email=override.reviewed_by_email,
            reviewed_at=override.reviewed_at,
        )

    scores: Counter[str] = Counter()
    reasons: list[str] = []
    category_key = str(source.vdr_category)

    for workstream, value in _CATEGORY_WORKSTREAM_SCORES.get(category_key, {}).items():
        scores[workstream] += value
        reasons.append(f"folder:{category_key}->{workstream}:{value}")

    content_sample = f"{source.original_name}\n{(source.parsed.text or '')[:1500]}".lower()
    for workstream, keywords in _WORKSTREAM_KEYWORDS.items():
        match_count = sum(1 for keyword in keywords if keyword.lower() in content_sample)
        if match_count:
            boost = min(30, 10 * match_count)
            scores[workstream] += boost
            reasons.append(f"keywords:{workstream}:{match_count}")

    if not scores:
        return RoutedWorkstreamSource(
            source=source,
            primary_workstream=COMMON_WORKSTREAM,
            workstream_tags=(COMMON_WORKSTREAM,),
            confidence=0.35,
            reasons=("unclassified",),
            requires_manual_review=True,
        )

    top_score = max(scores.values())
    sorted_scores = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    primary_workstream = sorted_scores[0][0]
    selected_tags = tuple(
        workstream for workstream, score in sorted_scores if score >= max(40, top_score - 20)
    ) or (primary_workstream,)
    confidence = min(0.98, top_score / 100.0)

    return RoutedWorkstreamSource(
        source=source,
        primary_workstream=primary_workstream,
        workstream_tags=selected_tags,
        confidence=confidence,
        reasons=tuple(reasons),
        requires_manual_review=confidence < min_confidence,
    )


def _normalize_override_map(
    overrides: Mapping[Any, WorkstreamRoutingOverride | Mapping[str, Any]] | None,
) -> dict[Any, WorkstreamRoutingOverride]:
    if not overrides:
        return {}

    normalized: dict[Any, WorkstreamRoutingOverride] = {}
    for key, value in overrides.items():
        normalized[key] = _coerce_override(value)
    return normalized


def _coerce_override(
    override: WorkstreamRoutingOverride | Mapping[str, Any],
) -> WorkstreamRoutingOverride:
    if isinstance(override, WorkstreamRoutingOverride):
        return WorkstreamRoutingOverride(
            primary_workstream=validate_workstream(override.primary_workstream),
            workstream_tags=normalize_workstream_tags(
                override.primary_workstream,
                override.workstream_tags,
            ),
            override_note=override.override_note,
            reviewed_by_email=override.reviewed_by_email,
            reviewed_at=override.reviewed_at,
        )

    primary_workstream = validate_workstream(str(override.get("primary_workstream", "")))
    workstream_tags = normalize_workstream_tags(primary_workstream, override.get("workstream_tags"))
    reviewed_at = override.get("reviewed_at")
    if reviewed_at is not None and not isinstance(reviewed_at, datetime):
        raise ValueError("reviewed_at must be a datetime when provided.")
    return WorkstreamRoutingOverride(
        primary_workstream=primary_workstream,
        workstream_tags=workstream_tags,
        override_note=override.get("override_note"),
        reviewed_by_email=override.get("reviewed_by_email"),
        reviewed_at=reviewed_at,
    )
