---
name: review-orchestrate
description: 멀티 에이전트 코드 리뷰 오케스트레이션. 자동 품질 검사 + 병렬 에이전트 리뷰 + 교차 검증 + 리포트 생성.
user-invokable: false
argument-hint: "type scope flags"
---

# 코드 리뷰 오케스트레이터

멀티 에이전트 코드 리뷰를 4단계 파이프라인으로 오케스트레이션합니다.

## 입력 파싱

호출 시 전달받는 파라미터:

- **type**: `full | quick | security | test | perf | infra`
- **scope**: 리뷰 대상 (아래 스코프 규칙 참조)
- **flags**: `--skip-gates`, `--backend`, `--severity critical|major` 등

### 스코프 규칙

| 인자 | 동작 |
|------|------|
| (없음) | 전체 코드베이스 |
| `--diff` | `git diff --name-only HEAD` 변경 파일 |
| `--diff main` | main 브랜치 대비 변경 파일 |
| `--module fdd\|kiis\|im\|platform` | 해당 모듈 디렉터리 |
| `--files path1 path2` | 특정 파일만 |
| `--backend` | 백엔드 코드 포함 (FDD/KIIS/IM 백엔드 경로) |
| `--severity critical\|major` | 해당 심각도 이상만 보고 |

### 에이전트 매트릭스

| type | 사용 에이전트 |
|------|-------------|
| `quick` | code-reviewer |
| `full` | code-reviewer + type-checker + api-auditor + security-auditor + a11y-auditor |
| `security` | security-auditor + api-auditor |
| `test` | test-auditor |
| `perf` | perf-auditor |
| `infra` | infra-auditor |

---

## 실행 파이프라인

### Phase 0A: Quality Gates (자동 품질 검사)

`--skip-gates` 플래그가 없으면 아래를 순서대로 실행:

```bash
cd amic-platform
npx tsc --noEmit          # TypeScript 타입 체크
npm run lint              # ESLint (--max-warnings 0)
npm run test              # Vitest 유닛 테스트
npm run build             # Vite 프로덕션 빌드
```

결과를 `machine_findings`로 수집합니다:
- 각 단계의 PASS/FAIL 상태
- 실패 시 에러 메시지 요약

> Phase 0A가 전부 PASS해도 Phase 1을 수행합니다 (자동 검사로 잡을 수 없는 논리적 이슈 탐지).

### Phase 0B: Review Gates (사전 검증)

**목적**: 에이전트 실행 전 허위 양성 발생 전제 조건 탐지

`--skip-gates` 플래그가 없으면 실행. 상세 규칙은 `amic-platform/.claude/skills/review-orchestrate/docs/gates.md` 참조.

#### 실행 단계

1. **백엔드 가용성 체크**:
   ```bash
   # Glob으로 백엔드 Python 파일 존재 확인
   Auto FDD/backend/**/*.py
   KIIS/**/*.py
   IM Module/**/*.py
   ```
   결과: `backend_fdd_available`, `backend_kiis_available`, `backend_im_available` 플래그 설정

2. **범위-에이전트 필터링**:
   - 리뷰 대상 파일 목록과 각 에이전트의 호환성 매트릭스 매칭
   - 매칭되는 파일이 없는 에이전트는 Phase 1에서 제외
   - 호환성 매트릭스는 이 스킬의 `docs/gates.md` 참조

3. **스키마 드리프트 탐지** (선택적, 중기 구현):
   - 프론트엔드 타입 정의와 백엔드 스키마 비교
   - 필드명 불일치 보고

4. **목 데이터 최신성 체크** (선택적, 장기 구현):
   - 하드코딩된 날짜 패턴 검색
   - 30일 이상 경과한 날짜 경고

#### 결과 수집

`gate_results` 객체로 수집:
```json
{
  "backend_availability": {
    "fdd": true/false,
    "kiis": true/false,
    "im": true/false
  },
  "agent_filtering": {
    "included": ["code-reviewer", "type-checker", ...],
    "excluded": ["api-auditor", ...],
    "reason": "매칭 파일 없음"
  },
  "schema_drift": {
    "fdd": ["field1", "field2"],
    "kiis": [],
    "im": []
  }
}
```

#### 에이전트 컨텍스트 전달

Phase 1의 각 에이전트 호출 시 `gate_results`를 컨텍스트로 포함:

