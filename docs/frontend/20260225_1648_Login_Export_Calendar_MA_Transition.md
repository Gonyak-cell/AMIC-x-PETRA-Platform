# Session 38 — 로그인 동작 수정 + Export/Calendar MA 전환

> 작성: 2026-02-25 16:48 | 검증 완료: tsc + vite build PASS, 코드 리뷰 ALL CORRECT

---

## 1. 작업 개요

| 작업 | 변경 파일 수 | 상태 |
|------|------------|------|
| 로그인 리다이렉트 수정 (항상 대시보드) | 2 | ✅ 완료 |
| 세션 쿠키 전환 (브라우저 종료 시 로그아웃) | 3 | ✅ 완료 |
| Export Hub — MA 모듈 추가 | 3 | ✅ 완료 |
| Calendar — MA Pipeline 전용 전환 | 6 | ✅ 완료 |
| **총 변경 파일** | **14** | |

---

## 2. Task 1: 로그인 리다이렉트 수정

### 문제
- 로그아웃 후 재로그인 시 이전 방문 페이지로 리다이렉트됨
- `ProtectedRoute`가 `state={{ from: location }}`으로 이전 위치를 전달하고, `LoginPage`가 이를 받아 리다이렉트

### 수정 내용

**`amic-platform/src/pages/LoginPage.tsx`**
- `useLocation` import 제거
- `from` 변수 (이전 페이지 경로) 추출 로직 제거
- `navigate(from, ...)` → `navigate("/", { replace: true })`
- `<Navigate to={from} replace />` → `<Navigate to="/" replace />`

**`amic-platform/src/components/auth/ProtectedRoute.tsx`**
- `useLocation` import 제거
- `const location = useLocation()` 제거
- `<Navigate to="/login" replace state={{ from: location }} />` → `<Navigate to="/login" replace />`

### 동작 확인
- 로그인 성공 → 항상 `/` (대시보드)로 이동
- 인증되지 않은 상태에서 보호 라우트 접근 → `/login`으로 리다이렉트 (이전 위치 전달 없음)

---

## 3. Task 2: 세션 쿠키 전환

### 문제
- `set_cookie(max_age=...)` 설정으로 쿠키가 브라우저 종료 후에도 유지됨
- FDD: `max_age=settings.access_token_expire_minutes * 60` / `max_age=settings.refresh_token_expire_days * 86400`
- KIIS: `max_age=15*60` / `max_age=7*24*60*60`
- IM: `max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES*60` / `max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS*86400`

### 수정 내용

3개 백엔드의 `login`과 `refresh` 엔드포인트에서 `max_age` 파라미터 제거:

| 파일 | set_cookie 호출 수 |
|------|-------------------|
| `fdd/backend/app/api/auth.py` | 4개 (login 2 + refresh 2) |
| `kiis/app/routers/auth.py` | 4개 (login 2 + refresh 2) |
| `im/src/api/routes/auth.py` | 4개 (login 2 + refresh 2) |

### 동작 확인
- `max_age` 제거 → 세션 쿠키로 전환 (브라우저 종료 시 자동 삭제)
- `httponly=True`, `secure`, `samesite="lax"` 보안 설정은 유지

---

## 4. Task 3: Export Hub — MA 모듈 추가

### 문제
- Export Hub에 FDD, KIIS, IM 3개 모듈만 표시
- MA Pipeline 모듈 누락

### 수정 내용

**`amic-platform/src/types/export.ts`**
```typescript
// Before
export type ExportModule = "fdd" | "kiis" | "im";
// After
export type ExportModule = "fdd" | "kiis" | "im" | "ma";
```

**`amic-platform/src/components/exports/ExportFilterBar.tsx`**
```typescript
// MODULE_OPTIONS에 추가
{ value: "ma", label: "M&A" },
```

**`amic-platform/src/pages/exports/ExportsPage.tsx`**
- subtitle: `"Unified export history across FDD, KIIS, IM, and M&A modules"`
- EmptyState description: `"Exports from FDD reports, KIIS research, IM documents, and M&A deal materials will appear here."`

---

## 5. Task 4: Calendar — MA Pipeline 전용 전환

### 문제
- Calendar가 FDD/KIIS/IM 기준으로 하드코딩됨 (3개 병렬 쿼리, 모듈별 토글/색상/범례)
- MA Pipeline 전환 후 사용하지 않는 데이터 소스에 의존

