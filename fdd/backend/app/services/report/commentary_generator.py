"""FDD 분석 시트별 LLM 코멘터리 생성 오케스트레이터.

각 분석 섹션의 엔진 결과를 받아서 LLM 라우터를 통해 코멘터리를 생성한다.
순수 함수 엔진 결과 → 프롬프트 구성 → LLM 생성 → Guardrail 검증.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CommentaryItem:
    """생성된 코멘터리 항목."""

    section_id: str               # e.g. "revenue_insight", "fcf_bridge_narrative"
    title_ko: str
    title_en: str
    content: str                  # 생성된 텍스트
    provider: str = ""            # 사용된 LLM 프로바이더
    is_fallback: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class CommentaryResult:
    """전체 코멘터리 생성 결과."""

    commentaries: list[CommentaryItem]
    total_generated: int
    total_failed: int
    warnings: list[str] = field(default_factory=list)


# ── 섹션별 프롬프트 템플릿 ────────────────────────────────

_COMMENTARY_TEMPLATES: dict[str, dict[str, str]] = {
    "revenue_insight": {
        "title_ko": "매출 분석 코멘터리",
        "title_en": "Revenue Analysis Commentary",
        "system": (
            "You are a Big 4 FDD analyst. Generate a concise commentary on the revenue analysis results. "
            "Focus on key trends, concentration risks, and notable changes. "
            "Use formal, professional Korean language. Keep it under 200 words."
        ),
        "user_template": (
            "매출 분석 결과:\n"
            "- 총 매출: {total_revenue}\n"
            "- Top 5 거래처 비중: {top_n_share}%\n"
            "- HHI 집중도: {hhi}\n"
            "- 주요 경고: {warnings}\n\n"
            "위 데이터를 기반으로 FDD 코멘터리를 작성해주세요."
        ),
    },
    "revenue_concentration_narrative": {
        "title_ko": "매출 집중도 리스크 서술",
        "title_en": "Revenue Concentration Risk Narrative",
        "system": (
            "You are a Big 4 FDD analyst specializing in risk assessment. "
            "Analyze the revenue concentration data and identify key risks. "
            "Output in Korean. Keep under 150 words."
        ),
        "user_template": (
            "매출 집중도 데이터:\n"
            "- HHI: {hhi}\n"
            "- Top 5 비중: {top_n_share}%\n"
            "- 고객 수: {customer_count}\n"
            "- 최대 거래처 비중: {max_share}%\n\n"
            "집중도 리스크를 분석해주세요."
        ),
    },
    "cost_structure_narrative": {
        "title_ko": "원가 구조 분석 코멘터리",
        "title_en": "Cost Structure Analysis Commentary",
        "system": (
            "You are a Big 4 FDD analyst. Analyze the cost structure and identify "
            "trends, anomalies, and areas of concern. Korean language. Under 200 words."
        ),
        "user_template": (
            "비용 구조:\n{cost_summary}\n\n"
            "경고 사항: {warnings}\n\n"
            "원가 구조 분석 코멘터리를 작성해주세요."
        ),
    },
    "fcf_bridge_narrative": {
        "title_ko": "FCF Bridge 코멘터리",
        "title_en": "FCF Bridge Commentary",
        "system": (
            "You are a Big 4 FDD analyst. Analyze the FCF bridge results and comment on "
            "cash conversion efficiency, CAPEX intensity, and working capital management. "
            "Korean language. Under 200 words."
        ),
        "user_template": (
            "FCF Bridge:\n"
            "- EBITDA: {ebitda}\n"
            "- 영업CF: {ocf}\n"
            "- CAPEX: {capex}\n"
            "- FCF: {fcf}\n"
            "- FCF Conversion: {fcf_conversion}%\n"
            "- 유지보수 CAPEX: {maint_capex}\n"
            "- 성장 CAPEX: {growth_capex}\n\n"
            "FCF 분석 코멘터리를 작성해주세요."
        ),
    },
    "capex_analysis_narrative": {
        "title_ko": "CAPEX 분석 코멘터리",
        "title_en": "CAPEX Analysis Commentary",
        "system": (
            "You are a Big 4 FDD analyst specializing in CAPEX analysis. "
            "Assess the CAPEX strategy (maintenance vs growth), intensity, and sustainability. "
            "Korean language. Under 150 words."
        ),
        "user_template": (
            "CAPEX 분석:\n{capex_summary}\n\n"
            "코멘터리를 작성해주세요."
        ),
    },
    "backlog_analysis_narrative": {
        "title_ko": "수주잔액 분석 코멘터리",
        "title_en": "Order Backlog Analysis Commentary",
        "system": (
            "You are a Big 4 FDD analyst. Analyze the order backlog data and assess "
            "order intake trends, concentration, aging, and coverage. "
            "Korean language. Under 200 words."
        ),
        "user_template": (
            "수주잔액 분석:\n"
            "- 총 잔액: {total_backlog}\n"
            "- Book-to-Bill: {btb}\n"
            "- 커버리지: {coverage}개월\n"
            "- Top 5 비중: {top_n_share}%\n"
            "- 납기 초과: {overdue_pct}%\n\n"
            "수주잔액 분석 코멘터리를 작성해주세요."
        ),
    },
    "negative_margin_narrative": {
        "title_ko": "역마진 리스크 서술",
        "title_en": "Negative Margin Risk Narrative",
        "system": (
            "You are a Big 4 FDD risk analyst. Assess the negative margin orders "
            "and their implications for profitability and cash flow. "
            "Korean language. Under 150 words."
        ),
        "user_template": (
            "역마진 현황:\n"
            "- 역마진 건수: {count}\n"
            "- 역마진 총액: {total_amount}\n"
            "- 예상 손실: {total_loss}\n\n"
            "역마진 리스크를 분석해주세요."
        ),
    },
    "consolidation_narrative": {
        "title_ko": "연결 분석 코멘터리",
        "title_en": "Consolidation Analysis Commentary",
        "system": (
            "You are a Big 4 FDD analyst. Comment on the multi-entity consolidation "
            "including entity contributions, IC transactions, and FX impact. "
            "Korean language. Under 200 words."
        ),
        "user_template": (
            "연결 분석:\n{consolidation_summary}\n\n"
            "연결 분석 코멘터리를 작성해주세요."
        ),
    },
    "interview_structuring": {
        "title_ko": "인터뷰 분석 요약",
        "title_en": "Interview Analysis Summary",
        "system": (
            "You are a Big 4 FDD analyst. Summarize the key findings from management "
            "interviews, highlighting risks and themes. Korean language. Under 250 words."
        ),
        "user_template": (
            "인터뷰 데이터:\n"
            "- 총 {total_notes}건\n"
            "- 출처: {source_dist}\n"
            "- 리스크 플래그: {risk_count}건\n"
            "- 주요 토픽: {topics}\n\n"
            "인터뷰 분석 요약을 작성해주세요."
        ),
    },
    "qualitative_risk_extraction": {
        "title_ko": "정성적 리스크 추출",
        "title_en": "Qualitative Risk Extraction",
        "system": (
            "You are a Big 4 FDD risk specialist. Extract and prioritize key risks "
            "from interview themes and risk flags. Korean language. Under 200 words."
        ),
        "user_template": (
            "테마 분석:\n"
            "- 총 테마: {total_themes}\n"
            "- 상위 테마: {top_themes}\n"
            "- 리스크 테마: {risk_themes}\n\n"
            "정성적 리스크를 추출하고 우선순위를 매겨주세요."
        ),
    },
}


class FDDCommentaryGenerator:
    """FDD 분석 코멘터리 생성기.

    기존 FDDModelRouter를 활용하여 각 섹션별 코멘터리를 생성한다.
    """

    def __init__(
        self,
        router: Any,
        *,
        industry_context: str = "",
        templates: dict[str, dict[str, str]] | None = None,
    ):
        self._router = router
        self._industry_context = industry_context
        self._templates = templates or _COMMENTARY_TEMPLATES

    def generate_commentary(
        self,
        section_id: str,
        data: dict[str, Any],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> CommentaryItem | None:
        """단일 섹션 코멘터리를 생성한다."""
        template = self._templates.get(section_id)
        if not template:
            logger.warning("No template for section: %s", section_id)
            return None

        system_prompt = template["system"]
        if self._industry_context:
            system_prompt += f"\n\n산업 컨텍스트:\n{self._industry_context}"

        user_prompt = template["user_template"]
        try:
            user_prompt = user_prompt.format(**data)
        except KeyError as e:
            logger.warning("Missing data key for %s: %s", section_id, e)
            return None

        try:
            response = self._router.generate(
                section_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Guardrail 검증
            warnings = []
            try:
                from app.agents.guardrails import validate_narrative_claims

                known_values = {k: str(v) for k, v in data.items() if v is not None}
                claim_warnings = validate_narrative_claims(response.text, known_values)
                warnings.extend(claim_warnings)
            except ImportError:
                pass

            return CommentaryItem(
                section_id=section_id,
                title_ko=template["title_ko"],
                title_en=template["title_en"],
                content=response.text,
                provider=response.provider,
                is_fallback=response.is_fallback,
                warnings=warnings,
            )

        except Exception as e:
            logger.warning("Commentary generation failed for %s: %s", section_id, e)
            return None

    def generate_all(
        self,
        section_data_map: dict[str, dict[str, Any]],
    ) -> CommentaryResult:
        """모든 섹션의 코멘터리를 한번에 생성한다.

        Args:
            section_data_map: {section_id: data_dict}

        Returns:
            CommentaryResult
        """
        commentaries: list[CommentaryItem] = []
        failed = 0
        warnings: list[str] = []

        for section_id, data in section_data_map.items():
            result = self.generate_commentary(section_id, data)
            if result:
                commentaries.append(result)
                warnings.extend(result.warnings)
            else:
                failed += 1
                warnings.append(f"COMMENTARY_FAILED: {section_id}")

        return CommentaryResult(
            commentaries=commentaries,
            total_generated=len(commentaries),
            total_failed=failed,
            warnings=warnings,
        )

    @staticmethod
    def available_sections() -> list[str]:
        """사용 가능한 코멘터리 섹션 ID 목록."""
        return list(_COMMENTARY_TEMPLATES.keys())
