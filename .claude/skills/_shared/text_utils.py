#!/usr/bin/env python3
"""공유 텍스트 유틸리티 함수.

이 모듈의 sanitize_str()는 다음 훅 파일에도 동일하게 복사되어 있다
(훅은 독립 프로세스로 실행되어 외부 import 불가):
- .claude/hooks/log-tool-error.py
- .claude/hooks/log-user-prompt.py
- .claude/hooks/daily-report-trigger.py

수정 시 위 파일들도 반드시 동시에 수정할 것.
"""

import re
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def sanitize_str(value: str) -> str:
    """Windows 한글 경로 등에서 발생하는 surrogate 문자 제거."""
    return value.encode("utf-8", errors="replace").decode("utf-8")


def normalize_snippet(snippet: str) -> str:
    """에러 스니펫 정규화 (비교용): 경로/숫자를 플레이스홀더로 치환."""
    text = snippet.lower()
    # 파일 경로 정규화
    text = re.sub(r"[a-z]:\\[^\s:]+", "[PATH]", text)
    text = re.sub(r"/[\w./\-]+", "[PATH]", text)
    # 라인 번호/숫자 정규화
    text = re.sub(r"\b\d+\b", "[N]", text)
    # 연속 공백 정리
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_timestamp(ts_str: str) -> datetime:
    """다양한 형식의 타임스탬프를 KST aware datetime으로 파싱.

    지원 형식:
    - "2026-02-24T20:49:26+09:00" (새 형식, ISO 8601 aware)
    - "2026-02-24T20:49:26" (기존 형식, naive → KST 가정)
    - "2026-02-26 19:52:23 +0900" (git log %ai 형식)
    """
    ts_str = ts_str.strip()

    # git log 형식: "2026-02-26 19:52:23 +0900"
    if len(ts_str) > 19 and (ts_str[-5] == "+" or ts_str[-5] == "-") and ts_str[-6] == " ":
        parts = ts_str.rsplit(" ", 1)
        if len(parts) == 2:
            dt_part = parts[0].replace(" ", "T")
            tz_part = parts[1]
            # "+0900" → "+09:00"
            if len(tz_part) == 5 and ":" not in tz_part:
                tz_part = tz_part[:3] + ":" + tz_part[3:]
            return datetime.fromisoformat(f"{dt_part}{tz_part}")

    # ISO 형식 시도
    dt = datetime.fromisoformat(ts_str)

    # naive datetime이면 KST로 가정 (기존 로그 하위 호환)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)

    return dt
