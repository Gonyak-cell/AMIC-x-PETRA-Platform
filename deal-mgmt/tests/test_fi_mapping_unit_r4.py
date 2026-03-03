"""R4 리뷰 추가 테스트 — FI 매핑 순수 함수 (R6-DL-01).

normalize_gp_name 함수의 '어드바이저리' 접미사 제거를 검증한다.
_STRIP_SUFFIXES 목록에 등록된 '어드바이저리'가 실제로 동작하는지
단위 테스트로 확인하여 커버리지 공백을 보완한다.
"""

from __future__ import annotations

from app.services.fi_mapping_service import normalize_gp_name


def test_normalize_gp_name_advisory_suffix() -> None:
    """'어드바이저리' 접미사가 제거된다 (R6-DL-01)."""
    assert normalize_gp_name("한국어드바이저리") == "한국"


def test_normalize_gp_name_advisory_with_prefix() -> None:
    """법인격 접두사 + '어드바이저리' 접미사 동시 제거."""
    assert normalize_gp_name("(주)한국어드바이저리") == "한국"
