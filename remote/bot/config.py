"""
봇 설정 — .env 파일에서 환경 변수를 로드하여 BotConfig 인스턴스를 생성한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# remote/.env 로드
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_PATH)


@dataclass
class BotConfig:
    telegram_bot_token: str
    allowed_user_ids: list[int]
    project_root: Path
    default_model: str = "sonnet"
    claude_timeout: int = 300
    max_turns: int = 10
    max_budget_usd: float = 2.00
    log_level: str = "INFO"
    allowed_tools: list[str] = field(
        default_factory=lambda: ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
    )
    readonly_tools: list[str] = field(
        default_factory=lambda: ["Bash", "Read", "Glob", "Grep"]
    )


def load_config() -> BotConfig:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다. "
            "remote/.env 파일을 확인하세요."
        )

    raw_ids = os.environ.get("TELEGRAM_USER_IDS", "")
    if not raw_ids:
        raise ValueError(
            "TELEGRAM_USER_IDS 환경 변수가 설정되지 않았습니다. "
            "remote/.env 파일을 확인하세요."
        )
    user_ids = [int(uid.strip()) for uid in raw_ids.split(",") if uid.strip()]

    # 프로젝트 루트: remote/ 의 부모 디렉토리
    default_root = Path(__file__).resolve().parents[2]
    project_root = Path(os.environ.get("PROJECT_ROOT", str(default_root)))

    return BotConfig(
        telegram_bot_token=token,
        allowed_user_ids=user_ids,
        project_root=project_root,
        default_model=os.environ.get("DEFAULT_MODEL", "sonnet"),
        claude_timeout=int(os.environ.get("CLAUDE_TIMEOUT", "300")),
        max_turns=int(os.environ.get("MAX_TURNS", "10")),
        max_budget_usd=float(os.environ.get("MAX_BUDGET_USD", "2.00")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
