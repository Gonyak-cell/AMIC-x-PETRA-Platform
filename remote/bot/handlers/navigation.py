"""
네비게이션 명령어 — /cd, /pwd, /ls
"""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.message_utils import split_message
from bot.security import owner_only

logger = logging.getLogger(__name__)

# 모듈 단축 별칭
_ALIASES: dict[str, str] = {
    "fdd": "fdd/backend",
    "kiis": "kiis",
    "im": "im",
    "deal-mgmt": "deal-mgmt",
    "ma": "deal-mgmt",
    "frontend": "amic-platform",
    "platform": "amic-platform",
    "root": ".",
    ".": ".",
}


@owner_only
async def cmd_cd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    session = context.bot_data.setdefault("session", {})
    args = context.args

    if not args:
        aliases = ", ".join(sorted(_ALIASES.keys()))
        await update.message.reply_text(
            f"사용법: /cd <path>\n단축 별칭: {aliases}"
        )
        return

    target = args[0]
    resolved = _ALIASES.get(target, target)

    if resolved == ".":
        new_cwd = config.project_root
    else:
        new_cwd = (config.project_root / resolved).resolve()

    # 프로젝트 루트 밖으로 이탈 방지
    try:
        new_cwd.relative_to(config.project_root)
    except ValueError:
        await update.message.reply_text("❌ 프로젝트 루트 밖으로는 이동할 수 없습니다.")
        return

    if not new_cwd.is_dir():
        await update.message.reply_text(f"❌ 디렉토리가 존재하지 않습니다: {resolved}")
        return

    session["cwd"] = str(new_cwd)
    relative = new_cwd.relative_to(config.project_root)
    display = str(relative) if str(relative) != "." else "(프로젝트 루트)"
    await update.message.reply_text(f"📂 작업 디렉토리 변경: {display}")


@owner_only
async def cmd_pwd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    session = context.bot_data.get("session", {})
    cwd = Path(session.get("cwd", str(config.project_root)))

    try:
        relative = cwd.relative_to(config.project_root)
        display = str(relative) if str(relative) != "." else "(프로젝트 루트)"
    except ValueError:
        display = str(cwd)

    await update.message.reply_text(f"📂 현재 디렉토리: {display}")


@owner_only
async def cmd_ls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    session = context.bot_data.get("session", {})
    cwd = session.get("cwd", str(config.project_root))
    args = context.args
    target = args[0] if args else "."

    # 경로 검증
    full_path = (Path(cwd) / target).resolve()
    try:
        full_path.relative_to(config.project_root)
    except ValueError:
        await update.message.reply_text("❌ 프로젝트 루트 밖은 조회할 수 없습니다.")
        return

    if not full_path.is_dir():
        await update.message.reply_text(f"❌ 디렉토리가 존재하지 않습니다: {target}")
        return

    try:
        entries = sorted(full_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        lines = [f"{'📁 ' if e.is_dir() else '  '}{e.name}" for e in entries]
        output = "\n".join(lines) or "(빈 디렉토리)"
    except PermissionError:
        output = "❌ 접근 권한이 없습니다."

    for part in split_message(output):
        await update.message.reply_text(part)
