# 텔레그램 봇으로 Claude Code를 원격 제어하는 완전 가이드

**텔레그램 메시지 하나로 집 PC의 Claude Code를 원격 조종할 수 있습니다.** 핵심은 Claude Code CLI의 `-p` (print) 모드입니다. 이 모드는 대화형 인터페이스 없이 명령 하나를 실행하고 결과를 텍스트로 출력한 뒤 종료합니다. Python으로 텔레그램 봇을 만들어 이 `-p` 모드와 연결하면, 외출 중 모바일에서 메시지를 보내고 PC의 Claude Code 응답을 받는 구조가 완성됩니다. 이미 이 용도로 만들어진 오픈소스 프로젝트도 여러 개 존재하며, 그중 **TeleClaude**는 Windows 전용으로 설계되어 초보자에게 가장 접근성이 높습니다.

이 가이드는 두 가지 방법을 모두 다룹니다. **방법 A**는 기존 오픈소스 TeleClaude를 바로 사용하는 것이고, **방법 B**는 직접 Python 스크립트를 처음부터 만드는 것입니다.

---

## 1단계: 텔레그램 봇 만들기 (BotFather)

두 방법 모두 텔레그램 봇이 필요합니다. 아래 절차는 **5분이면 완료**됩니다.

**봇 생성 절차:**

1. 텔레그램 앱에서 검색창에 `@BotFather`를 입력하고, 파란색 체크 표시가 있는 공식 계정을 선택합니다
2. "시작" 또는 "Start" 버튼을 누릅니다
3. `/newbot` 이라고 메시지를 보냅니다
4. 봇의 **표시 이름**을 입력합니다 (예: `내 Claude 봇`)
5. 봇의 **사용자명**을 입력합니다 — 반드시 `bot`으로 끝나야 합니다 (예: `my_claude_helper_bot`)
6. BotFather가 **API 토큰**을 보내줍니다. `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` 형태입니다. **이 토큰은 비밀번호처럼 절대 다른 사람에게 공개하면 안 됩니다**

**본인 텔레그램 ID 확인 (보안에 필수):**

7. 텔레그램에서 `@userinfobot`을 검색하여 대화를 시작합니다
8. 아무 메시지나 보내면 숫자로 된 **사용자 ID** (예: `987654321`)를 알려줍니다
9. 이 숫자를 메모해 둡니다 — 봇을 본인만 사용할 수 있도록 제한하는 데 사용합니다

---

## 방법 A: TeleClaude 오픈소스 프로젝트 사용 (가장 빠른 방법)

**TeleClaude** (`github.com/zertac/TeleClaude`)는 Windows 전용으로 설계된 텔레그램-Claude Code 연결 봇입니다. `.bat` 파일 더블클릭만으로 실행·중지·자동시작이 가능해 초보자에게 적합합니다. 대화 기억, 작업 폴더 변경(`/cd`), 파일 다운로드(`/getfile`) 기능을 내장하고 있습니다.

**설치 절차:**

```
1. https://github.com/zertac/TeleClaude 에서 "Code" → "Download ZIP" 클릭
2. 원하는 폴더에 압축 해제 (예: C:\TeleClaude)
3. 폴더 안의 config.json 파일을 메모장으로 열어서 수정:
```

```json
{
    "telegram_bot_token": "여기에_BotFather에서_받은_토큰_붙여넣기",
    "allowed_user_ids": [여기에_본인_텔레그램_숫자ID],
    "working_dir": "C:\\Projects"
}
```

```
4. 명령 프롬프트(cmd)에서 해당 폴더로 이동 후:
   pip install -r requirements.txt
5. bot_start.bat 더블클릭으로 실행
6. 텔레그램에서 만든 봇에게 메시지 보내기 — 끝!
```

