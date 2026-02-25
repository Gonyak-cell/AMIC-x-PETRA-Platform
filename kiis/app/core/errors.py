"""KIIS 에러 코드 체계.

에러 코드 범위:
  1000-1999  DART API
  2000-2999  KOFIA (금융투자협회)
  3000-3999  공공데이터 / REITs
  4000-4999  분석 / 평판
  9000-9019  시스템 (일반 + 인증)
  9999       내부 오류
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """KIIS 도메인 에러 코드."""

    # ── 1000-1999: DART API 에러 ──
    DART_AUTH_FAILED = 1001  # API 키 미등록 (DART status "010")
    DART_RATE_LIMITED = 1002  # 호출 제한 (DART status "011")
    DART_NO_RESULT = 1003  # 결과 없음 (DART status "013")
    DART_INVALID_PARAMS = 1004  # 파라미터 오류 (DART status "020")
    DART_SYSTEM_MAINTENANCE = 1005  # 시스템 점검 (DART status "800")
    DART_PARSE_FAILED = 1006  # XML/ZIP 파싱 실패
    DART_NETWORK_ERROR = 1007  # DART 네트워크 오류

    # ── 2000-2999: KOFIA 에러 ──
    KOFIA_FUND_NOT_FOUND = 2001  # 펀드 조회 실패
    KOFIA_PARSE_ERROR = 2002  # KOFIA 응답 파싱 실패
    KOFIA_NETWORK_ERROR = 2003  # KOFIA 네트워크 오류

    # ── 3000-3999: 공공데이터 / REITs 에러 ──
    REITS_PARSE_ERROR = 3001  # 리츠 HTML 파싱 실패
    REITS_NETWORK_ERROR = 3002  # 리츠 네트워크 오류
    PUBLIC_DATA_ERROR = 3003  # 공공데이터포털 API 오류

    # ── 4000-4999: 분석 / 평판 에러 ──
    ANALYSIS_COMPANY_NOT_FOUND = 4001  # 분석 대상 기업 미존재
    ANALYSIS_REPUTATION_FAILED = 4002  # 평판 계산 실패
    ANALYSIS_INSUFFICIENT_DATA = 4003  # 분석용 데이터 부족

    # ── 9000-9099: 시스템 에러 ──
    SYS_DB_ERROR = 9001  # DB 오류
    SYS_RATE_LIMIT = 9002  # 시스템 Rate Limit
    SYS_EXTERNAL_API = 9003  # 일반 외부 API 오류
    SYS_AUTH_FAILED = 9010  # 인증 실패
    SYS_AUTH_TOKEN_EXPIRED = 9011  # 토큰 만료
    SYS_AUTH_FORBIDDEN = 9012  # 권한 부족
    SYS_INTERNAL = 9999  # 내부 오류


def get_domain(code: ErrorCode) -> str:
    """에러 코드의 도메인 이름을 반환한다."""
    value = int(code)
    domain_map: dict[range, str] = {
        range(1000, 2000): "dart",
        range(2000, 3000): "kofia",
        range(3000, 4000): "public_data",
        range(4000, 5000): "analysis",
        range(9000, 10000): "system",
    }
    for r, name in domain_map.items():
        if value in r:
            return name
    return "unknown"
