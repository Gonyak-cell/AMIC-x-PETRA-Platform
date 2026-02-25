# 텔레그램 원격 제어 활용 가이드

> 2026-02-24 21:33 | AMIC x PETRA Platform

외출 중 모바일 텔레그램에서 집 PC의 Claude Code를 원격 조종하여 플랫폼 코딩 작업을 수행하는 완전 가이드.

---

## 1. 초기 설정 (최초 1회)

### 1-1. 텔레그램 봇 생성 (5분)

1. 텔레그램 앱에서 `@BotFather` 검색 → "시작" 클릭
2. `/newbot` 입력
3. 봇 이름 입력 (예: `AMIC Claude Bot`)
4. 봇 사용자명 입력 — 반드시 `bot`으로 끝남 (예: `amic_claude_helper_bot`)
5. **API 토큰** 복사 (`123456789:ABCdefGHI...` 형태)
6. `@userinfobot` 검색 → 아무 메시지 → **사용자 ID** (숫자) 확인

### 1-2. 환경 설정

```bash
cd remote
cp .env.example .env
```

`.env` 파일을 열어 실제 값 입력:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_USER_IDS=987654321
```

### 1-3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 1-4. 실행

```bash
start_bot.bat
```

콘솔에 `🤖 AMIC x PETRA — Claude Code Telegram Bot`이 표시되면 성공.

### 1-5. 첫 테스트

텔레그램에서 봇에게 `/start` 전송 → 환영 메시지가 오면 준비 완료!

---

## 2. 일상 활용 시나리오

### 시나리오 A: 외출 중 코드 상태 확인

카페에서 커피를 마시다가 "아까 커밋 제대로 했나?" 궁금할 때:

```
/status
→ 현재 git 상태 확인 (modified, untracked 파일 목록)

/log 5
→ 최근 5개 커밋 메시지 확인

/branch
→ 현재 브랜치 및 원격 브랜치 목록

/diff
→ 변경된 파일 요약 통계
```

### 시나리오 B: 빌드·테스트 원격 실행

퇴근 후 집에서 "오늘 작업한 코드 빌드 되나?" 확인:

```
/build
→ 🔨 프론트엔드 빌드 시작... (최대 5분 대기)
→ 빌드 성공/실패 결과 회신

/test fdd
→ 🧪 FDD 백엔드 pytest 실행

/test kiis
→ 🧪 KIIS 백엔드 pytest 실행

/test deal-mgmt
→ 🧪 MA 백엔드 pytest 실행

/test frontend
→ 프론트엔드 vitest 실행

/lint
→ ESLint 실행

/typecheck
→ TypeScript 타입 검사
```

### 시나리오 C: Claude에게 코딩 작업 지시

자유 텍스트를 보내면 Claude Code가 PC에서 직접 코드를 읽고·분석·수정합니다:

```
"kiis/app/routers/company.py의 list_companies 엔드포인트에
pagination 파라미터(skip, limit)를 추가해줘"

"amic-platform/src/modules/ma/pages/TransactionListPage.tsx에서
필터 칩 UI가 3개만 보이는데 원인을 분석해줘"

"deal-mgmt/app/services/workflow_engine.py의
advance_workflow 함수 로직을 설명해줘"

"fdd/backend/app/api/deals.py에 있는 N+1 쿼리 문제를 찾아서 수정해줘"
```

Claude는 실제로 파일을 읽고, 코드를 수정하고, 결과를 텔레그램으로 보내줍니다.

### 시나리오 D: 파일 조회·다운로드

특정 파일 내용을 빠르게 확인하거나 모바일로 받기:

```
/cd kiis
→ 📂 작업 디렉토리 변경: kiis

/ls app/routers/
→ 📁 __pycache__
  analysis.py
  company.py
  deals.py
  public_data.py

/cat app/routers/company.py
→ 📄 company.py
  ```python
  (파일 내용 표시)
  ```

/getfile app/routers/company.py
→ (파일을 텔레그램 문서로 다운로드)

/cd root
→ 📂 프로젝트 루트로 복귀
```

### 시나리오 E: 복잡한 작업 — 다중 턴 대화

한 번의 메시지로 끝나지 않는 복잡한 작업:

```
/session on
→ ✅ 세션 모드 ON — 다중 턴 대화가 활성화

"deal-mgmt의 closing 라우터에서 사용하는
standard_items 목록을 보여줘"

