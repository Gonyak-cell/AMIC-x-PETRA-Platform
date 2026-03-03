"""5개년 재무 데이터 + 세그먼트 매출 + 밸류에이션 — 실물 수준 샘플.

가상의 IT 서비스 기업(넥스트테크)의 2021~2025E 재무제표를 정의한다.
단위: 백만원 (억원 표시 시 /100 변환).
"""

from __future__ import annotations

from src.design_renderer.im_document import (
    ChartData,
    FinancialStatements,
    SegmentRevenue,
    SourceCitation,
    ValuationData,
)


def build_financial_statements() -> FinancialStatements:
    """5개년 재무제표 (2021~2025E)."""
    return FinancialStatements(
        # ── 손익계산서 ──
        revenue={
            "2021": 85_000,
            "2022": 102_000,
            "2023": 125_000,
            "2024": 155_000,
            "2025E": 192_000,
        },
        cost_of_goods_sold={
            "2021": 52_700,
            "2022": 61_200,
            "2023": 72_500,
            "2024": 86_800,
            "2025E": 105_600,
        },
        gross_profit={
            "2021": 32_300,
            "2022": 40_800,
            "2023": 52_500,
            "2024": 68_200,
            "2025E": 86_400,
        },
        operating_income={
            "2021": 10_200,
            "2022": 14_280,
            "2023": 20_000,
            "2024": 27_900,
            "2025E": 36_480,
        },
        ebitda={
            "2021": 14_450,
            "2022": 19_380,
            "2023": 26_250,
            "2024": 35_650,
            "2025E": 46_080,
        },
        net_income={
            "2021": 7_650,
            "2022": 10_710,
            "2023": 15_000,
            "2024": 20_925,
            "2025E": 27_360,
        },
        sga_expenses={
            "2021": 22_100,
            "2022": 26_520,
            "2023": 32_500,
            "2024": 40_300,
            "2025E": 49_920,
        },
        # ── 재무상태표 ──
        total_assets={
            "2021": 180_000,
            "2022": 215_000,
            "2023": 265_000,
            "2024": 330_000,
            "2025E": 410_000,
        },
        total_liabilities={
            "2021": 72_000,
            "2022": 82_000,
            "2023": 95_000,
            "2024": 110_000,
            "2025E": 125_000,
        },
        total_equity={
            "2021": 108_000,
            "2022": 133_000,
            "2023": 170_000,
            "2024": 220_000,
            "2025E": 285_000,
        },
        cash_and_equivalents={
            "2021": 25_000,
            "2022": 32_000,
            "2023": 45_000,
            "2024": 62_000,
            "2025E": 85_000,
        },
        total_debt={
            "2021": 45_000,
            "2022": 42_000,
            "2023": 38_000,
            "2024": 35_000,
            "2025E": 30_000,
        },
        # ── 현금흐름표 ──
        operating_cash_flow={
            "2021": 12_800,
            "2022": 17_640,
            "2023": 24_000,
            "2024": 33_480,
            "2025E": 43_200,
        },
        investing_cash_flow={
            "2021": -8_500,
            "2022": -10_200,
            "2023": -12_500,
            "2024": -15_500,
            "2025E": -19_200,
        },
        financing_cash_flow={
            "2021": -3_000,
            "2022": -2_500,
            "2023": -3_000,
            "2024": -3_500,
            "2025E": -4_000,
        },
        capex={
            "2021": 5_100,
            "2022": 6_120,
            "2023": 7_500,
            "2024": 9_300,
            "2025E": 11_520,
        },
        free_cash_flow={
            "2021": 7_700,
            "2022": 11_520,
            "2023": 16_500,
            "2024": 24_180,
            "2025E": 31_680,
        },
    )


def build_segment_revenue() -> SegmentRevenue:
    """사업부별 매출 (4개 세그먼트, 5개년)."""
    return SegmentRevenue(
        segments={
            "클라우드 인프라": {
                "2021": 34_000,
                "2022": 43_860,
                "2023": 56_250,
                "2024": 72_850,
                "2025E": 92_160,
            },
            "데이터 분석": {
                "2021": 21_250,
                "2022": 26_520,
                "2023": 33_750,
                "2024": 43_400,
                "2025E": 55_680,
            },
            "SI/컨설팅": {
                "2021": 17_000,
                "2022": 18_360,
                "2023": 21_250,
                "2024": 23_250,
                "2025E": 25_920,
            },
            "보안 솔루션": {
                "2021": 12_750,
                "2022": 13_260,
                "2023": 13_750,
                "2024": 15_500,
                "2025E": 18_240,
            },
        }
    )


