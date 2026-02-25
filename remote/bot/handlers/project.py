"""
프로젝트 전용 명령어 — Claude CLI 없이 직접 셸 실행 (비용 0).
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.claude_runner import run_shell
from bot.message_utils import split_message, truncate_output
from bot.security import owner_only

logger = logging.getLogger(__name__)

# 모듈별 테스트 명령 매핑
_TEST_COMMANDS: dict[str, str] = {
    "fdd": "cd fdd/backend && python -m pytest tests/ -v --tb=short",
    "kiis": "cd kiis && python -m pytest tests/ -v --tb=short",
    "im": "cd im && python -m pytest tests/ -v --tb=short",
    "deal-mgmt": "cd deal-mgmt && python -m pytest tests/ -v --tb=short",
    "ma": "cd deal-mgmt && python -m pytest tests/ -v --tb=short",
    "frontend": "cd amic-platform && npm run test",
}

# 모듈별 린트 명령 매핑
_LINT_COMMANDS: dict[str, str] = {
    "fdd": "cd fdd/backend && ruff check .",
    "kiis": "cd kiis && ruff check .",
    "im": "cd im && ruff check .",
    "deal-mgmt": "cd deal-mgmt && ruff check .",
    "ma": "cd deal-mgmt && ruff check .",
    "frontend": "cd amic-platform && npm run lint",
    "": "cd amic-platform && npm run lint",  # 기본값
}


async def _run_and_reply(
    update: Update, context: ContextTypes.DEFAULT_TYPE, cmd: str, timeout: int = 120
) -> None:
    """셸 명령 실행 후 결과를 전송하는 공통 헬퍼."""
    config = context.bot_data["config"]
    rate_limiter = context.bot_data.get("rate_limiter")
    cwd = context.bot_data.get("session", {}).get("cwd", str(config.project_root))

    if rate_limiter and not rate_limiter.check(update.effective_user.id):
        await update.message.reply_text(
            "⚠️ 속도 제한 초과 — 1분에 최대 5회 요청 가능합니다."
        )
        return

    await update.message.chat.send_action("typing")
    output = await run_shell(cmd, cwd=cwd, timeout=timeout)
    output = truncate_output(output, max_chars=3800)

    for part in split_message(output):
        await update.message.reply_text(part)


@owner_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_and_reply(update, context, "git status")


@owner_only
async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    try:
        n = int(args[0]) if args else 10
        n = min(max(1, n), 50)
    except ValueError:
        await update.message.reply_text("❌ 숫자를 입력하세요. 예: /log 10")
        return
    await _run_and_reply(update, context, f"git log --oneline -{n}")


@owner_only
async def cmd_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_and_reply(update, context, "git branch -a")


@owner_only
async def cmd_diff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_and_reply(update, context, "git diff --stat")


@owner_only
async def cmd_build(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔨 프론트엔드 빌드 시작...")
    await _run_and_reply(
        update, context, "cd amic-platform && npm run build", timeout=300
    )


@owner_only
async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    module = args[0].lower() if args else ""

    if not module:
        modules = ", ".join(_TEST_COMMANDS.keys())
        await update.message.reply_text(
            f"사용법: /test <module>\n사용 가능: {modules}"
        )
        return

    cmd = _TEST_COMMANDS.get(module)
    if not cmd:
        await update.message.reply_text(
            f"❌ 알 수 없는 모듈: {module}\n"
            f"사용 가능: {', '.join(_TEST_COMMANDS.keys())}"
        )
        return

    await update.message.reply_text(f"🧪 {module} 테스트 시작...")
    await _run_and_reply(update, context, cmd, timeout=300)


@owner_only
async def cmd_lint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    module = args[0].lower() if args else ""

    cmd = _LINT_COMMANDS.get(module)
    if not cmd:
        await update.message.reply_text(
            f"❌ 알 수 없는 모듈: {module}\n"
            f"사용 가능: {', '.join(k for k in _LINT_COMMANDS if k)}"
        )
        return

    await update.message.reply_text(f"🔍 린트 실행 중...")
    await _run_and_reply(update, context, cmd)


@owner_only
async def cmd_typecheck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔎 TypeScript 타입 검사 시작...")
    await _run_and_reply(
        update, context, "cd amic-platform && npx tsc -b --noEmit", timeout=180
    )
