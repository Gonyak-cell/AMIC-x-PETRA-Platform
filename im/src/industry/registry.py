"""산업 모듈 레지스트리 — @register_industry 데코레이터 + 조회 함수.

> 마지막 수정: 2026-02-12 10:39:21
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.industry.base import IndustryModule

logger = logging.getLogger(__name__)

# 레지스트리 (industry_id -> IndustryModule 클래스)
INDUSTRY_REGISTRY: dict[str, type[IndustryModule]] = {}


def get_industry_module(industry_id: str) -> IndustryModule:
    """industry_id로 산업 모듈 인스턴스를 생성하여 반환.

    Args:
        industry_id: 산업 식별자 (예: "tech", "manufacturing").

    Returns:
        해당 산업의 IndustryModule 인스턴스.

    Raises:
        UnsupportedIndustryError: 미등록 industry_id.
    """
    from src.industry.exceptions import UnsupportedIndustryError

    if industry_id not in INDUSTRY_REGISTRY:
        raise UnsupportedIndustryError(
            industry_id=industry_id,
            available=list(INDUSTRY_REGISTRY.keys()),
        )
    cls = INDUSTRY_REGISTRY[industry_id]
    return cls()


def get_industry_module_safe(industry_id: str) -> IndustryModule:
    """industry_id로 산업 모듈 인스턴스를 반환. 미등록 시 GeneralModule 폴백.

    get_industry_module()과 달리 UnsupportedIndustryError를 발생시키지 않고,
    미등록 산업 ID에 대해 GeneralModule로 폴백한다.

    Args:
        industry_id: 산업 식별자 (예: "tech", "manufacturing").

    Returns:
        해당 산업의 IndustryModule 인스턴스 또는 GeneralModule 인스턴스.

    Raises:
        UnsupportedIndustryError: GeneralModule도 미등록인 경우.
    """
    if industry_id in INDUSTRY_REGISTRY:
        return INDUSTRY_REGISTRY[industry_id]()

    # Fallback: GeneralModule
    if "general" in INDUSTRY_REGISTRY:
        logger.warning(
            "산업 모듈 미등록 '%s', GeneralModule로 폴백 (지원 산업: %s)",
            industry_id,
            list(INDUSTRY_REGISTRY.keys()),
        )
        return INDUSTRY_REGISTRY["general"]()

    # GeneralModule도 없으면 에러
    from src.industry.exceptions import UnsupportedIndustryError

    raise UnsupportedIndustryError(
        industry_id=industry_id,
        available=list(INDUSTRY_REGISTRY.keys()),
    )


def register_industry(
    cls: type[IndustryModule],
) -> type[IndustryModule]:
    """산업 모듈 클래스를 레지스트리에 등록하는 데코레이터.

    Usage::

        @register_industry
        class TechModule(IndustryModule):
            industry_id = "tech"
            ...
    """
    INDUSTRY_REGISTRY[cls.industry_id] = cls
    return cls
