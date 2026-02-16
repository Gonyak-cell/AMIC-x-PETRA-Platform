"""Financial Engine 패키지.

DART API에서 수집한 한글 재무 데이터를 정규화/매핑/계산/검증하여
Design Renderer의 FinancialStatements 형식으로 변환합니다.

Usage::
    from src.financial_engine import FinancialProcessor, ProcessorConfig
    from src.financial_engine import AccountMapper, MappingConfig
    from src.financial_engine import UnitNormalizer
"""

from src.financial_engine.calculator.cash_flow import (
    CashFlowMetrics,
    calculate_cash_flow_metrics,
    calculate_ebitda,
    calculate_fcf,
    calculate_nwc,
)
from src.financial_engine.calculator.growth import (
    GrowthMetrics,
    calculate_cagr,
    calculate_growth,
    calculate_yoy,
)
from src.financial_engine.calculator.leverage import (
    LeverageMetrics,
    calculate_leverage,
)
from src.financial_engine.calculator.profitability import (
    ProfitabilityMetrics,
    calculate_profitability,
)
from src.financial_engine.calculator import IndustryMetrics
from src.financial_engine.calculator.valuation import (
    ExitAnalysis,
    IRRScenario,
    ValuationMetrics,
    calculate_ev_ebitda,
    calculate_ev_revenue,
    calculate_irr,
    calculate_moic,
    calculate_pe_ratio,
    calculate_valuation_metrics,
)
from src.financial_engine.calculator.saas import (
    SaaSMetrics,
    calculate_saas_metrics,
)
from src.financial_engine.calculator.manufacturing_metrics import (
    ManufacturingMetrics,
    calculate_manufacturing_metrics,
)
from src.financial_engine.calculator.healthcare_metrics import (
    HealthcareMetrics,
    calculate_healthcare_metrics,
)
from src.financial_engine.calculator.logistics_metrics import (
    LogisticsMetrics,
    calculate_logistics_metrics,
)
from src.financial_engine.exceptions import (
    AccountNotFoundError,
    AmbiguousMappingError,
    BalanceSheetError,
    CalculationError,
    ConsistencyError,
    CurrencyConversionError,
    FinancialEngineError,
    InsufficientDataError,
    MappingError,
    NormalizationError,
    UnitConversionError,
    ValidationError,
)
from src.financial_engine.mapper.account_mapper import (
    AccountMapper,
    AccountMapping,
    MappingConfig,
)
from src.financial_engine.mapper.chart_of_accounts import (
    AccountMetadata,
    AccountSign,
    StandardAccount,
    StatementType,
)
from src.financial_engine.normalizer.unit_normalizer import (
    UnitNormalizer,
    UnitScale,
)
from src.financial_engine.processor import (
    FinancialProcessor,
    ProcessingResult,
    ProcessorConfig,
)
from src.financial_engine.validator.balance_checker import (
    BalanceCheckConfig,
    BalanceCheckReport,
    BalanceCheckResult,
    BalanceChecker,
)
from src.financial_engine.validator.consistency_checker import (
    AnomalyType,
    ConsistencyAnomaly,
    ConsistencyChecker,
    ConsistencyConfig,
    ConsistencyReport,
)

__all__ = [
    # Processor (main entry point)
    "FinancialProcessor",
    "ProcessorConfig",
    "ProcessingResult",
    # Mapper
    "AccountMapper",
    "AccountMapping",
    "MappingConfig",
    "StandardAccount",
    "StatementType",
    "AccountSign",
    "AccountMetadata",
    # Normalizer
    "UnitNormalizer",
    "UnitScale",
    # Calculators
    "ProfitabilityMetrics",
    "calculate_profitability",
    "GrowthMetrics",
    "calculate_growth",
    "calculate_yoy",
    "calculate_cagr",
    "CashFlowMetrics",
    "calculate_cash_flow_metrics",
    "calculate_ebitda",
    "calculate_fcf",
    "calculate_nwc",
    "LeverageMetrics",
    "calculate_leverage",
    # Valuation Calculator
    "ValuationMetrics",
    "IRRScenario",
    "ExitAnalysis",
    "calculate_valuation_metrics",
    "calculate_ev_ebitda",
    "calculate_pe_ratio",
    "calculate_ev_revenue",
    "calculate_irr",
    "calculate_moic",
    # Industry Calculators
    "IndustryMetrics",
    "SaaSMetrics",
    "calculate_saas_metrics",
    "ManufacturingMetrics",
    "calculate_manufacturing_metrics",
    "HealthcareMetrics",
    "calculate_healthcare_metrics",
    "LogisticsMetrics",
    "calculate_logistics_metrics",
    # Validators
    "BalanceChecker",
    "BalanceCheckConfig",
    "BalanceCheckResult",
    "BalanceCheckReport",
    "ConsistencyChecker",
    "ConsistencyConfig",
    "ConsistencyReport",
    "ConsistencyAnomaly",
    "AnomalyType",
    # Exceptions
    "FinancialEngineError",
    "MappingError",
    "AccountNotFoundError",
    "AmbiguousMappingError",
    "NormalizationError",
    "UnitConversionError",
    "CurrencyConversionError",
    "CalculationError",
    "InsufficientDataError",
    "ValidationError",
    "BalanceSheetError",
    "ConsistencyError",
]

__version__ = "0.4.0"
