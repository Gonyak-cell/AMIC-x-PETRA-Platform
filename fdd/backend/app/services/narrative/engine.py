"""Narrative Engine — 서술문 자동 생성.

FDD 분석 결과를 기반으로 템플릿 기반 서술문을 생성합니다.
LLM을 사용하지 않고, Jinja2 템플릿과 데이터 바인딩 방식을 사용합니다.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, Template

NARRATIVE_VERSION = "0.1.0"

# 템플릿 디렉토리 경로
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "narratives"


@dataclass
class NarrativeTemplate:
    """서술문 템플릿."""

    name: str
    text: str
    variables: list[str] = field(default_factory=list)
    category: str = "general"


# 내장 템플릿 정의
BUILTIN_TEMPLATES: dict[str, NarrativeTemplate] = {
    "qoe_summary": NarrativeTemplate(
        name="qoe_summary",
        category="qoe",
        text="""{{ period }} 기준 Reported EBITDA는 {{ reported_ebitda }}원이며, 총 {{ adjustment_count }}건의 조정을 통해 Adjusted EBITDA {{ adjusted_ebitda }}원을 산출하였습니다.

{% if adjustments %}주요 조정항목:
{% for adj in adjustments[:3] %}- {{ adj.category }}: {{ adj.amount }}원 ({{ adj.description }})
{% endfor %}{% endif %}
{% if adjustment_ratio > 0.1 %}조정비율이 {{ adjustment_ratio|round(1) }}%로 높은 편이며, 추가 검토가 필요합니다.{% endif %}""",
        variables=["period", "reported_ebitda", "adjusted_ebitda", "adjustment_count", "adjustments", "adjustment_ratio"],
    ),
    "qoe_adjustment_detail": NarrativeTemplate(
        name="qoe_adjustment_detail",
        category="qoe",
        text="""{{ category }} 조정: {{ amount }}원

{{ description }}

{% if evidence_refs %}근거자료:
{% for ref in evidence_refs %}- {{ ref.source_type }}: {{ ref.source_id }}
{% endfor %}{% endif %}""",
        variables=["category", "amount", "description", "evidence_refs"],
    ),
    "nwc_summary": NarrativeTemplate(
        name="nwc_summary",
        category="nwc",
        text="""{{ period }} 기준 Net Working Capital은 {{ total_nwc }}원입니다.

유동자산 {{ current_assets }}원에서 유동부채 {{ current_liabilities }}원을 차감하여 산출하였습니다.

{% if peg_method %}Target NWC Peg 방식: {{ peg_method }}
Target NWC: {{ target_nwc }}원
{% if adjustment %}Price Adjustment: {{ adjustment }}원{% endif %}{% endif %}""",
        variables=["period", "total_nwc", "current_assets", "current_liabilities", "peg_method", "target_nwc", "adjustment"],
    ),
    "nwc_trend": NarrativeTemplate(
        name="nwc_trend",
        category="nwc",
        text="""{{ period_start }}부터 {{ period_end }}까지 NWC 추이 분석:

{% if trend == "increasing" %}NWC가 증가 추세를 보이고 있습니다. 평균 월간 증가율은 {{ avg_change }}%입니다.{% elif trend == "decreasing" %}NWC가 감소 추세를 보이고 있습니다. 평균 월간 감소율은 {{ avg_change }}%입니다.{% else %}NWC가 안정적으로 유지되고 있습니다.{% endif %}

{% if key_drivers %}주요 변동 요인:
{% for driver in key_drivers %}- {{ driver }}
{% endfor %}{% endif %}""",
        variables=["period_start", "period_end", "trend", "avg_change", "key_drivers"],
    ),
    "debt_summary": NarrativeTemplate(
        name="debt_summary",
        category="debt",
        text="""{{ period }} 기준 Net Debt는 {{ net_debt }}원입니다.

총 차입금 {{ total_debt }}원에서 현금 및 현금성 자산 {{ cash }}원을 차감하여 산출하였습니다.

{% if debt_like_items %}Debt-like 항목 ({{ debt_like_total }}원):
{% for item in debt_like_items %}- {{ item.name }}: {{ item.amount }}원{% if item.reason %} ({{ item.reason }}){% endif %}
{% endfor %}{% endif %}

