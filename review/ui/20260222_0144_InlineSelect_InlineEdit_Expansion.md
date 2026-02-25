# InlineSelect 컴포넌트 + 인라인 편집 확장

**날짜**: 2026-02-22 01:44
**카테고리**: UI
**대상**: MA 모듈 TransactionWorkspacePage

---

## 배경

TransactionWorkspacePage의 Phase 4~5B 탭(PMI, Earnout, Risk, Compliance)에서:
- DataTable 셀 내 native `<select>` 7곳이 디자인 시스템과 불일치
- 읽기 전용으로만 표시되던 필드 7곳에 인라인 편집 기능 부재

### 기존 `<Select>` 컴포넌트를 사용할 수 없는 이유

`Select.tsx`는 `<div className="w-full">` + `<div className="relative">` 2겹 wrapper 구조.
DataTable 셀 안에서 block 컨텍스트가 되어 행 높이 증가 및 인라인 정렬 깨짐.
`className="!py-0.5"` override로도 outer div 문제는 해결 불가.

---

## 변경 사항

### 1. InlineSelect 컴포넌트 신규 생성

**파일**: `amic-platform/src/components/ui/InlineSelect.tsx`

- `inline-flex` wrapper (block 컨텍스트 없음, 셀 인라인 흐름 유지)
- `appearance-none` + `ChevronDown` 아이콘 (디자인 시스템 일관성)
- 디자인 토큰 준수: `border-gray-border`, `rounded-dr-sm`, `focus:ring-accent/30`, `focus:border-amic`
- `INLINE_INPUT_CLS` 상수도 함께 export (input 인라인 편집용 공용 스타일)

### 2. index.ts export 추가

**파일**: `amic-platform/src/components/ui/index.ts`

- `InlineSelect`, `InlineSelectProps`, `InlineSelectOption`, `INLINE_INPUT_CLS` export

### 3. native `<select>` 7곳 → InlineSelect 교체

**파일**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx`

| # | 탭 | 필드 | 변경 |
|---|---|------|------|
| 1 | PMI | `priority` | `<select className={INLINE_CLS}>` → `<InlineSelect>` |
| 2 | PMI | `status` | 동일 패턴 |
| 3 | Earnout | `status` | 동일 패턴 |
| 4 | Risk | `severity` | 동일 패턴 |
| 5 | Risk | `likelihood` | 동일 패턴 |
| 6 | Risk | `status` | 동일 패턴 |
| 7 | Compliance | `status` | 동일 패턴 |

### 4. 인라인 편집 확장 (7개 필드)

읽기 전용 텍스트 → `<input>` 인라인 편집으로 전환.

#### 텍스트 필드 (onBlur 패턴 — 포커스 아웃 시 API 호출)

| # | 탭 | 필드 | 타입 | 너비 | 훅 |
|---|---|------|------|------|-----|
| 1 | PMI | `assignee_name` | `text` | `w-28` | `updatePMITask` |
| 2 | Risk | `owner_email` | `text` | `w-36` | `updateRisk` |
| 3 | Compliance | `assignee_email` | `text` | `w-36` | `updateCompliance` |

#### 날짜 필드 (onChange 패턴 — 선택 즉시 API 호출)

| # | 탭 | 필드 | 너비 | 훅 |
|---|---|------|------|-----|
| 4 | PMI | `due_date` | `w-32` | `updatePMITask` |
| 5 | Compliance | `due_date` | `w-32` | `updateCompliance` |

#### 숫자 필드 (onBlur 패턴)

| # | 탭 | 필드 | 너비 | 훅 |
|---|---|------|------|-----|
| 6 | Earnout | `actual_value` | `w-24` | `updateEarnout` |
| 7 | Earnout | `payment_amount` | `w-24` | `updateEarnout` |

### 5. 기존 빌드 에러 수정 (부수 정리)

- KpiCard `value` prop: `number` → `String()` 래핑 (Risk/Compliance/Approvals 요약 KPI 10곳)
- Select `onChange` 핸들러: `v as Type` → `e.target.value as Type` (Risk/Compliance 모달 폼 4곳)
- 미사용 import 제거: `Clock`, `AppStatus`

---

## 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `amic-platform/src/components/ui/InlineSelect.tsx` | **신규** — DataTable 셀 전용 styled select |
| `amic-platform/src/components/ui/index.ts` | export 추가 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx` | select 교체 + 인라인 편집 + 빌드 에러 수정 |

---

## 검증

- `tsc -b`: 에러 0건
- `vite build`: 성공 (8.88s)
- `INLINE_CLS` 로컬 상수 → `INLINE_INPUT_CLS` import로 대체 (중복 제거)
- native `<select>` 잔여: 0건 확인
