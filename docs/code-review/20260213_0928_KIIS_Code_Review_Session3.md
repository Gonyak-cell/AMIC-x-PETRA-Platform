# KIIS 모듈 코드 리뷰 — Session 3

> 리뷰 일시: 2026-02-13 09:26
> 범위: 프론트엔드 전체 (18 pages, 14 hooks, 8 components, 14 types) + 백엔드 API 정합성
> 기준: `docs/20260213_0836_KIIS_Code_Review.md` 기존 28건 이슈 제외, **새 이슈만** 보고

---

## 요약

| 심각도 | 건수 |
|--------|------|
| Major  | 9    |
| Minor  | 6    |
| **합계** | **15** |

---

## Major 이슈 (9건)

### 1. useFundManagers 쿼리키가 useManagers 네임스페이스와 충돌

- **파일**: `src/modules/kiis/hooks/useFunds.ts:44`
- **심각도**: Major
- **카테고리**: 상태관리
- **문제**: `useFundManagers`의 쿼리키가 `["kiis", "managers", params]`로 설정되어 있음. `useTrackManagers`(`useManagers.ts:61`)가 `["kiis", "managers"]`를 무효화하면 펀드매니저 캐시까지 불필요하게 무효화됨. 두 훅이 서로 다른 API(`/kofia/managers` vs `/managers/track`)를 호출하지만 동일 쿼리키 prefix를 공유.
- **수정안**:
```typescript
// useFunds.ts:44 — 쿼리키를 "fund-managers"로 분리
export function useFundManagers(params = {}) {
  return useQuery<FundManagerItem[]>({
    queryKey: ["kiis", "fund-managers", params],  // "managers" → "fund-managers"
    // ...
  });
}
```

---

### 2. DealSourcingPage가 비활성 탭 데이터도 동시 fetch

- **파일**: `src/modules/kiis/pages/DealSourcingPage.tsx:75-83`
- **심각도**: Major
- **카테고리**: 런타임버그
- **문제**: `useDealTrends`, `useDealsBySector`, `useDealsByStage` 3개 쿼리가 탭 선택 상태와 무관하게 모두 마운트 시 실행. 사용자가 "Trends" 탭만 보고 있어도 나머지 2개 API 호출 발생.
- **수정안**:
```typescript
// DealSourcingPage.tsx — 각 useQuery에 enabled 조건 추가
const { data: trends, isLoading: trendsLoading } = useDealTrends({
  years: Number(years),
  enabled: tab === "trends",     // ← 추가
});
const { data: sectors, isLoading: sectorsLoading } = useDealsBySector({
  years: Number(years),
  enabled: tab === "sector",     // ← 추가
});
const { data: stages, isLoading: stagesLoading } = useDealsByStage({
  years: Number(years),
  enabled: tab === "stage",      // ← 추가
});
```
> 참고: 훅 시그니처에 `enabled` 옵션이 없으면 훅 내부 useQuery 옵션에 `enabled` 파라미터를 추가해야 함.

---

### 3. PortfolioPage — Check 버튼 로딩이 모든 행에 동시 표시

- **파일**: `src/modules/kiis/pages/PortfolioPage.tsx:170`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: `loading={checkSurvival.isPending}`이 모든 행의 Check 버튼에 적용됨. 한 기업의 survival check를 실행하면 테이블 전체의 Check 버튼이 로딩 상태로 전환.
- **수정안**:
```typescript
// PortfolioPage.tsx — 현재 체크 중인 portfolioId를 추적
const [checkingId, setCheckingId] = useState<number | null>(null);

const handleCheckSurvival = (item: PortfolioItem) => {
  setCheckingId(item.id);
  checkSurvival.mutate(item.id, {
    onSuccess: (res) => {
      toast.success(`${item.target_company_name}: ${res.previous_status} → ${res.new_status}`);
      setCheckingId(null);
    },
    onError: () => {
      toast.error("Survival check failed");
      setCheckingId(null);
    },
  });
};

// columns render에서:
loading={checkingId === row.id}  // checkSurvival.isPending → 특정 ID만
```

---

### 4. EntityResolutionPage — Delete 버튼 로딩이 모든 행에 동시 표시

- **파일**: `src/modules/kiis/pages/EntityResolutionPage.tsx:148`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: `loading={deleteAlias.isPending}`이 모든 행의 Delete 버튼에 적용됨. 이슈 #3과 동일한 패턴.
- **수정안**:
```typescript
// EntityResolutionPage.tsx — 삭제 중인 aliasId 추적
const [deletingId, setDeletingId] = useState<number | null>(null);

const handleDeleteAlias = (aliasId: number) => {
  setDeletingId(aliasId);
  deleteAlias.mutate(aliasId, {
    onSuccess: () => { toast.success("Alias deleted"); setDeletingId(null); },
    onError: () => { toast.error("Failed to delete alias"); setDeletingId(null); },
  });
};

// aliasColumns render에서:
loading={deletingId === row.id}  // deleteAlias.isPending → 특정 ID만
```

