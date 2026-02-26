"""LDD 섹션별 AI 분석기 — 52개 DDRL 항목 자동 분석."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.ralph.generators.ldd.json_utils import extract_json
from app.ralph.generators.ldd.prompts import (
    CROSS_VALIDATION_PROMPT,
    EXECUTIVE_SUMMARY_PROMPT,
    ITEM_ANALYSIS_PROMPT,
    REFINEMENT_PROMPT,
    SYSTEM_PROMPT,
    format_source_materials,
)
from app.ralph.parsers.base import ParsedFile

logger = logging.getLogger(__name__)

# RFI 접두어 매핑 (section_type → prefix)
_RFI_PREFIX: dict[str, str] = {
    "GOVERNANCE": "CORP",
    "CAPITAL": "CAP",
    "CONTRACTS": "CONTRACT",
    "LITIGATION": "LIT",
    "LABOR": "LABOR",
    "IP": "IP",
    "REAL_ESTATE": "RE",
    "PERMITS": "PERMIT",
    "TAX": "TAX",
    "DATA_IT": "IT",
}


class LDDSectionAnalyzer:
    """DDRL 항목별 AI 분석을 수행한다.

    LLM 호출은 외부에서 주입하는 `llm_call` 함수에 위임.
    """

    def __init__(self, llm_call=None, learned_patterns: list[str] | None = None):
        """
        Args:
            llm_call: async (system_prompt: str, user_prompt: str) -> str
                      LLM 호출 함수. None이면 더미 응답 반환.
            learned_patterns: 과거 세션에서 학습된 패턴 목록.
                              LearningPromptInjector로 시스템 프롬프트에 주입된다.
        """
        self._llm_call = llm_call
        self._learned_patterns = learned_patterns or []

    async def analyze_item(
        self,
        item_id: str,
        item_name: str,
        section_type: str,
        section_title: str,
        source_files: list[ParsedFile],
        feedback: str = "",
    ) -> dict[str, Any]:
        """단일 DDRL 항목을 분석한다."""
        # 소스 자료 포매팅
        materials = format_source_materials([
            {
                "name": f.source_path.split("\\")[-1] if "\\" in f.source_path else f.source_path.split("/")[-1],
                "text": f.text,
                "tables": [{"headers": t.headers, "rows": t.rows[:3]} for t in f.tables[:3]],
            }
            for f in source_files
            if f.is_valid
        ])

        rfi_prefix = _RFI_PREFIX.get(section_type, section_type[:4].upper())

        prompt = ITEM_ANALYSIS_PROMPT.format(
            item_id=item_id,
            item_name=item_name,
            section_type=section_type,
            section_title=section_title,
            source_materials=materials,
            feedback=feedback or "(초기 분석 — 이전 피드백 없음)",
            rfi_prefix=rfi_prefix,
        )

        raw = await self._call_llm(SYSTEM_PROMPT, prompt)
        return self._parse_json(raw, item_id)

    async def refine_item(
        self,
        previous_analysis: dict[str, Any],
        gate_feedback: str,
    ) -> dict[str, Any]:
        """품질 게이트 피드백을 반영하여 항목을 재분석한다."""
        prompt = REFINEMENT_PROMPT.format(
            previous_analysis=json.dumps(previous_analysis, ensure_ascii=False, indent=2),
            gate_feedback=gate_feedback,
        )

        raw = await self._call_llm(SYSTEM_PROMPT, prompt)
        return self._parse_json(raw, previous_analysis.get("item_id", "unknown"))

    async def generate_executive_summary(
        self,
        section_results: dict[str, list[dict]],
    ) -> str:
        """전체 분석 결과로 Executive Summary를 생성한다."""
        summaries: list[str] = []
        for section_type, items in section_results.items():
            issues = [i for i in items if i.get("status") == "ISSUE"]
            ok_count = sum(1 for i in items if i.get("status") == "OK")
            na_count = sum(1 for i in items if i.get("status") == "NA")
            pending_count = sum(1 for i in items if i.get("status") == "PENDING")

            summary = f"### {section_type}\n"
            summary += (
                f"- 총 {len(items)}개 항목: OK={ok_count}, ISSUE={len(issues)}"
                f", NA={na_count}, PENDING={pending_count}\n"
            )
            for issue in issues:
                level = issue.get("issue_level", "UNKNOWN")
                summary += f"  - [{level}] {issue.get('item_id', '')}: {issue.get('description', '')[:100]}\n"
            summaries.append(summary)

        prompt = EXECUTIVE_SUMMARY_PROMPT.format(
            section_summaries="\n".join(summaries),
        )

        return await self._call_llm(SYSTEM_PROMPT, prompt)

    async def cross_validate(self, full_report_text: str) -> dict[str, Any]:
        """보고서 전체에 대한 교차 검증을 수행한다."""
        prompt = CROSS_VALIDATION_PROMPT.format(
            full_report=full_report_text[:20000],
        )

        raw = await self._call_llm(SYSTEM_PROMPT, prompt)
        return self._parse_json(raw, "cross_validation")

    async def _call_llm(self, system: str, user: str) -> str:
        """LLM 호출을 수행한다. 학습 패턴이 있으면 시스템 프롬프트에 주입."""
        if self._llm_call is None:
            logger.warning("LLM 호출 함수가 설정되지 않음 — 더미 응답 반환")
            return json.dumps({
                "status": "PENDING",
                "issue_level": None,
                "risk_color": "",
                "description": "LLM 연결 필요 — 자동 분석 미수행",
                "deal_impact": "",
                "recommendation": "LLM API 키를 설정하여 자동 분석을 활성화하세요",
                "rfi_required": False,
                "rfi_number": "",
                "confidence": 0.0,
                "evidence_refs": [],
            })

        # 학습 패턴이 있으면 시스템 프롬프트에 주입
        enriched_system = system
        if self._learned_patterns:
            from app.ralph.learning.prompt_injector import LearningPromptInjector
            enriched_system = LearningPromptInjector().enrich_system_prompt(
                system, self._learned_patterns,
            )

        return await self._llm_call(enriched_system, user)

    def _parse_json(self, raw: str, context: str) -> dict[str, Any]:
        """LLM 응답에서 JSON을 추출한다."""
        return extract_json(
            raw,
            context=context,
            fallback={
                "status": "PENDING",
                "issue_level": None,
                "risk_color": "",
                "description": "분석 결과 파싱 실패",
                "deal_impact": "",
                "recommendation": "",
                "rfi_required": False,
                "rfi_number": "",
                "confidence": 0.0,
                "evidence_refs": [],
                "_raw_response": raw[:500],
            },
        )


class LDDDocumentGenerator:
    """Ralph Loop 오케스트레이터와 호환되는 LDD 문서 생성기.

    DocumentGenerator Protocol 구현:
    - generate_outline() → 10개 섹션 구조
    - generate_section() → 섹션별 항목 분석
    - assemble_document() → DOCX 렌더링
    """

    def __init__(self, analyzer: LDDSectionAnalyzer, sections_config: list[dict]):
        self._analyzer = analyzer
        self._sections_config = sections_config  # DEFAULT_LDD_SECTIONS
        self._source_map: dict[str, list[ParsedFile]] = {}  # section_type → parsed files

    def set_source_map(self, source_map: dict[str, list[ParsedFile]]):
        """섹션별 관련 실사자료를 설정한다."""
        self._source_map = source_map

    async def generate_outline(self, source_data: dict | None = None) -> list[dict]:
        """LDD 보고서 구조(10개 섹션)를 반환한다."""
        return [
            {
                "id": sec["section_type"],
                "section_id": sec["section_type"],
                "title": sec["title"],
                "item_count": len(sec["items"]),
            }
            for sec in self._sections_config
        ]

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict | None = None,
        source_data: dict | None = None,
        feedback: list[str] | str | None = None,
    ) -> str:
        """섹션 내 모든 항목을 분석하고 JSON 문자열로 반환한다."""
        # 피드백 문자열 변환 (오케스트레이터는 list[str] 전달)
        if isinstance(feedback, list):
            feedback_str = "\n".join(feedback) if feedback else ""
        else:
            feedback_str = feedback or ""

        # 해당 섹션 설정 찾기
        section_cfg = None
        for sec in self._sections_config:
            if sec["section_type"] == section_id:
                section_cfg = sec
                break

        if not section_cfg:
            return json.dumps({"error": f"섹션 '{section_id}'를 찾을 수 없습니다"})

        # 관련 실사자료
        source_files = self._source_map.get(section_id, [])

        # 항목별 분석
        results: list[dict] = []
        for item in section_cfg["items"]:
            result = await self._analyzer.analyze_item(
                item_id=item["item_id"],
                item_name=item["name"],
                section_type=section_id,
                section_title=section_cfg["title"],
                source_files=source_files,
                feedback=feedback_str,
            )
            result["item_id"] = item["item_id"]
            result["name"] = item["name"]
            results.append(result)

        return json.dumps(results, ensure_ascii=False)

    async def assemble_document(
        self,
        section_artifacts: dict[str, str],
        output_path: str | None = None,
    ) -> str:
        """분석 결과를 조합하여 LDD 보고서 데이터를 반환한다.

        실제 DOCX 렌더링은 ldd_report_service.py에 위임.
        """
        all_sections: dict[str, list[dict]] = {}
        for section_id, artifact_json in section_artifacts.items():
            try:
                items = json.loads(artifact_json)
                all_sections[section_id] = items
            except json.JSONDecodeError:
                all_sections[section_id] = []

        # Executive Summary 생성
        exec_summary = await self._analyzer.generate_executive_summary(all_sections)

        # 교차 검증
        full_text = json.dumps(all_sections, ensure_ascii=False)
        cross_val = await self._analyzer.cross_validate(full_text)

        report_data = {
            "executive_summary": exec_summary,
            "sections": all_sections,
            "cross_validation": cross_val,
        }

        return json.dumps(report_data, ensure_ascii=False)
