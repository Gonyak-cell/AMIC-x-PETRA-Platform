"""템플릿 슬롯 기반 LLM 프롬프트 — Ralph Loop이 콘텐츠를 생성할 때 사용.

마스터 PPTX 템플릿의 슬라이드 구조를 LLM에게 알려주고,
각 슬롯에 맞는 TemplateContent JSON을 생성하도록 요청한다.
"""

from __future__ import annotations

import logging

from src.template_engine.schemas import TemplateContent
from src.template_engine.shape_mapper import ShapeSlot

logger = logging.getLogger(__name__)


def build_template_content_prompt(
    slots: list[ShapeSlot],
    checklist_json: str,
    memo_type: str,
    project_name: str,
) -> str:
    """템플릿 슬롯 기반 콘텐츠 생성 프롬프트를 구성한다.

    Args:
        slots: analyze_template()에서 반환된 ShapeSlot 목록.
        checklist_json: VDR 체크리스트 확정 데이터 (JSON 문자열).
        memo_type: "TM" | "DM".
        project_name: 프로젝트명.

    Returns:
        LLM에 전달할 시스템 프롬프트 + 유저 프롬프트 문자열.
    """
    # 슬라이드별 슬롯 구조 정리
    slide_descriptions = _build_slide_descriptions(slots)

    memo_label = {
        "TM": "Teaser Memorandum (TM)",
        "DM": "Discussion Memo (DM)",
    }.get(memo_type, memo_type)

    return f"""당신은 대한민국 투자은행(IB) M&A 자문 전문가입니다.
다음 VDR 체크리스트 데이터를 분석하여, {memo_label} PPTX의 각 슬라이드에 삽입할 콘텐츠를 JSON으로 생성하세요.

## 규칙
1. 모든 텍스트는 한국어로 작성하되, 고유명사와 약어(EBITDA, M&A 등)는 영문 유지
2. 차트 데이터는 실제 수치를 사용하고, 추세선이 논리적이어야 함
3. 테이블은 헤더 행을 제외한 데이터 행만 제공
4. 숫자는 천 단위 콤마 포함 (e.g. "1,234")
5. 비율은 소수점 1자리 (e.g. "12.3%")
6. 각 슬라이드의 콘텐츠는 투자자에게 설득력 있는 스토리텔링을 따름

## 프로젝트 정보
- 프로젝트명: {project_name}
- 문서 유형: {memo_label}

## 템플릿 슬라이드 구조
{slide_descriptions}

## VDR 체크리스트 데이터
```json
{checklist_json}
```

## 출력 형식
TemplateContent JSON을 반환하세요. 각 SlideContent는 slide_idx와 texts/charts/tables를 포함합니다.

```json
{{
  "project_name": "{project_name}",
  "date": "February 2026",
  "memo_type": "{memo_type}",
  "slides": [
    {{
      "slide_idx": 1,
      "title": "슬라이드 제목",
      "texts": {{"shape_name": "삽입할 텍스트"}},
      "charts": {{
        "shape_name": {{
          "categories": ["2022", "2023", "2024"],
          "series": [{{"name": "매출", "values": [100, 120, 150]}}]
        }}
      }},
      "tables": {{
        "shape_name": {{
          "rows": [["데이터1", "데이터2"]]
        }}
      }}
    }}
  ],
  "excluded_slides": []
}}
```"""


def _build_slide_descriptions(slots: list[ShapeSlot]) -> str:
    """슬라이드별 슬롯 구조를 텍스트로 정리한다."""
    # 슬라이드별 그룹핑
    by_slide: dict[int, list[ShapeSlot]] = {}
    for slot in slots:
        if slot.slide_idx not in by_slide:
            by_slide[slot.slide_idx] = []
        by_slide[slot.slide_idx].append(slot)

    lines: list[str] = []
    for slide_idx in sorted(by_slide.keys()):
        slide_slots = by_slide[slide_idx]

        # 슬라이드 제목 추출 (첫 번째 텍스트 shape)
        title = ""
        for s in slide_slots:
            if s.text_preview and s.shape_type in ("placeholder", "text"):
                title = s.text_preview
                break

        lines.append(f"\n### Slide {slide_idx + 1}: {title}")

        for s in slide_slots:
            if s.shape_type == "chart":
                lines.append(
                    f"  - **차트** `{s.shape_name}` ({s.chart_type}) — 카테고리 + 시리즈 데이터 필요"
                )
            elif s.shape_type == "table":
                rows, cols = s.table_size or (0, 0)
                lines.append(
                    f"  - **테이블** `{s.shape_name}` ({rows}행 × {cols}열) — 데이터 행 필요"
                )
            elif s.shape_type in ("text", "auto_shape", "placeholder"):
                preview = (s.text_preview or "")[:50]
                if preview:
                    lines.append(
                        f"  - **텍스트** `{s.shape_name}` — 현재: \"{preview}\""
                    )

    return "\n".join(lines)


def parse_template_content_response(response_json: dict) -> TemplateContent:
    """LLM 응답 JSON을 TemplateContent로 변환한다."""
    from src.template_engine.schemas import (
        ChartContent,
        SeriesData,
        SlideContent,
        TableContent,
    )

    slides: list[SlideContent] = []
    for slide_data in response_json.get("slides", []):
        try:
            # 차트 파싱
            charts: dict[str, ChartContent] = {}
            for name, chart_data in slide_data.get("charts", {}).items():
                series = [
                    SeriesData(
                        name=s.get("name", ""),
                        values=s.get("values", []),
                    )
                    for s in chart_data.get("series", [])
                ]
                charts[name] = ChartContent(
                    categories=chart_data.get("categories", []),
                    series=series,
                )

            # 테이블 파싱
            tables: dict[str, TableContent] = {}
            for name, table_data in slide_data.get("tables", {}).items():
                tables[name] = TableContent(
                    rows=table_data.get("rows", []),
                    headers=table_data.get("headers"),
                )

            slides.append(SlideContent(
                slide_idx=slide_data.get("slide_idx", 0),
                title=slide_data.get("title"),
                texts=slide_data.get("texts", {}),
                charts=charts,
                tables=tables,
            ))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            logger.warning(
                "LLM 응답에서 슬라이드 파싱 실패: %s", exc,
            )
            continue

    return TemplateContent(
        project_name=response_json.get("project_name", ""),
        date=response_json.get("date", ""),
        memo_type=response_json.get("memo_type", ""),
        slides=slides,
        excluded_slides=response_json.get("excluded_slides", []),
    )
