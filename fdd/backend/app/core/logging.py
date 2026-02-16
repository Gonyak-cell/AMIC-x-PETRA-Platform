"""구조화 로깅 설정 (마스터파일 §4.5).

규칙:
- JSON 형식 구조화 로그 (ELK/Grafana 연동 대비)
- 컨텍스트 필수 포함 (전표번호/파일명/사용자 등)
- 개인정보 절대 포함 금지
- 금액 로그 마스킹 처리
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포매터."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 추가 컨텍스트 (deal_id, file_name, user 등)
        if hasattr(record, "ctx"):
            log_entry["context"] = record.ctx  # type: ignore[attr-defined]

        # 예외 정보
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging(*, level: str = "INFO", json_output: bool = True) -> None:
    """애플리케이션 로깅을 초기화한다.

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: True면 JSON 형식, False면 표준 텍스트 형식 (개발용).
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 기존 핸들러 제거
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거를 반환한다.

    사용 예:
        logger = get_logger(__name__)
        logger.info("Deal created", extra={"ctx": {"deal_id": deal_id}})
    """
    return logging.getLogger(f"fdd.{name}")


def mask_amount(amount: str | int | float) -> str:
    """금액 문자열을 마스킹한다 (마스터파일 §4.5: 금액 로그 마스킹).

    예: 123,456,789 → 1**,***,**9
        1234567 → 1*****7
    """
    s = str(amount).replace(",", "").replace(" ", "")

    # 숫자가 아닌 부분(부호, 소수점) 처리
    prefix = ""
    if s.startswith("-"):
        prefix = "-"
        s = s[1:]

    if len(s) <= 2:
        return prefix + s

    return prefix + s[0] + "*" * (len(s) - 2) + s[-1]