```
[Phase 0B 검증 결과]
백엔드 가용성:
- FDD Backend: {available/unavailable}
- KIIS Backend: {available/unavailable}
- IM Backend: {available/unavailable}

⚠️ 백엔드가 unavailable인 경우, 해당 백엔드에 대한 이슈는 낮은 신뢰도(LOW)로만 보고하거나 보고하지 않습니다.

스키마 드리프트:
- FDD: 불일치 필드 N개 ({field1, field2})
- KIIS: 일치 (✓)
```

### Phase 1: Verified Review (병렬 에이전트 리뷰)

에이전트 매트릭스에서 선택된 에이전트들을 **Task 도구로 병렬 호출**합니다.

각 에이전트 호출 시 전달하는 프롬프트:

```
{에이전트명} 에이전트 역할로 동작하세요.
.claude/agents/{에이전트명}.md의 지침과
amic-platform/.claude/skills/review-orchestrate/docs/vcp.md의 프로토콜을 따릅니다.
리뷰 관점은 amic-platform/.claude/skills/review-orchestrate/docs/checklist.md의 §1~§4 체크리스트를 참조합니다.

리뷰 대상: {스코프에 해당하는 파일/디렉터리 목록}
{--backend이면: 백엔드 경로도 포함}

모든 이슈에 대해 반드시:
1. Read로 실제 코드를 확인한 뒤 클레임
2. 증거(실제 코드 스니펫) 첨부
3. 신뢰도 점수 (HIGH/MEDIUM/LOW) 부여
4. 가설이 반증되면 보고하지 않기
5. **3.5단계 Self-Challenge**: 이슈 초안 완성 후 SC-1~SC-6 체크리스트 적용
   - SC-1~SC-5 중 하나라도 ✗ → 이슈 기각 (보고하지 않음)
   - △ 항목 수에 따라 신뢰도 자동 하향 (1개 → MEDIUM, 2개 이상 → LOW)

출력은 Verified Claim Protocol 표준 형식을 따릅니다.
이슈 헤더 형식: `[{ID}] {제목} — [{심각도}/{신뢰도}] — Priority: {P0/P1/P2/P3}`
```

**병렬 실행 규칙**:
- 독립적인 에이전트는 동시에 호출 (예: code-reviewer와 type-checker)
- Task 도구의 `run_in_background` 활용 가능
- 각 에이전트의 결과를 `agent_findings[]`로 수집

### Phase 2: Cross-Verification (교차 검증)

Phase 1에서 **Critical 또는 Major**로 보고된 이슈만 대상으로 합니다.

Task 도구로 `review-verifier` 에이전트를 호출:

```
review-verifier 에이전트의 인라인 검증 모드로 동작하세요.
.claude/agents/review-verifier.md의 지침을 따릅니다.

아래 이슈들을 실제 코드와 대조 검증하세요:
{Critical/Major 이슈 목록 — ID, 파일, 라인, 설명}

각 이슈에 대해:
1. Phase 1 에이전트와 독립적으로 Glob + Read로 코드를 직접 확인
2. VCP Self-Challenge(3.5단계) SC-1~SC-6 체크리스트 각 이슈에 적용
3. 5단계 판정: CONFIRMED / FALSE_POSITIVE / PARTIAL / DESIGN_RISK / LINE_MISMATCH
4. 허위 양성은 FP 6종 원인 분류(FP-IMPL/FP-HALLUC/FP-LINE/FP-LOGIC/FP-CTX/FP-SEV) 필수
```

교차 검증 결과에 따라:
- **정확**: 유지
- **허위 양성**: 제거
- **부분 정확**: 심각도 조정
- **설계 리스크**: 기술부채로 분류
- **라인 불일치**: 올바른 위치로 수정

> Critical/Major가 0건이면 Phase 2를 건너뜁니다.

### Phase 2B: Auto-Verification (자동 검증)

**목적**: Moderate 및 Minor 이슈의 자동 검증 (검증 범위 30% → 100%)

Phase 2(교차 검증)는 Critical + Major만 대상이므로, Moderate + Minor 이슈를 자동 검증합니다.

#### 실행 조건

Moderate 또는 Minor 이슈가 1건 이상 있을 때만 실행.

#### 실행 단계

1. **이슈 목록 준비**:
   - Phase 1에서 보고된 Moderate + Minor 이슈 수집
   - JSON 형식으로 변환 (ID, severity, file, line, code_snippet, claim_type 등)

