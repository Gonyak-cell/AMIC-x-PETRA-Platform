"""Financial Engine -- Valuation Calculator (Phase D1).

밸류에이션 지표를 계산합니다: EV/EBITDA, P/E, EV/Revenue, IRR, MOIC, Exit 분석.

> 마지막 수정: 2026-02-11 22:00:00
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터클래스
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IRRScenario:
    """개별 IRR 시나리오 결과.

    Attributes:
        entry_multiple: 진입 멀티플 (배수).
        exit_multiple: 엑싯 멀티플 (배수).
        holding_period: 보유 기간 (년).
        irr: 내부수익률 (%, 예: 25.3).
        entry_ev: 진입 EV.
        exit_ev: 엑싯 EV.
    """

    entry_multiple: float
    exit_multiple: float
    holding_period: int
    irr: float
    entry_ev: Decimal
    exit_ev: Decimal


@dataclass(frozen=True)
class ExitAnalysis:
    """엑싯 분석 결과.

    Attributes:
        exit_multiple: 엑싯 멀티플 (배수).
        exit_ev: 엑싯 Enterprise Value.
        exit_equity: 엑싯 Equity Value.
        moic: 투자수익배수 (MOIC).
        irr: 내부수익률 (%).
    """

    exit_multiple: float
    exit_ev: Decimal
    exit_equity: Decimal
    moic: float
    irr: float


@dataclass(frozen=True)
class ValuationMetrics:
    """밸류에이션 지표 데이터 클래스.

    각 필드는 ``{연도 또는 시나리오명: 값}`` 형태의 딕셔너리입니다.
    데이터가 없는 지표는 빈 딕셔너리로 초기화됩니다.

    Attributes:
        ev_ebitda: 연도별 EV/EBITDA 배수 ``{연도: float}``.
        pe_ratio: 연도별 P/E Ratio ``{연도: float}``.
        ev_revenue: 연도별 EV/Revenue 배수 ``{연도: float}``.
        irr_scenarios: 시나리오별 IRR ``{시나리오명: IRRScenario}``.
        moic_scenarios: 시나리오별 MOIC ``{시나리오명: float}``.
        exit_analysis: 엑싯 멀티플별 분석 ``{레이블: ExitAnalysis}``.
    """

    ev_ebitda: dict[str, float]
    pe_ratio: dict[str, float]
    ev_revenue: dict[str, float]
    irr_scenarios: dict[str, IRRScenario]
    moic_scenarios: dict[str, float]
    exit_analysis: dict[str, ExitAnalysis]


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------


def _compute_ratio(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> float | None:
    """분자/분모로 비율을 계산한다 (배수).

    Args:
        numerator: 분자 값.
        denominator: 분모 값.

    Returns:
        비율(배수) 값. 분자·분모가 ``None``이거나 분모가 0이면 ``None``.
    """
    if numerator is None or denominator is None:
        return None
    if denominator == Decimal("0"):
        return None
    return float(numerator / denominator)


# ---------------------------------------------------------------------------
# 배수 지표 계산
# ---------------------------------------------------------------------------


def calculate_ev_ebitda(
    ev: dict[str, Decimal | None],
    ebitda: dict[str, Decimal | None],
) -> dict[str, float]:
    """연도별 EV/EBITDA 멀티플을 계산한다.

    EV/EBITDA = Enterprise Value / EBITDA (배수).
    분모(EBITDA)가 0·``None``이거나 분자(EV)가 ``None``이면 해당 연도는 제외.

    Args:
        ev: 연도별 Enterprise Value ``{연도: Decimal | None}``.
        ebitda: 연도별 EBITDA ``{연도: Decimal | None}``.

    Returns:
        연도별 EV/EBITDA 딕셔너리.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_ev_ebitda(
        ...     {"2023": Decimal("350000")},
        ...     {"2023": Decimal("35000")},
        ... )
        {'2023': 10.0}
    """
    result: dict[str, float] = {}
    for year in ev:
        ratio = _compute_ratio(ev.get(year), ebitda.get(year))
        if ratio is not None:
            result[year] = round(ratio, 2)
    return result


def calculate_pe_ratio(
    equity_value: dict[str, Decimal | None],
    net_income: dict[str, Decimal | None],
) -> dict[str, float]:
    """연도별 P/E Ratio를 계산한다.

    P/E = Equity Value / Net Income (배수).

    Args:
        equity_value: 연도별 Equity Value ``{연도: Decimal | None}``.
        net_income: 연도별 당기순이익 ``{연도: Decimal | None}``.

    Returns:
        연도별 P/E Ratio 딕셔너리.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_pe_ratio(
        ...     {"2023": Decimal("200000")},
        ...     {"2023": Decimal("20000")},
        ... )
        {'2023': 10.0}
    """
    result: dict[str, float] = {}
    for year in equity_value:
        ratio = _compute_ratio(equity_value.get(year), net_income.get(year))
        if ratio is not None:
            result[year] = round(ratio, 2)
    return result


def calculate_ev_revenue(
    ev: dict[str, Decimal | None],
    revenue: dict[str, Decimal | None],
) -> dict[str, float]:
    """연도별 EV/Revenue 멀티플을 계산한다.

    EV/Revenue = Enterprise Value / Revenue (배수).

    Args:
        ev: 연도별 Enterprise Value ``{연도: Decimal | None}``.
        revenue: 연도별 매출액 ``{연도: Decimal | None}``.

    Returns:
        연도별 EV/Revenue 딕셔너리.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_ev_revenue(
        ...     {"2023": Decimal("350000")},
        ...     {"2023": Decimal("175000")},
        ... )
        {'2023': 2.0}
    """
    result: dict[str, float] = {}
    for year in ev:
        ratio = _compute_ratio(ev.get(year), revenue.get(year))
        if ratio is not None:
            result[year] = round(ratio, 2)
    return result


# ---------------------------------------------------------------------------
# IRR 솔버 (Newton-Raphson, 외부 의존성 없음)
# ---------------------------------------------------------------------------


def _solve_irr(
    cash_flows: list[float],
    *,
    guess: float = 0.10,
    max_iterations: int = 200,
    tolerance: float = 1e-8,
) -> float | None:
    """Newton-Raphson 방법으로 IRR을 구한다.

    NPV(r) = sum(CF_t / (1+r)^t) = 0 을 만족하는 r을 찾는다.
    수렴하지 않으면 ``None``을 반환한다.

    Args:
        cash_flows: 현금흐름 리스트 ``[CF_0, CF_1, ..., CF_n]``.
        guess: 초기 추정값 (기본 10%).
        max_iterations: 최대 반복 횟수.
        tolerance: 수렴 허용 오차.

    Returns:
        IRR (비율, 예: 0.25 = 25%). 수렴 실패 시 ``None``.
    """
    if not cash_flows or len(cash_flows) < 2:
        return None

    rate = guess
    for _ in range(max_iterations):
        npv = 0.0
        d_npv = 0.0
        for t, cf in enumerate(cash_flows):
            denom = (1.0 + rate) ** t
            if denom == 0.0:
                return None
            npv += cf / denom
            if t > 0:
                d_npv -= t * cf / ((1.0 + rate) ** (t + 1))

        if abs(npv) < tolerance:
            return rate

        if abs(d_npv) < 1e-15:
            break

        rate = rate - npv / d_npv

        # 발산 방지: rate가 비정상적으로 큰 경우
        if rate < -0.999 or rate > 100.0:
            break

    # 첫 번째 시도 실패 시 대체 초기값으로 재시도
    if guess != 0.0:
        return _solve_irr(
            cash_flows, guess=0.0, max_iterations=max_iterations, tolerance=tolerance
        )
    return None


# ---------------------------------------------------------------------------
# IRR / MOIC 개별 계산
# ---------------------------------------------------------------------------


def calculate_irr(
    entry_ev: Decimal,
    exit_ev: Decimal,
    holding_period: int,
    annual_cash_flows: list[Decimal] | None = None,
) -> float | None:
    """단일 시나리오의 IRR을 계산한다.

    현금흐름: [-entry_ev] + annual_cash_flows + [exit_ev + 마지막 연간CF].
    연간 현금흐름이 없으면 [-entry_ev, 0, ..., 0, exit_ev]로 처리.
    결과는 백분율(%).

    Args:
        entry_ev: 진입 Enterprise Value.
        exit_ev: 엑싯 Enterprise Value.
        holding_period: 보유 기간 (년, 1 이상).
        annual_cash_flows: 연간 현금흐름 리스트 (보유 기간과 길이 동일).
            ``None``이면 중간 현금흐름 없음.

    Returns:
        IRR(%) 또는 수렴 실패 시 ``None``.

    Examples:
        >>> from decimal import Decimal
        >>> irr = calculate_irr(Decimal("100000"), Decimal("200000"), 5)
        >>> irr is not None
        True
    """
    if entry_ev <= 0 or holding_period < 1:
        logger.debug(
            "IRR 계산 건너뜀: entry_ev=%s, holding_period=%s", entry_ev, holding_period
        )
        return None

    cfs: list[float] = [float(-entry_ev)]

    if annual_cash_flows:
        for i, cf in enumerate(annual_cash_flows):
            if i == holding_period - 1:
                # 마지막 해: 연간CF + 엑싯
                cfs.append(float(cf + exit_ev))
            else:
                cfs.append(float(cf))
        # annual_cash_flows 길이가 holding_period보다 짧으면 나머지 0으로 채움
        remaining = holding_period - len(annual_cash_flows)
        if remaining > 0:
            for i in range(remaining):
                if len(cfs) == holding_period:
                    cfs.append(float(exit_ev))
                else:
                    cfs.append(0.0)
    else:
        for _ in range(holding_period - 1):
            cfs.append(0.0)
        cfs.append(float(exit_ev))

    rate = _solve_irr(cfs)
    if rate is None:
        return None
    return round(rate * 100, 2)


def calculate_moic(
    exit_equity: Decimal,
    entry_equity: Decimal,
) -> float | None:
    """MOIC(투자수익배수)를 계산한다.

    MOIC = exit_equity / entry_equity.

    Args:
        exit_equity: 엑싯 시 Equity Value.
        entry_equity: 진입 시 Equity Value.

    Returns:
        MOIC(배수). entry_equity가 0 이하이면 ``None``.

    Examples:
        >>> from decimal import Decimal
        >>> calculate_moic(Decimal("250000"), Decimal("100000"))
        2.5
    """
    if entry_equity <= 0:
        logger.debug("MOIC 계산 건너뜀: entry_equity=%s", entry_equity)
        return None
    return round(float(exit_equity / entry_equity), 2)


# ---------------------------------------------------------------------------
# 시나리오 일괄 계산
# ---------------------------------------------------------------------------


def calculate_irr_scenarios(
    scenarios: dict[str, dict[str, Any]],
) -> dict[str, IRRScenario]:
    """다수 시나리오의 IRR을 일괄 계산한다.

    Args:
        scenarios: 시나리오 설정 딕셔너리::

            {
                "base": {
                    "entry_multiple": 8.0,
                    "exit_multiple": 10.0,
                    "holding_period": 5,
                    "ebitda_at_entry": Decimal("35000"),
                    "ebitda_at_exit": Decimal("50000"),
                    "annual_cash_flows": [...] | None,
                    "net_debt_at_entry": Decimal("40000") | None,
                    "net_debt_at_exit": Decimal("30000") | None,
                },
                ...
            }

    Returns:
        시나리오별 IRRScenario 딕셔너리. IRR 계산 실패 시 해당 시나리오 제외.
    """
    result: dict[str, IRRScenario] = {}

    for name, cfg in scenarios.items():
        entry_multiple = cfg.get("entry_multiple")
        exit_multiple = cfg.get("exit_multiple")
        holding_period = cfg.get("holding_period")
        ebitda_at_entry = cfg.get("ebitda_at_entry")
        ebitda_at_exit = cfg.get("ebitda_at_exit")

        if any(
            v is None
            for v in [
                entry_multiple,
                exit_multiple,
                holding_period,
                ebitda_at_entry,
                ebitda_at_exit,
            ]
        ):
            logger.debug("IRR 시나리오 '%s' 건너뜀: 필수 값 누락", name)
            continue

        entry_ev = Decimal(str(entry_multiple)) * ebitda_at_entry
        exit_ev = Decimal(str(exit_multiple)) * ebitda_at_exit
        annual_cfs = cfg.get("annual_cash_flows")

        irr = calculate_irr(entry_ev, exit_ev, holding_period, annual_cfs)
        if irr is None:
            logger.warning("IRR 시나리오 '%s' 수렴 실패", name)
            continue

        result[name] = IRRScenario(
            entry_multiple=float(entry_multiple),
            exit_multiple=float(exit_multiple),
            holding_period=int(holding_period),
            irr=irr,
            entry_ev=entry_ev,
            exit_ev=exit_ev,
        )

    return result


def calculate_moic_scenarios(
    scenarios: dict[str, dict[str, Decimal]],
) -> dict[str, float]:
    """다수 시나리오의 MOIC를 일괄 계산한다.

    Args:
        scenarios: ``{"base": {"exit_equity": Decimal(...), "entry_equity": Decimal(...)}, ...}``

    Returns:
        시나리오별 MOIC 딕셔너리. 계산 실패 시 해당 시나리오 제외.
    """
    result: dict[str, float] = {}

    for name, cfg in scenarios.items():
        exit_eq = cfg.get("exit_equity")
        entry_eq = cfg.get("entry_equity")

        if exit_eq is None or entry_eq is None:
            logger.debug("MOIC 시나리오 '%s' 건너뜀: 값 누락", name)
            continue

        moic = calculate_moic(exit_eq, entry_eq)
        if moic is not None:
            result[name] = moic

    return result


# ---------------------------------------------------------------------------
# Exit 분석
# ---------------------------------------------------------------------------


def calculate_exit_analysis(
    exit_multiples: list[float],
    ebitda_at_exit: Decimal,
    entry_equity: Decimal,
    holding_period: int,
    net_debt_at_exit: Decimal | None = None,
) -> dict[str, ExitAnalysis]:
    """여러 엑싯 멀티플에 대한 분석을 수행한다.

    각 멀티플에 대해:
    - exit_ev = multiple * ebitda_at_exit
    - exit_equity = exit_ev - net_debt_at_exit (net_debt가 없으면 exit_ev)
    - moic = exit_equity / entry_equity
    - irr = IRR 계산

    Args:
        exit_multiples: 분석할 엑싯 멀티플 리스트 (예: [6.0, 8.0, 10.0, 12.0]).
        ebitda_at_exit: 엑싯 시점 예상 EBITDA.
        entry_equity: 진입 시 투자금 (Equity Value).
        holding_period: 보유 기간 (년).
        net_debt_at_exit: 엑싯 시점 순부채. ``None``이면 0으로 처리.

    Returns:
        멀티플 레이블별 ExitAnalysis 딕셔너리 (예: ``{"8.0x": ExitAnalysis(...)}``)
    """
    result: dict[str, ExitAnalysis] = {}
    net_debt = net_debt_at_exit or Decimal("0")

    if entry_equity <= 0 or holding_period < 1:
        logger.debug(
            "Exit 분석 건너뜀: entry_equity=%s, holding_period=%s",
            entry_equity,
            holding_period,
        )
        return result

    for mult in exit_multiples:
        exit_ev = Decimal(str(mult)) * ebitda_at_exit
        exit_equity = exit_ev - net_debt

        moic = calculate_moic(exit_equity, entry_equity)
        if moic is None:
            continue

        irr = calculate_irr(entry_equity, exit_equity, holding_period)
        if irr is None:
            irr = 0.0

        label = f"{mult}x"
        result[label] = ExitAnalysis(
            exit_multiple=mult,
            exit_ev=exit_ev,
            exit_equity=exit_equity,
            moic=moic,
            irr=irr,
        )

    return result


# ---------------------------------------------------------------------------
# 통합 계산 함수
# ---------------------------------------------------------------------------


def calculate_valuation_metrics(
    *,
    ev: dict[str, Decimal | None] | None = None,
    ebitda: dict[str, Decimal | None] | None = None,
    equity_value: dict[str, Decimal | None] | None = None,
    net_income: dict[str, Decimal | None] | None = None,
    revenue: dict[str, Decimal | None] | None = None,
    irr_scenarios_config: dict[str, dict[str, Any]] | None = None,
    moic_scenarios_config: dict[str, dict[str, Decimal]] | None = None,
    exit_multiples: list[float] | None = None,
    ebitda_at_exit: Decimal | None = None,
    entry_equity: Decimal | None = None,
    holding_period: int | None = None,
    net_debt_at_exit: Decimal | None = None,
) -> ValuationMetrics:
    """밸류에이션 지표를 일괄 계산한다.

    모든 입력은 선택적이다. 데이터가 없는 지표는 빈 딕셔너리로 반환된다.

    Args:
        ev: 연도별 Enterprise Value.
        ebitda: 연도별 EBITDA.
        equity_value: 연도별 Equity Value.
        net_income: 연도별 당기순이익.
        revenue: 연도별 매출액.
        irr_scenarios_config: IRR 시나리오 설정.
        moic_scenarios_config: MOIC 시나리오 설정.
        exit_multiples: 엑싯 멀티플 리스트.
        ebitda_at_exit: 엑싯 시점 EBITDA.
        entry_equity: 진입 Equity.
        holding_period: 보유 기간.
        net_debt_at_exit: 엑싯 시점 순부채.

    Returns:
        ValuationMetrics: 계산된 밸류에이션 지표.
    """
    # 배수 지표
    ev_ebitda = calculate_ev_ebitda(ev, ebitda) if ev and ebitda else {}
    pe = (
        calculate_pe_ratio(equity_value, net_income)
        if equity_value and net_income
        else {}
    )
    ev_rev = calculate_ev_revenue(ev, revenue) if ev and revenue else {}

    # IRR 시나리오
    irr_scens = (
        calculate_irr_scenarios(irr_scenarios_config) if irr_scenarios_config else {}
    )

    # MOIC 시나리오
    moic_scens = (
        calculate_moic_scenarios(moic_scenarios_config) if moic_scenarios_config else {}
    )

    # Exit 분석
    exit_anal: dict[str, ExitAnalysis] = {}
    if (
        exit_multiples
        and ebitda_at_exit is not None
        and entry_equity is not None
        and holding_period is not None
    ):
        exit_anal = calculate_exit_analysis(
            exit_multiples,
            ebitda_at_exit,
            entry_equity,
            holding_period,
            net_debt_at_exit,
        )

    return ValuationMetrics(
        ev_ebitda=ev_ebitda,
        pe_ratio=pe,
        ev_revenue=ev_rev,
        irr_scenarios=irr_scens,
        moic_scenarios=moic_scens,
        exit_analysis=exit_anal,
    )
