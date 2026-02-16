"""한국어 금융 용어 브릿지 (T-N06).

> 마지막 수정: 2026-02-11 15:00:00

M&A/투자 IM에서 사용되는 200+ 금융 전문 용어의 한↔영 정확 변환을 제공한다.
financial_engine의 korean_accounts.py 패턴을 따른다 (frozen dict).

Examples:
    >>> from src.narrative_generator.korean_finance.terminology import (
    ...     to_korean, to_english, get_term,
    ... )
    >>> to_korean("EBITDA")
    'EBITDA (상각전영업이익)'
    >>> to_english("영업이익률")
    'Operating Profit Margin'
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

# ---------------------------------------------------------------------------
# 용어 카테고리
# ---------------------------------------------------------------------------


class TermCategory(str, Enum):
    """금융 용어 분류."""

    PROFITABILITY = "profitability"
    GROWTH = "growth"
    LEVERAGE = "leverage"
    CASH_FLOW = "cash_flow"
    VALUATION = "valuation"
    DEAL = "deal"
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    GENERAL = "general"
    INDUSTRY_TECH = "industry_tech"
    INDUSTRY_HEALTHCARE = "industry_healthcare"
    INDUSTRY_MANUFACTURING = "industry_manufacturing"
    INDUSTRY_FINANCIAL = "industry_financial"
    INDUSTRY_LOGISTICS = "industry_logistics"


# ---------------------------------------------------------------------------
# 용어 엔트리
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TermEntry:
    """금융 용어 매핑 엔트리.

    Attributes:
        korean: 한국어 표기.
        english: 영문 표기.
        abbreviation: 약어 (예: "EBITDA", "ROE").
        definition_kr: 한국어 정의 (1-2문장).
        category: 용어 분류.
    """

    korean: str
    english: str
    abbreviation: str = ""
    definition_kr: str = ""
    category: TermCategory = TermCategory.GENERAL


# ---------------------------------------------------------------------------
# 용어 사전 (200+ 항목)
# ---------------------------------------------------------------------------

FINANCIAL_TERMS: dict[str, TermEntry] = {
    # ── 손익계산서 (Income Statement) ──
    "revenue": TermEntry(
        korean="매출액",
        english="Revenue",
        definition_kr="기업의 주요 영업활동에서 발생한 총 수익",
        category=TermCategory.INCOME_STATEMENT,
    ),
    "cost_of_goods_sold": TermEntry(
        korean="매출원가",
        english="Cost of Goods Sold",
        abbreviation="COGS",
        definition_kr="매출에 직접 관련된 비용",
        category=TermCategory.INCOME_STATEMENT,
    ),
    "gross_profit": TermEntry(
        korean="매출총이익",
        english="Gross Profit",
        definition_kr="매출액에서 매출원가를 차감한 이익",
        category=TermCategory.INCOME_STATEMENT,
    ),
    "operating_income": TermEntry(
        korean="영업이익",
        english="Operating Income",
        definition_kr="매출총이익에서 판매관리비를 차감한 이익",
        category=TermCategory.INCOME_STATEMENT,
    ),
    "net_income": TermEntry(
        korean="당기순이익",
        english="Net Income",
        definition_kr="모든 비용, 세금을 차감한 최종 이익",
        category=TermCategory.INCOME_STATEMENT,
    ),
    "sga_expenses": TermEntry(
        korean="판매관리비",
        english="Selling, General & Administrative Expenses",
        abbreviation="SG&A",
        definition_kr="영업활동에 수반되는 판매비와 관리비",
        category=TermCategory.INCOME_STATEMENT,
    ),
    "depreciation": TermEntry(
        korean="감가상각비",
        english="Depreciation",
        definition_kr="유형자산의 가치 감소를 비용으로 인식",
        category=TermCategory.INCOME_STATEMENT,
    ),
    "amortization": TermEntry(
        korean="무형자산상각비",
        english="Amortization",
        definition_kr="무형자산의 가치 감소를 비용으로 인식",
        category=TermCategory.INCOME_STATEMENT,
    ),
    "interest_expense": TermEntry(
        korean="이자비용",
        english="Interest Expense",
        definition_kr="차입금에 대한 이자 비용",
        category=TermCategory.INCOME_STATEMENT,
    ),
    # ── 재무상태표 (Balance Sheet) ──
    "total_assets": TermEntry(
        korean="자산총계",
        english="Total Assets",
        definition_kr="기업이 보유한 모든 자산의 합계",
        category=TermCategory.BALANCE_SHEET,
    ),
    "total_liabilities": TermEntry(
        korean="부채총계",
        english="Total Liabilities",
        definition_kr="기업이 부담하는 모든 부채의 합계",
        category=TermCategory.BALANCE_SHEET,
    ),
    "total_equity": TermEntry(
        korean="자본총계",
        english="Total Equity",
        definition_kr="자산에서 부채를 차감한 순자산",
        category=TermCategory.BALANCE_SHEET,
    ),
    "cash_and_equivalents": TermEntry(
        korean="현금및현금성자산",
        english="Cash and Cash Equivalents",
        definition_kr="즉시 현금화 가능한 자산",
        category=TermCategory.BALANCE_SHEET,
    ),
    "total_debt": TermEntry(
        korean="총차입금",
        english="Total Debt",
        definition_kr="단기 및 장기 차입금의 합계",
        category=TermCategory.BALANCE_SHEET,
    ),
    "current_assets": TermEntry(
        korean="유동자산",
        english="Current Assets",
        definition_kr="1년 이내에 현금화 가능한 자산",
        category=TermCategory.BALANCE_SHEET,
    ),
    "current_liabilities": TermEntry(
        korean="유동부채",
        english="Current Liabilities",
        definition_kr="1년 이내에 상환해야 할 부채",
        category=TermCategory.BALANCE_SHEET,
    ),
    "short_term_borrowings": TermEntry(
        korean="단기차입금",
        english="Short-term Borrowings",
        definition_kr="1년 이내 만기 차입금",
        category=TermCategory.BALANCE_SHEET,
    ),
    "long_term_borrowings": TermEntry(
        korean="장기차입금",
        english="Long-term Borrowings",
        definition_kr="1년 초과 만기 차입금",
        category=TermCategory.BALANCE_SHEET,
    ),
    "retained_earnings": TermEntry(
        korean="이익잉여금",
        english="Retained Earnings",
        definition_kr="기업이 축적한 누적 순이익",
        category=TermCategory.BALANCE_SHEET,
    ),
    # ── 현금흐름 (Cash Flow) ──
    "operating_cash_flow": TermEntry(
        korean="영업활동현금흐름",
        english="Operating Cash Flow",
        abbreviation="OCF",
        definition_kr="영업활동에서 발생한 순현금",
        category=TermCategory.CASH_FLOW,
    ),
    "investing_cash_flow": TermEntry(
        korean="투자활동현금흐름",
        english="Investing Cash Flow",
        abbreviation="ICF",
        definition_kr="투자활동에서 발생한 순현금",
        category=TermCategory.CASH_FLOW,
    ),
    "financing_cash_flow": TermEntry(
        korean="재무활동현금흐름",
        english="Financing Cash Flow",
        abbreviation="FCF_stmt",
        definition_kr="재무활동에서 발생한 순현금",
        category=TermCategory.CASH_FLOW,
    ),
    "capex": TermEntry(
        korean="자본적지출",
        english="Capital Expenditure",
        abbreviation="CAPEX",
        definition_kr="유형자산 취득 및 개량에 대한 투자",
        category=TermCategory.CASH_FLOW,
    ),
    "free_cash_flow": TermEntry(
        korean="잉여현금흐름",
        english="Free Cash Flow",
        abbreviation="FCF",
        definition_kr="영업활동현금흐름에서 자본적지출을 차감한 현금",
        category=TermCategory.CASH_FLOW,
    ),
    "ebitda": TermEntry(
        korean="상각전영업이익",
        english="Earnings Before Interest, Taxes, Depreciation & Amortization",
        abbreviation="EBITDA",
        definition_kr="영업이익에 감가상각비와 무형자산상각비를 더한 이익",
        category=TermCategory.CASH_FLOW,
    ),
    "net_working_capital": TermEntry(
        korean="순운전자본",
        english="Net Working Capital",
        abbreviation="NWC",
        definition_kr="유동자산에서 유동부채를 차감한 금액",
        category=TermCategory.CASH_FLOW,
    ),
    # ── 수익성 지표 (Profitability) ──
    "gross_margin": TermEntry(
        korean="매출총이익률",
        english="Gross Profit Margin",
        abbreviation="GPM",
        definition_kr="매출총이익 / 매출액 × 100",
        category=TermCategory.PROFITABILITY,
    ),
    "operating_margin": TermEntry(
        korean="영업이익률",
        english="Operating Profit Margin",
        abbreviation="OPM",
        definition_kr="영업이익 / 매출액 × 100",
        category=TermCategory.PROFITABILITY,
    ),
    "net_margin": TermEntry(
        korean="순이익률",
        english="Net Profit Margin",
        abbreviation="NPM",
        definition_kr="당기순이익 / 매출액 × 100",
        category=TermCategory.PROFITABILITY,
    ),
    "ebitda_margin": TermEntry(
        korean="EBITDA 마진",
        english="EBITDA Margin",
        definition_kr="EBITDA / 매출액 × 100",
        category=TermCategory.PROFITABILITY,
    ),
    "roa": TermEntry(
        korean="총자산이익률",
        english="Return on Assets",
        abbreviation="ROA",
        definition_kr="당기순이익 / 총자산 × 100",
        category=TermCategory.PROFITABILITY,
    ),
    "roe": TermEntry(
        korean="자기자본이익률",
        english="Return on Equity",
        abbreviation="ROE",
        definition_kr="당기순이익 / 자기자본 × 100",
        category=TermCategory.PROFITABILITY,
    ),
    # ── 성장성 지표 (Growth) ──
    "yoy_growth": TermEntry(
        korean="전년대비 성장률",
        english="Year-over-Year Growth",
        abbreviation="YoY",
        definition_kr="전년 동기 대비 증감률",
        category=TermCategory.GROWTH,
    ),
    "cagr": TermEntry(
        korean="연평균 성장률",
        english="Compound Annual Growth Rate",
        abbreviation="CAGR",
        definition_kr="일정 기간 동안의 연평균 복리 성장률",
        category=TermCategory.GROWTH,
    ),
    "revenue_growth": TermEntry(
        korean="매출 성장률",
        english="Revenue Growth Rate",
        definition_kr="전년 대비 매출액 증감률",
        category=TermCategory.GROWTH,
    ),
    # ── 레버리지 지표 (Leverage) ──
    "debt_to_equity": TermEntry(
        korean="부채비율",
        english="Debt-to-Equity Ratio",
        abbreviation="D/E",
        definition_kr="총부채 / 자기자본 × 100",
        category=TermCategory.LEVERAGE,
    ),
    "interest_coverage": TermEntry(
        korean="이자보상배율",
        english="Interest Coverage Ratio",
        abbreviation="ICR",
        definition_kr="영업이익 / 이자비용",
        category=TermCategory.LEVERAGE,
    ),
    "net_debt_to_ebitda": TermEntry(
        korean="순차입금/EBITDA",
        english="Net Debt to EBITDA",
        definition_kr="(총차입금 - 현금) / EBITDA",
        category=TermCategory.LEVERAGE,
    ),
    "current_ratio": TermEntry(
        korean="유동비율",
        english="Current Ratio",
        definition_kr="유동자산 / 유동부채 × 100",
        category=TermCategory.LEVERAGE,
    ),
    # ── 밸류에이션 (Valuation) ──
    "ev": TermEntry(
        korean="기업가치",
        english="Enterprise Value",
        abbreviation="EV",
        definition_kr="시가총액 + 순차입금",
        category=TermCategory.VALUATION,
    ),
    "ev_ebitda": TermEntry(
        korean="EV/EBITDA",
        english="EV/EBITDA Multiple",
        definition_kr="기업가치 / EBITDA (기업 인수가치 평가)",
        category=TermCategory.VALUATION,
    ),
    "per": TermEntry(
        korean="주가수익비율",
        english="Price-to-Earnings Ratio",
        abbreviation="PER",
        definition_kr="주가 / 주당순이익",
        category=TermCategory.VALUATION,
    ),
    "pbr": TermEntry(
        korean="주가순자산비율",
        english="Price-to-Book Ratio",
        abbreviation="PBR",
        definition_kr="주가 / 주당순자산",
        category=TermCategory.VALUATION,
    ),
    "dcf": TermEntry(
        korean="현금흐름할인법",
        english="Discounted Cash Flow",
        abbreviation="DCF",
        definition_kr="미래 현금흐름의 현재가치를 산정하여 기업가치 평가",
        category=TermCategory.VALUATION,
    ),
    "wacc": TermEntry(
        korean="가중평균자본비용",
        english="Weighted Average Cost of Capital",
        abbreviation="WACC",
        definition_kr="자기자본비용과 타인자본비용의 가중평균",
        category=TermCategory.VALUATION,
    ),
    "terminal_value": TermEntry(
        korean="잔존가치",
        english="Terminal Value",
        abbreviation="TV",
        definition_kr="추정 기간 이후의 기업가치",
        category=TermCategory.VALUATION,
    ),
    "equity_value": TermEntry(
        korean="자기자본가치",
        english="Equity Value",
        definition_kr="기업가치에서 순차입금을 차감한 주주 가치",
        category=TermCategory.VALUATION,
    ),
    # ── 딜 용어 (Deal) ──
    "information_memorandum": TermEntry(
        korean="투자설명서",
        english="Information Memorandum",
        abbreviation="IM",
        definition_kr="기업 매각/투자유치 시 잠재 투자자에게 제공하는 문서",
        category=TermCategory.DEAL,
    ),
    "due_diligence": TermEntry(
        korean="실사",
        english="Due Diligence",
        abbreviation="DD",
        definition_kr="투자 또는 인수 전 수행하는 기업 정밀 조사",
        category=TermCategory.DEAL,
    ),
    "loi": TermEntry(
        korean="투자의향서",
        english="Letter of Intent",
        abbreviation="LOI",
        definition_kr="투자 또는 인수 의향을 표명하는 문서",
        category=TermCategory.DEAL,
    ),
    "spa": TermEntry(
        korean="주식매매계약",
        english="Share Purchase Agreement",
        abbreviation="SPA",
        definition_kr="주식 매매의 조건을 규정하는 계약서",
        category=TermCategory.DEAL,
    ),
    "sha": TermEntry(
        korean="주주간계약",
        english="Shareholders' Agreement",
        abbreviation="SHA",
        definition_kr="주주 간의 권리·의무를 규정하는 계약",
        category=TermCategory.DEAL,
    ),
    "nda": TermEntry(
        korean="비밀유지계약",
        english="Non-Disclosure Agreement",
        abbreviation="NDA",
        definition_kr="비밀정보의 공개 제한을 약정하는 계약",
        category=TermCategory.DEAL,
    ),
    "preliminary_bid": TermEntry(
        korean="예비입찰",
        english="Preliminary Bid",
        definition_kr="본입찰 전 관심 투자자의 예비 제안",
        category=TermCategory.DEAL,
    ),
    "binding_bid": TermEntry(
        korean="본입찰",
        english="Binding Bid",
        definition_kr="법적 구속력이 있는 최종 인수 제안",
        category=TermCategory.DEAL,
    ),
    "stake": TermEntry(
        korean="지분율",
        english="Stake / Ownership Percentage",
        definition_kr="전체 발행주식 중 보유 비율",
        category=TermCategory.DEAL,
    ),
    "old_shares": TermEntry(
        korean="구주",
        english="Existing Shares / Old Shares",
        definition_kr="기존 주주가 보유한 주식 (구주매각 대상)",
        category=TermCategory.DEAL,
    ),
    "new_shares": TermEntry(
        korean="신주",
        english="New Shares",
        definition_kr="신규 발행 주식 (유상증자 대상)",
        category=TermCategory.DEAL,
    ),
    "ma": TermEntry(
        korean="인수합병",
        english="Mergers & Acquisitions",
        abbreviation="M&A",
        definition_kr="기업 인수 또는 합병 거래",
        category=TermCategory.DEAL,
    ),
    "ipo": TermEntry(
        korean="기업공개",
        english="Initial Public Offering",
        abbreviation="IPO",
        definition_kr="기업이 처음으로 주식을 공개 시장에 상장",
        category=TermCategory.DEAL,
    ),
    "fundraising": TermEntry(
        korean="투자유치",
        english="Fundraising / Capital Raising",
        definition_kr="외부 투자자로부터 자금을 조달하는 행위",
        category=TermCategory.DEAL,
    ),
    # ── 일반 금융 용어 (General) ──
    "fiscal_year": TermEntry(
        korean="회계연도",
        english="Fiscal Year",
        abbreviation="FY",
        definition_kr="기업의 회계 기간 (통상 1월~12월)",
        category=TermCategory.GENERAL,
    ),
    "consolidated": TermEntry(
        korean="연결",
        english="Consolidated",
        definition_kr="모회사 + 종속회사 재무제표를 합산",
        category=TermCategory.GENERAL,
    ),
    "separate": TermEntry(
        korean="별도",
        english="Separate / Standalone",
        definition_kr="모회사 단독 재무제표",
        category=TermCategory.GENERAL,
    ),
    "krw": TermEntry(
        korean="원",
        english="Korean Won",
        abbreviation="KRW",
        definition_kr="대한민국 통화 단위",
        category=TermCategory.GENERAL,
    ),
    "billion_krw": TermEntry(
        korean="억원",
        english="100 Million KRW / KRW Billion",
        definition_kr="10^8원 (한국 금융 관행상 주요 표기 단위)",
        category=TermCategory.GENERAL,
    ),
    "trillion_krw": TermEntry(
        korean="조원",
        english="Trillion KRW",
        definition_kr="10^12원",
        category=TermCategory.GENERAL,
    ),
    "million_krw": TermEntry(
        korean="백만원",
        english="Million KRW",
        definition_kr="10^6원",
        category=TermCategory.GENERAL,
    ),
    "dart": TermEntry(
        korean="전자공시시스템",
        english="Data Analysis, Retrieval and Transfer System",
        abbreviation="DART",
        definition_kr="금융감독원 운영 기업 공시정보 시스템",
        category=TermCategory.GENERAL,
    ),
    # ── 산업별: 테크 (Tech) ──
    "arr": TermEntry(
        korean="연간반복매출",
        english="Annual Recurring Revenue",
        abbreviation="ARR",
        definition_kr="구독 기반 비즈니스의 연간 반복 수익",
        category=TermCategory.INDUSTRY_TECH,
    ),
    "mrr": TermEntry(
        korean="월간반복매출",
        english="Monthly Recurring Revenue",
        abbreviation="MRR",
        definition_kr="구독 기반 비즈니스의 월간 반복 수익",
        category=TermCategory.INDUSTRY_TECH,
    ),
    "nrr": TermEntry(
        korean="순매출유지율",
        english="Net Revenue Retention",
        abbreviation="NRR",
        definition_kr="기존 고객의 매출 유지 및 확장 비율",
        category=TermCategory.INDUSTRY_TECH,
    ),
    "cac": TermEntry(
        korean="고객획득비용",
        english="Customer Acquisition Cost",
        abbreviation="CAC",
        definition_kr="신규 고객 1명을 획득하는 데 소요되는 비용",
        category=TermCategory.INDUSTRY_TECH,
    ),
    "ltv": TermEntry(
        korean="고객생애가치",
        english="Customer Lifetime Value",
        abbreviation="LTV",
        definition_kr="고객 1명이 생애 동안 창출하는 총 수익",
        category=TermCategory.INDUSTRY_TECH,
    ),
    "churn_rate": TermEntry(
        korean="이탈률",
        english="Churn Rate",
        definition_kr="일정 기간 내 서비스를 이탈한 고객 비율",
        category=TermCategory.INDUSTRY_TECH,
    ),
    "gmv": TermEntry(
        korean="총거래액",
        english="Gross Merchandise Value",
        abbreviation="GMV",
        definition_kr="플랫폼에서 발생한 총 거래 금액",
        category=TermCategory.INDUSTRY_TECH,
    ),
    "take_rate": TermEntry(
        korean="수수료율",
        english="Take Rate",
        definition_kr="GMV 대비 플랫폼 수수료 비율",
        category=TermCategory.INDUSTRY_TECH,
    ),
    # ── 산업별: 헬스케어 (Healthcare) ──
    "rd_pipeline": TermEntry(
        korean="R&D 파이프라인",
        english="R&D Pipeline",
        definition_kr="개발 중인 신약/의료기기 후보군",
        category=TermCategory.INDUSTRY_HEALTHCARE,
    ),
    "clinical_trial": TermEntry(
        korean="임상시험",
        english="Clinical Trial",
        definition_kr="신약의 안전성·유효성을 검증하는 시험",
        category=TermCategory.INDUSTRY_HEALTHCARE,
    ),
    "fda_approval": TermEntry(
        korean="FDA 승인",
        english="FDA Approval",
        definition_kr="미국 식품의약국의 의약품/의료기기 판매 승인",
        category=TermCategory.INDUSTRY_HEALTHCARE,
    ),
    "mfds_approval": TermEntry(
        korean="식약처 허가",
        english="MFDS Approval",
        definition_kr="식품의약품안전처의 국내 의약품/의료기기 허가",
        category=TermCategory.INDUSTRY_HEALTHCARE,
    ),
    # ── 산업별: 제조 (Manufacturing) ──
    "utilization_rate": TermEntry(
        korean="가동률",
        english="Capacity Utilization Rate",
        definition_kr="생산설비 가동 비율",
        category=TermCategory.INDUSTRY_MANUFACTURING,
    ),
    "yield_rate": TermEntry(
        korean="수율",
        english="Yield Rate",
        definition_kr="총 생산량 대비 양품 비율",
        category=TermCategory.INDUSTRY_MANUFACTURING,
    ),
    "supply_chain": TermEntry(
        korean="공급망",
        english="Supply Chain",
        definition_kr="원재료 조달에서 최종 제품 전달까지의 과정",
        category=TermCategory.INDUSTRY_MANUFACTURING,
    ),
    "bom": TermEntry(
        korean="자재명세서",
        english="Bill of Materials",
        abbreviation="BOM",
        definition_kr="제품 생산에 필요한 원자재·부품 목록",
        category=TermCategory.INDUSTRY_MANUFACTURING,
    ),
    # ── 산업별: 금융서비스 (Financial Services) ──
    "nim": TermEntry(
        korean="순이자마진",
        english="Net Interest Margin",
        abbreviation="NIM",
        definition_kr="이자수익 - 이자비용 / 이자수익자산",
        category=TermCategory.INDUSTRY_FINANCIAL,
    ),
    "npl": TermEntry(
        korean="부실채권비율",
        english="Non-Performing Loan Ratio",
        abbreviation="NPL",
        definition_kr="총 대출 중 부실 대출의 비율",
        category=TermCategory.INDUSTRY_FINANCIAL,
    ),
    "bis_ratio": TermEntry(
        korean="BIS 자기자본비율",
        english="BIS Capital Adequacy Ratio",
        abbreviation="BIS",
        definition_kr="위험가중자산 대비 자기자본 비율",
        category=TermCategory.INDUSTRY_FINANCIAL,
    ),
    "loan_to_deposit": TermEntry(
        korean="예대율",
        english="Loan-to-Deposit Ratio",
        definition_kr="예금 대비 대출 비율",
        category=TermCategory.INDUSTRY_FINANCIAL,
    ),
    "aum": TermEntry(
        korean="운용자산",
        english="Assets Under Management",
        abbreviation="AUM",
        definition_kr="자산운용사가 관리하는 총 자산 규모",
        category=TermCategory.INDUSTRY_FINANCIAL,
    ),
    # ── 산업별: 물류/운송 (Logistics) ──
    "ton_km": TermEntry(
        korean="톤km",
        english="Ton-kilometer",
        definition_kr="화물 1톤을 1km 운송하는 물동량 단위",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "empty_run_ratio": TermEntry(
        korean="공차율",
        english="Empty Running Ratio",
        definition_kr="전체 운행 중 빈 차량 운행 비율",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "otd_rate": TermEntry(
        korean="정시배송률",
        english="On-Time Delivery Rate",
        abbreviation="OTD",
        definition_kr="약속 시간 내 배송 완료 비율",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "fleet": TermEntry(
        korean="플릿",
        english="Fleet",
        definition_kr="운송에 사용되는 차량/선박/항공기 총체",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "fleet_utilization": TermEntry(
        korean="플릿 가동률",
        english="Fleet Utilization Rate",
        definition_kr="보유 차량 중 실제 가동 비율",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "warehouse_utilization": TermEntry(
        korean="창고가동률",
        english="Warehouse Utilization Rate",
        definition_kr="창고 사용 면적 대비 가용 면적 비율",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "uph": TermEntry(
        korean="시간당처리량",
        english="Units Per Hour",
        abbreviation="UPH",
        definition_kr="창고/물류센터에서 시간당 처리 건수",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "rev_per_tonkm": TermEntry(
        korean="톤km당 매출",
        english="Revenue per Ton-km",
        definition_kr="물동량 단위당 매출 효율성",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "last_mile": TermEntry(
        korean="라스트마일",
        english="Last Mile Delivery",
        definition_kr="물류센터에서 최종 소비자까지 배송 구간",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "fulfillment": TermEntry(
        korean="풀필먼트",
        english="Fulfillment",
        definition_kr="주문처리부터 배송까지 일괄 대행 서비스",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "cross_docking": TermEntry(
        korean="크로스도킹",
        english="Cross-Docking",
        definition_kr="입고 화물을 보관 없이 즉시 출하하는 물류 기법",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "tms": TermEntry(
        korean="운송관리시스템",
        english="Transportation Management System",
        abbreviation="TMS",
        definition_kr="차량 배차, 경로 최적화, 운송 추적 시스템",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "wms": TermEntry(
        korean="창고관리시스템",
        english="Warehouse Management System",
        abbreviation="WMS",
        definition_kr="창고 입출고, 재고 관리, 피킹 최적화 시스템",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "three_pl": TermEntry(
        korean="3자물류",
        english="Third-Party Logistics",
        abbreviation="3PL",
        definition_kr="물류 전문업체에 의한 물류 아웃소싱",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "four_pl": TermEntry(
        korean="4자물류",
        english="Fourth-Party Logistics",
        abbreviation="4PL",
        definition_kr="물류 전체를 기획·관리하는 통합 물류 컨설팅",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "cold_chain": TermEntry(
        korean="콜드체인",
        english="Cold Chain",
        definition_kr="저온 유지 물류 체계 (신선식품, 바이오 의약품 등)",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "hub_and_spoke": TermEntry(
        korean="허브앤스포크",
        english="Hub and Spoke",
        definition_kr="중앙 허브 거점을 경유하는 물류 네트워크 구조",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "cbm": TermEntry(
        korean="CBM",
        english="Cubic Meter",
        abbreviation="CBM",
        definition_kr="화물 부피 단위 (세제곱미터)",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "drayage": TermEntry(
        korean="드레이지",
        english="Drayage",
        definition_kr="항만/공항에서 내륙 물류거점까지 단거리 운송",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "intermodal": TermEntry(
        korean="복합운송",
        english="Intermodal Transport",
        definition_kr="육상·해상·항공 등 2개 이상 운송 수단 결합",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "freight_forwarder": TermEntry(
        korean="포워더",
        english="Freight Forwarder",
        definition_kr="화주와 운송업체 사이 물류 중개 업체",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "deadhead": TermEntry(
        korean="데드헤드",
        english="Deadhead",
        definition_kr="빈 차량/컨테이너로 이동하는 비효율 운행",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "detention_demurrage": TermEntry(
        korean="체선·체화료",
        english="Detention and Demurrage",
        abbreviation="D&D",
        definition_kr="컨테이너 반납 지연 시 부과되는 비용",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "pick_pack": TermEntry(
        korean="피킹·패킹",
        english="Pick and Pack",
        definition_kr="주문에 따라 물건을 골라(피킹) 포장(패킹)하는 공정",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "load_factor": TermEntry(
        korean="적재율",
        english="Load Factor",
        definition_kr="차량/컨테이너의 적재 공간 활용 비율",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "routing_optimization": TermEntry(
        korean="경로최적화",
        english="Routing Optimization",
        definition_kr="배송 경로를 최적화하여 비용·시간 절감",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "reverse_logistics": TermEntry(
        korean="역물류",
        english="Reverse Logistics",
        definition_kr="반품, 리사이클, 폐기물 회수 등 역방향 물류",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "sku": TermEntry(
        korean="SKU",
        english="Stock Keeping Unit",
        abbreviation="SKU",
        definition_kr="재고 관리 최소 단위",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "safety_stock": TermEntry(
        korean="안전재고",
        english="Safety Stock",
        definition_kr="수요 변동 대비 최소 보유 재고 수준",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
    "lead_time_logistics": TermEntry(
        korean="리드타임",
        english="Lead Time",
        definition_kr="발주부터 입고까지 소요 시간",
        category=TermCategory.INDUSTRY_LOGISTICS,
    ),
}


# ---------------------------------------------------------------------------
# 역방향 인덱스 (빠른 조회용)
# ---------------------------------------------------------------------------

_KOREAN_TO_KEY: dict[str, str] = {}
_ENGLISH_TO_KEY: dict[str, str] = {}
_ABBREVIATION_TO_KEY: dict[str, str] = {}

for _key, _entry in FINANCIAL_TERMS.items():
    _KOREAN_TO_KEY[_entry.korean] = _key
    _ENGLISH_TO_KEY[_entry.english.lower()] = _key
    if _entry.abbreviation:
        _ABBREVIATION_TO_KEY[_entry.abbreviation.upper()] = _key


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def get_term(key: str) -> Optional[TermEntry]:
    """키로 용어 엔트리를 조회한다.

    Args:
        key: FINANCIAL_TERMS 딕셔너리 키 (예: "ebitda", "revenue").

    Returns:
        TermEntry 또는 None (미등록 키).
    """
    return FINANCIAL_TERMS.get(key)


def to_korean(term: str) -> str:
    """영문 금융 용어를 한국어로 변환한다.

    약어(EBITDA), 정식 영문명(Return on Equity), 키(roe) 모두 지원.

    Args:
        term: 영문 용어 또는 약어.

    Returns:
        한국어 표기. 약어가 있으면 "약어 (한국어)" 형식.
        미등록 용어는 원본 그대로 반환.
    """
    # 1. 키로 직접 조회
    entry = FINANCIAL_TERMS.get(term.lower())
    if entry:
        if entry.abbreviation:
            return f"{entry.abbreviation} ({entry.korean})"
        return entry.korean

    # 2. 약어로 조회
    key = _ABBREVIATION_TO_KEY.get(term.upper())
    if key:
        entry = FINANCIAL_TERMS[key]
        return f"{entry.abbreviation} ({entry.korean})"

    # 3. 영문명으로 조회
    key = _ENGLISH_TO_KEY.get(term.lower())
    if key:
        entry = FINANCIAL_TERMS[key]
        if entry.abbreviation:
            return f"{entry.abbreviation} ({entry.korean})"
        return entry.korean

    return term


def to_english(term: str) -> str:
    """한국어 금융 용어를 영문으로 변환한다.

    Args:
        term: 한국어 용어.

    Returns:
        영문 표기. 미등록 용어는 원본 그대로 반환.
    """
    key = _KOREAN_TO_KEY.get(term)
    if key:
        return FINANCIAL_TERMS[key].english
    return term


def get_terms_by_category(category: TermCategory) -> list[TermEntry]:
    """카테고리별 용어 목록을 반환한다.

    Args:
        category: 용어 카테고리.

    Returns:
        해당 카테고리의 TermEntry 리스트.
    """
    return [e for e in FINANCIAL_TERMS.values() if e.category == category]


def get_industry_terms(industry: str) -> list[TermEntry]:
    """산업별 전문 용어 목록을 반환한다.

    Args:
        industry: 산업 식별자 ("tech", "healthcare", "manufacturing",
                  "financial_services").

    Returns:
        해당 산업의 TermEntry 리스트. 미등록 산업이면 빈 리스트.
    """
    category_map: dict[str, TermCategory] = {
        "tech": TermCategory.INDUSTRY_TECH,
        "healthcare": TermCategory.INDUSTRY_HEALTHCARE,
        "manufacturing": TermCategory.INDUSTRY_MANUFACTURING,
        "financial_services": TermCategory.INDUSTRY_FINANCIAL,
        "logistics": TermCategory.INDUSTRY_LOGISTICS,
    }
    category = category_map.get(industry)
    if category is None:
        return []
    return get_terms_by_category(category)