**주요 명령어:** `/reset`(대화 초기화), `/cd 경로`(작업 폴더 변경), `/pwd`(현재 폴더 확인), `/getfile 파일경로`(파일 다운로드). Windows 시작 시 자동 실행하려면 `install_startup.bat`을 더블클릭합니다.

> ⚠️ **보안 주의:** TeleClaude는 `--dangerously-skip-permissions` 플래그를 사용합니다. Claude가 PC의 파일을 자유롭게 읽고 쓸 수 있으므로, 반드시 `allowed_user_ids`를 설정하여 본인만 접근하도록 제한하세요.

---

## 방법 B: 직접 Python 스크립트 만들기 (권장 — 더 안전하고 커스터마이징 가능)

### 2단계: Python 환경 준비

**Python 설치 확인:**
```
Windows 키 + R → cmd 입력 → 확인
python --version
```

`Python 3.10` 이상이 표시되면 됩니다. 설치되어 있지 않다면 `python.org`에서 다운로드 후, 설치 시 **"Add Python to PATH" 체크박스를 반드시 선택**합니다.

**필요한 라이브러리 설치:**
```
pip install python-telegram-bot --upgrade
```

**Claude Code CLI 확인:**
```
claude --version
```

버전이 표시되면 준비 완료입니다. Claude Code는 이미 설치·사용 중이라고 가정합니다.

### 3단계: 환경 변수 설정

봇 토큰과 사용자 ID를 코드에 직접 쓰지 않고 환경 변수로 관리하는 것이 안전합니다.

**Windows에서 환경 변수 설정 (영구 적용):**

1. Windows 검색에서 "환경 변수" 입력 → "시스템 환경 변수 편집" 클릭
2. "환경 변수(N)" 버튼 클릭
3. "사용자 변수"에서 "새로 만들기" 클릭
4. 아래 두 개를 각각 추가:

| 변수 이름 | 변수 값 |
|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | BotFather에서 받은 토큰 |
| `TELEGRAM_USER_ID` | @userinfobot에서 확인한 숫자 ID |

5. 확인 → 확인 → 확인으로 모두 닫기
6. **열려 있는 CMD/VS Code를 모두 닫고 다시 열기** (환경 변수 적용을 위해)

### 4단계: 전체 스크립트 작성

VS Code에서 새 파일을 만들고 `claude_telegram_bot.py`로 저장합니다. 아래 코드를 **전체 복사하여 붙여넣기**합니다.

