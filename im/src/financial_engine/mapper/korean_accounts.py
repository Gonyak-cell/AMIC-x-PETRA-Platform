"""Korean Account Name Mapping Dictionary (T-F02).

DART API 재무제표에서 사용되는 한글 계정과목명을 표준 계정 코드(StandardAccount)로
매핑하는 사전. 200+ 엔트리를 포함하며, DART 전자공시 데이터에 실제로 등장하는
다양한 계정명 변형(동의어, 괄호 표기, 띄어쓰기 변형 등)을 커버합니다.

> 마지막 수정: 2026-02-09 16:02:43
"""

from __future__ import annotations

from src.financial_engine.mapper.chart_of_accounts import StandardAccount

# ============================================================================
# 한글 계정명 → 표준 계정 매핑 사전
# ============================================================================
#
# 규칙:
#   - 키: DART API 원본 한글 계정명 (strip 후 원문 그대로)
#   - 값: StandardAccount enum 멤버
#   - 동일 표준 계정에 대해 복수의 한글 키가 존재할 수 있음
#   - 괄호 표기, 띄어쓰기 변형, 연결/별도 차이 등을 모두 포함
#
# 카테고리 구분:
#   [IS]  손익계산서 (Income Statement)
#   [BS]  재무상태표 (Balance Sheet)
#   [CF]  현금흐름표 (Cash Flow Statement)
# ============================================================================

