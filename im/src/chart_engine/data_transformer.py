"""데이터 변환기 — IMDocumentData → 섹션별 ChartSpec 자동 생성.

> 마지막 수정: 2026-02-10 13:45:13

재무/시장/주주 데이터를 분석하여 적절한 차트 유형을 자동 제안한다.
IMDocumentData에 직접 의존하지 않고, duck typing으로 속성을 참조.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChartSpec:
    """차트 명세 (chart_engine 내부 사용).

    design_renderer의 ChartData와 동일한 구조이나 별도 정의.
    """

    chart_type: str = ""
    title: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


class DataTransformer:
    """IMDocumentData의 재무/시장 데이터에서 차트 데이터를 자동 생성.

    Financial Analysis 섹션에 매출 추이 combo, 수익성 waterfall 등을
    자동으로 제안하는 역할.
    """

    def transform_financial(
        self,
        financial_statements: Any,
        derived_metrics: dict[str, float] | None = None,
    ) -> list[ChartSpec]:
        """재무제표 → financial_analysis 차트 목록 생성.

        Args:
            financial_statements: FinancialStatements (duck typed).
                속성: revenue, operating_income, ebitda, net_income, years
            derived_metrics: 파생 지표 dict (optional).

        Returns:
            ChartSpec 목록.
        """
        charts: list[ChartSpec] = []

        # revenue + operating_income 속성 확인
        revenue = getattr(financial_statements, "revenue", {})
        operating_income = getattr(financial_statements, "operating_income", {})
        ebitda = getattr(financial_statements, "ebitda", {})
        years = getattr(financial_statements, "years", [])

        if not years or len(years) < 2:
            return charts

        # 1) 매출 + 영업이익률 콤보 차트
        if revenue and operating_income:
            sorted_years = sorted(years)
            rev_values = [revenue.get(y, 0) for y in sorted_years]
            oi_values = [operating_income.get(y, 0) for y in sorted_years]
            margin_values = [
                oi / rev if rev != 0 else 0
                for rev, oi in zip(rev_values, oi_values)
            ]

            charts.append(
                ChartSpec(
                    chart_type="combo",
                    title="매출 및 영업이익률 추이",
                    data={
                        "years": sorted_years,
                        "bar_values": rev_values,
                        "bar_name": "매출",
                        "line_values": margin_values,
                        "line_name": "영업이익률",
                    },
                )
            )

        # 2) 영업이익 워터폴 (최신 연도)
        if revenue and operating_income and years:
            latest = sorted(years)[-1]
            rev = revenue.get(latest, 0)
            cogs = getattr(financial_statements, "cost_of_goods_sold", {}).get(latest, 0)
            sga = getattr(financial_statements, "sga_expenses", {}).get(latest, 0)
            oi = operating_income.get(latest, 0)

            if rev and (cogs or sga):
                charts.append(
                    ChartSpec(
                        chart_type="waterfall",
                        title=f"영업이익 구성 ({latest})",
                        data={
                            "categories": ["매출", "매출원가", "판관비", "영업이익"],
                            "values": [rev, -abs(cogs), -abs(sga), oi],
                            "measure": ["absolute", "relative", "relative", "total"],
                        },
                    )
                )

        # 3) EBITDA 추이 라인 차트 (3년 이상)
        if ebitda and len(years) >= 3:
            sorted_years = sorted(years)
            ebitda_values = [ebitda.get(y, 0) for y in sorted_years]

            charts.append(
                ChartSpec(
                    chart_type="line",
                    title="EBITDA 추이",
                    data={
                        "x": sorted_years,
                        "series": [
                            {"name": "EBITDA", "values": ebitda_values},
                        ],
                    },
                )
            )

        return charts

    def transform_segment(
        self,
        segment_revenue: Any,
    ) -> list[ChartSpec]:
        """사업부별 매출 → stacked_bar 차트 생성.

        Args:
            segment_revenue: SegmentRevenue (duck typed).
                속성: segments (dict[str, dict[str, float]])

        Returns:
            ChartSpec 목록.
        """
        charts: list[ChartSpec] = []

        segments = getattr(segment_revenue, "segments", {})
        if not segments:
            return charts

        # 연도 집합 추출
        all_years: set[str] = set()
        for year_dict in segments.values():
            all_years.update(year_dict.keys())

        if not all_years:
            return charts

        sorted_years = sorted(all_years)

        series = []
        for seg_name, year_dict in segments.items():
            series.append({
                "name": seg_name,
                "values": [year_dict.get(y, 0) for y in sorted_years],
            })

        charts.append(
            ChartSpec(
                chart_type="stacked_bar",
                title="사업부별 매출 추이",
                data={
                    "categories": sorted_years,
                    "series": series,
                },
            )
        )

        return charts

    def transform_market(
        self,
        market_data: Any,
    ) -> list[ChartSpec]:
        """시장 데이터 → market_overview 차트 목록 생성.

        Args:
            market_data: MarketData (duck typed).
                속성: tam, sam, som, competitors

        Returns:
            ChartSpec 목록.
        """
        charts: list[ChartSpec] = []

        tam = getattr(market_data, "tam", None)
        sam = getattr(market_data, "sam", None)
        som = getattr(market_data, "som", None)
        competitors = getattr(market_data, "competitors", [])

        # 1) TAM/SAM/SOM 도넛 차트
        if tam and sam and som:
            charts.append(
                ChartSpec(
                    chart_type="donut",
                    title="시장 규모 (TAM/SAM/SOM)",
                    data={
                        "labels": ["TAM", "SAM", "SOM"],
                        "values": [tam, sam, som],
                    },
                )
            )

        # 1b) TAM/SAM/SOM 퍼널 차트
        if tam and sam and som:
            charts.append(
                ChartSpec(
                    chart_type="funnel",
                    title="시장 규모 퍼널 (TAM → SAM → SOM)",
                    data={
                        "stages": ["TAM", "SAM", "SOM"],
                        "values": [tam, sam, som],
                    },
                )
            )

        # 2) 경쟁사 비교 수평 바 차트
        if competitors and len(competitors) >= 2:
            names = [c.get("name", "") for c in competitors]
            revenues = [c.get("revenue", 0) for c in competitors]

            charts.append(
                ChartSpec(
                    chart_type="hbar",
                    title="경쟁사 매출 비교",
                    data={
                        "categories": names,
                        "values": revenues,
                    },
                )
            )

        return charts

    def transform_shareholders(
        self,
        shareholders: list[Any],
    ) -> list[ChartSpec]:
        """주주 데이터 → 주주구성 차트 목록 생성.

        Args:
            shareholders: list[ShareholderInfo] (duck typed).
                속성: name, stake_pct

        Returns:
            ChartSpec 목록.
        """
        charts: list[ChartSpec] = []

        if not shareholders:
            return charts

        # 주주 구성 도넛 차트
        names = [getattr(sh, "name", "") for sh in shareholders]
        pcts = [getattr(sh, "stake_pct", 0.0) * 100 for sh in shareholders]

        if any(pcts):
            charts.append(
                ChartSpec(
                    chart_type="donut",
                    title="주주 구성",
                    data={
                        "labels": names,
                        "values": pcts,
                    },
                )
            )

        return charts

    def transform_all(
        self,
        document_data: Any,
    ) -> dict[str, list[ChartSpec]]:
        """IMDocumentData 전체에서 섹션별 차트 목록 생성.

        Args:
            document_data: IMDocumentData (duck typed).

        Returns:
            {"financial_analysis": [...], "market_overview": [...], ...}
        """
        result: dict[str, list[ChartSpec]] = {}

        # 재무 분석
        fs = getattr(document_data, "financial_statements", None)
        dm = getattr(document_data, "derived_metrics", None)
        if fs:
            financial_charts = self.transform_financial(fs, dm)
            if financial_charts:
                result["financial_analysis"] = financial_charts

        # 사업부별 매출
        sr = getattr(document_data, "segment_revenue", None)
        if sr:
            segment_charts = self.transform_segment(sr)
            if segment_charts:
                result.setdefault("financial_analysis", []).extend(segment_charts)

        # 시장 분석
        md = getattr(document_data, "market_data", None)
        if md:
            market_charts = self.transform_market(md)
            if market_charts:
                result["market_overview"] = market_charts

        # 주주 구성
        sh = getattr(document_data, "shareholders", [])
        if sh:
            shareholder_charts = self.transform_shareholders(sh)
            if shareholder_charts:
                result["shareholder_structure"] = shareholder_charts

        return result
