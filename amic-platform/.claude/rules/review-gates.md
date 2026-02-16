# Review Gates (0B단계)

**작성일**: 2026-02-16 19:21:44
**목적**: 에이전트 실행 전 허위 양성 발생 전제 조건 탐지

---

## 개요

이 게이트는 코드 리뷰 오케스트레이터의 Phase 0A(Quality Gates)와 Phase 1(Agent Review) 사이에서 실행됩니다.

**목표**: 에이전트가 잘못된 가정 하에 작동하지 않도록 사전 검증을 수행합니다.

---

## 검증 항목

### 1. 백엔드 가용성 체크

**목적**: 백엔드 코드가 실제로 존재하는지 확인하여 환각 방지

**실행 방법**:
```bash
# 각 백엔드 경로에서 Python 파일 검색
Glob: "Auto FDD/backend/**/*.py"
Glob: "KIIS/**/*.py"
Glob: "IM Module/**/*.py"
```

**결과 플래그**:
- `backend_fdd_available`: true/false (FDD 백엔드 존재 여부)
- `backend_kiis_available`: true/false (KIIS 백엔드 존재 여부)
- `backend_im_available`: true/false (IM 백엔드 존재 여부)

**에이전트 컨텍스트 전달**:
```
백엔드 가용성 상태:
- FDD Backend: {available/unavailable}
- KIIS Backend: {available/unavailable}
- IM Backend: {available/unavailable}

⚠️ 백엔드가 unavailable인 경우, 해당 백엔드에 대한 이슈는 낮은 신뢰도(LOW)로만 보고하거나 보고하지 않습니다.
```

**영향**:
- api-auditor, security-auditor가 백엔드 미제공 시 환각 방지
- 백엔드 코드 드리프트로 인한 허위 양성 90% 감소 예상

---

### 2. 스키마 드리프트 탐지

**목적**: 프론트엔드 타입 정의와 백엔드 API 응답 스키마가 불일치하는지 탐지

**실행 방법** (점진적 구현):

**Phase 1 — 필드명 비교 (1주차)**:
1. 프론트엔드 타입 파일 Glob: `amic-platform/src/modules/{fdd,kiis,im}/types/**/*.ts`
2. 백엔드 스키마 파일 Glob:
   - FDD: `Auto FDD/backend/app/schemas/*.py`
   - KIIS: `KIIS/app/schemas/*.py`
   - IM: `IM Module/auto-im-generator/app/schemas/*.py`
3. 각 모듈별로 주요 타입과 스키마 매칭:
   - `types/deal.ts` ↔ `schemas/deal.py` (FDD)
   - `types/company.ts` ↔ `schemas/company.py` (KIIS)
   - `types/document.ts` ↔ `schemas/document.py` (IM)
4. 필드명 추출 (정규식):
   - TypeScript: `(\w+):\s*[^;]+;`
   - Python: `(\w+):\s*[^=\n]+`
5. 불일치 보고:
   - FE에만 있는 필드: `{field}` (백엔드에서 제거됨 가능성)
   - BE에만 있는 필드: `{field}` (프론트엔드 미반영)

**Phase 2 — 타입 호환성 비교 (중기, 4-6주차)**:
- TypeScript 타입 → 예상 Python 타입 매핑
- 타입 불일치 탐지 (예: `string` ↔ `int`)

**결과 보고**:
```
스키마 드리프트 탐지:
- FDD: 불일치 필드 N개 발견 ({field1, field2})
- KIIS: 불일치 필드 N개 발견
- IM: 일치 (✓)

⚠️ 불일치 필드가 있는 경우, api-auditor가 해당 필드 관련 이슈를 보고할 때 컨텍스트에 포함합니다.
```

**영향**:
- API 스키마 진화로 인한 허위 양성 방지
- 실제 API 불일치 이슈 조기 발견

---

### 3. 목 데이터 최신성 체크

**목적**: 테스트/개발 목 데이터의 하드코딩된 날짜가 오래되어 테스트 실패를 유발하지 않도록 경고

**실행 방법**:
```bash
# 하드코딩된 날짜 패턴 검색 (YYYY-MM-DD 형식)
Grep: "20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])"
  - glob: "amic-platform/src/test/mocks/**/*.ts"
  - glob: "amic-platform/src/**/*.test.tsx"
```

**날짜 검증 로직**:
1. 발견된 각 날짜 문자열을 현재 날짜와 비교
2. 30일 이상 경과한 날짜가 5개 이상이면 경고

