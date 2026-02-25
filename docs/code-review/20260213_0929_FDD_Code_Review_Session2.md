# FDD 모듈 코드 리뷰 — 세션 2

> **리뷰 일시**: 2026-02-13 09:27
> **리뷰 범위**: FDD 프론트엔드 전체 (타입 9개, 훅 9개, 페이지 14개, 컴포넌트 6개, 라우팅 1개)
> **기존 리뷰 참조**: `docs/20260213_0833_FDD_Code_Review.md` (41개 이슈)
> **이번 리뷰**: 기존 이슈 제외, **신규 19개 이슈 + 기존 3개 정정**

---

## 0. 기존 리뷰 정정 사항 (False Positives)

### FP-1. 4.1 ReportPage "Untyped API Client" → 실제 문제 아님
- **파일**: `src/modules/fdd/pages/ReportPage.tsx:12`
- **기존 판정**: `import api from "@/api/client"` 가 "untyped"이므로 `fddApi`로 교체 필요
- **정정**: `api`는 `createApiClient("/api/fdd")`의 default export (`client.ts:88`). 다른 모든 FDD 훅(`useDeals`, `useUploads`, `useQoE` 등)과 동일한 인스턴스 사용. auth interceptor 포함. 타입 안전성은 제네릭 파라미터(`api.get<T>`)로 확보 가능하며, 현재 패턴은 프로젝트 전체 관례와 일치.

### FP-2. 4.4 NWC Hook Parameter Name Mismatch → 일치 확인
- **파일**: `src/modules/fdd/hooks/useNWC.ts:28`
- **기존 판정**: `custom_peg_value` 파라미터가 BE와 불일치 가능
- **정정**: FE `useRunNWC` body의 `custom_peg_value`와 BE `NWCRunRequest.custom_peg_value` (schemas/nwc.py:45) 완전 일치. `PegSimulationRequest`의 `custom_value`도 FE (nwc.ts:87) / BE (schemas/nwc.py:76) 양쪽 일치.

### FP-3. 5.2 NWCPage Sort Array Recreated → 이미 수정됨
- **파일**: `src/modules/fdd/pages/NWCPage.tsx:117-119`
- **기존 판정**: `[...items].sort(...)` 매 렌더 새 배열 생성
- **정정**: 현재 코드: `const sorted = useMemo(() => [...items].sort((a, b) => a.display_order - b.display_order), [items])` — `useMemo`로 래핑 완료.

---

## 1. Critical 이슈 (1개)

### C-1. DefinitionPage NWC_METHOD_OPTIONS와 BE PegMethod enum 불일치

- **파일**: `src/modules/fdd/pages/DefinitionPage.tsx:37-43`
- **심각도**: Critical
- **카테고리**: 타입불일치
- **문제**:
  - FE `NWC_METHOD_OPTIONS` 값: `6M_AVG | 12M_AVG | TTM_AVG | RECENT_3M_WEIGHTED | SEASONAL_EXCLUDED | CUSTOM`
  - BE `PegMethod` enum (`models/nwc.py:47-55`): `LTM_AVERAGE | TTM | LAST_MONTH | MAX | MIN | CUSTOM`
  - 6개 중 `CUSTOM`만 일치, 나머지 5개 전부 불일치
  - Definition의 `target_nwc.method` 값이 BE에 `dict[str, Any]`로 저장되므로 즉각 에러는 아니지만, NWC 엔진이 이 값을 PegMethod로 파싱할 때 `12M_AVG`, `TTM_AVG` 등은 매칭 실패
  - NWCPage의 `PEG_METHOD_OPTIONS` (NWCPage.tsx:33-40)는 BE와 정확히 일치하므로, 두 페이지 간 UX도 불일치

- **수정안**:
```typescript
// DefinitionPage.tsx
const NWC_METHOD_OPTIONS: SelectOption[] = [
  { value: "LTM_AVERAGE", label: "LTM Average (12M)" },
  { value: "TTM", label: "TTM" },
  { value: "LAST_MONTH", label: "Last Month" },
  { value: "MAX", label: "Maximum" },
  { value: "MIN", label: "Minimum" },
  { value: "CUSTOM", label: "Custom" },
];
```