---

### 5. SanctionListPage — 페이지네이션 미구현

- **파일**: `src/modules/kiis/pages/SanctionListPage.tsx`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: `useClassifiedSanctions(corpCode)`를 호출할 때 `page`/`size` 파라미터를 전달하지 않음. 백엔드 기본값(page=1, size=20)만 적용되어 20건 초과 시 나머지 데이터에 접근 불가. 다른 리스트 페이지(FundListPage, ManagerListPage 등)는 `Pagination` 컴포넌트 사용 중.
- **수정안**:
```typescript
// SanctionListPage.tsx — 페이지 상태 + Pagination 추가
const [page, setPage] = useState(1);

const { data: sanctions, isLoading } = useClassifiedSanctions(corpCode, {
  page,
  size: 20,
});
// useClassifiedSanctions가 items만 반환하므로 전체 응답(total 포함)을 반환하도록 훅 수정 필요
// 또는 별도로 ClassifiedSanctionListResponse를 반환하도록 변경

// JSX 하단에:
<Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
```

---

### 6. WatchlistPage — 알림 이력 페이지네이션 미구현

- **파일**: `src/modules/kiis/pages/WatchlistPage.tsx:27`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: `useAlerts()`를 파라미터 없이 호출. 백엔드 기본값(page=1, size=20)만 적용. 알림이 20건을 초과하면 과거 알림에 접근 불가.
- **수정안**:
```typescript
// WatchlistPage.tsx — 알림 섹션에 페이지네이션 추가
const [alertPage, setAlertPage] = useState(1);
const { data: alerts, isLoading: alertsLoading } = useAlerts({ page: alertPage, size: 20 });

// useAlerts 훅이 items만 반환하므로 전체 응답(AlertListResponse 포함 total)을 반환하도록 수정 필요
// JSX 알림 섹션 하단에:
<Pagination page={alertPage} totalPages={alertTotalPages} onPageChange={setAlertPage} />
```

---

### 7. CompanyDetailPage — 공시/딜/제재 섹션 페이지네이션 없음

- **파일**: `src/modules/kiis/pages/CompanyDetailPage.tsx:152-155`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: `useDisclosures(corpCode!)`, `useDealsByCompany(corpCode!)`, `useClassifiedSanctions(corpCode!)` 모두 페이지네이션 파라미터 없이 호출. 각 섹션이 BE default 20건만 표시하고 나머지 생략. 기업 상세 페이지는 여러 데이터를 한 화면에 보여주므로 "View all" 링크나 내부 페이지네이션 필요.
- **수정안**:
  - 간단한 방법: 각 섹션에 `size: 5` (미리보기)로 제한 + "View all →" 링크를 전용 페이지로 연결
  - 또는: 각 섹션에 "더 보기" 버튼으로 `size`를 점진적으로 늘리기

---

### 8. SanctionListPage — 검색 라벨이 실제 기능과 불일치

- **파일**: `src/modules/kiis/pages/SanctionListPage.tsx:88`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: Input 라벨이 `"Company Code / Name"`이지만, 입력값이 `corpCode` 상태에 직접 저장되어 `useClassifiedSanctions(corpCode)`의 URL 파라미터 `{corp_code}`로 전달됨. BE 엔드포인트 `GET /sanctions/classified/{corp_code}`는 법인코드만 지원하고 이름 검색은 불가.
- **수정안**:
```typescript
// SanctionListPage.tsx:88 — 라벨 수정
<Input
  label="Company Code"        // "Company Code / Name" → "Company Code"
  placeholder="Enter corp code (e.g. 00126380)..."
  // ...
/>
```
또는 `CorpCodeInput` 컴포넌트로 교체하여 다른 페이지(PortfolioPage, DisclosurePage)와 일관성 확보.

---

### 9. CompanyDetailPage — 워치리스트 중복 추가 방지 없음

