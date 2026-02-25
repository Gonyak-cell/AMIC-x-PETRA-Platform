"""
세션·모델 관리 명령어 — /session, /reset, /model, /cost, /budget
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.security import owner_only


@owner_only
async def cmd_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = context.bot_data.setdefault("session", {})
    args = context.args

    if not args:
        status = "ON ✅" if session.get("continue") else "OFF ⬜"
        await update.message.reply_text(
            f"세션 모드: {status}\n"
            "사용법: /session on|off\n\n"
            "ON = --continue 플래그로 다중 턴 대화\n"
            "OFF = 매 메시지 독립 처리 (기본)"
        )
        return

    mode = args[0].lower()
    if mode == "on":
        session["continue"] = True
        await update.message.reply_text("✅ 세션 모드 ON — 다중 턴 대화가 활성화되었습니다.")
    elif mode == "off":
        session["continue"] = False
        await update.message.reply_text("⬜ 세션 모드 OFF — 단발 모드로 전환되었습니다.")
    else:
        await update.message.reply_text("사용법: /session on|off")


@owner_only
async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    session = context.bot_data.setdefault("session", {})
    session["continue"] = False
    session["cwd"] = str(config.project_root)
    session["model"] = config.default_model
    session["budget"] = config.max_budget_usd
    context.bot_data["cost_tracker"] = {"total_usd": 0.0}
    await update.message.reply_text(
        "🔄 세션 초기화 완료\n"
        f"  디렉토리: (프로젝트 루트)\n"
        f"  모델: {config.default_model}\n"
        f"  예산: ${config.max_budget_usd:.2f}\n"
        "  누적 비용: $0.00"
    )


@owner_only
async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = context.bot_data.setdefault("session", {})
    args = context.args

    valid_models = {"sonnet", "opus", "haiku"}

    if not args:
        current = session.get("model", context.bot_data["config"].default_model)
        await update.message.reply_text(
            f"현재 모델: {current}\n"
            f"사용법: /model {{{' | '.join(sorted(valid_models))}}}"
        )
        return

    model = args[0].lower()
    if model not in valid_models:
        await update.message.reply_text(
            f"❌ 유효하지 않은 모델: {model}\n"
            f"사용 가능: {', '.join(sorted(valid_models))}"
        )
        return

    session["model"] = model
    await update.message.reply_text(f"🧠 모델 전환: {model}")


@owner_only
async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tracker = context.bot_data.get("cost_tracker", {"total_usd": 0.0})
    total = tracker.get("total_usd", 0.0)
    await update.message.reply_text(f"💰 이번 세션 누적 비용: ${total:.4f}")


@owner_only
async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = context.bot_data.setdefault("session", {})
    args = context.args

    if not args:
        current = session.get("budget", context.bot_data["config"].max_budget_usd)
        await update.message.reply_text(
            f"현재 요청당 예산 상한: ${current:.2f}\n"
            "사용법: /budget <USD 금액>"
        )
        return

    try:
        amount = float(args[0])
        if amount <= 0 or amount > 50:
            raise ValueError
    except (ValueError, IndexError):
        await update.message.reply_text("❌ 0~50 사이의 숫자를 입력하세요. 예: /budget 5.00")
        return

    session["budget"] = amount
    await update.message.reply_text(f"💰 요청당 예산 상한 변경: ${amount:.2f}")
