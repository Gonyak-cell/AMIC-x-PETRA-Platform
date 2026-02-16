"""Financial Engine -- 통화 변환기 (T-F05).

외화(USD, EUR, JPY, CNY, GBP 등) 금액을 KRW로 변환합니다.
API 기반 실시간 환율 조회와 정적 폴백 환율을 모두 지원합니다.

> 마지막 수정: 2026-02-09 16:02:25
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from src.financial_engine.exceptions import CurrencyConversionError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 기본 폴백 환율 (2024년 기준 근사치, KRW 기준)
# ---------------------------------------------------------------------------

DEFAULT_FALLBACK_RATES: dict[str, Decimal] = {
    "USD_KRW": Decimal("1350"),
    "EUR_KRW": Decimal("1450"),
    "JPY_KRW": Decimal("9"),
    "CNY_KRW": Decimal("185"),
    "GBP_KRW": Decimal("1700"),
}


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExchangeRate:
    """단일 환율 정보를 표현하는 불변 데이터 클래스.

    Attributes:
        from_currency: 원본 통화 코드 (예: ``"USD"``).
        to_currency: 대상 통화 코드 (예: ``"KRW"``).
        rate: 환율 (1 ``from_currency`` = ``rate`` ``to_currency``).
        source: 환율 출처. ``"api"`` 또는 ``"static"``.
        as_of_date: 환율 기준일 (ISO 8601 문자열, 예: ``"2024-06-01"``).
    """

    from_currency: str
    to_currency: str
    rate: Decimal
    source: str
    as_of_date: str


@dataclass
class CurrencyConfig:
    """통화 변환기 설정.

    ``fallback_rates`` 는 뮤터블 dict이므로 ``frozen=True`` 를 사용하지 않고
    ``field(default_factory=...)`` 로 기본값을 생성합니다.

    Attributes:
        api_url: 환율 API 엔드포인트 URL. 비어 있으면 API 조회를 건너뜁니다.
        api_key: 환율 API 인증 키.
        timeout: API 요청 타임아웃(초).
        fallback_rates: 정적 폴백 환율 딕셔너리. 키 형식: ``"USD_KRW"``.
    """

    api_url: str = ""
    api_key: str = ""
    timeout: float = 10.0
    fallback_rates: dict[str, Decimal] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# CurrencyConverter
# ---------------------------------------------------------------------------


class CurrencyConverter:
    """외화 금액을 KRW로 변환하는 통화 변환기.

    사용 흐름:
        1. ``CurrencyConfig`` 를 생성하여 API 또는 폴백 환율을 설정합니다.
        2. ``get_exchange_rate()`` 로 환율을 조회합니다 (비동기).
        3. ``convert()`` 로 실제 금액을 변환합니다.

    동일 통화 변환(예: KRW -> KRW)은 패스스루로 원본 금액을 그대로 반환합니다.

    Examples:
        >>> from decimal import Decimal
        >>> converter = CurrencyConverter()
        >>> converter.convert(Decimal("1000"), "USD", "KRW")
        Decimal('1350000')
    """

    def __init__(self, config: CurrencyConfig | None = None) -> None:
        """CurrencyConverter 초기화.

        Args:
            config: 통화 변환 설정. ``None`` 이면 기본 폴백 환율만 사용합니다.
        """
        if config is None:
            config = CurrencyConfig()

        self._config = config

        # 폴백 환율: 사용자 지정 값이 있으면 기본값 위에 덮어씌움
        self._fallback_rates: dict[str, Decimal] = {
            **DEFAULT_FALLBACK_RATES,
            **self._config.fallback_rates,
        }

    # ------------------------------------------------------------------
    # 환율 조회
    # ------------------------------------------------------------------

    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate:
        """환율을 조회합니다.

        API URL이 설정되어 있으면 API를 먼저 시도하고, 실패 시 정적 폴백
        환율로 전환합니다. API가 설정되지 않은 경우 정적 폴백만 사용합니다.

        Args:
            from_currency: 원본 통화 코드 (예: ``"USD"``).
            to_currency: 대상 통화 코드 (예: ``"KRW"``).

        Returns:
            조회된 환율 정보.

        Raises:
            CurrencyConversionError: API와 폴백 모두에서 환율을 찾을 수 없을 때.
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # 동일 통화: 환율 1
        if from_currency == to_currency:
            return ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=Decimal("1"),
                source="static",
                as_of_date=date.today().isoformat(),
            )

        # API 조회 시도
        if self._config.api_url:
            rate = await self._fetch_rate_from_api(from_currency, to_currency)
            if rate is not None:
                return rate

        # 정적 폴백
        return self._get_static_rate(from_currency, to_currency)

    # ------------------------------------------------------------------
    # 금액 변환
    # ------------------------------------------------------------------

    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        *,
        rate: ExchangeRate | None = None,
    ) -> Decimal:
        """금액을 변환합니다.

        동일 통화인 경우 원본 금액을 그대로 반환합니다.
        ``rate`` 가 제공되면 해당 환율을 사용하고, 그렇지 않으면 정적 폴백
        환율을 사용합니다. 비동기 API 환율이 필요한 경우 먼저
        ``get_exchange_rate()`` 를 호출하여 ``rate`` 를 전달하십시오.

        Args:
            amount: 변환할 금액.
            from_currency: 원본 통화 코드.
            to_currency: 대상 통화 코드.
            rate: 미리 조회한 환율 정보. ``None`` 이면 정적 폴백을 사용합니다.

        Returns:
            변환된 금액.

        Raises:
            CurrencyConversionError: 환율을 찾을 수 없을 때.
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # 동일 통화: 패스스루
        if from_currency == to_currency:
            return amount

        if rate is not None:
            return amount * rate.rate

        # 정적 폴백에서 환율 가져오기
        static_rate = self._get_static_rate(from_currency, to_currency)
        return amount * static_rate.rate

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------

    async def _fetch_rate_from_api(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate | None:
        """외부 API에서 환율을 조회합니다.

        API 호출 실패 시 ``None`` 을 반환하여 폴백으로 전환할 수 있도록 합니다.

        Args:
            from_currency: 원본 통화 코드.
            to_currency: 대상 통화 코드.

        Returns:
            조회 성공 시 ``ExchangeRate``, 실패 시 ``None``.
        """
        try:
            import aiohttp  # noqa: WPS433 (조건부 임포트)

            url = self._config.api_url
            params: dict[str, Any] = {
                "from": from_currency,
                "to": to_currency,
            }
            headers: dict[str, str] = {}
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self._config.timeout),
                ) as response:
                    if response.status != 200:
                        logger.warning(
                            "환율 API 응답 오류: status=%d, from=%s, to=%s",
                            response.status,
                            from_currency,
                            to_currency,
                        )
                        return None

                    data = await response.json()
                    rate_value = data.get("rate")
                    if rate_value is None:
                        logger.warning(
                            "환율 API 응답에 'rate' 필드 없음: from=%s, to=%s",
                            from_currency,
                            to_currency,
                        )
                        return None

                    return ExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=Decimal(str(rate_value)),
                        source="api",
                        as_of_date=data.get(
                            "date", date.today().isoformat()
                        ),
                    )

        except ImportError:
            logger.warning(
                "aiohttp가 설치되지 않아 API 환율 조회를 건너뜁니다."
            )
            return None
        except Exception:
            logger.warning(
                "환율 API 호출 실패: from=%s, to=%s",
                from_currency,
                to_currency,
                exc_info=True,
            )
            return None

    def _get_static_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate:
        """정적 폴백 환율을 조회합니다.

        정방향(``from_to``) 키를 먼저 찾고, 없으면 역방향(``to_from``) 키의
        역수를 계산합니다.

        Args:
            from_currency: 원본 통화 코드.
            to_currency: 대상 통화 코드.

        Returns:
            정적 환율 정보.

        Raises:
            CurrencyConversionError: 정적 폴백에서도 환율을 찾을 수 없을 때.
        """
        key = f"{from_currency}_{to_currency}"
        reverse_key = f"{to_currency}_{from_currency}"

        # 정방향 키 조회
        if key in self._fallback_rates:
            return ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=self._fallback_rates[key],
                source="static",
                as_of_date=date.today().isoformat(),
            )

        # 역방향 키 조회 (역수 계산)
        if reverse_key in self._fallback_rates:
            reverse_rate = self._fallback_rates[reverse_key]
            if reverse_rate == Decimal("0"):
                raise CurrencyConversionError(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    reason="역방향 환율이 0이므로 역수를 계산할 수 없습니다.",
                )
            return ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=Decimal("1") / reverse_rate,
                source="static",
                as_of_date=date.today().isoformat(),
            )

        raise CurrencyConversionError(
            from_currency=from_currency,
            to_currency=to_currency,
            reason=(
                f"'{key}' 또는 '{reverse_key}'에 해당하는 "
                f"폴백 환율이 존재하지 않습니다."
            ),
        )
