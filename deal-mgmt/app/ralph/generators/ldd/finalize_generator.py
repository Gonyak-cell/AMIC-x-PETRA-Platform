"""Ralph Loop #2용 LDD Finalize Generator.

사용자 체크리스트 리뷰 결과를 반영하여 최종 보고서를 생성한다.
승인된 항목은 스킵하고, 반려/수정된 항목만 재분석한다.
"""

from __future__ import annotations

import json
import logging

from app.ralph.generators.ldd.section_analyzer import LDDDocumentGenerator, LDDSectionAnalyzer

logger = logging.getLogger(__name__)


class LDDFinalizeGenerator(LDDDocumentGenerator):
    """Ralph Loop #2용 Generator.

    DocumentGenerator Protocol 구현:
    - generate_outline() → 재분석 필요 섹션만 반환
    - generate_section() → 승인 항목 스킵, 반려/수정 항목만 재분석
    - assemble_document() → 모든 섹션 조합 + Executive Summary 재생성
    """

    def __init__(
        self,
        analyzer: LDDSectionAnalyzer,
        sections_config: list[dict],
        user_feedback: dict[str, str],
        approved_items: set[str],
    ):
        super().__init__(analyzer, sections_config)
        self._user_feedback = user_feedback  # {item_id: feedback_str}
        self._approved_items = approved_items  # 승인된 item_id 집합
        self._existing_results: dict[str, dict] = {}  # {item_id: existing_item_dict}

        # 기존 분석 결과 캐시 (승인된 항목 재사용용)
        for sec in sections_config:
            for item in sec.get("items", []):
                item_id = item.get("item_id", "")
                self._existing_results[item_id] = item

    async def generate_outline(self, source_data: dict | None = None) -> list[dict]:
        """재분석 필요 섹션 목록을 반환한다.

        모든 항목이 승인된 섹션도 포함 — assemble에서 통합 필요.
        """
        outline = []
        for sec in self._sections_config:
            section_type = sec.get("section_type", sec.get("id", ""))
            items = sec.get("items", [])

            needs_reanalysis = any(item.get("item_id", "") not in self._approved_items for item in items)

            outline.append(
                {
                    "id": section_type,
                    "section_id": section_type,
                    "title": sec.get("title", ""),
                    "item_count": len(items),
                    "needs_reanalysis": needs_reanalysis,
                }
            )

        return outline

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict | None = None,
        source_data: dict | None = None,
        feedback: list[str] | str | None = None,
    ) -> str:
        """섹션 내 항목을 선택적으로 재분석한다.

        - 승인된 항목: 기존 분석 결과 그대로 반환 (LLM 호출 안 함)
        - 반려/미검토 항목: user_feedback를 반영하여 재분석
        """
        # 피드백 문자열 변환 (오케스트레이터는 list[str] 전달)
        if isinstance(feedback, list):
            feedback_str = "\n".join(feedback) if feedback else ""
        else:
            feedback_str = feedback or ""

        section_cfg = None
        for sec in self._sections_config:
            st = sec.get("section_type", sec.get("id", ""))
            if st == section_id:
                section_cfg = sec
                break

        if not section_cfg:
            return json.dumps({"error": f"섹션 '{section_id}'를 찾을 수 없습니다"})

        source_files = self._source_map.get(section_id, [])
        results: list[dict] = []

        for item in section_cfg.get("items", []):
            item_id = item.get("item_id", "")
            item_name = item.get("name", "")

            if item_id in self._approved_items:
                # 승인된 항목: 기존 결과 재사용 (비용 절감)
                existing = self._existing_results.get(item_id, item)
                result = {
                    "item_id": item_id,
                    "name": item_name,
                    "status": existing.get("status", "PENDING"),
                    "issue_level": existing.get("issue_level"),
                    "description": existing.get("description", ""),
                    "deal_impact": existing.get("deal_impact", ""),
                    "recommendation": existing.get("recommendation", ""),
                    "rfi_required": existing.get("rfi_required", False),
                    "rfi_number": existing.get("rfi_number", ""),
                    "confidence": existing.get("confidence", 0.0),
                    "evidence_refs": existing.get("evidence_refs", []),
                }

                # user_override가 있으면 적용
                if existing.get("user_override_status"):
                    result["status"] = existing["user_override_status"]
                if existing.get("user_override_level"):
                    result["issue_level"] = existing["user_override_level"]

                results.append(result)
                logger.debug("항목 %s: 승인 → 기존 결과 재사용", item_id)

            else:
                # 반려/미검토 항목: 재분석
                item_feedback = self._user_feedback.get(item_id, "")
                combined_feedback = feedback_str
                if item_feedback:
                    combined_feedback = f"{item_feedback}\n{combined_feedback}" if combined_feedback else item_feedback

                # 기존 분석이 있으면 refine, 없으면 새로 분석
                existing = self._existing_results.get(item_id)
                if existing and existing.get("description"):
                    result = await self._analyzer.refine_item(
                        previous_analysis=existing,
                        gate_feedback=combined_feedback,
                    )
                else:
                    result = await self._analyzer.analyze_item(
                        item_id=item_id,
                        item_name=item_name,
                        section_type=section_id,
                        section_title=section_cfg.get("title", ""),
                        source_files=source_files,
                        feedback=combined_feedback,
                    )

                result["item_id"] = item_id
                result["name"] = item_name
                results.append(result)
                logger.debug("항목 %s: 재분석 완료", item_id)

        return json.dumps(results, ensure_ascii=False)

    async def assemble_document(
        self,
        section_artifacts: dict[str, str],
        output_path: str | None = None,
    ) -> str:
        """모든 섹션을 조합하고 Executive Summary를 재생성한다."""
        all_sections: dict[str, list[dict]] = {}

        for section_id, artifact_json in section_artifacts.items():
            try:
                items = json.loads(artifact_json)
                all_sections[section_id] = items
            except json.JSONDecodeError:
                all_sections[section_id] = []

        # Executive Summary 재생성 (전체 결과 기반)
        exec_summary = await self._analyzer.generate_executive_summary(all_sections)

        # 교차 검증
        full_text = json.dumps(all_sections, ensure_ascii=False)
        cross_val = await self._analyzer.cross_validate(full_text)

        report_data = {
            "executive_summary": exec_summary,
            "sections": all_sections,
            "cross_validation": cross_val,
            "finalize_metadata": {
                "approved_count": len(self._approved_items),
                "reanalyzed_count": sum(
                    1
                    for sec_items in all_sections.values()
                    for item in sec_items
                    if item.get("item_id") not in self._approved_items
                ),
                "feedback_count": len(self._user_feedback),
            },
        }

        return json.dumps(report_data, ensure_ascii=False)
