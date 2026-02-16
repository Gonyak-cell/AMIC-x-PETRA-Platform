"""FDD 에러 코드 체계 (마스터파일 §4.4.1).

에러 코드 범위:
  1000-1999  데이터 인제스트
  2000-2999  계정 매핑
  3000-3999  QoE 계산
  4000-4999  NWC 계산
  5000-5999  Net Debt 계산
  6000-6999  문서 처리
  7000-7999  QA 검증 (Sprint 8)
  8000-8999  템플릿/보고서 (Sprint 10)
  9000-9009  시스템 (일반)
  9010-9019  인증/인가 (Sprint 11)
  9999       내부 오류
"""

from enum import IntEnum


class ErrorSeverity(IntEnum):
    """에러 심각도 (마스터파일 §4.4.2)."""

    INFO = 0  # 정상 처리 정보 → 로그만
    WARNING = 1  # 결과 신뢰도 하락 → 계속 + 경고
    ERROR = 2  # 기능 실행 불가 → 재시도 후 사용자 알림
    CRITICAL = 3  # 데이터 무결성 위협 → 즉시 중단 + 알림


class ErrorCode(IntEnum):
    """FDD 도메인 에러 코드."""

    # ── 1000-1999: 데이터 인제스트 에러 ──
    INGEST_TB_MISMATCH = 1001  # TB 합계 불일치
    INGEST_GL_PERIOD_MISSING = 1002  # GL 기간 누락
    INGEST_FILE_FORMAT = 1003  # 파일 형식 오류
    INGEST_EMPTY_DATA = 1004  # 빈 데이터
    INGEST_DUPLICATE_ENTRY = 1005  # 중복 데이터
    INGEST_ENCODING_ERROR = 1006  # 파일 인코딩 오류
    INGEST_FX_RATE_MISSING = 1007  # 환율 미등록
    INGEST_FX_CONVERSION_ERROR = 1008  # 환율 변환 오류
    INGEST_ENTITY_REQUIRED = 1009  # 멀티 엔티티 딜에서 entity_id 미지정

    # ── 2000-2999: 계정 매핑 에러 ──
    MAPPING_UNMAPPED_ACCOUNT = 2001  # 미매핑 계정 존재
    MAPPING_CONFLICT = 2002  # 매핑 충돌
    MAPPING_LOW_CONFIDENCE = 2003  # 매핑 신뢰도 낮음
    MAPPING_INVALID_TARGET = 2004  # 유효하지 않은 대상 계정

    # ── 3000-3999: QoE 계산 에러 ──
    QOE_NEGATIVE_EBITDA = 3001  # EBITDA 음수
    QOE_ADJUSTMENT_NO_BASIS = 3002  # 조정항목 근거 미비
    QOE_BRIDGE_IMBALANCE = 3003  # 브리지 합계 불일치
    QOE_PERIOD_MISMATCH = 3004  # 기간 데이터 불일치
    QOE_ANOMALY_DETECTION_FAILED = 3005  # 이상치 탐지 실패
    QOE_AI_ANALYSIS_FAILED = 3006  # AI 분석 실패
    QOE_AI_VALIDATION_FAILED = 3007  # AI 검증 실패

    # ── 4000-4999: NWC 계산 에러 ──
    NWC_DEFINITION_MISSING = 4001  # NWC 정의 미설정
    NWC_PERIOD_INSUFFICIENT = 4002  # 기간 데이터 부족
    NWC_PEG_CALCULATION = 4003  # Peg 계산 오류
    NWC_CLASSIFICATION_MISSING = 4004  # 분류 미완료

    # ── 5000-5999: Net Debt 계산 에러 ──
    DEBT_CLASSIFICATION_INCOMPLETE = 5001  # Debt 분류 미완료
    DEBT_LEASE_DATA_MISSING = 5002  # 리스 데이터 부족
    DEBT_CASH_RECONCILIATION = 5003  # 현금 조정 오류
    DEBT_DUPLICATE_ITEM = 5004  # 중복 항목

    # ── 6000-6999: 문서 처리 에러 ──
    DOC_OCR_FAILURE = 6001  # OCR 실패
    DOC_CONTRACT_PARSE = 6002  # 계약서 파싱 오류
    DOC_UNSUPPORTED_FORMAT = 6003  # 지원하지 않는 형식
    DOC_EXTRACTION_FAILED = 6004  # 데이터 추출 실패

    # ── 7000-7999: QA 검증 에러 (Sprint 8) ──
    QA_REPORT_NUMERIC_DIFF = 7001  # 표 수치 불일치
    QA_LAYOUT_PLACEHOLDER_MISSING = 7002  # placeholder 미치환
    QA_LAYOUT_OVERFLOW = 7003  # 텍스트/표 오버플로우
    QA_EVIDENCE_MISSING = 7004  # Evidence 누락
    QA_EVIDENCE_BROKEN = 7005  # Evidence 링크 깨짐
    QA_PERFORMANCE_SLA_FAIL = 7006  # 성능 SLA 미달
    QA_GOLDEN_MISMATCH = 7007  # 골든 데이터 불일치

    # ── 8000-8999: 템플릿/보고서 에러 (Sprint 10) ──
    TEMPLATE_VALIDATION_FAILED = 8001  # 템플릿 검증 실패
    TEMPLATE_SLOT_MISSING = 8002  # 필수 슬롯 누락
    TEMPLATE_SLOT_DUPLICATE = 8003  # 중복 슬롯
    TEMPLATE_CONTRACT_INVALID = 8004  # 템플릿 계약 무효
    TEMPLATE_INJECTION_FAILED = 8005  # 템플릿 주입 실패
    TEMPLATE_FILE_INVALID = 8006  # 템플릿 파일 무효
    DELTA_CALCULATION_FAILED = 8007  # Delta 계산 실패
    DELTA_VERSION_MISMATCH = 8008  # 버전 불일치

    # ── 9000-9999: 시스템 에러 ──
    SYS_DB_CONNECTION = 9001  # DB 연결 실패
    SYS_FILE_PROCESSING = 9002  # 파일 처리 오류
    SYS_EXTERNAL_SERVICE = 9003  # 외부 서비스 오류
    SYS_PERMISSION_DENIED = 9004  # 권한 없음
    SYS_RATE_LIMIT = 9005  # Rate limit 초과
    SYS_AI_TIMEOUT = 9006  # AI 타임아웃
    SYS_AI_RATE_LIMIT = 9007  # AI Rate limit 초과
    SYS_AI_TOKEN_LIMIT = 9008  # AI 토큰 한도 초과

    # ── 9010-9019: 인증/인가 에러 (Sprint 11) ──
    AUTH_INVALID_CREDENTIALS = 9010  # 로그인 실패
    AUTH_TOKEN_EXPIRED = 9011  # 토큰 만료
    AUTH_TOKEN_INVALID = 9012  # 유효하지 않은 토큰
    AUTH_REFRESH_TOKEN_EXPIRED = 9013  # Refresh 토큰 만료
    AUTH_FORBIDDEN = 9014  # 권한 부족 (RBAC)
    AUTH_USER_DISABLED = 9015  # 비활성화된 계정
    AUTH_SESSION_LIMIT = 9016  # 동시 세션 초과
    AUTH_TOKEN_REVOKED = 9017  # 취소된(blacklisted) 토큰

    SYS_INTERNAL = 9999  # 알 수 없는 내부 오류


