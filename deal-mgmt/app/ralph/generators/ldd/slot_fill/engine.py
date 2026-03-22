"""LDD template slot-fill 엔진."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.models.enums import LDDIssueLevel, LDDItemStatus, LDDReportType
from app.ralph.generators.ldd.project_green_style import (
    ProjectGreenToneContext,
    choose_project_green_modality,
    normalize_project_green_text,
)
from app.ralph.generators.ldd.slot_fill.prompt_builder import LDDSlotFillPromptBuilder
from app.ralph.generators.ldd.slot_fill.registry import TemplateRegistry
from app.ralph.generators.ldd.slot_fill.renderer import LDDTemplateRenderer
from app.ralph.generators.ldd.slot_fill.slot_parser import SlotResponseParser

logger = logging.getLogger(__name__)

_BLOCK_TITLES = {
    "FACTS": "검토 결과",
    "ANALYSIS": "법률 검토",
    "DEAL_IMPACT": "거래 영향",
    "RECOMMENDATION": "권고사항",
}
_BLOCK_MARKER = re.compile(r"^\[\[([A-Z_]+)\]\]\s*$", re.MULTILINE)

_STATUS_LABELS = {
    LDDItemStatus.OK: "이슈 없음",
    LDDItemStatus.ISSUE: "이슈 발견",
    LDDItemStatus.NA: "해당 없음",
    LDDItemStatus.PENDING: "추가 검토 필요",
}
_LEVEL_LABELS = {
    LDDIssueLevel.CRITICAL: "Critical",
    LDDIssueLevel.HIGH: "High",
    LDDIssueLevel.MEDIUM: "Medium",
    LDDIssueLevel.LOW: "Low",
}
_REPORT_TYPE_LABELS = {
    LDDReportType.FULL: "정식 Legal Due Diligence",
    LDDReportType.REDFLAG: "Redflag Due Diligence",
    LDDReportType.LAW_FIRM: "법무법인 스타일 Legal Due Diligence",
}
_SECTION_TEMPLATE_NAMES = {
    "GOVERNANCE": "governance",
    "CAPITAL": "capital",
    "CONTRACTS": "contracts",
    "LITIGATION": "litigation",
    "LABOR": "labor",
    "IP": "ip",
    "REAL_ESTATE": "real_estate",
    "PERMITS": "permits",
    "TAX": "tax",
    "DATA_IT": "data_it",
}


class LDDTemplateSlotFillEngine:
    """LDD sections를 고정 문안 기반 narrative blocks로 변환한다."""

    def __init__(
        self,
        template_dir: str | Path,
        *,
        llm_call=None,
        use_llm_slots: bool = False,
    ) -> None:
        self._registry = TemplateRegistry(template_dir)
        self._renderer = LDDTemplateRenderer()
        self._prompt_builder = LDDSlotFillPromptBuilder()
        self._slot_parser = SlotResponseParser()
        self._llm_call = llm_call
        self._use_llm_slots = use_llm_slots

    async def build_narrative_sections(
        self,
        report: Any,
        *,
        industry: str = "",
        raw_narrative_sections: dict[str, list[dict]] | None = None,
    ) -> dict[str, list[dict]]:
        """report.sections를 narrative_sections 형식으로 변환한다."""
        raw_lookup = self._index_raw_narratives(raw_narrative_sections or {})
        result: dict[str, list[dict]] = {}
        sections = getattr(report, "sections", None) or []

        for section in sections:
            section_type = section.get("section_type", "")
            template_name = _SECTION_TEMPLATE_NAMES.get(section_type)
            if not template_name:
                continue

            template = self._registry.get(template_name, industry=industry)
            if template is None:
                continue

            rendered_items: list[dict] = []
            for item in section.get("items", []):
                if not self._should_include_item(getattr(report, "report_type", None), item):
                    continue

                raw_narrative = raw_lookup.get((section_type, item.get("item_id", "")))
                data = self._build_item_data(report, section, item, raw_narrative)
                llm_slots = await self._resolve_llm_slots(template, data, industry=industry)
                rendered_text = self._renderer.render(
                    template=template,
                    data=data,
                    llm_slots=llm_slots,
                    industry=industry,
                    base_blocks=self._registry.base_blocks,
                )
                blocks = self._split_blocks(rendered_text)
                if not blocks:
                    continue

                rendered_items.append(
                    {
                        "item_id": item.get("item_id", ""),
                        "item_name": item.get("name", ""),
                        "status": item.get("status", LDDItemStatus.PENDING),
                        "issue_level": item.get("issue_level"),
                        "blocks": blocks,
                    }
                )

            if rendered_items and template.section_preamble:
                rendered_items = self._compact_section_preamble(rendered_items, template.section_preamble)

            if rendered_items:
                result[section_type] = rendered_items

        return result

    async def _resolve_llm_slots(self, template, data: dict[str, Any], *, industry: str) -> dict[str, str]:
        if not template.l3_slots or self._llm_call is None or not self._use_llm_slots:
            return {}

        system = self._prompt_builder.build_system_prompt(industry_context=industry)
        user = self._prompt_builder.build_user_prompt(template, data, industry_context=industry)
        raw = await self._llm_call(system, user)
        expected = list(template.l3_slots.keys())
        return self._slot_parser.parse(raw if isinstance(raw, str) else str(raw), expected)

    @staticmethod
    def _index_raw_narratives(raw_narrative_sections: dict[str, list[dict]]) -> dict[tuple[str, str], dict[str, str]]:
        indexed: dict[tuple[str, str], dict[str, str]] = {}
        for section_type, items in raw_narrative_sections.items():
            for item in items:
                item_id = item.get("item_id", "")
                block_map: dict[str, str] = {}
                for block in item.get("blocks", []):
                    block_type = block.get("block_type") or block.get("title") or ""
                    if block_type:
                        block_map[str(block_type)] = block.get("content", "")
                indexed[(section_type, item_id)] = block_map
        return indexed

    @staticmethod
    def _should_include_item(report_type: Any, item: dict[str, Any]) -> bool:
        if str(report_type) != str(LDDReportType.REDFLAG):
            return True

        status = item.get("status")
        level = item.get("issue_level")
        return status == LDDItemStatus.ISSUE and level in (
            LDDIssueLevel.CRITICAL,
            LDDIssueLevel.HIGH,
            LDDIssueLevel.MEDIUM,
        )

    def _build_item_data(
        self,
        report: Any,
        section: dict[str, Any],
        item: dict[str, Any],
        raw_narrative: dict[str, str] | None,
    ) -> dict[str, Any]:
        status = item.get("status", LDDItemStatus.PENDING)
        issue_level = item.get("issue_level")
        evidence_refs = [str(ref) for ref in item.get("evidence_refs", []) if ref]
        finding_summary = normalize_project_green_text(
            self._ensure_sentence(item.get("description") or self._default_finding(status, issue_level))
        )
        impact_summary = normalize_project_green_text(
            self._ensure_sentence(item.get("deal_impact") or self._default_impact(status, issue_level))
        )
        recommendation_summary = normalize_project_green_text(
            self._ensure_sentence(item.get("recommendation") or self._default_recommendation(status, issue_level))
        )
        target_company = getattr(report, "target_company", None) or "대상회사"
        confidence = item.get("confidence", 0.0) or 0.0
        modality = choose_project_green_modality(
            ProjectGreenToneContext(
                evidence_count=len(evidence_refs),
                confidence=float(confidence),
                status=str(status),
                issue_level=str(issue_level or ""),
                rfi_required=bool(item.get("rfi_required")),
                evidence_refs=tuple(evidence_refs),
            )
        )
        confidence_text = (
            f"AI 신뢰도는 약 {float(confidence) * 100:.0f}% 수준으로 평가되었습니다." if confidence else ""
        )

        finding_summary = normalize_project_green_text(finding_summary, modality=modality)
        impact_summary = normalize_project_green_text(impact_summary, modality=modality)
        confidence_text = normalize_project_green_text(confidence_text)

        evidence_sentence = normalize_project_green_text(
            self._ensure_sentence(
                f"관련 근거자료로는 {', '.join(evidence_refs[:5])}{' 등' if len(evidence_refs) > 5 else ''}이 확인되었습니다."
            )
            if evidence_refs
            else "제출자료 범위 내에서 근거자료의 식별은 제한적이었습니다."
        )
        rfi_sentence = normalize_project_green_text(
            self._ensure_sentence(
                f"추가 확인을 위해 RFI {item.get('rfi_number') or item.get('item_id', '')} 발행 또는 보강자료 요청을 권고합니다."
            )
            if item.get("rfi_required")
            else "현 단계에서 별도의 추가 자료 요청이 반드시 필요한 것으로 보이지는 않습니다."
        )

        return {
            "report": {
                "title": getattr(report, "title", ""),
                "target_company": target_company,
                "report_type": str(getattr(report, "report_type", "")),
                "report_type_label": _REPORT_TYPE_LABELS.get(
                    getattr(report, "report_type", None), str(getattr(report, "report_type", ""))
                ),
                "template_type": getattr(report, "template_type", "") or "",
                "deal_type": getattr(report, "deal_type", "") or "",
                "dd_period": getattr(report, "dd_period", "") or "",
                "law_firm": getattr(report, "law_firm", "") or "",
                "vdr_source": bool(getattr(report, "vdr_source", False)),
            },
            "section": {
                "section_type": section.get("section_type", ""),
                "title": section.get("title", ""),
                "display_name": self._strip_number_prefix(section.get("title", "")),
            },
            "item": {
                "item_id": item.get("item_id", ""),
                "name": item.get("name", ""),
                "status": status,
                "issue_level": issue_level or "",
                "risk_color": item.get("risk_color", ""),
                "confidence": confidence,
                "evidence_refs": evidence_refs,
                "rfi_required": bool(item.get("rfi_required")),
                "rfi_number": item.get("rfi_number", ""),
                "user_comment": item.get("user_comment", "") or "",
                "user_approved": item.get("user_approved"),
                "user_override_status": item.get("user_override_status") or "",
                "user_override_level": item.get("user_override_level") or "",
            },
            "derived": {
                "status_label": _STATUS_LABELS.get(status, str(status)),
                "issue_level_label": _LEVEL_LABELS.get(issue_level, "") if issue_level else "",
                "finding_summary": finding_summary,
                "impact_summary": impact_summary,
                "recommendation_summary": recommendation_summary,
                "status_sentence": normalize_project_green_text(
                    self._build_status_sentence(
                        target_company, item.get("name", ""), status, issue_level, finding_summary
                    ),
                    modality=modality,
                ),
                "analysis_sentence": normalize_project_green_text(
                    self._build_analysis_sentence(status, issue_level),
                    modality=modality,
                ),
                "impact_sentence": normalize_project_green_text(
                    self._build_impact_sentence(impact_summary),
                    modality=modality,
                ),
                "recommendation_sentence": normalize_project_green_text(
                    self._build_recommendation_sentence(recommendation_summary)
                ),
                "evidence_sentence": evidence_sentence,
                "rfi_sentence": rfi_sentence,
                "user_review_sentence": normalize_project_green_text(self._build_user_review_sentence(item)),
                "confidence_sentence": confidence_text,
                "supporting_documents": ", ".join(evidence_refs[:5]),
                "raw_facts": (raw_narrative or {}).get("FACTS", ""),
                "raw_analysis": (raw_narrative or {}).get("ANALYSIS", ""),
                "raw_recommendation": (raw_narrative or {}).get("RECOMMENDATION", ""),
            },
            "status": status,
            "issue_level": issue_level or "",
            "report_type": str(getattr(report, "report_type", "")),
            "has_evidence": bool(evidence_refs),
            "rfi_required": bool(item.get("rfi_required")),
            "has_user_comment": bool(item.get("user_comment")),
            "has_user_override": bool(item.get("user_override_status") or item.get("user_override_level")),
            "has_confidence": bool(confidence),
        }

    @staticmethod
    def _strip_number_prefix(title: str) -> str:
        return re.sub(r"^\d+\.\s*", "", title or "").strip()

    @staticmethod
    def _ensure_sentence(text: str) -> str:
        clean = " ".join((text or "").split())
        if not clean:
            return ""
        if clean[-1] not in ".!?":
            clean += "."
        return clean

    @staticmethod
    def _default_finding(status: Any, issue_level: Any) -> str:
        if status == LDDItemStatus.OK:
            return "제출자료 기준 본 항목과 관련하여 중대한 특이사항은 확인되지 않았습니다"
        if status == LDDItemStatus.NA:
            return "본 거래 구조 및 제출자료 기준 본 항목은 실질적으로 적용되지 않는 것으로 판단됩니다"
        if status == LDDItemStatus.ISSUE:
            level = _LEVEL_LABELS.get(issue_level, "주요")
            return f"제출자료 기준 본 항목과 관련하여 {level} 수준의 검토 필요 사항이 확인되었습니다"
        return "현재 제출자료만으로는 본 항목에 대한 최종 판단이 곤란합니다"

    @staticmethod
    def _default_impact(status: Any, issue_level: Any) -> str:
        if status == LDDItemStatus.OK:
            return "현 단계에서 본 항목이 거래 구조나 일정에 미치는 직접적인 제약은 제한적인 것으로 보입니다"
        if status == LDDItemStatus.NA:
            return "본 항목은 거래 실행 또는 종결 조건에 직접적인 영향을 미치지 않는 것으로 보입니다"
        if status == LDDItemStatus.ISSUE and issue_level == LDDIssueLevel.CRITICAL:
            return "거래 종결 조건, 가격 조정 또는 구조 재설계 논의가 필요할 수 있습니다"
        if status == LDDItemStatus.ISSUE:
            return "거래 조건 협상, 선행조치 설정 또는 진술보장 강화 논의가 필요할 수 있습니다"
        return "추가 자료 확인 전까지는 거래 영향도를 보수적으로 평가할 필요가 있습니다"

    @staticmethod
    def _default_recommendation(status: Any, issue_level: Any) -> str:
        if status == LDDItemStatus.OK:
            return "현 단계에서는 일반적인 진술보장 및 후속 모니터링 수준으로 관리하는 방안을 고려할 수 있습니다"
        if status == LDDItemStatus.NA:
            return "별도의 계약 반영 없이 본 항목을 참고 사항 수준으로 정리하는 방안을 고려할 수 있습니다"
        if status == LDDItemStatus.ISSUE and issue_level == LDDIssueLevel.CRITICAL:
            return "종결 전 선행조건 설정, 추가 실사 및 계약상 보호장치 강화를 우선 검토할 필요가 있습니다"
        if status == LDDItemStatus.ISSUE:
            return "추가 확인자료 확보 및 계약상 보호장치 반영 여부를 함께 검토할 필요가 있습니다"
        return "보강 자료를 추가 확보한 후 본 항목을 재평가하는 것이 바람직합니다"

    @staticmethod
    def _build_status_sentence(
        target_company: str,
        item_name: str,
        status: Any,
        issue_level: Any,
        finding_summary: str,
    ) -> str:
        if status == LDDItemStatus.ISSUE:
            label = _LEVEL_LABELS.get(issue_level, "주요")
            return f"{target_company}의 {item_name} 관련 검토 결과, {label} 수준의 검토 포인트가 확인되었습니다. {finding_summary}"
        return finding_summary

    @staticmethod
    def _build_analysis_sentence(status: Any, issue_level: Any) -> str:
        if status == LDDItemStatus.OK:
            return "자료상 확인된 범위에서는 관련 법령 및 계약 구조와의 충돌 가능성이 현저하지 않은 것으로 보입니다."
        if status == LDDItemStatus.NA:
            return "거래 구조상 본 항목이 직접 적용되지 않으므로 후속 계약 반영 필요성은 제한적입니다."
        if status == LDDItemStatus.ISSUE and issue_level == LDDIssueLevel.CRITICAL:
            return "확인된 사항은 종결 선행조건 또는 핵심 계약조건과 연동하여 우선적으로 검토할 필요가 있습니다."
        if status == LDDItemStatus.ISSUE:
            return "확인된 사항은 사실관계 보강과 함께 계약 반영 범위를 정교화할 필요가 있습니다."
        return "자료의 공백 또는 확인 미완료 상태가 남아 있어 확정 판단은 유보하는 것이 타당합니다."

    @staticmethod
    def _build_impact_sentence(impact_summary: str) -> str:
        return impact_summary

    @staticmethod
    def _build_recommendation_sentence(recommendation_summary: str) -> str:
        return recommendation_summary

    @staticmethod
    def _build_user_review_sentence(item: dict[str, Any]) -> str:
        approved = item.get("user_approved")
        comment = (item.get("user_comment") or "").strip()
        override_status = item.get("user_override_status")
        override_level = item.get("user_override_level")
        if approved is None and not comment and not override_status and not override_level:
            return ""

        parts: list[str] = []
        if approved is True:
            parts.append("리뷰어 승인 의견이 반영되어 있습니다.")
        elif approved is False:
            parts.append("리뷰어 반려 또는 보완 의견이 반영되어 있습니다.")
        if override_status:
            parts.append(f"사용자 상태 조정안은 {override_status}입니다.")
        if override_level:
            parts.append(f"사용자 이슈등급 조정안은 {override_level}입니다.")
        if comment:
            parts.append(f"리뷰 코멘트: {comment}")
        return " ".join(parts)

    @staticmethod
    def _split_blocks(rendered_text: str) -> list[dict]:
        positions = list(_BLOCK_MARKER.finditer(rendered_text))
        blocks: list[dict] = []
        for idx, match in enumerate(positions):
            block_type = match.group(1)
            start = match.end()
            end = positions[idx + 1].start() if idx + 1 < len(positions) else len(rendered_text)
            content = rendered_text[start:end].strip()
            if not content:
                continue
            blocks.append(
                {
                    "block_type": block_type,
                    "title": _BLOCK_TITLES.get(block_type, block_type),
                    "content": content,
                    "word_count": len(content),
                }
            )
        return blocks

    @classmethod
    def _compact_section_preamble(
        cls,
        rendered_items: list[dict[str, Any]],
        section_preamble: dict[str, int],
    ) -> list[dict[str, Any]]:
        if len(rendered_items) <= 1:
            return rendered_items

        compacted = [rendered_items[0]]
        for item in rendered_items[1:]:
            next_item = dict(item)
            next_blocks: list[dict[str, Any]] = []
            for block in item.get("blocks", []):
                next_block = dict(block)
                trim_count = section_preamble.get(str(block.get("block_type", "")), 0)
                if trim_count > 0:
                    trimmed = cls._trim_leading_sentences(str(block.get("content", "")), trim_count)
                    if trimmed:
                        next_block["content"] = trimmed
                        next_block["word_count"] = len(trimmed)
                    else:
                        continue
                next_blocks.append(next_block)
            next_item["blocks"] = next_blocks
            compacted.append(next_item)
        return compacted

    @staticmethod
    def _trim_leading_sentences(text: str, sentence_count: int) -> str:
        clean = (text or "").strip()
        if not clean or sentence_count <= 0:
            return clean

        remaining = clean
        trimmed_any = False
        for _ in range(sentence_count):
            match = re.search(r"[.!?](?:\s+|$)", remaining)
            if not match:
                break
            remaining = remaining[match.end() :].lstrip()
            trimmed_any = True

        if not trimmed_any:
            return clean
        return remaining
