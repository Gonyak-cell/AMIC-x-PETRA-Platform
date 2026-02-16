"""Financial Engine -- 통합 프로세서 (T-F12).

> 마지막 수정: 2026-02-11 22:00:00

Phase 3 Financial Engine의 오케스트레이터 모듈.
AccountMapper, UnitNormalizer, 각종 Calculator, Validator를 하나의
처리 파이프라인으로 묶어 원시 재무 데이터를 정규화/매핑/계산/검증한 뒤
design_renderer.im_document.FinancialStatements 형태로 출력한다.

파이프라인:
  1. Normalize — 문자열/혼합 단위를 Decimal(원 단위)로 통일
  2. Map — 한글 계정명을 StandardAccount로 변환
  3. Derive — EBITDA, FCF, TOTAL_DEBT 등 파생 계정 산출
  4. Calculate — 수익성/성장성/현금흐름/레버리지 지표 산출
  5. Validate — 재무상태표 균형, 다기간 일관성 검증

사용 예시::

    from decimal import Decimal
    from src.financial_engine.processor import FinancialProcessor

    processor = FinancialProcessor()
    raw = {
        '매출액': {'2022': Decimal('100000'), '2023': Decimal('120000')},
        '영업이익': {'2022': Decimal('20000'), '2023': Decimal('25000')},
        '당기순이익': {'2022': Decimal('15000'), '2023': Decimal('18000')},
        '자산총계': {'2022': Decimal('500000'), '2023': Decimal('600000')},
        '부채총계': {'2022': Decimal('300000'), '2023': Decimal('350000')},
        '자본총계': {'2022': Decimal('200000'), '2023': Decimal('250000')},
    }
    result = processor.process(raw, source_unit='원')
    fs = result.to_financial_statements()
    print(fs.revenue)  # {'2022': 100000.0, '2023': 120000.0}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from src.data_ingestor.dart.models import FinancialStatementsCollection
from src.design_renderer.im_document import FinancialStatements
from src.financial_engine.calculator.cash_flow import (
    CashFlowMetrics,
    calculate_cash_flow_metrics,
    calculate_ebitda,
    calculate_fcf,
)
from src.financial_engine.calculator.growth import (
    GrowthMetrics,
    calculate_growth,
)
from src.financial_engine.calculator.leverage import (
    LeverageMetrics,
    calculate_leverage,
)
from src.financial_engine.calculator.valuation import (
    ValuationMetrics,
    calculate_valuation_metrics,
)
from src.financial_engine.calculator.profitability import (
    ProfitabilityMetrics,
    calculate_profitability,
)
from src.financial_engine.calculator import IndustryMetrics
from src.financial_engine.calculator.healthcare_metrics import (
    calculate_healthcare_metrics,
)
from src.financial_engine.calculator.logistics_metrics import (
    calculate_logistics_metrics,
)
from src.financial_engine.calculator.manufacturing_metrics import (
    calculate_manufacturing_metrics,
)
from src.financial_engine.calculator.saas import calculate_saas_metrics
from src.financial_engine.mapper.account_mapper import (
    AccountMapper,
    MappingConfig,
)
from src.financial_engine.mapper.chart_of_accounts import (
    ACCOUNT_METADATA,
    StandardAccount,
)
from src.financial_engine.normalizer.unit_normalizer import UnitNormalizer
from src.financial_engine.validator.balance_checker import (
    BalanceCheckReport,
    BalanceChecker,
)
from src.financial_engine.validator.consistency_checker import (
    ConsistencyChecker,
    ConsistencyReport,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# StandardAccount 별칭 & 필드 매핑
# ---------------------------------------------------------------------------

_SA = StandardAccount

_ACCOUNT_TO_FIELD: dict[StandardAccount, str] = {
    _SA.REVENUE: "revenue",
    _SA.COST_OF_GOODS_SOLD: "cost_of_goods_sold",
    _SA.GROSS_PROFIT: "gross_profit",
    _SA.OPERATING_INCOME: "operating_income",
    _SA.NET_INCOME: "net_income",
    _SA.SGA_EXPENSES: "sga_expenses",
    _SA.EBITDA: "ebitda",
    _SA.TOTAL_ASSETS: "total_assets",
    _SA.TOTAL_LIABILITIES: "total_liabilities",
    _SA.TOTAL_EQUITY: "total_equity",
    _SA.CASH_AND_EQUIVALENTS: "cash_and_equivalents",
    _SA.TOTAL_DEBT: "total_debt",
    _SA.OPERATING_CASH_FLOW: "operating_cash_flow",
    _SA.INVESTING_CASH_FLOW: "investing_cash_flow",
    _SA.FINANCING_CASH_FLOW: "financing_cash_flow",
    _SA.CAPEX: "capex",
    _SA.FREE_CASH_FLOW: "free_cash_flow",
}


# ---------------------------------------------------------------------------
# 설정 & 결과 데이터클래스
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessorConfig:
    """프로세서 설정.

    Attributes:
        source_unit: 입력 데이터의 기본 금액 단위.
        target_unit: 출력 데이터의 금액 단위.
        mapping_config: AccountMapper에 전달할 매핑 설정.
        validate: True이면 Balance/Consistency 검증을 실행.
    """

    source_unit: str = "원"
    target_unit: str = "원"
    mapping_config: MappingConfig = field(default_factory=MappingConfig)
    validate: bool = True


@dataclass
class ProcessingResult:
    """처리 결과.

    Attributes:
        mapped_data: StandardAccount → {연도: Decimal} 매핑된 재무 데이터.
        profitability: 수익성 지표.
        growth: 성장성 지표.
        cash_flow: 현금흐름 지표.
        leverage: 레버리지 지표.
        balance_check: 재무상태표 균형 검증 보고서 (validate=False이면 None).
        consistency_check: 다기간 일관성 검증 보고서 (validate=False이면 None).
        unmapped_accounts: 매핑 실패한 한글 계정명 목록.
        warnings: 처리 중 발생한 경고 목록.
    """

    mapped_data: dict[StandardAccount, dict[str, Decimal | None]]
    profitability: ProfitabilityMetrics
    growth: GrowthMetrics
    cash_flow: CashFlowMetrics
    leverage: LeverageMetrics
    balance_check: BalanceCheckReport | None
    consistency_check: ConsistencyReport | None
    unmapped_accounts: list[str]
    warnings: list[str]
    industry_metrics: IndustryMetrics | None = None
    valuation: ValuationMetrics | None = None

    def to_financial_statements(self) -> FinancialStatements:
        """Decimal -> float 변환 + StandardAccount -> FinancialStatements 필드 매핑.

        _ACCOUNT_TO_FIELD에 있는 계정은 해당 필드에 매핑.
        _ACCOUNT_TO_FIELD에 없는 계정은 extra dict에 추가.
        계산된 파생 지표(EBITDA, FCF)도 포함.

        Returns:
            design_renderer.im_document.FinancialStatements
        """
        kwargs: dict[str, Any] = {}
        extra: dict[str, dict[str, float]] = {}

        for account, year_values in self.mapped_data.items():
            float_values = _decimal_dict_to_float(year_values)

            if account in _ACCOUNT_TO_FIELD:
                kwargs[_ACCOUNT_TO_FIELD[account]] = float_values
            else:
                # extra에 영문명으로 추가
                meta = ACCOUNT_METADATA.get(account)
                name_en = meta.name_en if meta else account.name
                extra[name_en] = float_values

        # EBITDA: mapped_data에 없으면 cash_flow 지표에서 가져옴
        if "ebitda" not in kwargs or not kwargs["ebitda"]:
            if self.cash_flow.ebitda:
                kwargs["ebitda"] = _decimal_dict_to_float(self.cash_flow.ebitda)

        # FREE_CASH_FLOW: mapped_data에 없으면 cash_flow 지표에서 가져옴
        if "free_cash_flow" not in kwargs or not kwargs["free_cash_flow"]:
            if self.cash_flow.free_cash_flow:
                kwargs["free_cash_flow"] = _decimal_dict_to_float(
                    self.cash_flow.free_cash_flow
                )

        kwargs["extra"] = extra
        return FinancialStatements(**kwargs)


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------


def _decimal_dict_to_float(
    d: dict[str, Decimal | None],
) -> dict[str, float]:
    """Decimal 딕셔너리를 float 딕셔너리로 변환한다. None 값은 제외."""
    return {
        year: float(val)
        for year, val in d.items()
        if val is not None
    }


def _filter_none_values(
    d: dict[str, Decimal | None],
) -> dict[str, Decimal]:
    """None 값을 제외한 Decimal 딕셔너리를 반환한다."""
    return {
        year: val
        for year, val in d.items()
        if val is not None
    }


# ---------------------------------------------------------------------------
# FinancialProcessor
# ---------------------------------------------------------------------------


class FinancialProcessor:
    """재무 데이터 통합 처리 파이프라인.

    원시 재무 데이터(한글 계정명 + 다양한 단위)를 입력받아:
    1. 단위 정규화 (원 단위 Decimal)
    2. 계정 매핑 (한글 → StandardAccount)
    3. 파생 계정 산출 (EBITDA, FCF, TOTAL_DEBT)
    4. 재무 지표 계산 (수익성, 성장성, 현금흐름, 레버리지)
    5. 데이터 검증 (균형, 일관성)

    을 수행하고 ProcessingResult를 반환한다.

    Args:
        config: 프로세서 설정. None이면 기본 ProcessorConfig 사용.

    Examples:
        >>> processor = FinancialProcessor()
        >>> result = processor.process(raw_data, source_unit='백만원')
        >>> fs = result.to_financial_statements()
    """

    def __init__(self, config: ProcessorConfig | None = None) -> None:
        """Initialize mapper, normalizer, validators.

        Args:
            config: 프로세서 설정. None이면 기본값 사용.
        """
        self._config = config or ProcessorConfig()
        self._mapper = AccountMapper(config=self._config.mapping_config)
        self._normalizer = UnitNormalizer()
        self._balance_checker = BalanceChecker()
        self._consistency_checker = ConsistencyChecker()

    @property
    def config(self) -> ProcessorConfig:
        """현재 설정을 반환한다."""
        return self._config

    def process(
        self,
        raw_data: dict[str, dict[str, str | Decimal | None]],
        *,
        source_unit: str | None = None,
        industry_id: str | None = None,
        industry_data: dict[str, dict[str, Decimal | None]] | None = None,
        valuation_config: dict[str, Any] | None = None,
    ) -> ProcessingResult:
        """Full pipeline: normalize -> map -> calculate -> validate.

        Pipeline steps:
        1. Normalize: UnitNormalizer로 모든 값을 Decimal(원 단위)로 변환
        2. Map: AccountMapper.map_all()로 한글 계정명을 StandardAccount로 변환
        3. Derive: 파생 계정(EBITDA, FCF, TOTAL_DEBT) 산출
        4. Calculate: 수익성/성장성/현금흐름/레버리지 지표 계산
        4e. Industry: 산업별 재무 지표 계산 (industry_id 제공 시)
        4f. Valuation: 밸류에이션 지표 계산 (valuation_config 제공 시)
        5. Validate: 재무상태표 균형, 다기간 일관성 검증

        Args:
            raw_data: {한글계정명: {연도: 값}} 형태의 원시 데이터.
                값은 str("150,000백만원"), Decimal, 또는 None.
            source_unit: 정규화 시 사용할 소스 단위. None이면 config.source_unit 사용.
            industry_id: 산업 식별자 (예: "tech", "manufacturing"). None이면 건너뜀.
            industry_data: 산업 고유 데이터 ``{키: {연도: Decimal | None}}``.
                표준 계정에 포함되지 않는 산업별 입력 데이터.
            valuation_config: 밸류에이션 설정 딕셔너리. None이면 건너뜀.

        Returns:
            ProcessingResult: 매핑된 데이터, 재무 지표, 검증 보고서를 포함한 결과.
        """
        warnings: list[str] = []
        effective_unit = source_unit or self._config.source_unit

        # 매퍼 상태 초기화
        self._mapper.reset()

        # --- 1. Normalize ---
        normalized = self._normalize_data(raw_data, effective_unit, warnings)

        # --- 2. Map ---
        mapped_data = self._mapper.map_all(normalized)
        unmapped = self._mapper.unmapped_accounts
        warnings.extend(self._mapper.warnings)

        # --- 3. Derive ---
        self._derive_accounts(mapped_data, warnings)

        # --- 4. Calculate ---
        profitability = self._calculate_profitability(mapped_data, warnings)
        growth = self._calculate_growth(mapped_data, warnings)
        cash_flow = self._calculate_cash_flow(mapped_data, warnings)
        leverage = self._calculate_leverage(mapped_data, cash_flow, warnings)

        # --- 4e. Industry-specific metrics ---
        industry_metrics: IndustryMetrics | None = None
        if industry_id:
            industry_metrics = self._calculate_industry_metrics(
                industry_id,
                mapped_data,
                industry_data or {},
                profitability,
                growth,
                warnings,
            )

        # --- 4f. Valuation ---
        valuation_metrics: ValuationMetrics | None = None
        if valuation_config:
            valuation_metrics = self._calculate_valuation(
                mapped_data, valuation_config, warnings
            )

        # --- 5. Validate ---
        balance_report: BalanceCheckReport | None = None
        consistency_report: ConsistencyReport | None = None

        if self._config.validate:
            balance_report = self._validate_balance(mapped_data, warnings)
            consistency_report = self._validate_consistency(
                normalized, warnings
            )

        return ProcessingResult(
            mapped_data=mapped_data,
            profitability=profitability,
            growth=growth,
            cash_flow=cash_flow,
            leverage=leverage,
            balance_check=balance_report,
            consistency_check=consistency_report,
            unmapped_accounts=unmapped,
            warnings=warnings,
            industry_metrics=industry_metrics,
            valuation=valuation_metrics,
        )

    def process_from_dart(
        self,
        collection: FinancialStatementsCollection,
        *,
        consolidated: bool = True,
    ) -> ProcessingResult:
        """FinancialStatementsCollection을 raw_data로 변환 후 process() 호출.

        Steps:
        1. collection에서 고유 계정명 추출
        2. 각 계정명에 대해 get_account_values() 호출
        3. raw_data dict 구성
        4. process(raw_data, source_unit="원") 호출 (DART 금액은 이미 원 단위)

        Args:
            collection: DART 재무제표 컬렉션.
            consolidated: True이면 연결(CFS), False이면 별도(OFS).

        Returns:
            ProcessingResult.
        """
        raw_data: dict[str, dict[str, Decimal | None]] = {}

        account_names = collection.account_names
        for account_nm in account_names:
            year_values = collection.get_account_values(
                account_nm, consolidated=consolidated
            )
            if year_values:
                raw_data[account_nm] = year_values

        logger.info(
            "DART 데이터 변환 완료: %d개 계정, consolidated=%s",
            len(raw_data),
            consolidated,
        )

        return self.process(raw_data, source_unit="원")

    # -----------------------------------------------------------------------
    # 내부 파이프라인 단계
    # -----------------------------------------------------------------------

    def _normalize_data(
        self,
        raw_data: dict[str, dict[str, str | Decimal | None]],
        source_unit: str,
        warnings: list[str],
    ) -> dict[str, dict[str, Decimal | None]]:
        """Step 1: 원시 데이터를 Decimal(원 단위)로 정규화한다.

        None 값은 보존하여 이후 단계에서 graceful하게 처리한다.

        Args:
            raw_data: 원시 데이터.
            source_unit: 소스 금액 단위.
            warnings: 경고를 수집할 리스트.

        Returns:
            정규화된 데이터 {계정명: {연도: Decimal | None}}.
        """
        normalized: dict[str, dict[str, Decimal | None]] = {}

        for account_name, year_values in raw_data.items():
            normalized_years: dict[str, Decimal | None] = {}
            for year, value in year_values.items():
                if value is None:
                    normalized_years[year] = None
                else:
                    try:
                        normalized_years[year] = self._normalizer.normalize(
                            value, source_unit=source_unit
                        )
                    except Exception as exc:
                        msg = (
                            f"정규화 실패: '{account_name}' {year}년 "
                            f"값='{value}' — {exc}"
                        )
                        logger.warning(msg)
                        warnings.append(msg)
                        normalized_years[year] = None
            normalized[account_name] = normalized_years

        return normalized

    def _derive_accounts(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> None:
        """Step 3: 파생 계정(EBITDA, FCF, TOTAL_DEBT)을 산출한다.

        이미 존재하는 파생 계정은 건너뛴다. mapped_data를 직접 수정한다.

        Args:
            mapped_data: 매핑된 데이터 (in-place 수정).
            warnings: 경고를 수집할 리스트.
        """
        # --- EBITDA ---
        if _SA.EBITDA not in mapped_data:
            try:
                oi = mapped_data.get(_SA.OPERATING_INCOME, {})
                dep = mapped_data.get(_SA.DEPRECIATION, {})
                amort = mapped_data.get(_SA.AMORTIZATION)

                if oi and dep:
                    ebitda_values = calculate_ebitda(oi, dep, amort)
                    if ebitda_values:
                        # Decimal 값을 Decimal | None 형태로 변환
                        mapped_data[_SA.EBITDA] = {
                            y: v for y, v in ebitda_values.items()
                        }
                        logger.info("EBITDA 파생 계정 산출 완료: %d개 연도", len(ebitda_values))
            except Exception as exc:
                msg = f"EBITDA 파생 계정 산출 실패: {exc}"
                logger.warning(msg)
                warnings.append(msg)

        # --- FREE_CASH_FLOW ---
        if _SA.FREE_CASH_FLOW not in mapped_data:
            try:
                ocf = mapped_data.get(_SA.OPERATING_CASH_FLOW, {})
                capex = mapped_data.get(_SA.CAPEX, {})

                if ocf and capex:
                    fcf_values = calculate_fcf(ocf, capex)
                    if fcf_values:
                        mapped_data[_SA.FREE_CASH_FLOW] = {
                            y: v for y, v in fcf_values.items()
                        }
                        logger.info("FCF 파생 계정 산출 완료: %d개 연도", len(fcf_values))
            except Exception as exc:
                msg = f"FCF 파생 계정 산출 실패: {exc}"
                logger.warning(msg)
                warnings.append(msg)

        # --- TOTAL_DEBT ---
        if _SA.TOTAL_DEBT not in mapped_data:
            try:
                st_borrow = mapped_data.get(_SA.SHORT_TERM_BORROWINGS, {})
                lt_borrow = mapped_data.get(_SA.LONG_TERM_BORROWINGS, {})
                bonds = mapped_data.get(_SA.BONDS_PAYABLE, {})
                cpltd = mapped_data.get(_SA.CURRENT_PORTION_LTD, {})

                # 최소한 단기차입금 또는 장기차입금이 있어야 계산
                if st_borrow or lt_borrow:
                    # 모든 연도 수집
                    all_years: set[str] = set()
                    for d in (st_borrow, lt_borrow, bonds, cpltd):
                        all_years.update(d.keys())

                    total_debt_values: dict[str, Decimal | None] = {}
                    for year in sorted(all_years):
                        components = [
                            st_borrow.get(year),
                            lt_borrow.get(year),
                            bonds.get(year),
                            cpltd.get(year),
                        ]
                        # None이 아닌 값만 합산
                        non_none = [c for c in components if c is not None]
                        if non_none:
                            total_debt_values[year] = sum(non_none, Decimal("0"))

                    if total_debt_values:
                        mapped_data[_SA.TOTAL_DEBT] = total_debt_values
                        logger.info(
                            "TOTAL_DEBT 파생 계정 산출 완료: %d개 연도",
                            len(total_debt_values),
                        )
            except Exception as exc:
                msg = f"TOTAL_DEBT 파생 계정 산출 실패: {exc}"
                logger.warning(msg)
                warnings.append(msg)

    def _get_account_values(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        account: StandardAccount,
    ) -> dict[str, Decimal | None]:
        """mapped_data에서 특정 계정의 연도별 값을 반환한다.

        Args:
            mapped_data: 매핑된 데이터.
            account: 조회할 StandardAccount.

        Returns:
            연도별 값 딕셔너리. 계정이 없으면 빈 딕셔너리.
        """
        return mapped_data.get(account, {})

    def _calculate_profitability(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> ProfitabilityMetrics:
        """Step 4a: 수익성 지표를 계산한다."""
        try:
            return calculate_profitability(
                revenue=self._get_account_values(mapped_data, _SA.REVENUE),
                gross_profit=self._get_account_values(mapped_data, _SA.GROSS_PROFIT),
                operating_income=self._get_account_values(mapped_data, _SA.OPERATING_INCOME),
                net_income=self._get_account_values(mapped_data, _SA.NET_INCOME),
                total_assets=self._get_account_values(mapped_data, _SA.TOTAL_ASSETS),
                total_equity=self._get_account_values(mapped_data, _SA.TOTAL_EQUITY),
            )
        except Exception as exc:
            msg = f"수익성 지표 계산 실패: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return ProfitabilityMetrics(
                gross_profit_margin={},
                operating_profit_margin={},
                net_profit_margin={},
                roa={},
                roe={},
            )

    def _calculate_growth(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> GrowthMetrics:
        """Step 4b: 성장성 지표를 계산한다.

        calculate_growth()는 dict[str, dict[str, Decimal]]을 기대하므로
        None 값을 제외한 딕셔너리를 구성한다.
        """
        try:
            metrics: dict[str, dict[str, Decimal]] = {}

            account_metric_map = {
                _SA.REVENUE: "revenue",
                _SA.OPERATING_INCOME: "operating_income",
                _SA.NET_INCOME: "net_income",
                _SA.EBITDA: "ebitda",
            }

            for account, metric_name in account_metric_map.items():
                values = self._get_account_values(mapped_data, account)
                filtered = _filter_none_values(values)
                if filtered:
                    metrics[metric_name] = filtered

            return calculate_growth(metrics)
        except Exception as exc:
            msg = f"성장성 지표 계산 실패: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return GrowthMetrics(yoy={}, cagr_3y={}, cagr_5y={})

    def _calculate_cash_flow(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> CashFlowMetrics:
        """Step 4c: 현금흐름 지표를 계산한다."""
        try:
            oi = self._get_account_values(mapped_data, _SA.OPERATING_INCOME)
            dep = self._get_account_values(mapped_data, _SA.DEPRECIATION)
            amort = self._get_account_values(mapped_data, _SA.AMORTIZATION) or None
            ocf = self._get_account_values(mapped_data, _SA.OPERATING_CASH_FLOW) or None
            capex = self._get_account_values(mapped_data, _SA.CAPEX) or None
            ca = self._get_account_values(mapped_data, _SA.CURRENT_ASSETS) or None
            cl = self._get_account_values(mapped_data, _SA.CURRENT_LIABILITIES) or None
            rev = self._get_account_values(mapped_data, _SA.REVENUE) or None

            return calculate_cash_flow_metrics(
                operating_income=oi,
                depreciation=dep,
                amortization=amort,
                operating_cash_flow=ocf,
                capex=capex,
                current_assets=ca,
                current_liabilities=cl,
                revenue=rev,
            )
        except Exception as exc:
            msg = f"현금흐름 지표 계산 실패: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return CashFlowMetrics(
                ebitda={},
                free_cash_flow={},
                net_working_capital={},
                ebitda_margin={},
            )

    def _calculate_leverage(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        cash_flow: CashFlowMetrics,
        warnings: list[str],
    ) -> LeverageMetrics:
        """Step 4d: 레버리지 지표를 계산한다."""
        try:
            total_liab = self._get_account_values(mapped_data, _SA.TOTAL_LIABILITIES)
            total_eq = self._get_account_values(mapped_data, _SA.TOTAL_EQUITY)
            oi = self._get_account_values(mapped_data, _SA.OPERATING_INCOME)
            ie = self._get_account_values(mapped_data, _SA.INTEREST_EXPENSE)

            # Net Debt/EBITDA에 필요한 데이터
            total_debt = self._get_account_values(mapped_data, _SA.TOTAL_DEBT) or None
            cash = self._get_account_values(mapped_data, _SA.CASH_AND_EQUIVALENTS) or None

            # EBITDA: mapped_data에 있으면 사용, 없으면 cash_flow에서 가져옴
            ebitda_data = self._get_account_values(mapped_data, _SA.EBITDA)
            if not ebitda_data and cash_flow.ebitda:
                ebitda_data = cash_flow.ebitda  # type: ignore[assignment]
            ebitda_for_leverage = ebitda_data or None

            return calculate_leverage(
                total_liabilities=total_liab,
                total_equity=total_eq,
                operating_income=oi,
                interest_expense=ie,
                total_debt=total_debt,
                cash_and_equivalents=cash,
                ebitda=ebitda_for_leverage,
            )
        except Exception as exc:
            msg = f"레버리지 지표 계산 실패: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return LeverageMetrics(
                debt_to_equity={},
                interest_coverage={},
                net_debt_to_ebitda={},
            )

    # -----------------------------------------------------------------------
    # 산업별 지표 계산 (Phase B)
    # -----------------------------------------------------------------------

    _INDUSTRY_CALCULATOR_IDS = {"tech", "manufacturing", "healthcare", "logistics"}

    def _calculate_valuation(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        valuation_config: dict[str, Any],
        warnings: list[str],
    ) -> ValuationMetrics | None:
        """Step 4f: 밸류에이션 지표를 계산한다.

        Args:
            mapped_data: 매핑된 재무 데이터.
            valuation_config: 밸류에이션 설정 딕셔너리.
            warnings: 경고를 수집할 리스트.

        Returns:
            ValuationMetrics 또는 None (실패 시).
        """
        try:
            return calculate_valuation_metrics(
                ev=valuation_config.get("ev"),
                ebitda=valuation_config.get("ebitda"),
                equity_value=valuation_config.get("equity_value"),
                net_income=valuation_config.get("net_income"),
                revenue=valuation_config.get("revenue"),
                irr_scenarios_config=valuation_config.get("irr_scenarios"),
                moic_scenarios_config=valuation_config.get("moic_scenarios"),
                exit_multiples=valuation_config.get("exit_multiples"),
                ebitda_at_exit=valuation_config.get("ebitda_at_exit"),
                entry_equity=valuation_config.get("entry_equity"),
                holding_period=valuation_config.get("holding_period"),
                net_debt_at_exit=valuation_config.get("net_debt_at_exit"),
            )
        except Exception as exc:
            msg = f"밸류에이션 지표 계산 실패: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return None

    def _calculate_industry_metrics(
        self,
        industry_id: str,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        industry_data: dict[str, dict[str, Decimal | None]],
        profitability: ProfitabilityMetrics,
        growth: GrowthMetrics,
        warnings: list[str],
    ) -> IndustryMetrics | None:
        """Step 4e: 산업별 재무 지표를 계산한다.

        Args:
            industry_id: 산업 식별자.
            mapped_data: 매핑된 재무 데이터.
            industry_data: 산업 고유 입력 데이터.
            profitability: 이미 계산된 수익성 지표 (Rule of 40용).
            growth: 이미 계산된 성장성 지표 (Rule of 40용).
            warnings: 경고를 수집할 리스트.

        Returns:
            산업별 지표 또는 None (미등록/실패 시).
        """
        if industry_id not in self._INDUSTRY_CALCULATOR_IDS:
            msg = f"산업별 지표 계산기 미등록: '{industry_id}'"
            logger.info(msg)
            warnings.append(msg)
            return None

        try:
            if industry_id == "tech":
                return self._calculate_saas(
                    mapped_data, industry_data, profitability, growth, warnings
                )
            elif industry_id == "manufacturing":
                return self._calculate_manufacturing(
                    mapped_data, industry_data, warnings
                )
            elif industry_id == "healthcare":
                return self._calculate_healthcare(
                    mapped_data, industry_data, warnings
                )
            elif industry_id == "logistics":
                return self._calculate_logistics(
                    mapped_data, industry_data, warnings
                )
        except Exception as exc:
            msg = f"산업별 지표 계산 실패 ({industry_id}): {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return None

        return None  # pragma: no cover

    def _calculate_saas(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        industry_data: dict[str, dict[str, Decimal | None]],
        profitability: ProfitabilityMetrics,
        growth: GrowthMetrics,
        warnings: list[str],
    ) -> IndustryMetrics:
        """SaaS 산업별 지표를 계산한다."""
        revenue = self._get_account_values(mapped_data, _SA.REVENUE)

        # Rule of 40용: 이미 계산된 영업이익률과 매출 성장률 활용
        operating_margin = profitability.operating_profit_margin or None
        revenue_growth = growth.yoy.get("revenue") if growth.yoy else None

        return calculate_saas_metrics(
            revenue=revenue,
            subscription_revenue=industry_data.get("subscription_revenue", {}),
            beginning_arr=industry_data.get("beginning_arr"),
            expansion_revenue=industry_data.get("expansion_revenue"),
            contraction_revenue=industry_data.get("contraction_revenue"),
            churned_revenue=industry_data.get("churned_revenue"),
            sales_marketing_cost=industry_data.get("sales_marketing_cost"),
            new_customers=industry_data.get("new_customers"),
            arpu=industry_data.get("arpu"),
            gross_margin_pct=industry_data.get("gross_margin_pct"),
            revenue_growth_rate=revenue_growth,
            operating_margin=operating_margin,
        )

    def _calculate_manufacturing(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        industry_data: dict[str, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> IndustryMetrics:
        """제조업 산업별 지표를 계산한다."""
        return calculate_manufacturing_metrics(
            revenue=self._get_account_values(mapped_data, _SA.REVENUE),
            cogs=self._get_account_values(mapped_data, _SA.COST_OF_GOODS_SOLD),
            capex=self._get_account_values(mapped_data, _SA.CAPEX),
            avg_inventory=self._get_account_values(
                mapped_data, _SA.INVENTORIES
            ) or None,
            availability=industry_data.get("availability"),
            performance=industry_data.get("performance"),
            quality=industry_data.get("quality"),
            actual_output=industry_data.get("actual_output"),
            max_capacity=industry_data.get("max_capacity"),
            good_units=industry_data.get("good_units"),
            total_units=industry_data.get("total_units"),
        )

    def _calculate_healthcare(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        industry_data: dict[str, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> IndustryMetrics:
        """헬스케어/바이오 산업별 지표를 계산한다."""
        # discount_rate 추출 (스칼라 값)
        discount_rate: Decimal | None = None
        dr_dict = industry_data.get("discount_rate")
        if dr_dict:
            # 첫 번째 값을 스칼라로 사용
            first_val = next(iter(dr_dict.values()), None)
            if first_val is not None:
                discount_rate = first_val

        # current_year 추출
        current_year: int | None = None
        cy_dict = industry_data.get("current_year")
        if cy_dict:
            first_val = next(iter(cy_dict.values()), None)
            if first_val is not None:
                current_year = int(first_val)

        return calculate_healthcare_metrics(
            revenue=self._get_account_values(mapped_data, _SA.REVENUE),
            rd_expense=self._get_account_values(
                mapped_data, _SA.RESEARCH_DEVELOPMENT
            ) or None,
            expected_cash_flows=industry_data.get("expected_cash_flows"),
            success_probabilities=industry_data.get("success_probabilities"),
            discount_rate=discount_rate,
            phase_data=industry_data.get("phase_data"),
            patent_expiry_years=industry_data.get("patent_expiry_years"),
            current_year=current_year,
        )

    def _calculate_logistics(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        industry_data: dict[str, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> IndustryMetrics:
        """물류/운송 산업별 지표를 계산한다."""
        return calculate_logistics_metrics(
            revenue=self._get_account_values(mapped_data, _SA.REVENUE),
            on_time_count=industry_data.get("on_time_count"),
            total_deliveries=industry_data.get("total_deliveries"),
            active_fleet=industry_data.get("active_fleet"),
            total_fleet=industry_data.get("total_fleet"),
            transport_revenue=industry_data.get("transport_revenue"),
            total_tonkm=industry_data.get("total_tonkm"),
            operating_cost=industry_data.get("operating_cost"),
        )

    def _validate_balance(
        self,
        mapped_data: dict[StandardAccount, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> BalanceCheckReport | None:
        """Step 5a: 재무상태표 균형 검증을 실행한다."""
        try:
            total_assets = self._get_account_values(mapped_data, _SA.TOTAL_ASSETS)
            total_liab = self._get_account_values(mapped_data, _SA.TOTAL_LIABILITIES)
            total_eq = self._get_account_values(mapped_data, _SA.TOTAL_EQUITY)

            if not total_assets or not total_liab or not total_eq:
                msg = "재무상태표 균형 검증 건너뜀: 필수 데이터(총자산/총부채/총자본) 부족"
                logger.info(msg)
                warnings.append(msg)
                return None

            report = self._balance_checker.check(
                total_assets=total_assets,
                total_liabilities=total_liab,
                total_equity=total_eq,
            )
            warnings.extend(report.warnings)
            return report
        except Exception as exc:
            msg = f"재무상태표 균형 검증 실패: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return None

    def _validate_consistency(
        self,
        normalized_data: dict[str, dict[str, Decimal | None]],
        warnings: list[str],
    ) -> ConsistencyReport | None:
        """Step 5b: 다기간 일관성 검증을 실행한다.

        ConsistencyChecker는 한글 계정명 기반으로 동작하므로
        normalized_data(매핑 전 데이터)를 사용한다.
        """
        try:
            if not normalized_data:
                return None

            report = self._consistency_checker.check(normalized_data)
            warnings.extend(report.warnings)
            return report
        except Exception as exc:
            msg = f"일관성 검증 실패: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return None
