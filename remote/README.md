# AMIC x PETRA — Telegram Bot 원격 제어

텔레그램 메시지로 집/사무실 PC의 Claude Code CLI를 원격 제어합니다.

## 빠른 시작

### 1. 텔레그램 봇 생성

1. 텔레그램에서 `@BotFather` 검색 → `/newbot` → 봇 생성 → **API 토큰** 복사
2. 텔레그램에서 `@userinfobot` 검색 → 아무 메시지 → **사용자 ID** 확인

### 2. 환경 설정

```bash
cd remote
cp .env.example .env
# .env 파일을 편집하여 토큰과 사용자 ID 입력
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 실행

```bash
# 방법 A: 직접 실행
python -m bot.main

# 방법 B: 배치 파일
start_bot.bat
```

### 5. 테스트

텔레그램 앱에서 봇에게 `/start` 전송 → 환영 메시지가 오면 성공!

---

## 명령어 목록

| 명령 | 설명 |
|------|------|
| `/start` | 시작 안내 |
| `/help` | 전체 도움말 |
| `/ping` | 봇 상태 확인 |
| `/status` | git status |
| `/log [N]` | 최근 N개 커밋 |
| `/branch` | 브랜치 목록 |
| `/diff` | diff 요약 |
| `/build` | 프론트엔드 빌드 |
| `/test <module>` | 모듈 테스트 (fdd, kiis, im, deal-mgmt, frontend) |
| `/lint [module]` | 린트 실행 |
| `/typecheck` | TypeScript 타입 검사 |
| `/cd <path>` | 작업 디렉토리 변경 (fdd, kiis, im, deal-mgmt, frontend, root) |
| `/pwd` | 현재 디렉토리 |
| `/ls [path]` | 디렉토리 목록 |
| `/cat <path>` | 파일 내용 보기 |
| `/getfile <path>` | 파일 다운로드 |
| `/session on\|off` | 다중 턴 대화 모드 |
| `/reset` | 세션 초기화 |
| `/model <name>` | 모델 전환 (sonnet, opus, haiku) |
| `/cost` | 누적 비용 조회 |
| `/budget <USD>` | 요청당 비용 상한 |

자유 텍스트 메시지를 보내면 Claude Code가 처리합니다.

---

## 자동 시작

```bash
# Windows 시작 프로그램에 등록
install_startup.bat
```

---

## 보안

- `TELEGRAM_USER_IDS`로 허가된 사용자만 접근 가능
- `--allowedTools`로 Claude 도구 제한 (Read, Write, Edit, Bash, Glob, Grep만)
- `--dangerously-skip-permissions` 사용 안 함
- `.env` 파일은 `.gitignore`에 포함
- `.env`, `.git/`, `*.pem` 등 민감 파일 접근 차단
- 요청당 비용 상한 ($2.00 기본)
- 분당 5회 속도 제한

---

## 테스트

```bash
cd remote
pip install pytest pytest-asyncio
pytest tests/ -v
```
