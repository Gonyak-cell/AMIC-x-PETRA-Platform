"""Executive Summary 섹션 렌더러.

AI 생성 내러티브 + 핵심 재무 KPI 하이라이트를 포함하는 요약 슬라이드.

PPTX 출력은 데이터 유무에 따라 3~5슬라이드를 동적 생성한다:
  - Slide 1: KPI Dashboard (6-8 KPI cards)
  - Slide 2: Executive Summary Narrative (AI 생성 내러티브 전문)
  - Slide 3: Deal Highlights (deal_structure 정보 — 조건부)
  - Slide 4: Key Takeaways (investment_highlights >= 3 — 조건부)
"""

from __future__ import annotations

import logging
from html import escape as html_escape
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import IMDocumentData

from src.design_renderer.section_renderers import register_renderer
from src.design_renderer.section_renderers.base import BaseSectionRenderer
from src.design_renderer.section_renderers.format_utils import fmt_amount, fmt_pct

logger = logging.getLogger(__name__)


def _format_pct(val: float | None) -> str:
    return fmt_pct(val)


def _format_amount(val: float | None, scale: str = "억원") -> str:
    return fmt_amount(val, scale=scale)


@register_renderer
class ExecutiveSummaryRenderer(BaseSectionRenderer):
    """Executive Summary 슬라이드 렌더러."""

    section_id = "executive_summary"

    def _build_kpis(self, data: IMDocumentData) -> list[dict[str, str]]:
        """KPI 데이터를 [{label, value}] 리스트로 변환 (기본 4~6개, HTML용)."""
        fs = data.financial_statements
        dm = data.derived_metrics or {}
        years = fs.years
        kpis: list[dict[str, str]] = []

        if years:
            latest = years[-1]
            if fs.revenue.get(latest) is not None:
                kpis.append({
                    "label": f"매출액 ({latest})",
                    "value": _format_amount(fs.revenue[latest]),
                })
            if fs.operating_income.get(latest) is not None:
                kpis.append({
                    "label": f"영업이익 ({latest})",
                    "value": _format_amount(fs.operating_income[latest]),
                })
            if fs.ebitda.get(latest) is not None:
                kpis.append({
                    "label": f"EBITDA ({latest})",
                    "value": _format_amount(fs.ebitda[latest]),
                })
            if fs.net_income.get(latest) is not None:
                kpis.append({
                    "label": f"순이익 ({latest})",
                    "value": _format_amount(fs.net_income[latest]),
                })

        if dm.get("revenue_cagr_3y") is not None:
            kpis.append({
                "label": "매출 CAGR (3Y)",
                "value": _format_pct(dm["revenue_cagr_3y"]),
            })
        if dm.get("ebitda_margin_latest") is not None:
            kpis.append({
                "label": "EBITDA 마진율",
                "value": _format_pct(dm["ebitda_margin_latest"]),
            })

        return kpis

    def _build_kpis_extended(self, data: IMDocumentData) -> list[dict[str, str]]:
        """확장 KPI 데이터 (6~8개, PPTX Dashboard 슬라이드용).

        기본 KPI에 YoY 성장률, 영업이익률, 순이익률 등 추가 지표를 포함한다.
        """
        fs = data.financial_statements
        dm = data.derived_metrics or {}
        years = fs.years
        kpis: list[dict[str, str]] = []

        if years:
            latest = years[-1]
            # 1. 매출액
            if fs.revenue.get(latest) is not None:
                kpis.append({
                    "label": f"매출액 ({latest})",
                    "value": _format_amount(fs.revenue[latest]),
                })
            # 2. 영업이익
            if fs.operating_income.get(latest) is not None:
                kpis.append({
                    "label": f"영업이익 ({latest})",
                    "value": _format_amount(fs.operating_income[latest]),
                })
            # 3. EBITDA
            if fs.ebitda.get(latest) is not None:
                kpis.append({
                    "label": f"EBITDA ({latest})",
                    "value": _format_amount(fs.ebitda[latest]),
                })
            # 4. 순이익
            if fs.net_income.get(latest) is not None:
                kpis.append({
                    "label": f"순이익 ({latest})",
                    "value": _format_amount(fs.net_income[latest]),
                })

        # 5. 매출 CAGR (3Y)
        if dm.get("revenue_cagr_3y") is not None:
            kpis.append({
                "label": "매출 CAGR (3Y)",
                "value": _format_pct(dm["revenue_cagr_3y"]),
            })

        # 6. EBITDA 마진율
        if dm.get("ebitda_margin_latest") is not None:
            kpis.append({
                "label": "EBITDA 마진율",
                "value": _format_pct(dm["ebitda_margin_latest"]),
            })

        # 7. 매출 YoY 성장률
        if dm.get("revenue_yoy") is not None:
            kpis.append({
                "label": "매출 YoY",
                "value": _format_pct(dm["revenue_yoy"]),
            })

        # 8. 영업이익률
        if dm.get("operating_margin_latest") is not None:
            kpis.append({
                "label": "영업이익률",
                "value": _format_pct(dm["operating_margin_latest"]),
            })

        # 8b. 순이익률 (영업이익률 없을 때 대체)
        if dm.get("operating_margin_latest") is None and dm.get("net_margin_latest") is not None:
            kpis.append({
                "label": "순이익률",
                "value": _format_pct(dm["net_margin_latest"]),
            })

        # 최대 8개로 제한
        return kpis[:8]

    def _build_deal_highlights(self, data: IMDocumentData) -> list[str]:
        """deal_structure에서 딜 하이라이트 불릿 항목을 추출한다.

        Returns:
            불릿 문자열 리스트. 비어 있으면 Slide 3 스킵.
        """
        ds = data.deal_structure
        if ds is None:
            return []

        bullets: list[str] = []
        if ds.transaction_type:
            bullets.append(f"딜 타입: {ds.transaction_type.value}")
        if ds.seller:
            bullets.append(f"매각주체: {ds.seller}")
        if ds.stake_pct is not None:
            bullets.append(f"매각 지분율: {ds.stake_pct * 100:.1f}%")
        if ds.old_shares is not None:
            bullets.append(f"구주 규모: {ds.old_shares:,.0f}억원")
        if ds.new_shares is not None:
            bullets.append(f"신주 규모: {ds.new_shares:,.0f}억원")
        if ds.valuation_low is not None and ds.valuation_high is not None:
            bullets.append(
                f"밸류에이션 범위: {ds.valuation_low:,.0f} ~ "
                f"{ds.valuation_high:,.0f}억원"
            )
        elif ds.valuation_low is not None:
            bullets.append(f"밸류에이션 하한: {ds.valuation_low:,.0f}억원~")
        elif ds.valuation_high is not None:
            bullets.append(f"밸류에이션 상한: ~{ds.valuation_high:,.0f}억원")
        if ds.valuation_method:
            bullets.append(f"밸류에이션 방법론: {ds.valuation_method}")

        # EV/EBITDA 배수 (valuation_data에서 최신 연도)
        vd = data.valuation_data
        if vd and vd.ev_ebitda:
            years_sorted = sorted(vd.ev_ebitda.keys())
            if years_sorted:
                latest_yr = years_sorted[-1]
                bullets.append(
                    f"EV/EBITDA ({latest_yr}): {vd.ev_ebitda[latest_yr]:.1f}x"
                )

        if ds.deal_background:
            bullets.append(f"거래 배경: {ds.deal_background}")

        # 주요 일정
        if ds.timeline:
            for milestone, date_val in ds.timeline.items():
                bullets.append(f"{milestone}: {date_val}")

        return bullets

    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        raise NotImplementedError("PDF output removed")

    def render_pptx(
        self,
        factory: Any,
        data: IMDocumentData,
        *,
        prs: Any,
        tokens: IMDesignTokens | None = None,
    ) -> list[Any]:
        """Executive Summary를 3~5 슬라이드로 렌더링.

        - Slide 1: KPI Dashboard (6-8 KPI cards)
        - Slide 2: Executive Summary Narrative (AI 생성 내러티브 전문)
        - Slide 3: Deal Highlights (deal_structure 정보 — 데이터 있을 때만)
        - Slide 4: Key Takeaways (investment_highlights >= 3 — 조건부)

        데이터가 없는 슬라이드는 자동 스킵하여 동적 페이지 수를 유지한다.
        """
        tokens = tokens or DEFAULT_TOKENS
        lay = tokens.layout

        from src.design_renderer.pptx_engine.shape_builder import (
            add_body_textbox,
            add_bullet_list,
            add_kpi_grid,
            add_sub_header_bar,
            add_summary_textbox,
        )

        slides: list[Any] = []

        # ── Slide 1: KPI Dashboard ──────────────────────────────────
        kpis = self._build_kpis_extended(data)
        if kpis:
            slide1 = factory.add_content_slide(title="Executive Summary — KPI Dashboard")
            y = lay.content_top
            add_kpi_grid(
                slide1,
                kpis,
                top=y,
                tokens=tokens,
                number_config=data.number_format,
                cols=4,
            )
            slides.append(slide1)

        # ── Slide 2: Executive Summary Narrative ────────────────────
        narrative = data.narratives.get("executive_summary", "")
        if narrative:
            slide2 = factory.add_content_slide(title="Executive Summary")
            y = lay.content_top

            # 내러티브가 충분히 길면 상단 요약 + 본문으로 분리
            paragraphs = [p.strip() for p in narrative.split("\n") if p.strip()]
            if len(paragraphs) >= 2:
                # 첫 문단을 요약(14pt bold), 나머지를 본문(10pt)
                summary_text = paragraphs[0]
                body_text = "\n".join(paragraphs[1:])
                add_summary_textbox(slide2, summary_text, top=y, tokens=tokens)
                y += 0.7
                add_body_textbox(
                    slide2, body_text, top=y, height=4.0, tokens=tokens,
                )
            else:
                # 짧은 내러티브: 본문만
                add_body_textbox(
                    slide2, narrative, top=y, height=4.5, tokens=tokens,
                )
            slides.append(slide2)

        # ── Slide 3: Deal Highlights (조건부) ───────────────────────
        deal_bullets = self._build_deal_highlights(data)
        if deal_bullets:
            slide3 = factory.add_content_slide(
                title="Executive Summary — Deal Highlights",
            )
            y = lay.content_top
            add_sub_header_bar(
                slide3, "딜 하이라이트", top=y, tokens=tokens,
            )
            y += 0.45
            add_bullet_list(
                slide3, deal_bullets, top=y, height=4.5, tokens=tokens,
            )
            slides.append(slide3)

        # ── Slide 4: Key Takeaways (조건부) ─────────────────────────
        highlights = data.investment_highlights
        if len(highlights) >= 3:
            slide4 = factory.add_content_slide(
                title="Executive Summary — 핵심 시사점",
            )
            y = lay.content_top
            add_sub_header_bar(
                slide4, "Key Takeaways", top=y, tokens=tokens,
            )
            y += 0.45
            # 상위 3개만 추출
            top_highlights = [
                f"{i}. {item}" for i, item in enumerate(highlights[:3], 1)
            ]
            add_bullet_list(
                slide4, top_highlights, top=y, height=4.0, tokens=tokens,
            )
            slides.append(slide4)

        # 데이터가 전혀 없는 극단적 경우: 빈 슬라이드 1장 반환
        if not slides:
            fallback = factory.add_content_slide(title="Executive Summary")
            add_body_textbox(
                fallback,
                "Executive Summary 데이터가 준비되지 않았습니다.",
                top=lay.content_top,
                tokens=tokens,
            )
            slides.append(fallback)

        return slides
