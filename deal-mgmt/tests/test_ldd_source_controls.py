from __future__ import annotations

import uuid

from app.models.enums import VdrFolderCategory
from app.ralph.parsers.base import ParsedFile
from app.services.ldd_source_controls import (
    build_ldd_evidence_ledger,
    build_ldd_evidence_records,
    build_ldd_source_control_qa,
    merge_source_control_qa,
    route_vdr_sources_for_ldd,
)
from app.services.text_extraction_service import VdrSourceFile
from app.services.workstream_router_service import (
    WorkstreamRoutingOverride,
    filter_sources_for_workstream,
    route_vdr_sources,
)


def _make_source(
    *,
    name: str,
    category: VdrFolderCategory,
    text: str,
    ddrl_sections: list[str] | None = None,
    chunks: list[dict] | None = None,
) -> VdrSourceFile:
    parsed = ParsedFile(
        source_path=f"/tmp/{name}",
        file_type=name.rsplit(".", 1)[-1],
        text=text,
        ddrl_sections=ddrl_sections or [],
        metadata={"chunks": chunks or []},
    )
    return VdrSourceFile(
        parsed=parsed,
        vdr_document_id=uuid.uuid4(),
        vdr_folder_id=uuid.uuid4(),
        vdr_category=category,
        original_name=name,
    )


def test_shared_router_filters_sources_for_target_workstream() -> None:
    legal_doc = _make_source(
        name="shareholders_agreement.pdf",
        category=VdrFolderCategory.LEGAL,
        text="change of control agreement and board approval",
    )
    financial_doc = _make_source(
        name="2024_financial_statements.xlsx",
        category=VdrFolderCategory.FINANCIAL,
        text="EBITDA revenue cash flow working capital",
    )
    common_doc = _make_source(
        name="management_presentation.pdf",
        category=VdrFolderCategory.COMMERCIAL,
        text="management presentation summary overview",
    )

    routed = route_vdr_sources([legal_doc, financial_doc, common_doc])
    ldd_sources = filter_sources_for_workstream(routed, "LDD")

    assert {source.original_name for source in ldd_sources} == {
        "shareholders_agreement.pdf",
        "management_presentation.pdf",
    }


def test_route_vdr_sources_for_ldd_filters_mixed_vdr_content() -> None:
    legal_doc = _make_source(
        name="shareholders_agreement.pdf",
        category=VdrFolderCategory.LEGAL,
        text="change of control agreement and corporate approval mechanics",
        ddrl_sections=["CONTRACTS"],
    )
    financial_doc = _make_source(
        name="2024_financial_statements.xlsx",
        category=VdrFolderCategory.FINANCIAL,
        text="EBITDA revenue cash flow working capital",
        ddrl_sections=["CAPITAL"],
    )
    valuation_doc = _make_source(
        name="peer_multiple_valuation_report.pdf",
        category=VdrFolderCategory.MARKET_RESEARCH,
        text="valuation multiple peer market report",
    )
    common_doc = _make_source(
        name="management_presentation.pdf",
        category=VdrFolderCategory.COMMERCIAL,
        text="management presentation summary overview for bidders",
    )

    routed, summary = route_vdr_sources_for_ldd([legal_doc, financial_doc, valuation_doc, common_doc])
    route_map = {entry.source.original_name: entry for entry in routed}

    assert route_map["shareholders_agreement.pdf"].primary_workstream == "LDD"
    assert route_map["shareholders_agreement.pdf"].include_for_ldd is True
    assert route_map["2024_financial_statements.xlsx"].primary_workstream == "FDD"
    assert route_map["2024_financial_statements.xlsx"].include_for_ldd is False
    assert route_map["peer_multiple_valuation_report.pdf"].primary_workstream == "VALUATION"
    assert route_map["peer_multiple_valuation_report.pdf"].include_for_ldd is False
    assert route_map["management_presentation.pdf"].primary_workstream == "COMMON"
    assert route_map["management_presentation.pdf"].include_for_ldd is True

    assert summary["summary"]["included_for_ldd"] == 2
    assert summary["summary"]["excluded_from_ldd"] == 2


