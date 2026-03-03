"""Pro-Forma 재무 전망 데이터 — TM 전용 (2026E~2030E).

기존 financials.py의 2021~2025E 실적에 이어지는 5개년 전망을 정의한다.
TM(Teaser Memorandum)의 proforma_plan / proforma_financials 섹션에서 사용된다.
단위: 백만원.
"""

from __future__ import annotations

from src.design_renderer.im_document import (
    ChartData,
    FinancialStatements,
)


def build_proforma_financial_statements() -> FinancialStatements:
    """Pro-Forma 5개년 전망 재무제표 (2026E~2030E).

    기존 2025E 실적(매출 192,000)에서 연평균 14.6% 성장 가정.

    Note:
        현재 tm_full.py에서는 build_financial_statements() (5개년 실적)만 사용한다.
        향후 DM(Detailed Memorandum)이나 실적+전망 병합 시나리오에서 활용 예정.
    """
    return FinancialStatements(
        # ── 손익계산서 ──
        revenue={
            "2026E": 225_000,
            "2027E": 265_000,
            "2028E": 310_000,
            "2029E": 350_000,
            "2030E": 380_000,
        },
        cost_of_goods_sold={
            "2026E": 119_250,
            "2027E": 137_800,
            "2028E": 158_100,
            "2029E": 175_000,
            "2030E": 186_200,
        },
        gross_profit={
            "2026E": 105_750,
            "2027E": 127_200,
            "2028E": 151_900,
            "2029E": 175_000,
            "2030E": 193_800,
        },
        operating_income={
            "2026E": 45_000,
            "2027E": 57_200,
            "2028E": 71_300,
            "2029E": 84_000,
            "2030E": 98_800,
        },
        ebitda={
            "2026E": 56_250,
            "2027E": 70_200,
            "2028E": 86_800,
            "2029E": 101_500,
            "2030E": 114_000,
        },
        net_income={
            "2026E": 33_750,
            "2027E": 42_900,
            "2028E": 53_500,
            "2029E": 63_000,
            "2030E": 74_100,
        },
        sga_expenses={
            "2026E": 60_750,
            "2027E": 70_000,
            "2028E": 80_600,
            "2029E": 91_000,
            "2030E": 95_000,
        },
        # ── 재무상태표 ──
        total_assets={
            "2026E": 500_000,
            "2027E": 600_000,
            "2028E": 720_000,
            "2029E": 850_000,
            "2030E": 980_000,
        },
        total_liabilities={
            "2026E": 140_000,
            "2027E": 155_000,
            "2028E": 170_000,
            "2029E": 185_000,
            "2030E": 200_000,
        },
        total_equity={
            "2026E": 360_000,
            "2027E": 445_000,
            "2028E": 550_000,
            "2029E": 665_000,
            "2030E": 780_000,
        },
        cash_and_equivalents={
            "2026E": 110_000,
            "2027E": 145_000,
            "2028E": 190_000,
            "2029E": 245_000,
            "2030E": 310_000,
        },
        total_debt={
            "2026E": 25_000,
            "2027E": 20_000,
            "2028E": 15_000,
            "2029E": 10_000,
            "2030E": 5_000,
        },
        # ── 현금흐름표 ──
        operating_cash_flow={
            "2026E": 52_000,
            "2027E": 65_000,
            "2028E": 81_000,
            "2029E": 96_000,
            "2030E": 110_000,
        },
        investing_cash_flow={
            "2026E": -22_000,
            "2027E": -25_000,
            "2028E": -28_000,
            "2029E": -30_000,
            "2030E": -32_000,
        },
        financing_cash_flow={
            "2026E": -5_000,
            "2027E": -5_000,
            "2028E": -5_000,
            "2029E": -5_000,
            "2030E": -5_000,
        },
        capex={
            "2026E": 14_000,
            "2027E": 16_000,
            "2028E": 18_000,
            "2029E": 20_000,
            "2030E": 22_000,
        },
        free_cash_flow={
            "2026E": 38_000,
            "2027E": 49_000,
            "2028E": 63_000,
            "2029E": 76_000,
            "2030E": 88_000,
        },
    )


def build_proforma_charts() -> dict[str, list[ChartData]]:
    """Pro-Forma 전망 차트 데이터 (TM proforma 섹션용)."""
    return {
        "proforma_financials": [
            ChartData(
                chart_type="combo",
                title="Pro-Forma 매출 및 EBITDA 마진 전망",
                data={
                    "categories": ["2026E", "2027E", "2028E", "2029E", "2030E"],
                    "bar_series": [
                        {
                            "name": "매출액",
                            "values": [225_000, 265_000, 310_000, 350_000, 380_000],
                        }
                    ],
                    "line_series": [
                        {
                            "name": "EBITDA 마진",
                            "values": [0.250, 0.265, 0.280, 0.290, 0.300],
                        }
                    ],
                },
            ),
            ChartData(
                chart_type="line",
                title="Pro-Forma Free Cash Flow 전망 (백만원)",
                data={
                    "x": ["2026E", "2027E", "2028E", "2029E", "2030E"],
                    "series": [
                        {
                            "name": "Free Cash Flow",
                            "values": [38_000, 49_000, 63_000, 76_000, 88_000],
                        }
                    ],
                },
            ),
        ],
        "proforma_plan": [
            ChartData(
                chart_type="stacked_bar",
                title="사업부별 매출 전망",
                data={
                    "categories": ["2026E", "2027E", "2028E", "2029E", "2030E"],
                    "series": [
                        {
                            "name": "클라우드 인프라",
                            "values": [113_000, 134_000, 158_000, 182_000, 210_000],
                        },
                        {
                            "name": "데이터 분석",
                            "values": [65_000, 79_000, 96_000, 112_000, 114_000],
                        },
                        {
                            "name": "SI/컨설팅",
                            "values": [28_000, 30_000, 32_000, 30_000, 28_000],
                        },
                        {
                            "name": "보안 솔루션",
                            "values": [19_000, 22_000, 24_000, 26_000, 28_000],
                        },
                    ],
                },
            ),
        ],
    }