2. **auto-verify 스킬 호출**:
   ```
   Skill 도구로 auto-verify 호출:
   - 입력: issues_json
   - 출력: 검증 결과 (verified, flagged)
   ```

3. **검증 결과 처리**:
   - **verified**: 이슈 유지
   - **flagged**: "⚠️ 자동 검증 실패 — 수동 검토 필요" 표시 추가
     - 우선순위 1단계 하향 (예: P2 → P3)
     - 신뢰도를 MEDIUM 또는 LOW로 조정

#### auto-verify 검증 방법

`.claude/skills/auto-verify/SKILL.md` 참조. 4단계 자동 체크:

1. **파일 존재 확인** (25점): Glob으로 파일 존재 여부
2. **라인 번호 검증** (25점): Read로 라인 ±5 이내 확인
3. **코드 스니펫 매칭** (50점): 보고된 코드 vs 실제 코드 퍼지 매칭 (80% 임계값)
4. **패턴 주장 검증** (10점): "X가 없다" → Grep으로 부재 확인

**판정**: 총점 ≥75 → 검증됨, <75 → 수동 검토 플래그

#### 결과 보고

```
Phase 2B 자동 검증:
- Moderate 이슈: 18/23건 검증됨 (78%)
- Minor 이슈: 12/15건 검증됨 (80%)
- 수동 검토 플래그: 8건
  - [m-R2]: 코드 스니펫 불일치 (점수: 45)
  - [L-A1]: 라인 번호 범위 초과 (점수: 35)
  - ...
```

> Moderate/Minor가 0건이면 Phase 2B를 건너뜁니다.

### Phase 3: Report Assembly (리포트 조립)

모든 Phase의 결과를 병합하여 최종 리포트를 생성합니다.

**병합 규칙**:
- 같은 파일 + 같은 라인 범위 + 같은 관심사 → 병합 (높은 심각도 유지)
- 두 에이전트가 같은 이슈 발견 → "교차 검증됨" 표시 (+10 보너스)

**신뢰도 가중 우선순위 계산**:

각 이슈에 대해 우선순위 점수를 계산합니다 (`amic-platform/.claude/skills/review-orchestrate/docs/vcp.md` 참조):

```
우선순위 점수 = (심각도 가중치 × 신뢰도 가중치) + 보너스
```

1. **심각도 가중치 할당**:
   - Critical: 100
   - Major: 70
   - Moderate: 40
   - Minor: 20

2. **신뢰도 가중치 적용**:
   - HIGH (90%+): ×1.0
   - MEDIUM (60-89%): ×0.6 (40% 하향)
   - LOW (<60%): ×0.3 (70% 하향)

3. **보너스 가산**:
   - 교차 검증 (2+ 에이전트): +10
   - review-verifier 확인: +15

4. **우선순위 등급 부여**:
   - P0 (90+): 즉시 수정 (보안/데이터 무결성)
   - P1 (60-89): 스프린트 우선 (안정성/정확성)
   - P2 (30-59): 개선 권장 (코드 품질)
   - P3 (<30): 저우선 (개선 가능)

**정렬 및 조직**:
- 모든 이슈를 우선순위 점수 기준 내림차순 정렬
- 같은 우선순위 등급 내에서는 심각도 기준 정렬
- 신뢰도 하향된 이슈(MEDIUM/LOW)에 주석 표시:
  ```
  ⚠️ 이 치명적(Critical) 이슈는 중간 신뢰도(MEDIUM)로 인해 P1으로 분류되었습니다.
  ```

**추가 섹션** (이 스킬의 docs/checklist.md 연계):

```markdown
## 계획 대비 구현 검증 (§6)

{최초 계획 문서가 제공된 경우 — 이 스킬의 docs/checklist.md §6 형식으로 작성}

| # | 계획된 항목 | 구현 상태 | 검증 근거 (파일:라인) |
|---|-----------|---------|---------------------|
| 1 | {항목}    | ✅/❌/⚠️ | {파일:라인}           |

## 품질 게이트 상태 (§7)

{CI 결과 조회 가능 시 — docs/checklist.md §7 형식으로 작성}

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| ruff/eslint | ✅/❌/⚠️ | §1 정합성 {자동 검증됨/수동 검토} |
| pytest/vitest | ✅/❌/⚠️ | §2 완전성 {자동 검증됨/수동 검토} |
```

