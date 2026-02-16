"""Industry Module — 산업별 KPI, 재무 가중치, 차트 추천, 내러티브 변형 제공 모듈.

> 마지막 수정: 2026-02-12 10:39:21

산업별 특화 데이터를 파이프라인 전반(렌더링, 차트, 재무, 내러티브)에 공급한다.
레지스트리 패턴으로 산업 모듈을 등록하고 industry_id로 조회한다.

사용 예시::

    from src.industry import get_industry_module, IndustryModule

    module = get_industry_module("tech")
    kpis = module.get_kpis()
"""

# Base
from src.industry.base import IndustryModule

# Exceptions
from src.industry.exceptions import IndustryError, UnsupportedIndustryError

# Models
from src.industry.models import (
    IndustryChartRecommendation,
    IndustryContext,
    IndustryKPI,
    KPIUnit,
    RiskCategory,
)

# Registry
from src.industry.registry import (
    INDUSTRY_REGISTRY,
    get_industry_module,
    get_industry_module_safe,
    register_industry,
)

# Concrete modules (import 시 @register_industry 데코레이터 실행)
from src.industry.financial_services import FinancialServicesModule
from src.industry.general import GeneralModule
from src.industry.healthcare import HealthcareModule
from src.industry.logistics import LogisticsModule
from src.industry.manufacturing import ManufacturingModule
from src.industry.tech_saas import TechSaaSModule

# Korea Overlay
from src.industry.korea import get_korea_overlay_data
from src.industry.korea.models import KoreaOverlayData

__version__ = "0.3.0"

__all__ = [
    # Base
    "IndustryModule",
    # Registry
    "INDUSTRY_REGISTRY",
    "get_industry_module",
    "get_industry_module_safe",
    "register_industry",
    # Models
    "IndustryKPI",
    "IndustryContext",
    "IndustryChartRecommendation",
    "KPIUnit",
    "RiskCategory",
    # Exceptions
    "IndustryError",
    "UnsupportedIndustryError",
    # Concrete modules
    "GeneralModule",
    "TechSaaSModule",
    "ManufacturingModule",
    "HealthcareModule",
    "LogisticsModule",
    "FinancialServicesModule",
    # Korea Overlay
    "get_korea_overlay_data",
    "KoreaOverlayData",
]