- **파일**: `src/modules/kiis/pages/CompanyDetailPage.tsx:170-181`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: "Watchlist" 버튼 클릭 시 이미 추가된 기업인지 확인하지 않음. BE가 409 에러를 반환하거나 중복 생성될 수 있음. 현재 워치리스트 상태를 조회하는 로직이 없어 버튼이 항상 "추가" 모드.
- **수정안**:
```typescript
// CompanyDetailPage.tsx — 이미 워치리스트에 있는지 확인
const { data: watchlist } = useWatchlist();
const isWatched = watchlist?.some((w) => w.company_id === company.id);

// 버튼을 조건부로 변경:
<Button
  variant={isWatched ? "ghost" : "secondary"}
  icon={isWatched ? Check : Plus}
  onClick={isWatched ? undefined : handleAddWatchlist}
  disabled={isWatched}
  loading={addToWatchlist.isPending}
>
  {isWatched ? "Watched" : "Watchlist"}
</Button>
```

---

## Minor 이슈 (6건)

### 10. DisclosurePage — typeVariant 매핑 불완전

- **파일**: `src/modules/kiis/pages/DisclosurePage.tsx:37-42`
- **심각도**: Minor
- **카테고리**: 타입불일치
- **문제**: `typeVariant` 매핑이 7개 DisclosureType 중 4개만 정의(`annual_report`, `audit_report`, `material`, `sanction`). `quarterly`, `semi_annual`, `other`는 fallback "neutral"로 표시되어 시각적 구분 불가.
- **수정안**:
```typescript
const typeVariant: Record<string, BadgeVariant> = {
  annual_report: "info",
  audit_report: "success",
  quarterly: "info",         // ← 추가
  semi_annual: "info",       // ← 추가
  material: "warning",
  sanction: "error",
  other: "neutral",          // ← 명시적 선언
};
```

---

### 11. useReitAssets 훅이 Dead Code

- **파일**: `src/modules/kiis/hooks/useReits.ts:35-46`
- **심각도**: Minor
- **카테고리**: 런타임버그
- **문제**: `useReitAssets(reitsCode)` 훅이 정의되어 있지만 프론트엔드 어디서도 사용하지 않음. `ReitDetailPage`는 `useReitDetail`의 응답(`REITsDetailResponse { reits, assets }`)에 이미 포함된 assets를 사용. 별도 BE 엔드포인트 `GET /reits/{code}/assets`가 호출되지 않음.
- **수정안**: `useReitAssets` 훅 삭제, 또는 향후 별도 자산 페이지에서 사용할 계획이면 주석으로 의도 명시.

---

### 12. FundDetailPage — manager_name을 keyField로 사용

- **파일**: `src/modules/kiis/pages/FundDetailPage.tsx:124`
- **심각도**: Minor
- **카테고리**: 런타임버그
- **문제**: `<DataTable keyField="manager_name" ...>` — 동명이인 매니저가 같은 펀드에 존재하면 React key 충돌. 확률은 낮지만 BE 스키마에 고유 ID가 없어 발생 가능.
- **수정안**:
```typescript
// manager_name + position 조합으로 고유 키 생성하거나 index 사용
<DataTable
  columns={managerColumns}
  data={managers}
  keyField="manager_name"  // BE에서 unique id를 추가하는 것이 이상적
  compact
  striped
/>
// 또는 data를 map하여 임시 id 부여:
// data={managers.map((m, i) => ({ ...m, _id: `${m.manager_name}-${i}` }))}
// keyField="_id"
```

---

### 13. useReitAssets / useFundManagers — Response Type Generic 누락

- **파일**: `src/modules/kiis/hooks/useReits.ts:39`, `src/modules/kiis/hooks/useFunds.ts:46`
- **심각도**: Minor
- **카테고리**: 타입불일치
- **문제**: 두 훅 모두 `kiisApi.get(...)` 호출 시 response type generic을 지정하지 않아 `data`가 `any` 타입. 다른 훅들(`useCompanies`, `useFunds` 등)은 `kiisApi.get<FundListResponse>(...)` 형태로 타입 지정.
- **수정안**:
```typescript
// useReits.ts:39
const { data } = await kiisApi.get<REITsAssetListResponse>(
  `/reits/${reitsCode}/assets`,
);

// useFunds.ts:46
const { data } = await kiisApi.get<FundManagerListResponse>("/kofia/managers", {
  params,
});
```
> `REITsAssetListResponse`와 `FundManagerListResponse` 타입이 FE에 없으면 추가 필요:
> ```typescript
> // types/reit.ts
> export interface REITsAssetListResponse { total: number; items: REITsAssetItem[]; }
> // types/fund.ts
> export interface FundManagerListResponse { total: number; items: FundManagerItem[]; }
> ```

---

### 14. useWatchlist — total 카운트 생략

