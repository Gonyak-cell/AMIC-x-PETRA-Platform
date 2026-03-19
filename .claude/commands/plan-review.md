---
name: plan-review
description: "Codex CLI(GPT-5.4, xhigh)로 플랜 파일 리뷰 요청. 사용법: /plan-review [plan_file_path]"
---

# 플랜 리뷰 — Codex CLI (GPT-5.4, reasoning: xhigh)

플랜 파일을 Codex CLI에 전달하여 독립적인 AI 리뷰를 받고, 피드백을 사용자에게 원문 그대로 보여준 뒤 플랜을 개선한다.

## 실행 순서

### 1. 플랜 파일 결정

`$ARGUMENTS`가 제공되면 해당 경로를 사용한다.
미제공 시 아래 명령으로 가장 최근 플랜 파일을 자동 선택한다:

```bash
ls -t ~/.claude/plans/*.md 2>/dev/null | head -1
```

선택된 플랜 파일을 Read로 읽어 내용을 확인한다.

### 2. 리뷰 프롬프트 작성

아래 템플릿에 플랜 내용을 삽입하여 `/tmp/codex-review-prompt.txt` 파일에 Write한다.

**프롬프트 템플릿:**

```
You are a senior software architect performing a thorough code review of an implementation plan.

Project context: Monorepo with Python backends (FastAPI, SQLAlchemy, Alembic) + TypeScript/React frontend + Electron desktop app. Deployed via Docker Compose on Azure VM.

You have access to the full codebase via the working directory. READ the relevant source files mentioned in the plan to validate the proposed changes against actual code.

PLAN FILE: {플랜 파일명}

---
{플랜 전체 내용}
---

Review criteria:
1. COMPLETENESS: Are all implementation steps covered? Missing error handling, tests, DB migrations?
2. ORDERING: Are dependencies between steps correctly sequenced?
3. CODE VALIDATION: Read the actual source files referenced in the plan. Do the proposed changes align with existing code patterns, types, and APIs?
4. RISK: What could go wrong during implementation? Rate overall risk (Low/Medium/High).
5. ALTERNATIVES: Are there simpler approaches using existing utilities/functions that were overlooked?
6. EDGE CASES: What failure modes or edge cases are not addressed?

Output format (markdown):
## Review Summary (1-2 sentences)
## Strengths (bullet list)
## Concerns (bullet list, ordered by severity)
## Code Validation Notes (what you found by reading the actual source files)
## Suggestions (numbered, actionable)
## Risk Rating: [Low|Medium|High] - [reason]
```

### 3. Codex exec 실행

Bash 도구로 아래 명령을 실행한다 (**timeout: 300000**):

```bash
npx @openai/codex exec \
  -C "$(pwd)" \
  --full-auto \
  --ephemeral \
  -o "/tmp/codex-review-result.md" \
  - < "/tmp/codex-review-prompt.txt"
```

### 4. 결과 출력

`/tmp/codex-review-result.md` 파일을 Read로 읽는다.

**반드시 Codex 리뷰 원문을 그대로 사용자에게 출력한다** (요약/편집/생략 없이 전문 표시).

원문 출력 후, 핵심 포인트를 한글로 간략 요약한다:
```
### Codex 리뷰 요약 (한글)
- 핵심 우려 1: ...
- 핵심 우려 2: ...
- 위험도: ...
```

### 5. 플랜 수정 여부 질문

사용자에게 플랜 수정 여부를 질문한다.

수정 승인 시, **각 수정 항목에 어떤 Codex 코멘트를 반영했는지 인용 표시**:
```
## 수정 내역
- [Codex 코멘트] "Step 3 lacks error handling for network failures"
  → Step 3에 네트워크 에러 핸들링 추가
- [Codex 코멘트] "Migration should run before model changes"
  → Step 2와 Step 4 순서 변경
```
