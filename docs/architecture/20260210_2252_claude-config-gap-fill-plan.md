# Claude Code Configuration Gap-Fill Plan

## Context
3개 프로젝트(Auto FDD, KIIS, IM Module)의 Claude Code 설정(agents, skills, rules, hooks, commands, MCP)을 비교 분석한 결과, 각 프로젝트의 갭을 파악하고 이를 채우기 위한 구현 계획입니다.

**발견 사항**:
- Auto FDD `.mcp.json`에 이미 3개 MCP 서버(filesystem, postgres, github) 존재 → Context7 추가
- KIIS 기존 `auto-format.sh`를 `ruff-format.sh`로 교체 (IM Module 패턴 통일)

## Summary of Changes

| 프로젝트 | 추가 항목 | 파일 수 |
|---------|----------|---------|
| **Auto FDD** | Commands 8개 + MCP에 Context7 추가 | **9** |
| **KIIS** | Agents 10 + Rules 10 + Commands 8 + Skills 10 + Hooks 5(신규)+1(교체) + MCP 1 + settings.json 업데이트 | **46** |
| **IM Module** | Rules 10개 | **10** |
| **합계** | | **65** |

---

## Phase 1: Auto FDD — Commands 추가 (8개)

**디렉토리**: `C:\Users\diedi\OneDrive\Documents\Coding\Auto FDD\.claude\commands\`

| # | 파일 | 설명 | 참조 에이전트 |
|---|------|------|-------------|
| 1 | `plan.md` | 개발 계획 수립 | — |
| 2 | `review.md` | 코드 리뷰 | @pr-reviewer |
| 3 | `test.md` | 테스트 실행 (backend pytest + frontend tsc) | @test-generator |
| 4 | `generate-fdd.md` | FDD 분석 파이프라인 전체 실행 | @orchestrator → @data-parser → @coa-mapper → @qoe-analyzer → @nwc-classifier → @debt-classifier → @evidence-tracer → @report-writer |
| 5 | `migrate.md` | DB 마이그레이션 (생성/적용/롤백) | @migration-validator |
| 6 | `security-scan.md` | 보안 감사 (시크릿/코드/API/의존성) | — |
| 7 | `benchmark.md` | 성능 벤치마크 (API/엔진/DB/메모리) | — |
| 8 | `deploy-check.md` | 배포 전 검증 체크리스트 | — |

**템플릿 참조**: `IM Module/.claude/commands/generate-im.md`, `review.md`, `security-scan.md`

### 1B. Auto FDD MCP — Context7 추가

**파일**: `C:\Users\diedi\OneDrive\Documents\Coding\Auto FDD\.mcp.json`

기존 3개 서버(filesystem, postgres, github)에 Context7 추가:
```json
{
  "mcpServers": {
    "filesystem": { ... },
    "postgres": { ... },
    "github": { ... },
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

---

## Phase 2: KIIS — 전체 설정 추가 (46개)

### 2A. Agents (10개)

**디렉토리**: `C:\Users\diedi\OneDrive\Documents\Coding\KIIS\.claude\agents\`

| # | 파일 | 역할 | model | tools |
|---|------|------|-------|-------|
| 1 | `data-collector.md` | DART/KOFIA/REITs 데이터 수집 | sonnet | Read,Grep,Glob,Bash,Task |
| 2 | `nlp-analyzer.md` | 한국어 NLP (kiwipiepy), 감성분석, 키워드 추출 | sonnet | Read,Grep,Bash |
| 3 | `entity-resolver.md` | 엔티티 해소 — 퍼지 매칭으로 동일 기업/펀드 식별 | sonnet | Read,Grep,Bash |
| 4 | `reputation-scorer.md` | 평판 점수 산정 (뉴스40%+성과30%+규제20%+투명성10%) | sonnet | Read,Bash |
| 5 | `deal-analyst.md` | 딜 발굴, 투자 분석, DNA 시각화 | sonnet | Read,Grep,Bash |
| 6 | `api-developer.md` | FastAPI 라우터/서비스/스키마 개발 | sonnet | Read,Write,Edit,Grep,Glob,Bash |
| 7 | `db-architect.md` | SQLAlchemy 모델 설계, Alembic 마이그레이션 | sonnet | Read,Write,Edit,Bash |
| 8 | `test-engineer.md` | pytest async 테스트, 외부 API mocking | sonnet | Read,Write,Edit,Bash |
| 9 | `code-reviewer.md` | 코드 리뷰 (규칙 준수, 보안, 성능) | sonnet | Read,Grep,Glob,Bash |
| 10 | `security-reviewer.md` | 보안 취약점 스캔 (OWASP, 시크릿 탐지) | sonnet | Read,Grep,Bash |

**핵심 패턴**: Auto FDD `orchestrator.md` 포맷 (frontmatter + Role + Workflow + Decision Points + Output + Guardrails)

### 2B. Rules (10개)

**디렉토리**: `C:\Users\diedi\OneDrive\Documents\Coding\KIIS\.claude\rules\`

| # | 파일 | 내용 | paths 필터 | 참조 |
|---|------|------|-----------|------|
| 1 | `python-style.md` | 네이밍, 타입 힌트, SQLAlchemy 2.0 async, Pydantic v2 | `app/**/*.py` | FDD python-style.md |
| 2 | `database-rules.md` | async 패턴, N+1 방지, 인덱스 전략, 마이그레이션 안전 | `app/models/**`, `migrations/**` | FDD database-rules.md |
| 3 | `api-design.md` | 라우터 패턴, URL 규칙, 에러 응답, 페이지네이션 | `app/routers/**` | FDD api-design.md |
| 4 | `testing-rules.md` | pytest async, Mock 외부 API, Fixture 설계 | `tests/**` | FDD testing-rules.md |
| 5 | `scraping-rules.md` | robots.txt 준수, Rate limiting, 에러 핸들링 | `app/services/*_service.py` | KIIS 도메인 고유 |
| 6 | `nlp-guidelines.md` | kiwipiepy 사용법, 불용어, 감성사전, 엔티티 링킹 | `app/services/nlp_*`, `app/utils/entity_*` | KIIS 도메인 고유 |
| 7 | `async-patterns.md` | asyncio 패턴, Semaphore, APScheduler, httpx 타임아웃 | `app/**/*.py` | KIIS 도메인 고유 |
| 8 | `data-integrity.md` | 엔티티 중복방지, 데이터 검증, Audit trail | `app/models/**`, `app/services/**` | KIIS 도메인 고유 |
| 9 | `security-checklist.md` | OWASP, DART API 키 관리, SSRF 방지, JWT | `app/**/*.py` | FDD security-checklist.md |
| 10 | `git-workflow.md` | 브랜치 전략, 커밋 규칙, PR 프로세스 | — (글로벌) | FDD git-workflow.md |

### 2C. Commands (8개)

**디렉토리**: `C:\Users\diedi\OneDrive\Documents\Coding\KIIS\.claude\commands\`

| # | 파일 | 설명 | 호출 에이전트 |
|---|------|------|-------------|
| 1 | `plan.md` | 개발 계획 수립 | — |
| 2 | `review.md` | 코드 리뷰 | @code-reviewer |
| 3 | `test.md` | pytest 실행 | @test-engineer |
| 4 | `sync-dart.md` | DART/KOFIA/REITs 데이터 수동 동기화 | @data-collector |
| 5 | `analyze-company.md` | 기업 종합 분석 (데이터 수집→NLP→평판→딜분석) | @data-collector → @nlp-analyzer → @reputation-scorer → @deal-analyst |
| 6 | `check-health.md` | 시스템 헬스체크 (DB, Redis, ES, API) | — |
| 7 | `security-scan.md` | 보안 감사 | @security-reviewer |
| 8 | `benchmark.md` | 성능 벤치마크 | — |

### 2D. Skills (10개 추가, 기존 3개 유지)

**디렉토리**: `C:\Users\diedi\OneDrive\Documents\Coding\KIIS\.claude\skills\`

| # | 디렉토리 | 설명 | user-invocable |
|---|---------|------|---------------|
| 1 | `docker-ops/SKILL.md` | Docker compose 관리 (up/down/logs) | Yes |
| 2 | `api-test/SKILL.md` | httpx로 API 엔드포인트 테스트 | Yes |
| 3 | `new-api/SKILL.md` | 라우터+서비스+스키마+모델 보일러플레이트 생성 | Yes |
| 4 | `new-service/SKILL.md` | 새 서비스 모듈 스캐폴딩 | Yes |
| 5 | `db-query/SKILL.md` | SQL 디버깅 (EXPLAIN ANALYZE) | Yes |
| 6 | `security-audit/SKILL.md` | 보안 취약점 스캔 | Yes |
| 7 | `sync-data/SKILL.md` | DART/KOFIA/REITs 수동 동기화 트리거 | Yes |
| 8 | `reputation-calc/SKILL.md` | 평판 점수 계산 테스트 | Yes |
| 9 | `entity-check/SKILL.md` | 엔티티 해소 매칭 테스트 | Yes |
| 10 | `ruff-fix/SKILL.md` | ruff check --fix + format 전체 실행 | Yes |

### 2E. Hooks (5개 신규 + 1개 교체)

**디렉토리**: `C:\Users\diedi\OneDrive\Documents\Coding\KIIS\.claude\hooks\`

기존 `auto-format.sh` → `ruff-format.sh`로 교체, `protect-files.sh` 유지

| # | 파일 | 트리거 | 설명 | 비고 |
|---|------|--------|------|------|
| - | `protect-files.sh` | PreToolUse:Edit\|Write | .env, migrations/versions/ 보호 | **기존 유지** |
| 1 | `ruff-format.sh` | PostToolUse:Edit\|Write | .py 파일 ruff format + check --fix | **auto-format.sh 교체** |
| 2 | `pre-bash-firewall.sh` | PreToolUse:Bash | rm -rf, git reset --hard 등 차단 | 신규 (IM Module 참조) |
| 3 | `block-destructive-db.sh` | PreToolUse:Bash | DROP TABLE, TRUNCATE 차단 | 신규 (IM Module 참조) |
| 4 | `validate-env.sh` | SessionStart | Python venv, .env, Docker 확인 | 신규 (IM Module 참조) |
| 5 | `run-affected-tests.sh` | PostToolUse:Edit | 수정 파일 관련 테스트 자동 실행 | 신규 (IM Module 참조) |
| 6 | `check-secrets.sh` | PreToolUse:Bash | 커밋 전 하드코딩 시크릿 스캔 | 신규 |

**settings.json 업데이트 필요**: 새 훅들을 등록, auto-format.sh 참조 제거

### 2F. MCP (1개)

**파일**: `C:\Users\diedi\OneDrive\Documents\Coding\KIIS\.mcp.json`

```json
{
  "mcpServers": {
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

---

## Phase 3: IM Module — Rules 추가 (10개)

**디렉토리**: `C:\Users\diedi\OneDrive\Documents\Coding\IM Module\auto-im-generator\.claude\rules\`

| # | 파일 | 내용 | paths 필터 | 참조 |
|---|------|------|-----------|------|
| 1 | `python-style.md` | 네이밍, 타입 힌트, Pydantic v2 | `src/**/*.py` | FDD python-style.md |
| 2 | `financial-conventions.md` | Decimal 처리, 부호 규칙, KRW 정수 | `src/engines/**`, `src/services/**` | FDD financial-conventions.md |
| 3 | `database-rules.md` | SQLAlchemy async, N+1 방지, 마이그레이션 | `src/models/**`, `migrations/**` | FDD database-rules.md |
| 4 | `api-design.md` | FastAPI 패턴, 에러 응답, 페이지네이션 | `src/routers/**` | FDD api-design.md |
| 5 | `testing-rules.md` | pytest async, mocking, fixture | `tests/**` | FDD testing-rules.md |
| 6 | `pptx-rules.md` | python-pptx 패턴, 레이아웃, 폰트, 이미지 임베딩 | `src/engines/pptx*`, `src/services/pptx*` | **IM 고유** |
| 7 | `chart-standards.md` | Plotly 차트 (Waterfall, Donut, Combo, Bar, Line), 300DPI | `src/engines/chart*` | FDD chart-standards.md 확장 |
| 8 | `narrative-rules.md` | IM 내러티브 작성 규칙, 톤, 팩트체킹, 숫자 표기 | `src/engines/narrative*` | **IM 고유** |
| 9 | `security-checklist.md` | OWASP, DART API 키, PPTX 악성 매크로 검사 | `src/**/*.py` | FDD security-checklist.md |
| 10 | `git-workflow.md` | 브랜치, 커밋, PR 규칙 | — (글로벌) | FDD git-workflow.md |

---

## Implementation Order (우선순위)

### Priority 1 — 기반 설정 (먼저)
1. KIIS Rules 10개 → 코딩 표준 확립
2. KIIS MCP 1개 → Context7 활성화
3. Auto FDD Commands 8개 + MCP Context7 추가 → 워크플로우 자동화

### Priority 2 — 도메인 에이전트
4. KIIS Agents 10개 → 도메인 전문성
5. KIIS Hooks 6개 + settings.json → 안전장치

### Priority 3 — 보완
6. IM Module Rules 10개 → 코딩 표준
7. KIIS Commands 8개 → 워크플로우
8. KIIS Skills 10개 → 태스크 자동화

---

## Verification

구현 후 각 프로젝트에서 다음을 확인:

1. **Commands**: 각 프로젝트 디렉토리에서 Claude Code 실행 → `/plan`, `/review`, `/test` 등 호출
2. **Agents**: `@agent-name` 호출 → 응답 확인
3. **Skills**: `/skill-name` 호출 → 실행 확인
4. **Hooks**: 파일 수정 시 auto-format 작동, 위험 명령 차단 확인
5. **Rules**: 코드 작성 시 규칙 적용 여부 확인 (예: float 대신 Decimal 사용 유도)
6. **MCP**: Context7 서버 연결 확인
