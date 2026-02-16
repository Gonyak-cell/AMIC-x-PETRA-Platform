"""FDD 모델 라우터 팩토리.

기존 LLMClient 인스턴스를 활용하여 FDDModelRouter를 생성한다.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.services.llm.client import (
    AnthropicClient,
    GeminiClient,
    LLMClient,
    OpenAIClient,
)
from app.services.llm.routing.model_router import FDDModelRouter

logger = get_logger(__name__)


def create_fdd_model_router(
    routing_map: dict[str, str] | None = None,
) -> FDDModelRouter:
    """FDD 모델 라우터를 생성한다.

    3개 프로바이더 클라이언트를 인스턴스화하고,
    사용 가능한 것만 라우터에 등록한다.

    Args:
        routing_map: 커스텀 라우팅 맵 (None이면 DEFAULT_FDD_ROUTING 사용)

    Returns:
        FDDModelRouter 인스턴스
    """
    providers: dict[str, LLMClient] = {
        "openai": OpenAIClient(),
        "anthropic": AnthropicClient(),
        "gemini": GeminiClient(),
    }

    available = [name for name, client in providers.items() if client.is_available()]
    logger.info(
        "FDD ModelRouter created",
        extra={"ctx": {"available_providers": available}},
    )

    return FDDModelRouter(providers=providers, routing_map=routing_map)