KOREAN_ACCOUNT_MAP: dict[str, StandardAccount] = {
    # ========================================================================
    # [IS] 손익계산서 — 매출/수익 (REVENUE)
    # ========================================================================
    "매출액": StandardAccount.REVENUE,
    "영업수익": StandardAccount.REVENUE,
    "순매출": StandardAccount.REVENUE,
    "매출": StandardAccount.REVENUE,
    "영업수익(매출액)": StandardAccount.REVENUE,
    "수익(매출액)": StandardAccount.REVENUE,
    "매출(수익)": StandardAccount.REVENUE,
    "순영업수익": StandardAccount.REVENUE,
    "매출액(영업수익)": StandardAccount.REVENUE,
    "영업이익(수익)": StandardAccount.REVENUE,
    "총매출액": StandardAccount.REVENUE,
    "수익": StandardAccount.REVENUE,
    "영업수익 합계": StandardAccount.REVENUE,
    "매출액 합계": StandardAccount.REVENUE,
    "제품매출액": StandardAccount.REVENUE,
    "상품매출액": StandardAccount.REVENUE,
    "용역매출액": StandardAccount.REVENUE,
    "서비스매출액": StandardAccount.REVENUE,
    "제품매출": StandardAccount.REVENUE,
    "상품매출": StandardAccount.REVENUE,
    "용역매출": StandardAccount.REVENUE,
    "서비스매출": StandardAccount.REVENUE,
    "총수익": StandardAccount.REVENUE,
    "순수익": StandardAccount.REVENUE,
    "매출 및 영업수익": StandardAccount.REVENUE,
    # ========================================================================
    # [IS] 손익계산서 — 매출원가 (COGS)
    # ========================================================================
    "매출원가": StandardAccount.COST_OF_GOODS_SOLD,
    "영업비용": StandardAccount.COST_OF_GOODS_SOLD,
    "매출비용": StandardAccount.COST_OF_GOODS_SOLD,
    "영업원가": StandardAccount.COST_OF_GOODS_SOLD,
    "제품매출원가": StandardAccount.COST_OF_GOODS_SOLD,
    "상품매출원가": StandardAccount.COST_OF_GOODS_SOLD,
    "용역매출원가": StandardAccount.COST_OF_GOODS_SOLD,
    "서비스매출원가": StandardAccount.COST_OF_GOODS_SOLD,
    "제조원가": StandardAccount.COST_OF_GOODS_SOLD,
    "매출원가 합계": StandardAccount.COST_OF_GOODS_SOLD,
    "원가": StandardAccount.COST_OF_GOODS_SOLD,
    "매출원가(영업비용)": StandardAccount.COST_OF_GOODS_SOLD,
    # ========================================================================
    # [IS] 손익계산서 — 매출총이익 (GROSS_PROFIT)
    # ========================================================================
    "매출총이익": StandardAccount.GROSS_PROFIT,
    "매출총손익": StandardAccount.GROSS_PROFIT,
    "매출총이익(손실)": StandardAccount.GROSS_PROFIT,
    "매출 총이익": StandardAccount.GROSS_PROFIT,
    "매출 총손익": StandardAccount.GROSS_PROFIT,
    "총이익": StandardAccount.GROSS_PROFIT,
    # ========================================================================
    # [IS] 손익계산서 — 판매비와관리비 (SGA_EXPENSES)
    # ========================================================================
    "판매비와관리비": StandardAccount.SGA_EXPENSES,
    "판관비": StandardAccount.SGA_EXPENSES,
    "판매비와 관리비": StandardAccount.SGA_EXPENSES,
    "판매관리비": StandardAccount.SGA_EXPENSES,
    "판매비및관리비": StandardAccount.SGA_EXPENSES,
    "판매비 및 관리비": StandardAccount.SGA_EXPENSES,
    "판매비": StandardAccount.SGA_EXPENSES,
    "관리비": StandardAccount.SGA_EXPENSES,
    "판매비와관리비 합계": StandardAccount.SGA_EXPENSES,
    "일반관리비": StandardAccount.SGA_EXPENSES,
    # ========================================================================
    # [IS] 손익계산서 — 영업이익 (OPERATING_INCOME)
    # ========================================================================
    "영업이익": StandardAccount.OPERATING_INCOME,
    "영업손익": StandardAccount.OPERATING_INCOME,
    "영업이익(손실)": StandardAccount.OPERATING_INCOME,
    "영업이익(손익)": StandardAccount.OPERATING_INCOME,
    "영업이익 합계": StandardAccount.OPERATING_INCOME,
    # ========================================================================
    # [IS] 손익계산서 — 감가상각비 (DEPRECIATION)
    # ========================================================================
    "감가상각비": StandardAccount.DEPRECIATION,
    "유형자산감가상각비": StandardAccount.DEPRECIATION,
    "감가상각": StandardAccount.DEPRECIATION,
    "감가상각비용": StandardAccount.DEPRECIATION,
    "유형자산 감가상각비": StandardAccount.DEPRECIATION,
    "사용권자산감가상각비": StandardAccount.DEPRECIATION,
    "사용권자산 감가상각비": StandardAccount.DEPRECIATION,
    # ========================================================================
    # [IS] 손익계산서 — 무형자산상각비 (AMORTIZATION)
    # ========================================================================
    "무형자산상각비": StandardAccount.AMORTIZATION,
    "상각비": StandardAccount.AMORTIZATION,
    "무형자산감가상각비": StandardAccount.AMORTIZATION,
    "무형자산 상각비": StandardAccount.AMORTIZATION,
    "무형자산 감가상각비": StandardAccount.AMORTIZATION,
    # ========================================================================
    # [IS] 손익계산서 — 이자비용 (INTEREST_EXPENSE)
    # ========================================================================
    "이자비용": StandardAccount.INTEREST_EXPENSE,
    "이자비용(금융비용)": StandardAccount.INTEREST_EXPENSE,
    "차입금이자": StandardAccount.INTEREST_EXPENSE,
    "사채이자": StandardAccount.INTEREST_EXPENSE,
    "이자 비용": StandardAccount.INTEREST_EXPENSE,
    "지급이자": StandardAccount.INTEREST_EXPENSE,
    "지급이자및할인료": StandardAccount.INTEREST_EXPENSE,
    "지급이자 및 할인료": StandardAccount.INTEREST_EXPENSE,
    # ========================================================================
    # [IS] 손익계산서 — 이자수익 (INTEREST_INCOME)
    # ========================================================================
    "이자수익": StandardAccount.INTEREST_INCOME,
    "이자수익(금융수익)": StandardAccount.INTEREST_INCOME,
    "이자 수익": StandardAccount.INTEREST_INCOME,
    "수입이자": StandardAccount.INTEREST_INCOME,
    "수입이자및배당금": StandardAccount.INTEREST_INCOME,
    "수입이자 및 배당금": StandardAccount.INTEREST_INCOME,
    # ========================================================================
    # [IS] 손익계산서 — 당기순이익 (NET_INCOME)
    # ========================================================================
    "당기순이익": StandardAccount.NET_INCOME,
    "당기순손익": StandardAccount.NET_INCOME,
    "순이익": StandardAccount.NET_INCOME,
    "당기순이익(손실)": StandardAccount.NET_INCOME,
    "연결당기순이익": StandardAccount.NET_INCOME,
    "당기순이익(손익)": StandardAccount.NET_INCOME,
    "분기순이익": StandardAccount.NET_INCOME,
    "반기순이익": StandardAccount.NET_INCOME,
    "당기 순이익": StandardAccount.NET_INCOME,
    "당기 순손익": StandardAccount.NET_INCOME,
    "연결 당기순이익": StandardAccount.NET_INCOME,
    "총포괄손익": StandardAccount.NET_INCOME,
    "당기총포괄손익": StandardAccount.NET_INCOME,
    "지배기업소유주지분순이익": StandardAccount.NET_INCOME,
    "지배기업 소유주지분 순이익": StandardAccount.NET_INCOME,
    # ========================================================================
    # [IS] 손익계산서 — 법인세비용 (INCOME_TAX)
    # ========================================================================
    "법인세비용": StandardAccount.INCOME_TAX_EXPENSE,
    "법인세": StandardAccount.INCOME_TAX_EXPENSE,
    "소득세비용": StandardAccount.INCOME_TAX_EXPENSE,
    "법인세 비용": StandardAccount.INCOME_TAX_EXPENSE,
    "법인세비용(수익)": StandardAccount.INCOME_TAX_EXPENSE,
    "법인세등": StandardAccount.INCOME_TAX_EXPENSE,
    # ========================================================================
    # [IS] 손익계산서 — 법인세차감전순이익 (INCOME_BEFORE_TAX)
    # ========================================================================
    "법인세비용차감전순이익": StandardAccount.INCOME_BEFORE_TAX,
    "세전순이익": StandardAccount.INCOME_BEFORE_TAX,
    "세전이익": StandardAccount.INCOME_BEFORE_TAX,
    "법인세비용차감전순손익": StandardAccount.INCOME_BEFORE_TAX,
    "법인세차감전순이익": StandardAccount.INCOME_BEFORE_TAX,
    "법인세비용차감전이익": StandardAccount.INCOME_BEFORE_TAX,
    "법인세비용 차감전 순이익": StandardAccount.INCOME_BEFORE_TAX,
    "법인세비용 차감전 순손익": StandardAccount.INCOME_BEFORE_TAX,
    "세전 순이익": StandardAccount.INCOME_BEFORE_TAX,
    "세전 이익": StandardAccount.INCOME_BEFORE_TAX,
    "법인세차감전이익": StandardAccount.INCOME_BEFORE_TAX,
    "법인세차감전순손익": StandardAccount.INCOME_BEFORE_TAX,
    # ========================================================================
    # [IS] 손익계산서 — 기타수익 (OTHER_INCOME)
    # ========================================================================
    "기타수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "기타영업외수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "기타 수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "기타영업외 수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "영업외수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "영업외 수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    # ========================================================================
    # [IS] 손익계산서 — 기타비용 (OTHER_EXPENSE)
    # ========================================================================
    "기타비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "기타영업외비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "기타 비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "기타영업외 비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "영업외비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "영업외 비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    # ========================================================================
    # [IS] 손익계산서 — 금융수익 (FINANCIAL_INCOME)
    # ========================================================================
    "금융수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "금융이익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "금융 수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "금융수익 합계": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "기타금융수익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    # ========================================================================
    # [IS] 손익계산서 — 금융비용 (FINANCIAL_EXPENSE)
    # ========================================================================
    "금융비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "금융원가": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "금융 비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "금융비용 합계": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "기타금융비용": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    # ========================================================================
    # [BS] 재무상태표 — 자산총계 (TOTAL_ASSETS)
    # ========================================================================
    "자산총계": StandardAccount.TOTAL_ASSETS,
    "총자산": StandardAccount.TOTAL_ASSETS,
    "자산 총계": StandardAccount.TOTAL_ASSETS,
    "자산합계": StandardAccount.TOTAL_ASSETS,
    "자산 합계": StandardAccount.TOTAL_ASSETS,
    # ========================================================================
    # [BS] 재무상태표 — 유동자산 (CURRENT_ASSETS)
    # ========================================================================
    "유동자산": StandardAccount.CURRENT_ASSETS,
    "유동자산 합계": StandardAccount.CURRENT_ASSETS,
    "유동 자산": StandardAccount.CURRENT_ASSETS,
    # ========================================================================
    # [BS] 재무상태표 — 비유동자산 (NON_CURRENT_ASSETS)
    # ========================================================================
    "비유동자산": StandardAccount.NON_CURRENT_ASSETS,
    "비유동자산 합계": StandardAccount.NON_CURRENT_ASSETS,
    "비유동 자산": StandardAccount.NON_CURRENT_ASSETS,
    "고정자산": StandardAccount.NON_CURRENT_ASSETS,
    # ========================================================================
    # [BS] 재무상태표 — 현금및현금성자산 (CASH_AND_EQUIVALENTS)
    # ========================================================================
    "현금및현금성자산": StandardAccount.CASH_AND_EQUIVALENTS,
    "현금 및 현금성자산": StandardAccount.CASH_AND_EQUIVALENTS,
    "현금및현금등가물": StandardAccount.CASH_AND_EQUIVALENTS,
    "현금 및 현금등가물": StandardAccount.CASH_AND_EQUIVALENTS,
    "현금및현금성 자산": StandardAccount.CASH_AND_EQUIVALENTS,
    "현금": StandardAccount.CASH_AND_EQUIVALENTS,
    "현금성자산": StandardAccount.CASH_AND_EQUIVALENTS,
    "현금과현금성자산": StandardAccount.CASH_AND_EQUIVALENTS,
    # ========================================================================
    # [BS] 재무상태표 — 단기금융상품 (SHORT_TERM_INVESTMENTS)
    # ========================================================================
    "단기금융상품": StandardAccount.SHORT_TERM_INVESTMENTS,
    "단기투자자산": StandardAccount.SHORT_TERM_INVESTMENTS,
    "단기금융자산": StandardAccount.SHORT_TERM_INVESTMENTS,
    "단기 금융상품": StandardAccount.SHORT_TERM_INVESTMENTS,
    "유동금융자산": StandardAccount.SHORT_TERM_INVESTMENTS,
    # ========================================================================
    # [BS] 재무상태표 — 매출채권 (TRADE_RECEIVABLES)
    # ========================================================================
    "매출채권": StandardAccount.ACCOUNTS_RECEIVABLE,
    "매출채권및기타채권": StandardAccount.ACCOUNTS_RECEIVABLE,
    "매출채권 및 기타채권": StandardAccount.ACCOUNTS_RECEIVABLE,
    "매출채권및기타수취채권": StandardAccount.ACCOUNTS_RECEIVABLE,
    "매출채권 및 기타수취채권": StandardAccount.ACCOUNTS_RECEIVABLE,
    "외상매출금": StandardAccount.ACCOUNTS_RECEIVABLE,
    "받을어음": StandardAccount.ACCOUNTS_RECEIVABLE,
    "받을어음및매출채권": StandardAccount.ACCOUNTS_RECEIVABLE,
    "받을어음 및 매출채권": StandardAccount.ACCOUNTS_RECEIVABLE,
    "매출채권및받을어음": StandardAccount.ACCOUNTS_RECEIVABLE,
    # ========================================================================
    # [BS] 재무상태표 — 재고자산 (INVENTORIES)
    # ========================================================================
    "재고자산": StandardAccount.INVENTORIES,
    "재고": StandardAccount.INVENTORIES,
    "재고자산 합계": StandardAccount.INVENTORIES,
    "상품": StandardAccount.INVENTORIES,
    "제품": StandardAccount.INVENTORIES,
    "원재료": StandardAccount.INVENTORIES,
    "재공품": StandardAccount.INVENTORIES,
    # ========================================================================
    # [BS] 재무상태표 — 기타유동자산 (OTHER_CURRENT_ASSETS)
    # ========================================================================
    "기타유동자산": StandardAccount.OTHER_CURRENT_ASSETS,
    "기타 유동자산": StandardAccount.OTHER_CURRENT_ASSETS,
    "기타유동자산 합계": StandardAccount.OTHER_CURRENT_ASSETS,
    "선급금": StandardAccount.OTHER_CURRENT_ASSETS,
    "선급비용": StandardAccount.OTHER_CURRENT_ASSETS,
    "미수금": StandardAccount.OTHER_CURRENT_ASSETS,
    "미수수익": StandardAccount.OTHER_CURRENT_ASSETS,
    # ========================================================================
    # [BS] 재무상태표 — 유형자산 (PPE)
    # ========================================================================
    "유형자산": StandardAccount.PPE,
    "유형자산 합계": StandardAccount.PPE,
    "유형 자산": StandardAccount.PPE,
    "토지": StandardAccount.PPE,
    "건물": StandardAccount.PPE,
    "기계장치": StandardAccount.PPE,
    "구축물": StandardAccount.PPE,
    "건설중인자산": StandardAccount.PPE,
    # ========================================================================
    # [BS] 재무상태표 — 무형자산 (INTANGIBLE_ASSETS)
    # ========================================================================
    "무형자산": StandardAccount.INTANGIBLE_ASSETS,
    "무형자산 합계": StandardAccount.INTANGIBLE_ASSETS,
    "무형 자산": StandardAccount.INTANGIBLE_ASSETS,
    "영업권": StandardAccount.INTANGIBLE_ASSETS,
    "산업재산권": StandardAccount.INTANGIBLE_ASSETS,
    "개발비": StandardAccount.INTANGIBLE_ASSETS,
    "소프트웨어": StandardAccount.INTANGIBLE_ASSETS,
    # ========================================================================
    # [BS] 재무상태표 — 투자부동산 (INVESTMENT_PROPERTY)
    # ========================================================================
    "투자부동산": StandardAccount.INVESTMENT_PROPERTY,
    "투자 부동산": StandardAccount.INVESTMENT_PROPERTY,
    # ========================================================================
    # [BS] 재무상태표 — 장기금융상품 (LONG_TERM_INVESTMENTS)
    # ========================================================================
    "장기금융상품": StandardAccount.LONG_TERM_INVESTMENTS,
    "장기투자자산": StandardAccount.LONG_TERM_INVESTMENTS,
    "장기금융자산": StandardAccount.LONG_TERM_INVESTMENTS,
    "장기 금융상품": StandardAccount.LONG_TERM_INVESTMENTS,
    "비유동금융자산": StandardAccount.LONG_TERM_INVESTMENTS,
    "관계기업투자": StandardAccount.LONG_TERM_INVESTMENTS,
    "관계기업투자주식": StandardAccount.LONG_TERM_INVESTMENTS,
    "관계기업 및 공동기업 투자": StandardAccount.LONG_TERM_INVESTMENTS,
    "지분법적용투자주식": StandardAccount.LONG_TERM_INVESTMENTS,
    # ========================================================================
    # [BS] 재무상태표 — 부채총계 (TOTAL_LIABILITIES)
    # ========================================================================
    "부채총계": StandardAccount.TOTAL_LIABILITIES,
    "총부채": StandardAccount.TOTAL_LIABILITIES,
    "부채 총계": StandardAccount.TOTAL_LIABILITIES,
    "부채합계": StandardAccount.TOTAL_LIABILITIES,
    "부채 합계": StandardAccount.TOTAL_LIABILITIES,
    # ========================================================================
    # [BS] 재무상태표 — 유동부채 (CURRENT_LIABILITIES)
    # ========================================================================
    "유동부채": StandardAccount.CURRENT_LIABILITIES,
    "유동부채 합계": StandardAccount.CURRENT_LIABILITIES,
    "유동 부채": StandardAccount.CURRENT_LIABILITIES,
    # ========================================================================
    # [BS] 재무상태표 — 비유동부채 (NON_CURRENT_LIABILITIES)
    # ========================================================================
    "비유동부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "비유동부채 합계": StandardAccount.NON_CURRENT_LIABILITIES,
    "비유동 부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "고정부채": StandardAccount.NON_CURRENT_LIABILITIES,
    # ========================================================================
    # [BS] 재무상태표 — 매입채무 (TRADE_PAYABLES)
    # ========================================================================
    "매입채무": StandardAccount.ACCOUNTS_PAYABLE,
    "매입채무및기타채무": StandardAccount.ACCOUNTS_PAYABLE,
    "매입채무 및 기타채무": StandardAccount.ACCOUNTS_PAYABLE,
    "매입채무및기타지급채무": StandardAccount.ACCOUNTS_PAYABLE,
    "매입채무 및 기타지급채무": StandardAccount.ACCOUNTS_PAYABLE,
    "외상매입금": StandardAccount.ACCOUNTS_PAYABLE,
    "지급어음": StandardAccount.ACCOUNTS_PAYABLE,
    "지급어음및매입채무": StandardAccount.ACCOUNTS_PAYABLE,
    "지급어음 및 매입채무": StandardAccount.ACCOUNTS_PAYABLE,
    # ========================================================================
    # [BS] 재무상태표 — 단기차입금 (SHORT_TERM_BORROWINGS)
    # ========================================================================
    "단기차입금": StandardAccount.SHORT_TERM_BORROWINGS,
    "단기금융부채": StandardAccount.SHORT_TERM_BORROWINGS,
    "단기 차입금": StandardAccount.SHORT_TERM_BORROWINGS,
    "유동성장기부채": StandardAccount.SHORT_TERM_BORROWINGS,
    "유동성장기차입금": StandardAccount.SHORT_TERM_BORROWINGS,
    "유동성 장기부채": StandardAccount.SHORT_TERM_BORROWINGS,
    "단기사채": StandardAccount.SHORT_TERM_BORROWINGS,
    # ========================================================================
    # [BS] 재무상태표 — 장기차입금 (LONG_TERM_BORROWINGS)
    # ========================================================================
    "장기차입금": StandardAccount.LONG_TERM_BORROWINGS,
    "장기금융부채": StandardAccount.LONG_TERM_BORROWINGS,
    "사채": StandardAccount.LONG_TERM_BORROWINGS,
    "장기 차입금": StandardAccount.LONG_TERM_BORROWINGS,
    "비유동금융부채": StandardAccount.LONG_TERM_BORROWINGS,
    "회사채": StandardAccount.LONG_TERM_BORROWINGS,
    "전환사채": StandardAccount.LONG_TERM_BORROWINGS,
    "신주인수권부사채": StandardAccount.LONG_TERM_BORROWINGS,
    # ========================================================================
    # [BS] 재무상태표 — 총차입금 (TOTAL_DEBT)
    # ========================================================================
    "총차입금": StandardAccount.TOTAL_DEBT,
    "총금융부채": StandardAccount.TOTAL_DEBT,
    "차입금 합계": StandardAccount.TOTAL_DEBT,
    "금융부채 합계": StandardAccount.TOTAL_DEBT,
    "총 차입금": StandardAccount.TOTAL_DEBT,
    # ========================================================================
    # [BS] 재무상태표 — 자본총계 (TOTAL_EQUITY)
    # ========================================================================
    "자본총계": StandardAccount.TOTAL_EQUITY,
    "총자본": StandardAccount.TOTAL_EQUITY,
    "자본 총계": StandardAccount.TOTAL_EQUITY,
    "자본합계": StandardAccount.TOTAL_EQUITY,
    "자본 합계": StandardAccount.TOTAL_EQUITY,
    "지배기업소유주지분": StandardAccount.TOTAL_EQUITY,
    "지배기업 소유주지분": StandardAccount.TOTAL_EQUITY,
    # ========================================================================
    # [BS] 재무상태표 — 자본금 (CAPITAL_STOCK)
    # ========================================================================
    "자본금": StandardAccount.CAPITAL_STOCK,
    "납입자본": StandardAccount.CAPITAL_STOCK,
    "납입 자본": StandardAccount.CAPITAL_STOCK,
    "보통주자본금": StandardAccount.CAPITAL_STOCK,
    "보통주 자본금": StandardAccount.CAPITAL_STOCK,
    "우선주자본금": StandardAccount.CAPITAL_STOCK,
    # ========================================================================
    # [BS] 재무상태표 — 자본잉여금 (CAPITAL_SURPLUS)
    # ========================================================================
    "자본잉여금": StandardAccount.CAPITAL_SURPLUS,
    "주식발행초과금": StandardAccount.CAPITAL_SURPLUS,
    "자본 잉여금": StandardAccount.CAPITAL_SURPLUS,
    "주식발행 초과금": StandardAccount.CAPITAL_SURPLUS,
    "기타자본잉여금": StandardAccount.CAPITAL_SURPLUS,
    # ========================================================================
    # [BS] 재무상태표 — 이익잉여금 (RETAINED_EARNINGS)
    # ========================================================================
    "이익잉여금": StandardAccount.RETAINED_EARNINGS,
    "미처분이익잉여금": StandardAccount.RETAINED_EARNINGS,
    "이익 잉여금": StandardAccount.RETAINED_EARNINGS,
    "미처분 이익잉여금": StandardAccount.RETAINED_EARNINGS,
    "이익잉여금(결손금)": StandardAccount.RETAINED_EARNINGS,
    "결손금": StandardAccount.RETAINED_EARNINGS,
    "처분전이익잉여금": StandardAccount.RETAINED_EARNINGS,
    # ========================================================================
    # [BS] 재무상태표 — 자기주식 (TREASURY_STOCK)
    # ========================================================================
    "자기주식": StandardAccount.TREASURY_STOCK,
    "자기 주식": StandardAccount.TREASURY_STOCK,
    "자사주": StandardAccount.TREASURY_STOCK,
    # ========================================================================
    # [CF] 현금흐름표 — 영업활동현금흐름 (OPERATING_CASH_FLOW)
    # ========================================================================
    "영업활동현금흐름": StandardAccount.OPERATING_CASH_FLOW,
    "영업활동으로인한현금흐름": StandardAccount.OPERATING_CASH_FLOW,
    "영업활동 현금흐름": StandardAccount.OPERATING_CASH_FLOW,
    "영업활동으로 인한 현금흐름": StandardAccount.OPERATING_CASH_FLOW,
    "영업활동으로인한현금흐름의변동": StandardAccount.OPERATING_CASH_FLOW,
    "영업에서 창출된 현금흐름": StandardAccount.OPERATING_CASH_FLOW,
    "영업에서창출된현금흐름": StandardAccount.OPERATING_CASH_FLOW,
    "영업활동 현금 흐름": StandardAccount.OPERATING_CASH_FLOW,
    "영업활동으로 인한 현금의 증감": StandardAccount.OPERATING_CASH_FLOW,
    # ========================================================================
    # [CF] 현금흐름표 — 투자활동현금흐름 (INVESTING_CASH_FLOW)
    # ========================================================================
    "투자활동현금흐름": StandardAccount.INVESTING_CASH_FLOW,
    "투자활동으로인한현금흐름": StandardAccount.INVESTING_CASH_FLOW,
    "투자활동 현금흐름": StandardAccount.INVESTING_CASH_FLOW,
    "투자활동으로 인한 현금흐름": StandardAccount.INVESTING_CASH_FLOW,
    "투자활동으로인한현금흐름의변동": StandardAccount.INVESTING_CASH_FLOW,
    "투자활동 현금 흐름": StandardAccount.INVESTING_CASH_FLOW,
    "투자활동으로 인한 현금의 증감": StandardAccount.INVESTING_CASH_FLOW,
    # ========================================================================
    # [CF] 현금흐름표 — 재무활동현금흐름 (FINANCING_CASH_FLOW)
    # ========================================================================
    "재무활동현금흐름": StandardAccount.FINANCING_CASH_FLOW,
    "재무활동으로인한현금흐름": StandardAccount.FINANCING_CASH_FLOW,
    "재무활동 현금흐름": StandardAccount.FINANCING_CASH_FLOW,
    "재무활동으로 인한 현금흐름": StandardAccount.FINANCING_CASH_FLOW,
    "재무활동으로인한현금흐름의변동": StandardAccount.FINANCING_CASH_FLOW,
    "재무활동 현금 흐름": StandardAccount.FINANCING_CASH_FLOW,
    "재무활동으로 인한 현금의 증감": StandardAccount.FINANCING_CASH_FLOW,
    # ========================================================================
    # [CF] 현금흐름표 — 자본적지출 (CAPEX)
    # ========================================================================
    "자본적지출": StandardAccount.CAPEX,
    "유형자산의취득": StandardAccount.CAPEX,
    "유형자산 취득": StandardAccount.CAPEX,
    "설비투자": StandardAccount.CAPEX,
    "유형자산의 취득": StandardAccount.CAPEX,
    "유형자산취득": StandardAccount.CAPEX,
    "자본적 지출": StandardAccount.CAPEX,
    "투자지출": StandardAccount.CAPEX,
    "유형자산의증가": StandardAccount.CAPEX,
    "유형자산 증가": StandardAccount.CAPEX,
    # ========================================================================
    # [CF] 현금흐름표 — 배당금지급 (DIVIDENDS_PAID)
    # ========================================================================
    "배당금지급": StandardAccount.DIVIDENDS_PAID,
    "배당금의지급": StandardAccount.DIVIDENDS_PAID,
    "현금배당금": StandardAccount.DIVIDENDS_PAID,
    "배당금 지급": StandardAccount.DIVIDENDS_PAID,
    "배당금의 지급": StandardAccount.DIVIDENDS_PAID,
    "현금 배당금": StandardAccount.DIVIDENDS_PAID,
    "배당금": StandardAccount.DIVIDENDS_PAID,
    "배당금지급액": StandardAccount.DIVIDENDS_PAID,
    # ========================================================================
    # [IS] 추가 동의어 — DART 실제 데이터 커버리지 확대
    # ========================================================================
    "계속영업이익": StandardAccount.OPERATING_INCOME,
    "계속영업손익": StandardAccount.OPERATING_INCOME,
    "계속사업이익": StandardAccount.OPERATING_INCOME,
    "중단영업손익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "중단사업손익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "종업원급여": StandardAccount.SGA_EXPENSES,
    "복리후생비": StandardAccount.SGA_EXPENSES,
    "경상연구개발비": StandardAccount.SGA_EXPENSES,
    "연구개발비": StandardAccount.SGA_EXPENSES,
    "연구비": StandardAccount.SGA_EXPENSES,
    "광고선전비": StandardAccount.SGA_EXPENSES,
    "대손상각비": StandardAccount.SGA_EXPENSES,
    "외환차손": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "외환차익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "외화환산손실": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "외화환산이익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "유형자산처분손실": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "유형자산처분이익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    "지분법손실": StandardAccount.OTHER_NON_OPERATING_EXPENSE,
    "지분법이익": StandardAccount.OTHER_NON_OPERATING_INCOME,
    # ========================================================================
    # [BS] 추가 동의어 — DART 실제 데이터 커버리지 확대
    # ========================================================================
    "기타비유동자산": StandardAccount.NON_CURRENT_ASSETS,
    "기타 비유동자산": StandardAccount.NON_CURRENT_ASSETS,
    "이연법인세자산": StandardAccount.NON_CURRENT_ASSETS,
    "기타비유동부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "기타 비유동부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "이연법인세부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "충당부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "퇴직급여충당부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "퇴직급여부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "순확정급여부채": StandardAccount.NON_CURRENT_LIABILITIES,
    "확정급여채무": StandardAccount.NON_CURRENT_LIABILITIES,
    "기타유동부채": StandardAccount.CURRENT_LIABILITIES,
    "기타 유동부채": StandardAccount.CURRENT_LIABILITIES,
    "미지급금": StandardAccount.CURRENT_LIABILITIES,
    "미지급비용": StandardAccount.CURRENT_LIABILITIES,
    "선수금": StandardAccount.CURRENT_LIABILITIES,
    "예수금": StandardAccount.CURRENT_LIABILITIES,
    "미지급법인세": StandardAccount.CURRENT_LIABILITIES,
    "기타포괄손익누계액": StandardAccount.TOTAL_EQUITY,
    "기타자본구성요소": StandardAccount.TOTAL_EQUITY,
    "기타자본항목": StandardAccount.TOTAL_EQUITY,
    "비지배지분": StandardAccount.TOTAL_EQUITY,
    "비지배 지분": StandardAccount.TOTAL_EQUITY,
    "소수주주지분": StandardAccount.TOTAL_EQUITY,
    # ========================================================================
    # [CF] 추가 동의어 — DART 실제 데이터 커버리지 확대
    # ========================================================================
    "무형자산의취득": StandardAccount.CAPEX,
    "무형자산 취득": StandardAccount.CAPEX,
    "무형자산취득": StandardAccount.CAPEX,
    "차입금의상환": StandardAccount.FINANCING_CASH_FLOW,
    "차입금의 상환": StandardAccount.FINANCING_CASH_FLOW,
    "차입금상환": StandardAccount.FINANCING_CASH_FLOW,
    "자기주식의취득": StandardAccount.FINANCING_CASH_FLOW,
    "자기주식 취득": StandardAccount.FINANCING_CASH_FLOW,
}