- **파일**: `src/modules/kiis/hooks/useWatchlist.ts:13-18`
- **심각도**: Minor
- **카테고리**: 상태관리
- **문제**: `useWatchlist`가 `data.items`만 반환하고 `data.total`을 버림. 현재 `WatchlistPage`에서 total을 사용하지 않지만, 향후 페이지네이션이나 카운트 뱃지 추가 시 훅 시그니처 변경 필요.
- **수정안**: 전체 `WatchlistListResponse` 반환으로 변경:
```typescript
export function useWatchlist() {
  return useQuery<WatchlistListResponse>({
    queryKey: ["kiis", "watchlist"],
    queryFn: async () => {
      const { data } = await kiisApi.get<WatchlistListResponse>("/watchlist");
      return data;  // data.items 대신 data 전체 반환
    },
  });
}
// 사용처에서: watchlist?.items, watchlist?.total
```

---

### 15. CompanyDetailPage — 평판 점수 로딩 시 섹션 미표시

- **파일**: `src/modules/kiis/pages/CompanyDetailPage.tsx:242`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**: `{reputation && (...)}` 조건부 렌더링으로, 평판 점수 로딩 중에는 해당 섹션이 완전히 보이지 않음. 다른 섹션(Disclosures, Deals)은 데이터 없을 때 EmptyState를 표시하지만, Reputation 섹션은 로딩 중에 아무것도 표시하지 않아 레이아웃이 로딩 완료 후 갑자기 변경됨.
- **수정안**:
```typescript
// CompanyDetailPage.tsx:242 — 로딩 상태 추가
const { data: reputation, isLoading: reputationLoading } = useReputationScore(corpCode!);

// JSX에서:
{reputationLoading ? (
  <Card title="Reputation Score" headerBar>
    <Spinner />
  </Card>
) : reputation ? (
  <Card title="Reputation Score" headerBar>
    {/* 기존 렌더링 */}
  </Card>
) : null}
```

---

## FE ↔ BE 타입 정합성 검증 결과

14개 타입 파일을 대응하는 백엔드 스키마와 필드 단위로 비교한 결과:

| FE Type | BE Schema | 정합성 | 비고 |
|---------|-----------|--------|------|
| `company.ts` | `company.py` | ✅ | 모든 필드 일치 |
| `dashboard.ts` | `dashboard.py` | ✅ | 모든 필드 일치 |
| `news.ts` | `news.py` | ✅ | 모든 필드 일치 |
| `watchlist.ts` | `alert.py` | ✅ | 모든 필드 일치 |
| `sanction.ts` | `sanction.py` | ✅ | 모든 필드 일치 |
| `fund.ts` | `fund.py` | ✅ | 모든 필드 일치 (BE Decimal → FE string으로 올바르게 매핑) |
| `reit.ts` | `reits.py` | ✅ | 모든 필드 일치 |
| `manager.ts` | `manager.py` | ✅ | 모든 필드 일치 (from_fund_id, to_fund_id 포함) |
| `portfolio.ts` | `portfolio.py` | ✅ | 모든 필드 일치 (ValuationUpdateRequest string → BE Decimal 자동 변환) |
| `entity.ts` | `entity.py` | ✅ | 모든 필드 일치 |
| `disclosure.ts` | `disclosure.py` | ⚠️ | `dart_viewer_url`: FE `string \| null` vs BE `str` (required) — 방어적이므로 무해 |
| `deal.ts` | `deal.py` | ✅ | 모든 필드 일치 (amount: FE string, BE Decimal — Pydantic JSON 직렬화와 일치) |
| `analysis.ts` | `analysis.py` | ✅ | 모든 필드 일치 (BE @field_serializer가 Decimal→float 변환) |
| `search.ts` | `search.py` | ✅ | 모든 필드 일치 |

### API 경로 정합성

모든 프론트엔드 훅의 API 경로가 백엔드 라우터 prefix와 정확히 일치함:
- Vite Proxy: `/api/kiis` → `:8001/api/v1`
- 모든 엔드포인트 prefix 일치 확인 완료 (companies, news, sanctions, kofia, reits 등)

### 페이지네이션 방식

- FE와 BE 모두 `page`(1-indexed) + `size` 방식 사용 — 일관성 확인 완료
- `FundManagerListResponse`만 예외: BE 응답에 `page`/`size` 필드 없음 (total + items만)

---

## 기존 리뷰와의 관계

이 문서의 15건 이슈는 모두 `docs/20260213_0836_KIIS_Code_Review.md`의 28건과 중복되지 않음.
기존 리뷰에서 이미 보고된 주요 이슈 (참고용):
- ~~DashboardPage 하드코딩된 라벨~~ (기존 #6)
- ~~variant map 중복~~ (기존 HIGH)
- ~~null body POST~~ (기존 HIGH)
- ~~SearchBar unsafe type casting~~ (기존 #7)
- ~~KiisRoutes lazy loading 미적용~~ (기존 MEDIUM)
