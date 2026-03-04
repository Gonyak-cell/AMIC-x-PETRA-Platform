"""FDD 산업 모듈 레지스트리.

IM의 Registry Pattern을 FDD에 적응.
@register_fdd_industry 데코레이터로 산업 모듈 자동 등록.
"""

from __future__ import annotations

from typing import TypeVar

from app.industry.base import FDDIndustryModule

T = TypeVar("T", bound=type[FDDIndustryModule])

# 전역 레지스트리: {industry_id: FDDIndustryModule 인스턴스}
INDUSTRY_REGISTRY: dict[str, FDDIndustryModule] = {}


def register_fdd_industry(cls: T) -> T:
    """산업 모듈을 레지스트리에 등록하는 데코레이터.

    Usage::

        @register_fdd_industry
        class FDDTechSaaSModule(FDDIndustryModule):
            industry_id = "tech"
            ...

    Args:
        cls: FDDIndustryModule 서브클래스.

    Returns:
        등록된 클래스 (변경 없이 그대로 반환).
    """
    instance = cls()
    INDUSTRY_REGISTRY[instance.industry_id] = instance
    return cls


def get_fdd_industry_module(industry_id: str) -> FDDIndustryModule:
    """산업 모듈을 반환한다 (strict).

    Args:
        industry_id: 산업 식별자.

    Returns:
        FDDIndustryModule 인스턴스.

    Raises:
        KeyError: 지원하지 않는 산업 ID.
    """
    module = INDUSTRY_REGISTRY.get(industry_id)
    if module is None:
        available = list(INDUSTRY_REGISTRY.keys())
        raise KeyError(
            f"지원하지 않는 FDD 산업: '{industry_id}'. 사용 가능: {available}"
        )
    return module


def get_fdd_industry_module_safe(industry_id: str) -> FDDIndustryModule:
    """산업 모듈을 반환한다 (safe — 없으면 general 폴백).

    Args:
        industry_id: 산업 식별자.

    Returns:
        FDDIndustryModule 인스턴스. 없으면 "general" 모듈 반환.
    """
    module = INDUSTRY_REGISTRY.get(industry_id)
    if module is not None:
        return module
    return INDUSTRY_REGISTRY["general"]


def list_industries() -> list[dict[str, str]]:
    """등록된 산업 목록을 반환한다.

    Returns:
        [{"id": ..., "name_kr": ..., "name_en": ...}, ...]
    """
    return [
        {
            "id": mod.industry_id,
            "name_kr": mod.industry_name_kr,
            "name_en": mod.industry_name_en,
        }
        for mod in INDUSTRY_REGISTRY.values()
    ]
