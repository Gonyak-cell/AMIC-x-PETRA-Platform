"""PPTX(TM/DM/IM) Ralph Loop 통합 생성기.

기존 memo_generator.py를 래핑하여 DocumentGenerator Protocol을 구현한다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RalphMemoGenerator:
    """Ralph Loop 오케스트레이터와 호환되는 PPTX 생성기.

    DocumentGenerator Protocol:
    - generate_outline() → 슬라이드 구조 (섹션 목록)
    - generate_section() → 섹션별 콘텐츠 JSON
    - assemble_document() → memo_generator로 최종 PPTX 생성
    """

    def __init__(
        self,
        memo_type: str = "TM",
        project_code: str = "PROJECT",
        llm_call=None,
    ):
        self.memo_type = memo_type
        self.project_code = project_code
        self._llm_call = llm_call

    async def generate_outline(self, source_data: dict | None = None) -> list[dict]:
        """메모 유형에 따른 슬라이드 구조를 반환한다."""
        structures = {
            "TM": [
                {"section_id": "cover", "title": "Cover"},
                {"section_id": "disclaimer", "title": "Disclaimer"},
                {"section_id": "executive_summary", "title": "Executive Summary"},
                {"section_id": "company_overview", "title": "Company Overview"},
                {"section_id": "industry_overview", "title": "Industry Overview"},
                {"section_id": "financial_highlights", "title": "Financial Highlights"},
                {"section_id": "investment_highlights", "title": "Investment Highlights"},
                {"section_id": "transaction_overview", "title": "Transaction Overview"},
            ],
            "DM": [
                {"section_id": "cover", "title": "Cover"},
                {"section_id": "disclaimer", "title": "Disclaimer"},
                {"section_id": "discussion_overview", "title": "Discussion Overview"},
                {"section_id": "key_topics", "title": "Key Discussion Topics"},
                {"section_id": "financial_analysis", "title": "Financial Analysis"},
                {"section_id": "next_steps", "title": "Next Steps"},
            ],
            "IM": [
                {"section_id": "cover", "title": "Cover"},
                {"section_id": "disclaimer", "title": "Disclaimer"},
                {"section_id": "executive_summary", "title": "Executive Summary"},
                {"section_id": "company_overview", "title": "Company Overview"},
                {"section_id": "products_services", "title": "Products & Services"},
                {"section_id": "market_analysis", "title": "Market Analysis"},
                {"section_id": "competitive_landscape", "title": "Competitive Landscape"},
                {"section_id": "management_team", "title": "Management Team"},
                {"section_id": "financial_overview", "title": "Financial Overview"},
                {"section_id": "financial_projections", "title": "Financial Projections"},
                {"section_id": "valuation", "title": "Valuation"},
                {"section_id": "transaction_structure", "title": "Transaction Structure"},
                {"section_id": "appendix", "title": "Appendix"},
            ],
        }
        return structures.get(self.memo_type, structures["TM"])

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict | None = None,
        source_data: dict | None = None,
        feedback: str | None = None,
    ) -> str:
        """섹션별 콘텐츠를 생성한다 (LLM 필요)."""
        if self._llm_call is None:
            # LLM 미연결 시 스켈레톤 반환
            return json.dumps({
                "section_id": section_id,
                "slides": [{
                    "layout": "MAIN",
                    "title": section_id.replace("_", " ").title(),
                    "body": [
                        {"type": "text", "content": f"[{section_id}] 콘텐츠 생성 대기 중 — LLM 연결 필요"},
                    ],
                }],
            })

        prompt = self._build_section_prompt(section_id, section_criteria, source_data, feedback)
        system = (
            f"당신은 IB(Investment Bank)급 {self.memo_type} 메모랜덤 작성 전문가입니다.\n"
            f"프로젝트: {self.project_code}\n"
            "슬라이드 콘텐츠를 JSON 형식으로 생성하세요."
        )
        raw = await self._llm_call(system, prompt)
        return self._extract_json(raw)

    async def assemble_document(
        self,
        section_artifacts: dict[str, str],
        output_path: str | None = None,
    ) -> str:
        """섹션 결과를 조합하여 PPTX를 생성한다."""
        # 전체 슬라이드 목록 조합
        all_slides: list[dict] = []
        for section_id, artifact_json in section_artifacts.items():
            try:
                data = json.loads(artifact_json)
                slides = data.get("slides", [])
                all_slides.extend(slides)
            except json.JSONDecodeError:
                logger.warning("섹션 %s 파싱 실패", section_id)

        # memo_generator 호출용 JSON 구성
        content = {
            "project_name": self.project_code,
            "memo_type": self._memo_type_label(),
            "date": self._current_date(),
            "disclaimer": self._default_disclaimer(),
            "slides": all_slides,
        }

        if not output_path:
            from app.pptx.memo_generator import TEMPLATES_DIR
            output_dir = Path(TEMPLATES_DIR).parent.parent / "generated" / "memorandum"
            output_dir.mkdir(parents=True, exist_ok=True)
            import uuid as _uuid
            output_path = str(output_dir / f"{self.memo_type}_{self.project_code}_{_uuid.uuid4().hex[:8]}.pptx")

        try:
            from app.pptx.memo_generator import generate_memo
            result = generate_memo(
                memo_type=self.memo_type,
                project_code=self.project_code,
                output_path=output_path,
                content=content,
            )
            return result.output_path
        except Exception as e:
            logger.error("PPTX 생성 실패: %s", e)
            # JSON으로라도 반환
            return json.dumps(content, ensure_ascii=False)

    def _build_section_prompt(
        self,
        section_id: str,
        criteria: dict | None,
        source_data: dict | None,
        feedback: str | None,
    ) -> str:
        parts = [f"## 섹션: {section_id}\n"]
        if criteria:
            parts.append(f"### 수용 기준\n{json.dumps(criteria, ensure_ascii=False, indent=2)}\n")
        if source_data:
            parts.append(f"### 소스 데이터\n{json.dumps(source_data, ensure_ascii=False)[:5000]}\n")
        if feedback:
            parts.append(f"### 이전 피드백\n{feedback}\n")

        parts.append(
            "### 출력 형식\n"
            "```json\n"
            '{"section_id": "...", "slides": [{"layout": "MAIN", "title": "...", '
            '"body": [{"type": "text", "content": "..."}]}]}\n'
            "```\n"
        )
        return "\n".join(parts)

    def _extract_json(self, raw: str) -> str:
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]
        try:
            json.loads(text.strip())
            return text.strip()
        except json.JSONDecodeError:
            return json.dumps({"section_id": "error", "slides": [], "error": "JSON 파싱 실패"})

    def _memo_type_label(self) -> str:
        labels = {"TM": "Teaser Memo", "DM": "Discussion Memo", "IM": "Information Memorandum"}
        return labels.get(self.memo_type, self.memo_type)

    def _current_date(self) -> str:
        from datetime import date
        d = date.today()
        return d.strftime("%B %Y")

    def _default_disclaimer(self) -> str:
        return (
            "본 자료는 정보 제공 목적으로만 작성되었으며, "
            "투자 권유 또는 법적 자문을 구성하지 않습니다. "
            "수신인의 사전 서면 동의 없이 제3자에게 배포하거나 복제할 수 없습니다."
        )
