from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.enums import LDDIssueLevel, LDDItemStatus, LDDReportType
from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter
from app.ralph.generators.ldd.slot_fill import LDDTemplateSlotFillEngine, TemplateRegistry
from app.schemas.ldd_report import DEFAULT_LDD_SECTIONS

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "ldd_slotfill"


def _make_report(*, report_type=LDDReportType.FULL):
    sections = copy.deepcopy(DEFAULT_LDD_SECTIONS)
    states = [
        (LDDItemStatus.ISSUE, LDDIssueLevel.CRITICAL),
        (LDDItemStatus.ISSUE, LDDIssueLevel.HIGH),
        (LDDItemStatus.OK, None),
        (LDDItemStatus.PENDING, None),
        (LDDItemStatus.NA, None),
    ]

    idx = 0
    for section in sections:
        for item in section["items"]:
            status, level = states[idx % len(states)]
            idx += 1
            item["status"] = status
            item["issue_level"] = level
            item["description"] = f"{item['name']} 관련 확인사항 요약"
            item["deal_impact"] = f"{item['name']} 이슈가 거래 조건 및 일정에 미치는 영향"
            item["recommendation"] = f"{item['name']} 관련 추가 확인 및 계약 반영 권고"
            item["evidence_refs"] = [f"{item['item_id']}.pdf"]
            item["confidence"] = 0.82
            if status == LDDItemStatus.ISSUE:
                item["rfi_required"] = True
                item["rfi_number"] = f"{item['item_id']}-001"

    return SimpleNamespace(
        title="LDD Template SlotFill Test",
        target_company="테스트주식회사",
        report_type=report_type,
        deal_type="STOCK_ACQUISITION",
        template_type="DEFAULT",
        dd_period="2026-03-01 ~ 2026-03-15",
        law_firm="테스트로펌",
        vdr_source=True,
        sections=sections,
        narrative_sections={},
    )


def test_slotfill_registry_loads_all_default_sections():
    registry = TemplateRegistry(TEMPLATE_DIR)
    expected = {
        "governance",
        "capital",
        "contracts",
        "litigation",
        "labor",
        "ip",
        "real_estate",
        "permits",
        "tax",
        "data_it",
    }
    assert set(registry.section_ids) == expected
    assert registry.base_blocks.get("scope_notice")


@pytest.mark.asyncio
async def test_slotfill_engine_builds_blocks_for_all_sections():
    report = _make_report()
    engine = LDDTemplateSlotFillEngine(TEMPLATE_DIR)

    result = await engine.build_narrative_sections(report)

    assert set(result.keys()) == {section["section_type"] for section in report.sections}
    for items in result.values():
        assert items
        for item in items:
            assert item["blocks"]
            assert all("{{" not in block["content"] for block in item["blocks"])
            assert {block["block_type"] for block in item["blocks"]} >= {"FACTS", "ANALYSIS", "RECOMMENDATION"}


@pytest.mark.asyncio
async def test_slotfill_engine_filters_redflag_items():
    report = _make_report(report_type=LDDReportType.REDFLAG)
    report.sections = [copy.deepcopy(DEFAULT_LDD_SECTIONS[0])]
    items = report.sections[0]["items"]

    items[0]["status"] = LDDItemStatus.ISSUE
    items[0]["issue_level"] = LDDIssueLevel.CRITICAL
    items[0]["description"] = "Critical issue"
    items[0]["deal_impact"] = "Critical impact"
    items[0]["recommendation"] = "Critical recommendation"

    items[1]["status"] = LDDItemStatus.ISSUE
    items[1]["issue_level"] = LDDIssueLevel.LOW
    items[1]["description"] = "Low issue"
    items[1]["deal_impact"] = "Low impact"
    items[1]["recommendation"] = "Low recommendation"

    items[2]["status"] = LDDItemStatus.OK
    items[2]["issue_level"] = None
    items[2]["description"] = "OK"

    engine = LDDTemplateSlotFillEngine(TEMPLATE_DIR)
    result = await engine.build_narrative_sections(report)

    governance_items = result["GOVERNANCE"]
    assert len(governance_items) == 1
    assert governance_items[0]["item_id"] == items[0]["item_id"]


@pytest.mark.asyncio
async def test_slotfill_output_converts_to_law_firm_structure():
    report = _make_report()
    engine = LDDTemplateSlotFillEngine(TEMPLATE_DIR)
    narratives = await engine.build_narrative_sections(report)

    adapter = LawFirmNarrativeAdapter()
    converted = adapter.convert_chapter(narratives["GOVERNANCE"], "I")

    assert converted
    assert converted[0].status_section
    assert converted[0].review_section
    assert converted[0].recommendation_section
