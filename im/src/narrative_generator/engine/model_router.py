"""LLM 모델 라우터 (섹션 → 프로바이더 매핑).

> 마지막 수정: 2026-02-11 21:38:33

각 IM 섹션을 최적의 LLM 프로바이더에 라우팅한다.
환경변수 또는 설정으로 매핑을 커스터마이즈할 수 있다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.narrative_generator.engine.llm_provider import (
    LLMProvider,
    LLMResponse,
    ProviderName,
)
from src.narrative_generator.exceptions import LLMAPIError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 기본 라우팅 맵
# ---------------------------------------------------------------------------

DEFAULT_ROUTING: dict[str, ProviderName] = {
    # --- 정량/수치 중심 (OpenAI GPT-4o: 수치 정확도 + 정형 출력) ---
    "financial_analysis": ProviderName.OPENAI,
    "transaction_structure": ProviderName.OPENAI,
    "shareholder_structure": ProviderName.OPENAI,
    # --- 전략/정성 서술 (Claude: 장문 일관성 + 뉘앙스) ---
    "executive_summary": ProviderName.ANTHROPIC,
    "investment_highlights": ProviderName.ANTHROPIC,
    "value_creation": ProviderName.ANTHROPIC,
    "growth_strategy": ProviderName.ANTHROPIC,
    # --- 사실 기반 개요/조사 (Gemini: 빠른 정보 합성 + 비용 효율) ---
    "company_overview": ProviderName.GOOGLE,
    "business_overview": ProviderName.GOOGLE,
    "deal_overview": ProviderName.GOOGLE,
    "market_overview": ProviderName.GOOGLE,
    # --- Supporting (Gemini: 비용 효율) ---
    "management_team": ProviderName.GOOGLE,
    "business_model": ProviderName.GOOGLE,
    "appendix": ProviderName.GOOGLE,
    "contact": ProviderName.GOOGLE,
}


# ---------------------------------------------------------------------------
# RoutingDecision
# ---------------------------------------------------------------------------


@dataclass
class RoutingDecision:
    """라우팅 결정 결과.

    Attributes:
        section_id: 섹션 식별자.
        provider: 선택된 프로바이더.
        was_fallback: 폴백이 적용되었는지 여부.
        original_provider: 원래 지정된 프로바이더 (폴백 시에만).
    """

    section_id: str
    provider: ProviderName
    was_fallback: bool = False
    original_provider: ProviderName | None = None


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------


class ModelRouter:
    """섹션별 LLM 프로바이더 라우터.

    Args:
        providers: {ProviderName: LLMProvider} 딕셔너리.
        routing_map: {section_id: ProviderName} 매핑. None이면 기본값 사용.
        fallback_order: 폴백 프로바이더 우선순위 리스트.
    """

    def __init__(
        self,
        providers: dict[ProviderName, Any],
        routing_map: dict[str, ProviderName] | None = None,
        fallback_order: list[ProviderName] | None = None,
    ) -> None:
        self._providers = providers
        self._routing_map = routing_map or dict(DEFAULT_ROUTING)
        self._fallback_order = fallback_order or [
            ProviderName.OPENAI,
            ProviderName.ANTHROPIC,
            ProviderName.GOOGLE,
        ]

    def resolve(self, section_id: str) -> RoutingDecision:
        """섹션에 대한 프로바이더를 결정한다 (폴백 포함).

        Args:
            section_id: 섹션 식별자.

        Returns:
            RoutingDecision.

        Raises:
            LLMAPIError: 사용 가능한 프로바이더가 없을 때.
        """
        # 1. 라우팅 맵에서 지정된 프로바이더 확인
        target = self._routing_map.get(section_id, ProviderName.OPENAI)
        provider = self._providers.get(target)

        if provider and provider.is_available:
            return RoutingDecision(
                section_id=section_id,
                provider=target,
            )

        # 2. 지정 프로바이더 불가 → 폴백
        logger.warning(
            "프로바이더 '%s' 사용 불가 (section='%s') — 폴백 시도",
            target.value,
            section_id,
        )
        for fallback in self._fallback_order:
            if fallback == target:
                continue
            fb_provider = self._providers.get(fallback)
            if fb_provider and fb_provider.is_available:
                logger.info(
                    "폴백 적용: section='%s', %s → %s",
                    section_id,
                    target.value,
                    fallback.value,
                )
                return RoutingDecision(
                    section_id=section_id,
                    provider=fallback,
                    was_fallback=True,
                    original_provider=target,
                )

        # 3. 모든 프로바이더 불가
        raise LLMAPIError(
            provider="all",
            original_error=f"사용 가능한 LLM 프로바이더 없음 (section='{section_id}')",
        )

    def generate(
        self,
        section_id: str,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """섹션에 적합한 프로바이더를 선택하여 텍스트를 생성한다.

        Args:
            section_id: 섹션 식별자.
            system_prompt: 시스템 프롬프트.
            user_prompt: 유저 프롬프트.
            temperature: 생성 온도.
            max_tokens: 최대 응답 토큰 수.

        Returns:
            LLMResponse.
        """
        decision = self.resolve(section_id)
        provider = self._providers[decision.provider]

        if decision.was_fallback:
            logger.info(
                "폴백 생성: section='%s', 원래=%s, 실제=%s",
                section_id,
                decision.original_provider.value if decision.original_provider else "?",
                decision.provider.value,
            )

        return provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @property
    def available_providers(self) -> list[ProviderName]:
        """사용 가능한 프로바이더 목록."""
        return [
            name
            for name, p in self._providers.items()
            if p.is_available
        ]

    @property
    def routing_summary(self) -> dict[str, str]:
        """현재 라우팅 맵 요약 (디버깅용)."""
        return {
            section: provider.value
            for section, provider in self._routing_map.items()
        }
