"""FDD LLM-as-Judge Gate — 6차원 LLM 평가 (Gate 2).

6개 품질 차원 (FDD 맞춤 가중치):
1. numerical_accuracy (25%) — 엔진 결과와 텍스트 수치 일치
2. completeness (20%) — 필수 분석 항목 빠짐없이 기술
3. analytical_depth (20%) — 원인 분석, 트렌드, 딜 임팩트
4. professionalism (15%) — Big 4 FDD 수준 용어/문장 구조
5. evidence_linking (15%) — EvidenceRef 연결 여부
6. confidentiality (5%) — 프로젝트 코드명, 민감 정보 마스킹
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Awaitable

from app.ralph.gates.base import DimensionScore, GateResult, QualityGate

logger = logging.getLogger(__name__)

LLMCallFn = Callable[[str, str, float, int], Awaitable[str]]

_JUDGE_SYSTEM_PROMPT = """You are a senior FDD quality reviewer at a Big 4 accounting firm.
Evaluate the provided FDD report section on 6 quality dimensions.

For each dimension, provide:
- score: 0.0 to 5.0 (5 is perfect Big 4 quality)
- feedback: specific, actionable improvement suggestions

## Dimensions (weights)
1. numerical_accuracy (25%): Do numbers in the text exactly match the engine data?
2. completeness (20%): Are all required analysis items covered without gaps?
3. analytical_depth (20%): Does the text provide root-cause analysis, trends, and deal impact (not just lists)?
4. professionalism (15%): Is the language at Big 4 FDD standard (terminology, structure, benchmarking)?
5. evidence_linking (15%): Does every claim reference its data source?
6. confidentiality (5%): Are project codenames used instead of real names? Is sensitive info masked?

## Response Format (strict JSON)
```json
{
  "dimensions": [
    {"name": "numerical_accuracy", "score": 4.5, "feedback": "..."},
    {"name": "completeness", "score": 4.0, "feedback": "..."},
    {"name": "analytical_depth", "score": 3.5, "feedback": "..."},
    {"name": "professionalism", "score": 4.2, "feedback": "..."},
    {"name": "evidence_linking", "score": 3.8, "feedback": "..."},
    {"name": "confidentiality", "score": 5.0, "feedback": "..."}
  ],
  "critical_flags": [],
  "overall_feedback": "..."
}
```

Only output JSON. No additional text."""

_JUDGE_USER_PROMPT = """## Section Under Review
Section ID: {section_id}
Block Type: {block_type}

## Refined Content
```json
{artifact_content}
```

## Engine Data (Ground Truth)
```json
{source_data}
```

Evaluate this section against all 6 dimensions. Return strict JSON."""

# 차원 가중치 매핑
_DIMENSION_WEIGHTS: dict[str, tuple[str, float]] = {
    "numerical_accuracy": ("수치 정확성", 0.25),
    "completeness": ("완전성", 0.20),
    "analytical_depth": ("분석 깊이", 0.20),
    "professionalism": ("전문성", 0.15),
    "evidence_linking": ("근거 연결", 0.15),
    "confidentiality": ("기밀 준수", 0.05),
}


class FDDLLMJudgeGate(QualityGate):
    """FDD LLM-as-Judge 다차원 평가 Gate (Gate 2)."""

    def __init__(self, llm_call: LLMCallFn) -> None:
        self._llm_call = llm_call

    @property
    def name(self) -> str:
        return "fdd_llm_judge"

    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        """LLM을 사용하여 6차원 평가를 수행한다."""
        start_ns = time.perf_counter_ns()

        section_id = prd_section.get("id", "unknown")
        block_type = prd_section.get("block_type", "text")

        user_prompt = _JUDGE_USER_PROMPT.format(
            section_id=section_id,
            block_type=block_type,
            artifact_content=artifact_path[:4000],  # 토큰 제한
            source_data=json.dumps(source_data or {}, ensure_ascii=False)[:2000],
        )

        try:
            response_text = await self._llm_call(
                _JUDGE_SYSTEM_PROMPT,
                user_prompt,
                0.1,   # temperature (일관된 평가)
                1024,  # max_tokens
            )
            eval_result = self._parse_evaluation(response_text)
        except Exception as e:
            logger.error("LLM Judge evaluation failed: %s", e)
            return self._timed_result(
                start_ns,
                dimensions=[DimensionScore("llm_error", "LLM 오류", 0.0, 1.0, str(e))],
                issues=[f"LLM evaluation failed: {e}"],
                suggestions=["Retry with different parameters"],
                critical_flags=[],
                cost_usd=0.02,  # estimated cost even on failure
            )

        # DimensionScore 리스트 구성
        dimensions: list[DimensionScore] = []
        for dim_data in eval_result.get("dimensions", []):
            dim_name = dim_data.get("name", "")
            label, weight = _DIMENSION_WEIGHTS.get(dim_name, (dim_name, 0.1))
            dimensions.append(DimensionScore(
                name=dim_name,
                label=label,
                score=min(5.0, max(0.0, float(dim_data.get("score", 0)))),
                weight=weight,
                feedback=dim_data.get("feedback", ""),
            ))

        # 누락된 차원 기본값 추가
        evaluated_names = {d.name for d in dimensions}
        for dim_name, (label, weight) in _DIMENSION_WEIGHTS.items():
            if dim_name not in evaluated_names:
                dimensions.append(DimensionScore(
                    name=dim_name, label=label, score=3.0, weight=weight,
                    feedback="Not evaluated",
                ))

        critical_flags = eval_result.get("critical_flags", [])
        overall = eval_result.get("overall_feedback", "")

        # 이슈/제안 추출
        issues: list[str] = []
        suggestions: list[str] = []
        for d in dimensions:
            if d.score < 3.5 and d.feedback:
                issues.append(f"[{d.label}] {d.feedback}")
            elif d.score < 4.0 and d.feedback:
                suggestions.append(f"[{d.label}] {d.feedback}")

        if overall:
            suggestions.append(f"[Overall] {overall}")

        return self._timed_result(
            start_ns, dimensions, issues, suggestions, critical_flags,
            cost_usd=0.03,  # estimated LLM cost per evaluation
        )

    def _parse_evaluation(self, response: str) -> dict:
        """LLM 응답에서 평가 JSON을 추출한다."""
        text = response.strip()

        # Markdown code fence 제거
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM judge response as JSON")
            return {
                "dimensions": [
                    {"name": "parse_error", "score": 2.0, "feedback": "Could not parse LLM response"},
                ],
                "critical_flags": [],
                "overall_feedback": "Evaluation parse error",
            }
