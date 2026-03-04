"""FDD Report IR 전용 Generator — Ralph Loop DocumentGenerator 프로토콜 구현.

Report IR의 10개 블록 타입 중 LLM refinement 대상:
- TextBlock (Executive Summary, QoE/NWC/Debt Commentary, Korea Overlay)
- ClaimBlock (서술문 + EvidenceRef)
- IssueBlock (이슈 로그 — 권고사항 개선)

패스스루 (데이터 기반, 개선 불필요):
- CoverBlock, KPIBlock, TableBlock, ChartBlock, ScopeBlock, MethodologyBlock, AppendixBlock
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.renderers.report_builder import BlockType

logger = logging.getLogger(__name__)

# LLM 호출 타입 alias
LLMCallFn = Callable[[str, str, float, int], Awaitable[str]]

# 리파인 대상 블록 타입
REFINABLE_TYPES = {BlockType.TEXT, BlockType.CLAIM, BlockType.ISSUE}

# 섹션 ID 접두사 → 분석 영역 매핑
_SECTION_CONTEXT = {
    "text_exec": "Executive Summary",
    "text_qoe": "Quality of Earnings Commentary",
    "text_nwc": "Net Working Capital Commentary",
    "text_debt": "Net Debt Commentary",
    "text_korea": "Korea Regulatory & Accounting Overlay",
    "text_benchmark": "Industry KPI Benchmarks",
    "claim_": "FDD Claim / Finding",
    "issue_": "Issue Log",
}

_SYSTEM_PROMPT = """You are a senior FDD (Financial Due Diligence) analyst at a Big 4 accounting firm.
Your task is to refine the quality of FDD report sections to investment-banking grade.

## Quality Standards
1. **Numerical Accuracy**: All numbers MUST match the engine results exactly
2. **Completeness**: Cover all required analysis items — no gaps
3. **Analytical Depth**: Provide root cause analysis, trends, and deal impact — not just lists
4. **Professionalism**: Use Big 4 FDD terminology, structured sentences, industry benchmarks
5. **Evidence Linking**: Every claim must reference its data source (EvidenceRef)
6. **Confidentiality**: Use project codenames, mask sensitive information

## Output Format
Return a JSON object with the refined block content. Preserve the original structure.
Only modify textual content (content, claim_text, bullet_points, recommendation, description).
Do NOT change data fields (evidence_refs, evidence_id, issue_id, category codes).
"""

_REFINEMENT_USER_PROMPT = """## Section to Refine
Section ID: {section_id}
Block Type: {block_type}
Context: {context}

## Original Content
```json
{original_content}
```

## Engine Data (Ground Truth)
```json
{engine_data}
```

{checklist_section}

{feedback_section}

