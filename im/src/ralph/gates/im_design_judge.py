"""IM LLM Design Judge — LLM 기반 IM PPTX 6차원 디자인 평가.

PPTX 텍스트 전문 + 슬라이드 구조 메타데이터를 LLM에 전달하여
디자인 품질을 6차원으로 평가한다.

6차원:
1. information_density: 슬라이드당 정보량 적절성
2. visual_hierarchy: 시각적 위계 명확성
3. chart_effectiveness: 차트 효과성
4. slide_narrative_flow: 스토리텔링 흐름
5. brand_consistency: AMIC 디자인 시스템 일관성
6. investor_readiness: 투자자 대면 준비도
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Awaitable

from src.ralph.gates.base import DimensionScore, GateResult, QualityGate

logger = logging.getLogger(__name__)

IM_DESIGN_JUDGE_SYSTEM_PROMPT = """당신은 M&A Investment Banking의 시니어 IM(Investment Memorandum) 디자인 심사위원입니다.
IM PPTX 문서의 디자인 품질을 6개 차원으로 평가합니다.

## AMIC 디자인 시스템
- 5단계 그린 팔레트: Signature(#0F3A32) → Solid(#1C8F57) → Highlight(#26C260) → Fresh(#A3E96B) → Light(#E6FDD6)
- 헤딩: SUITE Bold
- 본문: Pretendard Regular/Medium
- 데이터/KPI: Pretendard ExtraBold

## 평가 차원 (각 1~5점)

1. **information_density** (0.20): 슬라이드당 정보량이 적절한가? 과밀하거나 과소하지 않은가?
2. **visual_hierarchy** (0.20): 제목→본문→수치의 시각적 위계가 명확한가?
3. **chart_effectiveness** (0.20): 차트/그래프가 데이터를 효과적으로 인사이트로 전달하는가?
4. **slide_narrative_flow** (0.15): 슬라이드 간 스토리텔링 흐름이 자연스러운가?
5. **brand_consistency** (0.10): AMIC 디자인 시스템 (색상, 폰트, 레이아웃)이 일관적인가?
6. **investor_readiness** (0.15): Goldman Sachs / Morgan Stanley 수준의 투자자 대면 준비가 되었는가?

## 점수 앵커
- 5점: Goldman Sachs / Morgan Stanley 급
- 4점: 전문적이고 깔끔한 딜 문서
- 3점: 기업 내부 보고서 수준
- 2점: 아마추어/학생 프레젠테이션
- 1점: 사용 불가

## 출력 형식 (JSON만, 다른 텍스트 없이)
```json
{
  "dimensions": [
    {"name": "information_density", "score": 4, "feedback": "구체적 피드백"},
    {"name": "visual_hierarchy", "score": 4, "feedback": "구체적 피드백"},
    {"name": "chart_effectiveness", "score": 3, "feedback": "구체적 피드백"},
    {"name": "slide_narrative_flow", "score": 4, "feedback": "구체적 피드백"},
    {"name": "brand_consistency", "score": 5, "feedback": "구체적 피드백"},
    {"name": "investor_readiness", "score": 4, "feedback": "구체적 피드백"}
  ],
  "critical_issues": ["있다면 나열"],
  "improvement_suggestions": ["구체적 개선 제안"]
}
```
"""

IM_DESIGN_WEIGHTS: dict[str, tuple[float, str]] = {
    "information_density": (0.20, "정보 밀도"),
    "visual_hierarchy": (0.20, "시각적 위계"),
    "chart_effectiveness": (0.20, "차트 효과성"),
    "slide_narrative_flow": (0.15, "내러티브 흐름"),
    "brand_consistency": (0.10, "브랜드 일관성"),
    "investor_readiness": (0.15, "투자자 준비도"),
}


class IMLLMDesignJudge(QualityGate):
    """IM LLM 디자인 심사 게이트.

    Args:
        llm_call: async (system, user) -> str 시그니처의 LLM 호출 함수.
    """

    def __init__(
        self,
        llm_call: Callable[[str, str], Awaitable[str]] | None = None,
    ) -> None:
        self._llm_call = llm_call

    @property
    def name(self) -> str:
        return "im_llm_design_judge"

    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        start = time.perf_counter_ns()

        if self._llm_call is None:
            return self._timed_result(
                start,
                [],
                ["LLM Design Judge 비활성: llm_call 미설정"],
                [],
                [],
            )

        # 1. PPTX에서 텍스트 + 구조 메타데이터 추출
        try:
            slide_metadata = self._extract_slide_metadata(artifact_path)
        except Exception as exc:
            return self._timed_result(
                start,
                [],
                [f"PPTX 메타데이터 추출 실패: {exc}"],
                [],
                [],
            )

        # 2. LLM 호출
        user_prompt = self._build_user_prompt(slide_metadata, prd_section)

        try:
            response = await self._llm_call(
                IM_DESIGN_JUDGE_SYSTEM_PROMPT,
                user_prompt,
            )
        except Exception as exc:
            return self._timed_result(
                start,
                [],
                [f"LLM 호출 실패: {exc}"],
                [],
                [],
                cost_usd=0.02,
            )

        # 3. 응답 파싱
        dimensions, issues, suggestions, critical_flags = self._parse_response(response)

        return self._timed_result(
            start,
            dimensions,
            issues,
            suggestions,
            critical_flags,
            cost_usd=0.03,
            raw_data={"slide_count": len(slide_metadata)},
        )

    def _extract_slide_metadata(self, pptx_path: str) -> list[dict[str, Any]]:
        """PPTX에서 슬라이드별 메타데이터를 추출한다."""
        from pptx import Presentation

        prs = Presentation(pptx_path)
        slides_meta: list[dict[str, Any]] = []

        for slide_idx, slide in enumerate(prs.slides, 1):
            meta: dict[str, Any] = {
                "slide_number": slide_idx,
                "texts": [],
                "has_chart": False,
                "has_table": False,
                "chart_count": 0,
                "table_count": 0,
                "shape_count": len(slide.shapes),
                "total_chars": 0,
            }

            for shape in slide.shapes:
                if shape.has_text_frame:
                    text = shape.text_frame.text.strip()
                    if text:
                        meta["texts"].append(text[:200])  # 200자 제한
                        meta["total_chars"] += len(text)
                if shape.has_chart:
                    meta["has_chart"] = True
                    meta["chart_count"] += 1
                if shape.has_table:
                    meta["has_table"] = True
                    meta["table_count"] += 1

            slides_meta.append(meta)

        return slides_meta

    def _build_user_prompt(
        self,
        slides_meta: list[dict[str, Any]],
        prd_section: dict[str, Any],
    ) -> str:
        """LLM 사용자 프롬프트를 구성한다."""
        lines = [
            f"## IM 문서 분석 ({len(slides_meta)}장 슬라이드)",
            f"문서 유형: {prd_section.get('memo_type', 'IM')}",
            "",
            "### 슬라이드별 구조",
        ]

        for meta in slides_meta[:30]:  # 최대 30장
            texts_preview = " | ".join(meta["texts"][:3])
            extras = []
            if meta["chart_count"]:
                extras.append(f"차트 {meta['chart_count']}개")
            if meta["table_count"]:
                extras.append(f"테이블 {meta['table_count']}개")
            extra_str = f" [{', '.join(extras)}]" if extras else ""

            lines.append(
                f"- 슬라이드 {meta['slide_number']} "
                f"({meta['total_chars']}자{extra_str}): {texts_preview[:100]}"
            )

        # 통계 요약
        total_chars = sum(m["total_chars"] for m in slides_meta)
        total_charts = sum(m["chart_count"] for m in slides_meta)
        total_tables = sum(m["table_count"] for m in slides_meta)

        lines.extend(
            [
                "",
                "### 통계 요약",
                f"- 총 슬라이드: {len(slides_meta)}장",
                f"- 총 텍스트: {total_chars:,}자",
                f"- 차트: {total_charts}개",
                f"- 테이블: {total_tables}개",
                f"- 평균 텍스트/슬라이드: {total_chars // max(len(slides_meta), 1)}자",
                "",
                "위 구조를 기반으로 6차원 디자인 품질을 평가해주세요.",
            ]
        )

        return "\n".join(lines)

    def _parse_response(
        self,
        response_text: str,
    ) -> tuple[list[DimensionScore], list[str], list[str], list[str]]:
        """LLM 응답을 파싱한다."""
        dimensions: list[DimensionScore] = []
        issues: list[str] = []
        suggestions: list[str] = []
        critical_flags: list[str] = []

        try:
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(json_text)

            for dim_data in data.get("dimensions", []):
                dim_name = dim_data.get("name", "")
                if dim_name in IM_DESIGN_WEIGHTS:
                    weight, label = IM_DESIGN_WEIGHTS[dim_name]
                    score = float(dim_data.get("score", 3.0))
                    feedback = dim_data.get("feedback", "")

                    dimensions.append(
                        DimensionScore(
                            name=dim_name,
                            label=label,
                            score=min(5.0, max(1.0, score)),
                            weight=weight,
                            feedback=feedback,
                        )
                    )

                    if score < 3.0:
                        issues.append(f"{label}: {feedback}")

            critical_flags.extend(data.get("critical_issues", []))
            suggestions.extend(data.get("improvement_suggestions", []))

        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("LLM Design Judge 응답 파싱 실패: %s", exc)
            for dim_name, (weight, label) in IM_DESIGN_WEIGHTS.items():
                dimensions.append(
                    DimensionScore(
                        name=dim_name,
                        label=label,
                        score=3.0,
                        weight=weight,
                        feedback="응답 파싱 실패 — 기본 점수 적용",
                    )
                )

        return dimensions, issues, suggestions, critical_flags