**리포트 저장**:
- bash로 현재 시간 확인: `date '+%Y%m%d_%H%M'`
- 파일명: `docs/YYYYMMDD_HHMM_{Scope}_Code_Review.md`

---

## 최종 리포트 형식

```markdown
# Code Review — {Scope}

> **Review Date**: YYYY-MM-DD HH:MM
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: {스코프 설명}
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc({PASS/FAIL}) eslint({PASS/FAIL}) vitest({PASS/FAIL}) build({PASS/FAIL})
> **Review Gates**: Backend({available/unavailable}) Agent-Filtering({N개 에이전트 호출})

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | N     | HIGH: N / MEDIUM: N / LOW: N | P0: N / P1: N |
| Major    | N     | HIGH: N / MEDIUM: N / LOW: N | P0: N / P1: N / P2: N |
| Moderate | N     | HIGH: N / MEDIUM: N / LOW: N | P1: N / P2: N / P3: N |
| Minor    | N     | HIGH: N / MEDIUM: N / LOW: N | P2: N / P3: N |
| **Total**| **N** | HIGH: **N** / MEDIUM: **N** / LOW: **N** | P0: **N** / P1: **N** / P2: **N** / P3: **N** |

**FP Prevention**: 가설 N건 검증, N건 사전 거부 (거부율: X%) | 교차 검증 N건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 N건 하향 조정 (Critical→P1, Major→P2 등)
- LOW 신뢰도 이슈 N건 하향 조정

## Findings

{Verified Claim Protocol 표준 형식의 이슈 목록 — 우선순위 점수 내림차순 정렬}

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)
1. [ID] [Critical/HIGH]: one-line summary — file (점수: {N})

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)
1. [ID] [Critical/MEDIUM ⚠️]: one-line summary — file (점수: {N}, 신뢰도 하향됨)
2. [ID] [Major/HIGH]: one-line summary — file (점수: {N})

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
1. [ID] [Moderate/HIGH]: one-line summary — file (점수: {N})

### P3 — 저우선 (점수: <30, 개선 가능)
1. [ID] [Minor/MEDIUM ⚠️]: one-line summary — file (점수: {N})

## Methodology

- Agents: {사용된 에이전트 목록}
- Excluded Agents: {범위-에이전트 필터링으로 제외된 에이전트}
- Files scanned: {파일 수}
- Protocol: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- Cross-verification: Critical + Major
- Backend availability: FDD({available/unavailable}) KIIS({available/unavailable}) IM({available/unavailable})

## 검증 투명성

### 검증 통계
- 검증한 가설: N건
- 거부된 가설 (사전 제거): N건
- 보고된 이슈: N건
- 거부율: X%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | N | "X가 없다" → Grep으로 발견 |
| 범위 외 | N | 백엔드 이슈이나 백엔드 미제공 |
| 이미 수정됨 | N | 코드 읽어보니 이미 구현됨 |
| 오판 | N | 코드 로직 잘못 이해 |
| 중복 | N | 다른 에이전트가 이미 보고 |
| 신뢰도 불충분 | N | 증거 약함 (LOW 미만) |
```

---

## 요약 출력

리포트 저장 후 사용자에게 요약을 출력합니다:

```
## 리뷰 완료

### 범위 및 검증
- 대상: {스코프}
- 대상 파일: N개
- Quality Gates: tsc(✓) eslint(✓) vitest(✓) build(✓)
- Review Gates: Backend(✓) Agent-Filtering(N개 호출, N개 제외)

### 발견 이슈
- 총 N건 (Critical: N, Major: N, Moderate: N, Minor: N)
- 우선순위: P0(N건) P1(N건) P2(N건) P3(N건)
- 신뢰도 분포: HIGH(N건) MEDIUM(N건) LOW(N건)

### 허위 양성 방지
- 교차 검증: N건 수행 (FP 제거: N건)
- 검증 투명성: 가설 N건 검증, N건 사전 거부 (거부율: X%)
- 거부 사유: 반증됨(N) 범위외(N) 이미수정됨(N) 오판(N) 중복(N) 신뢰도불충분(N)

### 신뢰도 가중 우선순위
- MEDIUM 신뢰도 하향: N건 (Critical→P1, Major→P2 등)
- LOW 신뢰도 하향: N건

### 리포트
- 파일: docs/YYYYMMDD_HHMM_{Scope}_Code_Review.md
- 프로토콜: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
```