**결과 보고**:
```
목 데이터 최신성:
- 총 하드코딩된 날짜: N개
- 30일 이상 경과: N개
- 경고: {파일 경로} — {날짜} (N일 경과)

⚠️ 오래된 날짜가 많으면 테스트 실패 원인이 될 수 있습니다.
```

**영향**:
- 날짜 기반 테스트 실패 사전 탐지
- 개발 환경 신뢰도 향상

---

### 4. 범위-에이전트 필터링

**목적**: 리뷰 대상 파일 유형에 적합한 에이전트만 호출하여 범위 확장 허위 양성 방지

**에이전트-파일 호환성 매트릭스**:

| 에이전트 | 적용 가능 파일 패턴 | 제외 패턴 |
|---------|-------------------|----------|
| code-reviewer | `**/*.{ts,tsx}` | - |
| type-checker | `**/*.{ts,tsx}` | `**/*.test.{ts,tsx}` |
| api-auditor | `**/hooks/*.ts`, `**/api/*.ts`, `**/types/*.ts` | `**/ui/*.tsx` |
| security-auditor | `**/*.{ts,tsx}`, `.env*`, `vite.config.ts` | `**/*.test.tsx` |
| test-auditor | `**/*.test.{ts,tsx}`, `**/e2e/**/*.ts` | - |
| perf-auditor | `**/*.{ts,tsx}`, `vite.config.ts` | `**/test/**`, `**/e2e/**` |
| infra-auditor | `Dockerfile`, `docker-compose*.yml`, `nginx/**`, `package.json` | `src/**` |
| accessibility-auditor | `**/*.tsx` | `**/*.test.tsx`, `**/types/**` |
| component-reviewer | `**/components/**/*.tsx` | `**/*.test.tsx` |

**실행 로직**:
1. 리뷰 대상 파일 목록을 Glob/Git로 수집
2. 각 에이전트의 적용 가능 패턴과 매칭
3. 매칭되는 파일이 없는 에이전트는 호출하지 않음
4. 매칭되는 파일만 해당 에이전트에 전달

**예시**:
```
리뷰 대상: src/lib/format.ts, src/components/ui/Button.tsx

필터링 결과:
✓ code-reviewer → 2개 파일
✓ type-checker → 2개 파일
✗ api-auditor → 매칭 0개 (제외)
✓ security-auditor → 2개 파일
✗ test-auditor → 매칭 0개 (제외)
✓ perf-auditor → 2개 파일
✗ infra-auditor → 매칭 0개 (제외)
✓ accessibility-auditor → Button.tsx (1개)
✓ component-reviewer → Button.tsx (1개)
```

**결과 보고**:
```
범위-에이전트 필터링:
- 호출할 에이전트: N개
- 제외된 에이전트: N개 (이유: 매칭 파일 없음)
```

**영향**:
- 유틸 함수에서 UI/UX 패턴 이슈 플래그 방지
- 불필요한 에이전트 실행 제거 → 리뷰 속도 향상

---

## 통합 방법

review-orchestrate/SKILL.md의 Phase 0A와 Phase 1 사이에 삽입:

```markdown
### Phase 0B: Review Gates (사전 검증)

Phase 0A(Quality Gates) 통과 후, 에이전트 호출 전에 실행:

1. **백엔드 가용성 체크**:
   - Glob으로 백엔드 디렉터리 존재 확인
   - 결과: backend_{module}_available 플래그

2. **범위-에이전트 필터링**:
   - 리뷰 대상 파일과 에이전트 호환성 매칭
   - 매칭 없는 에이전트 제외

3. **스키마 드리프트 탐지** (선택적, 4-6주차):
   - 프론트엔드 타입 vs 백엔드 스키마 비교
   - 불일치 필드 보고

4. **목 데이터 최신성 체크** (선택적, 장기):
   - 하드코딩된 날짜 검색
   - 30일 이상 경과 경고

결과를 `gate_results` 객체로 수집하여 Phase 1 에이전트에 컨텍스트로 전달.
```

---

## 성공 지표

- **백엔드 허위 양성 방지**: 백엔드 미제공 시 환각 이슈 0건
- **범위 확장 허위 양성 감소**: 유틸 함수에서 UI 이슈 플래그 90% 감소
- **게이트 실행 시간**: <30초 (전체 리뷰 시간의 <10%)

---

## 롤백 계획

`--skip-gates` 플래그 사용 시 Phase 0B를 완전히 건너뜁니다.

```bash
/review --skip-gates
```

---

**문서 종료** — review-orchestrate에 통합 준비 완료.
