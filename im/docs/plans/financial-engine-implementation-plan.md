# Phase 3: Financial Engine 구현 계획

> 작성일: 2026-02-09 15:52:55
> 최종 수정: 2026-02-10 21:04:09
> 대상: Phase 3 Financial Engine (`src/financial_engine/`)
> 스프린트: S3 (1주)
> 티켓: 14개
> 상태: **✅ v0.3.0 완료** (14개 티켓, 18개 소스 파일, 187 tests 전체 통과)
>
> **문서 관리 규칙**: 본 문서 업데이트 시 PowerShell `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'`로 현재 시각을 확인하여 "최종 수정" 필드에 `yyyy-MM-dd HH:mm:ss` 형식으로 기재한다.

---

## 1. 개요

### 1.1 목적

Data Ingestor(Phase 2)가 DART API에서 수집한 **한글 재무 데이터**를 Design Renderer(Phase 4)의 `FinancialStatements` 형식으로 변환하는 **데이터 정규화/계산 계층**을 구축한다.

### 1.2 핵심 기능

| 기능 | 설명 |
|------|------|
| 계정 매핑 | 한글 계정명(매출액, 영업이익 등) → 표준 코드(REVENUE, OP_INCOME) |
| 단위 정규화 | 천원/백만원/억원 → 원 단위 Decimal 변환 |
| 파생 지표 산출 | EBITDA, FCF, CAGR, GPM, OPM, ROE 등 |
| 데이터 검증 | A=L+E 균형 검증, 다기간 일관성 검증 |

### 1.3 데이터 흐름

```
┌─────────────────────────────────────────────┐
│ Data Ingestor (Phase 2) ✅                   │
│ DartFinancialStatement                       │
│ - account_nm: str (한글)                     │
│ - thstrm_amount / frmtrm_amount: Decimal     │
│ - bsns_year: str                             │
│ FinancialStatementsCollection                │
│ - get_account_values(account_nm) → dict      │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Financial Engine (Phase 3) ✅                │
│ 1. AccountMapper: 한글→StandardAccount       │
│ 2. UnitNormalizer: 단위→원(Decimal)          │
│ 3. Calculator: EBITDA, FCF, margins, CAGR   │
│ 4. Validator: 균형 검증, 일관성 검증          │
│ 5. ProcessingResult.to_financial_statements()│
│    → Decimal → float 변환                    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Design Renderer (Phase 4) ✅                 │
│ FinancialStatements                          │
│ - revenue: dict[str, float]                  │
│ - operating_income: dict[str, float]         │
│ - ebitda: dict[str, float]  (← 계산 필요)    │
│ - free_cash_flow: dict[str, float]           │
│ ... (총 20개 필드)                            │
└─────────────────────────────────────────────┘
```

### 1.4 입출력 계약

**입력** (`src/data_ingestor/dart/models.py:149`):
```python
class DartFinancialStatement(DartBaseModel):
    account_nm: str          # "매출액", "영업이익" 등 (한글)
    bsns_year: str           # "2024"
    thstrm_amount: str       # 당기금액 (콤마 정리 후 Decimal 변환)
    frmtrm_amount: str       # 전기금액
    bfefrmtrm_amount: str    # 전전기금액
    fs_div: str              # "CFS" (연결) / "OFS" (별도)

class FinancialStatementsCollection(DartBaseModel):
    items: list[DartFinancialStatement]
    def get_account_values(account_nm, consolidated=True) -> dict[str, Decimal | None]
```