"그 중에서 '주주간계약서 검토'와 '이사회 결의서'
항목의 순서를 바꿔줘"

"변경 사항을 확인시켜줘"

/session off
→ 단발 모드로 복귀
```

세션 모드에서는 이전 대화 맥락이 유지되어 "그것", "위에서" 같은 참조가 가능합니다.

### 시나리오 F: 모델·비용 관리

작업 성격에 따라 모델과 예산을 조절:

```
/model haiku
→ 🧠 모델 전환: haiku (빠르고 저렴, 간단한 질문용)

/model sonnet
→ 🧠 모델 전환: sonnet (기본, 균형 잡힌 성능)

/model opus
→ 🧠 모델 전환: opus (가장 강력, 복잡한 분석·리팩토링)

/budget 5.00
→ 💰 요청당 예산 상한 $5.00으로 변경

/cost
→ 💰 이번 세션 누적 비용: $0.1234

/reset
→ 🔄 세션 초기화 (디렉토리, 모델, 비용 모두 리셋)
```

---

## 3. 실전 워크플로우 예시

### 워크플로우 1: "아침에 어제 작업 이어가기"

```
나: /log 3
봇: 3c89684 fix(infra): fix issues found in local production Docker test
    7ffc408 fix(infra): unify JWT secret across all backends in production
    4dd7ee9 feat(infra): add production deployment pipeline

나: /status
봇: On branch feat/ma-workflow
    modified: deal-mgmt/app/services/workflow_engine.py
    ...

나: "어제 workflow_engine.py에서 뭘 변경했는지 요약해줘"
봇: (Claude가 git diff를 분석하여 변경 요약 제공)
```

### 워크플로우 2: "빌드 깨졌는지 체크"

```
나: /build
봇: 🔨 프론트엔드 빌드 시작...
    (3분 후)
    ✓ 1247 modules transformed
    ✓ built in 42.3s

나: /test deal-mgmt
봇: 🧪 deal-mgmt 테스트 시작...
    85 passed, 0 failed
```

### 워크플로우 3: "급한 버그 수정"

```
나: /model opus
봇: 🧠 모델 전환: opus

나: /session on
봇: ✅ 세션 모드 ON

나: "kiis/app/services/reputation_service.py에서
    get_reputation_themes가 빈 배열을 반환하는 버그가 있어.
    원인을 찾아서 수정해줘"
봇: (파일을 읽고 분석)
    원인: themes_mapping에서 키 매칭 시 대소문자 불일치...
    수정 완료: lower() 비교로 변경...

나: /test kiis
봇: 🧪 kiis 테스트 시작...
    42 passed, 0 failed

나: /cost
봇: 💰 이번 세션 누적 비용: $0.0847

