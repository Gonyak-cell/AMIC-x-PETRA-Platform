# FDD Module Code Review — Session 3

> **Date**: 2026-02-13 12:28
> **Scope**: Session 2 수정사항 검증 + 추가 리뷰 + Batch 1-3 수정 완료

---

## Part 1: Session 2 이슈 검증 결과

### CONFIRMED FIXED (10개)

| ID | Issue | Evidence |
|----|-------|----------|
| **M-7** | KRW 하드코딩 (4 pages) | 4개 페이지 모두 `deal?.base_currency ?? "KRW"` + `currency` prop 전달 확인 |
| **C-1** | NWC_METHOD_OPTIONS ↔ BE PegMethod 불일치 | DefinitionPage:37-44 = NWCPage PEG_METHOD_OPTIONS 동일 |
| **M-1** | ReportVersionCard download URL | `/api/fdd/deals/...` 사용 확인 |
| **M-3** | useFinalizeReportVersion notes 누락 | `{ version, notes?: string }` 확인 |
| **M-5** | ReportPage DOCX format 누락 | DOCX radio + blob download 구현 확인 |
| **M-8** | useSuggestMappings 불필요한 invalidation | 애초에 onSuccess 없음 — **False Positive** |
| **m-1** | DefinitionPage useQuery enabled 가드 | `enabled: !!dealId` 확인 |
| **m-3** | ReportVersionCard `<a>` contains `<Button>` | `Button` + `window.open()` 변경 확인 |
| **m-4** | DefinitionPage error state 없음 | `isError` 핸들러 추가 확인 |
| **m-9** | `text-positive`/`text-negative` 미정의 | tailwind.config에 `positive`/`negative` 색상 정의됨 — **False Positive** |

### Session 3에서 수정 완료 (이번 세션)

| ID | Issue | Fix |
|----|-------|-----|
| **M-4/M-9** | `approved_by` fallback 불일치 | 5개 페이지 모두 `"unknown"` 통일 |
| **N-1** | FDD query key 모듈 접두사 없음 | 9개 hook + 1개 테스트 → `["fdd", ...]` 접두사 추가 |
| **N-2** | approve mapping → tie-out 캐시 미invalidate | `useApproveMapping`/`useApproveAllMappings`에 tie-out invalidation 추가 |
| **N-3** | `useStandardLineItems` staleTime 없음 | `staleTime: 60 * 60 * 1000` (1시간) 추가 |
| **N-4** | DefinitionPage inline 쿼리 | `useDefinitions.ts` 추출 (3개 hook) |
| **N-5** | IssuesPage `resolved_by` 하드코딩 | `useAuth` import + `user?.email ?? "unknown"` 적용 |
| **N-6** | 빈 ID 가드 없음 | QoEPage/NWCPage/NetDebtPage 핸들러에 early return 추가 |
| **N-7** | Error 메시지 한/영 혼재 | 3개 파일 → 영어 통일 |
| **N-8** | formatAmount JPY 소수점 미처리 | `ZERO_DECIMAL_CURRENCIES` Set 도입 (KRW, JPY, VND, IDR, HUF) |
| **M-2** (partial) | `usePegSimulation` POST in useQuery | 의도적 사용 코멘트 추가 |

---

## Part 2: 수정된 파일 목록 (17개)

| # | File | Changes |
|---|------|---------|
| 1 | `src/modules/fdd/pages/DefinitionPage.tsx` | fallback→"unknown", 에러 영어화, queryKey 접두사, hook 분리 |
| 2 | `src/modules/fdd/pages/QoEPage.tsx` | fallback→"unknown", ID 가드 |
| 3 | `src/modules/fdd/pages/NetDebtPage.tsx` | fallback→"unknown", 에러 영어화, ID 가드 3곳 |
| 4 | `src/modules/fdd/pages/NWCPage.tsx` | 에러 영어화, classOrder 상수화, ID 가드 |
| 5 | `src/modules/fdd/pages/MappingPage.tsx` | fallback→"unknown" (2곳) |
| 6 | `src/modules/fdd/pages/IssuesPage.tsx` | useAuth 추가, resolved_by 2곳 수정 |
| 7 | `src/modules/fdd/hooks/useDeals.ts` | queryKey `["fdd", "deals"]` + optimistic update 키 수정 |
| 8 | `src/modules/fdd/hooks/useQoE.ts` | queryKey `["fdd", "qoe"]` |
| 9 | `src/modules/fdd/hooks/useNWC.ts` | queryKey `["fdd", "nwc"]` + POST 코멘트 |
| 10 | `src/modules/fdd/hooks/useDebt.ts` | queryKey `["fdd", "debt"]` |
| 11 | `src/modules/fdd/hooks/useMapping.ts` | queryKey 3종 접두사 + tie-out invalidation + staleTime |
| 12 | `src/modules/fdd/hooks/useIssues.ts` | queryKey `["fdd", "issues"]` |
| 13 | `src/modules/fdd/hooks/useUploads.ts` | queryKey `["fdd", "uploads"]` |
| 14 | `src/modules/fdd/hooks/useReportVersions.ts` | queryKey `["fdd", "report-versions"]` |
| 15 | `src/modules/fdd/hooks/useVdr.ts` | queryKey `["fdd", "vdr-status"]` |
| 16 | `src/modules/fdd/hooks/useDefinitions.ts` | **NEW** — DefinitionPage에서 추출 |
| 17 | `src/lib/format.ts` | `ZERO_DECIMAL_CURRENCIES` Set + `isZeroDecimal()` 함수 |
| 18 | `src/modules/fdd/hooks/__tests__/useDeals.test.tsx` | queryKey 업데이트 |

---

## Part 3: 검증 결과

| Check | Result |
|-------|--------|
| TypeScript (`tsc --noEmit`) | ✅ 0 errors |
| FDD Unit Tests (10 tests) | ✅ All passed |
| Vite Build | ✅ Built in 4.18s |

---

## Part 4: Deferred Issues (BE 협의 필요)

| ID | Issue | Reason |
|----|-------|--------|
| **m-5** | debt_like/cash_like UI | BE 스키마 비정형 — 확정 후 구현 |
| **m-6/m-7** | Snapshot Select 드롭다운 | BE API 필요 (snapshot 목록 조회) |
| **m-2** | `useUpdateNWCLineItem` 빈 nwcId | `latestNWC?.id ?? ""` — BE API 선행 |
