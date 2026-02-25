"""
자유 텍스트 핸들러 — 일반 메시지를 claude -p 로 전달한다.
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.claude_runner import run_claude
from bot.message_utils import format_cost_info, split_message
from bot.security import owner_only

logger = logging.getLogger(__name__)


@owner_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """사용자 텍스트 → Claude Code CLI → 응답 회신."""
    config = context.bot_data["config"]
    rate_limiter = context.bot_data["rate_limiter"]
    session = context.bot_data.setdefault("session", {})
    cost_tracker = context.bot_data.setdefault("cost_tracker", {"total_usd": 0.0})

    user_id = update.effective_user.id
    user_message = update.message.text
    logger.info("[수신] %s: %s", user_id, user_message[:80])

    # 속도 제한 확인
    if not rate_limiter.check(user_id):
        await update.message.reply_text(
            "⚠️ 속도 제한 초과 — 1분에 최대 5회 요청 가능합니다. 잠시 후 다시 시도하세요."
        )
        return

    # typing indicator를 주기적으로 갱신
    stop_typing = asyncio.Event()

    async def keep_typing():
        while not stop_typing.is_set():
            try:
                await update.message.chat.send_action("typing")
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop_typing.wait(), timeout=4.0)
                break
            except asyncio.TimeoutError:
                continue

    typing_task = asyncio.create_task(keep_typing())

    # 세션 상태
    cwd = session.get("cwd", str(config.project_root))
    continue_session = session.get("continue", False)
    model = session.get("model", config.default_model)
    budget = session.get("budget", config.max_budget_usd)

    try:
        result = await run_claude(
            user_message,
            cwd=cwd,
            allowed_tools=config.allowed_tools,
            continue_session=continue_session,
            model=model,
            max_turns=config.max_turns,
            max_budget_usd=budget,
            timeout=config.claude_timeout,
        )
    finally:
        stop_typing.set()
        await typing_task

    # 비용 누적
    if result.cost_usd:
        cost_tracker["total_usd"] += result.cost_usd

    # 응답 전송
    parts = split_message(result.text)
    for i, part in enumerate(parts):
        try:
            await update.message.reply_text(part)
        except Exception as e:
            await update.message.reply_text(f"⚠️ 메시지 전송 오류: {e}")
            break
        if i < len(parts) - 1:
            await asyncio.sleep(0.3)

    # 비용 정보 추가
    cost_line = format_cost_info(
        result.cost_usd, result.input_tokens, result.output_tokens, result.duration_seconds
    )
    if cost_line:
        await update.message.reply_text(cost_line)

    logger.info("[완료] %s파트, %.1fs", len(parts), result.duration_seconds)