**출력** (`src/design_renderer/im_document.py:131`):
```python
@dataclass
class FinancialStatements:
    # 손익계산서
    revenue: dict[str, float] = field(default_factory=dict)
    cost_of_goods_sold: dict[str, float] = field(default_factory=dict)
    gross_profit: dict[str, float] = field(default_factory=dict)
    operating_income: dict[str, float] = field(default_factory=dict)
    ebitda: dict[str, float] = field(default_factory=dict)
    net_income: dict[str, float] = field(default_factory=dict)
    sga_expenses: dict[str, float] = field(default_factory=dict)
    # 재무상태표
    total_assets: dict[str, float] = field(default_factory=dict)
    total_liabilities: dict[str, float] = field(default_factory=dict)
    total_equity: dict[str, float] = field(default_factory=dict)
    cash_and_equivalents: dict[str, float] = field(default_factory=dict)
    total_debt: dict[str, float] = field(default_factory=dict)
    # 현금흐름표
    operating_cash_flow: dict[str, float] = field(default_factory=dict)
    investing_cash_flow: dict[str, float] = field(default_factory=dict)
    financing_cash_flow: dict[str, float] = field(default_factory=dict)
    capex: dict[str, float] = field(default_factory=dict)
    free_cash_flow: dict[str, float] = field(default_factory=dict)
    # 추가
    extra: dict[str, dict[str, float]] = field(default_factory=dict)
```

---

## 2. 모듈 구조

```
src/financial_engine/
├── __init__.py                    # Public API, __version__ = "0.3.0"
├── exceptions.py                  # FinancialEngineError 예외 계층
├── mapper/
│   ├── __init__.py
│   ├── chart_of_accounts.py       # T-F01: StandardAccount Enum (50+)
│   ├── korean_accounts.py         # T-F02: KOREAN_ACCOUNT_MAP (200+)
│   └── account_mapper.py          # T-F03: AccountMapper (rapidfuzz)
├── normalizer/
│   ├── __init__.py
│   ├── unit_normalizer.py         # T-F04: UnitNormalizer
│   └── currency_converter.py      # T-F05: CurrencyConverter
├── calculator/
│   ├── __init__.py
│   ├── profitability.py           # T-F06: GPM, OPM, NPM, ROA, ROE
│   ├── growth.py                  # T-F07: YoY, CAGR
│   ├── cash_flow.py               # T-F08: EBITDA, FCF, NWC
│   └── leverage.py                # T-F09: D/E, ICR
├── validator/
│   ├── __init__.py
│   ├── balance_checker.py         # T-F10: A = L + E 검증
│   └── consistency_checker.py     # T-F11: 다기간 일관성 검증
└── processor.py                   # T-F12: FinancialProcessor 파이프라인
```

---

## 3. 핵심 설계 결정

### 3.1 Decimal 전용 내부 계산

모든 내부 계산은 `Decimal` 타입으로 수행하며, `float` 변환은 최종 `to_financial_statements()` 호출 시에만 발생한다. 이를 통해 재무 데이터의 정밀도를 보존한다.

```python
# 내부: Decimal로 계산
mapped_data[StandardAccount.REVENUE]["2024"] = Decimal("150000000000")

# 최종 변환 (processor.py → to_financial_statements())
revenue = {"2024": float(Decimal("150000000000"))}  # → 150000000000.0
```

### 3.2 3단계 계정명 매칭

```
1단계: 정확 일치 — KOREAN_ACCOUNT_MAP dict lookup (O(1))
2단계: 퍼지 매칭 — rapidfuzz.process.extractOne (score_cutoff=80)
3단계: 실패 처리 — unmapped_accounts 목록에 기록 + warnings
```

### 3.3 Exception 계층

`data_ingestor/exceptions.py` 패턴을 그대로 미러링:

```python
FinancialEngineError (base)          # message + details dict
├── MappingError                     # 계정 매핑 실패
├── NormalizationError               # 단위/통화 정규화 실패
│   └── CurrencyConversionError      # 통화 변환 실패
├── CalculationError                 # 지표 계산 실패
└── ValidationError                  # 데이터 검증 실패
```

### 3.4 Graceful Missing Data 처리

Calculator 함수는 입력이 `None`이거나 누락된 연도가 있을 때 예외를 발생시키지 않고 해당 지표를 `None`으로 반환하며 `warnings` 목록에 기록한다. Design Renderer는 이미 빈 `dict`(`{}`)를 핸들링할 수 있다.

### 3.5 process_from_dart() 편의 메서드

`FinancialStatementsCollection`에서 직접 처리 가능한 편의 메서드를 제공:

```python
# 방법 1: DART 컬렉션 직접 전달
result = processor.process_from_dart(collection, consolidated=True)

# 방법 2: dict로 변환 후 전달
raw_data = {"매출액": {"2024": Decimal("150000000000")}, ...}
result = processor.process(raw_data, source_unit="원")
```

