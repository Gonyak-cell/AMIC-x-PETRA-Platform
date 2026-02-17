"""FDD 멀티모델 LLM 라우터 — IM ModelRouter 패턴 적응.

섹션/태스크 ID에 따라 최적의 LLM 프로바이더를 선택하고,
프로바이더 미사용 시 폴백 체인으로 자동 대체.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.services.llm.client import LLMClient, LLMProvider, LLMResponse

logger = get_logger(__name__)


# ── FDD 라우팅 맵 ─────────────────────────────────────────
# 각 섹션/태스크별로 최적의 프로바이더를 지정한다.

DEFAULT_FDD_ROUTING: dict[str, str] = {
    # ── 정량 분석 (OpenAI — 수치 정확도, JSON 구조화) ──
    "qoe_adjustment_classification": "openai",
    "qoe_analysis_narrative": "openai",
    "nwc_analysis_narrative": "openai",
    "debt_analysis_narrative": "openai",
    "coa_mapping": "openai",
    # ── 전략/정성 (Anthropic — 장문 일관성, 뉘앙스) ──
    "executive_summary": "anthropic",
    "overall_assessment": "anthropic",
    "risk_narrative": "anthropic",
    "issue_commentary": "anthropic",
    # ── 지원/방법론 (Gemini — 비용 효율) ──
    "methodology_description": "gemini",
    "scope_description": "gemini",
    "benchmark_context": "gemini",
    "industry_context_narrative": "gemini",
}

# 폴백 체인: primary → secondary → tertiary
FALLBACK_CHAIN: dict[str, list[str]] = {
    "openai": ["anthropic", "gemini"],
    "anthropic": ["openai", "gemini"],
    "gemini": ["openai", "anthropic"],
}


@dataclass(frozen=True)
class RoutingDecision:
    """라우팅 결정 결과."""

    section_id: str
    provider: str
    is_fallback: bool = False
    original_provider: str | None = None


@dataclass
class FDDLLMResponse:
    """라우터 응답 — LLMResponse + 라우팅 메타데이터."""

    text: str
    provider: str
    model: str
    section_id: str
    is_fallback: bool = False
    original_provider: str | None = None
    token_usage: dict[str, int] = field(default_factory=dict)


class FDDModelRouter:
    """FDD 멀티모델 라우터.

    섹션 ID별로 최적의 프로바이더를 선택하고,
    사용 불가 시 폴백 체인을 순회한다.

    Args:
        providers: {provider_name: LLMClient} 맵
        routing_map: 섹션별 프로바이더 맵 (기본: DEFAULT_FDD_ROUTING)
        fallback_order: 커스텀 폴백 순서 (None이면 FALLBACK_CHAIN 사용)
    """

    def __init__(
        self,
        providers: dict[str, LLMClient],
        routing_map: dict[str, str] | None = None,
        fallback_order: list[str] | None = None,
    ):
        self._providers = providers
        self._routing_map = routing_map or DEFAULT_FDD_ROUTING
        self._fallback_order = fallback_order

    @property
    def available_providers(self) -> list[str]:
        """사용 가능한 프로바이더 목록."""
        return [name for name, client in self._providers.items() if client.is_available()]

    @property
    def routing_summary(self) -> dict[str, str]:
        """현재 라우팅 맵 (디버그용)."""
        return dict(self._routing_map)

    def resolve(self, section_id: str, *, industry: str = "") -> RoutingDecision:
        """섹션에 대한 프로바이더를 결정한다.

        Args:
            section_id: 섹션/태스크 식별자
            industry: 산업 식별자 (복합 키 라우팅용, 예: "healthcare")

        Returns:
            RoutingDecision (fallback 여부 포함)

        Raises:
            RuntimeError: 사용 가능한 프로바이더가 전혀 없을 때
        """
        # 1차: 복합 키 (industry:section_id) 조회
        if industry:
            compound_key = f"{industry}:{section_id}"
            compound_primary = self._routing_map.get(compound_key)
            if compound_primary:
                client = self._providers.get(compound_primary)
                if client and client.is_available():
                    return RoutingDecision(
                        section_id=section_id,
                        provider=compound_primary,
                    )

        # 2차: 기본 키 (section_id) 조회
        primary = self._routing_map.get(section_id, "openai")

        # 1차: primary 프로바이더 사용 가능한지 확인
        primary_client = self._providers.get(primary)
        if primary_client and primary_client.is_available():
            return RoutingDecision(
                section_id=section_id,
                provider=primary,
            )

        # 2차: 폴백 체인 순회 (커스텀 폴백 → 기본 폴백 체인)
        if self._fallback_order:
            fallbacks = [f for f in self._fallback_order if f != primary]
        else:
            fallbacks = FALLBACK_CHAIN.get(primary, [])
        for fallback_name in fallbacks:
            fallback_client = self._providers.get(fallback_name)
            if fallback_client and fallback_client.is_available():
                logger.info(
                    "Router fallback",
                    extra={
                        "ctx": {
                            "section_id": section_id,
                            "original": primary,
                            "fallback": fallback_name,
                        }
                    },
                )
                return RoutingDecision(
                    section_id=section_id,
                    provider=fallback_name,
                    is_fallback=True,
                    original_provider=primary,
                )

        raise RuntimeError(
            f"라우터: '{section_id}'에 사용 가능한 프로바이더가 없습니다. "
            f"등록된 프로바이더: {list(self._providers.keys())}"
        )

    def generate(
        self,
        section_id: str,
        *,
        industry: str = "",
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_schema: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> FDDLLMResponse:
        """섹션에 맞는 프로바이더로 텍스트를 생성한다.

        Args:
            section_id: 섹션/태스크 식별자
            industry: 산업 식별자 (복합 키 라우팅용)
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 온도
            max_tokens: 최대 출력 토큰
            json_schema: JSON 구조화 출력 스키마
            timeout_seconds: 타임아웃

        Returns:
            FDDLLMResponse

        Raises:
            RuntimeError: 사용 가능한 프로바이더 없음
        """
        decision = self.resolve(section_id, industry=industry)
        client = self._providers[decision.provider]

        logger.info(
            "Router generating",
            extra={
                "ctx": {
                    "section_id": section_id,
                    "provider": decision.provider,
                    "is_fallback": decision.is_fallback,
                }
            },
        )

        response: LLMResponse = client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_schema=json_schema,
            timeout_seconds=timeout_seconds,
        )

        if not response.content or not response.content.strip():
            logger.warning(
                "Router received empty response",
                extra={
                    "ctx": {
                        "section_id": section_id,
                        "provider": decision.provider,
                        "model": response.model,
                    }
                },
            )
            raise RuntimeError(
                f"LLM returned empty response for section '{section_id}' "
                f"(provider: {decision.provider}, model: {response.model})"
            )

        return FDDLLMResponse(
            text=response.content,
            provider=decision.provider,
            model=response.model,
            section_id=section_id,
            is_fallback=decision.is_fallback,
            original_provider=decision.original_provider,
            token_usage=response.token_usage,
        )
