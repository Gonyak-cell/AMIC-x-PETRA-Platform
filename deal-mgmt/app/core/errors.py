"""Deal-mgmt (MA) 에러 코드 체계.

에러 코드 범위:
  1000-1999  거래 (Transaction)
  2000-2999  문서 (Document)
  3000-3999  DD / 체크리스트
  4000-4999  워크플로우
  5000-5999  Ralph (AI)
  6000-6999  법률 / 컴플라이언스
  9000-9099  시스템 (일반 + 인증)
  9999       내부 오류
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """MA 도메인 에러 코드."""

    # ── 1000-1999: 거래 에러 ──
    TXN_NOT_FOUND = 1001  # 거래 미존재
    TXN_CREATION_FAILED = 1002  # 거래 생성 실패
    TXN_UPDATE_FAILED = 1003  # 거래 업데이트 실패

    # ── 2000-2999: 문서 에러 ──
    DOC_NOT_FOUND = 2001  # 문서 미존재
    DOC_NOT_READY = 2002  # 문서 미준비 상태
    DOC_CONFLICT = 2003  # 문서 충돌

    # ── 3000-3999: DD / 체크리스트 에러 ──
    DD_ITEM_NOT_FOUND = 3001  # DD 체크리스트 항목 미존재
    DD_WORKSTREAM_ERROR = 3002  # 워크스트림 오류

    # ── 4000-4999: 워크플로우 에러 ──
    WF_INVALID_TRANSITION = 4001  # 잘못된 상태 전환
    WF_PREREQUISITES_UNMET = 4002  # 필수 조건 미충족
    WF_APPROVAL_REQUIRED = 4003  # 승인 필요
    WF_STATUS_CONFLICT = 4004  # 상태 충돌

    # ── 5000-5999: Ralph (AI) 에러 ──
    RALPH_SESSION_NOT_FOUND = 5001  # Ralph 세션 미존재
    RALPH_LLM_ERROR = 5002  # Ralph LLM 오류
    RALPH_PPTX_FAILED = 5003  # Ralph PPTX 생성 실패

    # ── 6000-6999: 법률 / 컴플라이언스 에러 ──
    LEGAL_DOC_NOT_FOUND = 6001  # 법률 문서 미존재
    COMPLIANCE_ITEM_NOT_FOUND = 6002  # 컴플라이언스 항목 미존재
    APPROVAL_NOT_FOUND = 6003  # 승인 요청 미존재

    # ── 9000-9099: 시스템 에러 ──
    SYS_SERVICE_UNAVAILABLE = 9001  # 외부 서비스 불가
    SYS_DB_ERROR = 9002  # DB 오류
    SYS_AUTH_FAILED = 9010  # 인증 실패
    SYS_AUTH_FORBIDDEN = 9011  # 권한 부족
    SYS_CONFLICT = 9020  # 이해충돌
    SYS_INTERNAL = 9999  # 내부 오류


def get_domain(code: ErrorCode) -> str:
    """에러 코드의 도메인 이름을 반환한다."""
    value = int(code)
    domain_map: dict[range, str] = {
        range(1000, 2000): "transaction",
        range(2000, 3000): "document",
        range(3000, 4000): "dd",
        range(4000, 5000): "workflow",
        range(5000, 6000): "ralph",
        range(6000, 7000): "legal",
        range(9000, 10000): "system",
    }
    for r, name in domain_map.items():
        if value in r:
            return name
    return "unknown"