---

## 2. Major 이슈 (9개)

### M-1. ReportVersionCard download URL이 Vite proxy 우회

- **파일**: `src/modules/fdd/components/report/ReportVersionCard.tsx:25`
- **심각도**: Major
- **카테고리**: 런타임버그
- **문제**:
  ```typescript
  const downloadUrl = `/api/v1/deals/${dealId}/reports/versions/${version.version}/download`;
  ```
  - `/api/v1/...` 직접 사용 → Vite dev server proxy 경유하지 않음
  - Vite proxy 설정: `/api/fdd` → `:8000/api/v1`
  - 개발 환경에서 이 URL은 Vite dev server에서 404 반환
  - 프로덕션에서는 nginx가 `/api/v1` 라우팅하면 동작할 수 있으나, 모듈별 prefix 누락

- **수정안**:
```typescript
const downloadUrl = `/api/fdd/deals/${dealId}/reports/versions/${version.version}/download`;
```

### M-2. usePegSimulation이 POST를 useQuery로 래핑

- **파일**: `src/modules/fdd/hooks/useNWC.ts:39-50`
- **심각도**: Major
- **카테고리**: 상태관리
- **문제**:
  ```typescript
  export function usePegSimulation(dealId: string, nwcId: string) {
    return useQuery({
      queryFn: async () => {
        const { data } = await api.post(`/deals/${dealId}/nwc/${nwcId}/peg-simulate`);
        return data;
      },
    });
  }
  ```
  - `useQuery`는 GET 시맨틱: `refetchOnWindowFocus`, `refetchOnMount`, `staleTime` 기반 자동 재요청
  - POST 요청이 window focus 때마다 재실행될 수 있음
  - 현재 빈 body로 POST → 서버 상태 변경 없는 "read-via-POST" 패턴이지만, TanStack Query 권장 패턴이 아님
  - `isPending`/`isError` 시맨틱이 mutation과 다름

- **수정안**: 두 가지 옵션
  1. BE가 GET을 지원하면 → `api.get()`으로 변경 (가장 깔끔)
  2. POST 유지 필요 시 → `useMutation` + `useEffect`로 자동 실행, 또는 `refetchOnWindowFocus: false` 추가

### M-3. useFinalizeReportVersion 빈 body로 PUT 요청

- **파일**: `src/modules/fdd/hooks/useReportVersions.ts:35-36`
- **심각도**: Major
- **카테고리**: 타입불일치
- **문제**:
  ```typescript
  mutationFn: async (version: number) => {
    const { data } = await api.put(`/deals/${dealId}/reports/versions/${version}/finalize`);
    // body 없음!
  }
  ```
  - BE endpoint (`reports.py:329-334`): `body: ReportVersionFinalize` 파라미터 필수
  - `ReportVersionFinalize` schema: `{ notes: str | None = None }`
  - Pydantic v2는 optional-only body에 대해 빈 body를 허용할 수 있으나, Content-Type header 불일치 시 422 반환 가능
  - `notes` 입력 기회가 사용자에게 제공되지 않음

- **수정안**:
```typescript
mutationFn: async ({ version, notes }: { version: number; notes?: string }) => {
  const { data } = await api.put(
    `/deals/${dealId}/reports/versions/${version}/finalize`,
    { notes: notes ?? null }
  );
  return data as ReportVersion;
},
```

### M-4. DefinitionPage approved_by "system" 하드코딩

- **파일**: `src/modules/fdd/pages/DefinitionPage.tsx:385-387`
- **심각도**: Major
- **카테고리**: 런타임버그
- **문제**:
  ```typescript
  const { data } = await api.put(
    `/deals/${dealId}/definitions/${version}/approve`,
    { approved_by: "system" }  // ← 하드코딩
  );
  ```
  - 모든 정의 승인이 "system"으로 기록 → 감사 추적(audit trail) 무의미
  - BE는 `approved_by` 값을 그대로 DB에 저장 (`approved_by: str`)
  - DefinitionCard에서 `definition.approved_by` 표시하지만 항상 "system"

