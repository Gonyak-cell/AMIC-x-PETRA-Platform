"""ModelRouter 팩토리.

> 마지막 수정: 2026-02-11 21:38:33

NarrativeConfig를 기반으로 프로바이더를 초기화하고 ModelRouter를 생성한다.
"""

from __future__ import annotations

import logging

from src.narrative_generator.config import NarrativeConfig, get_config
from src.narrative_generator.engine.llm_provider import ProviderName
from src.narrative_generator.engine.model_router import ModelRouter
from src.narrative_generator.engine.providers.anthropic_provider import (
    AnthropicProvider,
)
from src.narrative_generator.engine.providers.google_provider import GoogleProvider
from src.narrative_generator.engine.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def create_model_router(
    config: NarrativeConfig | None = None,
) -> ModelRouter:
    """설정 기반으로 ModelRouter를 생성한다.

    Args:
        config: NarrativeConfig. None이면 get_config() 사용.

    Returns:
        초기화된 ModelRouter.
    """
    cfg = config or get_config()

    # 프로바이더 초기화
    providers: dict[ProviderName, OpenAIProvider | AnthropicProvider | GoogleProvider] = {}

    openai_provider = OpenAIProvider(
        api_key=cfg.openai_api_key,
        default_model=cfg.narrative_model_name,
    )
    providers[ProviderName.OPENAI] = openai_provider

    anthropic_provider = AnthropicProvider(
        api_key=cfg.anthropic_api_key,
        default_model=cfg.anthropic_model_name,
    )
    providers[ProviderName.ANTHROPIC] = anthropic_provider

    google_provider = GoogleProvider(
        api_key=cfg.google_api_key,
        default_model=cfg.google_model_name,
    )
    providers[ProviderName.GOOGLE] = google_provider

    # 라우팅 맵 파싱
    routing_map: dict[str, ProviderName] | None = None
    raw_map = cfg.get_routing_map()
    if raw_map:
        routing_map = {}
        for section_id, provider_str in raw_map.items():
            try:
                routing_map[section_id] = ProviderName(provider_str)
            except ValueError:
                logger.warning(
                    "알 수 없는 프로바이더 '%s' (section='%s') — 무시",
                    provider_str,
                    section_id,
                )

    # 폴백 순서 파싱
    fallback_order: list[ProviderName] = []
    for p in cfg.get_fallback_order():
        try:
            fallback_order.append(ProviderName(p))
        except ValueError:
            logger.warning("알 수 없는 폴백 프로바이더 '%s' — 무시", p)

    router = ModelRouter(
        providers=providers,
        routing_map=routing_map,
        fallback_order=fallback_order or None,
    )

    available = router.available_providers
    logger.info(
        "ModelRouter 초기화 완료: 사용 가능=%s, 라우팅 맵=%s",
        [p.value for p in available],
        "custom" if routing_map else "default",
    )

    return router
