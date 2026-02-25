"""
AMIC x PETRA Platform — Telegram Bot 진입점.
python -m bot.main 으로 실행한다.
"""

from __future__ import annotations

import logging
import sys

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import load_config
from bot.handlers.base import cmd_help, cmd_myid, cmd_ping, cmd_start
from bot.handlers.file_ops import cmd_cat, cmd_getfile
from bot.handlers.general import handle_message
from bot.handlers.navigation import cmd_cd, cmd_ls, cmd_pwd
from bot.handlers.project import (
    cmd_branch,
    cmd_build,
    cmd_diff,
    cmd_lint,
    cmd_log,
    cmd_status,
    cmd_test,
    cmd_typecheck,
)
from bot.handlers.session import cmd_budget, cmd_cost, cmd_model, cmd_reset, cmd_session
from bot.security import RateLimiter


def main() -> None:
    try:
        config = load_config()
    except ValueError as e:
        print(f"❌ 설정 오류: {e}")
        sys.exit(1)

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        level=getattr(logging, config.log_level.upper(), logging.INFO),
    )
    logger = logging.getLogger(__name__)

    print("=" * 55)
    print("🤖 AMIC x PETRA — Claude Code Telegram Bot")
    print(f"   프로젝트: {config.project_root}")
    print(f"   모델: {config.default_model}")
    print(f"   허가 사용자: {config.allowed_user_ids}")
    print("   종료: Ctrl+C")
    print("=" * 55)

    app = Application.builder().token(config.telegram_bot_token).build()

    # 공유 데이터
    app.bot_data["config"] = config
    app.bot_data["rate_limiter"] = RateLimiter(max_per_minute=5)
    app.bot_data["session"] = {"cwd": str(config.project_root), "continue": False}
    app.bot_data["cost_tracker"] = {"total_usd": 0.0}

    # 기본 명령어
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("myid", cmd_myid))

    # Git 명령어
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CommandHandler("branch", cmd_branch))
    app.add_handler(CommandHandler("diff", cmd_diff))

    # 빌드·테스트
    app.add_handler(CommandHandler("build", cmd_build))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CommandHandler("lint", cmd_lint))
    app.add_handler(CommandHandler("typecheck", cmd_typecheck))

    # 네비게이션
    app.add_handler(CommandHandler("cd", cmd_cd))
    app.add_handler(CommandHandler("pwd", cmd_pwd))
    app.add_handler(CommandHandler("ls", cmd_ls))

    # 파일
    app.add_handler(CommandHandler("cat", cmd_cat))
    app.add_handler(CommandHandler("getfile", cmd_getfile))

    # 세션·모델
    app.add_handler(CommandHandler("session", cmd_session))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("cost", cmd_cost))
    app.add_handler(CommandHandler("budget", cmd_budget))

    # 자유 텍스트 (마지막에 등록)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("봇 폴링 시작")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
