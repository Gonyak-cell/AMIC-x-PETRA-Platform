"""LDD 6블록 서술(Narrative) 생성기.

항목별로 status/issue_level에 따라 1~6개 블록의 심층 서술을 순차 생성한다.
이전 블록의 결과가 다음 블록의 입력으로 전달되는 체인 구조.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from app.ralph.generators.ldd.narrative_prompts import (
    BLOCK_PROMPTS,
    BLOCK_TITLES,
    NARRATIVE_SYSTEM_PROMPT,
)
from app.ralph.generators.ldd.narrative_types import (
    NarrativeBlock,
    NarrativeBlockType,
    NarrativeResult,
    get_blocks_for_item,
)
from app.ralph.generators.ldd.prompts import format_source_materials
from app.ralph.parsers.base import ParsedFile

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """항목별 6블록 서술을 생성한다.

    LLM 호출은 외부에서 주입하는 ``llm_call`` 함수에 위임.
    체인 구조: FACTS → LEGAL_REVIEW → ANALYSIS → DEAL_IMPACT → PENALTY → RECOMMENDATION
    """

    def __init__(
        self,
        llm_call=None,
        learned_patterns: list[str] | None = None,
    ):
        self._llm_call = llm_call
        self._learned_patterns = learned_patterns or []

    async def generate_narrative(
        self,
        item: dict[str, Any],
        section_type: str,
        section_title: str,
        source_files: list[ParsedFile],
        legal_context: str = "",
    ) -> NarrativeResult:
        """단일 항목의 6블록 서술을 생성한다.

        Args:
            item: 체크리스트 항목 dict (status, issue_level, description 등 포함)
            section_type: 섹션 유형 (예: "GOVERNANCE")
            section_title: 섹션 제목 (예: "1. 기업 일반 및 지배구조")
            source_files: 관련 실사자료 목록
            legal_context: Phase 3에서 주입할 법률 인용 컨텍스트

        Returns:
            NarrativeResult
        """
        item_id = item.get("item_id", "")
        item_name = item.get("name", "")
        status = item.get("status", "PENDING")
        issue_level = item.get("issue_level")

        # 생성할 블록 결정
        block_types = get_blocks_for_item(status, issue_level)
        if not block_types:
            return NarrativeResult(
                item_id=item_id,
                item_name=item_name,
                section_type=section_type,
            )

        # 소스 자료 포매팅
        def _extract_filename(path: str) -> str:
            """Windows/Unix 경로 모두 지원하는 파일명 추출."""
            if "\\" in path:
                return PureWindowsPath(path).name
            return PurePosixPath(path).name

        materials = format_source_materials([
            {
                "name": _extract_filename(f.source_path),
                "text": f.text,
                "tables": [{"headers": t.headers, "rows": t.rows[:3]} for t in f.tables[:3]],
            }
            for f in source_files
            if f.is_valid
        ])

        # 체크리스트 분석 결과 텍스트
        checklist_analysis = self._format_checklist(item)

        # 블록 순차 생성 (체인)
        blocks: list[NarrativeBlock] = []
        block_contents: dict[str, str] = {}
        total_cost = 0.0

        for block_type in block_types:
            prompt = self._build_block_prompt(
                block_type=block_type,
                item_id=item_id,
                item_name=item_name,
                section_type=section_type,
                section_title=section_title,
                source_materials=materials,
                checklist_analysis=checklist_analysis,
                legal_context=legal_context,
                issue_level=issue_level or "",
                block_contents=block_contents,
            )

            try:
                content, block_cost = await self._call_llm(prompt)
            except Exception as exc:
                logger.warning(
                    "블록 생성 실패 [%s/%s/%s]: %s",
                    item_id, block_type.value, section_type, exc,
                )
                content = f"(생성 실패 — 수동 작성 필요: {block_type.value})"
                block_cost = 0.0

            total_cost += block_cost
            char_count = len(content)

            block = NarrativeBlock(
                block_type=block_type,
                title=BLOCK_TITLES.get(block_type.value, block_type.value),
                content=content,
                word_count=char_count,
            )
            blocks.append(block)
            block_contents[block_type.value] = content

        total_chars = sum(b.word_count for b in blocks)

        return NarrativeResult(
            item_id=item_id,
            item_name=item_name,
            section_type=section_type,
            blocks=blocks,
            total_chars=total_chars,
            cost_usd=total_cost,
        )

    async def generate_section_narratives(
        self,
        section: dict[str, Any],
        source_files: list[ParsedFile],
        legal_context: str = "",
    ) -> list[NarrativeResult]:
        """섹션 내 모든 항목의 서술을 생성한다."""
        results = []
        section_type = section.get("section_type", "")
        section_title = section.get("title", "")

        for item in section.get("items", []):
            try:
                result = await self.generate_narrative(
                    item=item,
                    section_type=section_type,
                    section_title=section_title,
                    source_files=source_files,
                    legal_context=legal_context,
                )
            except Exception as exc:
                item_id = item.get("item_id", "unknown")
                logger.warning(
                    "항목 서술 생성 실패 [%s/%s] — 빈 결과 반환: %s",
                    section_type, item_id, exc,
                )
                result = NarrativeResult(
                    item_id=item_id,
                    item_name=item.get("name", ""),
                    section_type=section_type,
                )
            results.append(result)

        return results

    def _build_block_prompt(
        self,
        block_type: NarrativeBlockType,
        item_id: str,
        item_name: str,
        section_type: str,
        section_title: str,
        source_materials: str,
        checklist_analysis: str,
        legal_context: str,
        issue_level: str,
        block_contents: dict[str, str],
    ) -> str:
        """블록 타입에 맞는 프롬프트를 구성한다."""
        template = BLOCK_PROMPTS.get(block_type.value, "")

        # 블록별 필요한 이전 결과 매핑
        format_args: dict[str, str] = {
            "item_id": item_id,
            "item_name": item_name,
            "section_type": section_type,
            "section_title": section_title,
            "source_materials": source_materials,
            "checklist_analysis": checklist_analysis,
            "legal_context": legal_context or "(법률 컨텍스트 미제공)",
            "issue_level": issue_level or "N/A",
            "facts_content": block_contents.get("FACTS", "(미생성)"),
            "legal_review_content": block_contents.get("LEGAL_REVIEW", "(미생성)"),
            "analysis_content": block_contents.get("ANALYSIS", "(미생성)"),
            "deal_impact_content": block_contents.get("DEAL_IMPACT", "(미생성)"),
        }

        return template.format(**format_args)

    def _format_checklist(self, item: dict) -> str:
        """체크리스트 분석 결과를 텍스트로 포매팅한다."""
        parts = []
        parts.append(f"상태: {item.get('status', 'PENDING')}")
        if item.get("issue_level"):
            parts.append(f"이슈 레벨: {item['issue_level']}")
        if item.get("description"):
            parts.append(f"발견사항: {item['description']}")
        if item.get("deal_impact"):
            parts.append(f"거래 영향: {item['deal_impact']}")
        if item.get("recommendation"):
            parts.append(f"권고: {item['recommendation']}")
        if item.get("evidence_refs"):
            parts.append(f"근거 자료: {', '.join(item['evidence_refs'])}")
        return "\n".join(parts) if parts else "(체크리스트 분석 결과 없음)"

    async def _call_llm(self, user_prompt: str) -> tuple[str, float]:
        """LLM 호출.

        Returns:
            (content, cost_usd) 튜플. cost_usd는 추정 비용.
        """
        if self._llm_call is None:
            logger.warning("LLM 호출 함수가 설정되지 않음 — 더미 서술 반환")
            return "(LLM 연결 필요 — 서술 자동 생성 미수행)", 0.0

        system = NARRATIVE_SYSTEM_PROMPT
        if self._learned_patterns:
            try:
                from app.ralph.learning.prompt_injector import LearningPromptInjector
                system = LearningPromptInjector().enrich_system_prompt(
                    system, self._learned_patterns,
                )
            except Exception as exc:
                logger.debug("학습 패턴 주입 실패: %s", exc)

        result = await self._llm_call(system, user_prompt)

        # llm_call이 (content, cost) 튜플 또는 단순 str을 반환할 수 있음
        if isinstance(result, tuple) and len(result) >= 2:
            content, cost = result[0], float(result[1])
        else:
            content = str(result)
            # 토큰 기반 비용 추정: 입력 ~2K토큰 + 출력 ~1K토큰 (Claude Sonnet 기준)
            estimated_tokens = len(user_prompt) / 4 + len(content) / 4
            cost = estimated_tokens * 0.000003  # $3/M tokens 추정

        return content, cost