def test_route_vdr_sources_for_ldd_applies_manual_override() -> None:
    custom_doc = _make_source(
        name="board_pack_notes.txt",
        category=VdrFolderCategory.CUSTOM,
        text="General overview only.",
    )

    routed, summary = route_vdr_sources_for_ldd(
        [custom_doc],
        routing_overrides={
            custom_doc.vdr_document_id: WorkstreamRoutingOverride(
                primary_workstream="LDD",
                workstream_tags=("LDD",),
                override_note="Reviewed by legal team",
            )
        },
    )

    assert routed[0].is_override is True
    assert routed[0].requires_manual_review is False
    assert routed[0].include_for_ldd is True
    assert routed[0].primary_workstream == "LDD"
    assert summary["summary"]["overridden_documents"] == 1
    assert summary["documents"][0]["is_override"] is True


def test_build_ldd_evidence_ledger_tracks_traceability_and_foreign_refs() -> None:
    legal_doc = _make_source(
        name="shareholders_agreement.pdf",
        category=VdrFolderCategory.LEGAL,
        text="shareholders agreement requires prior investor consent before control transfer",
        ddrl_sections=["CONTRACTS"],
        chunks=[
            {
                "chunk_id": "page-3",
                "locator_type": "page",
                "page": 3,
                "ordinal": 3,
                "text": "Prior investor consent is required before any control transfer under the shareholders agreement.",
            }
        ],
    )
    financial_doc = _make_source(
        name="2024_financial_statements.xlsx",
        category=VdrFolderCategory.FINANCIAL,
        text="financial statements and revenue bridge",
        chunks=[
            {
                "chunk_id": "sheet-1-row-2",
                "locator_type": "sheet_row",
                "sheet": "P&L",
                "row": 2,
                "ordinal": 1,
                "text": "Revenue bridge and EBITDA analysis",
            }
        ],
    )
    routed, routing_summary = route_vdr_sources_for_ldd([legal_doc, financial_doc])
    sections = [
        {
            "section_type": "CONTRACTS",
            "items": [
                {
                    "item_id": "CONTRACT-04",
                    "name": "Change of Control Approval",
                    "status": "ISSUE",
                    "issue_level": "CRITICAL",
                    "confidence": 0.81,
                    "description": "Investor consent remains unresolved before control transfer.",
                    "rfi_required": False,
                    "evidence_refs": [
                        "shareholders_agreement.pdf",
                        "2024_financial_statements.xlsx",
                        "missing_note.pdf",
                    ],
                }
            ],
        }
    ]

    ledger = build_ldd_evidence_ledger(sections, routed)
    item = ledger["by_item_id"]["CONTRACT-04"]
    source_qa = build_ldd_source_control_qa(routing_summary, ledger, sections=sections)

    assert item["direct_evidence_count"] == 1
    assert item["foreign_workstream_refs"] == ["2024_financial_statements.xlsx"]
    assert item["unresolved_refs"] == ["missing_note.pdf"]
    assert item["documents"][0]["page_reference"] == "Page 3"
    assert "investor consent" in item["documents"][0]["snippet"].lower()
    assert ledger["summary"]["foreign_workstream_refs"] == 1
    assert ledger["summary"]["unresolved_refs"] == 1
    assert source_qa["passed"] is False
    assert any(issue["code"] == "foreign_workstream_contamination" for issue in source_qa["issues"])
    assert any(issue["code"] == "unresolved_evidence_refs" for issue in source_qa["issues"])


