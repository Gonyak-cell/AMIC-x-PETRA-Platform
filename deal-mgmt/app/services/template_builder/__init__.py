"""계약서 템플릿 빌더 패키지 — 5종 표준 템플릿 자동 생성.

5종 계약서(SPA/SHA/BTA/SSA/MOU) 각각에 대해 실제 한국 M&A 법률 조항 수준의
표준 템플릿 데이터를 생성한다. DB 모델과 독립적으로 동작한다.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import ClauseData, TemplateData, VariableData, extract_jinja_variables, validate_template_data
from .bta_builder import build_bta_template
from .docx_parser import parse_docx
from .mou_builder import build_mou_template
from .sha_builder import build_sha_template
from .spa_builder import build_spa_template
from .ssa_builder import build_ssa_template

# 5종 빌더 레지스트리: doc_type → builder function
BUILDERS: dict[str, Callable[[], TemplateData]] = {
    "SPA": build_spa_template,
    "SHA": build_sha_template,
    "BTA": build_bta_template,
    "SSA": build_ssa_template,
    "MOU": build_mou_template,
}

__all__ = [
    "BUILDERS",
    "ClauseData",
    "TemplateData",
    "VariableData",
    "build_bta_template",
    "build_mou_template",
    "build_sha_template",
    "build_spa_template",
    "build_ssa_template",
    "extract_jinja_variables",
    "parse_docx",
    "validate_template_data",
]