### 설계 결정
- MA 트랜잭션 단일 쿼리로 교체 (`maApi.get("/transactions")`)
- 7단계 워크플로우 기반 진행률 계산: `Math.round((phase_order / 7) * 100)`
- 이벤트 3종: 거래 생성일 / 목표 종결일 / 현재 단계 표시
- 모듈 토글 제거 (MA 단일이므로 불필요)

### 수정 파일 및 변경 내용

**`amic-platform/src/types/calendar.ts`** — 전면 교체
| 항목 | Before | After |
|------|--------|-------|
| CalendarEventModule | `"fdd" \| "kiis" \| "im"` | `"ma"` |
| CalendarEventType | `"deadline" \| "filing" \| "...` 등 | `"transaction_created" \| "target_close" \| "phase_current"` |
| CalendarFilter | `{ month, year, modules }` | `{ month, year }` |

**`amic-platform/src/hooks/useCalendar.ts`** — 전면 교체
- FDD/KIIS/IM 3개 `useQueries` 병렬 쿼리 → MA `useQuery` 단일 쿼리
- `CalendarErrors`: `{ fdd, kiis, im }` → `{ ma }`
- 이벤트 매핑:
  - `txn.created_at` → `transaction_created` (거래 생성)
  - `txn.target_close_date` → `target_close` (목표 종결일)
  - `txn.phase` → `phase_current` (현재 단계)
- Gantt 매핑:
  - `startDate` = `created_at`, `endDate` = `target_close_date ?? today`
  - `progress` = `phase_order / 7 * 100`
- 재사용한 기존 코드:
  - `PHASE_CONFIG` (from `@/modules/ma/constants`)
  - `Transaction` type (from `@/modules/ma/types/transaction`)
  - `maApi` (from `@/api/maClient`)
  - `toArray`, `safeStr` (from `@/api/safe-parse`)

**`amic-platform/src/components/calendar/CalendarGrid.tsx`**
```typescript
const MODULE_COLORS = { ma: "bg-amber-500" };
const MODULE_BADGE = { ma: "warning" };
```

**`amic-platform/src/components/calendar/GanttTimeline.tsx`**
```typescript
const MODULE_BAR_COLORS = { ma: "bg-amber-400" };
const MODULE_BADGE = { ma: "warning" };
```

**`amic-platform/src/components/calendar/CalendarFilterBar.tsx`**
- `MODULES` 배열 및 모듈 토글 버튼 전체 삭제
- Props에서 `modules`, `onToggleModule` 제거

**`amic-platform/src/pages/calendar/CalendarPage.tsx`**
- `modules` 상태 변수 제거
- `filter`에서 `modules` 제거: `{ month, year }`
- 에러 배너: `errors.ma` 단일 ("M&A Pipeline 서비스에 연결할 수 없습니다")
- 범례: MA Transaction 단일 (`bg-amber-500`)
- subtitle: `"M&A Pipeline milestones and transaction progress"`

---

## 6. 코드 리뷰 결과

### 리뷰 방법
2개 Explore 에이전트 병렬 실행:
- Agent 1: 로그인/인증 변경 (5개 파일) 검증
- Agent 2: Calendar/Export 변경 (10개+ 파일) 검증

### 결과 요약

| 검증 항목 | 결과 |
|----------|------|
| 타입 정합성 | ✅ CalendarEventModule/CalendarEventType 일관성 확인 |
| import 정리 | ✅ 사용하지 않는 import 제거 확인 |
| 기존 시스템 연동 | ✅ maApi, PHASE_CONFIG, Transaction 타입 정상 참조 |
| 프론트-백 인터페이스 | ✅ cookie 설정 3개 백엔드 일관성 확인 |
| ICS 내보내기 호환성 | ✅ CalendarEvent 필드(id, title, date, module, type) 동일 |
| 빌드 검증 | ✅ tsc --noEmit + vite build 성공 |
| 허위 리뷰 검증 | ✅ 0건 — 모든 리뷰 항목이 실제 코드와 일치 |
| 수정 필요 사항 | 없음 |

---

## 7. 검증 방법

```bash
# TypeScript 타입 체크
cd amic-platform && npx tsc --noEmit

# 프로덕션 빌드
npx vite build

# 브라우저 검증 (수동)
# 1. 로그인 → 항상 대시보드 랜딩 확인
# 2. 브라우저 종료 후 재접속 → 로그인 필요 확인
# 3. Calendar 페이지 → MA 트랜잭션 이벤트 표시 확인
# 4. Calendar Gantt 뷰 → MA 프로젝트 바 표시 확인
# 5. Export Hub → 필터에 M&A 옵션 표시 확인
```
