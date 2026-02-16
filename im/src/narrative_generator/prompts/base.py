"""BasePrompt 추상 클래스 + PromptRegistry (T-N07).

> 마지막 수정: 2026-02-10 11:52:29

모든 섹션 프롬프트의 기반 클래스와, section_id로 프롬프트를 조회하는 레지스트리.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.exceptions import PromptNotFoundError
from src.narrative_generator.korean_finance.tone_adapter import (
    FACTUAL_OPTIMISM,
    ToneAdapter,
)
from src.narrative_generator.rag.retriever import RetrievedContext

# ---------------------------------------------------------------------------
# 공통 시스템 프롬프트 요소
# ---------------------------------------------------------------------------

COMMON_SYSTEM_PREAMBLE = (
    "## 역할\n"
    "당신은 Investment Banking 전문가로, M&A 및 투자유치를 위한 "
    "Information Memorandum(IM) 문서를 작성하는 전문 작성자입니다.\n\n"
    "## 핵심 규칙\n"
    "1. 모든 수치는 반드시 제공된 재무 데이터에서만 인용하십시오. "
    "데이터에 없는 수치를 추측하거나 생성하지 마십시오.\n"
    "2. 금액은 '억원' 단위로 표기하되, 원본 데이터의 정확한 값을 사용하십시오.\n"
    "3. 비율(%, 배수)은 소수점 첫째자리까지 표기하십시오.\n"
    "4. 한국어로 작성하되, 금융 전문 용어는 영문 약어를 병기하십시오 "
    "(예: EBITDA, ROE, CAGR).\n"
    "5. Plain text로만 작성하십시오 (HTML, Markdown 금지).\n"
    "6. 3~5개 문단으로 구성하십시오.\n"
)


# ---------------------------------------------------------------------------
# BasePrompt
# ---------------------------------------------------------------------------


class BasePrompt(ABC):
    """섹션별 프롬프트 추상 기반 클래스.

    각 섹션 프롬프트는 이 클래스를 상속하여 구현한다.

    Attributes:
        section_id: IM 섹션 식별자 (예: "executive_summary").
    """

    section_id: str = ""

    def __init__(self) -> None:
        self._tone_adapter = ToneAdapter(FACTUAL_OPTIMISM)

    def build_system_prompt(self, *, industry_context: str = "") -> str:
        """시스템 프롬프트를 조립한다.

        Args:
            industry_context: 산업별 추가 컨텍스트 문자열.

        Returns:
            완성된 시스템 프롬프트 문자열.
        """
        parts = [
            COMMON_SYSTEM_PREAMBLE,
            self._tone_adapter.get_system_instruction(),
            self._get_section_instruction(),
        ]
        if industry_context:
            parts.append(f"\n## 산업 컨텍스트\n{industry_context}\n")
        return "\n".join(parts)

    def build_user_prompt(
        self,
        data: IMDocumentData,
        context: list[RetrievedContext] | None = None,
    ) -> str:
        """유저 프롬프트를 조립한다.

        Args:
            data: IM 문서 통합 데이터.
            context: RAG로 검색된 관련 컨텍스트 리스트.

        Returns:
            완성된 유저 프롬프트 문자열.
        """
        parts: list[str] = []

        # 1. 기업 기본 정보
        parts.append(f"## 기업 정보\n- 기업명: {data.company_name_kr}")
        if data.company_name_en:
            parts.append(f"- 영문명: {data.company_name_en}")

        # 2. 섹션별 데이터
        section_data = self.extract_data(data)
        if section_data:
            parts.append("\n## 섹션 데이터")
            for key, value in section_data.items():
                parts.append(f"- {key}: {_format_value(value)}")

        # 3. RAG 컨텍스트
        if context:
            parts.append("\n## 참고 컨텍스트")
            for i, ctx in enumerate(context, 1):
                source_info = f" (출처: {ctx.source})" if ctx.source else ""
                parts.append(f"[{i}] {ctx.text}{source_info}")

        # 4. 작성 지시
        parts.append(f"\n## 작성 지시\n{self._get_writing_instruction()}")

        return "\n".join(parts)

    @abstractmethod
    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        """해당 섹션에 필요한 데이터를 IMDocumentData에서 추출한다.

        Args:
            data: IM 문서 통합 데이터.

        Returns:
            {항목명: 값} 딕셔너리.
        """

    @abstractmethod
    def _get_section_instruction(self) -> str:
        """섹션별 시스템 프롬프트 보조 지시문을 반환한다."""

    @abstractmethod
    def _get_writing_instruction(self) -> str:
        """유저 프롬프트 내 작성 지시문을 반환한다."""

    def get_token_budget(self) -> int:
        """해당 섹션의 출력 토큰 예산을 반환한다.

        서브클래스에서 오버라이드하여 섹션별 예산을 설정한다.
        기본값: 600 토큰.
        """
        return 600


# ---------------------------------------------------------------------------
# PromptRegistry
# ---------------------------------------------------------------------------


class PromptRegistry:
    """섹션 프롬프트 레지스트리.

    section_id → BasePrompt 인스턴스 매핑을 관리한다.

    Examples:
        >>> registry = PromptRegistry()
        >>> registry.register(ExecutiveSummaryPrompt())
        >>> prompt = registry.get("executive_summary")
    """

    def __init__(self) -> None:
        self._prompts: dict[str, BasePrompt] = {}

    def register(self, prompt: BasePrompt) -> None:
        """프롬프트를 레지스트리에 등록한다.

        Args:
            prompt: BasePrompt 서브클래스 인스턴스.
        """
        self._prompts[prompt.section_id] = prompt

    def get(self, section_id: str) -> BasePrompt:
        """section_id로 프롬프트를 조회한다.

        Args:
            section_id: 섹션 식별자.

        Returns:
            해당 섹션의 BasePrompt 인스턴스.

        Raises:
            PromptNotFoundError: 등록되지 않은 section_id.
        """
        prompt = self._prompts.get(section_id)
        if prompt is None:
            raise PromptNotFoundError(section_id)
        return prompt

    def get_all(self) -> dict[str, BasePrompt]:
        """등록된 모든 프롬프트를 반환한다."""
        return dict(self._prompts)

    def has(self, section_id: str) -> bool:
        """해당 section_id가 등록되어 있는지 확인한다."""
        return section_id in self._prompts

    @property
    def section_ids(self) -> list[str]:
        """등록된 모든 section_id 목록."""
        return list(self._prompts.keys())


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------


def _format_value(value: Any) -> str:
    """값을 프롬프트용 문자열로 포맷한다."""
    if isinstance(value, dict):
        items = [f"{k}: {v}" for k, v in value.items()]
        return ", ".join(items)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, float):
        if abs(value) < 1:
            return f"{value:.1%}"
        return f"{value:,.1f}"
    return str(value)


def _format_financial_dict(d: dict[str, float], unit: str = "억원") -> str:
    """재무 데이터 딕셔너리를 프롬프트용 문자열로 포맷한다.

    Args:
        d: {연도: 금액} 딕셔너리.
        unit: 금액 단위.

    Returns:
        "2022년: 1,500억원, 2023년: 1,800억원" 형식.
    """
    if not d:
        return "데이터 없음"
    parts = []
    for year in sorted(d.keys()):
        val = d[year]
        # 원 단위를 억원으로 변환
        if unit == "억원" and abs(val) >= 1e8:
            display = f"{val / 1e8:,.1f}{unit}"
        elif unit == "억원" and abs(val) >= 1e6:
            display = f"{val / 1e6:,.1f}백만원"
        else:
            display = f"{val:,.0f}원"
        parts.append(f"{year}년: {display}")
    return ", ".join(parts)


def _format_metrics_dict(d: dict[str, float]) -> str:
    """파생 지표 딕셔너리를 프롬프트용 문자열로 포맷한다."""
    if not d:
        return "데이터 없음"
    parts = []
    for key, val in d.items():
        if "margin" in key or "yoy" in key or "cagr" in key:
            parts.append(f"{key}: {val:.1%}")
        elif "ratio" in key or "to_equity" in key:
            parts.append(f"{key}: {val:.1%}")
        else:
            parts.append(f"{key}: {val:,.1f}")
    return ", ".join(parts)