```python
"""
텔레그램 봇을 통한 Claude Code CLI 원격 제어 스크립트
=====================================================
사용법: python claude_telegram_bot.py
종료: Ctrl + C
"""

import os
import asyncio
import logging
from functools import wraps
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================
# 설정값 (환경 변수에서 읽어옵니다)
# ============================================================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))
CLAUDE_TIMEOUT = 300  # Claude 응답 대기 최대 시간 (초). 5분 = 300초
MAX_TELEGRAM_LENGTH = 4096  # 텔레그램 메시지 최대 길이

# ============================================================
# 로깅 설정
# ============================================================
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# 보안: 허가된 사용자만 봇을 사용할 수 있도록 제한
# ============================================================
def owner_only(func):
    """본인만 사용 가능하도록 제한하는 데코레이터"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != ALLOWED_USER_ID:
            logger.warning(f"[차단] 허가되지 않은 사용자 접근 시도: {user_id}")
            return  # 무응답 (봇 존재를 노출하지 않음)
        return await func(update, context, *args, **kwargs)
    return wrapper

# ============================================================
# 긴 메시지를 텔레그램 제한에 맞게 분할
# ============================================================
def split_message(text: str) -> list[str]:
    """4096자 제한에 맞춰 메시지를 분할합니다."""
    if len(text) <= MAX_TELEGRAM_LENGTH:
        return [text]

    parts = []
    while text:
        if len(text) <= MAX_TELEGRAM_LENGTH:
            parts.append(text)
            break

        chunk = text[:MAX_TELEGRAM_LENGTH]
        # 줄바꿈 위치에서 자르기 시도
        split_at = chunk.rfind("\n")
        if split_at == -1:
            # 공백 위치에서 자르기 시도
            split_at = chunk.rfind(" ")
        if split_at == -1:
            # 어쩔 수 없이 강제 분할
            split_at = MAX_TELEGRAM_LENGTH

        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return parts

# ============================================================
# Claude Code CLI 실행 함수
# ============================================================
async def run_claude(prompt: str) -> str:
    """
    claude -p 명령어를 비대화형으로 실행하고 결과를 반환합니다.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=CLAUDE_TIMEOUT
        )

        result = ""
        if stdout:
            result += stdout.decode("utf-8", errors="replace")
        if stderr:
            error_text = stderr.decode("utf-8", errors="replace").strip()
            if error_text:
                result += f"\n\n⚠️ [오류 출력]\n{error_text}"

        if not result.strip():
            result = "(응답이 비어 있습니다)"

        return result.strip()

    except asyncio.TimeoutError:
        try:
            proc.kill()
        except OSError:
            pass
        return f"⏰ Claude가 {CLAUDE_TIMEOUT}초 안에 응답하지 못했습니다. 더 짧은 질문을 시도해보세요."

    except FileNotFoundError:
        return (
            "❌ 'claude' 명령어를 찾을 수 없습니다.\n"
            "Claude Code CLI가 설치되어 있고 PATH에 등록되어 있는지 확인하세요.\n"
            "CMD에서 'claude --version' 을 실행해보세요."
        )

    except Exception as e:
        return f"❌ 오류가 발생했습니다: {type(e).__name__}: {e}"

# ============================================================
# 텔레그램 명령어 핸들러
# ============================================================
@owner_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """시작 명령어"""
    await update.message.reply_text(
        "🤖 Claude Code 원격 제어 봇이 작동 중입니다!\n\n"
        "사용법: 아무 메시지나 보내면 Claude Code가 처리합니다.\n\n"
        "명령어:\n"
        "  /start — 이 안내 메시지\n"
        "  /help — 도움말\n"
        "  /ping — 봇 작동 확인\n"
        f"  /myid — 내 텔레그램 ID 확인\n\n"
        f"✅ 인증된 사용자: {ALLOWED_USER_ID}"
    )

@owner_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """도움말"""
    await update.message.reply_text(
        "📖 사용 안내\n\n"
        "일반 텍스트 메시지를 보내면 다음과 같이 실행됩니다:\n"
        '  claude -p "보낸 메시지 내용"\n\n'
        "Claude Code가 응답을 생성하면 텔레그램으로 돌려보내줍니다.\n\n"
        "⏱ 응답 대기 시간: 최대 5분\n"
        "📏 긴 응답은 자동으로 여러 메시지로 분할됩니다."
    )

@owner_only
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """봇 생존 확인"""
    await update.message.reply_text("🏓 Pong! 봇이 정상 작동 중입니다.")

async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """사용자 ID 확인 (인증 없이 모든 사용자 가능)"""
    user_id = update.effective_user.id
    await update.message.reply_text(f"📋 당신의 텔레그램 ID: {user_id}")

# ============================================================
# 핵심: 일반 메시지를 Claude에 전달
# ============================================================
@owner_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """사용자가 보낸 텍스트를 Claude Code CLI로 전달하고 결과를 회신합니다."""
    user_message = update.message.text
    logger.info(f"[수신] {user_message[:80]}...")

    # "입력 중..." 표시
    await update.message.chat.send_action("typing")

    # Claude Code 실행
    response = await run_claude(user_message)

    # 응답 분할 전송
    parts = split_message(response)
    for i, part in enumerate(parts):
        try:
            await update.message.reply_text(part)
        except Exception as e:
            await update.message.reply_text(f"⚠️ 메시지 전송 오류: {e}")
            break
        if i < len(parts) - 1:
            await asyncio.sleep(0.3)

    logger.info(f"[완료] 응답 {len(parts)}개 메시지 전송")

# ============================================================
# 메인 실행
# ============================================================
def main() -> None:
    # 설정값 검증
    if not BOT_TOKEN:
        print("❌ 오류: TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
        print("   Windows 환경 변수에 봇 토큰을 등록하세요.")
        return

    if ALLOWED_USER_ID == 0:
        print("❌ 오류: TELEGRAM_USER_ID 환경 변수가 설정되지 않았습니다.")
        print("   텔레그램에서 @userinfobot 으로 ID를 확인한 후 등록하세요.")
        return

    print("=" * 50)
    print("🤖 Claude Code 텔레그램 봇 시작")
    print(f"   허가된 사용자 ID: {ALLOWED_USER_ID}")
    print("   종료하려면 Ctrl+C 를 누르세요")
    print("=" * 50)

    # 봇 빌드
    app = Application.builder().token(BOT_TOKEN).build()

    # 핸들러 등록
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 폴링 시작 (무한 루프)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
```