---

## 4. 핵심 클래스 시그니처

### 4.1 mapper/chart_of_accounts.py (T-F01)

```python
class StatementType(str, Enum):
    """재무제표 유형."""
    INCOME_STATEMENT = "IS"
    BALANCE_SHEET = "BS"
    CASH_FLOW = "CF"

class AccountSign(str, Enum):
    """계정과목 부호 관례."""
    DEBIT = "debit"
    CREDIT = "credit"

class StandardAccount(str, Enum):
    """표준 계정과목 코드 (50+).

    IS: REVENUE, COGS, GROSS_PROFIT, SGA_EXPENSES, OPERATING_INCOME,
        DEPRECIATION, AMORTIZATION, INTEREST_EXPENSE, NET_INCOME, ...
    BS: TOTAL_ASSETS, CURRENT_ASSETS, CASH_AND_EQUIVALENTS, PPE,
        TOTAL_LIABILITIES, TOTAL_EQUITY, RETAINED_EARNINGS, ...
    CF: OPERATING_CASH_FLOW, INVESTING_CASH_FLOW, FINANCING_CASH_FLOW, CAPEX, ...
    """

@dataclass(frozen=True)
class AccountMetadata:
    code: StandardAccount
    statement_type: StatementType
    sign: AccountSign
    is_subtotal: bool = False
    parent: StandardAccount | None = None

ACCOUNT_METADATA: dict[StandardAccount, AccountMetadata]  # 전체 50+ 계정
```

### 4.2 mapper/korean_accounts.py (T-F02)

```python
KOREAN_ACCOUNT_MAP: dict[str, StandardAccount] = {
    "매출액": StandardAccount.REVENUE,
    "영업수익": StandardAccount.REVENUE,
    "순매출": StandardAccount.REVENUE,
    # ... 200+ 매핑
}

def get_korean_names(account: StandardAccount) -> list[str]:
    """표준 계정의 모든 한글 동의어 반환."""
```

### 4.3 mapper/account_mapper.py (T-F03)

```python
@dataclass(frozen=True)
class AccountMapping:
    original_name: str
    standard_code: StandardAccount
    confidence: float          # 0.0 ~ 1.0
    match_type: str           # "exact" | "fuzzy" | "custom"

@dataclass
class MappingConfig:
    fuzzy_threshold: int = 80
    strict_mode: bool = False
    custom_mappings: dict[str, StandardAccount] = field(default_factory=dict)

class AccountMapper:
    def __init__(self, config: MappingConfig | None = None) -> None
    def map(self, account_name: str) -> AccountMapping | None
    def map_all(self, data: dict[str, dict[str, Decimal]]) -> dict[StandardAccount, dict[str, Decimal]]
    def add_synonym(self, korean_name: str, standard_code: StandardAccount) -> None
    @property
    def unmapped_accounts(self) -> list[str]
```

### 4.4 normalizer/unit_normalizer.py (T-F04)

```python
@dataclass(frozen=True)
class UnitScale:
    name: str
    multiplier: Decimal
    patterns: list[str]       # regex patterns

UNIT_SCALES: list[UnitScale]  # 원, 천원, 백만원, 억원, 조원

class UnitNormalizer:
    def normalize(self, value: str, *, source_unit: str | None = None) -> Decimal
    def normalize_batch(self, data: dict[str, str | Decimal], *, source_unit: str | None = None) -> dict[str, Decimal]
    def detect_unit(self, value: str) -> UnitScale | None
    def convert(self, value: Decimal, *, from_unit: str, to_unit: str) -> Decimal
```

### 4.5 normalizer/currency_converter.py (T-F05)

```python
@dataclass(frozen=True)
class ExchangeRate:
    from_currency: str
    to_currency: str
    rate: Decimal
    source: str               # "api" | "static"
    as_of_date: str

@dataclass(frozen=True)
class CurrencyConfig:
    api_url: str = ""
    api_key: str = ""
    timeout: float = 10.0
    fallback_rates: dict[str, Decimal]  # {"USD_KRW": Decimal("1350"), ...}

class CurrencyConverter:
    def __init__(self, config: CurrencyConfig | None = None) -> None
    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> ExchangeRate
    def convert(self, amount: Decimal, from_currency: str, to_currency: str, *, rate: ExchangeRate | None = None) -> Decimal
```

