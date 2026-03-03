"""태그 파서 — 내러티브 텍스트 내 특수 태그 파싱.

내러티브 텍스트에 포함된 `[Chart:...]`, `[FinancialTable:...]` 등의
인라인 태그를 파싱하여 구조화된 데이터로 변환한다.

Usage::

    from src.design_renderer.tm_pipeline.tag_parser import parse_tags

    tags = parse_tags(narrative_text)
    for tag in tags:
        print(tag.tag_type, tag.params)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ParsedTag:
    """파싱된 인라인 태그."""

    tag_type: str  # "Chart", "FinancialTable", "KPI", "Source"
    params: dict[str, str] = field(default_factory=dict)
    raw: str = ""  # 원본 태그 문자열
    start: int = 0  # 원본 텍스트 내 시작 위치
    end: int = 0  # 원본 텍스트 내 종료 위치


# 태그 패턴: [TagType:key=value,key=value]
_TAG_PATTERN = re.compile(
    r"\[(?P<type>Chart|FinancialTable|KPI|Source)"
    r":(?P<params>[^\]]*)\]"
)

# 파라미터 패턴: key=value
_PARAM_PATTERN = re.compile(r"(?P<key>\w+)=(?P<value>[^,\]]+)")


def parse_tags(text: str) -> list[ParsedTag]:
    """텍스트 내 인라인 태그를 파싱.

    Args:
        text: 내러티브 텍스트.

    Returns:
        파싱된 태그 리스트.
    """
    tags: list[ParsedTag] = []
    for match in _TAG_PATTERN.finditer(text):
        tag_type = match.group("type")
        params_str = match.group("params")
        params: dict[str, str] = {}
        for param_match in _PARAM_PATTERN.finditer(params_str):
            params[param_match.group("key")] = param_match.group("value").strip()

        tags.append(
            ParsedTag(
                tag_type=tag_type,
                params=params,
                raw=match.group(0),
                start=match.start(),
                end=match.end(),
            )
        )
    return tags


def strip_tags(text: str) -> str:
    """텍스트에서 인라인 태그를 제거.

    Args:
        text: 태그가 포함된 텍스트.

    Returns:
        태그가 제거된 텍스트.
    """
    return _TAG_PATTERN.sub("", text).strip()


def extract_chart_refs(text: str) -> list[dict[str, str]]:
    """텍스트에서 차트 참조만 추출.

    Args:
        text: 내러티브 텍스트.

    Returns:
        차트 참조 딕셔너리 리스트 (chart_id, title 등).
    """
    tags = parse_tags(text)
    return [t.params for t in tags if t.tag_type == "Chart"]
