# AMIC x PETRA Platform — 전체 적용 규칙 총람

> 작성일: 2026-02-23 12:11
> 이 문서는 이 프로젝트에 현재 적용 중인 **모든 규칙**을 단일 문서로 통합합니다.
> 원본 규칙 파일이 변경되면 이 문서도 함께 갱신하세요.

---

## 목차

1. [도구 실행 자율성 (전역)](#1-도구-실행-자율성-전역)
2. [언어 정책](#2-언어-정책)
3. [Git 워크플로우](#3-git-워크플로우)
4. [모노레포 전용 개발 규칙](#4-모노레포-전용-개발-규칙)
5. [문서 관리 규칙](#5-문서-관리-규칙)
6. [리뷰 문서화 규칙](#6-리뷰-문서화-규칙)
7. [코드 리뷰 원칙](#7-코드-리뷰-원칙)
8. [Verified Claim Protocol (VCP v1.1)](#8-verified-claim-protocol-vcp-v11)
9. [Review Gates (Phase 0B)](#9-review-gates-phase-0b)
10. [워크플로우 오케스트레이션 원칙](#10-워크플로우-오케스트레이션-원칙)
11. [컨텍스트 한계 관리](#11-컨텍스트-한계-관리)
12. [모듈별 규칙 — FDD](#12-모듈별-규칙--fdd)
13. [모듈별 규칙 — KIIS](#13-모듈별-규칙--kiis)
14. [모듈별 규칙 — IM](#14-모듈별-규칙--im)

---

## 1. 도구 실행 자율성 (전역)

**출처**: `~/.claude/settings.json` + `~/.claude/CLAUDE.md` + `MEMORY.md`

### 자동 승인 (확인 없이 즉시 실행)

| 도구 | 범위 |
|------|------|
| `Bash(*)` | 모든 터미널 명령 |
| `Edit(*)` | 모든 파일 수정 |
| `Write(*)` | 모든 파일 생성 |
| `Read(*)` | 모든 파일 읽기 |
| `WebSearch(*)` | 모든 웹 검색 |
| `WebFetch(*)` | 모든 URL 접근 |

### 위험 작업 (반드시 사용자 확인 필요)

| 명령 | 이유 |
|------|------|
| `git push --force` / `git push -f` | 원격 히스토리 덮어쓰기 |
| `git reset --hard` | 로컬 변경사항 전체 폐기 |
| `git clean -f` / `git clean -fd` | 미추적 파일 삭제 |
| `git branch -D` | 브랜치 강제 삭제 |
| `rm -rf` / `rm -fr` | 디렉토리/파일 재귀 삭제 |
| DB 테이블 DROP / 대규모 삭제 | 되돌릴 수 없는 데이터 손실 |
| 프로덕션 서버 직접 배포 | 운영 영향 |
| 외부 서비스 메시지 전송 (Slack, 이메일) | 공유 상태 변경 |

> `settings.json`의 `deny` 배열이 `allow: ["Bash(*)"]`보다 우선 적용됩니다.

---

## 2. 언어 정책

**출처**: `MEMORY.md`

- **모든 응답은 한국어**로 작성한다.
- 예외: 코드 자체, 파일명, 기술 용어 (TypeScript, API 등)는 영어 유지.
- 적용 범위: 대화, 설명, 분석, 플랜, 문서 등 모든 텍스트 출력.

---

## 3. Git 워크플로우

**출처**: `.claude/rules/git-workflow.md`

### 브랜치 전략

| 브랜치 | 목적 | Merge 대상 |
|--------|------|----------|
| `master` | Production-ready | — |
| `develop` | Integration | `master` |
| `feat/*` | 신규 기능 | `develop` |
| `fix/*` | 버그 수정 | `develop` |
| `hotfix/*` | 프로덕션 긴급 수정 | `master` + `develop` |

### 브랜치 네이밍 예시

```
feat/ma-workflow
feat/kiis-gp-search
fix/im-unreachable
hotfix/cors-security
```

### 커밋 메시지 (Conventional Commits)

```
feat(fdd/qoe): add adjustment candidate detection
fix(kiis/kofia): fix fund search pagination
fix(platform/dashboard): fix KPI loading state
docs(architecture): add MA workflow plan
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `style`

**Scopes**: `fdd/*`, `kiis/*`, `im/*`, `platform/*`, `docker`, `nginx`, `ci`

### PR 기준

- 최대 400 lines changed
- CI 통과 필수 (merge 전)
- Squash merge to develop/master
- 관련 이슈 링크 (있을 경우)

### CI 필수 체크

```yaml
# Backend (모듈별)
- ruff check
- ruff format --check
- pytest

# Frontend
- eslint
- tsc --noEmit
- vite build
```

### master 브랜치 보호 규칙

- PR 필수 (직접 커밋 금지)
- CI 통과 필수
- Force push 금지

---

## 4. 모노레포 전용 개발 규칙

**출처**: `amic-platform/.claude/rules/monorepo-only.md`

**백엔드 코드는 반드시 모노레포 내 경로만 수정한다.**

| 모듈 | 수정 경로 (모노레포) | 금지 경로 (단독 리포) |
|------|---------------------|---------------------|
| FDD | `fdd/backend/` | `Auto FDD/backend/` |
| KIIS | `kiis/` | `KIIS/` |
| IM | `im/` | `IM Module/auto-im-generator/` |
| MA | `deal-mgmt/` | — |

**이유**: Docker Compose가 모노레포 디렉터리를 볼륨 마운트하므로, 단독 리포 수정은 컨테이너에 미반영.

**규칙**:
1. 단독 리포 디렉터리는 읽기 전용 참조용 (수정 금지)
2. `docker compose up --build`로 변경사항 검증
3. 단독 리포 코드가 모노레포에 없으면 복사 후 수정

---

## 5. 문서 관리 규칙

**출처**: `amic-platform/.claude/rules/docs-organization.md` + `doc-filename-timestamp.md` + `CLAUDE.local.md`

### 파일명 형식

```
YYYYMMDD_HHMM_{문서명}.md
```

- 문서 수정 시마다 파일명 타임스탬프를 **수정 시점**으로 갱신
- 시간 확인: `powershell.exe -Command "Get-Date -Format 'yyyyMMdd_HHmm'"`

### docs 폴더 분류 체계

모든 문서는 `docs/{카테고리}/` 에 저장 (루트 `docs/` 직접 저장 금지)

| 폴더 | 대상 |
|------|------|
| `docs/architecture/` | 전체 구조, 통합 계획, 아키텍처 설계 |
| `docs/code-review/` | 코드 리뷰 리포트, VCP 프로토콜 |
| `docs/security/` | 보안 감사, JWT, CORS |
| `docs/deployment/` | 배포 체크리스트, CI/CD, Docker |
| `docs/fdd/` | FDD 모듈 전용 |
| `docs/kiis/` | KIIS 모듈 전용 |
| `docs/im/` | IM 모듈 전용 |
| `docs/frontend/` | 프론트엔드 공통 (UI/UX, 컴포넌트) |
| `docs/testing/` | 테스트 계획, E2E, 단위 테스트 전략 |

**새 문서 추가 시 `docs/INDEX.md` 업데이트 필수**

### 문서 작성 워크플로

```
1. 카테고리 결정
2. powershell Get-Date로 현재 시간 확인
3. docs/{카테고리}/YYYYMMDD_HHMM_{주제}.md 생성
4. docs/INDEX.md 업데이트
```

### 예외 (타임스탬프 불필요)

`CLAUDE.md`, `CLAUDE.local.md`, `README.md`, `MEMORY.md`, `docs/INDEX.md`, `review/INDEX.md`

---

## 6. 리뷰 문서화 규칙

**출처**: `amic-platform/.claude/rules/review-documentation.md`

**모든 오류 수정 및 리뷰 내역은 `review/{카테고리}/` 폴더에 문서화 필수**

### 카테고리

| 카테고리 | 폴더 |
|---------|------|
| 버그 수정 | `review/bugfix/` |
| 보안 취약점 | `review/security/` |
| 코드 리뷰 수정 | `review/review/` |
| 리팩토링 | `review/refactor/` |
| 접근성 | `review/a11y/` |
| 성능 | `review/perf/` |
| 긴급 수정 | `review/hotfix/` |
| 타입 오류 | `review/type/` |
| 빌드 오류 | `review/build/` |
| UI/UX 수정 | `review/ui/` |

### 파일명 형식

```
review/{카테고리}/YYYYMMDD_HHMM_{요약}.md
```

**새 리뷰 문서 추가 시 `review/INDEX.md` 업데이트 필수**

### 문서화 생략 가능

- 단순 오타 수정 (동작 영향 없음)
- 주석/문서만 수정
- 자동 포매팅 변경 (prettier, eslint --fix)

---

## 7. 코드 리뷰 원칙

**출처**: `amic-platform/.claude/rules/code-review.md`

1. **사실 기반**: 이슈 보고 시 **파일 경로 + 라인 번호** 반드시 포함. 추측성 표현 금지.
2. **수치 정확성**: 파일 수, 이슈 수는 Glob/Grep으로 직접 카운트. 이전 세션 수치 재인용 금지.
3. **이슈 ID 참조**: 기존 리뷰 문서 이슈 참조 시 원본 문서를 Read하여 ID 확인.
4. **코드 패턴 주장**: "X 패턴 사용" → Grep으로 실제 존재 확인. 단일 파일 패턴 일반화 금지.
5. **리뷰 자체 검증**: `review-verifier` 에이전트로 수치, 파일 경로, 이슈 참조 재확인.
6. **수정 검증**: "수정됨" 판정 시 현재 코드를 Read하여 확인. 추측 금지.
7. **수정 내역 문서화**: 오류 수정 후 `review/{카테고리}/` 폴더에 문서 작성.

---

## 8. Verified Claim Protocol (VCP v1.1)

**출처**: `amic-platform/.claude/rules/verified-claim-protocol.md`

코드 리뷰 에이전트가 이슈를 보고하기 전 반드시 수행하는 **6단계 검증 프로토콜**.

### 6단계 순서

| 단계 | 내용 |
|------|------|
| **1단계** | Glob으로 파일 존재 확인 |
| **2단계** | Read로 실제 코드 직접 읽기 |
| **3단계** | 주장 유형별 검증 (Grep, 컨텍스트 확인 등) |
| **3.5단계** | Self-Challenge (SC-1~SC-6) — 적대적 재검토 |
| **4단계** | Read 결과의 실제 코드 스니펫 증거 첨부 |
| **5단계** | 신뢰도 점수 부여 (HIGH/MEDIUM/LOW) |

### Self-Challenge 항목

| 항목 | 질문 |
|------|------|
| SC-1 | 실제 실행 가능한 코드 경로인가? (dead code 아닌지) |
| SC-2 | "X가 없다" 재확인 (barrel export 등 우회 경로 포함) |
| SC-3 | 라이브러리가 내부 처리하는 기능을 "누락"으로 오판하지 않았는가? |
| SC-4 | 백엔드 스키마 불일치 주장 시 실제 백엔드 코드를 읽었는가? |
| SC-5 | 코드베이스 전체에서 동일 패턴이 사용되는가? |
| SC-6 | 제안한 수정안이 타입 에러/런타임 오류를 유발하지 않는가? |

**SC-1~SC-5 중 하나라도 ✗ → 해당 이슈 REJECT (보고하지 않음)**

### 우선순위 계산

```
우선순위 점수 = (심각도 가중치 × 신뢰도 가중치) + 보너스

심각도: Critical=100, Major=70, Moderate=40, Minor=20
신뢰도: HIGH=1.0, MEDIUM=0.6, LOW=0.3
보너스: 교차 검증+10, review-verifier 확인+15

P0: 90+, P1: 60-89, P2: 30-59, P3: <30
```

**Critical + MEDIUM 신뢰도 = 60점 → P1 (P0 아님)**

### 금지 패턴

- 추측성 표현 ("~인 것 같다", "probably")
- Read 없이 라인 번호 기재
- 메모리 기반 코드 인용
- 단일 파일에서 확인한 패턴을 타 파일에 일반화
- "X가 없다"를 Grep 없이 주장
- 이전 세션 수치 재사용

---

## 9. Review Gates (Phase 0B)

**출처**: `amic-platform/.claude/rules/review-gates.md`

에이전트 실행 전 사전 검증. Phase 0A(Quality Gates) 통과 후 Phase 1 전 실행.

### 검증 항목 4가지

**1. 백엔드 가용성 체크**
- Glob으로 백엔드 Python 파일 존재 확인
- 미제공 백엔드 관련 이슈는 LOW 신뢰도로만 보고

**2. 범위-에이전트 필터링**

| 에이전트 | 적용 파일 |
|---------|----------|
| code-reviewer | `**/*.{ts,tsx}` |
| api-auditor | `**/hooks/*.ts`, `**/api/*.ts`, `**/types/*.ts` |
| security-auditor | `**/*.{ts,tsx}`, `.env*`, `vite.config.ts` |
| test-auditor | `**/*.test.{ts,tsx}`, `**/e2e/**/*.ts` |
| accessibility-auditor | `**/*.tsx` |
| infra-auditor | `Dockerfile`, `docker-compose*.yml`, `nginx/**` |

매칭 파일이 없는 에이전트는 호출하지 않음.

**3. 스키마 드리프트 탐지** (중기 구현)
- 프론트엔드 타입 vs 백엔드 스키마 필드명 비교

**4. 목 데이터 최신성 체크** (장기 구현)
- 하드코딩된 날짜 30일 이상 경과 시 경고

---

## 10. 워크플로우 오케스트레이션 원칙

**출처**: `amic-platform/.claude/rules/workflow-orchestration.md`

### 플랜 우선 원칙

**플랜 모드(`EnterPlanMode`) 진입 기준** (하나라도 해당):
- 3개 이상 파일 수정
- 아키텍처/설계 결정 필요
- 접근 방법 2가지 이상
- 요구사항 불명확

**예외** (바로 실행): 오타 수정, 1~2줄 버그 픽스, 단순 리네임

### 서브에이전트 전략

- 독립적 탐색 작업은 **최대 3개 병렬** 실행
- 메인 컨텍스트 윈도우 보호 목적으로 적극 활용
- 각 에이전트는 하나의 명확한 역할만 수행

### 완료 검증 기준 (Definition of Done)

**공통 (모든 작업)**:
- "Staff Engineer가 이 코드를 승인할까?" 자문
- 변경된 동작과 기존 동작의 차이 설명 가능
- 의도치 않은 사이드 이펙트 없음 확인

**Feature**: `tsc --noEmit` + ESLint 통과 + 핵심 흐름 실행 확인
**Bugfix**: 원래 버그 재현 안 됨 확인 + 수정 범위 최소화
**Refactor**: 동작 변경 없음 + 기존 테스트 전원 통과

### 자율 버그 수정

- 버그 리포트 수신 시 핸드홀딩 없이 즉시 자율 수정
- 사용자 확인 필요한 예외: 스키마/API 계약 변경, 보안 수정, 데이터 마이그레이션

### 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **Simplicity First** | 가장 단순한 변경, 최소 코드 영향 |
| **No Laziness** | 근본 원인 파악, 임시방편 금지 |
| **Minimal Impact** | 요청된 것만 건드림, 사이드 이펙트 금지 |
| **No Speculation** | 읽지 않은 코드에 제안하지 않음 |
| **Reversibility Aware** | 되돌리기 어려운 작업은 사용자 확인 |

### 자기 개선 루프

- 사용자가 실수를 지적하면 즉시 `MEMORY.md`에 학습 내용 기록
- 반복 패턴이면 별도 토픽 파일 생성
- 틀린 메모리 항목 즉시 수정 또는 삭제

---

## 11. 컨텍스트 한계 관리

**출처**: `CLAUDE.local.md` + `fdd/CLAUDE.md` + `im/CLAUDE.md`

- 컨텍스트 부족 예상 시 **즉시 작업 중단**
- 중단 시 반드시 수행:
  1. 완료/미완료 작업 목록 정리
  2. 이어가기 위한 컨텍스트 요약
  3. `CLAUDE.local.md`에 진행 상황 기록
  4. 사용자에게 새 세션 안내
- **절대 금지**: 컨텍스트 부족 상태에서 억지로 계속 진행

---

## 12. 모듈별 규칙 — FDD

**출처**: `fdd/CLAUDE.md`

### 금전 규칙 (CRITICAL)

- 모든 금액: Python `Decimal`, JSON/TypeScript `string` — **`float` 절대 금지**
- DB 컬럼: `NUMERIC(18,4)` 예외 없음
- KRW: 소수점 0자리, FX 환율: 최대 4자리
- 반올림: `quantize()` 명시적 사용 (암묵적 반올림 금지)

### 아키텍처 규칙

- **Report IR Pattern**: engines → report_builder.py → JSON IR → renderers
- **Engine 함수**: 순수 함수, `tuple[Result, list[EvidenceLink]]` 반환, DB 접근·사이드 이펙트 금지
- **LLM 경계**: 계산 = rule engine 전용. LLM = 판단/텍스트 분석 전용. 모든 LLM 출력 = JSON Schema 강제

### API URL 형식

`/api/v1/qoe-bridge` (kebab-case)

---

## 13. 모듈별 규칙 — KIIS

**출처**: `kiis/CLAUDE.md`

- async/await 패턴 필수 (동기 함수 금지)
- Pydantic v2: `model_config = ConfigDict(from_attributes=True)`
- DB: `expire_on_commit=False` 필수
- API: `/api/v1/{domain}/{resource}`, 페이지네이션 최대 100
- DART API Rate Limit: 분당 900회
- `migrations/versions/` 수동 편집 금지 — Alembic으로만 관리
- 테스트 모킹: `pytest-httpx`, URL은 `url=re.compile(r".*pattern.*")` regex 사용

### 자동화 훅 (KIIS)

- PreToolUse (Edit|Write): `.env`, `migrations/versions/` 편집 자동 차단
- PostToolUse (Edit|Write): `.py` 편집 후 자동 `ruff format` + `ruff check --fix`

---

## 14. 모듈별 규칙 — IM

**출처**: `im/CLAUDE.md`

- 재무 계산 로직: 단위 테스트 먼저 작성 후 구현 (TDD)
- DART API 키 등 시크릿: 코드 하드코딩 절대 금지 (`.env` 사용)
- DART API Rate Limit: 분당 100회
- 재무 수치: DART 원본과 정확히 일치 (근사치 금지)
- 외부 API 호출 시 에러 핸들링 + 재시도 로직 필수
- 커밋 전: black + isort + mypy + pytest 실행

---

## 규칙 파일 원본 위치

| 규칙 | 원본 경로 |
|------|----------|
| 전역 도구 자율성 | `~/.claude/CLAUDE.md` + `~/.claude/settings.json` |
| 언어 정책 | `~/.claude/projects/.../memory/MEMORY.md` |
| Git 워크플로우 | `amic-platform/.claude/rules/git-workflow.md` |
| 모노레포 전용 | `amic-platform/.claude/rules/monorepo-only.md` |
| 문서 조직 | `amic-platform/.claude/rules/docs-organization.md` |
| 파일명 타임스탬프 | `amic-platform/.claude/rules/doc-filename-timestamp.md` |
| 리뷰 문서화 | `amic-platform/.claude/rules/review-documentation.md` |
| 코드 리뷰 원칙 | `amic-platform/.claude/rules/code-review.md` |
| VCP v1.1 | `amic-platform/.claude/rules/verified-claim-protocol.md` |
| Review Gates | `amic-platform/.claude/rules/review-gates.md` |
| 워크플로우 오케스트레이션 | `amic-platform/.claude/rules/workflow-orchestration.md` |
| 컨텍스트 관리 | `CLAUDE.local.md` |
| FDD 규칙 | `fdd/CLAUDE.md` |
| KIIS 규칙 | `kiis/CLAUDE.md` |
| IM 규칙 | `im/CLAUDE.md` |
