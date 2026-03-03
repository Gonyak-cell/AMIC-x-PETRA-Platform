"""fi_mapping_service 순수 함수 단위 테스트 (TQ-03).

- _format_billions: Decimal 금액 → 한국어 포맷 변환
- _check_keyword_match: GP 포트폴리오 키워드 교집합 판정
- normalize_gp_name: GP명 정규화 (접두사/접미사 제거)
"""

from __future__ import annotations

from decimal import Decimal

from app.services.fi_mapping_service import (
    _check_keyword_match,
    _format_billions,
    normalize_gp_name,
)

# ── _format_billions 단위 테스트 ──────────────────────────


def test_format_billions_under_10000() -> None:
    """1만억 미만은 'N,NNN억' 형식."""
    result = _format_billions(Decimal("9999"))
    assert result == "9,999억"


def test_format_billions_exactly_10000() -> None:
    """1만억은 정확히 '1.0조'."""
    result = _format_billions(Decimal("10000"))
    assert result == "1.0조"


def test_format_billions_over_10000() -> None:
    """1.5만억은 '1.5조'."""
    result = _format_billions(Decimal("15000"))
    assert result == "1.5조"


def test_format_billions_small() -> None:
    """소액(100억)은 '100억' — 천 단위 구분자 없음."""
    result = _format_billions(Decimal("100"))
    assert result == "100억"


def test_format_billions_large_trillion() -> None:
    """20,000억은 '2.0조'."""
    result = _format_billions(Decimal("20000"))
    assert result == "2.0조"


def test_format_billions_with_decimal() -> None:
    """소수점 있는 억 단위는 정수로 반올림 없이 표시."""
    result = _format_billions(Decimal("1234"))
    assert result == "1,234억"


# ── _check_keyword_match 단위 테스트 ──────────────────────


def _make_gp_profile_stub(portfolio_sectors: list[str] | None) -> object:
    """테스트용 GpProfile 스텁 (DB 미저장).

    SQLAlchemy ORM 모델을 object.__new__로 생성하면 _sa_instance_state 부재로
    AttributeError가 발생하므로 SimpleNamespace를 사용한다.
    """
    from types import SimpleNamespace

    return SimpleNamespace(portfolio_sectors=portfolio_sectors)


def test_check_keyword_match_hit() -> None:
    """포트폴리오 섹터와 타겟 키워드 교집합 존재 → True."""
    profile = _make_gp_profile_stub(["식품", "제조", "유통"])
    result = _check_keyword_match(profile, ["제조", "IT"])
    assert result is True


def test_check_keyword_match_miss() -> None:
    """교집합 없음 → False."""
    profile = _make_gp_profile_stub(["금융", "부동산"])
    result = _check_keyword_match(profile, ["제조", "IT"])
    assert result is False


def test_check_keyword_match_none_target() -> None:
    """target_keywords=None → False (키워드 미제공)."""
    profile = _make_gp_profile_stub(["식품", "제조"])
    result = _check_keyword_match(profile, None)
    assert result is False


def test_check_keyword_match_empty_target() -> None:
    """target_keywords=[] → False (빈 리스트)."""
    profile = _make_gp_profile_stub(["식품", "제조"])
    result = _check_keyword_match(profile, [])
    assert result is False


def test_check_keyword_match_empty_profile_sectors() -> None:
    """profile.portfolio_sectors=None → False."""
    profile = _make_gp_profile_stub(None)
    result = _check_keyword_match(profile, ["제조"])
    assert result is False


def test_check_keyword_match_case_insensitive() -> None:
    """대소문자 무관 매칭 — 소문자로 정규화 후 비교."""
    profile = _make_gp_profile_stub(["IT", "SaaS"])
    result = _check_keyword_match(profile, ["it"])
    assert result is True


def test_check_keyword_match_whitespace_stripped() -> None:
    """앞뒤 공백 있어도 매칭 성공."""
    profile = _make_gp_profile_stub(["  제조  "])
    result = _check_keyword_match(profile, ["제조"])
    assert result is True


# ── normalize_gp_name 단위 테스트 ──────────────────────────


def test_normalize_gp_name_prefix_removal() -> None:
    """'(주)' 접두사만 제거 — 접미사 없는 입력으로 접두사 로직 독립 검증."""
    assert normalize_gp_name("(주)한국코리아") == "한국코리아"


def test_normalize_gp_name_jusikhwesa_prefix() -> None:
    """'주식회사' 접두사만 제거 — 접미사 없는 입력으로 접두사 로직 독립 검증."""
    assert normalize_gp_name("주식회사한국코리아") == "한국코리아"


def test_normalize_gp_name_suffix_removal() -> None:
    """'자산운용' 접미사 제거."""
    assert normalize_gp_name("한국자산운용") == "한국"


def test_normalize_gp_name_multiple_suffixes() -> None:
    """중첩 접미사 반복 제거."""
    assert normalize_gp_name("에이비씨캐피털파트너스") == "에이비씨"


def test_normalize_gp_name_new_suffix_private_equity() -> None:
    """신규 추가 접미사 '프라이빗에쿼티' 제거."""
    assert normalize_gp_name("한국프라이빗에쿼티") == "한국"


def test_normalize_gp_name_new_suffix_ventures() -> None:
    """신규 추가 접미사 '벤처스' 제거."""
    assert normalize_gp_name("케이벤처스") == "케이"


def test_normalize_gp_name_new_suffix_asset() -> None:
    """신규 추가 접미사 '에셋' 제거."""
    assert normalize_gp_name("한국에셋") == "한국"


def test_normalize_gp_name_new_suffix_asset_management() -> None:
    """신규 추가 접미사 '에셋매니지먼트' 제거."""
    assert normalize_gp_name("비케이에셋매니지먼트") == "비케이"


def test_normalize_gp_name_new_prefix_yuhan_chaegim() -> None:
    """신규 추가 접두사 '유한책임회사'만 제거 — 접미사 없는 입력으로 독립 검증."""
    assert normalize_gp_name("유한책임회사알파코리아") == "알파코리아"


def test_normalize_gp_name_no_change_needed() -> None:
    """접두사/접미사 없으면 원본 유지."""
    result = normalize_gp_name("그린파트너")
    assert result == "그린파트너"


def test_normalize_gp_name_middle_substring_not_removed() -> None:
    """중간 부분 문자열은 제거하지 않음 — endswith 기반 접미사 매칭 검증.

    '한국자산신탁'에서 '자산'이 중간에 있어도 제거되지 않아야 한다.
    """
    result = normalize_gp_name("한국자산신탁")
    assert result == "한국자산신탁"
