"""체크리스트 필드 레지스트리 — 80개 표준 필드 정의.

VDR 파싱 시 추출할 필드 목록을 정의한다.
각 필드는 카테고리, 키, 라벨, 타입, 단위, 필수 여부를 포함한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FieldCategory = Literal[
    "FINANCIAL", "COMPANY", "MARKET", "DEAL", "MANAGEMENT", "SHAREHOLDERS"
]
FieldType = Literal["text", "number", "currency", "percentage", "date", "list"]


@dataclass(frozen=True)
class FieldDefinition:
    """체크리스트 필드 정의."""

    field_key: str
    field_label: str
    category: FieldCategory
    field_type: FieldType = "text"
    unit: str | None = None
    is_required: bool = True
    fiscal_year: int | None = None


# ---------------------------------------------------------------------------
# FINANCIAL (30항목: 10개 지표 × 3개년)
# ---------------------------------------------------------------------------

_FINANCIAL_METRICS: list[tuple[str, str, FieldType, str | None]] = [
    ("revenue", "매출액", "currency", "백만원"),
    ("cogs", "매출원가", "currency", "백만원"),
    ("gross_profit", "매출총이익", "currency", "백만원"),
    ("operating_income", "영업이익", "currency", "백만원"),
    ("ebitda", "EBITDA", "currency", "백만원"),
    ("net_income", "순이익", "currency", "백만원"),
    ("total_assets", "총자산", "currency", "백만원"),
    ("total_equity", "자본총계", "currency", "백만원"),
    ("total_debt", "총차입금", "currency", "백만원"),
    ("cash", "현금성자산", "currency", "백만원"),
]

_FINANCIAL_YEARS = [2022, 2023, 2024]


def _build_financial_fields() -> list[FieldDefinition]:
    """3개년 × 10개 지표 = 30개 재무 필드 생성."""
    fields: list[FieldDefinition] = []
    sort_base = 0
    for year in _FINANCIAL_YEARS:
        for key_base, label_base, ftype, unit in _FINANCIAL_METRICS:
            fields.append(
                FieldDefinition(
                    field_key=f"{key_base}_{year}",
                    field_label=f"{label_base} ({year})",
                    category="FINANCIAL",
                    field_type=ftype,
                    unit=unit,
                    is_required=key_base in ("revenue", "operating_income", "ebitda", "net_income"),
                    fiscal_year=year,
                )
            )
            sort_base += 1
    return fields


# ---------------------------------------------------------------------------
# COMPANY (12항목)
# ---------------------------------------------------------------------------

_COMPANY_FIELDS: list[FieldDefinition] = [
    FieldDefinition("company_name", "회사명 (한글)", "COMPANY"),
    FieldDefinition("company_name_en", "회사명 (영문)", "COMPANY", is_required=False),
    FieldDefinition("founded_date", "설립일", "COMPANY", field_type="date"),
    FieldDefinition("ceo_name", "대표이사", "COMPANY"),
    FieldDefinition("employee_count", "임직원 수", "COMPANY", field_type="number", unit="명"),
    FieldDefinition("headquarters", "본사 소재지", "COMPANY"),
    FieldDefinition("business_registration_no", "사업자등록번호", "COMPANY", is_required=False),
    FieldDefinition("industry_classification", "업종 분류", "COMPANY"),
    FieldDefinition("main_products", "주요 제품/서비스", "COMPANY", field_type="list"),
    FieldDefinition("website", "웹사이트", "COMPANY", is_required=False),
    FieldDefinition("company_description", "회사 개요", "COMPANY"),
    FieldDefinition("history_highlights", "주요 연혁", "COMPANY", field_type="list", is_required=False),
]

# ---------------------------------------------------------------------------
# MARKET (8항목)
# ---------------------------------------------------------------------------

_MARKET_FIELDS: list[FieldDefinition] = [
    FieldDefinition("tam", "TAM (Total Addressable Market)", "MARKET", field_type="currency", unit="억원"),
    FieldDefinition("sam", "SAM (Serviceable Addressable Market)", "MARKET", field_type="currency", unit="억원", is_required=False),
    FieldDefinition("som", "SOM (Serviceable Obtainable Market)", "MARKET", field_type="currency", unit="억원", is_required=False),
    FieldDefinition("market_growth_rate", "시장 성장률", "MARKET", field_type="percentage"),
    FieldDefinition("market_position", "시장 내 위치", "MARKET"),
    FieldDefinition("key_competitors", "주요 경쟁사", "MARKET", field_type="list"),
    FieldDefinition("competitive_advantage", "경쟁 우위", "MARKET", field_type="list"),
    FieldDefinition("industry_trends", "산업 트렌드", "MARKET", field_type="list", is_required=False),
]

# ---------------------------------------------------------------------------
# DEAL (10항목)
# ---------------------------------------------------------------------------

_DEAL_FIELDS: list[FieldDefinition] = [
    FieldDefinition("deal_type", "거래 유형", "DEAL"),
    FieldDefinition("deal_background", "거래 배경", "DEAL"),
    FieldDefinition("stake_pct", "매각 지분율", "DEAL", field_type="percentage"),
    FieldDefinition("asking_price", "매각 희망가", "DEAL", field_type="currency", unit="억원", is_required=False),
    FieldDefinition("valuation_method", "밸류에이션 방법론", "DEAL"),
    FieldDefinition("ev_ebitda_multiple", "EV/EBITDA 배수", "DEAL", field_type="number", unit="x"),
    FieldDefinition("deal_timeline", "거래 일정", "DEAL"),
    FieldDefinition("key_conditions", "주요 조건", "DEAL", field_type="list", is_required=False),
    FieldDefinition("advisor_name", "자문사", "DEAL", is_required=False),
    FieldDefinition("investment_highlights", "투자 하이라이트", "DEAL", field_type="list"),
]

# ---------------------------------------------------------------------------
# MANAGEMENT (10항목: 5명 × name/title)
# ---------------------------------------------------------------------------

_MANAGEMENT_FIELDS: list[FieldDefinition] = []
for _n in range(1, 6):
    _MANAGEMENT_FIELDS.extend([
        FieldDefinition(
            f"mgmt_{_n}_name", f"경영진 {_n} 성명", "MANAGEMENT",
            is_required=_n <= 2,
        ),
        FieldDefinition(
            f"mgmt_{_n}_title", f"경영진 {_n} 직책", "MANAGEMENT",
            is_required=_n <= 2,
        ),
    ])

# ---------------------------------------------------------------------------
# SHAREHOLDERS (10항목: 5명 × name/pct)
# ---------------------------------------------------------------------------

_SHAREHOLDERS_FIELDS: list[FieldDefinition] = []
for _n in range(1, 6):
    _SHAREHOLDERS_FIELDS.extend([
        FieldDefinition(
            f"sh_{_n}_name", f"주주 {_n} 성명", "SHAREHOLDERS",
            is_required=_n <= 2,
        ),
        FieldDefinition(
            f"sh_{_n}_pct", f"주주 {_n} 지분율", "SHAREHOLDERS",
            field_type="percentage",
            is_required=_n <= 2,
        ),
    ])


# ---------------------------------------------------------------------------
# 레지스트리
# ---------------------------------------------------------------------------

_ALL_FIELDS: list[FieldDefinition] | None = None


def get_all_fields() -> list[FieldDefinition]:
    """전체 체크리스트 필드 목록을 반환한다 (캐싱)."""
    global _ALL_FIELDS
    if _ALL_FIELDS is None:
        _ALL_FIELDS = [
            *_build_financial_fields(),
            *_COMPANY_FIELDS,
            *_MARKET_FIELDS,
            *_DEAL_FIELDS,
            *_MANAGEMENT_FIELDS,
            *_SHAREHOLDERS_FIELDS,
        ]
    return _ALL_FIELDS


def get_fields_by_category(category: FieldCategory) -> list[FieldDefinition]:
    """특정 카테고리의 필드만 반환한다."""
    return [f for f in get_all_fields() if f.category == category]


def get_field_by_key(field_key: str) -> FieldDefinition | None:
    """field_key로 필드 정의를 조회한다."""
    for f in get_all_fields():
        if f.field_key == field_key:
            return f
    return None


def get_required_fields() -> list[FieldDefinition]:
    """필수 필드만 반환한다."""
    return [f for f in get_all_fields() if f.is_required]


def get_category_summary() -> dict[str, int]:
    """카테고리별 필드 수를 반환한다."""
    summary: dict[str, int] = {}
    for f in get_all_fields():
        summary[f.category] = summary.get(f.category, 0) + 1
    return summary
