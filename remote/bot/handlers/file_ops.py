"""
파일 조작 명령어 — /cat, /getfile
"""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.message_utils import split_message, truncate_output
from bot.security import owner_only

logger = logging.getLogger(__name__)

# 보안: 접근 차단 패턴
_BLOCKED_PATTERNS = {".env", ".git", ".pem", ".key", ".p12", ".pfx", "credentials"}


def _is_blocked(path: Path) -> bool:
    """보안상 접근이 차단된 파일인지 확인한다."""
    name_lower = path.name.lower()
    for pattern in _BLOCKED_PATTERNS:
        if pattern in name_lower:
            return True
    # .git/ 디렉토리 내부
    for parent in path.parents:
        if parent.name == ".git":
            return True
    return False


def _resolve_path(
    file_path: str, cwd: str, project_root: Path
) -> tuple[Path | None, str | None]:
    """경로를 검증하고 절대 경로로 해석한다. 오류 시 (None, 메시지) 반환."""
    resolved = (Path(cwd) / file_path).resolve()

    try:
        resolved.relative_to(project_root)
    except ValueError:
        return None, "❌ 프로젝트 루트 밖의 파일은 접근할 수 없습니다."

    if _is_blocked(resolved):
        return None, "🔒 보안상 이 파일에 접근할 수 없습니다."

    if not resolved.is_file():
        return None, f"❌ 파일을 찾을 수 없습니다: {file_path}"

    return resolved, None


@owner_only
async def cmd_cat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    session = context.bot_data.get("session", {})
    cwd = session.get("cwd", str(config.project_root))
    args = context.args

    if not args:
        await update.message.reply_text("사용법: /cat <파일 경로>")
        return

    file_path = " ".join(args)
    resolved, error = _resolve_path(file_path, cwd, config.project_root)
    if error:
        await update.message.reply_text(error)
        return

    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        await update.message.reply_text(f"❌ 파일 읽기 오류: {e}")
        return

    if not content.strip():
        await update.message.reply_text("(빈 파일)")
        return

    # 파일 확장자로 언어 힌트
    ext = resolved.suffix.lstrip(".")
    header = f"📄 {resolved.name}\n"

    content = truncate_output(content, max_chars=3600)
    text = f"{header}```{ext}\n{content}\n```"

    for part in split_message(text):
        await update.message.reply_text(part)


@owner_only
async def cmd_getfile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    session = context.bot_data.get("session", {})
    cwd = session.get("cwd", str(config.project_root))
    args = context.args

    if not args:
        await update.message.reply_text("사용법: /getfile <파일 경로>")
        return

    file_path = " ".join(args)
    resolved, error = _resolve_path(file_path, cwd, config.project_root)
    if error:
        await update.message.reply_text(error)
        return

    # 50MB 제한
    size_mb = resolved.stat().st_size / (1024 * 1024)
    if size_mb > 50:
        await update.message.reply_text(
            f"❌ 파일이 너무 큽니다 ({size_mb:.1f}MB). 텔레그램 제한: 50MB"
        )
        return

    try:
        with open(resolved, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=resolved.name,
            )
    except Exception as e:
        await update.message.reply_text(f"❌ 파일 전송 오류: {e}")