# 에러 코드별 기본 심각도
ERROR_SEVERITY_MAP: dict[ErrorCode, ErrorSeverity] = {
    # 데이터 인제스트 — 대부분 ERROR, tie-out 불일치는 CRITICAL
    ErrorCode.INGEST_TB_MISMATCH: ErrorSeverity.CRITICAL,
    ErrorCode.INGEST_GL_PERIOD_MISSING: ErrorSeverity.ERROR,
    ErrorCode.INGEST_FILE_FORMAT: ErrorSeverity.ERROR,
    ErrorCode.INGEST_EMPTY_DATA: ErrorSeverity.ERROR,
    ErrorCode.INGEST_DUPLICATE_ENTRY: ErrorSeverity.WARNING,
    ErrorCode.INGEST_ENCODING_ERROR: ErrorSeverity.ERROR,
    ErrorCode.INGEST_FX_RATE_MISSING: ErrorSeverity.ERROR,
    ErrorCode.INGEST_FX_CONVERSION_ERROR: ErrorSeverity.ERROR,
    ErrorCode.INGEST_ENTITY_REQUIRED: ErrorSeverity.WARNING,
    # 계정 매핑
    ErrorCode.MAPPING_UNMAPPED_ACCOUNT: ErrorSeverity.ERROR,
    ErrorCode.MAPPING_CONFLICT: ErrorSeverity.ERROR,
    ErrorCode.MAPPING_LOW_CONFIDENCE: ErrorSeverity.WARNING,
    ErrorCode.MAPPING_INVALID_TARGET: ErrorSeverity.ERROR,
    # QoE
    ErrorCode.QOE_NEGATIVE_EBITDA: ErrorSeverity.WARNING,
    ErrorCode.QOE_ADJUSTMENT_NO_BASIS: ErrorSeverity.WARNING,
    ErrorCode.QOE_BRIDGE_IMBALANCE: ErrorSeverity.CRITICAL,
    ErrorCode.QOE_PERIOD_MISMATCH: ErrorSeverity.ERROR,
    ErrorCode.QOE_ANOMALY_DETECTION_FAILED: ErrorSeverity.ERROR,
    ErrorCode.QOE_AI_ANALYSIS_FAILED: ErrorSeverity.ERROR,
    ErrorCode.QOE_AI_VALIDATION_FAILED: ErrorSeverity.WARNING,
    # NWC
    ErrorCode.NWC_DEFINITION_MISSING: ErrorSeverity.ERROR,
    ErrorCode.NWC_PERIOD_INSUFFICIENT: ErrorSeverity.ERROR,
    ErrorCode.NWC_PEG_CALCULATION: ErrorSeverity.ERROR,
    ErrorCode.NWC_CLASSIFICATION_MISSING: ErrorSeverity.WARNING,
    # Net Debt
    ErrorCode.DEBT_CLASSIFICATION_INCOMPLETE: ErrorSeverity.ERROR,
    ErrorCode.DEBT_LEASE_DATA_MISSING: ErrorSeverity.WARNING,
    ErrorCode.DEBT_CASH_RECONCILIATION: ErrorSeverity.CRITICAL,
    ErrorCode.DEBT_DUPLICATE_ITEM: ErrorSeverity.WARNING,
    # 문서 처리
    ErrorCode.DOC_OCR_FAILURE: ErrorSeverity.ERROR,
    ErrorCode.DOC_CONTRACT_PARSE: ErrorSeverity.ERROR,
    ErrorCode.DOC_UNSUPPORTED_FORMAT: ErrorSeverity.ERROR,
    ErrorCode.DOC_EXTRACTION_FAILED: ErrorSeverity.ERROR,
    # QA 검증
    ErrorCode.QA_REPORT_NUMERIC_DIFF: ErrorSeverity.ERROR,
    ErrorCode.QA_LAYOUT_PLACEHOLDER_MISSING: ErrorSeverity.WARNING,
    ErrorCode.QA_LAYOUT_OVERFLOW: ErrorSeverity.WARNING,
    ErrorCode.QA_EVIDENCE_MISSING: ErrorSeverity.ERROR,
    ErrorCode.QA_EVIDENCE_BROKEN: ErrorSeverity.ERROR,
    ErrorCode.QA_PERFORMANCE_SLA_FAIL: ErrorSeverity.WARNING,
    ErrorCode.QA_GOLDEN_MISMATCH: ErrorSeverity.ERROR,
    # 템플릿/보고서
    ErrorCode.TEMPLATE_VALIDATION_FAILED: ErrorSeverity.ERROR,
    ErrorCode.TEMPLATE_SLOT_MISSING: ErrorSeverity.ERROR,
    ErrorCode.TEMPLATE_SLOT_DUPLICATE: ErrorSeverity.WARNING,
    ErrorCode.TEMPLATE_CONTRACT_INVALID: ErrorSeverity.ERROR,
    ErrorCode.TEMPLATE_INJECTION_FAILED: ErrorSeverity.ERROR,
    ErrorCode.TEMPLATE_FILE_INVALID: ErrorSeverity.ERROR,
    ErrorCode.DELTA_CALCULATION_FAILED: ErrorSeverity.ERROR,
    ErrorCode.DELTA_VERSION_MISMATCH: ErrorSeverity.ERROR,
    # 시스템
    ErrorCode.SYS_DB_CONNECTION: ErrorSeverity.CRITICAL,
    ErrorCode.SYS_FILE_PROCESSING: ErrorSeverity.ERROR,
    ErrorCode.SYS_EXTERNAL_SERVICE: ErrorSeverity.ERROR,
    ErrorCode.SYS_PERMISSION_DENIED: ErrorSeverity.ERROR,
    ErrorCode.SYS_RATE_LIMIT: ErrorSeverity.WARNING,
    ErrorCode.SYS_AI_TIMEOUT: ErrorSeverity.ERROR,
    ErrorCode.SYS_AI_RATE_LIMIT: ErrorSeverity.WARNING,
    ErrorCode.SYS_AI_TOKEN_LIMIT: ErrorSeverity.ERROR,
    # 인증/인가
    ErrorCode.AUTH_INVALID_CREDENTIALS: ErrorSeverity.WARNING,
    ErrorCode.AUTH_TOKEN_EXPIRED: ErrorSeverity.WARNING,
    ErrorCode.AUTH_TOKEN_INVALID: ErrorSeverity.WARNING,
    ErrorCode.AUTH_REFRESH_TOKEN_EXPIRED: ErrorSeverity.WARNING,
    ErrorCode.AUTH_FORBIDDEN: ErrorSeverity.ERROR,
    ErrorCode.AUTH_USER_DISABLED: ErrorSeverity.ERROR,
    ErrorCode.AUTH_SESSION_LIMIT: ErrorSeverity.WARNING,
    ErrorCode.AUTH_TOKEN_REVOKED: ErrorSeverity.WARNING,
    ErrorCode.SYS_INTERNAL: ErrorSeverity.CRITICAL,
}


def get_severity(code: ErrorCode) -> ErrorSeverity:
    """에러 코드의 기본 심각도를 반환한다."""
    return ERROR_SEVERITY_MAP.get(code, ErrorSeverity.ERROR)


def get_domain(code: ErrorCode) -> str:
    """에러 코드의 도메인 이름을 반환한다."""
    value = int(code)
    domain_map: dict[range, str] = {
        range(1000, 2000): "ingest",
        range(2000, 3000): "mapping",
        range(3000, 4000): "qoe",
        range(4000, 5000): "nwc",
        range(5000, 6000): "debt",
        range(6000, 7000): "document",
        range(7000, 8000): "qa",
        range(8000, 9000): "template",
        range(9000, 10000): "system",
    }
    for r, name in domain_map.items():
        if value in r:
            return name
    return "unknown"