### 5단계: 실행 및 테스트

**VS Code 터미널에서 실행:**

1. VS Code를 엽니다 (환경 변수 설정 후 재시작 필수)
2. 터미널을 엽니다 (`Ctrl + ~` 또는 상단 메뉴 → 터미널 → 새 터미널)
3. 스크립트가 저장된 폴더로 이동합니다:
```
cd C:\내_프로젝트_폴더
```
4. 실행합니다:
```
python claude_telegram_bot.py
```
5. `🤖 Claude Code 텔레그램 봇 시작` 메시지가 나타나면 성공입니다
6. 텔레그램 앱에서 만든 봇에게 `/start`를 보내보세요
7. 아무 질문이나 보내면 Claude Code가 응답합니다 (예: `Python으로 구구단 코드 짜줘`)

---

## Claude Code `-p` 모드의 핵심 옵션들

`claude -p` 명령은 단발성 질의-응답 구조로 동작합니다. 대화형 UI 없이 질문 하나를 처리하고 결과를 stdout으로 출력한 뒤 종료합니다. 메모리 사용량이 대화형 모드의 절반 수준(**약 512MB**)이라 백그라운드 실행에 적합합니다.

위 스크립트는 가장 기본적인 `claude -p "메시지"` 형태를 사용합니다. 필요에 따라 `run_claude` 함수의 명령어를 수정하여 아래 옵션을 추가할 수 있습니다.

| 옵션 | 용도 | 예시 |
|------|------|------|
| `--model opus` | 모델 지정 | 더 강력한 모델로 변경 |
| `--output-format json` | JSON 출력 | 비용·토큰 정보 포함 |
| `--max-turns 5` | 에이전트 턴 제한 | 무한 루프 방지 |
| `--max-budget-usd 1.00` | 비용 상한 | 예산 초과 방지 |
| `--allowedTools "Read,Bash"` | 도구 허용 | 특정 도구만 사용 가능 |
| `--append-system-prompt "..."` | 시스템 프롬프트 추가 | 응답 스타일 커스터마이징 |

예를 들어, Claude가 파일을 읽고 Bash 명령을 실행할 수 있게 하려면 `run_claude` 함수에서 명령어를 이렇게 수정합니다:

```python
proc = await asyncio.create_subprocess_exec(
    "claude", "-p", prompt,
    "--allowedTools", "Read,Bash,Write,Edit",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

> ⚠️ **중요:** `-p` 모드에서는 도구 사용 권한이 기본적으로 전부 거부됩니다. `--allowedTools`로 명시적으로 허용하거나 `--dangerously-skip-permissions`로 전체 권한을 열어야 합니다. 후자는 보안상 위험하므로 `--allowedTools`로 필요한 도구만 허용하는 것이 안전합니다.

---

## PC가 켜져 있을 때 자동 실행하는 방법

### 방법 1: Windows 작업 스케줄러 (권장)

1. `Win + R` → `taskschd.msc` 입력 → 확인
2. 오른쪽 "작업 만들기" 클릭 (기본 작업 만들기가 아닌 **"작업 만들기"**)
3. **일반 탭:** 이름을 `Claude Telegram Bot`으로 입력. "사용자가 로그온할 때만 실행" 선택
4. **트리거 탭:** "새로 만들기" → **"로그온할 때"** 선택 → 확인
5. **동작 탭:** "새로 만들기" →
   - 프로그램/스크립트: `pythonw.exe` (콘솔 창 없이 실행)
   - 인수 추가: `C:\내_프로젝트_폴더\claude_telegram_bot.py`
   - 시작 위치: `C:\내_프로젝트_폴더`
6. **설정 탭:** "다음 시간 이상 실행되면 작업 중지" **체크 해제** (봇은 계속 실행되어야 하므로)
7. 확인

이제 Windows에 로그인하면 봇이 자동으로 백그라운드 실행됩니다.

### 방법 2: 배치 파일 만들기 (간단한 수동 실행용)

`start_bot.bat` 파일을 만들고 아래 내용을 붙여넣습니다:

```batch
@echo off
echo Claude Telegram Bot을 시작합니다...
pythonw.exe C:\내_프로젝트_폴더\claude_telegram_bot.py
```

이 `.bat` 파일을 더블클릭하면 콘솔 창 없이 봇이 백그라운드에서 실행됩니다. 종료하려면 작업 관리자(`Ctrl+Shift+Esc`)에서 `pythonw.exe` 프로세스를 찾아 종료합니다.

### 방법 3: Windows 시작 폴더에 등록 (가장 간단)

1. `Win + R` → `shell:startup` 입력 → 확인
2. 열린 폴더에 위에서 만든 `start_bot.bat` 파일의 **바로가기**를 넣습니다
3. PC 재시작 시 자동 실행됩니다

---

## 보안을 강화하는 6가지 필수 조치

**첫째, 텔레그램 사용자 ID로 접근 제한합니다.** 위 스크립트의 `owner_only` 데코레이터가 이 역할을 합니다. `TELEGRAM_USER_ID` 환경 변수에 등록된 사용자만 봇과 대화할 수 있고, 다른 사람이 메시지를 보내면 봇은 아무런 응답도 하지 않습니다.

**둘째, 봇 토큰을 코드에 직접 적지 마세요.** 환경 변수(`TELEGRAM_BOT_TOKEN`)를 사용하는 이유입니다. 코드를 GitHub에 올리거나 다른 사람에게 보여줘도 토큰이 노출되지 않습니다.

**셋째, `--dangerously-skip-permissions` 사용을 피하세요.** 이 플래그는 Claude에게 PC 전체 접근 권한을 부여합니다. 대신 `--allowedTools`로 필요한 도구(예: `Read,Bash`)만 허용하면 훨씬 안전합니다.

**넷째, 봇 사용자명을 추측하기 어렵게 설정합니다.** `my_private_ai_bot_x7k2` 같이 무작위 문자를 포함하면 다른 사람이 봇을 찾기 어렵습니다.

**다섯째, 토큰이 유출되었다면** 즉시 BotFather에서 `/revoke` 명령으로 토큰을 재발급합니다.

**여섯째, Claude의 작업 범위를 제한합니다.** 스크립트를 실행할 때 특정 프로젝트 폴더에서 실행하면(`cd C:\Projects\my-app && python claude_telegram_bot.py`), Claude Code는 해당 폴더를 작업 디렉토리로 인식합니다.

---

## 이미 만들어진 오픈소스 프로젝트 10선

직접 스크립트를 작성하는 대신 기존 프로젝트를 활용할 수도 있습니다. 아래는 2025~2026년 기준 활발한 프로젝트들입니다.

| 프로젝트 | 언어 | 특징 | Windows 지원 |
|---------|------|------|:----------:|
| **zertac/TeleClaude** | Python | Windows 전용, .bat 스크립트, 파일 다운로드 | ✅ |
| **RichardAtCT/claude-code-telegram** | Python | 가장 기능이 풍부, 웹훅, 스케줄러, 비용 제어 | ✅ |
| **PleasePrompto/ductor** | Python | Claude + Codex 모두 지원, Docker 샌드박스, 크론 | ✅ |
| **linuz90/claude-telegram-bot** | TypeScript | 음성·사진·문서 지원, MCP 서버 연동 | ⚠️ Bun 필요 |
| **NachoSEO/claudegram** | TypeScript | 스트리밍 응답, 세션 기억, MCP 통합 | ⚠️ Node.js |
| **godagoo/claude-telegram-relay** | TypeScript | Supabase 메모리, 능동적 체크인 | ⚠️ Bun 필요 |
| **hanxiao/claudecode-telegram** | Python | tmux + Cloudflare Tunnel 방식, 경량 | ❌ Linux/macOS |
| **seedprod/claude-code-telegram** | Python | Skills 시스템, 일일 브리핑 | ❌ macOS |
| **Nickqiaoo/chatcode** | Go/TS | 권한 UI, diff 뷰, 파일 브라우저 | ⚠️ |
| **yottoCode** | Swift | 네이티브 macOS 앱 (상용, 무료 티어 있음) | ❌ macOS만 |

Windows 초보자에게 가장 추천하는 순서는 **TeleClaude → 이 가이드의 직접 스크립트 → ductor** 순입니다. TeleClaude는 가장 간단하고, 직접 스크립트는 원리를 이해하고 커스터마이징하기 좋으며, ductor는 가장 기능이 풍부합니다.

---

## 전체 구조를 한눈에 이해하기

전체 데이터 흐름은 아래와 같은 단일 파이프라인으로 동작합니다.

```
📱 모바일 텔레그램          ☁️ 텔레그램 서버          🖥️ 집/사무실 PC
─────────────           ──────────────          ─────────────────
메시지 입력 ──────→ 봇 서버로 전달 ──────→ Python 스크립트가 수신
                                              │
                                              ▼
                                        claude -p "메시지" 실행
                                              │
                                              ▼
                                        Claude Code가 응답 생성
                                              │
                                              ▼