- **수정안**:
```typescript
// useAuth에서 현재 사용자 정보 가져오기
const { user } = useAuth();
// ...
{ approved_by: user?.email ?? "system" }
```

### M-5. ReportPage DOCX 포맷 옵션 누락

- **파일**: `src/modules/fdd/pages/ReportPage.tsx:216-271`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**:
  - Format 선택 UI에 `pptx`와 `json` 라디오 버튼만 존재
  - BE는 `docx` 포맷 완전 지원 (`reports.py:67-78`): Word 문서 생성 + 다운로드
  - 또한 `generateMutation` (lines 73-94)에서 blob 다운로드 로직이 PPTX MIME만 처리:
    ```typescript
    const blob = new Blob([response.data], {
      type: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    });
    ```
  - DOCX 추가 시 MIME type 분기 필요

- **수정안**: DOCX 라디오 버튼 추가 + blob MIME type을 format에 따라 동적 설정

### M-6. NWCPage sectionHeaders 인덱스 계산 오류

- **파일**: `src/modules/fdd/pages/NWCPage.tsx:158-175`
- **심각도**: Major
- **카테고리**: 런타임버그
- **문제**:
  ```typescript
  const sorted = useMemo(
    () => [...items].sort((a, b) => a.display_order - b.display_order),
    [items],
  );
  // ...
  const aboveLine = sorted.filter((i) => i.classification === "ABOVE_LINE");
  const belowLine = sorted.filter((i) => i.classification === "BELOW_LINE");
  const excluded = sorted.filter((i) => i.classification === "EXCLUDED");
  // ...
  sectionHeaders={[
    { index: 0, label: `Above the Line (${aboveLine.length})` },
    { index: aboveLine.length, label: `Below the Line (${belowLine.length})` },
    { index: aboveLine.length + belowLine.length, label: `Excluded (${excluded.length})` },
  ]}
  ```
  - `sorted`는 `display_order`로 정렬 → ABOVE_LINE, BELOW_LINE, EXCLUDED 항목이 **섞여있을 수 있음**
  - sectionHeaders의 index는 0, N, N+M으로 연속 구간을 가정
  - 실제 데이터에서 `display_order`가 classification과 무관하면, section header가 잘못된 행에 표시됨

- **수정안**: classification으로 1차 정렬 후 display_order로 2차 정렬:
```typescript
const sorted = useMemo(
  () => [...items].sort((a, b) => {
    const classOrder = { ABOVE_LINE: 0, BELOW_LINE: 1, EXCLUDED: 2 };
    const classCompare = (classOrder[a.classification] ?? 99) - (classOrder[b.classification] ?? 99);
    return classCompare !== 0 ? classCompare : a.display_order - b.display_order;
  }),
  [items],
);
```

### M-7. NWCPage/QoEPage/NetDebtPage currency "KRW" 하드코딩

- **파일**: `src/modules/fdd/pages/NWCPage.tsx` (전체), `QoEPage.tsx`, `NetDebtPage.tsx`
- **심각도**: Major
- **카테고리**: 런타임버그
- **문제**:
  ```typescript
  formatAmount(nwc.total_current_assets, "KRW")  // NWCPage.tsx:63
  formatAmount(nwc.peg_target, "KRW")             // NWCPage.tsx:88
  // 동일 패턴이 QoEPage, NetDebtPage에도 반복
  ```
  - Deal 모델은 `base_currency: string` 필드를 가지며 `KRW | USD | EUR | JPY` 지원 (constants.ts)
  - USD/EUR/JPY 딜에서도 모든 금액이 ₩ 포맷으로 표시됨
  - 각 페이지에서 Deal 정보를 이미 로드하거나 부모(DealWorkspacePage)에서 전달 가능

