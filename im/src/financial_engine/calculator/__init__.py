"""Financial Engine — Calculator 서브패키지.

수익성, 성장성, 현금흐름, 레버리지, 산업별 지표를 계산합니다.

> 마지막 수정: 2026-02-11 15:30:00
"""

from src.financial_engine.calculator.healthcare_metrics import (
    HealthcareMetrics,
    calculate_healthcare_metrics,
)
from src.financial_engine.calculator.logistics_metrics import (
    LogisticsMetrics,
    calculate_logistics_metrics,
)
from src.financial_engine.calculator.manufacturing_metrics import (
    ManufacturingMetrics,
    calculate_manufacturing_metrics,
)
from src.financial_engine.calculator.saas import (
    SaaSMetrics,
    calculate_saas_metrics,
)

# 산업별 지표 유니온 타입
IndustryMetrics = (
    SaaSMetrics | ManufacturingMetrics | HealthcareMetrics | LogisticsMetrics
)

__all__ = [
    # Industry calculators
    "SaaSMetrics",
    "calculate_saas_metrics",
    "ManufacturingMetrics",
    "calculate_manufacturing_metrics",
    "HealthcareMetrics",
    "calculate_healthcare_metrics",
    "LogisticsMetrics",
    "calculate_logistics_metrics",
    # Type alias
    "IndustryMetrics",
]