응답 확인 ←─────── 봇 서버로 전달 ←─────── Python이 텔레그램으로 회신
```

PC에서 Python 스크립트가 **폴링(polling)** 방식으로 텔레그램 서버에 주기적으로 새 메시지가 있는지 확인합니다. 별도 서버나 포트 포워딩이 필요 없어 방화벽 설정을 건드릴 필요가 없습니다. PC가 인터넷에 연결되어 있고 스크립트가 실행 중이기만 하면 동작합니다.

---

## 결론: 핵심 점검 사항과 다음 단계

이 시스템의 작동에 필요한 조건은 딱 세 가지입니다. PC가 켜져 있고 인터넷에 연결되어 있을 것, Claude Code CLI가 설치되어 인증된 상태일 것, Python 스크립트가 실행 중일 것. 이 세 조건이 충족되면 지구 어디서든 텔레그램으로 Claude Code를 사용할 수 있습니다.

시작은 방법 B의 직접 스크립트로 원리를 이해한 뒤, 필요에 따라 TeleClaude나 ductor 같은 완성된 프로젝트로 전환하는 것을 추천합니다. 특히 **`--allowedTools` 옵션으로 도구 권한을 최소한으로 제한**하는 것이 보안의 핵심입니다. 원격 제어는 편리하지만, 결국 외부에서 PC 명령을 실행하는 것이므로 접근 제한에 세심한 주의를 기울여야 합니다.