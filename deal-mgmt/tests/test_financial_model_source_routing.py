from __future__ import annotations

import uuid

from app.models.enums import (
    FinancialModelType,
    FMChecklistCategory,
    FMChecklistItemStatus,
    VdrFolderCategory,
)
from app.models.financial_model import FMChecklistItem
from app.ralph.parsers.base import ParsedFile
from app.services.financial_model_service import (
    _build_financial_model_source_routing,
    _get_financial_model_target_workstreams,
    _seed_financial_model_checklist_from_sources,
)
from app.services.text_extraction_service import VdrSourceFile
from app.services.workstream_router_service import is_source_allowed_for_any_workstream, route_vdr_sources


def _make_source(
    *,
    name: str,
    category: VdrFolderCategory,
    text: str,
    chunks: list[dict] | None = None,
) -> VdrSourceFile:
    parsed = ParsedFile(
        source_path=f"/tmp/{name}",
        file_type=name.rsplit(".", 1)[-1],
        text=text,
        metadata={"chunks": chunks or []},
    )
    return VdrSourceFile(
        parsed=parsed,
        vdr_document_id=uuid.uuid4(),
        vdr_folder_id=uuid.uuid4(),
        vdr_category=category,
        original_name=name,
    )


def _make_item(
    *,
    title: str,
    category: FMChecklistCategory,
    field_type: str,
    unit: str | None,
) -> FMChecklistItem:
    return FMChecklistItem(
        id=uuid.uuid4(),
        checklist_id=uuid.uuid4(),
        category=category,
        order_index=0,
        title=title,
        description=title,
        status=FMChecklistItemStatus.AUTO_GENERATED,
        unit=unit,
        field_type=field_type,
    )


def test_financial_model_source_routing_includes_fdd_and_valuation_docs() -> None:
    financial_doc = _make_source(
        name="qoe_working_capital.xlsx",
        category=VdrFolderCategory.FINANCIAL,
        text="Accounts receivable days (DSO) are 45 days and EBITDA margin is 18%.",
    )
    valuation_doc = _make_source(
        name="valuation_bridge.pdf",
        category=VdrFolderCategory.MARKET_RESEARCH,
        text="Exit Multiple (EV/EBITDA) is 6.5x based on peer valuation analysis.",
    )

    routed_sources = route_vdr_sources([financial_doc, valuation_doc])
    summary = _build_financial_model_source_routing(
        routed_sources,
        _get_financial_model_target_workstreams(FinancialModelType.FULL),
    )

    assert summary["summary"]["target_workstreams"] == ["FDD", "VALUATION"]
    assert summary["summary"]["included_for_financial_model"] == 2
    assert all(document["include_for_financial_model"] for document in summary["documents"])


def test_seed_financial_model_checklist_from_sources_prefills_fdd_item() -> None:
    financial_doc = _make_source(
        name="qoe_working_capital.xlsx",
        category=VdrFolderCategory.FINANCIAL,
        text="Accounts receivable days (DSO) are 45 days based on the latest QoE review.",
        chunks=[
            {
                "chunk_id": "sheet-1-row-4",
                "locator_type": "sheet_row",
                "sheet": "NWC",
                "row": 4,
                "ordinal": 1,
                "text": "Accounts receivable days (DSO) are 45 days based on the latest QoE review.",
            }
        ],
    )
    routed_sources = route_vdr_sources([financial_doc])
    relevant_sources = [
        routed
        for routed in routed_sources
        if is_source_allowed_for_any_workstream(
            routed,
            _get_financial_model_target_workstreams(FinancialModelType.PROJECTION),
        )
    ]
    item = _make_item(
        title="매출채권 회전일수 (DSO)",
        category=FMChecklistCategory.NWC_ASSUMPTIONS,
        field_type="number",
        unit="일",
    )

    seeded_count = _seed_financial_model_checklist_from_sources([item], relevant_sources)

    assert seeded_count == 1
    assert item.auto_value == "45"
    assert item.source_vdr_doc_name == "qoe_working_capital.xlsx"
    assert item.source_location == "Sheet NWC Row 4"
    assert item.confidence is not None


def test_seed_financial_model_checklist_from_sources_prefills_valuation_item() -> None:
    valuation_doc = _make_source(
        name="valuation_bridge.pdf",
        category=VdrFolderCategory.MARKET_RESEARCH,
        text="Exit Multiple (EV/EBITDA) is 6.5x based on peer valuation analysis.",
        chunks=[
            {
                "chunk_id": "page-7",
                "locator_type": "page",
                "page": 7,
                "ordinal": 1,
                "text": "Exit Multiple (EV/EBITDA) is 6.5x based on peer valuation analysis.",
            }
        ],
    )
    routed_sources = route_vdr_sources([valuation_doc])
    relevant_sources = [
        routed
        for routed in routed_sources
        if is_source_allowed_for_any_workstream(
            routed,
            _get_financial_model_target_workstreams(FinancialModelType.DCF),
        )
    ]
    item = _make_item(
        title="Exit Multiple (EV/EBITDA)",
        category=FMChecklistCategory.DCF_PARAMETERS,
        field_type="number",
        unit="x",
    )

    seeded_count = _seed_financial_model_checklist_from_sources([item], relevant_sources)

    assert seeded_count == 1
    assert item.auto_value == "6.5x"
    assert item.source_vdr_doc_name == "valuation_bridge.pdf"
    assert item.source_location == "Page 7"
