from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.enums import LDDIssueLevel, LDDItemStatus, LDDReportType
from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrativeAdapter
from app.ralph.generators.ldd.project_green_style import (
    ProjectGreenToneContext,
    choose_project_green_modality,
    normalize_project_green_text,
)
from app.ralph.generators.ldd.slot_fill import LDDTemplateSlotFillEngine, TemplateRegistry
from app.ralph.generators.ldd.slot_fill.loader import BaseBlocks, ConditionalBlock, SectionTemplate
from app.ralph.generators.ldd.slot_fill.renderer import LDDTemplateRenderer
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


def test_renderer_resolves_base_refs_inside_conditional_blocks():
    renderer = LDDTemplateRenderer()
    template = SectionTemplate(
        section_id="contracts",
        body="[[ANALYSIS]] 본문입니다.",
        conditional_blocks=[
            ConditionalBlock(
                condition="status == 'PENDING'",
                insert_after="analysis_sentence",
                text="{{@source_gap_notice}} 추가 자료 확보가 필요합니다.",
            )
        ],
    )

    rendered = renderer.render(
        template,
        {"status": "PENDING"},
        base_blocks=BaseBlocks(blocks={"source_gap_notice": "자료 공백이 있는 영역은 잠정 판단으로 유지합니다."}),
    )

    assert "{{@" not in rendered
    assert "자료 공백이 있는 영역은 잠정 판단으로 유지합니다." in rendered

def test_project_green_modality_selects_by_evidence_strength():
    strong = choose_project_green_modality(
        ProjectGreenToneContext(
            evidence_count=2,
            confidence=0.9,
            status="ISSUE",
            rfi_required=False,
            evidence_refs=("shareholders_agreement.pdf", "permit_license.pdf"),
        )
    )
    medium = choose_project_green_modality(
        ProjectGreenToneContext(
            evidence_count=1,
            confidence=0.62,
            status="ISSUE",
            rfi_required=False,
            evidence_refs=("management_presentation.pdf",),
        )
    )
    weak = choose_project_green_modality(
        ProjectGreenToneContext(
            evidence_count=0,
            confidence=0.2,
            status="ISSUE",
            rfi_required=True,
            evidence_refs=(),
        )
    )

    assert strong == "판단됩니다"
    assert medium == "보입니다"
    assert weak == "사료됩니다"


def test_project_green_normalization_applies_selected_modality():
    assert normalize_project_green_text("관할관청의 사전승인이 필요한 것으로 보임.", modality="판단됩니다") == (
        "관할관청의 사전승인이 필요한 것으로 판단됩니다."
    )
    assert normalize_project_green_text("계약상 사전 동의 절차가 필요한 것으로 판단됨.", modality="보입니다") == (
        "계약상 사전 동의 절차가 필요한 것으로 보입니다."
    )
    assert normalize_project_green_text("추가 자료 확인이 필요한 것으로 보임.", modality="사료됩니다") == (
        "추가 자료 확인이 필요한 것으로 사료됩니다."
    )
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
async def test_slotfill_engine_compacts_section_preamble_after_first_item():
    report = _make_report()
    engine = LDDTemplateSlotFillEngine(TEMPLATE_DIR)

    result = await engine.build_narrative_sections(report)

    governance_items = result["GOVERNANCE"]
    first_facts = next(block["content"] for block in governance_items[0]["blocks"] if block["block_type"] == "FACTS")
    second_facts = next(block["content"] for block in governance_items[1]["blocks"] if block["block_type"] == "FACTS")
    first_analysis = next(
        block["content"] for block in governance_items[0]["blocks"] if block["block_type"] == "ANALYSIS"
    )
    second_analysis = next(
        block["content"] for block in governance_items[1]["blocks"] if block["block_type"] == "ANALYSIS"
    )

    assert first_facts.startswith("본 문안은 현재까지")
    assert second_facts.startswith("당사는 테스트주식회사의")
    assert first_analysis.startswith("본 항목에서는 설립")
    assert second_analysis.startswith("확인된 사항은")


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
