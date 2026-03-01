"""한글 계정명 → 표준 계정 코드 3단계 매핑 엔진 (T-F03).

> 마지막 수정: 2026-02-09 16:16:30

DART 전자공시 데이터에서 추출한 한글 계정과목명을 표준 계정 코드(StandardAccount)로
변환하는 3단계 매핑 엔진을 구현한다.

매칭 단계:
  1. **정확 일치** — O(1) dict lookup (KOREAN_ACCOUNT_MAP + custom_mappings)
  2. **퍼지 매칭** — rapidfuzz.process.extractOne (score_cutoff 기반)
  3. **매핑 실패** — unmapped_accounts 기록 + 경고 로그

우선순위: custom_mappings > _runtime_synonyms > KOREAN_ACCOUNT_MAP (base)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from src.financial_engine.exceptions import (
    AccountNotFoundError,
)
from src.financial_engine.mapper.chart_of_accounts import StandardAccount
from src.financial_engine.mapper.korean_accounts import KOREAN_ACCOUNT_MAP

# ---------------------------------------------------------------------------
# rapidfuzz 선택적 임포트
# ---------------------------------------------------------------------------

_RAPIDFUZZ_AVAILABLE: bool = False
try:
    from rapidfuzz import fuzz, process  # noqa: F401

    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터클래스
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountMapping:
    """단일 계정 매핑 결과.

    Attributes:
        original_name: 원본 한글 계정명.
        standard_code: 매핑된 표준 계정 코드.
        confidence: 매칭 신뢰도 (0.0 ~ 1.0). 정확 일치 시 1.0.
        match_type: 매칭 유형 ("exact" | "fuzzy" | "custom").
    """

    original_name: str
    standard_code: StandardAccount
    confidence: float
    match_type: str


@dataclass
class MappingConfig:
    """매핑 설정.

    Attributes:
        fuzzy_threshold: rapidfuzz 퍼지 매칭 최소 점수 (0~100).
        strict_mode: True이면 매핑 실패 시 AccountNotFoundError 발생.
        custom_mappings: 사용자 정의 한글명 → StandardAccount 매핑.
    """

    fuzzy_threshold: int = 80
    strict_mode: bool = False
    custom_mappings: dict[str, StandardAccount] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# AccountMapper
# ---------------------------------------------------------------------------


class AccountMapper:
    """한글 계정명을 StandardAccount로 변환하는 3단계 매핑 엔진.

    매칭 우선순위:
      1. custom_mappings (사용자 정의, 최우선)
      2. _runtime_synonyms (런타임 추가 동의어)
      3. KOREAN_ACCOUNT_MAP (기본 사전, 376+ 엔트리)

    Examples:
        >>> mapper = AccountMapper()
        >>> result = mapper.map("매출액")
        >>> result.standard_code
        <StandardAccount.REVENUE: 'IS_REVENUE'>
        >>> result.confidence
        1.0
    """

    def __init__(self, config: MappingConfig | None = None) -> None:
        """매퍼를 초기화한다.

        Args:
            config: 매핑 설정. None이면 기본 MappingConfig 사용.
        """
        self._config = config or MappingConfig()
        self._runtime_synonyms: dict[str, StandardAccount] = {}
        self._unmapped: list[str] = []
        self._warnings: list[str] = []

        # _combined_map 구축: base < runtime < custom (뒤가 높은 우선순위)
        self._combined_map: dict[str, StandardAccount] = {}
        self._rebuild_combined_map()

    def _rebuild_combined_map(self) -> None:
        """_combined_map을 우선순위에 따라 재구축한다.

        우선순위: KOREAN_ACCOUNT_MAP (base) < _runtime_synonyms < custom_mappings
        """
        self._combined_map = {}
        # 1. 기본 사전 (최저 우선순위)
        self._combined_map.update(KOREAN_ACCOUNT_MAP)
        # 2. 런타임 동의어
        self._combined_map.update(self._runtime_synonyms)
        # 3. 사용자 정의 매핑 (최고 우선순위)
        self._combined_map.update(self._config.custom_mappings)

        logger.debug(
            "매핑 사전 구축 완료: base=%d, runtime=%d, custom=%d, combined=%d",
            len(KOREAN_ACCOUNT_MAP),
            len(self._runtime_synonyms),
            len(self._config.custom_mappings),
            len(self._combined_map),
        )

    def map(self, account_name: str) -> AccountMapping | None:
        """한글 계정명을 StandardAccount로 매핑한다.

        3단계 매칭:
          1. _combined_map에서 정확 일치 → confidence=1.0
          2. rapidfuzz 퍼지 매칭 → confidence=score/100
          3. 매핑 실패 → strict_mode에 따라 예외 또는 None

        Args:
            account_name: 한글 계정명 (strip 처리됨).

        Returns:
            매핑 성공 시 AccountMapping, 실패 시 None (strict_mode=False).

        Raises:
            AccountNotFoundError: strict_mode=True이고 매핑 실패 시.
        """
        name = account_name.strip()
        if not name:
            warning_msg = "빈 계정명이 입력되었습니다."
            logger.warning(warning_msg)
            self._warnings.append(warning_msg)
            return None

        # --- 1단계: 정확 일치 ---
        if name in self._combined_map:
            standard_code = self._combined_map[name]
            # custom_mappings에서 온 것인지 판별
            match_type = (
                "custom"
                if name in self._config.custom_mappings
                else "exact"
            )
            logger.debug("정확 일치: '%s' → %s (%s)", name, standard_code.name, match_type)
            return AccountMapping(
                original_name=name,
                standard_code=standard_code,
                confidence=1.0,
                match_type=match_type,
            )

        # --- 2단계: 퍼지 매칭 ---
        if _RAPIDFUZZ_AVAILABLE:
            result = process.extractOne(
                name,
                self._combined_map.keys(),
                score_cutoff=self._config.fuzzy_threshold,
            )
            if result is not None:
                matched_name, score, _ = result
                standard_code = self._combined_map[matched_name]
                confidence = score / 100.0

                warning_msg = (
                    f"퍼지 매칭: '{name}' → '{matched_name}' "
                    f"({standard_code.name}, score={score:.1f})"
                )
                logger.info(warning_msg)
                self._warnings.append(warning_msg)

                return AccountMapping(
                    original_name=name,
                    standard_code=standard_code,
                    confidence=confidence,
                    match_type="fuzzy",
                )
        else:
            warning_msg = (
                f"rapidfuzz 미설치: '{name}'에 대한 퍼지 매칭을 건너뜁니다. "
                "pip install rapidfuzz 로 설치하세요."
            )
            logger.warning(warning_msg)
            self._warnings.append(warning_msg)

        # --- 3단계: 매핑 실패 ---
        if name not in self._unmapped:
            self._unmapped.append(name)

        if self._config.strict_mode:
            raise AccountNotFoundError(account_name=name)

        logger.warning("매핑 실패: '%s' — unmapped에 추가됨", name)
        return None

    def map_all(
        self,
        data: dict[str, dict[str, Decimal | None]],
    ) -> dict[StandardAccount, dict[str, Decimal | None]]:
        """한글 계정명 dict를 StandardAccount dict로 일괄 변환한다.

        매핑 성공한 항목만 포함한다. 동일 StandardAccount에 여러 한글 키가
        매핑될 경우 첫 번째로 매핑된 항목만 사용한다 (덮어쓰지 않음).

        Args:
            data: {한글계정명: {연도: 금액}} 형태의 원본 데이터.

        Returns:
            {StandardAccount: {연도: 금액}} 형태의 변환된 데이터.

        Examples:
            >>> mapper = AccountMapper()
            >>> data = {"매출액": {"2023": Decimal("1000000")}}
            >>> result = mapper.map_all(data)
            >>> StandardAccount.REVENUE in result
            True
        """
        result: dict[StandardAccount, dict[str, Decimal | None]] = {}

        for korean_name, year_values in data.items():
            mapping = self.map(korean_name)
            if mapping is None:
                continue

            # 동일 StandardAccount에 대해 첫 번째만 사용
            if mapping.standard_code not in result:
                result[mapping.standard_code] = year_values
            else:
                warning_msg = (
                    f"중복 매핑 무시: '{korean_name}' → {mapping.standard_code.name} "
                    f"(이미 매핑된 항목 존재)"
                )
                logger.warning(warning_msg)
                self._warnings.append(warning_msg)

        logger.info(
            "일괄 매핑 완료: 입력 %d건, 성공 %d건, 실패 %d건",
            len(data),
            len(result),
            len(self._unmapped),
        )
        return result

    def add_synonym(self, korean_name: str, standard_code: StandardAccount) -> None:
        """런타임에 동의어를 추가한다.

        추가된 동의어는 KOREAN_ACCOUNT_MAP보다 높은 우선순위를 가지지만,
        custom_mappings보다는 낮은 우선순위를 가진다.

        Args:
            korean_name: 추가할 한글 계정명.
            standard_code: 매핑할 표준 계정 코드.
        """
        self._runtime_synonyms[korean_name] = standard_code
        self._rebuild_combined_map()
        logger.info("동의어 추가: '%s' → %s", korean_name, standard_code.name)

    @property
    def unmapped_accounts(self) -> list[str]:
        """매핑 실패한 계정명 목록을 반환한다."""
        return list(self._unmapped)

    @property
    def warnings(self) -> list[str]:
        """처리 중 발생한 경고 목록을 반환한다."""
        return list(self._warnings)

    def reset(self) -> None:
        """unmapped 목록과 warnings 목록을 초기화한다."""
        self._unmapped.clear()
        self._warnings.clear()
        logger.debug("unmapped/warnings 초기화 완료")
