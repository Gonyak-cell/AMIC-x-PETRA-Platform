"""표준 계정과목표(Standard Chart of Accounts) — T-F01.

> 마지막 수정: 2026-02-09 16:01:02

IFRS/K-IFRS 기반 표준 계정과목 코드, 재무제표 유형, 부호 관례를 정의한다.
손익계산서(IS), 재무상태표(BS), 현금흐름표(CF) 3종 재무제표의 50+ 계정을 포함하며,
design_renderer.im_document.FinancialStatements 데이터클래스의 모든 필드를 커버한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


@unique
class StatementType(str, Enum):
    """재무제표 유형."""

    INCOME_STATEMENT = "IS"
    BALANCE_SHEET = "BS"
    CASH_FLOW = "CF"


@unique
class AccountSign(str, Enum):
    """계정과목 부호 관례.

    - DEBIT(차변): 자산 증가, 비용 증가 시 차변 기입.
    - CREDIT(대변): 부채/자본 증가, 수익 증가 시 대변 기입.
    """

    DEBIT = "debit"
    CREDIT = "credit"


@unique
class StandardAccount(str, Enum):
    """표준 계정과목 코드 (50+ 항목).

    IFRS/K-IFRS 기준으로 손익계산서(IS), 재무상태표(BS), 현금흐름표(CF)를
    포괄하는 표준 계정과목 체계.

    네이밍 규칙:
      - UPPER_SNAKE_CASE
      - 소계/합계 항목은 TOTAL_ / GROSS_ / NET_ 접두어
      - 파생 지표(derived)는 별도 주석 표기
    """

    # ======================================================================
    # 손익계산서 (Income Statement)
    # ======================================================================

    # --- 매출 ---
    REVENUE = "IS_REVENUE"
    COST_OF_GOODS_SOLD = "IS_COGS"
    GROSS_PROFIT = "IS_GROSS_PROFIT"  # 소계: REVENUE - COGS

    # --- 판매비와관리비 ---
    SGA_EXPENSES = "IS_SGA_EXPENSES"
    SALARY_EXPENSES = "IS_SALARY"
    RENT_EXPENSES = "IS_RENT"
    ADVERTISING_EXPENSES = "IS_ADVERTISING"
    RESEARCH_DEVELOPMENT = "IS_R_AND_D"
    OTHER_SGA_EXPENSES = "IS_OTHER_SGA"

    # --- 영업이익 ---
    OPERATING_INCOME = "IS_OPERATING_INCOME"  # 소계: GROSS_PROFIT - SGA

    # --- 감가상각/상각 ---
    DEPRECIATION = "IS_DEPRECIATION"
    AMORTIZATION = "IS_AMORTIZATION"
    DEPRECIATION_AND_AMORTIZATION = "IS_DA"  # 소계: DEP + AMORT

    # --- 영업외손익 ---
    INTEREST_INCOME = "IS_INTEREST_INCOME"
    INTEREST_EXPENSE = "IS_INTEREST_EXPENSE"
    NET_INTEREST_EXPENSE = "IS_NET_INTEREST"  # 소계
    OTHER_NON_OPERATING_INCOME = "IS_OTHER_NON_OP_INCOME"
    OTHER_NON_OPERATING_EXPENSE = "IS_OTHER_NON_OP_EXPENSE"
    FOREIGN_EXCHANGE_GAIN_LOSS = "IS_FX_GAIN_LOSS"

    # --- 법인세차감전순이익 ---
    INCOME_BEFORE_TAX = "IS_EBT"

    # --- 법인세 ---
    INCOME_TAX_EXPENSE = "IS_TAX_EXPENSE"

    # --- 당기순이익 ---
    NET_INCOME = "IS_NET_INCOME"
    NET_INCOME_CONTROLLING = "IS_NET_INCOME_CTRL"  # 지배기업 소유주 귀속
    NET_INCOME_NON_CONTROLLING = "IS_NET_INCOME_NCI"  # 비지배지분 귀속

    # --- 파생 지표 (Derived) ---
    EBITDA = "IS_EBITDA"  # 파생: OPERATING_INCOME + D&A
    EBIT = "IS_EBIT"  # = OPERATING_INCOME (IFRS 기준 동의어)

    # ======================================================================
    # 재무상태표 (Balance Sheet)
    # ======================================================================

    # --- 자산 ---
    TOTAL_ASSETS = "BS_TOTAL_ASSETS"

    # 유동자산
    CURRENT_ASSETS = "BS_CURRENT_ASSETS"  # 소계
    CASH_AND_EQUIVALENTS = "BS_CASH"
    SHORT_TERM_INVESTMENTS = "BS_ST_INVESTMENTS"
    ACCOUNTS_RECEIVABLE = "BS_AR"
    INVENTORIES = "BS_INVENTORIES"
    OTHER_CURRENT_ASSETS = "BS_OTHER_CA"
    PREPAID_EXPENSES = "BS_PREPAID"

    # 비유동자산
    NON_CURRENT_ASSETS = "BS_NON_CURRENT_ASSETS"  # 소계
    PPE = "BS_PPE"  # 유형자산 (Property, Plant & Equipment)
    INTANGIBLE_ASSETS = "BS_INTANGIBLE"
    GOODWILL = "BS_GOODWILL"
    LONG_TERM_INVESTMENTS = "BS_LT_INVESTMENTS"
    RIGHT_OF_USE_ASSETS = "BS_ROU_ASSETS"  # 사용권자산 (IFRS 16)
    INVESTMENT_PROPERTY = "BS_INVEST_PROPERTY"
    OTHER_NON_CURRENT_ASSETS = "BS_OTHER_NCA"

    # --- 부채 ---
    TOTAL_LIABILITIES = "BS_TOTAL_LIABILITIES"

    # 유동부채
    CURRENT_LIABILITIES = "BS_CURRENT_LIABILITIES"  # 소계
    ACCOUNTS_PAYABLE = "BS_AP"
    SHORT_TERM_BORROWINGS = "BS_ST_BORROWINGS"
    CURRENT_PORTION_LTD = "BS_CPLTD"  # 유동성장기부채
    OTHER_CURRENT_LIABILITIES = "BS_OTHER_CL"
    ACCRUED_EXPENSES = "BS_ACCRUED"

    # 비유동부채
    NON_CURRENT_LIABILITIES = "BS_NON_CURRENT_LIABILITIES"  # 소계
    LONG_TERM_BORROWINGS = "BS_LT_BORROWINGS"
    BONDS_PAYABLE = "BS_BONDS"
    LEASE_LIABILITIES = "BS_LEASE_LIAB"  # 리스부채 (IFRS 16)
    PROVISIONS = "BS_PROVISIONS"  # 충당부채
    DEFERRED_TAX_LIABILITIES = "BS_DTL"
    OTHER_NON_CURRENT_LIABILITIES = "BS_OTHER_NCL"

    # 총차입금 (파생)
    TOTAL_DEBT = "BS_TOTAL_DEBT"  # 파생: ST_BORROWINGS + LT_BORROWINGS + BONDS + CPLTD
    NET_DEBT = "BS_NET_DEBT"  # 파생: TOTAL_DEBT - CASH

    # --- 자본 ---
    TOTAL_EQUITY = "BS_TOTAL_EQUITY"
    CAPITAL_STOCK = "BS_CAPITAL_STOCK"  # 자본금
    CAPITAL_SURPLUS = "BS_CAPITAL_SURPLUS"  # 자본잉여금
    RETAINED_EARNINGS = "BS_RETAINED_EARNINGS"
    TREASURY_STOCK = "BS_TREASURY_STOCK"  # 자기주식
    ACCUMULATED_OCI = "BS_AOCI"  # 기타포괄손익누계액
    NON_CONTROLLING_INTEREST = "BS_NCI"  # 비지배지분

    # ======================================================================
    # 현금흐름표 (Cash Flow Statement)
    # ======================================================================

    OPERATING_CASH_FLOW = "CF_OPERATING"
    INVESTING_CASH_FLOW = "CF_INVESTING"
    FINANCING_CASH_FLOW = "CF_FINANCING"

    # 영업활동 세부
    CF_DEPRECIATION_AMORTIZATION = "CF_DA"  # 감가상각비/상각비 (비현금 가산)
    CF_CHANGE_IN_WORKING_CAPITAL = "CF_WC_CHANGE"  # 운전자본 변동
    CF_CHANGE_IN_RECEIVABLES = "CF_AR_CHANGE"
    CF_CHANGE_IN_INVENTORIES = "CF_INV_CHANGE"
    CF_CHANGE_IN_PAYABLES = "CF_AP_CHANGE"

    # 투자활동 세부
    CAPEX = "CF_CAPEX"  # 자본적 지출
    ACQUISITION_OF_SUBSIDIARIES = "CF_ACQUISITION"
    DISPOSAL_OF_PPE = "CF_DISPOSAL_PPE"
    PURCHASE_OF_INVESTMENTS = "CF_PURCHASE_INVEST"
    SALE_OF_INVESTMENTS = "CF_SALE_INVEST"

    # 재무활동 세부
    PROCEEDS_FROM_BORROWINGS = "CF_BORROW_PROCEEDS"
    REPAYMENT_OF_BORROWINGS = "CF_BORROW_REPAY"
    ISSUANCE_OF_EQUITY = "CF_EQUITY_ISSUE"
    DIVIDENDS_PAID = "CF_DIVIDENDS_PAID"
    SHARE_BUYBACK = "CF_SHARE_BUYBACK"

    # 기타
    NET_CHANGE_IN_CASH = "CF_NET_CHANGE"  # 소계: OCF + ICF + FCF
    FREE_CASH_FLOW = "CF_FCF"  # 파생: OCF - CAPEX


# ---------------------------------------------------------------------------
# AccountMetadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountMetadata:
    """표준 계정과목 메타데이터.

    Attributes:
        code: 표준 계정과목 코드.
        name_kr: 한글 계정명.
        name_en: 영문 계정명.
        statement_type: 소속 재무제표 유형 (IS / BS / CF).
        sign: 부호 관례 (debit / credit).
        is_subtotal: 소계/합계 항목 여부. True이면 하위 항목의 합산으로 도출.
        is_derived: 파생 지표 여부. True이면 다른 계정에서 계산으로 도출.
        parent: 상위 소계 계정. None이면 최상위 항목.
    """

    code: StandardAccount
    name_kr: str
    name_en: str
    statement_type: StatementType
    sign: AccountSign
    is_subtotal: bool = False
    is_derived: bool = False
    parent: StandardAccount | None = None


# ---------------------------------------------------------------------------
# ACCOUNT_METADATA: 전체 계정 메타데이터 사전
# ---------------------------------------------------------------------------

_IS = StatementType.INCOME_STATEMENT
_BS = StatementType.BALANCE_SHEET
_CF = StatementType.CASH_FLOW
_DR = AccountSign.DEBIT
_CR = AccountSign.CREDIT
_A = StandardAccount  # alias

ACCOUNT_METADATA: dict[StandardAccount, AccountMetadata] = {
    # ==================================================================
    # 손익계산서 (Income Statement)
    # ==================================================================
    _A.REVENUE: AccountMetadata(
        code=_A.REVENUE,
        name_kr="매출액",
        name_en="Revenue",
        statement_type=_IS,
        sign=_CR,
    ),
    _A.COST_OF_GOODS_SOLD: AccountMetadata(
        code=_A.COST_OF_GOODS_SOLD,
        name_kr="매출원가",
        name_en="Cost of Goods Sold",
        statement_type=_IS,
        sign=_DR,
        parent=_A.GROSS_PROFIT,
    ),
    _A.GROSS_PROFIT: AccountMetadata(
        code=_A.GROSS_PROFIT,
        name_kr="매출총이익",
        name_en="Gross Profit",
        statement_type=_IS,
        sign=_CR,
        is_subtotal=True,
    ),
    _A.SGA_EXPENSES: AccountMetadata(
        code=_A.SGA_EXPENSES,
        name_kr="판매비와관리비",
        name_en="SG&A Expenses",
        statement_type=_IS,
        sign=_DR,
        parent=_A.OPERATING_INCOME,
    ),
    _A.SALARY_EXPENSES: AccountMetadata(
        code=_A.SALARY_EXPENSES,
        name_kr="급여",
        name_en="Salary Expenses",
        statement_type=_IS,
        sign=_DR,
        parent=_A.SGA_EXPENSES,
    ),
    _A.RENT_EXPENSES: AccountMetadata(
        code=_A.RENT_EXPENSES,
        name_kr="임차료",
        name_en="Rent Expenses",
        statement_type=_IS,
        sign=_DR,
        parent=_A.SGA_EXPENSES,
    ),
    _A.ADVERTISING_EXPENSES: AccountMetadata(
        code=_A.ADVERTISING_EXPENSES,
        name_kr="광고선전비",
        name_en="Advertising Expenses",
        statement_type=_IS,
        sign=_DR,
        parent=_A.SGA_EXPENSES,
    ),
    _A.RESEARCH_DEVELOPMENT: AccountMetadata(
        code=_A.RESEARCH_DEVELOPMENT,
        name_kr="연구개발비",
        name_en="Research & Development",
        statement_type=_IS,
        sign=_DR,
        parent=_A.SGA_EXPENSES,
    ),
    _A.OTHER_SGA_EXPENSES: AccountMetadata(
        code=_A.OTHER_SGA_EXPENSES,
        name_kr="기타판관비",
        name_en="Other SG&A Expenses",
        statement_type=_IS,
        sign=_DR,
        parent=_A.SGA_EXPENSES,
    ),
    _A.OPERATING_INCOME: AccountMetadata(
        code=_A.OPERATING_INCOME,
        name_kr="영업이익",
        name_en="Operating Income",
        statement_type=_IS,
        sign=_CR,
        is_subtotal=True,
    ),
    _A.DEPRECIATION: AccountMetadata(
        code=_A.DEPRECIATION,
        name_kr="감가상각비",
        name_en="Depreciation",
        statement_type=_IS,
        sign=_DR,
        parent=_A.DEPRECIATION_AND_AMORTIZATION,
    ),
    _A.AMORTIZATION: AccountMetadata(
        code=_A.AMORTIZATION,
        name_kr="무형자산상각비",
        name_en="Amortization",
        statement_type=_IS,
        sign=_DR,
        parent=_A.DEPRECIATION_AND_AMORTIZATION,
    ),
    _A.DEPRECIATION_AND_AMORTIZATION: AccountMetadata(
        code=_A.DEPRECIATION_AND_AMORTIZATION,
        name_kr="감가상각비 및 상각비",
        name_en="Depreciation & Amortization",
        statement_type=_IS,
        sign=_DR,
        is_subtotal=True,
    ),
    _A.INTEREST_INCOME: AccountMetadata(
        code=_A.INTEREST_INCOME,
        name_kr="이자수익",
        name_en="Interest Income",
        statement_type=_IS,
        sign=_CR,
    ),
    _A.INTEREST_EXPENSE: AccountMetadata(
        code=_A.INTEREST_EXPENSE,
        name_kr="이자비용",
        name_en="Interest Expense",
        statement_type=_IS,
        sign=_DR,
    ),
    _A.NET_INTEREST_EXPENSE: AccountMetadata(
        code=_A.NET_INTEREST_EXPENSE,
        name_kr="순이자비용",
        name_en="Net Interest Expense",
        statement_type=_IS,
        sign=_DR,
        is_subtotal=True,
    ),
    _A.OTHER_NON_OPERATING_INCOME: AccountMetadata(
        code=_A.OTHER_NON_OPERATING_INCOME,
        name_kr="기타영업외수익",
        name_en="Other Non-Operating Income",
        statement_type=_IS,
        sign=_CR,
    ),
    _A.OTHER_NON_OPERATING_EXPENSE: AccountMetadata(
        code=_A.OTHER_NON_OPERATING_EXPENSE,
        name_kr="기타영업외비용",
        name_en="Other Non-Operating Expense",
        statement_type=_IS,
        sign=_DR,
    ),
    _A.FOREIGN_EXCHANGE_GAIN_LOSS: AccountMetadata(
        code=_A.FOREIGN_EXCHANGE_GAIN_LOSS,
        name_kr="외환차손익",
        name_en="Foreign Exchange Gain/Loss",
        statement_type=_IS,
        sign=_DR,
    ),
    _A.INCOME_BEFORE_TAX: AccountMetadata(
        code=_A.INCOME_BEFORE_TAX,
        name_kr="법인세차감전순이익",
        name_en="Income Before Tax",
        statement_type=_IS,
        sign=_CR,
        is_subtotal=True,
    ),
    _A.INCOME_TAX_EXPENSE: AccountMetadata(
        code=_A.INCOME_TAX_EXPENSE,
        name_kr="법인세비용",
        name_en="Income Tax Expense",
        statement_type=_IS,
        sign=_DR,
    ),
    _A.NET_INCOME: AccountMetadata(
        code=_A.NET_INCOME,
        name_kr="당기순이익",
        name_en="Net Income",
        statement_type=_IS,
        sign=_CR,
        is_subtotal=True,
    ),
    _A.NET_INCOME_CONTROLLING: AccountMetadata(
        code=_A.NET_INCOME_CONTROLLING,
        name_kr="지배기업 소유주 귀속 순이익",
        name_en="Net Income (Controlling)",
        statement_type=_IS,
        sign=_CR,
        parent=_A.NET_INCOME,
    ),
    _A.NET_INCOME_NON_CONTROLLING: AccountMetadata(
        code=_A.NET_INCOME_NON_CONTROLLING,
        name_kr="비지배지분 귀속 순이익",
        name_en="Net Income (Non-Controlling)",
        statement_type=_IS,
        sign=_CR,
        parent=_A.NET_INCOME,
    ),
    _A.EBITDA: AccountMetadata(
        code=_A.EBITDA,
        name_kr="EBITDA",
        name_en="EBITDA",
        statement_type=_IS,
        sign=_CR,
        is_subtotal=True,
        is_derived=True,
    ),
    _A.EBIT: AccountMetadata(
        code=_A.EBIT,
        name_kr="EBIT",
        name_en="EBIT",
        statement_type=_IS,
        sign=_CR,
        is_subtotal=True,
        is_derived=True,
    ),
    # ==================================================================
    # 재무상태표 (Balance Sheet) — 자산
    # ==================================================================
    _A.TOTAL_ASSETS: AccountMetadata(
        code=_A.TOTAL_ASSETS,
        name_kr="자산총계",
        name_en="Total Assets",
        statement_type=_BS,
        sign=_DR,
        is_subtotal=True,
    ),
    _A.CURRENT_ASSETS: AccountMetadata(
        code=_A.CURRENT_ASSETS,
        name_kr="유동자산",
        name_en="Current Assets",
        statement_type=_BS,
        sign=_DR,
        is_subtotal=True,
        parent=_A.TOTAL_ASSETS,
    ),
    _A.CASH_AND_EQUIVALENTS: AccountMetadata(
        code=_A.CASH_AND_EQUIVALENTS,
        name_kr="현금및현금성자산",
        name_en="Cash and Cash Equivalents",
        statement_type=_BS,
        sign=_DR,
        parent=_A.CURRENT_ASSETS,
    ),
    _A.SHORT_TERM_INVESTMENTS: AccountMetadata(
        code=_A.SHORT_TERM_INVESTMENTS,
        name_kr="단기금융상품",
        name_en="Short-Term Investments",
        statement_type=_BS,
        sign=_DR,
        parent=_A.CURRENT_ASSETS,
    ),
    _A.ACCOUNTS_RECEIVABLE: AccountMetadata(
        code=_A.ACCOUNTS_RECEIVABLE,
        name_kr="매출채권",
        name_en="Accounts Receivable",
        statement_type=_BS,
        sign=_DR,
        parent=_A.CURRENT_ASSETS,
    ),
    _A.INVENTORIES: AccountMetadata(
        code=_A.INVENTORIES,
        name_kr="재고자산",
        name_en="Inventories",
        statement_type=_BS,
        sign=_DR,
        parent=_A.CURRENT_ASSETS,
    ),
    _A.OTHER_CURRENT_ASSETS: AccountMetadata(
        code=_A.OTHER_CURRENT_ASSETS,
        name_kr="기타유동자산",
        name_en="Other Current Assets",
        statement_type=_BS,
        sign=_DR,
        parent=_A.CURRENT_ASSETS,
    ),
    _A.PREPAID_EXPENSES: AccountMetadata(
        code=_A.PREPAID_EXPENSES,
        name_kr="선급비용",
        name_en="Prepaid Expenses",
        statement_type=_BS,
        sign=_DR,
        parent=_A.CURRENT_ASSETS,
    ),
    _A.NON_CURRENT_ASSETS: AccountMetadata(
        code=_A.NON_CURRENT_ASSETS,
        name_kr="비유동자산",
        name_en="Non-Current Assets",
        statement_type=_BS,
        sign=_DR,
        is_subtotal=True,
        parent=_A.TOTAL_ASSETS,
    ),
    _A.PPE: AccountMetadata(
        code=_A.PPE,
        name_kr="유형자산",
        name_en="Property, Plant & Equipment",
        statement_type=_BS,
        sign=_DR,
        parent=_A.NON_CURRENT_ASSETS,
    ),
    _A.INTANGIBLE_ASSETS: AccountMetadata(
        code=_A.INTANGIBLE_ASSETS,
        name_kr="무형자산",
        name_en="Intangible Assets",
        statement_type=_BS,
        sign=_DR,
        parent=_A.NON_CURRENT_ASSETS,
    ),
    _A.GOODWILL: AccountMetadata(
        code=_A.GOODWILL,
        name_kr="영업권",
        name_en="Goodwill",
        statement_type=_BS,
        sign=_DR,
        parent=_A.NON_CURRENT_ASSETS,
    ),
    _A.LONG_TERM_INVESTMENTS: AccountMetadata(
        code=_A.LONG_TERM_INVESTMENTS,
        name_kr="장기금융상품",
        name_en="Long-Term Investments",
        statement_type=_BS,
        sign=_DR,
        parent=_A.NON_CURRENT_ASSETS,
    ),
    _A.RIGHT_OF_USE_ASSETS: AccountMetadata(
        code=_A.RIGHT_OF_USE_ASSETS,
        name_kr="사용권자산",
        name_en="Right-of-Use Assets",
        statement_type=_BS,
        sign=_DR,
        parent=_A.NON_CURRENT_ASSETS,
    ),
    _A.INVESTMENT_PROPERTY: AccountMetadata(
        code=_A.INVESTMENT_PROPERTY,
        name_kr="투자부동산",
        name_en="Investment Property",
        statement_type=_BS,
        sign=_DR,
        parent=_A.NON_CURRENT_ASSETS,
    ),
    _A.OTHER_NON_CURRENT_ASSETS: AccountMetadata(
        code=_A.OTHER_NON_CURRENT_ASSETS,
        name_kr="기타비유동자산",
        name_en="Other Non-Current Assets",
        statement_type=_BS,
        sign=_DR,
        parent=_A.NON_CURRENT_ASSETS,
    ),
    # ==================================================================
    # 재무상태표 (Balance Sheet) — 부채
    # ==================================================================
    _A.TOTAL_LIABILITIES: AccountMetadata(
        code=_A.TOTAL_LIABILITIES,
        name_kr="부채총계",
        name_en="Total Liabilities",
        statement_type=_BS,
        sign=_CR,
        is_subtotal=True,
    ),
    _A.CURRENT_LIABILITIES: AccountMetadata(
        code=_A.CURRENT_LIABILITIES,
        name_kr="유동부채",
        name_en="Current Liabilities",
        statement_type=_BS,
        sign=_CR,
        is_subtotal=True,
        parent=_A.TOTAL_LIABILITIES,
    ),
    _A.ACCOUNTS_PAYABLE: AccountMetadata(
        code=_A.ACCOUNTS_PAYABLE,
        name_kr="매입채무",
        name_en="Accounts Payable",
        statement_type=_BS,
        sign=_CR,
        parent=_A.CURRENT_LIABILITIES,
    ),
    _A.SHORT_TERM_BORROWINGS: AccountMetadata(
        code=_A.SHORT_TERM_BORROWINGS,
        name_kr="단기차입금",
        name_en="Short-Term Borrowings",
        statement_type=_BS,
        sign=_CR,
        parent=_A.CURRENT_LIABILITIES,
    ),
    _A.CURRENT_PORTION_LTD: AccountMetadata(
        code=_A.CURRENT_PORTION_LTD,
        name_kr="유동성장기부채",
        name_en="Current Portion of Long-Term Debt",
        statement_type=_BS,
        sign=_CR,
        parent=_A.CURRENT_LIABILITIES,
    ),
    _A.OTHER_CURRENT_LIABILITIES: AccountMetadata(
        code=_A.OTHER_CURRENT_LIABILITIES,
        name_kr="기타유동부채",
        name_en="Other Current Liabilities",
        statement_type=_BS,
        sign=_CR,
        parent=_A.CURRENT_LIABILITIES,
    ),
    _A.ACCRUED_EXPENSES: AccountMetadata(
        code=_A.ACCRUED_EXPENSES,
        name_kr="미지급비용",
        name_en="Accrued Expenses",
        statement_type=_BS,
        sign=_CR,
        parent=_A.CURRENT_LIABILITIES,
    ),
    _A.NON_CURRENT_LIABILITIES: AccountMetadata(
        code=_A.NON_CURRENT_LIABILITIES,
        name_kr="비유동부채",
        name_en="Non-Current Liabilities",
        statement_type=_BS,
        sign=_CR,
        is_subtotal=True,
        parent=_A.TOTAL_LIABILITIES,
    ),
    _A.LONG_TERM_BORROWINGS: AccountMetadata(
        code=_A.LONG_TERM_BORROWINGS,
        name_kr="장기차입금",
        name_en="Long-Term Borrowings",
        statement_type=_BS,
        sign=_CR,
        parent=_A.NON_CURRENT_LIABILITIES,
    ),
    _A.BONDS_PAYABLE: AccountMetadata(
        code=_A.BONDS_PAYABLE,
        name_kr="사채",
        name_en="Bonds Payable",
        statement_type=_BS,
        sign=_CR,
        parent=_A.NON_CURRENT_LIABILITIES,
    ),
    _A.LEASE_LIABILITIES: AccountMetadata(
        code=_A.LEASE_LIABILITIES,
        name_kr="리스부채",
        name_en="Lease Liabilities",
        statement_type=_BS,
        sign=_CR,
        parent=_A.NON_CURRENT_LIABILITIES,
    ),
    _A.PROVISIONS: AccountMetadata(
        code=_A.PROVISIONS,
        name_kr="충당부채",
        name_en="Provisions",
        statement_type=_BS,
        sign=_CR,
        parent=_A.NON_CURRENT_LIABILITIES,
    ),
    _A.DEFERRED_TAX_LIABILITIES: AccountMetadata(
        code=_A.DEFERRED_TAX_LIABILITIES,
        name_kr="이연법인세부채",
        name_en="Deferred Tax Liabilities",
        statement_type=_BS,
        sign=_CR,
        parent=_A.NON_CURRENT_LIABILITIES,
    ),
    _A.OTHER_NON_CURRENT_LIABILITIES: AccountMetadata(
        code=_A.OTHER_NON_CURRENT_LIABILITIES,
        name_kr="기타비유동부채",
        name_en="Other Non-Current Liabilities",
        statement_type=_BS,
        sign=_CR,
        parent=_A.NON_CURRENT_LIABILITIES,
    ),
    _A.TOTAL_DEBT: AccountMetadata(
        code=_A.TOTAL_DEBT,
        name_kr="총차입금",
        name_en="Total Debt",
        statement_type=_BS,
        sign=_CR,
        is_subtotal=True,
        is_derived=True,
    ),
    _A.NET_DEBT: AccountMetadata(
        code=_A.NET_DEBT,
        name_kr="순차입금",
        name_en="Net Debt",
        statement_type=_BS,
        sign=_CR,
        is_subtotal=True,
        is_derived=True,
    ),
    # ==================================================================
    # 재무상태표 (Balance Sheet) — 자본
    # ==================================================================
    _A.TOTAL_EQUITY: AccountMetadata(
        code=_A.TOTAL_EQUITY,
        name_kr="자본총계",
        name_en="Total Equity",
        statement_type=_BS,
        sign=_CR,
        is_subtotal=True,
    ),
    _A.CAPITAL_STOCK: AccountMetadata(
        code=_A.CAPITAL_STOCK,
        name_kr="자본금",
        name_en="Capital Stock",
        statement_type=_BS,
        sign=_CR,
        parent=_A.TOTAL_EQUITY,
    ),
    _A.CAPITAL_SURPLUS: AccountMetadata(
        code=_A.CAPITAL_SURPLUS,
        name_kr="자본잉여금",
        name_en="Capital Surplus",
        statement_type=_BS,
        sign=_CR,
        parent=_A.TOTAL_EQUITY,
    ),
    _A.RETAINED_EARNINGS: AccountMetadata(
        code=_A.RETAINED_EARNINGS,
        name_kr="이익잉여금",
        name_en="Retained Earnings",
        statement_type=_BS,
        sign=_CR,
        parent=_A.TOTAL_EQUITY,
    ),
    _A.TREASURY_STOCK: AccountMetadata(
        code=_A.TREASURY_STOCK,
        name_kr="자기주식",
        name_en="Treasury Stock",
        statement_type=_BS,
        sign=_DR,  # 자본 차감 항목
        parent=_A.TOTAL_EQUITY,
    ),
    _A.ACCUMULATED_OCI: AccountMetadata(
        code=_A.ACCUMULATED_OCI,
        name_kr="기타포괄손익누계액",
        name_en="Accumulated Other Comprehensive Income",
        statement_type=_BS,
        sign=_CR,
        parent=_A.TOTAL_EQUITY,
    ),
    _A.NON_CONTROLLING_INTEREST: AccountMetadata(
        code=_A.NON_CONTROLLING_INTEREST,
        name_kr="비지배지분",
        name_en="Non-Controlling Interest",
        statement_type=_BS,
        sign=_CR,
        parent=_A.TOTAL_EQUITY,
    ),
    # ==================================================================
    # 현금흐름표 (Cash Flow Statement)
    # ==================================================================
    _A.OPERATING_CASH_FLOW: AccountMetadata(
        code=_A.OPERATING_CASH_FLOW,
        name_kr="영업활동현금흐름",
        name_en="Operating Cash Flow",
        statement_type=_CF,
        sign=_DR,
        is_subtotal=True,
    ),
    _A.CF_DEPRECIATION_AMORTIZATION: AccountMetadata(
        code=_A.CF_DEPRECIATION_AMORTIZATION,
        name_kr="감가상각비 및 상각비 (현금흐름)",
        name_en="Depreciation & Amortization (CF)",
        statement_type=_CF,
        sign=_DR,
        parent=_A.OPERATING_CASH_FLOW,
    ),
    _A.CF_CHANGE_IN_WORKING_CAPITAL: AccountMetadata(
        code=_A.CF_CHANGE_IN_WORKING_CAPITAL,
        name_kr="운전자본 변동",
        name_en="Change in Working Capital",
        statement_type=_CF,
        sign=_DR,
        parent=_A.OPERATING_CASH_FLOW,
    ),
    _A.CF_CHANGE_IN_RECEIVABLES: AccountMetadata(
        code=_A.CF_CHANGE_IN_RECEIVABLES,
        name_kr="매출채권 변동",
        name_en="Change in Receivables",
        statement_type=_CF,
        sign=_DR,
        parent=_A.CF_CHANGE_IN_WORKING_CAPITAL,
    ),
    _A.CF_CHANGE_IN_INVENTORIES: AccountMetadata(
        code=_A.CF_CHANGE_IN_INVENTORIES,
        name_kr="재고자산 변동",
        name_en="Change in Inventories",
        statement_type=_CF,
        sign=_DR,
        parent=_A.CF_CHANGE_IN_WORKING_CAPITAL,
    ),
    _A.CF_CHANGE_IN_PAYABLES: AccountMetadata(
        code=_A.CF_CHANGE_IN_PAYABLES,
        name_kr="매입채무 변동",
        name_en="Change in Payables",
        statement_type=_CF,
        sign=_CR,
        parent=_A.CF_CHANGE_IN_WORKING_CAPITAL,
    ),
    _A.INVESTING_CASH_FLOW: AccountMetadata(
        code=_A.INVESTING_CASH_FLOW,
        name_kr="투자활동현금흐름",
        name_en="Investing Cash Flow",
        statement_type=_CF,
        sign=_DR,
        is_subtotal=True,
    ),
    _A.CAPEX: AccountMetadata(
        code=_A.CAPEX,
        name_kr="자본적지출",
        name_en="Capital Expenditure",
        statement_type=_CF,
        sign=_DR,
        parent=_A.INVESTING_CASH_FLOW,
    ),
    _A.ACQUISITION_OF_SUBSIDIARIES: AccountMetadata(
        code=_A.ACQUISITION_OF_SUBSIDIARIES,
        name_kr="종속기업 취득",
        name_en="Acquisition of Subsidiaries",
        statement_type=_CF,
        sign=_DR,
        parent=_A.INVESTING_CASH_FLOW,
    ),
    _A.DISPOSAL_OF_PPE: AccountMetadata(
        code=_A.DISPOSAL_OF_PPE,
        name_kr="유형자산 처분",
        name_en="Disposal of PPE",
        statement_type=_CF,
        sign=_CR,
        parent=_A.INVESTING_CASH_FLOW,
    ),
    _A.PURCHASE_OF_INVESTMENTS: AccountMetadata(
        code=_A.PURCHASE_OF_INVESTMENTS,
        name_kr="투자자산 취득",
        name_en="Purchase of Investments",
        statement_type=_CF,
        sign=_DR,
        parent=_A.INVESTING_CASH_FLOW,
    ),
    _A.SALE_OF_INVESTMENTS: AccountMetadata(
        code=_A.SALE_OF_INVESTMENTS,
        name_kr="투자자산 매각",
        name_en="Sale of Investments",
        statement_type=_CF,
        sign=_CR,
        parent=_A.INVESTING_CASH_FLOW,
    ),
    _A.FINANCING_CASH_FLOW: AccountMetadata(
        code=_A.FINANCING_CASH_FLOW,
        name_kr="재무활동현금흐름",
        name_en="Financing Cash Flow",
        statement_type=_CF,
        sign=_DR,
        is_subtotal=True,
    ),
    _A.PROCEEDS_FROM_BORROWINGS: AccountMetadata(
        code=_A.PROCEEDS_FROM_BORROWINGS,
        name_kr="차입금 조달",
        name_en="Proceeds from Borrowings",
        statement_type=_CF,
        sign=_CR,
        parent=_A.FINANCING_CASH_FLOW,
    ),
    _A.REPAYMENT_OF_BORROWINGS: AccountMetadata(
        code=_A.REPAYMENT_OF_BORROWINGS,
        name_kr="차입금 상환",
        name_en="Repayment of Borrowings",
        statement_type=_CF,
        sign=_DR,
        parent=_A.FINANCING_CASH_FLOW,
    ),
    _A.ISSUANCE_OF_EQUITY: AccountMetadata(
        code=_A.ISSUANCE_OF_EQUITY,
        name_kr="유상증자",
        name_en="Issuance of Equity",
        statement_type=_CF,
        sign=_CR,
        parent=_A.FINANCING_CASH_FLOW,
    ),
    _A.DIVIDENDS_PAID: AccountMetadata(
        code=_A.DIVIDENDS_PAID,
        name_kr="배당금 지급",
        name_en="Dividends Paid",
        statement_type=_CF,
        sign=_DR,
        parent=_A.FINANCING_CASH_FLOW,
    ),
    _A.SHARE_BUYBACK: AccountMetadata(
        code=_A.SHARE_BUYBACK,
        name_kr="자사주 매입",
        name_en="Share Buyback",
        statement_type=_CF,
        sign=_DR,
        parent=_A.FINANCING_CASH_FLOW,
    ),
    _A.NET_CHANGE_IN_CASH: AccountMetadata(
        code=_A.NET_CHANGE_IN_CASH,
        name_kr="현금및현금성자산 순증감",
        name_en="Net Change in Cash",
        statement_type=_CF,
        sign=_DR,
        is_subtotal=True,
    ),
    _A.FREE_CASH_FLOW: AccountMetadata(
        code=_A.FREE_CASH_FLOW,
        name_kr="잉여현금흐름",
        name_en="Free Cash Flow",
        statement_type=_CF,
        sign=_DR,
        is_subtotal=True,
        is_derived=True,
    ),
}


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------


def get_accounts_by_statement(
    statement_type: StatementType,
) -> list[AccountMetadata]:
    """특정 재무제표 유형에 속하는 계정 메타데이터 목록을 반환한다.

    Args:
        statement_type: 조회할 재무제표 유형 (IS / BS / CF).

    Returns:
        해당 재무제표에 속하는 AccountMetadata 리스트 (enum 선언 순서 유지).
    """
    return [
        meta
        for meta in ACCOUNT_METADATA.values()
        if meta.statement_type == statement_type
    ]


def get_subtotals() -> list[AccountMetadata]:
    """소계/합계 항목만 반환한다."""
    return [meta for meta in ACCOUNT_METADATA.values() if meta.is_subtotal]


def get_derived_accounts() -> list[AccountMetadata]:
    """파생 지표(derived) 계정만 반환한다."""
    return [meta for meta in ACCOUNT_METADATA.values() if meta.is_derived]


def get_children(parent: StandardAccount) -> list[AccountMetadata]:
    """특정 상위 계정의 하위 계정 목록을 반환한다.

    Args:
        parent: 상위 계정 코드.

    Returns:
        해당 상위 계정을 parent로 갖는 AccountMetadata 리스트.
    """
    return [meta for meta in ACCOUNT_METADATA.values() if meta.parent == parent]


def lookup(code: StandardAccount) -> AccountMetadata:
    """표준 계정 코드로 메타데이터를 조회한다.

    Args:
        code: 표준 계정과목 코드.

    Returns:
        해당 계정의 AccountMetadata.

    Raises:
        KeyError: 등록되지 않은 계정 코드.
    """
    try:
        return ACCOUNT_METADATA[code]
    except KeyError:
        raise KeyError(
            f"등록되지 않은 계정 코드: {code!r}. "
            f"ACCOUNT_METADATA에 해당 StandardAccount를 등록하세요."
        ) from None


# ---------------------------------------------------------------------------
# 무결성 검증 (모듈 로드 시 실행)
# ---------------------------------------------------------------------------


def _validate_completeness() -> None:
    """모든 StandardAccount 멤버가 ACCOUNT_METADATA에 등록되었는지 검증한다.

    모듈 임포트 시 자동 실행되며, 누락된 계정이 있으면 즉시 오류를 발생시킨다.
    """
    missing = [acct for acct in StandardAccount if acct not in ACCOUNT_METADATA]
    if missing:
        raise RuntimeError(
            f"ACCOUNT_METADATA에 누락된 StandardAccount 항목: "
            f"{[m.name for m in missing]}"
        )


_validate_completeness()
