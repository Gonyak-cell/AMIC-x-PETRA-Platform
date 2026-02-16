"""FDD 멀티모델 LLM 라우팅 패키지.

IM의 섹션별 라우팅 패턴을 FDD에 적응.
섹션별로 최적의 LLM 프로바이더를 선택하고, 폴백 체인을 제공.
"""

from app.services.llm.routing.model_router import FDDModelRouter, RoutingDecision
from app.services.llm.routing.router_factory import create_fdd_model_router

__all__ = [
    "FDDModelRouter",
    "RoutingDecision",
    "create_fdd_model_router",
]
