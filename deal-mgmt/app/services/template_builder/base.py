"""계약서 템플릿 빌더 — 공통 데이터 구조 및 유틸리티.

DB 모델과 독립적인 순수 데이터 클래스를 정의하여,
빌더가 DB 없이도 동작할 수 있도록 한다.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any


@dataclasses.dataclass(frozen=True, slots=True)
class ClauseData:
    """템플릿 조항 데이터 (DB 독립)."""

    clause_order: int
    title: str
    content: str
    is_boilerplate: bool = False
    condition_expression: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class VariableData:
    """템플릿 변수 데이터 (DB 독립)."""

    variable_key: str
    input_type: str  # TEXT, TEXTAREA, NUMBER, DATE, SELECT, BOOLEAN, CURRENCY, PERCENTAGE
    question_label: str
    description: str = ""
    default_value: str = ""
    is_required: bool = True
    select_options: dict[str, Any] | None = None
    display_order: int = 0
    group_name: str = ""
    visible_condition: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class TemplateData:
    """완성된 계약서 템플릿 데이터 (DB 독립)."""

    doc_type: str  # SPA, SHA, BTA, SSA, MOU
    name: str
    description: str
    clauses: list[ClauseData]
    variables: list[VariableData]
    version: str = "1.0"


# ── 공통 유틸리티 ─────────────────────────────────────────────────────────────

_JINJA_VAR_RE = re.compile(r"\{\{\s*(\w+)(?:\s*\|\s*\w+)?\s*\}\}")


def extract_jinja_variables(content: str) -> set[str]:
    """Jinja2 {{ var_name }} 또는 {{ var_name|filter }}에서 변수명을 추출한다."""
    return set(_JINJA_VAR_RE.findall(content))


def validate_template_data(data: TemplateData) -> list[str]:
    """템플릿 데이터의 무결성을 검증한다. 위반 사항 목록을 반환.

    검증 항목:
    1. 조항 순서(clause_order)가 1부터 연속인지
    2. 변수 키(variable_key)가 중복 없는지
    3. Jinja2 {{ var }}가 variables에 등록된 키와 일치하는지
    4. SELECT 타입 변수에 select_options가 있는지
    5. 필수 변수에 question_label이 있는지
    """
    issues: list[str] = []

    # 1. 조항 순서 연속성
    orders = sorted(c.clause_order for c in data.clauses)
    expected = list(range(1, len(data.clauses) + 1))
    if orders != expected:
        issues.append(f"clause_order 불연속: {orders} (기대: {expected})")

    # 2. 변수 키 중복 (O(n))
    keys = [v.variable_key for v in data.variables]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for k in keys:
        if k in seen:
            duplicates.add(k)
        seen.add(k)
    if duplicates:
        issues.append(f"중복 variable_key: {duplicates}")

    # 3. Jinja2 변수 ↔ 등록 변수 일치
    all_jinja_vars: set[str] = set()
    for clause in data.clauses:
        all_jinja_vars |= extract_jinja_variables(clause.content)

    registered_keys = {v.variable_key for v in data.variables}
    orphan_vars = all_jinja_vars - registered_keys
    if orphan_vars:
        issues.append(f"미등록 Jinja2 변수: {orphan_vars}")

    # 4. SELECT 타입 → select_options 필수
    for var in data.variables:
        if var.input_type == "SELECT" and not var.select_options:
            issues.append(f"SELECT 변수 '{var.variable_key}'에 select_options 누락")

    # 5. 필수 변수 → question_label 필수
    for var in data.variables:
        if var.is_required and not var.question_label.strip():
            issues.append(f"필수 변수 '{var.variable_key}'에 question_label 누락")

    return issues