{% if ifrs16_impact %}IFRS 16 리스부채 영향: {{ ifrs16_impact }}원{% endif %}""",
        variables=["period", "net_debt", "total_debt", "cash", "debt_like_items", "debt_like_total", "ifrs16_impact"],
    ),
    "executive_summary": NarrativeTemplate(
        name="executive_summary",
        category="summary",
        text="""Financial Due Diligence Summary — {{ deal_name }}

분석 기간: {{ analysis_period }}
대상 회사: {{ target_name }}

■ Quality of Earnings
{{ qoe_summary }}

■ Net Working Capital
{{ nwc_summary }}

■ Net Debt
{{ debt_summary }}

{% if key_findings %}■ Key Findings
{% for finding in key_findings %}- {{ finding }}
{% endfor %}{% endif %}

{% if risk_factors %}■ Risk Factors
{% for risk in risk_factors %}- {{ risk }}
{% endfor %}{% endif %}""",
        variables=["deal_name", "analysis_period", "target_name", "qoe_summary", "nwc_summary", "debt_summary", "key_findings", "risk_factors"],
    ),
    "issue_highlight": NarrativeTemplate(
        name="issue_highlight",
        category="issue",
        text="""[{{ severity | upper }}] {{ title }}

Category: {{ category }}
Status: {{ status }}

{{ description }}

{% if recommendation %}권고사항: {{ recommendation }}{% endif %}""",
        variables=["severity", "title", "category", "status", "description", "recommendation"],
    ),
}


def _format_currency(value: Decimal | float | int | str | None) -> str:
    """금액을 한국어 형식으로 포맷팅합니다."""
    if value is None:
        return "-"
    try:
        if isinstance(value, str):
            value = Decimal(value.replace(",", ""))
        return f"{Decimal(str(value)):,.0f}"
    except Exception:
        return str(value)


def _format_percentage(value: Decimal | float | int | str | None) -> str:
    """백분율을 포맷팅합니다."""
    if value is None:
        return "-"
    try:
        if isinstance(value, str):
            value = float(value)
        return f"{float(value):.1f}%"
    except Exception:
        return str(value)


def _create_jinja_env() -> Environment:
    """Jinja2 환경을 생성합니다."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)) if TEMPLATES_DIR.exists() else None,
        autoescape=False,
    )
    # 커스텀 필터 등록
    env.filters["currency"] = _format_currency
    env.filters["percentage"] = _format_percentage
    return env


def load_narrative_template(template_name: str) -> NarrativeTemplate:
    """템플릿을 로드합니다.

    Args:
        template_name: 템플릿 이름

    Returns:
        NarrativeTemplate 인스턴스

    Raises:
        ValueError: 템플릿을 찾을 수 없음
    """
    # 내장 템플릿 확인
    if template_name in BUILTIN_TEMPLATES:
        return BUILTIN_TEMPLATES[template_name]

    # YAML 파일에서 로드 시도
    yaml_path = TEMPLATES_DIR / f"{template_name}.yaml"
    if yaml_path.exists():
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return NarrativeTemplate(
                name=template_name,
                text=data.get("text", ""),
                variables=data.get("variables", []),
                category=data.get("category", "general"),
            )

    raise ValueError(f"Template not found: {template_name}")


def generate_narrative(
    template_name: str,
    context: dict[str, Any],
) -> str:
    """템플릿 기반 서술문을 생성합니다.

    Args:
        template_name: 템플릿 이름
        context: 템플릿 변수 딕셔너리

    Returns:
        생성된 서술문
    """
    template = load_narrative_template(template_name)
    env = _create_jinja_env()
    jinja_template = env.from_string(template.text)
    return jinja_template.render(**context).strip()