### 4.6 calculator/profitability.py (T-F06)

```python
@dataclass(frozen=True)
class ProfitabilityMetrics:
    gross_profit_margin: dict[str, float]       # {year: GPM %}
    operating_profit_margin: dict[str, float]    # {year: OPM %}
    net_profit_margin: dict[str, float]          # {year: NPM %}
    roa: dict[str, float]                        # {year: ROA %}
    roe: dict[str, float]                        # {year: ROE %}

def calculate_margin(numerator: Decimal | None, denominator: Decimal | None) -> float | None
def calculate_profitability(revenue, gross_profit, operating_income, net_income, total_assets, total_equity) -> ProfitabilityMetrics
```

### 4.7 calculator/growth.py (T-F07)

```python
@dataclass(frozen=True)
class GrowthMetrics:
    yoy: dict[str, dict[str, float]]    # {metric_name: {year: yoy%}}
    cagr_3y: dict[str, float]           # {metric_name: cagr}
    cagr_5y: dict[str, float]

def calculate_yoy(values: dict[str, Decimal]) -> dict[str, float]
def calculate_cagr(start_value: Decimal, end_value: Decimal, years: int) -> float | None
def calculate_growth(metrics: dict[str, dict[str, Decimal]]) -> GrowthMetrics
```

### 4.8 calculator/cash_flow.py (T-F08)

```python
@dataclass(frozen=True)
class CashFlowMetrics:
    ebitda: dict[str, Decimal]
    free_cash_flow: dict[str, Decimal]
    net_working_capital: dict[str, Decimal]
    ebitda_margin: dict[str, float]

def calculate_ebitda(operating_income, depreciation, amortization=None) -> dict[str, Decimal]
def calculate_fcf(operating_cash_flow, capex) -> dict[str, Decimal]
def calculate_nwc(current_assets, current_liabilities) -> dict[str, Decimal]
def calculate_cash_flow_metrics(...) -> CashFlowMetrics
```

### 4.9 calculator/leverage.py (T-F09)

```python
@dataclass(frozen=True)
class LeverageMetrics:
    debt_to_equity: dict[str, float]
    interest_coverage: dict[str, float]
    net_debt_to_ebitda: dict[str, float]

def calculate_debt_to_equity(total_liabilities, total_equity) -> dict[str, float]
def calculate_interest_coverage(operating_income, interest_expense) -> dict[str, float]
def calculate_leverage(...) -> LeverageMetrics
```

### 4.10 validator/balance_checker.py (T-F10)

```python
@dataclass(frozen=True)
class BalanceCheckConfig:
    tolerance: Decimal = Decimal("1000")
    tolerance_pct: float = 0.001

@dataclass(frozen=True)
class BalanceCheckResult:
    year: str
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    difference: Decimal
    is_balanced: bool

@dataclass
class BalanceCheckReport:
    results: list[BalanceCheckResult]
    all_balanced: bool
    warnings: list[str]

class BalanceChecker:
    def __init__(self, config: BalanceCheckConfig | None = None) -> None
    def check(self, total_assets, total_liabilities, total_equity) -> BalanceCheckReport
    def check_year(self, year, assets, liabilities, equity) -> BalanceCheckResult
```

### 4.11 validator/consistency_checker.py (T-F11)

```python
class AnomalyType(str, Enum):
    LARGE_CHANGE = "large_change"
    SIGN_REVERSAL = "sign_reversal"
    RETAINED_EARNINGS_MISMATCH = "re_mismatch"
    MISSING_DATA = "missing_data"

@dataclass(frozen=True)
class ConsistencyAnomaly:
    anomaly_type: AnomalyType
    account: str
    year: str
    description: str
    severity: str             # "warning" | "error"

@dataclass
class ConsistencyReport:
    anomalies: list[ConsistencyAnomaly]
    is_consistent: bool

class ConsistencyChecker:
    def __init__(self, config: ConsistencyConfig | None = None) -> None
    def check(self, data: dict[str, dict[str, Decimal]]) -> ConsistencyReport
    def check_retained_earnings(self, retained_earnings, net_income, dividends=None) -> list[ConsistencyAnomaly]
```

