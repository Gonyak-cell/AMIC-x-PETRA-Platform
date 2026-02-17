"""Report Service - FDD 보고서 IR 생성.

모든 분석 결과를 수집하여 Report IR을 생성합니다.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.industry import get_fdd_industry_module_safe
from app.models import Deal, Issue, NetDebtCalculation, NWCCalculation, QoECalculation
from app.models.debt import DebtStatus
from app.models.nwc import NWCStatus
from app.models.qoe import QoEStatus
from app.renderers.report_builder import (
    CoverBlock,
    ReportIR,
    ReportMetadata,
    build_fx_summary_block,
    build_issue_block,
    build_issue_summary_table_block,
    build_kpi_block,
    build_methodology_block,
    build_net_debt_schedule_block,
    build_nwc_definition_table_block,
    build_nwc_peg_table_block,
    build_qoe_adjustments_table_block,
    build_qoe_table_block,
    build_scope_block,
    build_text_block,
    report_ir_to_dict,
)

logger = get_logger(__name__)


def _build_multi_entity_sections(
    db: Session,
    deal_id: UUID,
    sections: list,
) -> None:
    """멀티 엔티티 딜에 대한 보고서 섹션을 추가한다.

    엔티티가 2개 이상인 딜에 대해:
    - 엔티티별 금액 breakdown 테이블
    - FX 환율 요약 테이블
    - 연결 조정(IC 제거) 요약 테이블
    """
    from sqlalchemy import select

    from app.models.entity import Entity, EntityType
    from app.models.exchange_rate import ExchangeRate

    entities = list(
        db.scalars(
            select(Entity).where(
                Entity.deal_id == deal_id,
                Entity.is_active.is_(True),
                Entity.entity_type != EntityType.CONSOLIDATED,
            )
        )
    )

    if len(entities) < 2:
        return

    # 1. Entity Breakdown
    entity_names = [e.name for e in entities]
    entity_rows = []
    for entity in entities:
        entity_rows.append(
            {
                "category": entity.name,
                "entity_type": entity.entity_type.value,
                "currency": entity.functional_currency,
                "ownership": f"{entity.ownership_pct or 100:.2f}%",
            }
        )

    # Entity structure overview table
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    entity_overview = TableBlock(
        title="Entity Structure",
        columns=[
            TableColumn(
                key="category", header="Entity", width=2.5, align=AlignType.LEFT
            ),
            TableColumn(
                key="entity_type", header="Type", width=1.2, align=AlignType.CENTER
            ),
            TableColumn(
                key="currency", header="Currency", width=1.0, align=AlignType.CENTER
            ),
            TableColumn(
                key="ownership", header="Ownership", width=1.0, align=AlignType.RIGHT
            ),
        ],
        rows=entity_rows,
        zebra_stripe=True,
    )
    sections.append(entity_overview)

    # 2. FX Rate Summary
    fx_rates = list(
        db.scalars(select(ExchangeRate).where(ExchangeRate.deal_id == deal_id))
    )
    if fx_rates:
        fx_rows = []
        for rate in fx_rates:
            fx_rows.append(
                {
                    "pair": f"{rate.from_currency}/{rate.to_currency}",
                    "rate_type": rate.rate_type.value,
                    "rate": f"{rate.rate:,.4f}",
                    "effective_date": rate.effective_date.isoformat(),
                    "source": rate.source.value,
                }
            )
        sections.append(build_fx_summary_block("Exchange Rates Applied", fx_rows))


def _format_currency(value: Decimal | None, unit: str = "백만원") -> str:
    """금액을 표시 형식으로 변환."""
    if value is None:
        return "-"
    formatted = f"{value:,.0f}"
    return formatted


def _decimal_to_str(value: Decimal | None) -> str:
    """Decimal을 문자열로 변환."""
    if value is None:
        return ""
    return str(value)


def build_report_ir(
    db: Session,
    deal_id: UUID,
    include_qoe: bool = True,
    include_nwc: bool = True,
    include_debt: bool = True,
    include_issues: bool = True,
    use_llm_narratives: bool = False,
    use_template_slotfill: bool = False,
) -> ReportIR:
    """Deal에 대한 FDD Report IR을 생성.

    Args:
        db: DB 세션
        deal_id: Deal UUID
        include_qoe: QoE 섹션 포함 여부
        include_nwc: NWC 섹션 포함 여부
        include_debt: Net Debt 섹션 포함 여부
        include_issues: Issue Log 포함 여부
        use_llm_narratives: LLM 내러티브 생성 사용 여부

    Returns:
        ReportIR 인스턴스
    """
    # Deal 조회
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise NotFoundError(resource="Deal", resource_id=str(deal_id))

    # 산업 컨텍스트 로드
    industry_id = deal.industry.value if deal.industry else "general"
    industry_module = get_fdd_industry_module_safe(industry_id)
    industry_ctx = industry_module.get_context()

    # 한국 오버레이 로드
    korea_overlay = industry_module.get_korea_overlay()

    # LLM 내러티브 생성기 (선택적)
    narrator = None
    if use_llm_narratives:
        try:
            from app.services.llm.routing import create_fdd_model_router
            from app.services.report.narrative_generator import FDDNarrativeGenerator

            router = create_fdd_model_router()
            if router.available_providers:
                industry_narrative_ctx = industry_module.format_narrative_context()
                # 한국 오버레이 컨텍스트를 LLM에도 전달
                if korea_overlay:
                    overlay_ctx = korea_overlay.format_overlay_context()
                    if overlay_ctx:
                        industry_narrative_ctx += f"\n\n{overlay_ctx}"
                narrator = FDDNarrativeGenerator(
                    router,
                    industry_context=industry_narrative_ctx,
                    industry_id=industry_id,
                )
        except Exception as e:
            logger.warning(f"LLM narrator init failed, skipping narratives: {e}")

    # 메타데이터
    metadata = ReportMetadata(
        deal_id=str(deal_id),
        deal_name=deal.name,
        generated_at=datetime.utcnow().isoformat() + "Z",
        version="1.0",
        engine_versions={"qoe": "0.1.0", "nwc": "0.1.0", "debt": "0.1.0"},
    )

    sections = []

    # 1. Cover Slide
    sections.append(
        CoverBlock(
            deal_name=deal.name,
            deal_type="Financial Due Diligence",
            target_name=deal.name,
            date=datetime.utcnow().date(),
            prepared_by="Auto FDD",
            confidentiality="CONFIDENTIAL",
        )
    )

    # 2. Scope & Definitions
    scope_items = [
        ("period", "Analysis Period", "FY2024 - FY2025"),
        ("entity", "Target Entity", deal.name),
        ("industry", "Industry", f"{industry_module.industry_name_en} ({industry_module.industry_name_kr})"),
        ("currency", "Currency", "KRW (백만원)"),
        ("data_sources", "Data Sources", "Trial Balance, General Ledger"),
    ]
    definitions = {
        "EBITDA": "Earnings Before Interest, Taxes, Depreciation, and Amortization",
        "Adjusted EBITDA": "EBITDA adjusted for non-recurring and non-operating items",
        "NWC": "Net Working Capital - Current Assets less Current Liabilities (excluding cash and debt)",
        "Net Debt": "Total Debt less Cash and Cash Equivalents",
    }
    sections.append(build_scope_block(scope_items, definitions))

    # 3. KPI Summary
    kpis = []

    # QoE 데이터 수집
    qoe_calc = None
    if include_qoe:
        qoe_calc = (
            db.query(QoECalculation)
            .filter(
                QoECalculation.deal_id == deal_id,
                QoECalculation.status == QoEStatus.APPROVED,
            )
            .order_by(QoECalculation.created_at.desc())
            .first()
        )
        if qoe_calc:
            kpis.append(
                (
                    "Reported EBITDA",
                    _format_currency(qoe_calc.reported_ebitda),
                    "백만원",
                )
            )
            kpis.append(
                (
                    "Adjusted EBITDA",
                    _format_currency(qoe_calc.adjusted_ebitda),
                    "백만원",
                )
            )

    # NWC 데이터 수집
    nwc_calc = None
    if include_nwc:
        nwc_calc = (
            db.query(NWCCalculation)
            .filter(
                NWCCalculation.deal_id == deal_id,
                NWCCalculation.status == NWCStatus.APPROVED,
            )
            .order_by(NWCCalculation.created_at.desc())
            .first()
        )
        if nwc_calc:
            kpis.append(
                ("Net Working Capital", _format_currency(nwc_calc.total_nwc), "백만원")
            )

    # Debt 데이터 수집
    debt_calc = None
    if include_debt:
        debt_calc = (
            db.query(NetDebtCalculation)
            .filter(
                NetDebtCalculation.deal_id == deal_id,
                NetDebtCalculation.status == DebtStatus.APPROVED,
            )
            .order_by(NetDebtCalculation.created_at.desc())
            .first()
        )
        if debt_calc:
            kpis.append(("Net Debt", _format_currency(debt_calc.net_debt), "백만원"))

    if kpis:
        sections.append(
            build_kpi_block("Executive Summary", kpis, columns=min(len(kpis), 4))
        )

    # 3.5 Industry KPI Benchmarks
    if industry_ctx.kpi_benchmarks and industry_id != "general":
        benchmark_bullets = []
        for bm in industry_ctx.kpi_benchmarks:
            low = f"{bm.benchmark_range[0]}"
            high = f"{bm.benchmark_range[1]}"
            benchmark_bullets.append(
                f"{bm.name_en}: {low} ~ {high}{bm.unit} ({bm.formula})"
            )
        sections.append(
            build_text_block(
                f"Industry benchmarks for {industry_module.industry_name_en}",
                title="Industry KPI Benchmarks",
                bullet_points=benchmark_bullets,
            )
        )

    # 4. QoE Analysis
    if include_qoe and qoe_calc:
        # QoE Bridge Table
        bridge_data = [
            {
                "category": "Revenue",
                "amount": _format_currency(
                    qoe_calc.category_breakdown.get("revenue")
                    if qoe_calc.category_breakdown
                    else None
                ),
            },
            {
                "category": "Gross Profit",
                "amount": _format_currency(qoe_calc.gross_profit),
            },
            {
                "category": "Reported EBITDA",
                "amount": _format_currency(qoe_calc.reported_ebitda),
            },
            {
                "category": "Total Adjustments",
                "amount": _format_currency(qoe_calc.total_adjustments),
            },
            {
                "category": "Adjusted EBITDA",
                "amount": _format_currency(qoe_calc.adjusted_ebitda),
            },
        ]
        sections.append(
            build_qoe_table_block("Quality of Earnings", bridge_data, ["amount"])
        )

        # QoE Adjustments Detail
        adjustments = []
        for adj in qoe_calc.adjustment_items:
            adjustments.append(
                {
                    "category": adj.category.value if adj.category else "",
                    "description": adj.description or "",
                    "amount": _format_currency(adj.amount),
                    "status": adj.status.value if adj.status else "",
                    "evidence": "Yes" if adj.evidence_link_id else "No",
                }
            )
        if adjustments:
            sections.append(
                build_qoe_adjustments_table_block("QoE Adjustments Detail", adjustments)
            )

    # 5. NWC Analysis
    if include_nwc and nwc_calc:
        # NWC Definition Table
        nwc_items = []
        for item in nwc_calc.line_items:
            nwc_items.append(
                {
                    "account": item.account_name or "",
                    "classification": item.classification.value
                    if item.classification
                    else "",
                    "balance": _format_currency(item.balance),
                    "included": "Yes" if item.included_in_nwc else "No",
                }
            )
        if nwc_items:
            sections.append(
                build_nwc_definition_table_block(
                    "Net Working Capital Definition", nwc_items
                )
            )

        # NWC Peg Scenarios (if available)
        if nwc_calc.peg_scenarios:
            peg_data = []
            for method, values in nwc_calc.peg_scenarios.items():
                peg_data.append(
                    {
                        "method": method,
                        "target_nwc": _format_currency(
                            Decimal(str(values.get("target", 0)))
                        ),
                        "adjustment": _format_currency(
                            Decimal(str(values.get("adjustment", 0)))
                        ),
                        "notes": values.get("notes", ""),
                    }
                )
            sections.append(build_nwc_peg_table_block("NWC Peg Scenarios", peg_data))

    # 6. Net Debt Analysis
    if include_debt and debt_calc:
        debt_items = []

        # Debt items
        for item in debt_calc.debt_items:
            debt_items.append(
                {
                    "item": item.name or "",
                    "type": item.item_type.value if item.item_type else "",
                    "balance": _format_currency(item.balance),
                    "adjustment": _format_currency(item.adjustment),
                    "adjusted": _format_currency(
                        (item.balance or Decimal(0)) + (item.adjustment or Decimal(0))
                    ),
                }
            )

        if debt_items:
            sections.append(
                build_net_debt_schedule_block("Net Debt Schedule", debt_items)
            )

        # Net Debt Summary
        sections.append(
            build_text_block(
                f"Total Net Debt: {_format_currency(debt_calc.net_debt)} 백만원",
                title="Net Debt Summary",
                bullet_points=[
                    f"Total Debt: {_format_currency(debt_calc.total_debt)} 백만원",
                    f"Total Cash: {_format_currency(debt_calc.total_cash)} 백만원",
                    f"Debt-like Items: {_format_currency(debt_calc.debt_like_total)} 백만원",
                    f"Cash-like Items: {_format_currency(debt_calc.cash_like_total)} 백만원",
                ],
            )
        )

    # 7. Multi-Entity Sections (entity structure, FX rates)
    _build_multi_entity_sections(db, deal_id, sections)

    # 7.5 Korea Overlay (K-IFRS, 규제, 세무)
    if korea_overlay and industry_id != "general":
        korea_bullets = []

        if korea_overlay.kifrs_notes:
            korea_bullets.append("**K-IFRS 조정 사항**")
            for note in korea_overlay.kifrs_notes:
                korea_bullets.append(
                    f"K-IFRS {note.standard_number} ({note.topic_kr}): {note.ebitda_impact}"
                )

        if korea_overlay.regulatory_items:
            korea_bullets.append("**규제 검토 사항**")
            for reg in korea_overlay.regulatory_items:
                korea_bullets.append(f"{reg.law_name_kr} ({reg.authority}): {reg.fdd_impact}")

        if korea_overlay.tax_items:
            korea_bullets.append("**세무 검토 사항**")
            for tax in korea_overlay.tax_items:
                korea_bullets.append(f"{tax.description_kr}: {tax.fdd_consideration}")

        if korea_bullets:
            sections.append(
                build_text_block(
                    f"한국 PE FDD 특수 고려사항 ({industry_module.industry_name_kr})",
                    title="Korea Regulatory & Accounting Overlay",
                    bullet_points=korea_bullets,
                )
            )

    # 8. Issue Log
    if include_issues:
        issues = (
            db.query(Issue)
            .filter(Issue.deal_id == deal_id)
            .order_by(Issue.severity.desc(), Issue.created_at.desc())
            .all()
        )
        if issues:
            issue_list = []
            for issue in issues:
                issue_list.append(
                    {
                        "issue_id": str(issue.id)[:8],
                        "category": issue.category.value if issue.category else "",
                        "severity": issue.severity.value
                        if issue.severity
                        else "medium",
                        "title": issue.title or "",
                        "description": issue.description or "",
                        "status": issue.status.value if issue.status else "open",
                        "recommendation": issue.recommendation or "",
                    }
                )

            sections.append(build_issue_block(issue_list, title="Issue Log"))

            # Issue Summary Table
            sections.append(
                build_issue_summary_table_block("Issue Summary", issue_list[:10])
            )

    # 8.5a Template SlotFill Narratives (new)
    if use_template_slotfill:
        _build_slotfill_narratives(
            sections,
            deal,
            qoe_calc,
            nwc_calc,
            debt_calc,
            issues if include_issues else [],
            industry_module,
            industry_id,
        )

    # 8.5b LLM-Generated Narratives (legacy)
    elif narrator:
        try:
            # Executive Summary narrative
            qoe_summary = None
            if qoe_calc:
                qoe_summary = {
                    "reported_ebitda": _format_currency(qoe_calc.reported_ebitda),
                    "adjusted_ebitda": _format_currency(qoe_calc.adjusted_ebitda),
                    "total_adjustments": _format_currency(qoe_calc.total_adjustments),
                }
            nwc_summary = None
            if nwc_calc:
                nwc_summary = {
                    "net_working_capital": _format_currency(nwc_calc.total_nwc),
                    "peg_target": _format_currency(nwc_calc.peg_target) if hasattr(nwc_calc, "peg_target") else "N/A",
                }
            debt_summary = None
            if debt_calc:
                debt_summary = {
                    "net_debt": _format_currency(debt_calc.net_debt),
                    "adjusted_net_debt": _format_currency(debt_calc.adjusted_net_debt) if hasattr(debt_calc, "adjusted_net_debt") else "N/A",
                }

            exec_summary = narrator.generate_executive_summary(
                deal_name=deal.name,
                industry_name=industry_module.industry_name_en,
                qoe_data=qoe_summary,
                nwc_data=nwc_summary,
                debt_data=debt_summary,
            )
            if exec_summary:
                sections.append(
                    build_text_block(exec_summary, title="Executive Summary (AI-Generated)")
                )
        except Exception as e:
            logger.warning(f"LLM narrative generation failed: {e}")

    # 9. Methodology
    industry_note = (
        f" with {industry_module.industry_name_en}-specific adjustment rules"
        if industry_id != "general"
        else ""
    )
    methodology_steps = [
        (
            1,
            "Data Collection",
            "Collected Trial Balance, General Ledger, and supporting schedules",
        ),
        (
            2,
            "Account Mapping",
            "Mapped source accounts to standardized FDD chart of accounts",
        ),
        (
            3,
            "QoE Analysis",
            f"Calculated reported EBITDA and identified adjustment candidates{industry_note}",
        ),
        (
            4,
            "NWC Analysis",
            "Classified working capital items and calculated target NWC",
        ),
        (
            5,
            "Net Debt Analysis",
            "Identified debt and cash items, calculated adjusted net debt",
        ),
        (
            6,
            "Consolidation",
            "Multi-entity consolidation with FX conversion and IC elimination",
        ),
        (7, "Quality Review", "Automated anomaly detection and evidence verification"),
    ]
    limitations = [
        "Analysis based on data provided by management",
        "No independent audit procedures performed",
        "Forward-looking adjustments require management judgment",
    ]
    sections.append(build_methodology_block(methodology_steps, limitations=limitations))

    return ReportIR(metadata=metadata, sections=sections)


# ---------------------------------------------------------------------------
# Template SlotFill helpers
# ---------------------------------------------------------------------------

_SECTION_TITLES: dict[str, str] = {
    "executive_summary": "Executive Summary",
    "qoe_analysis": "Quality of Earnings Commentary",
    "nwc_analysis": "Net Working Capital Commentary",
    "debt_analysis": "Net Debt Commentary",
    "risk_narrative": "Risk Assessment",
    "methodology": "Methodology",
}


def _build_fdd_data_dict(
    deal: Deal,
    qoe_calc: QoECalculation | None,
    nwc_calc: NWCCalculation | None,
    debt_calc: NetDebtCalculation | None,
    issues: list,
    industry_module: object | None = None,
) -> dict:
    """FDD 분석 데이터를 렌더러에 전달할 dict로 구성한다."""
    data: dict = {
        "deal_name": deal.name,
        "industry_name": getattr(industry_module, "industry_name_en", "General"),
        "industry_name_kr": getattr(industry_module, "industry_name_kr", "일반"),
        "analysis_period": "FY2024 - FY2025",
        "scope_items": "Quality of Earnings, Net Working Capital, Net Debt",
    }

    if qoe_calc:
        top_adjs = []
        for adj in (qoe_calc.adjustment_items or [])[:5]:
            top_adjs.append({
                "description": adj.description or "",
                "amount": _format_currency(adj.amount),
                "category": adj.category.value if adj.category else "",
            })
        data["qoe"] = {
            "reported_ebitda": _format_currency(qoe_calc.reported_ebitda),
            "adjusted_ebitda": _format_currency(qoe_calc.adjusted_ebitda),
            "total_adjustments": _format_currency(qoe_calc.total_adjustments),
            "adjustment_count": len(qoe_calc.adjustment_items or []),
            "gross_profit": _format_currency(qoe_calc.gross_profit),
            "top_adjustments": top_adjs,
            "category_breakdown": qoe_calc.category_breakdown or {},
        }

    if nwc_calc:
        data["nwc"] = {
            "total_nwc": _format_currency(nwc_calc.total_nwc),
            "peg_target": _format_currency(nwc_calc.peg_target)
            if hasattr(nwc_calc, "peg_target") and nwc_calc.peg_target
            else "N/A",
            "line_item_count": len(nwc_calc.line_items or []),
            "peg_scenarios": nwc_calc.peg_scenarios or {},
        }

    if debt_calc:
        data["debt"] = {
            "net_debt": _format_currency(debt_calc.net_debt),
            "total_debt": _format_currency(debt_calc.total_debt),
            "total_cash": _format_currency(debt_calc.total_cash),
            "debt_like_total": _format_currency(debt_calc.debt_like_total),
            "cash_like_total": _format_currency(debt_calc.cash_like_total),
        }

    issue_list = []
    for issue in (issues or []):
        issue_list.append({
            "title": issue.title or "",
            "severity": issue.severity.value if issue.severity else "medium",
            "category": issue.category.value if issue.category else "",
            "description": issue.description or "",
        })
    data["issues"] = issue_list

    return data


def _extract_known_values(fdd_data: dict) -> dict[str, str]:
    """Guardrail 교차검증을 위한 known_values dict를 구성한다."""
    known: dict[str, str] = {}
    for section_key in ("qoe", "nwc", "debt"):
        section = fdd_data.get(section_key)
        if isinstance(section, dict):
            for k, v in section.items():
                if isinstance(v, str) and v not in ("N/A", ""):
                    known[k] = v
    return known


def _build_slotfill_narratives(
    sections: list,
    deal: Deal,
    qoe_calc: QoECalculation | None,
    nwc_calc: NWCCalculation | None,
    debt_calc: NetDebtCalculation | None,
    issues: list,
    industry_module: object,
    industry_id: str,
) -> None:
    """템플릿 슬롯 채우기 방식으로 내러티브를 생성하고 sections에 추가한다."""
    from pathlib import Path

    from app.agents.guardrails import validate_narrative_claims
    from app.services.report.slot_fill import (
        FDDSlotFillPromptBuilder,
        FDDTemplateRenderer,
        SlotResponseParser,
        TemplateRegistry,
    )

    # 1. 인프라 초기화
    templates_dir = Path(__file__).parent / "templates"
    registry = TemplateRegistry(templates_dir)
    renderer = FDDTemplateRenderer()
    prompt_builder = FDDSlotFillPromptBuilder()
    parser = SlotResponseParser()
    base_blocks = registry.base_blocks

    # 2. FDD 데이터 dict 구성
    fdd_data = _build_fdd_data_dict(
        deal, qoe_calc, nwc_calc, debt_calc, issues, industry_module,
    )

    # 3. LLM 라우터 (L3 슬롯용)
    router = None
    try:
        from app.services.llm.routing import create_fdd_model_router

        router = create_fdd_model_router()
        if not router.available_providers:
            router = None
    except Exception as e:
        logger.warning("LLM router init failed for slotfill, L2-only mode: %s", e)

    # 4. 산업 내러티브 컨텍스트
    industry_ctx = ""
    if hasattr(industry_module, "format_narrative_context"):
        industry_ctx = industry_module.format_narrative_context()

    # 5. 섹션별 렌더링
    section_order = [
        "executive_summary",
        "qoe_analysis",
        "nwc_analysis",
        "debt_analysis",
        "risk_narrative",
        "methodology",
    ]

    for section_id in section_order:
        if not registry.has(section_id):
            continue

        template = registry.get(section_id, industry=industry_id)
        if template is None:
            continue

        try:
            # L3 슬롯이 있고 라우터가 있으면 LLM 호출
            llm_slots: dict[str, str] = {}
            if template.l3_slots and router:
                system = prompt_builder.build_system_prompt(
                    industry_context=industry_ctx,
                )
                user = prompt_builder.build_user_prompt(template, fdd_data)
                response = router.generate(
                    section_id,
                    system_prompt=system,
                    user_prompt=user,
                    temperature=0.2,
                    max_tokens=512,
                )
                llm_slots = parser.parse(
                    response.text, list(template.l3_slots.keys()),
                )

            # 렌더링
            text = renderer.render(
                template,
                fdd_data,
                llm_slots,
                industry=industry_id,
                base_blocks=base_blocks,
            )

            # Guardrail
            known_values = _extract_known_values(fdd_data)
            warnings = validate_narrative_claims(text, known_values)
            if warnings:
                logger.warning(
                    "SlotFill guardrail warnings [%s]: %s", section_id, warnings,
                )

            title = _SECTION_TITLES.get(section_id, section_id.replace("_", " ").title())
            sections.append(build_text_block(text, title=title))

        except Exception as e:
            logger.error("SlotFill failed for section '%s': %s", section_id, e)


async def generate_pptx(
    report_ir: ReportIR,
    pptx_service_url: str = "http://localhost:3100",
) -> bytes:
    """Report IR을 PPT 파일로 변환.

    Args:
        report_ir: ReportIR 인스턴스
        pptx_service_url: pptx-service URL

    Returns:
        PPTX 파일 바이트
    """
    ir_dict = report_ir_to_dict(report_ir)

    # pptx-service 스키마에 맞게 변환
    schema = {
        "meta": ir_dict["metadata"],
        "sections": ir_dict["sections"],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{pptx_service_url}/render",
            json=schema,
        )

        if response.status_code != 200:
            logger.error(
                f"pptx-service error: {response.status_code} - {response.text}"
            )
            raise RuntimeError(f"Failed to generate PPTX: {response.text}")

        return response.content