def test_build_ldd_evidence_records_emits_normalized_rows() -> None:
    ledger = {
        "by_item_id": {
            "CONTRACT-04": {
                "item_id": "CONTRACT-04",
                "section_type": "CONTRACTS",
                "confidence": 0.81,
                "unresolved_refs": ["missing_note.pdf"],
                "documents": [
                    {
                        "reference": "shareholders_agreement.pdf",
                        "document_id": str(uuid.uuid4()),
                        "original_name": "shareholders_agreement.pdf",
                        "primary_workstream": "LDD",
                        "workstream_tags": ["LDD"],
                        "evidence_kind": "DIRECT_CONTRACT",
                        "directness": "DIRECT",
                        "page_reference": "Page 3",
                        "chunk_id": "page-3",
                        "snippet": "Prior investor consent is required.",
                        "locator": {"locator_type": "page", "page": 3},
                        "requires_manual_review": False,
                        "include_for_ldd": True,
                    }
                ],
            }
        }
    }

    records = build_ldd_evidence_records(
        transaction_id=str(uuid.uuid4()),
        report_id=str(uuid.uuid4()),
        evidence_ledger=ledger,
        analysis_phase="FINAL",
    )

    assert len(records) == 2

    evidence_record = next(record for record in records if not record["is_unresolved_reference"])
    unresolved_record = next(record for record in records if record["is_unresolved_reference"])

    assert evidence_record["item_id"] == "CONTRACT-04"
    assert evidence_record["source_page"] == "Page 3"
    assert evidence_record["chunk_id"] == "page-3"
    assert evidence_record["used_in_final"] is True

    assert unresolved_record["item_id"] == "CONTRACT-04"
    assert unresolved_record["reference_label"] == "missing_note.pdf"
    assert unresolved_record["evidence_kind"] == "UNRESOLVED_REFERENCE"
    assert unresolved_record["used_in_final"] is True


def test_source_control_qa_marks_placeholder_and_missing_evidence_as_hard_blocks() -> None:
    sections = [
        {
            "section_type": "PERMITS",
            "items": [
                {
                    "item_id": "PERMIT-01",
                    "name": "Permit",
                    "status": "ISSUE",
                    "issue_level": "HIGH",
                    "description": "[이곳에 텍스트 입력]",
                    "deal_impact": "",
                    "recommendation": "",
                    "confidence": 0.7,
                    "evidence_refs": [],
                }
            ],
        }
    ]
    qa = build_ldd_source_control_qa(
        {"summary": {"included_for_ldd": 1, "excluded_from_ldd": 0, "manual_review_documents": 0}},
        {
            "summary": {
                "foreign_workstream_refs": 0,
                "unresolved_refs": 0,
                "items_missing_evidence": 1,
                "items_missing_direct_evidence": 0,
            }
        },
        sections=sections,
    )

    codes = {issue["code"] for issue in qa["issues"]}
    assert qa["passed"] is False
    assert "core_section_coverage_gap" in codes
    assert "missing_required_evidence" in codes
    assert "template_placeholder_remnants" in codes
    assert all(issue.get("hard_block") for issue in qa["issues"] if issue["code"] in codes)


def test_source_control_qa_blocks_common_only_and_manual_review_inputs() -> None:
    qa = build_ldd_source_control_qa(
        {
            "summary": {"included_for_ldd": 2, "excluded_from_ldd": 0, "manual_review_documents": 2},
            "documents": [
                {
                    "document_id": str(uuid.uuid4()),
                    "original_name": "management_presentation.pdf",
                    "primary_workstream": "COMMON",
                    "workstream_tags": ["COMMON"],
                    "confidence": 0.42,
                    "requires_manual_review": True,
                    "include_for_ldd": True,
                },
                {
                    "document_id": str(uuid.uuid4()),
                    "original_name": "management_qna_notes.pdf",
                    "primary_workstream": "COMMON",
                    "workstream_tags": ["COMMON"],
                    "confidence": 0.48,
                    "requires_manual_review": True,
                    "include_for_ldd": True,
                },
            ],
        },
        {
            "summary": {
                "foreign_workstream_refs": 0,
                "unresolved_refs": 0,
                "items_missing_evidence": 0,
                "items_missing_direct_evidence": 0,
            },
            "by_section": {
                "GOVERNANCE": [{"evidence_count": 1}],
                "CAPITAL": [{"evidence_count": 1}],
                "CONTRACTS": [{"evidence_count": 1}],
            },
        },
        sections=[
            {"section_type": "GOVERNANCE", "items": [{"item_id": "G-1", "status": "ISSUE", "recommendation": "Collect board minutes."}]},
            {"section_type": "CAPITAL", "items": [{"item_id": "C-1", "status": "ISSUE", "recommendation": "Collect cap table support."}]},
            {"section_type": "CONTRACTS", "items": [{"item_id": "K-1", "status": "ISSUE", "recommendation": "Collect executed SHA."}]},
        ],
    )

    codes = {issue["code"] for issue in qa["issues"]}
    assert qa["passed"] is False
    assert "routing_manual_review_block" in codes
    assert "common_only_ldd_inputs" in codes


