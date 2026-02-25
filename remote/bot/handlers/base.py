"""
기본 명령어 핸들러 — /start, /help, /ping, /myid
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.security import owner_only


@owner_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    await update.message.reply_text(
        "🤖 AMIC x PETRA — Claude Code 원격 제어 봇\n\n"
        "아무 메시지를 보내면 Claude Code가 처리합니다.\n\n"
        "📋 명령어:\n"
        "  /help — 전체 도움말\n"
        "  /ping — 봇 상태 확인\n"
        "  /status — git status\n"
        "  /log — 최근 커밋\n"
        "  /build — 프론트엔드 빌드\n"
        "  /test [module] — 테스트 실행\n"
        "  /cd [path] — 작업 디렉토리 변경\n"
        "  /model [name] — 모델 전환\n"
        "  /cost — 누적 비용\n\n"
        f"✅ 프로젝트: {config.project_root.name}\n"
        f"🧠 모델: {config.default_model}"
    )


@owner_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 AMIC x PETRA Telegram Bot 도움말\n\n"
        "━━━ 기본 ━━━\n"
        "/start — 시작 안내\n"
        "/help — 이 도움말\n"
        "/ping — 봇 생존 확인\n"
        "/myid — 내 텔레그램 ID\n\n"
        "━━━ Git ━━━\n"
        "/status — git status\n"
        "/log [N] — 최근 N개 커밋 (기본 10)\n"
        "/branch — 브랜치 목록\n"
        "/diff — diff 요약\n\n"
        "━━━ 빌드·테스트 ━━━\n"
        "/build — 프론트엔드 빌드\n"
        "/test fdd|kiis|deal-mgmt|frontend\n"
        "/lint [module] — 린트\n"
        "/typecheck — TypeScript 타입 검사\n\n"
        "━━━ 네비게이션 ━━━\n"
        "/cd fdd|kiis|im|deal-mgmt|frontend|root\n"
        "/pwd — 현재 디렉토리\n"
        "/ls [path] — 디렉토리 목록\n\n"
        "━━━ 파일 ━━━\n"
        "/cat <path> — 파일 내용 보기\n"
        "/getfile <path> — 파일 다운로드\n\n"
        "━━━ 세션·모델 ━━━\n"
        "/session on|off — 다중 턴 대화\n"
        "/reset — 세션 초기화\n"
        "/model sonnet|opus — 모델 전환\n"
        "/cost — 누적 비용\n"
        "/budget <USD> — 요청당 비용 상한\n\n"
        "⏱ 응답 대기: 최대 5분\n"
        "📏 긴 응답은 자동 분할됩니다"
    )


@owner_only
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🏓 Pong! 봇이 정상 작동 중입니다.")


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """인증 없이 누구나 사용 가능 — ID 확인용."""
    user_id = update.effective_user.id
    await update.message.reply_text(f"📋 당신의 텔레그램 ID: {user_id}")