- **수정안**: DealWorkspacePage에서 `deal.base_currency`를 context 또는 prop으로 전달:
```typescript
// NWCPage에서
const { deal } = useDealContext(); // 또는 useOutletContext
formatAmount(nwc.total_current_assets, deal.base_currency)
```

### M-8. useSuggestMappings onSuccess 잘못된 쿼리 키 무효화

- **파일**: `src/modules/fdd/hooks/useMapping.ts:31-33`
- **심각도**: Major
- **카테고리**: 상태관리
- **문제**:
  ```typescript
  export function useSuggestMappings(dealId: string) {
    return useMutation({
      mutationFn: async () => {
        const { data } = await api.post(`/deals/${dealId}/mappings/suggest`);
        return data as MappingSuggestion[];
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["mappings", dealId] });
      },
    });
  }
  ```
  - `suggest` 엔드포인트는 **제안 결과를 반환**할 뿐 DB에 매핑을 저장하지 않음
  - `["mappings", dealId]` 쿼리를 무효화해도 기존 매핑 목록에 변화 없음 → 불필요한 네트워크 요청
  - 제안 결과는 mutation의 return value (`data`)로만 접근 가능 → UI에서 `suggestMutation.data`로 표시해야 함
  - 실제 매핑 저장은 `useSaveMappings`에서 수행

- **수정안**: `onSuccess`에서 불필요한 invalidation 제거:
```typescript
onSuccess: () => {
  // 제안 결과는 mutation.data로 접근 — 별도 캐시 무효화 불필요
},
```

### M-9. approve 뮤테이션에서 실제 사용자 ID 미사용 (패턴 이슈)

- **파일**: 다수 (DefinitionPage, MappingPage, QoEPage, NetDebtPage)
- **심각도**: Major
- **카테고리**: 런타임버그
- **문제**:
  - DefinitionPage: `{ approved_by: "system" }` (M-4와 동일)
  - MappingPage의 `useApproveMapping`, `useApproveAllMappings`: 호출부에서 `approved_by` 전달 필요
  - QoEPage의 `useApproveAdjustment`: 호출부에서 `approved_by` 전달 필요
  - NetDebtPage의 `useApproveDebtItem`: 호출부에서 `approved_by` 전달 필요
  - 각 페이지에서 `approved_by` 값을 어디서 가져오는지 일관성 없음
  - `useAuth().user.email` 등 통일된 패턴 필요

- **수정안**: 공통 `useCurrentUserEmail()` 훅 생성 또는 `useAuth`에서 직접 참조:
```typescript
// 각 페이지에서
const { user } = useAuth();
// approve 호출 시
{ approved_by: user?.email ?? "system" }
```

---

## 3. Minor 이슈 (9개)

### m-1. DefinitionPage useQuery에 enabled 가드 누락