### 4.12 processor.py (T-F12)

```python
@dataclass
class ProcessingResult:
    mapped_data: dict[StandardAccount, dict[str, Decimal]]
    profitability: ProfitabilityMetrics
    growth: GrowthMetrics
    cash_flow: CashFlowMetrics
    leverage: LeverageMetrics
    balance_check: BalanceCheckReport
    consistency_check: ConsistencyReport
    unmapped_accounts: list[str]
    warnings: list[str]

    def to_financial_statements(self) -> FinancialStatements:
        """design_renderer.im_document.FinancialStatements로 변환.
        Decimal → float, StandardAccount → 필드명 매핑.
        """

@dataclass(frozen=True)
class ProcessorConfig:
    source_unit: str = "원"
    target_unit: str = "원"
    mapping_config: MappingConfig = field(default_factory=MappingConfig)
    validate: bool = True

class FinancialProcessor:
    def __init__(self, config: ProcessorConfig | None = None) -> None
    def process(self, raw_data: dict[str, dict[str, str | Decimal]], *, source_unit: str | None = None) -> ProcessingResult
    def process_from_dart(self, collection: FinancialStatementsCollection, *, consolidated: bool = True) -> ProcessingResult
```

---

## 5. 의존성 그래프

```
    T-F01 (chart_of_accounts)    T-F02 (korean_accounts)
           \                         /
            \                       /
             v                     v
          T-F03 (account_mapper)
                  |
                  v
 T-F04       T-F05       T-F06  T-F07  T-F08  T-F09      T-F10
 (unit)    (currency) (profit) (growth)(cash) (leverage) (balance)
   \          /           \      |      |       /            |
    \        /             \     |      |      /             v
     v      v               v   v      v     v          T-F11
  [Normalizer]              [Calculator]              (consistency)
        \                       /                        /
         \                     /                        /
          v                   v                        v
                    T-F12 (processor.py)
                           |
                    +------+------+
                    |             |
                    v             v
              T-F13 (tests)  T-F14 (E2E)
```

---

## 6. 병렬 실행 계획

### Step 1: 인프라 (직렬, 선행 작업)

- `src/financial_engine/exceptions.py` — 예외 계층
- `src/financial_engine/mapper/__init__.py`
- `src/financial_engine/normalizer/__init__.py`
- `src/financial_engine/calculator/__init__.py`
- `src/financial_engine/validator/__init__.py`

### Step 2: Group A (6개 병렬 — 의존성 없음)

| Ticket | 파일 | 워크스트림 | 핵심 내용 |
|--------|------|-----------|-----------|
| T-F01 | `mapper/chart_of_accounts.py` | A: Mapping | `StandardAccount` Enum 50+, `AccountMetadata` |
| T-F02 | `mapper/korean_accounts.py` | A: Mapping | `KOREAN_ACCOUNT_MAP` dict 200+ |
| T-F04 | `normalizer/unit_normalizer.py` | B: Normalization | "1,500백만원" → `Decimal("1500000000")` |
| T-F05 | `normalizer/currency_converter.py` | B: Normalization | USD/EUR → KRW, fallback 정적 환율 |
| T-F06 | `calculator/profitability.py` | C: Calculation | GPM, OPM, NPM, ROA, ROE |
| T-F07 | `calculator/growth.py` | C: Calculation | YoY, 3Y/5Y CAGR |

### Step 3: Group B (3개 병렬 — T-F01 참조만)

| Ticket | 파일 | 워크스트림 | 핵심 내용 |
|--------|------|-----------|-----------|
| T-F08 | `calculator/cash_flow.py` | C: Calculation | EBITDA=OI+D&A, FCF=OCF-CapEx, NWC |
| T-F09 | `calculator/leverage.py` | C: Calculation | D/E, ICR, Net Debt/EBITDA |
| T-F10 | `validator/balance_checker.py` | D: Validation | A=L+E, 허용 오차 |