def build_valuation_data() -> ValuationData:
    """밸류에이션 상세 데이터 — IRR/MOIC/민감도 포함."""
    return ValuationData(
        ev={
            "2023": 262_500,
            "2024": 356_500,
            "2025E": 460_800,
        },
        # Equity Value = EV - Gross Debt (현금 미차감 방식)
        # 표준 EV - Net Debt와 다름: 매수자 관점에서 인수 후 부채 상환만 반영
        equity_value={
            "2023": 224_500,  # 262,500 - 38,000
            "2024": 321_500,  # 356,500 - 35,000
            "2025E": 430_800,  # 460,800 - 30,000
        },
        ev_ebitda={
            "2023": 10.0,
            "2024": 10.0,
            "2025E": 10.0,
        },
        # PER: 동종업계 비교 기업 기반 참고 Multiple (EV 기반 산출값과 독립적으로 제공).
        # equity_value / net_income 직접 산출과 일치하지 않을 수 있다.
        pe_ratio={
            "2023": 17.5,
            "2024": 17.0,
            "2025E": 15.8,
        },
        ev_revenue={
            "2023": 2.1,
            "2024": 2.3,
            "2025E": 2.4,
        },
        irr_scenarios={
            "base": {
                "entry_ev_ebitda": 10.0,
                "exit_ev_ebitda": 10.0,
                "hold_years": 5,
                "ebitda_cagr": 0.20,
                "irr": 0.22,
            },
            "upside": {
                "entry_ev_ebitda": 10.0,
                "exit_ev_ebitda": 12.0,
                "hold_years": 5,
                "ebitda_cagr": 0.25,
                "irr": 0.32,
            },
            "downside": {
                "entry_ev_ebitda": 10.0,
                "exit_ev_ebitda": 8.0,
                "hold_years": 5,
                "ebitda_cagr": 0.12,
                "irr": 0.10,
            },
        },
        moic_scenarios={
            "base": 2.7,
            "upside": 3.9,
            "downside": 1.6,
        },
        exit_analysis={
            "trade_sale": {
                "probability": 0.50,
                "exit_ev_ebitda": 11.0,
                "expected_irr": 0.25,
            },
            "ipo": {
                "probability": 0.30,
                "exit_ev_ebitda": 14.0,
                "expected_irr": 0.35,
            },
            "secondary_sale": {
                "probability": 0.20,
                "exit_ev_ebitda": 9.0,
                "expected_irr": 0.15,
            },
        },
        sensitivity_data={
            "row_label": "Exit Multiple (EV/EBITDA)",
            "col_label": "EBITDA CAGR (%)",
            "row_values": [7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0],
            "col_values": [0.10, 0.15, 0.20, 0.25, 0.30],
            "matrix": [
                [1.0, 1.2, 1.5, 1.8, 2.2],
                [1.2, 1.5, 1.8, 2.2, 2.7],
                [1.4, 1.7, 2.1, 2.6, 3.2],
                [1.6, 2.0, 2.5, 3.1, 3.8],
                [1.8, 2.2, 2.8, 3.5, 4.3],
                [2.0, 2.5, 3.1, 3.9, 4.8],
                [2.2, 2.7, 3.5, 4.3, 5.4],
            ],
        },
    )