나: /session off
```

---

## 4. 디렉토리 단축 별칭

`/cd` 명령의 단축 별칭:

| 별칭 | 실제 경로 | 용도 |
|------|-----------|------|
| `fdd` | `fdd/backend/` | FDD 백엔드 |
| `kiis` | `kiis/` | KIIS 백엔드 |
| `im` | `im/` | IM 백엔드 |
| `deal-mgmt` 또는 `ma` | `deal-mgmt/` | MA 백엔드 |
| `frontend` 또는 `platform` | `amic-platform/` | 프론트엔드 |
| `root` 또는 `.` | 프로젝트 루트 | 루트 복귀 |

---

## 5. 테스트 가능 모듈

| 명령 | 모듈 | 테스트 도구 |
|------|------|------------|
| `/test fdd` | FDD 백엔드 | pytest |
| `/test kiis` | KIIS 백엔드 | pytest |
| `/test im` | IM 백엔드 | pytest |
| `/test deal-mgmt` 또는 `/test ma` | MA 백엔드 | pytest |
| `/test frontend` | 프론트엔드 | vitest |

---

## 6. 보안 주의사항

### 반드시 지켜야 할 것

- **`.env` 파일을 절대 공유하지 않기** — 봇 토큰이 노출되면 누구나 봇을 제어 가능
- **봇 사용자명을 추측하기 어렵게** — `my_private_bot_x7k2` 같이 랜덤 문자 포함
- **`TELEGRAM_USER_IDS`에 본인 ID만** — 신뢰할 수 있는 사람만 추가

### 자동 보호 기능

- 허가되지 않은 사용자가 메시지를 보내면 → **무응답** (봇 존재 비노출)
- `.env`, `.git/`, `*.pem`, `*.key` 파일 → **접근 차단**
- 프로젝트 루트 밖 경로 → **접근 차단**
- 요청당 비용 상한 $2.00 (기본) → **과금 방지**
- 분당 5회 속도 제한 → **폭주 방지**
- Claude 도구는 `Read, Write, Edit, Bash, Glob, Grep`만 허용 → **MCP·웹 접근 차단**

### 토큰이 유출되었다면

1. 텔레그램에서 `@BotFather` → `/revoke` → 토큰 재발급
2. `.env`의 `TELEGRAM_BOT_TOKEN` 값 교체
3. 봇 재시작

---

## 7. 자동 시작 설정

### 방법 A: Windows 시작 프로그램 (권장)

```bash
install_startup.bat
```

PC 로그인 시 봇이 자동으로 백그라운드 실행됩니다.

### 방법 B: Windows 작업 스케줄러

1. `Win + R` → `taskschd.msc`
2. "작업 만들기" →
   - 이름: `AMIC Telegram Bot`
   - 트리거: "로그온할 때"
   - 동작: `pythonw.exe`, 인수 `-m bot.main`, 시작 위치 `remote/` 경로
   - 설정: "다음 시간 이상 실행되면 작업 중지" **해제**
3. 확인

### 봇 종료

```bash
stop_bot.bat
```

또는 작업 관리자(`Ctrl+Shift+Esc`)에서 `python.exe` 프로세스 종료.

---

## 8. 팁 & 트릭

### 효율적인 사용 팁

1. **간단한 상태 확인은 명령어로** — `/status`, `/log`는 Claude 비용 0원
2. **복잡한 작업만 자유 텍스트로** — Claude 호출은 비용 발생
3. **모델 선택이 중요** — 간단한 질문은 `haiku`, 코딩은 `sonnet`, 복잡한 분석은 `opus`
4. **세션 모드는 필요할 때만** — `/session on`은 컨텍스트 유지하지만 토큰 소비 증가
5. **긴 작업 전 예산 확인** — `/budget 10.00`으로 상한 올려두기

### 문제 해결

| 증상 | 해결 |
|------|------|
| 봇이 응답하지 않음 | PC가 켜져 있고 `start_bot.bat`이 실행 중인지 확인 |
| "claude 명령어를 찾을 수 없습니다" | Claude Code CLI가 설치되어 PATH에 등록되었는지 확인 |
| 메시지를 보내도 무응답 | `.env`의 `TELEGRAM_USER_IDS`에 본인 ID가 맞는지 확인 |
| 타임아웃 발생 | 질문을 더 짧게 나누거나, `.env`의 `CLAUDE_TIMEOUT`을 늘리기 |
| 봇 토큰 오류 | `@BotFather`에서 토큰을 재확인, `.env` 업데이트 |

### 비용 절약 전략

- **Git 명령어 적극 활용** — `/status`, `/log`, `/diff`는 무료
- **모듈 지정 테스트** — `/test fdd`처럼 필요한 모듈만 테스트
- **haiku 기본 사용** — 간단한 질문은 `haiku`가 10배 저렴
- **세션 모드 절제** — 단발 질문은 `/session off` 상태에서
- **`/cost`로 주기적 확인** — 예상치 못한 과금 방지

---

## 9. 아키텍처 참고

```
📱 모바일 텔레그램        ☁️ 텔레그램 서버        🖥️ PC (집/사무실)
─────────────         ──────────────        ─────────────────
메시지 입력  ──────→  봇 서버로 전달  ──────→  Python 봇이 수신
                                              │
                                     ┌────────┴────────┐
                                     │                 │
                                  명령어?          자유 텍스트?
                                     │                 │
                                     ▼                 ▼
                               직접 실행          claude -p "..."
                            (git, npm 등)         (Claude Code)
                                     │                 │
                                     └────────┬────────┘
                                              │
                                              ▼
응답 확인  ←──────  봇 서버로 전달  ←──────  텔레그램으로 회신
```

- **폴링 방식** — 별도 서버·포트 포워딩·방화벽 설정 불필요
- **필요 조건**: PC 전원 ON + 인터넷 연결 + Python 스크립트 실행 중
- **모든 코드는 `remote/` 폴더에 격리** — 프로젝트 코드와 완전 분리