# ============================================================================
# 역방향 인덱스: StandardAccount → list[str]
# ============================================================================

_REVERSE_INDEX: dict[StandardAccount, list[str]] | None = None


def _build_reverse_index() -> dict[StandardAccount, list[str]]:
    """역방향 인덱스를 구축한다 (최초 호출 시 1회 실행)."""
    index: dict[StandardAccount, list[str]] = {}
    for korean_name, standard_account in KOREAN_ACCOUNT_MAP.items():
        index.setdefault(standard_account, []).append(korean_name)
    return index


def get_korean_names(account: StandardAccount) -> list[str]:
    """표준 계정의 모든 한글 동의어를 반환한다.

    Args:
        account: 한글 동의어를 조회할 표준 계정.

    Returns:
        해당 표준 계정에 매핑된 모든 한글 계정명 리스트.
        매핑이 없으면 빈 리스트를 반환한다.

    Examples:
        >>> from src.financial_engine.mapper.chart_of_accounts import StandardAccount
        >>> names = get_korean_names(StandardAccount.REVENUE)
        >>> "매출액" in names
        True
        >>> "영업수익" in names
        True
    """
    global _REVERSE_INDEX  # noqa: PLW0603
    if _REVERSE_INDEX is None:
        _REVERSE_INDEX = _build_reverse_index()
    return list(_REVERSE_INDEX.get(account, []))