def generate_qoe_narrative(
    period: str,
    reported_ebitda: Decimal | str,
    adjusted_ebitda: Decimal | str,
    adjustments: list[dict[str, Any]] | None = None,
) -> str:
    """QoE 분석 결과 서술문을 생성합니다.

    Args:
        period: 분석 기간 (예: "FY2025")
        reported_ebitda: Reported EBITDA
        adjusted_ebitda: Adjusted EBITDA
        adjustments: 조정 항목 리스트

    Returns:
        QoE 서술문
    """
    adjustments = adjustments or []

    # 조정 비율 계산
    try:
        reported = Decimal(str(reported_ebitda).replace(",", ""))
        adjusted = Decimal(str(adjusted_ebitda).replace(",", ""))
        if reported != 0:
            adjustment_ratio = float(abs(adjusted - reported) / abs(reported) * 100)
        else:
            adjustment_ratio = 0.0
    except Exception:
        adjustment_ratio = 0.0

    return generate_narrative(
        "qoe_summary",
        {
            "period": period,
            "reported_ebitda": _format_currency(reported_ebitda),
            "adjusted_ebitda": _format_currency(adjusted_ebitda),
            "adjustment_count": len(adjustments),
            "adjustments": adjustments,
            "adjustment_ratio": adjustment_ratio,
        },
    )


def generate_nwc_narrative(
    period: str,
    total_nwc: Decimal | str,
    current_assets: Decimal | str,
    current_liabilities: Decimal | str,
    peg_method: str | None = None,
    target_nwc: Decimal | str | None = None,
    adjustment: Decimal | str | None = None,
) -> str:
    """NWC 분석 결과 서술문을 생성합니다.

    Args:
        period: 분석 기간
        total_nwc: 순운전자본
        current_assets: 유동자산
        current_liabilities: 유동부채
        peg_method: Peg 방식 (선택)
        target_nwc: Target NWC (선택)
        adjustment: 조정액 (선택)

    Returns:
        NWC 서술문
    """
    return generate_narrative(
        "nwc_summary",
        {
            "period": period,
            "total_nwc": _format_currency(total_nwc),
            "current_assets": _format_currency(current_assets),
            "current_liabilities": _format_currency(current_liabilities),
            "peg_method": peg_method,
            "target_nwc": _format_currency(target_nwc) if target_nwc else None,
            "adjustment": _format_currency(adjustment) if adjustment else None,
        },
    )


def generate_debt_narrative(
    period: str,
    net_debt: Decimal | str,
    total_debt: Decimal | str,
    cash: Decimal | str,
    debt_like_items: list[dict[str, Any]] | None = None,
    ifrs16_impact: Decimal | str | None = None,
) -> str:
    """Net Debt 분석 결과 서술문을 생성합니다.

    Args:
        period: 분석 기간
        net_debt: Net Debt
        total_debt: 총 차입금
        cash: 현금 및 현금성 자산
        debt_like_items: Debt-like 항목 리스트
        ifrs16_impact: IFRS 16 리스부채 영향

    Returns:
        Net Debt 서술문
    """
    debt_like_items = debt_like_items or []

    # Debt-like 합계 계산
    debt_like_total = Decimal("0")
    for item in debt_like_items:
        try:
            amount = item.get("amount", 0)
            if isinstance(amount, str):
                amount = Decimal(amount.replace(",", ""))
            debt_like_total += Decimal(str(amount))
        except Exception:
            pass

    return generate_narrative(
        "debt_summary",
        {
            "period": period,
            "net_debt": _format_currency(net_debt),
            "total_debt": _format_currency(total_debt),
            "cash": _format_currency(cash),
            "debt_like_items": debt_like_items,
            "debt_like_total": _format_currency(debt_like_total),
            "ifrs16_impact": _format_currency(ifrs16_impact) if ifrs16_impact else None,
        },
    )


def generate_executive_summary(
    deal_name: str,
    target_name: str,
    analysis_period: str,
    qoe_summary: str,
    nwc_summary: str,
    debt_summary: str,
    key_findings: list[str] | None = None,
    risk_factors: list[str] | None = None,
) -> str:
    """Executive Summary를 생성합니다.

    Args:
        deal_name: 딜 이름
        target_name: 대상 회사명
        analysis_period: 분석 기간
        qoe_summary: QoE 요약
        nwc_summary: NWC 요약
        debt_summary: Debt 요약
        key_findings: 주요 발견 사항 리스트
        risk_factors: 리스크 요인 리스트

    Returns:
        Executive Summary 서술문
    """
    return generate_narrative(
        "executive_summary",
        {
            "deal_name": deal_name,
            "target_name": target_name,
            "analysis_period": analysis_period,
            "qoe_summary": qoe_summary,
            "nwc_summary": nwc_summary,
            "debt_summary": debt_summary,
            "key_findings": key_findings or [],
            "risk_factors": risk_factors or [],
        },
    )