### Step 4: Group C (2개 병렬)

| Ticket | 파일 | 의존 | 핵심 내용 |
|--------|------|------|-----------|
| T-F03 | `mapper/account_mapper.py` | ← T-F01, T-F02 | rapidfuzz 퍼지 매칭, 90%+ 정확도 |
| T-F11 | `validator/consistency_checker.py` | ← T-F10 | 50%+ 변동, 이익잉여금 연속성 |

### Step 5: Group D (직렬)

| Ticket | 파일 | 의존 | 핵심 내용 |
|--------|------|------|-----------|
| T-F12 | `processor.py` | ← T-F03~T-F11 | `FinancialProcessor` 파이프라인 + `to_financial_statements()` |

### Step 6: Group E (직렬)

| Ticket | 핵심 내용 |
|--------|-----------|
| T-F13 | 단위/통합 테스트, 커버리지 90%+ |
| T-F14 | E2E: `FinancialStatementsCollection` → `FinancialProcessor` → `FinancialStatements` |

---

## 7. 티켓 상세

### T-F01: chart_of_accounts.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Account Mapping |
| **의존성** | ← 없음 |
| **설명** | IFRS/K-IFRS 기반 표준 계정과목 코드 50+ 정의. `StatementType`(IS/BS/CF), `AccountSign`(debit/credit), `StandardAccount` Enum, `AccountMetadata` dataclass |
| **산출물** | `src/financial_engine/mapper/chart_of_accounts.py` |
| **검증** | 필수 계정(REVENUE, COGS, OP_INCOME, NET_INCOME, TOTAL_ASSETS, TOTAL_LIABILITIES, TOTAL_EQUITY) 존재 확인 |
| **예상 테스트** | 8개 |

### T-F02: korean_accounts.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Account Mapping |
| **의존성** | ← 없음 |
| **설명** | DART API 한글 계정명 200+ 동의어 사전. "매출액", "영업수익", "순매출" → REVENUE 등 |
| **산출물** | `src/financial_engine/mapper/korean_accounts.py` |
| **검증** | 주요 7개 계정 각각 2+ 동의어 존재 확인, reverse lookup |
| **예상 테스트** | 10개 |

### T-F03: account_mapper.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Account Mapping |
| **의존성** | ← T-F01, T-F02 |
| **설명** | rapidfuzz 기반 퍼지 매칭 엔진. 정확일치 → fuzzy(cutoff=80) → 실패. `AccountMapping` 결과에 confidence 포함 |
| **산출물** | `src/financial_engine/mapper/account_mapper.py` |
| **검증** | 매핑 정확도 90%+ 테스트, strict mode MappingError, custom_mappings |
| **예상 테스트** | 15개 |

### T-F04: unit_normalizer.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Normalization |
| **의존성** | ← 없음 |
| **설명** | 한국 재무 단위 정규화. "1,500백만원" → `Decimal("1500000000")`, "3.5억원" → `Decimal("350000000")` |
| **산출물** | `src/financial_engine/normalizer/unit_normalizer.py` |
| **검증** | 원/천원/백만원/억원/조원 각 변환, 콤마/소수점/음수/빈문자열 처리 |
| **예상 테스트** | 12개 |

### T-F05: currency_converter.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Normalization |
| **의존성** | ← 없음 |
| **설명** | USD/EUR/JPY → KRW 변환. async API 호출 + fallback 정적 환율 |
| **산출물** | `src/financial_engine/normalizer/currency_converter.py` |
| **검증** | 변환 정확도, API mock, fallback 동작, KRW→KRW 패스스루 |
| **예상 테스트** | 8개 |

### T-F06: profitability.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Calculation |
| **의존성** | ← 없음 |
| **설명** | 수익성 지표: GPM=매출총이익/매출, OPM=영업이익/매출, NPM=순이익/매출, ROA=순이익/자산, ROE=순이익/자본 |
| **산출물** | `src/financial_engine/calculator/profitability.py` |
| **검증** | 각 비율 계산, zero revenue, None 값, 음수 마진 |
| **예상 테스트** | 10개 |

