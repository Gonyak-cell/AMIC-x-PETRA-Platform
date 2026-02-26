"""일일 리포트 시스템 테스트 fixture."""

import sys
from pathlib import Path

import pytest

# 테스트 대상 모듈 import 경로 설정
_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
_shared_dir = str(Path(__file__).resolve().parent.parent.parent / "_shared")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
if _shared_dir not in sys.path:
    sys.path.insert(0, _shared_dir)


@pytest.fixture
def sample_error():
    """Python traceback 에러 레코드."""
    return {
        "ts": "2026-02-24T20:49:26",
        "session_id": "test-session-001",
        "event": "PostToolUseFailure",
        "tool_name": "Bash",
        "command": 'docker exec api python -c "from app.core.database import get_engine"',
        "return_code": 1,
        "error_snippet": (
            'Traceback (most recent call last):\n'
            '  File "/app/app/core/database.py", line 42\n'
            "ImportError: cannot import name 'get_engine'"
        ),
        "category": "test",
        "cwd": "C:\\Users\\test\\project",
    }


@pytest.fixture
def sample_error_with_tz():
    """타임존 포함 에러 레코드."""
    return {
        "ts": "2026-02-24T20:49:26+09:00",
        "session_id": "test-session-001",
        "event": "PostToolUseFailure",
        "tool_name": "Bash",
        "command": "python test.py",
        "return_code": 1,
        "error_snippet": "AssertionError: expected 42 got 0",
        "category": "test",
        "cwd": "/home/user/project",
    }


@pytest.fixture
def sample_commit():
    """fix 타입 커밋 레코드."""
    return {
        "hash": "abc1234",
        "full_hash": "abc1234567890",
        "timestamp": "2026-02-24 21:00:00 +0900",
        "subject": "fix(platform/dashboard): fix KPI loading state",
        "body": "",
        "type": "fix",
        "scope": "platform/dashboard",
        "files": ["app/core/database.py", "app/services/kpi.py"],
    }


@pytest.fixture
def sample_prompts():
    """세션 프롬프트 목록."""
    return [
        {
            "ts": "2026-02-24T20:48:00",
            "session_id": "test-session-001",
            "prompt": "KPI 로딩 상태 수정해줘",
            "category": "fix",
        },
        {
            "ts": "2026-02-24T20:49:10",
            "session_id": "test-session-001",
            "prompt": "database.py 임포트 확인해봐",
            "category": "review",
        },
        {
            "ts": "2026-02-24T20:50:30",
            "session_id": "test-session-001",
            "prompt": "다시 테스트 실행해줘",
            "category": "test",
        },
    ]