- **파일**: `src/modules/fdd/pages/DefinitionPage.tsx:357-363`
- **심각도**: Minor
- **카테고리**: 런타임버그
- **문제**:
  ```typescript
  const { data: definitions, isLoading } = useQuery<DealDefinition[]>({
    queryKey: ["definitions", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/definitions`);
      return data;
    },
    // enabled 누락!
  });
  ```
  - `dealId`는 `useParams()`에서 가져오며 초기 렌더 시 `undefined`일 수 있음
  - API 호출: `/deals/undefined/definitions` → BE에서 UUID 파싱 실패 → 422 에러
  - 다른 모든 FDD 훅은 `enabled: !!dealId` 패턴 사용

- **수정안**: `enabled: !!dealId` 추가

### m-2. NWCPage useUpdateNWCLineItem에 빈 nwcId 전달

- **파일**: `src/modules/fdd/pages/NWCPage.tsx:380`
- **심각도**: Minor
- **카테고리**: 런타임버그
- **문제**:
  ```typescript
  const updateItemMutation = useUpdateNWCLineItem(dealId!, latestNWC?.id ?? "");
  ```
  - `latestNWC`가 null이면 `nwcId = ""`
  - 훅 내부: `api.put(/deals/${dealId}/nwc/${""}/items/${itemId})` → 잘못된 URL 구성
  - 실제로 `latestNWC`가 null이면 UI에서 mutation 호출 불가능하므로 런타임 에러는 발생하지 않지만, 방어 코딩 부족

- **수정안**: `latestNWC` 존재 시에만 훅 사용하도록 조건부 렌더링 또는 guard

### m-3. ReportVersionCard에서 `<a>` 안에 `<Button>` 중첩

- **파일**: `src/modules/fdd/components/report/ReportVersionCard.tsx:47-55`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**:
  ```tsx
  <a href={downloadUrl} target="_blank" rel="noopener noreferrer">
    <Button variant="ghost" size="sm" icon={Download}>
      Download
    </Button>
  </a>
  ```
  - `<a>` 안에 `<button>` (Button 컴포넌트 내부)은 유효하지 않은 HTML 중첩
  - 스크린 리더가 이중 인터랙티브 요소로 혼동
  - 일부 브라우저에서 예측 불가 동작

- **수정안**: `<a>` 스타일링을 Button과 동일하게 하거나, `Button`에 `as="a"` prop 지원 추가

### m-4. DefinitionPage 에러 상태 미처리

- **파일**: `src/modules/fdd/pages/DefinitionPage.tsx:440-462`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**:
  - `useQuery`의 `isError` / `error` 상태를 처리하지 않음
  - API 실패 시 `isLoading=false`, `definitions=undefined` → 빈 목록으로 표시
  - 사용자는 에러 발생을 인지할 수 없음

- **수정안**: `isError` 상태 추가:
```tsx
if (isError) {
  return <div className="text-negative">정의 목록을 불러오는 데 실패했습니다.</div>;
}
```

### m-5. DefinitionPage에서 debt_like/cash_like 항목 추가 UI 없음

- **파일**: `src/modules/fdd/pages/DefinitionPage.tsx:27-34`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**:
  - `DEFAULT_DEFINITION`의 `debt_like`과 `cash_like`는 빈 배열 `[]`
  - BE 스키마: `list[dict[str, Any]]` — `{item, category, rationale}` 구조
  - DefinitionForm에는 `debt_like`/`cash_like` 항목을 추가/편집하는 UI가 전혀 없음
  - 사용자가 Debt-like/Cash-like 항목을 정의할 수 없음

- **수정안**: debt_like/cash_like 섹션에 동적 폼 추가 (item + category + rationale 필드)

### m-6. NWCPage Snapshot ID 수동 텍스트 입력

- **파일**: `src/modules/fdd/pages/NWCPage.tsx:424-428`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**:
  ```tsx
  <Input
    placeholder="Snapshot ID"
    value={snapshotId}
    onChange={(e) => setSnapshotId(e.target.value)}
    className="w-72"
  />
  ```
  - 사용자가 UUID를 직접 입력해야 함 → 실수 가능성 높음
  - Deal의 snapshots 목록을 조회하여 Select 드롭다운으로 제공해야 함
  - `DealSnapshot` 타입과 snapshots API (`GET /deals/{dealId}/snapshots`)가 이미 존재

- **수정안**: `useQuery`로 snapshots 목록 로드 → `Select` 컴포넌트로 변경

### m-7. QoEPage/NetDebtPage에도 m-6, M-7 동일 이슈

- **파일**: `src/modules/fdd/pages/QoEPage.tsx`, `src/modules/fdd/pages/NetDebtPage.tsx`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**:
  - Snapshot ID 수동 텍스트 입력 (m-6과 동일)
  - Currency "KRW" 하드코딩 (M-7과 동일)
  - 세 페이지 모두 동일한 패턴으로 반복

- **수정안**: m-6, M-7 수정을 QoEPage, NetDebtPage에도 동일 적용

### m-8. monthly_trend FE 타입 vs BE 타입 불일치

- **파일**: `src/modules/fdd/types/nwc.ts:48` vs `Auto FDD/backend/app/schemas/nwc.py:58`
- **심각도**: Minor
- **카테고리**: 타입불일치
- **문제**:
  - FE: `monthly_trend: Record<string, MonthlyTrendEntry>` — 타입 구조: `{ current_assets: string; current_liabilities: string; nwc: string }`
  - BE: `monthly_trend: dict` — 타입 힌트 없음 (Pydantic `dict` = `dict[str, Any]`)
  - BE가 반환하는 실제 구조가 FE `MonthlyTrendEntry`와 일치하지 않을 수 있음
  - BE 스키마에 정확한 타입 힌트가 없어 런타임에서만 확인 가능

- **수정안**: BE 스키마에 타입 힌트 추가:
```python
monthly_trend: dict[str, dict[str, Decimal]]  # {month: {current_assets, current_liabilities, nwc}}
```

### m-9. NWCPage "text-positive" Tailwind 클래스 확인 필요

- **파일**: `src/modules/fdd/pages/NWCPage.tsx:93`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**:
  ```tsx
  <span className={`font-mono font-medium tabular-nums ${delta >= 0 ? "text-positive" : "text-negative"}`}>
  ```
  - `text-positive`와 `text-negative`는 Tailwind 기본 클래스가 아닌 커스텀 클래스
  - `tailwind.config.ts`에서 이 클래스가 정의되어 있는지 확인 필요
  - 미정의 시 색상 미적용 → 기본 텍스트 색으로 표시

- **수정안**: `tailwind.config.ts`에서 `text-positive` / `text-negative` 정의 확인 및 필요시 추가

---

## 4. 이슈 요약 테이블

| 카테고리 | Critical | Major | Minor | 합계 |
|---------|----------|-------|-------|------|
| 타입불일치 | 1 | 2 | 1 | **4** |
| 런타임버그 | 0 | 4 | 2 | **6** |
| 상태관리 | 0 | 2 | 0 | **2** |
| UX결함 | 0 | 1 | 6 | **7** |
| **합계** | **1** | **9** | **9** | **19** |

---

## 5. 권장 수정 우선순위

### P0 — 즉시 수정 (기능 오류)
1. **C-1**: DefinitionPage NWC method 값 BE와 일치시키기
2. **M-1**: ReportVersionCard download URL → `/api/fdd/...` 변경
3. **M-6**: NWCPage sectionHeaders 정렬 로직 수정

### P1 — 이번 스프린트
4. **M-2**: usePegSimulation POST-in-useQuery 패턴 수정
5. **M-3**: useFinalizeReportVersion body 추가
6. **M-4/M-9**: approved_by 실제 사용자 ID 사용 (패턴 통합)
7. **M-7**: currency 하드코딩 → deal.base_currency 참조
8. **M-8**: useSuggestMappings 불필요한 invalidation 제거

### P2 — 다음 스프린트
9. **M-5**: ReportPage DOCX 옵션 추가
10. **m-1**: DefinitionPage `enabled` 가드 추가
11. **m-3**: `<a>` + `<Button>` 중첩 해소
12. **m-4**: DefinitionPage 에러 상태 처리
13. **m-5**: debt_like/cash_like UI 추가

### P3 — 백로그
14. **m-2**: useUpdateNWCLineItem 빈 nwcId 방어
15. **m-6/m-7**: Snapshot Select 드롭다운 (3페이지)
16. **m-8**: BE monthly_trend 타입 명시
17. **m-9**: Tailwind 커스텀 클래스 확인

---

## 6. 검증 방법

1. **C-1**: DefinitionPage에서 NWC method 선택 → NWCPage에서 동일 값 확인
2. **M-1**: 개발 환경에서 ReportVersionCard 다운로드 클릭 → 404 아닌 파일 다운로드 확인
3. **M-6**: NWC 계산 결과에서 classification이 혼합된 데이터로 sectionHeaders 정확성 확인
4. **M-7**: USD 딜 생성 → QoE/NWC/Debt 페이지에서 $ 포맷 표시 확인
5. **전체**: `npm run build` TypeScript 컴파일 에러 없음 확인
6. **전체**: `npm run test` 기존 73개 테스트 통과 확인