### T-F07: growth.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Calculation |
| **의존성** | ← 없음 |
| **설명** | 성장 지표: YoY=(current-prev)/prev, CAGR=(end/start)^(1/n)-1 |
| **산출물** | `src/financial_engine/calculator/growth.py` |
| **검증** | CAGR(100, 150, 3)≈14.47%, 단일연도 데이터, zero start |
| **예상 테스트** | 10개 |

### T-F08: cash_flow.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Calculation |
| **의존성** | ← 없음 |
| **설명** | EBITDA=영업이익+D&A, FCF=OCF-CapEx, NWC=유동자산-유동부채 |
| **산출물** | `src/financial_engine/calculator/cash_flow.py` |
| **검증** | 각 지표 계산, D&A 누락 시 처리, EBITDA margin |
| **예상 테스트** | 10개 |

### T-F09: leverage.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Calculation |
| **의존성** | ← 없음 |
| **설명** | D/E=부채/자본, ICR=영업이익/이자비용, Net Debt/EBITDA |
| **산출물** | `src/financial_engine/calculator/leverage.py` |
| **검증** | zero equity, zero interest expense, 음수 자본 |
| **예상 테스트** | 8개 |

### T-F10: balance_checker.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Validation |
| **의존성** | ← 없음 |
| **설명** | 자산=부채+자본 등식 검증. 절대 오차 + 비율 오차 두 방식 지원 |
| **산출물** | `src/financial_engine/validator/balance_checker.py` |
| **검증** | 균형/불균형/오차범위내 케이스, 연도별 결과 |
| **예상 테스트** | 8개 |

### T-F11: consistency_checker.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Validation |
| **의존성** | ← T-F10 |
| **설명** | 다기간 일관성: 50%+ YoY 변동 탐지, 부호 반전, 이익잉여금 연속성(RE(t)=RE(t-1)+NI-Div) |
| **산출물** | `src/financial_engine/validator/consistency_checker.py` |
| **검증** | 이상 탐지, 안정 데이터 통과, 커스텀 threshold |
| **예상 테스트** | 10개 |

### T-F12: processor.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Orchestration |
| **의존성** | ← T-F03~T-F11 |
| **설명** | `FinancialProcessor` 파이프라인: mapping → normalization → calculation → validation → `ProcessingResult.to_financial_statements()` |
| **산출물** | `src/financial_engine/processor.py` |
| **검증** | full pipeline, process_from_dart, Decimal→float 변환, unmapped 추적 |
| **예상 테스트** | 12개 |

### T-F13: 테스트 스위트 ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-F12 |
| **설명** | `tests/test_financial_engine/` 모듈별 테스트 + conftest.py fixtures |
| **산출물** | 14개 테스트 파일, 187개 테스트 전체 통과 |
| **검증** | `pytest tests/test_financial_engine/ -v`, 커버리지 90%+ |

### T-F14: E2E Integration ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-D15, T-F12 |
| **설명** | DART API → FinancialProcessor → FinancialStatements 전체 흐름 |
| **산출물** | `tests/test_integration/test_dart_to_financial.py` |
| **검증** | 실제 DART 형식 데이터로 round-trip, 전체 20개 필드 매핑 확인 |

---

## 8. 테스트 전략

### 8.1 테스트 구조

```
tests/test_financial_engine/
├── __init__.py
├── conftest.py                    # 공유 fixture
│   ├── sample_dart_data           # 한글 계정명 + Decimal 3개년 데이터
│   ├── sample_balanced_bs         # 균형 재무상태표
│   └── sample_unbalanced_bs       # 불균형 재무상태표
├── test_exceptions.py             # ~12 tests
├── test_chart_of_accounts.py      # ~8 tests
├── test_korean_accounts.py        # ~10 tests
├── test_account_mapper.py         # ~15 tests
├── test_unit_normalizer.py        # ~12 tests
├── test_currency_converter.py     # ~8 tests
├── test_profitability.py          # ~10 tests
├── test_growth.py                 # ~10 tests
├── test_cash_flow.py              # ~10 tests
├── test_leverage.py               # ~8 tests
├── test_balance_checker.py        # ~8 tests
├── test_consistency_checker.py    # ~10 tests
└── test_processor.py              # ~12 tests

tests/test_integration/
└── test_dart_to_financial.py      # ~8 tests

총 실제 결과: 14개 테스트 파일, 187 tests 전체 통과
```

