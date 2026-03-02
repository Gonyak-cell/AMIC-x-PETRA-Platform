"""에러 발생 시 함수 입력값을 자동으로 로그에 기록하는 데코레이터.

사용 예:
    @log_error_with_input
    async def transition(self, tx_id: str, to_stage: str) -> Transaction:
        ...

에러 발생 시 logger.error()에 extra={"error_input": {...}}가 자동 추가되어
JSONFormatter가 error.input 블록으로 기록한다.
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def log_error_with_input(func: Callable[..., T]) -> Callable[..., T]:
    """에러 발생 시 함수 입력값을 로그에 포함하는 데코레이터."""
    logger = logging.getLogger(func.__module__)
    sig = inspect.signature(func)

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            input_data = _capture_inputs(sig, args, kwargs)
            logger.error(
                "%s failed: %s",
                func.__qualname__,
                e,
                exc_info=True,
                extra={"error_input": input_data},
            )
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            input_data = _capture_inputs(sig, args, kwargs)
            logger.error(
                "%s failed: %s",
                func.__qualname__,
                e,
                exc_info=True,
                extra={"error_input": input_data},
            )
            raise

    if inspect.iscoroutinefunction(func):
        return async_wrapper  # type: ignore[return-value]
    return sync_wrapper  # type: ignore[return-value]


# ── 내부 헬퍼 ──────────────────────────────────────


_SKIP_PARAMS = frozenset({"self", "cls", "db", "session", "request", "response", "notes"})


def _capture_inputs(
    sig: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """함수 시그니처에서 입력값을 딕셔너리로 추출한다."""
    try:
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
    except TypeError:
        return {"_raw_args": [_safe_repr(a) for a in args[:5]]}

    result: dict[str, Any] = {}
    for name, value in bound.arguments.items():
        if name in _SKIP_PARAMS:
            continue
        try:
            result[name] = _safe_repr(value)
        except Exception:
            result[name] = "<unserializable>"
    return result


def _safe_repr(value: Any, max_len: int = 200) -> Any:
    """직렬화 가능한 표현으로 변환한다."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:max_len] if len(value) > max_len else value
    if isinstance(value, (list, tuple)):
        return [_safe_repr(v) for v in value[:10]]
    if isinstance(value, dict):
        return {str(k): _safe_repr(v) for k, v in list(value.items())[:20]}
    if hasattr(value, "id"):
        return f"<{type(value).__name__} id={value.id}>"
    if hasattr(value, "__dict__"):
        return f"<{type(value).__name__}>"
    return str(value)[:max_len]
