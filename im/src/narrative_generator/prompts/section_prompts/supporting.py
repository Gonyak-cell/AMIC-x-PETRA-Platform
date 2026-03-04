"""Supporting 섹션 프롬프트 4개 (T-N11).

> 마지막 수정: 2026-02-10 11:52:29

Management Team, Business Model, Appendix, Contact.
"""

from __future__ import annotations

from typing import Any

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.prompts.base import BasePrompt, _format_financial_dict


class ManagementTeamPrompt(BasePrompt):
    """Management Team 섹션 프롬프트."""

    section_id = "management_team"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.management_team:
            team_info = []
            for member in data.management_team:
                info = f"{member.name} ({member.title})"
                if member.role:
                    info += f" - {member.role}"
                if member.career:
                    info += f" | 경력: {', '.join(member.career[:3])}"
                team_info.append(info)
            result["경영진"] = team_info

        if data.company_overview and data.company_overview.employee_count:
            result["임직원 수"] = f"{data.company_overview.employee_count:,}명"

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Management Team (경영진)\n"
            "핵심 경영진의 경력, 역량, 리더십을 소개합니다.\n"
            "투자자가 경영진의 역량과 트랙레코드를 신뢰할 수 있도록 합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Management Team 소개를 작성하십시오.\n"
            "1문단: 경영진 전반 소개 및 핵심 강점\n"
            "2문단: 주요 경영진 개별 소개 (경력, 역량 중심)\n"
            "3문단: 조직 역량 및 기업 문화\n"
        )

    def get_token_budget(self) -> int:
        return 500


class BusinessModelPrompt(BasePrompt):
    """Business Model 섹션 프롬프트."""

    section_id = "business_model"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.company_overview:
            co = data.company_overview
            if co.business_model:
                result["비즈니스 모델"] = co.business_model
            if co.key_products:
                result["주요 제품/서비스"] = co.key_products
            if co.value_chain:
                result["가치 사슬"] = co.value_chain

        if data.segment_revenue:
            segments = list(data.segment_revenue.segments.keys())
            result["사업 부문"] = segments

        fs = data.financial_statements
        result["매출 추이"] = _format_financial_dict(fs.revenue)
        result["매출총이익"] = _format_financial_dict(fs.gross_profit)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Business Model (비즈니스 모델)\n"
            "기업의 수익 창출 메커니즘, 가치 제안, 핵심 역량을 설명합니다.\n"
            "비즈니스 모델의 지속 가능성과 확장 가능성을 강조합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Business Model을 작성하십시오.\n"
            "1문단: 핵심 수익 모델 및 가치 제안\n"
            "2문단: 주요 제품/서비스 포트폴리오\n"
            "3문단: 비즈니스 모델의 확장성과 경쟁 모트(moat)\n"
        )

    def get_token_budget(self) -> int:
        return 500


class AppendixPrompt(BasePrompt):
    """Appendix 섹션 프롬프트."""

    section_id = "appendix"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}
        fs = data.financial_statements

        result["매출액"] = _format_financial_dict(fs.revenue)
        result["영업이익"] = _format_financial_dict(fs.operating_income)
        result["당기순이익"] = _format_financial_dict(fs.net_income)
        result["자산총계"] = _format_financial_dict(fs.total_assets)
        result["부채총계"] = _format_financial_dict(fs.total_liabilities)
        result["자본총계"] = _format_financial_dict(fs.total_equity)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Appendix (부록)\n"
            "본문에서 다루지 못한 상세 재무 데이터와 보충 설명을 제공합니다.\n"
            "간결한 요약 형태로 작성합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Appendix 요약을 작성하십시오.\n"
            "주요 재무 지표의 연도별 추이를 간결하게 서술하십시오.\n"
            "1-2문단으로 충분합니다.\n"
        )

    def get_token_budget(self) -> int:
        return 300


class ContactPrompt(BasePrompt):
    """Contact 섹션 프롬프트."""

    section_id = "contact"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.contacts:
            contacts_info = []
            for c in data.contacts:
                info = c.name
                if c.title:
                    info += f" ({c.title})"
                if c.company:
                    info += f" | {c.company}"
                contacts_info.append(info)
            result["담당자"] = contacts_info

        result["프로젝트명"] = data.project_name
        result["기업명"] = data.company_name_kr

        return result

    def _get_section_instruction(self) -> str:
        return "## 섹션: Contact (연락처)\n문의처 안내 및 마무리 인사를 작성합니다.\n"

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 간단한 마무리 문구를 작성하십시오.\n"
            "본 IM에 대한 문의처를 안내하는 1-2문장이면 충분합니다.\n"
        )

    def get_token_budget(self) -> int:
        return 200