## Task
Refine the original content to meet Big 4 FDD quality standards.
Return ONLY the refined JSON block (same structure as original)."""


def _get_section_context(section_id: str) -> str:
    """섹션 ID로 분석 영역을 추론한다."""
    for prefix, ctx in _SECTION_CONTEXT.items():
        if section_id.startswith(prefix):
            return ctx
    return "FDD Analysis Section"


class FDDReportGenerator:
    """FDD Report IR 전용 Generator.

    Report IR의 refinable 블록만 추출하여 LLM으로 개선한 뒤,
    원본 IR에 다시 병합한다.
    """

    def __init__(
        self,
        report_ir_dict: dict[str, Any],
        llm_call: LLMCallFn,
        checklist_corrections: list[dict[str, Any]] | None = None,
        learned_patterns: list[str] | None = None,
    ) -> None:
        """
        Args:
            report_ir_dict: report_ir_to_dict()로 직렬화된 Report IR
            llm_call: async (system, user, temperature, max_tokens) -> str
            checklist_corrections: Pass 2용 체크리스트 수정 사항
            learned_patterns: 과거 세션에서 학습한 패턴
        """
        self._ir_dict = report_ir_dict
        self._llm_call = llm_call
        self._checklist_corrections = checklist_corrections or []
        self._learned_patterns = learned_patterns or []

        # 시스템 프롬프트에 학습 패턴 주입
        self._system_prompt = _SYSTEM_PROMPT
        if self._learned_patterns:
            from app.ralph.learning.prompt_injector import LearningPromptInjector

            injector = LearningPromptInjector()
            self._system_prompt = injector.enrich_system_prompt(
                _SYSTEM_PROMPT,
                self._learned_patterns,
            )

    async def generate_outline(
        self,
        source_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Report IR에서 refinable 섹션을 추출한다.

        Returns:
            [{"id": "text_3", "index": 3, "block_type": "text", "title": "..."}, ...]
        """
        outline: list[dict[str, Any]] = []
        sections = self._ir_dict.get("sections", [])

        for idx, section in enumerate(sections):
            block_type = section.get("type", "")
            if block_type not in {bt.value for bt in REFINABLE_TYPES}:
                continue

            # Pass 2: 수정된 섹션만 대상
            if self._checklist_corrections:
                related = self._get_related_corrections(section)
                if not related:
                    continue

            section_id = self._make_section_id(block_type, idx, section)
            outline.append(
                {
                    "id": section_id,
                    "index": idx,
                    "block_type": block_type,
                    "title": section.get("title") or section.get("claim_text", "")[:60],
                }
            )

        logger.info(
            "FDD outline: %d refinable sections out of %d total",
            len(outline),
            len(sections),
        )
        return outline

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict[str, Any],
        source_data: dict[str, Any],
        feedback: list[str] | None = None,
    ) -> str:
        """섹션을 LLM으로 개선한다.

        Returns:
            Refined 블록의 JSON 문자열
        """
        idx = section_criteria.get("index", 0)
        original_block = self._ir_dict["sections"][idx]
        block_type = section_criteria.get("block_type", "text")
        context = _get_section_context(section_id)

        # 체크리스트 수정 컨텍스트
        checklist_section = ""
        if self._checklist_corrections:
            related = self._get_related_corrections(original_block)
            if related:
                checklist_section = "## Checklist Corrections to Apply\n```json\n"
                checklist_section += json.dumps(related, ensure_ascii=False, indent=2)
                checklist_section += "\n```\nYou MUST incorporate these corrections into the refined text."

        # 피드백 컨텍스트
        feedback_section = ""
        if feedback:
            feedback_section = "## Previous Feedback (fix these issues)\n"
            for fb in feedback:
                feedback_section += f"- {fb}\n"

        # 엔진 데이터 요약 (source_data에서 관련 부분 추출)
        engine_data = self._extract_engine_data(original_block, source_data)

        user_prompt = _REFINEMENT_USER_PROMPT.format(
            section_id=section_id,
            block_type=block_type,
            context=context,
            original_content=json.dumps(original_block, ensure_ascii=False, indent=2),
            engine_data=json.dumps(engine_data, ensure_ascii=False, indent=2),
            checklist_section=checklist_section,
            feedback_section=feedback_section,
        )

        # LLM 호출
        response_text = await self._llm_call(
            self._system_prompt,
            user_prompt,
            0.3,  # temperature
            2048,  # max_tokens
        )

        # JSON 파싱 (markdown code fence 제거)
        refined_json = self._parse_json_response(response_text)
        return refined_json

    async def assemble_document(
        self,
        section_artifacts: dict[str, str],
        output_path: str,
    ) -> str:
        """Refined 섹션을 원본 IR에 병합한다.

        Returns:
            Refined IR JSON 문자열
        """
        refined_ir = json.loads(json.dumps(self._ir_dict))  # deep copy

        for section_id, artifact_json in section_artifacts.items():
            # section_id에서 index 추출 (형식: "{type}_{index}" 또는 "{type}_{index}_{suffix}")
            parts = section_id.split("_")
            try:
                idx = int(parts[1]) if len(parts) >= 2 else -1
            except (ValueError, IndexError):
                continue

            if 0 <= idx < len(refined_ir["sections"]):
                try:
                    refined_block = json.loads(artifact_json)
                    # 원본 블록의 구조적 필드는 보존하고 텍스트 필드만 교체
                    original = refined_ir["sections"][idx]
                    merged = self._merge_block(original, refined_block)
                    refined_ir["sections"][idx] = merged
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Failed to merge section %s: %s", section_id, e)

        return json.dumps(refined_ir, ensure_ascii=False, indent=2)

    # ── Private Helpers ──────────────────────────────────────────────────

    def _make_section_id(self, block_type: str, idx: int, section: dict) -> str:
        """고유 섹션 ID를 생성한다."""
        suffix = ""
        if block_type == "text":
            title = section.get("title", "")
            if "exec" in title.lower() or "summary" in title.lower():
                suffix = "exec"
            elif "qoe" in title.lower() or "earning" in title.lower():
                suffix = "qoe"
            elif "nwc" in title.lower() or "working" in title.lower():
                suffix = "nwc"
            elif "debt" in title.lower():
                suffix = "debt"
            elif "korea" in title.lower() or "overlay" in title.lower():
                suffix = "korea"
            elif "benchmark" in title.lower() or "industry" in title.lower():
                suffix = "benchmark"
        return f"{block_type}_{idx}_{suffix}" if suffix else f"{block_type}_{idx}"

    def _get_related_corrections(self, block: dict) -> list[dict]:
        """블록과 관련된 체크리스트 수정 사항을 찾는다."""
        if not self._checklist_corrections:
            return []

        block_type = block.get("type", "")
        title = (block.get("title") or block.get("claim_text") or "").lower()
        category = (block.get("category") or "").lower()

        related = []
        for corr in self._checklist_corrections:
            corr_cat = corr.get("category", "").lower()
            # 카테고리 매칭
            if (
                (block_type == "text" and corr_cat in title)
                or (
                    block_type == "claim"
                    and (corr_cat == category or corr_cat in title)
                )
                or block_type == "issue"
            ):
                related.append(corr)

        return related

    def _extract_engine_data(self, block: dict, source_data: dict) -> dict:
        """블록과 관련된 엔진 데이터를 추출한다."""
        block_type = block.get("type", "")
        title = (block.get("title") or "").lower()

        # source_data에서 관련 분석 데이터 추출
        relevant = {}
        if "qoe" in title or "earning" in title:
            relevant = source_data.get("qoe", {})
        elif "nwc" in title or "working" in title:
            relevant = source_data.get("nwc", {})
        elif "debt" in title:
            relevant = source_data.get("debt", {})
        elif "summary" in title or "exec" in title:
            # Executive Summary에는 모든 요약 데이터
            for key in ("qoe", "nwc", "debt"):
                if key in source_data:
                    relevant[key] = source_data[key]
        elif block_type == "issue":
            relevant = {"issues": source_data.get("issues", [])}

        return relevant or source_data

    def _merge_block(self, original: dict, refined: dict) -> dict:
        """원본 블록에 refined 텍스트를 병합한다.

        구조적 필드 (type, evidence_refs, issue_id 등)는 원본 유지.
        텍스트 필드 (content, claim_text, bullet_points 등)는 refined 사용.
        """
        # 보존할 구조적 필드
        PRESERVE_FIELDS = {
            "type",
            "position",
            "size",
            "evidence_refs",
            "evidence_id",
            "source_type",
            "source_id",
            "verified",
            "issue_id",
            "chart_type",
            "data",
            "image_base64",
            "columns",
            "rows",
            "footer_rows",
            "kpis",
            "scope_items",
            "definitions",
            "steps",
            "items",
            "show_header",
            "zebra_stripe",
        }

        merged = dict(original)
        for key, value in refined.items():
            if key in PRESERVE_FIELDS:
                continue  # 구조적 필드 원본 유지
            merged[key] = value  # 텍스트 필드 교체

        return merged

    def _parse_json_response(self, response: str) -> str:
        """LLM 응답에서 JSON을 추출한다."""
        text = response.strip()

        # Markdown code fence 제거
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # JSON 유효성 확인
        try:
            json.loads(text)
        except json.JSONDecodeError:
            logger.warning("LLM response is not valid JSON, returning as-is")
        return text