def test_source_control_qa_blocks_recommendation_summary_mismatch() -> None:
    qa = build_ldd_source_control_qa(
        {
            "summary": {"included_for_ldd": 3, "excluded_from_ldd": 0, "manual_review_documents": 0},
            "documents": [
                {
                    "document_id": str(uuid.uuid4()),
                    "original_name": "governance_board_minutes.pdf",
                    "primary_workstream": "LDD",
                    "workstream_tags": ["LDD"],
                    "confidence": 0.87,
                    "requires_manual_review": False,
                    "include_for_ldd": True,
                },
                {
                    "document_id": str(uuid.uuid4()),
                    "original_name": "shareholders_agreement.pdf",
                    "primary_workstream": "LDD",
                    "workstream_tags": ["LDD"],
                    "confidence": 0.92,
                    "requires_manual_review": False,
                    "include_for_ldd": True,
                },
                {
                    "document_id": str(uuid.uuid4()),
                    "original_name": "cap_table.xlsx",
                    "primary_workstream": "LDD",
                    "workstream_tags": ["LDD"],
                    "confidence": 0.91,
                    "requires_manual_review": False,
                    "include_for_ldd": True,
                },
            ],
        },
        {
            "summary": {
                "foreign_workstream_refs": 0,
                "unresolved_refs": 0,
                "items_missing_evidence": 0,
                "items_missing_direct_evidence": 0,
            },
            "by_section": {
                "GOVERNANCE": [{"evidence_count": 1}],
                "CAPITAL": [{"evidence_count": 1}],
                "CONTRACTS": [{"evidence_count": 1}],
            },
        },
        sections=[
            {"section_type": "GOVERNANCE", "items": [{"item_id": "G-1", "status": "ISSUE", "recommendation": "Collect the last two years of board minutes before signing."}]},
            {"section_type": "CAPITAL", "items": [{"item_id": "C-1", "status": "ISSUE", "recommendation": "Update the cap table and option dilution schedule."}]},
            {"section_type": "CONTRACTS", "items": [{"item_id": "K-1", "status": "ISSUE", "recommendation": "Document the waiver as an express closing condition."}]},
        ],
        qa_result={
            "summary_rows": [
                {
                    "chapter_number": "III",
                    "chapter_title": "Contracts",
                    "recommendation": "Prepare a post-closing branding integration memo.",
                }
            ]
        },
    )

    codes = {issue["code"] for issue in qa["issues"]}
    assert qa["passed"] is False
    assert "recommendation_summary_mismatch" in codes


def test_merge_source_control_qa_preserves_existing_issues() -> None:
    source_qa = {
        "passed": False,
        "issues": [
            {
                "code": "foreign_workstream_contamination",
                "severity": "critical",
                "message": "blocked",
                "hard_block": True,
            }
        ],
        "summary": {"foreign_workstream_refs": 1},
    }

    merged = merge_source_control_qa(
        {"overall_score": 4.0, "issues": [{"code": "draft_warning", "severity": "warning", "message": "warn"}]},
        source_qa,
    )

    assert merged["overall_score"] == 4.0
    assert len(merged["issues"]) == 2
    assert merged["source_controls"]["summary"]["foreign_workstream_refs"] == 1
    assert "foreign_workstream_contamination" in merged["hard_block_codes"]
