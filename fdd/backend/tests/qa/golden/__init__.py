"""Golden 데이터셋 — Sprint 8 Phase 4.

QA 검증용 표준 테스트 데이터셋.
각 케이스는 예상 결과와 함께 정의되어 있습니다.
"""

from tests.qa.golden.datasets import (
    GOLDEN_DATASETS,
    GoldenCase,
    GoldenCaseType,
    get_cases_by_type,
)

__all__ = [
    "GOLDEN_DATASETS",
    "GoldenCase",
    "GoldenCaseType",
    "get_cases_by_type",
]