### 8.2 테스트 방법론

| 방법 | 적용 대상 |
|------|-----------|
| 단위 테스트 | 모든 함수/메서드 |
| Property-based (Hypothesis) | CAGR, margin 수학적 불변성 |
| Parametrize | 단위 변환, 계정 매핑 edge cases |
| Integration | processor.py full pipeline |
| E2E | DART → FinancialStatements round-trip |

### 8.3 핵심 검증 항목

```python
# CAGR 수학 검증
assert abs(calculate_cagr(Decimal("100"), Decimal("150"), 3) - 0.1447) < 0.001

# EBITDA 공식
assert ebitda["2024"] == operating_income["2024"] + depreciation["2024"]

# Balance check
assert total_assets["2024"] == total_liabilities["2024"] + total_equity["2024"]

# Decimal → float 변환
fs = result.to_financial_statements()
assert isinstance(fs.revenue["2024"], float)
```

---

## 9. 리스크 & 대응

| # | 리스크 | 심각도 | 대응 |
|---|--------|--------|------|
| 1 | 한글 계정명 모호성 (업종별 차이) | HIGH | 3단계 매칭 + `custom_mappings` + confidence 점수 |
| 2 | DART 단위 미표기 | MEDIUM | 명시적 `source_unit` 파라미터 + balance check 교차 검증 |
| 3 | D&A 미공시 → EBITDA 계산 불가 | MEDIUM | `None` 반환 + `warnings` 기록, renderer가 `{}` 핸들링 |
| 4 | Decimal → float 정밀도 손실 | LOW | 최종 변환 단계에서만 수행, 내부 Decimal 유지 |
| 5 | rapidfuzz 성능 | LOW | exact match 우선(O(1)), fuzzy는 miss시만 (200개 항목은 μs 수준) |
| 6 | 환율 API 장애 | LOW | `fallback_rates` 정적 환율, 대부분 DART 데이터는 KRW |

---

## 10. 재사용 기존 코드

| 파일 | 재사용 요소 |
|------|-------------|
| `src/data_ingestor/exceptions.py` | Exception 계층 패턴 (message + details dict) |
| `src/data_ingestor/dart/models.py:302` | `FinancialStatementsCollection.get_account_values()` — 입력 추출 |
| `src/design_renderer/im_document.py:131` | `FinancialStatements` dataclass — 출력 타겟 |
| `src/data_ingestor/aggregator.py` | `FinancialSummary` 패턴 참고 |

---

## 11. 검증 계획

```bash
# 1. 단위 테스트
pytest tests/test_financial_engine/ -v

# 2. 커버리지
pytest tests/test_financial_engine/ --cov=src/financial_engine --cov-report=term-missing

# 3. E2E 테스트
pytest tests/test_integration/test_dart_to_financial.py -v

# 4. 타입 체크
mypy src/financial_engine/

# 5. 코드 포맷
black --check src/financial_engine/ tests/test_financial_engine/
isort --check-only src/financial_engine/ tests/test_financial_engine/
```

**결과**: 테스트 187개 전체 통과, 커버리지 90%+

---

## 12. 마일스톤

| 단계 | 완료 시 | 성과물 | 상태 |
|------|---------|--------|------|
| Step 1 완료 | 인프라 준비 | `exceptions.py`, 모든 `__init__.py` | ✅ 완료 |
| Step 2 완료 | 기초 모듈 | 6개 독립 모듈 + 각각 테스트 | ✅ 완료 |
| Step 3 완료 | 계산/검증 | 모든 Calculator + BalanceChecker | ✅ 완료 |
| Step 4 완료 | 핵심 엔진 | AccountMapper(fuzzy) + ConsistencyChecker | ✅ 완료 |
| Step 5 완료 | 통합 파이프라인 | `FinancialProcessor.process()` 동작 | ✅ 완료 |
| Step 6 완료 | **v0.3.0 릴리스** | 전체 테스트 통과, E2E 검증 완료 | ✅ 완료 |
