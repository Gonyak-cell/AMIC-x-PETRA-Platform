# Auto FDD — Claude Code Rules

## Project Structure
- Monorepo: `backend/` (Python FastAPI), `frontend/` (React+Vite), `pptx-service/` (Node.js Express)
- Docker Compose: `docker compose up -d` → db:5432, backend:8000, pptx:3100, frontend:5173
- Makefile: up, down, logs, build, test, migrate, migrate-gen, dev-frontend, dev-pptx

## CRITICAL: Money Rules
- ALL monetary values: `Decimal` (Python) or `string` (JSON/TypeScript). **NEVER `float`.**
- DB columns: `NUMERIC(18,4)` — no exceptions.
- KRW: zero decimal places. FX rates: up to 4 decimal places.
- Tests: use `Decimal("123.4567")` not `123.4567`.
- Rounding: always explicit via `quantize()`, never implicit.

## Architecture Rules
- **Report IR Pattern**: engines → report_builder.py → JSON IR → renderers (PPT/Word)
- **Engine functions**: MUST be pure. Return `tuple[Result, list[EvidenceLink]]`. NO DB access, NO side effects.
- **Snapshot hashing**: definition_hash + input_hash + engine_version → result_hash
- **LLM boundary**: Calculations = rule engine ONLY. LLM = judgment/text analysis ONLY. All LLM output = JSON Schema forced. User approval required.

## Naming Conventions
| Target | Convention | Example |
|--------|-----------|---------|
| Python files/functions/vars | snake_case | `qoe_engine.py`, `calculate_ebitda()` |
| Python classes | PascalCase | `QoEBridge`, `DealDefinition` |
| React components/files | PascalCase | `DealListPage.tsx` |
| DB tables | snake_case plural | `deal_definitions`, `audit_logs` |
| API URLs | kebab-case | `/api/v1/qoe-bridge` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Git branches | pattern/{issue}-{desc} | `feature/FDD-201-upload-api` |

## Git Rules
- Conventional Commits: `feat|fix|refactor|test|docs|chore(scope): description`
- Max PR: 400 lines. 1+ approver + CI pass required.
- Branches: `main` (prod), `develop` (integration), `feature/`, `bugfix/`, `hotfix/`

## Error Handling
- Domain errors: `FDDError(ErrorCode.XXX)` from `app.core.exceptions`
- Code ranges: 1000=ingest, 2000=mapping, 3000=QoE, 4000=NWC, 5000=debt, 6000=doc, 9000=system
- API errors: RFC 7807 Problem Details format
- Severity: CRITICAL=halt, ERROR=retry→notify, WARNING=continue+warn, INFO=log

## Testing Commands
- Backend: `cd backend && python -m pytest -v`
- Frontend lint: `cd frontend && npm run lint`
- Full CI: ruff + black + mypy + pytest (BE), eslint + tsc (FE), tsc (pptx)

## Timestamp Rules

- 문서에 시간을 기재/업데이트할 때 **반드시 PowerShell로 현재 시간 확인** 후 기재
- 명령어: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
- 형식: `YYYY년 MM월 DD일 HH시 mm분 ss초` (예: 2026년 02월 06일 14시 30분 25초)
- 적용 대상: 진행현황 문서, 계획 문서, 로그 등 모든 시간 기록

## CRITICAL: Context Limit Management

- 컨텍스트 윈도우 부족이 예상되면 **즉시 작업 중단** — 품질 저하된 결과물 생성 금지.
- 중단 시 반드시 아래를 수행:
  1. **완료/미완료 작업 목록** 정리 (TodoWrite 형식)
  2. 이어가기 위한 **컨텍스트 요약** 작성 (핵심 결정사항, 현재 상태, 다음 단계)
  3. `CLAUDE.local.md`에 진행 상황 기록 (세션 간 연속성 보장)
  4. 사용자에게 **"새 세션에서 이어서 작업하세요"** 안내 + 복사 가능한 프롬프트 제공
- **절대 금지**: 컨텍스트 부족 상태에서 억지로 작업 계속하는 것 — 코드 누락, 잘못된 참조, 불완전한 구현의 원인.

## .claude/ Automation Ecosystem (자동 적용)

아래 모든 리소스는 Claude Code가 **자동으로 로드** — 수동 활성화 불필요.

### Rules (11개 — 조건부 자동 적용)

`.claude/rules/*.md` 파일의 `paths:` frontmatter 글롭 패턴에 매칭되는 파일 편집 시 자동 로드:

| Rule                        | Triggers On                                                      |
| --------------------------- | ---------------------------------------------------------------- |
| `financial-conventions` | `backend/app/engines/**`, `services/**`, `models/**`, `schemas/**` |
| `python-style` | `backend/**/*.py` |
| `typescript-style` | `frontend/**/*.{ts,tsx}`, `pptx-service/**/*.ts` |
| `database-rules` | `backend/app/models/**`, `backend/alembic/**` |
| `testing-rules` | `backend/tests/**/*.py`, `frontend/**/*.test.*` |
| `api-design` | `backend/app/api/**`, `backend/app/schemas/**` |
| `security-checklist` | `backend/**`, `frontend/**`, `.env*`, `docker-compose*` |
| `git-workflow` | `.git/**`, `.github/**` |
| `chart-standards` | `frontend/src/components/**`, `backend/app/renderers/**` |
| `performance-guidelines` | `backend/**/*.py`, `frontend/**/*.{ts,tsx}` |
| `financial-data-integrity` | `backend/app/engines/**`, `services/**`, `tests/**` |

### Skills (28개 — `/skill-name` 슬래시 명령)
`.claude/skills/<name>/SKILL.md` — 사용자가 `/skill-name`으로 호출:
- **FDD (13)**: fdd-anomaly-detector, fdd-checklist, fdd-data-extractor, fdd-data-processor, fdd-financial-analysis, fdd-financial-analyst, fdd-project-manager, fdd-quality-reviewer, fdd-report-generator, fdd-report-writer, fdd-scenario-builder, fdd-variance-analyzer, regulatory-compliance
- **Dev (9)**: api-tester, infra-validator, security-scanner, test, lint, new-api, new-engine, db-migrate, sprint-status
- **Doc (5)**: xlsx, pdf, docx, pptx, frontend-design
- **Meta (1)**: skill-creator

### Agents (12개 — Task 서브에이전트)
`.claude/agents/<name>.md` — Task tool의 `subagent_type`으로 자동 등록:
- **FDD (9)**: orchestrator, data-parser, coa-mapper, qoe-analyzer, nwc-classifier, debt-classifier, contract-analyzer, report-writer, evidence-tracer
- **QA/Dev (3)**: pr-reviewer, test-generator, migration-validator

### Hooks (3개 — 이벤트 트리거)
`.claude/settings.json`에 정의, `.claude/hooks/` 스크립트 실행:
- **PreToolUse:Bash** → `validate-bash-command.py` (위험 명령어 차단)
- **PostToolUse:Edit|Write** → `auto-format.py` (코드 자동 포맷팅)
- **SessionStart** → `session-start-reminder.py` (세션 시작 알림)

## Key Docs (Korean)
- Master spec: `FDD_자동화_개발계획_로드맵_마스터파일.md`
- Sprint roadmap: `FDD_개발_로드맵.md`
- Progress: `FDD_프로젝트_진행현황.md`