def build_charts() -> dict[str, list[ChartData]]:
    """섹션별 차트 데이터 (5종+)."""
    return {
        "financial_analysis": [
            ChartData(
                chart_type="combo",
                title="매출액 및 영업이익률 추이",
                data={
                    "categories": ["2021", "2022", "2023", "2024", "2025E"],
                    "bar_series": [
                        {
                            "name": "매출액",
                            "values": [85_000, 102_000, 125_000, 155_000, 192_000],
                        }
                    ],
                    "line_series": [
                        {
                            "name": "영업이익률",
                            "values": [0.120, 0.140, 0.160, 0.180, 0.190],
                        }
                    ],
                },
            ),
            ChartData(
                chart_type="line",
                title="EBITDA 추이 (백만원)",
                data={
                    "x": ["2021", "2022", "2023", "2024", "2025E"],
                    "series": [
                        {
                            "name": "EBITDA",
                            "values": [14_450, 19_380, 26_250, 35_650, 46_080],
                        }
                    ],
                },
            ),
        ],
        "market_overview": [
            ChartData(
                chart_type="donut",
                title="IT 서비스 시장 점유율 (2024)",
                data={
                    "labels": [
                        "삼성SDS",
                        "LG CNS",
                        "넥스트테크",
                        "SK C&C",
                        "포스코DX",
                        "기타",
                    ],
                    "values": [0.22, 0.18, 0.08, 0.07, 0.05, 0.40],
                },
            ),
        ],
        "shareholder_structure": [
            ChartData(
                chart_type="donut",
                title="주주 구성 현황",
                data={
                    "labels": [
                        "넥스트캐피탈 PE",
                        "김진수 대표",
                        "기관투자자",
                        "임직원 ESOP",
                        "소액주주",
                    ],
                    "values": [0.45, 0.20, 0.15, 0.08, 0.12],
                },
            ),
        ],
        "business_overview": [
            ChartData(
                chart_type="stacked_bar",
                title="사업부별 매출 추이",
                data={
                    "categories": ["2021", "2022", "2023", "2024", "2025E"],
                    "series": [
                        {
                            "name": "클라우드 인프라",
                            "values": [34_000, 43_860, 56_250, 72_850, 92_160],
                        },
                        {
                            "name": "데이터 분석",
                            "values": [21_250, 26_520, 33_750, 43_400, 55_680],
                        },
                        {
                            "name": "SI/컨설팅",
                            "values": [17_000, 18_360, 21_250, 23_250, 25_920],
                        },
                        {
                            "name": "보안 솔루션",
                            "values": [12_750, 13_260, 13_750, 15_500, 18_240],
                        },
                    ],
                },
            ),
        ],
        "valuation": [
            ChartData(
                chart_type="hbar",
                title="동종업계 EV/EBITDA 비교",
                data={
                    "categories": [
                        "삼성SDS",
                        "LG CNS",
                        "넥스트테크",
                        "SK C&C",
                        "포스코DX",
                    ],
                    "values": [12.5, 11.0, 10.0, 9.5, 8.0],
                },
            ),
        ],
    }


def build_source_citations() -> dict[str, list[SourceCitation]]:
    """섹션별 출처 메타데이터 (5+개 섹션)."""
    return {
        "financial_analysis": [
            SourceCitation(
                source_name="금융감독원 전자공시시스템",
                url="https://dart.fss.or.kr",
                access_date="2026-01-15",
                document_title="넥스트테크 2024년 사업보고서",
            ),
            SourceCitation(
                source_name="넥스트테크 내부 관리회계 자료",
                access_date="2026-01-20",
            ),
        ],
        "market_overview": [
            SourceCitation(
                source_name="한국IDC",
                url="https://www.idc.com/kr",
                access_date="2026-01-10",
                document_title="2025 국내 IT 서비스 시장 전망 보고서",
            ),
            SourceCitation(
                source_name="과학기술정보통신부",
                access_date="2025-12",
                document_title="2024 ICT 산업 통계연보",
            ),
        ],
        "company_overview": [
            SourceCitation(
                source_name="넥스트테크 홈페이지",
                url="https://www.nexttech.co.kr",
                access_date="2026-01-05",
            ),
        ],
        "valuation": [
            SourceCitation(
                source_name="Bloomberg Terminal",
                access_date="2026-01-15",
                document_title="IT 서비스 업종 Comparable Analysis",
            ),
        ],
        "investment_highlights": [
            SourceCitation(
                source_name="Gartner",
                access_date="2025-11",
                document_title="Magic Quadrant for Managed Cloud Services — Korea 2025",
            ),
        ],
        "management_team": [
            SourceCitation(
                source_name="넥스트테크 2024년 사업보고서",
                access_date="2026-01-15",
                document_title="임원현황",
            ),
        ],
    }
