"""LLM-as-Judge Gate — 멀티 모델 Judge Panel 기반 다차원 콘텐츠 평가.

Judge Panel:
- Financial Judge (GPT-4o): 수치 정확성, 재무적 deal_impact 구체성
- Legal/Narrative Judge (Claude): 법률 분석 깊이, 서사 품질
- Completeness Judge (Gemini Flash): 저비용 1차 완전성 필터
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.ralph.gates.base import DimensionScore, GateResult, QualityGate

logger = logging.getLogger(__name__)

# ── 평가 프롬프트 템플릿 ──────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """당신은 20년 경력의 M&A 시니어 어드바이저입니다.
투자은행(IB) 수준의 M&A 문서 품질을 평가합니다.

각 차원에 대해 1-5점으로 평가하되, 반드시 점수를 부여하기 전에 추론 과정을 먼저 서술하세요 (G-Eval 방식).

점수 앵커:
- 5점: 즉시 딜을 추진하고 싶게 만드는 품질. 주요 IB 수준.
- 4점: 경미한 수정 후 사용 가능. 전문적.
- 3점: 보완 필요하지만 기본 구조는 갖춤.
- 2점: 대폭 재작업 필요. 아마추어 수준.
- 1점: 사용 불가. 회사 설명문 수준.
"""

LDD_JUDGE_PROMPT = """아래 LDD(법률실사) 보고서의 섹션을 평가해 주세요.

## 평가 대상 섹션
{section_text}

## 평가 차원 (각 1-5점)

1. **완전성 (completeness)**: DDRL 체크리스트 항목이 빠짐없이 기재되었는가?
2. **정확성 (accuracy)**: 법률 분석이 사실관계에 근거하고 논리적인가?
3. **설득력 (persuasiveness)**: deal_impact이 구체적이고 의사결정에 도움이 되는가?
4. **전문성 (professionalism)**: 법률 용어 사용이 적절하고 IB 수준의 표현인가?
5. **분석 깊이 (depth)**: 단순 사실 나열이 아닌 법적 쟁점과 리스크 분석이 있는가?
6. **기밀 준수 (confidentiality)**: 프로젝트 코드명을 사용하고 대상회사 정보를 적절히 처리했는가?

## 출력 형식 (JSON)
```json
{{
  "dimensions": [
    {{"name": "completeness", "score": 4, "reasoning": "...", "feedback": "..."}},
    {{"name": "accuracy", "score": 3, "reasoning": "...", "feedback": "구체적 개선 지시"}},
    ...
  ],
  "critical_flags": ["있다면 기재"],
  "overall_feedback": "전체적 평가 요약"
}}
```
"""

EXCEL_JUDGE_PROMPT = """아래 재무모델(Excel)의 콘텐츠를 평가해 주세요.

## 평가 대상 콘텐츠
{section_text}

## 평가 차원 (각 1-5점)

1. **가정값 합리성 (assumptions_quality)**: 매출 성장률, 마진, WACC 등 가정이 업계 벤치마크 대비 합리적인가?
2. **밸류에이션 방법론 (methodology)**: DCF/COMPS/LBO 방법론 적용이 정확한가? Terminal Value 계산이 적절한가?
3. **재무제표 정합성 (consistency)**: IS→BS→CF 간 수치가 일관적인가? BS 균형이 맞는가?
4. **전문성 (professionalism)**: IB/PE 수준의 구조와 표현인가? Named Range, 수식 참조가 적절한가?
5. **시나리오 분석 (scenario_depth)**: Base/Upside/Downside 시나리오가 충분한가? 민감도 분석이 있는가?
6. **가정 근거 (narrative)**: 각 가정의 근거가 명시되어 있는가? 출처가 기재되어 있는가?

## 출력 형식 (JSON)
```json
{{
  "dimensions": [
    {{"name": "assumptions_quality", "score": 4, "reasoning": "...", "feedback": "..."}},
    {{"name": "methodology", "score": 3, "reasoning": "...", "feedback": "구체적 개선 지시"}},
    {{"name": "consistency", "score": 4, "reasoning": "...", "feedback": "..."}},
    {{"name": "professionalism", "score": 3, "reasoning": "...", "feedback": "..."}},
    {{"name": "scenario_depth", "score": 3, "reasoning": "...", "feedback": "..."}},
    {{"name": "narrative", "score": 3, "reasoning": "...", "feedback": "..."}}
  ],
  "critical_flags": [],
  "overall_feedback": "전체적 평가 요약"
}}
```
"""

PPTX_JUDGE_PROMPT = """아래 M&A 메모랜덤({memo_type})의 콘텐츠를 평가해 주세요.

