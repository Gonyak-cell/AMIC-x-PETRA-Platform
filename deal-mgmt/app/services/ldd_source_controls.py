"""LDD-specific source controls built on top of shared workstream routing."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.ralph.generators.ldd.project_green_style import ProjectGreenToneContext, choose_project_green_modality
from app.services.text_extraction_service import VdrSourceFile
from app.services.workstream_router_service import (
    COMMON_WORKSTREAM,
    FDD_WORKSTREAM,
    LDD_WORKSTREAM,
    VALUATION_WORKSTREAM,
    RoutedWorkstreamSource,
    WorkstreamRoutingOverride,
    build_workstream_routing_summary,
    route_vdr_sources,
)


@dataclass(frozen=True)
class RoutedLDDSource(RoutedWorkstreamSource):
    include_for_ldd: bool = False

SOURCE_CONTROL_HARD_BLOCK_CODES: frozenset[str] = frozenset(
    {
        "foreign_workstream_contamination",
        "unresolved_evidence_refs",
        "missing_required_evidence",
        "missing_direct_evidence_for_material_issue",
        "template_placeholder_remnants",
    }
)

_DIRECT_CONTRACT_KEYWORDS = (
    "agreement",
    "contract",
    "sha",
    "spa",
    "ssa",
    "bta",
    "주주간계약",
    "계약",
    "정관",
)
_DIRECT_LEGAL_KEYWORDS = (
    "permit",
    "license",
    "registry",
    "certificate",
    "judgment",
    "lawsuit",
    "complaint",
    "허가",
    "인허가",
    "등기",
    "등록",
    "판결",
    "소장",
)
_INDIRECT_SUMMARY_KEYWORDS = ("memo", "summary", "presentation", "meeting", "interview", "메모", "요약", "발표")
_INDIRECT_CORRESPONDENCE_KEYWORDS = ("email", "mail", "letter", "correspondence", "이메일", "메일", "서신")
_PLACEHOLDER_PATTERNS: tuple[str, ...] = (
    "{{",
    "}}",
    "[이곳에 텍스트 입력]",
    "[부문명 기재]",
    "[작성자 기재]",
    "[검토범위 기재]",
    "[프로젝트 코드명]",
)


def route_vdr_sources_for_ldd(
    source_files: list[VdrSourceFile],
    *,
    min_common_confidence: float = 0.55,
    routing_overrides: Mapping[Any, WorkstreamRoutingOverride | Mapping[str, Any]] | None = None,
) -> tuple[list[RoutedLDDSource], dict[str, Any]]:
    routed = [
        RoutedLDDSource(
            source=entry.source,
            primary_workstream=entry.primary_workstream,
            workstream_tags=entry.workstream_tags,
            confidence=entry.confidence,
            reasons=entry.reasons,
            requires_manual_review=entry.requires_manual_review,
            is_override=entry.is_override,
            override_note=entry.override_note,
            reviewed_by_email=entry.reviewed_by_email,
            reviewed_at=entry.reviewed_at,
            include_for_ldd=LDD_WORKSTREAM in entry.workstream_tags
            or (COMMON_WORKSTREAM in entry.workstream_tags and entry.confidence >= min_common_confidence),
        )
        for entry in route_vdr_sources(
            source_files,
            min_confidence=min_common_confidence,
            overrides=routing_overrides,
        )
    ]
    summary = build_workstream_routing_summary(
        routed,
        included_for=LDD_WORKSTREAM,
        min_common_confidence=min_common_confidence,
    )
    summary["summary"]["included_for_ldd"] = summary["summary"].pop("included_for_workstream")
    summary["summary"]["excluded_from_ldd"] = (
        summary["summary"]["total_documents"] - summary["summary"]["included_for_ldd"]
    )
    for doc in summary["documents"]:
        routed_doc = next(
            candidate for candidate in routed if str(candidate.source.vdr_document_id) == doc["document_id"]
        )
        doc["include_for_ldd"] = routed_doc.include_for_ldd
    return routed, summary


def filter_ldd_relevant_sources(
    routed_sources: list[RoutedLDDSource],
    *,
    min_common_confidence: float = 0.55,
) -> list[VdrSourceFile]:
    return [routed.source for routed in routed_sources if routed.include_for_ldd]


def is_ldd_routed_source(routed: RoutedLDDSource, *, min_common_confidence: float = 0.55) -> bool:
    return routed.include_for_ldd


def build_ldd_evidence_ledger(
    sections: list[dict] | None,
    routed_sources: list[RoutedLDDSource],
    *,
    min_common_confidence: float = 0.55,
) -> dict[str, Any]:
    source_lookup = _build_source_lookup(routed_sources)
    section_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_items: dict[str, dict[str, Any]] = {}
    direct_refs = 0
    indirect_refs = 0
    foreign_refs = 0
    unresolved_refs = 0
    items_missing_evidence = 0
    items_missing_direct_evidence = 0
    items_with_manual_review_sources = 0

    for section in sections or []:
        section_type = section.get("section_type", "")
        for item in section.get("items", []) or []:
            item_id = str(item.get("item_id", ""))
            evidence_docs: list[dict[str, Any]] = []
            unresolved: list[str] = []
            foreign: list[str] = []

            for ref in item.get("evidence_refs", []) or []:
                reference = str(ref)
                routed = _resolve_routed_source(reference, source_lookup)
                if routed is None:
                    unresolved.append(reference)
                    continue

                profile = _profile_evidence_source(routed)
                chunk = _select_trace_chunk(item, routed.source)
                include_for_ldd = is_ldd_routed_source(routed, min_common_confidence=min_common_confidence)

                if profile["directness"] == "DIRECT":
                    direct_refs += 1
                else:
                    indirect_refs += 1

                if not include_for_ldd:
                    foreign.append(reference)
                    foreign_refs += 1

                evidence_docs.append(
                    {
                        "reference": reference,
                        "document_id": str(routed.source.vdr_document_id),
                        "original_name": routed.source.original_name,
                        "folder_category": str(routed.source.vdr_category),
                        "workstream_tags": list(routed.workstream_tags),
                        "primary_workstream": routed.primary_workstream,
                        "include_for_ldd": include_for_ldd,
                        "requires_manual_review": routed.requires_manual_review,
                        "chunk_id": chunk.get("chunk_id"),
                        "page_reference": chunk.get("page_reference"),
                        "snippet": chunk.get("snippet"),
                        "locator": chunk.get("locator"),
                        **profile,
                    }
                )

            unresolved_refs += len(unresolved)
            if evidence_docs and any(doc["requires_manual_review"] for doc in evidence_docs):
                items_with_manual_review_sources += 1

            material_issue = item.get("status") == "ISSUE" and item.get("issue_level") in {"CRITICAL", "HIGH"}
            has_direct = any(doc["directness"] == "DIRECT" for doc in evidence_docs)
            if _requires_evidence(item) and not evidence_docs:
                items_missing_evidence += 1
            if material_issue and evidence_docs and not has_direct:
                items_missing_direct_evidence += 1

            modality = choose_project_green_modality(
                ProjectGreenToneContext(
                    evidence_count=len(evidence_docs),
                    confidence=float(item.get("confidence", 0.0) or 0.0),
                    status=str(item.get("status", "")),
                    issue_level=str(item.get("issue_level", "") or ""),
                    rfi_required=bool(item.get("rfi_required")),
                    evidence_refs=tuple(doc["original_name"] for doc in evidence_docs),
                )
            )

            ledger_item = {
                "item_id": item_id,
                "item_name": item.get("name", ""),
                "section_type": section_type,
                "status": item.get("status"),
                "issue_level": item.get("issue_level"),
                "confidence": item.get("confidence", 0.0),
                "evidence_count": len(evidence_docs),
                "direct_evidence_count": sum(1 for doc in evidence_docs if doc["directness"] == "DIRECT"),
                "indirect_evidence_count": sum(1 for doc in evidence_docs if doc["directness"] == "INDIRECT"),
                "foreign_workstream_refs": foreign,
                "unresolved_refs": unresolved,
                "recommended_modality": modality,
                "requires_manual_review": any(doc["requires_manual_review"] for doc in evidence_docs),
                "missing_required_evidence": _requires_evidence(item) and len(evidence_docs) == 0,
                "missing_direct_evidence_for_material_issue": material_issue and bool(evidence_docs) and not has_direct,
                "documents": evidence_docs,
            }
            section_items[section_type].append(ledger_item)
            all_items[item_id] = ledger_item

    return {
        "version": "2.0",
        "summary": {
            "items_with_evidence": sum(1 for item in all_items.values() if item["evidence_count"] > 0),
            "items_missing_evidence": items_missing_evidence,
            "items_missing_direct_evidence": items_missing_direct_evidence,
            "items_with_manual_review_sources": items_with_manual_review_sources,
            "direct_refs": direct_refs,
            "indirect_refs": indirect_refs,
            "foreign_workstream_refs": foreign_refs,
            "unresolved_refs": unresolved_refs,
        },
        "by_section": dict(section_items),
        "by_item_id": all_items,
    }


def build_ldd_evidence_records(
    *,
    transaction_id: str,
    report_id: str,
    evidence_ledger: dict[str, Any] | None,
    analysis_phase: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    used_in_final = analysis_phase.upper() == "FINAL"
    for item in (evidence_ledger or {}).get("by_item_id", {}).values():
        documents = list(item.get("documents") or [])
        if documents:
            for ordinal, document in enumerate(documents, start=1):
                records.append(
                    {
                        "ldd_report_id": report_id,
                        "transaction_id": transaction_id,
                        "item_id": item.get("item_id", ""),
                        "section_type": item.get("section_type", ""),
                        "vdr_document_id": document.get("document_id"),
                        "reference_label": document.get("reference", ""),
                        "original_name": document.get("original_name"),
                        "primary_workstream": document.get("primary_workstream"),
                        "workstream_tags": document.get("workstream_tags") or [],
                        "evidence_kind": document.get("evidence_kind"),
                        "directness": document.get("directness"),
                        "confidence": float(item.get("confidence", 0.0) or 0.0),
                        "relevance_score": float(item.get("confidence", 0.0) or 0.0),
                        "source_page": document.get("page_reference"),
                        "chunk_id": document.get("chunk_id"),
                        "source_snippet": document.get("snippet"),
                        "evidence_locator": document.get("locator"),
                        "requires_manual_review": bool(document.get("requires_manual_review")),
                        "is_foreign_workstream": not bool(document.get("include_for_ldd")),
                        "is_unresolved_reference": False,
                        "used_in_draft": True,
                        "used_in_final": used_in_final,
                        "analysis_phase": analysis_phase.upper(),
                        "ordinal": ordinal,
                    }
                )
        base_ordinal = len(documents)
        for offset, unresolved in enumerate(item.get("unresolved_refs") or [], start=1):
            records.append(
                {
                    "ldd_report_id": report_id,
                    "transaction_id": transaction_id,
                    "item_id": item.get("item_id", ""),
                    "section_type": item.get("section_type", ""),
                    "vdr_document_id": None,
                    "reference_label": unresolved,
                    "original_name": None,
                    "primary_workstream": None,
                    "workstream_tags": [],
                    "evidence_kind": "UNRESOLVED_REFERENCE",
                    "directness": None,
                    "confidence": float(item.get("confidence", 0.0) or 0.0),
                    "relevance_score": 0.0,
                    "source_page": None,
                    "chunk_id": None,
                    "source_snippet": None,
                    "evidence_locator": None,
                    "requires_manual_review": False,
                    "is_foreign_workstream": False,
                    "is_unresolved_reference": True,
                    "used_in_draft": True,
                    "used_in_final": used_in_final,
                    "analysis_phase": analysis_phase.upper(),
                    "ordinal": base_ordinal + offset,
                }
            )
    return records


def build_ldd_source_control_qa(
    source_routing: dict[str, Any] | None,
    evidence_ledger: dict[str, Any] | None,
    *,
    sections: list[dict] | None = None,
) -> dict[str, Any]:
    routing_summary = (source_routing or {}).get("summary", {})
    ledger_summary = (evidence_ledger or {}).get("summary", {})
    issues: list[dict[str, Any]] = []

    manual_review_docs = int(routing_summary.get("manual_review_documents", 0) or 0)
    foreign_refs = int(ledger_summary.get("foreign_workstream_refs", 0) or 0)
    unresolved_refs = int(ledger_summary.get("unresolved_refs", 0) or 0)
    missing_evidence = int(ledger_summary.get("items_missing_evidence", 0) or 0)
    missing_direct_evidence = int(ledger_summary.get("items_missing_direct_evidence", 0) or 0)
    placeholder_hits = _collect_placeholder_hits(sections)

    if foreign_refs > 0:
        issues.append(
            _make_issue(
                "foreign_workstream_contamination",
                "critical",
                f"LDD evidence refs contain {foreign_refs} documents routed to a non-LDD workstream.",
                hard_block=True,
            )
        )

    if unresolved_refs > 0:
        issues.append(
            _make_issue(
                "unresolved_evidence_refs",
                "critical",
                f"{unresolved_refs} evidence refs could not be resolved to a VDR document.",
                hard_block=True,
            )
        )

    if missing_evidence > 0:
        issues.append(
            _make_issue(
                "missing_required_evidence",
                "critical",
                f"{missing_evidence} reviewed LDD items still have no evidence backing the output.",
                hard_block=True,
            )
        )

    if missing_direct_evidence > 0:
        issues.append(
            _make_issue(
                "missing_direct_evidence_for_material_issue",
                "major",
                f"{missing_direct_evidence} material issue items rely only on indirect evidence.",
                hard_block=True,
            )
        )

    if manual_review_docs > 0:
        issues.append(
            _make_issue(
                "routing_manual_review_needed",
                "warning",
                f"{manual_review_docs} routed documents remain low-confidence and should be reviewed manually.",
            )
        )

    if placeholder_hits:
        issues.append(
            _make_issue(
                "template_placeholder_remnants",
                "critical",
                f"Found unreplaced placeholder markers in {len(placeholder_hits)} content fields.",
                details=placeholder_hits[:10],
                hard_block=True,
            )
        )

    return {
        "passed": not any(issue.get("hard_block") for issue in issues),
        "issues": issues,
        "summary": {
            "included_documents": int(routing_summary.get("included_for_ldd", 0) or 0),
            "excluded_documents": int(routing_summary.get("excluded_from_ldd", 0) or 0),
            "manual_review_documents": manual_review_docs,
            "foreign_workstream_refs": foreign_refs,
            "unresolved_refs": unresolved_refs,
            "items_missing_evidence": missing_evidence,
            "items_missing_direct_evidence": missing_direct_evidence,
            "placeholder_hits": len(placeholder_hits),
        },
    }


def merge_source_control_qa(
    qa_result: dict[str, Any] | None,
    source_control_qa: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(qa_result or {})
    existing_issues = list(merged.get("issues") or [])
    existing_issues.extend(source_control_qa.get("issues") or [])
    merged["issues"] = existing_issues
    merged["source_controls"] = source_control_qa
    merged["hard_block_codes"] = sorted(
        {
            issue["code"]
            for issue in existing_issues
            if issue.get("hard_block") or issue.get("code") in SOURCE_CONTROL_HARD_BLOCK_CODES
        }
    )
    return merged


def _build_source_lookup(routed_sources: list[RoutedLDDSource]) -> dict[str, RoutedLDDSource]:
    lookup: dict[str, RoutedLDDSource] = {}
    for routed in routed_sources:
        prefixed = f"[VDR:{routed.source.vdr_document_id}]{routed.source.original_name}"
        lookup[prefixed] = routed
        lookup[routed.source.original_name] = routed
        lookup[str(routed.source.vdr_document_id)] = routed
    return lookup


def _resolve_routed_source(reference: str, source_lookup: dict[str, RoutedLDDSource]) -> RoutedLDDSource | None:
    if reference in source_lookup:
        return source_lookup[reference]
    for name, routed in source_lookup.items():
        if reference in name or name in reference:
            return routed
    return None


def _profile_evidence_source(routed: RoutedLDDSource) -> dict[str, Any]:
    ref_lower = routed.source.original_name.lower()
    if any(keyword in ref_lower for keyword in _DIRECT_CONTRACT_KEYWORDS):
        return {"evidence_kind": "DIRECT_CONTRACT", "directness": "DIRECT"}
    if any(keyword in ref_lower for keyword in _DIRECT_LEGAL_KEYWORDS):
        return {"evidence_kind": "DIRECT_LEGAL", "directness": "DIRECT"}
    if any(keyword in ref_lower for keyword in _INDIRECT_CORRESPONDENCE_KEYWORDS):
        return {"evidence_kind": "INDIRECT_CORRESPONDENCE", "directness": "INDIRECT"}
    if any(keyword in ref_lower for keyword in _INDIRECT_SUMMARY_KEYWORDS):
        return {"evidence_kind": "INDIRECT_SUMMARY", "directness": "INDIRECT"}
    if routed.primary_workstream == FDD_WORKSTREAM:
        return {"evidence_kind": "FINANCIAL_SUPPORT", "directness": "INDIRECT"}
    if routed.primary_workstream == VALUATION_WORKSTREAM:
        return {"evidence_kind": "VALUATION_SUPPORT", "directness": "INDIRECT"}
    return {"evidence_kind": "GENERAL_SUPPORT", "directness": "INDIRECT"}


def _select_trace_chunk(item: dict[str, Any], source: VdrSourceFile) -> dict[str, Any]:
    chunks = list((source.parsed.metadata or {}).get("chunks") or [])
    if not chunks:
        text = (source.parsed.text or "").strip()
        if not text:
            return {"chunk_id": None, "page_reference": None, "snippet": None, "locator": None}
        return {
            "chunk_id": None,
            "page_reference": None,
            "snippet": text[:280],
            "locator": {"locator_type": "document"},
        }

    keywords = _build_item_keywords(item)
    best = None
    best_score = -1
    for chunk in chunks:
        text = str(chunk.get("text", "") or "")
        lowered = text.lower()
        score = sum(3 if keyword in lowered else 0 for keyword in keywords if len(keyword) >= 4)
        if item.get("description"):
            score += 5 if str(item["description"]).lower()[:80] in lowered else 0
        if score > best_score:
            best = chunk
            best_score = score

    selected = best or chunks[0]
    return {
        "chunk_id": selected.get("chunk_id"),
        "page_reference": _format_page_reference(selected),
        "snippet": str(selected.get("text", "") or "")[:280] or None,
        "locator": {
            key: value
            for key, value in {
                "locator_type": selected.get("locator_type"),
                "page": selected.get("page"),
                "paragraph": selected.get("paragraph"),
                "sheet": selected.get("sheet"),
                "row": selected.get("row"),
                "ordinal": selected.get("ordinal"),
            }.items()
            if value is not None
        }
        or None,
    }


def _format_page_reference(chunk: dict[str, Any]) -> str | None:
    if chunk.get("page") is not None:
        return f"Page {chunk['page']}"
    if chunk.get("sheet") is not None and chunk.get("row") is not None:
        return f"Sheet {chunk['sheet']} Row {chunk['row']}"
    if chunk.get("paragraph") is not None:
        return f"Paragraph {chunk['paragraph']}"
    if chunk.get("ordinal") is not None:
        return f"Chunk {chunk['ordinal']}"
    return None


def _build_item_keywords(item: dict[str, Any]) -> list[str]:
    raw = [
        str(item.get("name", "") or ""),
        str(item.get("description", "") or ""),
        str(item.get("deal_impact", "") or ""),
        str(item.get("recommendation", "") or ""),
    ]
    keywords: list[str] = []
    for fragment in raw:
        for token in fragment.lower().replace("/", " ").replace(",", " ").split():
            token = token.strip()
            if len(token) >= 4 and token not in keywords:
                keywords.append(token)
    return keywords[:12]


def _requires_evidence(item: dict[str, Any]) -> bool:
    status = item.get("status")
    return status in {"ISSUE", "OK"}


def _collect_placeholder_hits(sections: list[dict] | None) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for section in sections or []:
        for item in section.get("items", []) or []:
            for field_name in ("description", "deal_impact", "recommendation"):
                value = str(item.get(field_name, "") or "")
                for pattern in _PLACEHOLDER_PATTERNS:
                    if pattern in value:
                        hits.append(
                            {
                                "item_id": str(item.get("item_id", "")),
                                "field": field_name,
                                "pattern": pattern,
                            }
                        )
                        break
    return hits


def _make_issue(
    code: str,
    severity: str,
    message: str,
    *,
    details: list[dict[str, Any]] | None = None,
    hard_block: bool = False,
) -> dict[str, Any]:
    issue = {
        "code": code,
        "severity": severity,
        "message": message,
        "hard_block": hard_block,
    }
    if details:
        issue["details"] = details
    return issue
