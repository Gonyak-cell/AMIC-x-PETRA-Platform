"""IM API 에러 코드 체계.

에러 코드 범위:
  1000-1999  데이터 인제스트
  2000-2999  재무 엔진
  3000-3999  내러티브 / 문서 생성
  4000-4999  태스크 / 파이프라인
  5000-5999  유효성 검증
  9000-9019  시스템 (일반 + 인증)
  9999       내부 오류
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """IM API 도메인 에러 코드."""

    # ── 1000-1999: 데이터 인제스트 에러 ──
    INGEST_COMPANY_NOT_FOUND = 1001  # 기업 정보 미존재
    INGEST_FILE_PARSE_FAILED = 1002  # 업로드 파일 파싱 실패
    INGEST_DATA_VALIDATION = 1003  # 인제스트 데이터 검증 실패

    # ── 2000-2999: 재무 엔진 에러 ──
    FINANCIAL_CALC_FAILED = 2001  # 재무 계산 실패
    FINANCIAL_DATA_MISSING = 2002  # 재무 데이터 누락

    # ── 3000-3999: 내러티브 / 문서 생성 에러 ──
    NARRATIVE_GENERATION_FAILED = 3001  # 내러티브 생성 실패
    NARRATIVE_LLM_ERROR = 3002  # LLM API 오류
    DOC_NOT_FOUND = 3003  # 문서 미존재
    DOC_CONFLICT = 3004  # 문서 충돌 (이미 존재)
    DOC_FILE_NOT_FOUND = 3005  # 생성된 파일 미존재

    # ── 4000-4999: 태스크 / 파이프라인 에러 ──
    TASK_EXECUTION_FAILED = 4001  # 비동기 태스크 실패
    TASK_TIMEOUT = 4002  # 태스크 타임아웃

    # ── 5000-5999: 유효성 검증 에러 ──
    VALIDATION_FIELD_ERROR = 5001  # 필드 검증 실패
    VALIDATION_SCHEMA_ERROR = 5002  # 스키마 검증 실패

    # ── 9000-9099: 시스템 에러 ──
    SYS_DB_ERROR = 9001  # DB 오류
    SYS_REDIS_ERROR = 9002  # Redis 오류
    SYS_AUTH_FAILED = 9010  # 인증 실패
    SYS_AUTH_FORBIDDEN = 9011  # 권한 부족
    SYS_API_KEY_INVALID = 9012  # API 키 무효
    SYS_INTERNAL = 9999  # 내부 오류


def get_domain(code: ErrorCode) -> str:
    """에러 코드의 도메인 이름을 반환한다."""
    value = int(code)
    domain_map: dict[range, str] = {
        range(1000, 2000): "ingest",
        range(2000, 3000): "financial",
        range(3000, 4000): "narrative",
        range(4000, 5000): "task",
        range(5000, 6000): "validation",
        range(9000, 10000): "system",
    }
    for r, name in domain_map.items():
        if value in r:
            return name
    return "unknown"