## 평가 대상 콘텐츠
{section_text}

## 평가 차원 (각 1-5점)

1. **완전성 (completeness)**: 필수 섹션과 정보가 빠짐없이 포함되었는가?
2. **정확성 (accuracy)**: 재무 수치가 일관적이고 교차 검증이 가능한가?
3. **설득력 (persuasiveness)**: 투자 논리(thesis)가 명확하고 PE 바이어를 설득할 수 있는가?
4. **전문성 (professionalism)**: IB급 어투, 구체적 수치, 업계 벤치마크를 활용하는가?
5. **분석 깊이 (depth)**: TAM/SAM/SOM, 경쟁 환경, 성장 전략이 구체적인가?
6. **기밀 준수 (confidentiality)**: TM의 경우 대상회사 역추적이 불가능한가?

## 출력 형식 (JSON)
```json
{{
  "dimensions": [
    {{"name": "completeness", "score": 4, "reasoning": "...", "feedback": "..."}},
    ...
  ],
  "critical_flags": [],
  "overall_feedback": "전체적 평가 요약"
}}
```
"""

# ── 차원별 가중치 ─────────────────────────────────────────────────────────────

LDD_WEIGHTS: dict[str, tuple[float, str]] = {
    "completeness": (0.20, "완전성"),
    "accuracy": (0.25, "정확성/일관성"),
    "persuasiveness": (0.20, "설득력"),
    "professionalism": (0.15, "전문성"),
    "depth": (0.15, "분석 깊이"),
    "confidentiality": (0.05, "기밀 준수"),
}

PPTX_WEIGHTS: dict[str, tuple[float, str]] = {
    "completeness": (0.20, "완전성"),
    "accuracy": (0.25, "정확성/일관성"),
    "persuasiveness": (0.20, "설득력"),
    "professionalism": (0.15, "전문성"),
    "depth": (0.15, "분석 깊이"),
    "confidentiality": (0.05, "기밀 준수"),
}

EXCEL_WEIGHTS: dict[str, tuple[float, str]] = {
    "assumptions_quality": (0.20, "가정값 합리성"),
    "methodology": (0.25, "밸류에이션 방법론"),
    "consistency": (0.20, "재무제표 정합성"),
    "professionalism": (0.15, "IB/PE 수준 구조"),
    "scenario_depth": (0.10, "시나리오 분석"),
    "narrative": (0.10, "가정 근거"),
}


class LLMJudgeGate(QualityGate):
    """LLM-as-Judge 멀티 모델 평가 게이트.

    Args:
        llm_provider: LLM 호출 함수 (async (system, user) -> str)
        doc_type: "ldd" | "pptx"
    """

    def __init__(
        self,
        llm_provider: Any = None,
        doc_type: str = "ldd",
    ) -> None:
        self._llm = llm_provider
        self._doc_type = doc_type
        if doc_type == "ldd":
            self._weights = LDD_WEIGHTS
        elif doc_type == "excel":
            self._weights = EXCEL_WEIGHTS
        else:
            self._weights = PPTX_WEIGHTS

    @property
    def name(self) -> str:
        return "llm_judge"

    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        start = time.perf_counter_ns()
        cost = 0.0

        # 문서에서 텍스트 추출
        text = self._extract_text(artifact_path)
        if not text:
            return self._timed_result(
                start,
                [],
                ["문서에서 텍스트를 추출할 수 없습니다"],
                [],
                [],
            )

        # LLM 호출
        if self._llm is None:
            return self._fallback_evaluate(start, text)

        try:
            prompt = self._build_prompt(text, prd_section)
            response = await self._llm(JUDGE_SYSTEM_PROMPT, prompt)
            cost = getattr(response, "cost_usd", 0.01)  # 비용 추적

            # JSON 파싱
            result_data = self._parse_response(response if isinstance(response, str) else str(response))
        except Exception as exc:
            logger.warning("LLM Judge 호출 실패, fallback 사용: %s", exc)
            return self._fallback_evaluate(start, text)

        # DimensionScore 변환
        dimensions: list[DimensionScore] = []
        for dim_data in result_data.get("dimensions", []):
            dim_name = dim_data.get("name", "")
            if dim_name in self._weights:
                weight, label = self._weights[dim_name]
                dimensions.append(
                    DimensionScore(
                        name=dim_name,
                        label=label,
                        score=float(dim_data.get("score", 3)),
                        weight=weight,
                        feedback=dim_data.get("feedback", ""),
                    )
                )

        critical_flags = result_data.get("critical_flags", [])
        suggestions = [result_data.get("overall_feedback", "")]
        issues = [d.feedback for d in dimensions if d.score < 3 and d.feedback]

        return self._timed_result(
            start,
            dimensions,
            issues,
            suggestions,
            critical_flags,
            cost_usd=cost,
        )

    def _extract_text(self, artifact_path: str) -> str:
        """PPTX, DOCX, 또는 XLSX에서 텍스트를 추출한다."""
        if artifact_path.endswith(".pptx"):
            return self._extract_pptx_text(artifact_path)
        elif artifact_path.endswith(".docx"):
            return self._extract_docx_text(artifact_path)
        elif artifact_path.endswith(".xlsx"):
            return self._extract_xlsx_text(artifact_path)
        return ""

    def _extract_pptx_text(self, path: str) -> str:
        try:
            from pptx import Presentation

            prs = Presentation(path)
            texts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        texts.append(shape.text_frame.text)
                    if shape.has_table:
                        for row in shape.table.rows:
                            texts.append(" | ".join(cell.text for cell in row.cells))
            return "\n".join(texts)
        except Exception:
            return ""

    def _extract_docx_text(self, path: str) -> str:
        try:
            from docx import Document

            doc = Document(path)
            texts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    texts.append(" | ".join(cell.text for cell in row.cells))
            return "\n".join(texts)
        except Exception:
            return ""

    def _extract_xlsx_text(self, path: str) -> str:
        """Excel 워크북에서 셀 텍스트를 추출한다."""
        try:
            from openpyxl import load_workbook

            wb = load_workbook(path, data_only=True)
            texts: list[str] = []
            for ws in wb.worksheets:
                texts.append(f"=== {ws.title} ===")
                max_row = min(ws.max_row or 1, 100)
                for row in ws.iter_rows(min_row=1, max_row=max_row, values_only=False):
                    row_texts = []
                    for cell in row:
                        if cell.value is not None:
                            row_texts.append(str(cell.value))
                    if row_texts:
                        texts.append(" | ".join(row_texts))
            wb.close()
            return "\n".join(texts)
        except Exception:
            return ""

    def _build_prompt(self, text: str, prd: dict) -> str:
        # 텍스트가 너무 길면 잘라냄 (토큰 예산)
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n... (이하 생략)"

        if self._doc_type == "ldd":
            return LDD_JUDGE_PROMPT.format(section_text=text)
        elif self._doc_type == "excel":
            return EXCEL_JUDGE_PROMPT.format(section_text=text)
        else:
            memo_type = prd.get("memo_type", "IM")
            return PPTX_JUDGE_PROMPT.format(memo_type=memo_type, section_text=text)

    def _parse_response(self, response: str) -> dict:
        """LLM 응답에서 JSON을 파싱한다."""
        # JSON 블록 추출
        json_match = response
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            json_match = response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            json_match = response[start:end].strip()

        try:
            return json.loads(json_match)
        except json.JSONDecodeError:
            return {"dimensions": [], "critical_flags": [], "overall_feedback": response[:200]}

    def _fallback_evaluate(self, start: int, text: str) -> GateResult:
        """LLM 없을 때 규칙 기반 평가 (개발/테스트용)."""
        dimensions = []
        for dim_name, (weight, label) in self._weights.items():
            # 간단한 휴리스틱
            score = 3.0
            if dim_name == "completeness":
                score = min(5.0, 2.0 + len(text) / 2000)
            elif dim_name == "accuracy":
                score = 3.5  # 기본
            dimensions.append(DimensionScore(dim_name, label, score, weight))

        return self._timed_result(
            start,
            dimensions,
            ["LLM 미연결 — 규칙 기반 fallback 평가"],
            [],
            [],
        )
