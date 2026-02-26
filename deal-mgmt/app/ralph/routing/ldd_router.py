"""LDD 멀티모델 라우터 — 7단계 파이프라인 프로바이더 라우팅.

FDD의 FDDModelRouter 패턴을 비동기 + LDD 특화:
- Stage별 최적 프로바이더 자동 선택
- 듀얼 분석(Stage 3/4) 시 Writer/Reviewer 분리 보장
- 프로바이더 폴백 체인
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── LDD 라우팅 맵 ─────────────────────────────────────────────────

DEFAULT_LDD_ROUTING: dict[str, str] = {
    # Stage 1: 문서 분류 (비용 효율)
    "document_classification": "google",

    # Stage 2: 조항 추출 (법률 문서 이해력)
    "clause_extraction": "anthropic",

    # Stage 3: 리스크 분석 (관점 다양화)
    "risk_analysis_buyer": "anthropic",
    "risk_analysis_independent": "openai",

    # Stage 4: 누락 탐지 (커버리지 극대화)
    "gap_detection_checklist": "anthropic",
    "gap_detection_freeform": "openai",

    # Stage 5: 관할권 교차 (언어별 특화)
    "jurisdiction_korean": "anthropic",
    "jurisdiction_english": "openai",

    # Stage 6: 레포트 생성 (톤 일관성)
    "report_generation": "anthropic",
    "executive_summary": "anthropic",

    # Stage 7: QA (독립 팩트체크 — 분석에 미사용 프로바이더)
    "final_qa": "google",

    # 기존 섹션별 분석 (단일 LLM 모드 호환)
    "governance_analysis": "anthropic",
    "capital_analysis": "anthropic",
    "contracts_analysis": "anthropic",
    "litigation_analysis": "anthropic",
    "labor_analysis": "anthropic",
    "ip_analysis": "openai",
    "real_estate_analysis": "google",
    "permits_analysis": "openai",
    "tax_analysis": "openai",
    "data_it_analysis": "openai",
}

# 폴백 체인
FALLBACK_CHAIN: dict[str, list[str]] = {
    "anthropic": ["openai", "google"],
    "openai": ["anthropic", "google"],
    "google": ["openai", "anthropic"],
}


@dataclass(frozen=True)
class RoutingDecision:
    """라우팅 결정 결과."""

    section_id: str
    provider: str
    is_fallback: bool = False
    original_provider: str | None = None


class LDDModelRouter:
    """LDD 멀티모델 라우터.

    RalphLLMClient의 어댑터 가용성을 확인하여
    최적 프로바이더를 선택하고, 불가 시 폴백한다.

    Args:
        llm_client: RalphLLMClient 인스턴스
        routing_map: 섹션별 프로바이더 맵 (기본: DEFAULT_LDD_ROUTING)
    """

    def __init__(
        self,
        llm_client,
        routing_map: dict[str, str] | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._routing_map = routing_map or DEFAULT_LDD_ROUTING
        # 어댑터에서 사용 가능한 프로바이더 목록 구축
        self._available_providers: set[str] = set()
        for adapter in self._llm_client._adapters:
            if adapter.is_available:
                self._available_providers.add(adapter.provider_name)

    @property
    def available_providers(self) -> list[str]:
        return sorted(self._available_providers)

    def resolve(self, section_id: str) -> RoutingDecision:
        """섹션에 대한 프로바이더를 결정한다.

        Returns:
            RoutingDecision (폴백 여부 포함)

        Raises:
            RuntimeError: 사용 가능한 프로바이더가 전혀 없을 때
        """
        primary = self._routing_map.get(section_id, "anthropic")

        # 1차: primary 사용 가능?
        if primary in self._available_providers:
            return RoutingDecision(section_id=section_id, provider=primary)

        # 2차: 폴백 체인
        for fallback in FALLBACK_CHAIN.get(primary, []):
            if fallback in self._available_providers:
                logger.info(
                    "LDD 라우터 폴백: section=%s, 원래=%s → 폴백=%s",
                    section_id, primary, fallback,
                )
                return RoutingDecision(
                    section_id=section_id,
                    provider=fallback,
                    is_fallback=True,
                    original_provider=primary,
                )

        raise RuntimeError(
            f"LDD 라우터: '{section_id}'에 사용 가능한 프로바이더 없음. "
            f"등록: {self.available_providers}"
        )

    async def call_routed(self, section_id: str, system: str, user: str) -> str:
        """섹션에 맞는 프로바이더로 LLM을 호출한다."""
        decision = self.resolve(section_id)
        result = await self._llm_client.call_for_provider(
            system, user, provider=decision.provider,
        )
        if not result or not result.strip():
            raise ValueError(
                f"LDD 라우터: '{section_id}' (provider={decision.provider}) 빈 응답 반환"
            )
        return result
