"""통일 구조화 로깅 모듈.

모든 백엔드에서 동일한 JSON 로그 스키마를 사용한다.
기존 logging.getLogger(__name__) + logger.info/error 호출 변경 없이
핸들러/포매터 교체만으로 JSON 출력 전환.

JSON 스키마:
- 공통: timestamp, level, logger, message, service, module, function, line, request_id
- ERROR: error.error_code, error.type, error.message, error.stacktrace, error.input
- WARNING: warning.warning_code, warning.category (선택)
- HTTP: http.method, http.path, http.status_code, http.duration_ms (미들웨어)
"""

import json
import logging
import os
import sys
import traceback
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

SERVICE_NAME = "fdd"

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "authorization",
        "credit_card",
        "ssn",
        "jwt",
        "cookie",
        "access_token",
        "refresh_token",
        "private_key",
        "secret_key",
    }
)


class JSONFormatter(logging.Formatter):
    """통일 JSON 로그 포매터."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": SERVICE_NAME,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Request ID (ContextVar에서 자동 주입)
        try:
            from app.core.log_context import get_request_id

            request_id = get_request_id()
            if request_id:
                log_entry["request_id"] = request_id
        except ImportError:
            pass

        # 추가 컨텍스트 (extra={"ctx": {...}} 패턴 하위 호환)
        if hasattr(record, "ctx"):
            log_entry["context"] = record.ctx  # type: ignore[attr-defined]

        # ERROR: 스택 트레이스 + error 블록
        if record.exc_info and record.exc_info[1] is not None:
            exc_type, exc_value, exc_tb = record.exc_info
            error_block: dict[str, Any] = {
                "type": type(exc_value).__name__,
                "message": str(exc_value),
                "stacktrace": "".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                ),
            }

            # error_code 추출 (도메인 예외에서)
            if hasattr(exc_value, "code"):
                code = exc_value.code
                code_str = (
                    f"{SERVICE_NAME.upper()}-{code.value}"
                    if hasattr(code, "value")
                    else str(code)
                )
                error_block["error_code"] = code_str
            elif hasattr(exc_value, "error_code"):
                error_block["error_code"] = exc_value.error_code

            # 입력값 (데코레이터에서 extra={"error_input": {...}}로 주입)
            if hasattr(record, "error_input"):
                error_block["input"] = _sanitize(record.error_input)  # type: ignore[attr-defined]

            log_entry["error"] = error_block

        # WARNING: warning 블록 (선택적, extra={"warning_code": ...}로 주입)
        if hasattr(record, "warning_code"):
            log_entry["warning"] = {
                "warning_code": record.warning_code,  # type: ignore[attr-defined]
                "category": getattr(record, "warning_category", "general"),
            }

        # HTTP 블록 (미들웨어에서 extra={"http": {...}}로 주입)
        if hasattr(record, "http"):
            log_entry["http"] = record.http  # type: ignore[attr-defined]

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """개발 환경용 읽기 쉬운 텍스트 포매터."""

    def __init__(self) -> None:
        super().__init__(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    *,
    level: str = "INFO",
    json_output: bool = True,
    service_name: str | None = None,
    log_dir: str | None = None,
) -> None:
    """애플리케이션 로깅을 초기화한다.

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: True면 JSON 형식 (프로덕션), False면 텍스트 형식 (개발).
        service_name: 서비스 식별자 (기본값: 모듈 상수 SERVICE_NAME).
        log_dir: 로그 파일 저장 디렉토리. None이면 파일 저장 안 함.
            지정 시 {service}.log (전체) + {service}-error.log (ERROR+) 생성.
    """
    global SERVICE_NAME
    if service_name:
        SERVICE_NAME = service_name

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter() if json_output else TextFormatter())
    root.addHandler(handler)

    # 파일 핸들러 (log_dir 또는 LOG_DIR 환경변수)
    file_dir = log_dir or os.environ.get("LOG_DIR")
    if file_dir:
        _setup_file_handlers(file_dir)

    # 외부 라이브러리 소음 감소
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _setup_file_handlers(log_dir: str) -> None:
    """RotatingFileHandler를 루트 로거에 추가한다.

    생성 파일:
        {log_dir}/{SERVICE_NAME}.log       — 전체 로그 (10MB × 5 백업)
        {log_dir}/{SERVICE_NAME}-error.log — ERROR 이상 (10MB × 3 백업)
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    json_fmt = JSONFormatter()

    # 전체 로그 파일
    all_handler = RotatingFileHandler(
        log_path / f"{SERVICE_NAME}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    all_handler.setFormatter(json_fmt)
    root.addHandler(all_handler)

    # 에러 전용 로그 파일
    error_handler = RotatingFileHandler(
        log_path / f"{SERVICE_NAME}-error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_fmt)
    root.addHandler(error_handler)


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거를 반환한다.

    사용 예:
        logger = get_logger(__name__)
        logger.info("Deal created", extra={"ctx": {"deal_id": deal_id}})
    """
    return logging.getLogger(f"{SERVICE_NAME}.{name}")


# ── 민감정보 마스킹 ──────────────────────────────────────


def _sanitize(data: Any, depth: int = 0) -> Any:
    """민감정보를 재귀적으로 마스킹한다."""
    if depth > 5:
        return "..."
    if isinstance(data, dict):
        return {
            k: "***MASKED***"
            if k.lower() in _SENSITIVE_KEYS
            else _sanitize(v, depth + 1)
            for k, v in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [_sanitize(item, depth + 1) for item in data[:20]]
    if isinstance(data, str) and len(data) > 1000:
        return data[:500] + f"...(truncated {len(data)} chars)"
    return data


def mask_amount(amount: str | int | float) -> str:
    """금액 문자열을 마스킹한다.

    예: 123,456,789 → 1**,***,**9
        1234567 → 1*****7
    """
    s = str(amount).replace(",", "").replace(" ", "")

    prefix = ""
    if s.startswith("-"):
        prefix = "-"
        s = s[1:]

    if len(s) <= 2:
        return prefix + s

    return prefix + s[0] + "*" * (len(s) - 2) + s[-1]
