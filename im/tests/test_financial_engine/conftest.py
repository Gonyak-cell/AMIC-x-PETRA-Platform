"""Financial Engine 테스트 공유 픽스처.

> 마지막 수정: 2026-02-09

모든 financial engine 테스트에서 공유하는 pytest 픽스처를 정의합니다.
- sample_dart_data: DART API 스타일 한글 계정명 + 3개년 Decimal 데이터
- sample_balanced_bs / sample_unbalanced_bs: 재무상태표 균형 검증용
- account_mapper / unit_normalizer: 매퍼/정규화기 인스턴스
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.mapper.account_mapper import AccountMapper
from src.financial_engine.normalizer.unit_normalizer import UnitNormalizer


# ---------------------------------------------------------------------------
# DART 스타일 한글 계정명 + 3개년 Decimal 데이터
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_dart_data() -> dict[str, dict[str, Decimal | None]]:
    """DART API 형태의 한글 계정명 + 3개년(2022-2024) Decimal 데이터.

    손익계산서(IS), 재무상태표(BS), 현금흐름표(CF) 주요 계정을 포함합니다.
    """
    return {
        # --- 손익계산서 (IS) ---
        "매출액": {
            "2022": Decimal("500000000000"),
            "2023": Decimal("620000000000"),
            "2024": Decimal("750000000000"),
        },
        "매출원가": {
            "2022": Decimal("300000000000"),
            "2023": Decimal("360000000000"),
            "2024": Decimal("420000000000"),
        },
        "매출총이익": {
            "2022": Decimal("200000000000"),
            "2023": Decimal("260000000000"),
            "2024": Decimal("330000000000"),
        },
        "영업이익": {
            "2022": Decimal("80000000000"),
            "2023": Decimal("105000000000"),
            "2024": Decimal("140000000000"),
        },
        "당기순이익": {
            "2022": Decimal("55000000000"),
            "2023": Decimal("72000000000"),
            "2024": Decimal("98000000000"),
        },
        "감가상각비": {
            "2022": Decimal("15000000000"),
            "2023": Decimal("18000000000"),
            "2024": Decimal("22000000000"),
        },
        # --- 재무상태표 (BS) ---
        "자산총계": {
            "2022": Decimal("1200000000000"),
            "2023": Decimal("1400000000000"),
            "2024": Decimal("1650000000000"),
        },
        "부채총계": {
            "2022": Decimal("500000000000"),
            "2023": Decimal("560000000000"),
            "2024": Decimal("620000000000"),
        },
        "자본총계": {
            "2022": Decimal("700000000000"),
            "2023": Decimal("840000000000"),
            "2024": Decimal("1030000000000"),
        },
        "현금및현금성자산": {
            "2022": Decimal("120000000000"),
            "2023": Decimal("150000000000"),
            "2024": Decimal("200000000000"),
        },
        # --- 현금흐름표 (CF) ---
        "영업활동현금흐름": {
            "2022": Decimal("95000000000"),
            "2023": Decimal("120000000000"),
            "2024": Decimal("155000000000"),
        },
        "자본적지출": {
            "2022": Decimal("30000000000"),
            "2023": Decimal("40000000000"),
            "2024": Decimal("50000000000"),
        },
    }


# ---------------------------------------------------------------------------
# 재무상태표 균형 검증용 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_balanced_bs() -> dict[str, dict[str, Decimal]]:
    """자산총계 == 부채총계 + 자본총계 (균형 재무상태표, 3개년)."""
    return {
        "자산총계": {
            "2022": Decimal("1000"),
            "2023": Decimal("1200"),
            "2024": Decimal("1500"),
        },
        "부채총계": {
            "2022": Decimal("400"),
            "2023": Decimal("500"),
            "2024": Decimal("600"),
        },
        "자본총계": {
            "2022": Decimal("600"),
            "2023": Decimal("700"),
            "2024": Decimal("900"),
        },
    }


@pytest.fixture()
def sample_unbalanced_bs() -> dict[str, dict[str, Decimal]]:
    """자산총계 != 부채총계 + 자본총계 (불균형 재무상태표)."""
    return {
        "자산총계": {
            "2022": Decimal("1000"),
            "2023": Decimal("1200"),
            "2024": Decimal("1500"),
        },
        "부채총계": {
            "2022": Decimal("400"),
            "2023": Decimal("500"),
            "2024": Decimal("600"),
        },
        "자본총계": {
            "2022": Decimal("600"),
            "2023": Decimal("700"),
            "2024": Decimal("850"),  # 1500 != 600 + 850
        },
    }


# ---------------------------------------------------------------------------
# 매퍼 / 정규화기 인스턴스
# ---------------------------------------------------------------------------


@pytest.fixture()
def account_mapper() -> AccountMapper:
    """기본 설정의 AccountMapper 인스턴스."""
    return AccountMapper()


@pytest.fixture()
def unit_normalizer() -> UnitNormalizer:
    """기본 설정의 UnitNormalizer 인스턴스."""
    return UnitNormalizer()
