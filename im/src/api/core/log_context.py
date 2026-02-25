"""ContextVar 기반 요청 컨텍스트 관리.

미들웨어에서 설정, 모든 로그에서 자동 참조.
"""

import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def set_request_id(request_id: str | None = None) -> str:
    """요청 ID를 설정하고 반환한다."""
    rid = request_id or f"req_{uuid.uuid4().hex[:16]}"
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str | None:
    """현재 컨텍스트의 요청 ID를 반환한다."""
    return _request_id_var.get()


def set_user_id(user_id: str | None) -> None:
    """인증된 사용자 ID를 설정한다."""
    _user_id_var.set(user_id)


def get_user_id() -> str | None:
    """현재 컨텍스트의 사용자 ID를 반환한다."""
    return _user_id_var.get()
