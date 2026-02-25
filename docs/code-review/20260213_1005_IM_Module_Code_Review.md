# IM 모듈 코드 리뷰 보고서

> 리뷰 일시: 2026-02-13 10:03
> 리뷰 범위: IM 모듈 프론트엔드 전체 + 백엔드 API 정합성 검증
> 기존 감사 참고: `docs/20260212_1659_IM_FE_BE_Mismatch_Audit.md`

---

## 목차

1. [발견 이슈 요약](#1-발견-이슈-요약)
2. [상세 이슈](#2-상세-이슈)
3. [FE ↔ BE 타입 정합성 검증](#3-fe--be-타입-정합성-검증)
4. [기존 감사 결과 반영 확인](#4-기존-감사-결과-반영-확인)
5. [코드 품질 소견](#5-코드-품질-소견)

---

## 1. 발견 이슈 요약

| # | 심각도 | 카테고리 | 파일 | 요약 |
|---|--------|----------|------|------|
| 1 | Critical | 런타임버그 | ProgressTracker.tsx:68-70 | FAILED 상태일 때 실패 지점 표시가 항상 Stage 0(PENDING)에 고정 |
| 2 | Major | UX결함 | CreateDocumentPage.tsx:116 | corp_code 숫자 전용 검증 누락 (길이만 체크) |
| 3 | Major | UX결함 | DocumentListPage.tsx | 상태별 필터 기능 없음 (SamplePage에는 구현되어 있음) |
| 4 | Major | 타입불일치 | TemplatesPage.tsx:14-50 | 템플릿 섹션명이 하드코딩된 표시용 문자열로 백엔드 프리셋과 불일치 |
| 5 | Minor | UX결함 | DocumentListPage.tsx:80-90 | KPI 카드: Total은 전체, 나머지는 현재 페이지 데이터로 기준 혼재 |
| 6 | Minor | 런타임버그 | CreateDocumentPage.tsx:109 | useEffect 의존성에 fetchCompany 객체 포함 → 불필요한 effect 재실행 |
| 7 | Minor | UX결함 | document.ts:50-66 | industry_kpi/industry_overview가 CONTENT_SECTIONS에 없어 CUSTOM 모드 선택 불가 |
| 8 | Minor | UX결함 | CreateDocumentPage.tsx:103 | URL corpCode → industry 자동 매핑 시 항상 "general"로 초기화 |

---

## 2. 상세 이슈

### Issue #1 — ProgressTracker FAILED 상태 표시 오류

- **파일**: `src/modules/im/components/ProgressTracker.tsx:68-70`
- **심각도**: Critical
- **카테고리**: 런타임버그
- **문제**: `STATUS_ORDER["FAILED"] = -1`로 설정되어 있고, `isFailedStage = isFailed && index === 0`이므로, 문서가 어느 단계에서 실패하든 항상 첫 번째 스테이지(PENDING)에만 실패 마크가 표시된다. 예를 들어 ANALYZING 단계(progress 40%)에서 실패해도, PENDING만 빨간 원으로 표시되고 나머지(COLLECTING 포함)는 모두 회색으로 나타남.
- **기대 동작**: 실패 전까지 완료된 단계는 완료(체크) 표시, 실패한 단계에 에러 마크 표시
- **수정안**:

```tsx
// ProgressTracker.tsx — STAGES 배열에서 현재 진행도 기반 실패 위치 계산
// 기존 STATUS_ORDER에 FAILED: -1 대신, progressPct 기반으로 실패 단계를 추론

// 방법: progressPct 기반 실패 단계 계산
const PROGRESS_STAGE_MAP = [0, 20, 40, 55, 80, 100]; // 각 stage 시작 pct

function getFailedStageIndex(progressPct: number): number {
  for (let i = PROGRESS_STAGE_MAP.length - 1; i >= 0; i--) {
    if (progressPct >= PROGRESS_STAGE_MAP[i]) return i;
  }
  return 0;
}

// 컴포넌트 내:
const failedAtIndex = isFailed ? getFailedStageIndex(progressPct) : -1;

// 스테이지 렌더링:
const isCompleted = !isFailed
  ? currentIndex > index
  : index < failedAtIndex;
const isCurrent = !isFailed && currentIndex === index;
const isFailedStage = isFailed && index === failedAtIndex;
```

---

### Issue #2 — corp_code 숫자 전용 검증 누락

- **파일**: `src/modules/im/pages/CreateDocumentPage.tsx:116`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: `handleFetchCompany`에서 `corpCodeInput.length !== 8`만 검증하고, 숫자 여부(`isdigit`)를 확인하지 않는다. 백엔드는 `field_validator`로 `v.isdigit()`를 검증하므로, 사용자가 "abcdefgh" 입력 시 FE 통과 → BE 422 에러 발생.
- **수정안**:

```tsx
// CreateDocumentPage.tsx — handleFetchCompany
const handleFetchCompany = async () => {
  if (!corpCodeInput || corpCodeInput.length !== 8 || !/^\d{8}$/.test(corpCodeInput)) {
    toast.error("Please enter a valid 8-digit numeric corp code");
    return;
  }
  // ...
};

// 또는 Input에 pattern 추가:
<Input
  label="Corp Code (8-digit)"
  value={corpCodeInput}
  onChange={(e) => setCorpCodeInput(e.target.value.replace(/\D/g, ""))}
  placeholder="e.g. 00126380"
  maxLength={8}
  inputMode="numeric"
/>
```

---

### Issue #3 — DocumentListPage 상태 필터 없음

- **파일**: `src/modules/im/pages/DocumentListPage.tsx`
- **심각도**: Major
- **카테고리**: UX결함
- **문제**: 상태별 필터링 UI가 없다. `SamplePage.tsx:247-258`에는 필터 버튼이 구현되어 있지만, 실제 API 연동 리스트 페이지에는 적용되지 않았다. 사용자가 COMPLETED / FAILED / In-Progress 문서를 빠르게 찾을 수 없다.
- **수정안**:

```tsx
// DocumentListPage.tsx — status 필터 추가
const [statusFilter, setStatusFilter] = useState<string>("ALL");

// API 호출 시 (백엔드에 status 파라미터가 있다면):
const { data, isLoading, isError } = useDocuments({
  offset: page * PAGE_SIZE,
  limit: PAGE_SIZE,
  // status: statusFilter !== "ALL" ? statusFilter : undefined, // 백엔드 지원 필요
});

// 또는 클라이언트 사이드 필터:
const filteredItems = useMemo(() => {
  if (statusFilter === "ALL") return data?.items ?? [];
  return (data?.items ?? []).filter((d) => d.status === statusFilter);
}, [data?.items, statusFilter]);

// UI에 필터 버튼 추가 (SamplePage 패턴 참고)
```

> **참고**: 백엔드 `list_documents` 엔드포인트는 현재 `search` 파라미터만 지원하고 `status` 필터 파라미터는 없다. 서버 사이드 필터가 필요하면 백엔드 수정도 필요.

---

### Issue #4 — TemplatesPage 섹션명 하드코딩

- **파일**: `src/modules/im/pages/TemplatesPage.tsx:14-50`
- **심각도**: Major
- **카테고리**: 타입불일치
- **문제**: 각 템플릿(TITAN, COVENANT, FULL)의 `sections` 배열이 표시용 문자열로 하드코딩되어 있으며, 백엔드의 실제 프리셋 섹션 구성과 다르다.
  - 예: TITAN 템플릿에 "Financial Highlights", "Investment Rationale"이 포함되어 있으나, 백엔드 `TITAN_SECTIONS`에는 이 섹션이 존재하지 않고 대신 `executive_summary`, `company_overview`, `financial_analysis`, `contact` 등이 포함됨.
  - 사용자에게 보여지는 섹션 목록과 실제 생성되는 섹션이 다르면 혼동을 유발.
- **수정안**:

```tsx
// TemplatesPage.tsx — 백엔드 프리셋 섹션과 일치하도록 SECTION_LABEL_MAP 활용
import { SECTION_LABEL_MAP, type SectionId } from "@/modules/im/types/document";

interface TemplateInfo {
  style: IMStyle;
  name: string;
  description: string;
  icon: typeof FileText;
  sections: SectionId[];
}

const TEMPLATES: TemplateInfo[] = [
  {
    style: "TITAN",
    name: "Titan",
    description: "...",
    icon: Briefcase,
    sections: ["cover", "disclaimer", "toc_divider", "executive_summary",
               "company_overview", "financial_analysis", "contact"],
  },
  // ... 다른 템플릿도 백엔드 프리셋에 맞춰 수정
];

// 렌더링 시:
{template.sections.map((sectionId) => (
  <span key={sectionId} className="...">
    {SECTION_LABEL_MAP[sectionId] ?? sectionId}
  </span>
))}
```

---

### Issue #5 — KPI 카드 데이터 기준 혼재

- **파일**: `src/modules/im/pages/DocumentListPage.tsx:80-90`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**: "Total Projects" KPI는 `data.total` (전체 문서 수)을 사용하고, "In Progress (page)", "Completed (page)", "Failed (page)"는 현재 페이지의 `items` 배열에서 계산한다. 레이블에 "(page)"를 표기했으나, Total만 전역이어서 "Total: 100, In Progress: 2, Completed: 15, Failed: 0"처럼 합계가 17/100으로 보여 혼란스럽다.
- **수정안**:

```tsx
// 옵션 A: Total도 현재 페이지로 통일
total: items.length,

// 옵션 B: 서버에서 전체 status별 count를 제공하는 API 추가
// GET /documents/stats → { total, pending, completed, failed, ... }

// 옵션 C: 레이블을 더 명확하게
<KpiCard label={`Total (all ${total})`} value={String(items.length)} ... />
```

---

### Issue #6 — useEffect 의존성 배열에 mutation 객체 포함

- **파일**: `src/modules/im/pages/CreateDocumentPage.tsx:109`
- **심각도**: Minor
- **카테고리**: 런타임버그
- **문제**: `useEffect([urlCorpCode, fetchCompany])` — `fetchCompany`는 `useFetchCompany()` (=`useMutation`)가 반환하는 객체로, `isPending`, `data` 등 상태가 변할 때마다 새 참조가 생성된다. effect 본문 내 `lastFetchedCorpCode` ref 가드가 중복 실행을 방지하지만, 불필요한 effect 호출이 매 렌더마다 발생한다.
- **수정안**:

```tsx
// fetchCompany.mutateAsync는 stable reference이므로:
const fetchCompanyMutate = fetchCompany.mutateAsync;
useEffect(() => {
  if (!urlCorpCode || urlCorpCode.length !== 8) return;
  if (urlCorpCode === lastFetchedCorpCode.current) return;
  lastFetchedCorpCode.current = urlCorpCode;
  fetchCompanyMutate(urlCorpCode)
    .then(() => { /* ... */ })
    .catch(() => { /* ... */ });
}, [urlCorpCode, fetchCompanyMutate]);
```

---

### Issue #7 — CUSTOM 모드에서 산업 섹션 선택 불가

- **파일**: `src/modules/im/types/document.ts:50-66`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**: `CONTENT_SECTIONS` 배열에 `industry_kpi`, `industry_overview`가 포함되어 있지 않아, CUSTOM 모드에서 사용자가 산업별 섹션을 명시적으로 선택할 수 없다. 백엔드가 산업 설정에 따라 자동 포함한다면 의도된 동작이나, 사용자에게 이를 알리는 UI가 없다.
- **수정안**:

```tsx
// 옵션 A: CONTENT_SECTIONS에 산업 섹션 추가
export const CONTENT_SECTIONS: { id: SectionId; label: string }[] = [
  // ... 기존 15개 ...
  { id: "industry_kpi", label: "Industry KPIs" },
  { id: "industry_overview", label: "Industry Overview" },
];

// 옵션 B: 산업 선택 시 자동 포함됨을 안내하는 메시지 추가 (CreateDocumentPage)
{formData.industry !== "general" && formData.im_style === "CUSTOM" && (
  <p className="text-xs text-text-secondary">
    Industry-specific sections (KPIs, Overview) will be automatically included.
  </p>
)}
```

---

### Issue #8 — URL corpCode → industry 초기화 시 매핑 미적용

- **파일**: `src/modules/im/pages/CreateDocumentPage.tsx:103`
- **심각도**: Minor
- **카테고리**: UX결함
- **문제**: URL에서 `corpCode`를 받아 자동 fetch할 때, `industry: "general"`로 하드코딩 초기화한다. 이후 `useEffect`에서 company 데이터 기반 자동 매핑이 동작하지만, fetch → company 로딩 → industry 설정까지 시간차가 있어 step 2로 넘어간 후에야 industry가 바뀔 수 있다. UX 상 step 1에서 이미 industry가 "general"로 표시되어 사용자가 수동으로 바꿀 수 있으며, 이 경우 자동 매핑이 무시된다 (`formData.industry !== "general"` 체크).
- **수정안**: 현재 동작은 기능적으로 정상이지만, 자동 매핑 중임을 표시하면 UX 개선 가능.

```tsx
// Company preview 영역에 industry 매핑 상태 표시
{company?.industry && formData.industry === "general" && (
  <span className="text-xs text-amic animate-pulse">
    Detecting industry...
  </span>
)}
```

---

## 3. FE ↔ BE 타입 정합성 검증

### 3-1. Enum/Union 값 대조

| 타입 | 값 수 | FE | BE | 결과 |
|------|-------|----|----|------|
| `DocumentStatus` | 7 | PENDING / COLLECTING / ANALYZING / GENERATING / RENDERING / COMPLETED / FAILED | `DocumentStatus(str, Enum)` 동일 | ✅ |
| `CompanyFetchStatus` | 4 | PENDING / REFRESHING / COMPLETED / FAILED | `company_service.py` 참조 (PENDING, REFRESHING, + task의 COMPLETED/FAILED) | ✅ |
| `IMStyle` | 4 | TITAN / COVENANT / FULL / CUSTOM | `_VALID_IM_STYLES` set | ✅ |
| `IndustryId` | 9 | general ~ consumer | `_ALL_VALID_INDUSTRIES` (6+3) | ✅ |
| `SectionId` | 21 | 19 기본 + 2 산업별 | `SECTION_IDS`(19) + `INDUSTRY_SECTION_IDS`(2) | ✅ |

### 3-2. Document 필드별 대조

| FE 필드 (`Document` interface) | BE 필드 (`DocumentResponse` schema) | 타입 일치 | 비고 |
|------|------|:---:|------|
| `id: string` | `id: UUID` | ✅ | JSON 직렬화 시 string |
| `owner_id: string` | `owner_id: UUID` | ✅ | |
| `corp_code: string` | `corp_code: str` | ✅ | |
| `company_name: string` | `company_name: str` | ✅ | |
| `project_name: string \| null` | `project_name: str \| None` | ✅ | |
| `im_style: IMStyle` | `im_style: str` | ✅ | FE가 더 strict |
| `sections: SectionId[]` | `sections: list[str]` | ✅ | FE가 더 strict |
| `industry: IndustryId \| null` | `industry: str \| None` | ✅ | BE `@property` from generation_config |
| `status: DocumentStatus` | `status: str` | ✅ | FE가 더 strict |
| `progress_pct: number` | `progress_pct: int` | ✅ | |
| `celery_task_id: string \| null` | `celery_task_id: str \| None` | ✅ | |
| `pptx_path: string \| null` | `pptx_path: str \| None` | ✅ | |
| `pdf_path: string \| null` | `pdf_path: str \| None` | ✅ | |
| `file_size_bytes: number \| null` | `file_size_bytes: int \| None` | ✅ | |
| `created_at: string` | `created_at: datetime` | ✅ | ISO-8601 직렬화 |
| `updated_at: string` | `updated_at: datetime` | ✅ | |
| `completed_at: string \| null` | `completed_at: datetime \| None` | ✅ | |

**총 17 필드 — 전부 일치 ✅**

### 3-3. Company 필드별 대조

| FE 필드 (`Company` interface) | BE 필드 (`CompanyResponse` schema) | 타입 일치 | 비고 |
|------|------|:---:|------|
| `id: string` | `id: UUID` | ✅ | |
| `corp_code: string` | `corp_code: str` | ✅ | |
| `corp_name: string` | `corp_name: str` | ✅ | |
| `corp_name_en: string \| null` | `corp_name_en: str \| None` | ✅ | |
| `stock_code: string \| null` | `stock_code: str \| None` | ✅ | |
| `industry: string \| null` | `industry: str \| None` | ✅ | DART 원본 산업명 |
| `homepage_url: string \| null` | `homepage_url: str \| None` | ✅ | |
| `fetch_status: CompanyFetchStatus` | `fetch_status: str` | ✅ | FE가 더 strict |
| `last_fetched_at: string \| null` | `last_fetched_at: datetime \| None` | ✅ | |
| `cache_expires_at: string \| null` | `cache_expires_at: datetime \| None` | ✅ | |
| `created_at: string` | `created_at: datetime` | ✅ | |
| `updated_at: string` | `updated_at: datetime` | ✅ | |

**총 12 필드 — 전부 일치 ✅**

### 3-4. DocumentCreate 요청 대조

| FE 필드 (`DocumentCreate`) | BE 필드 (`DocumentCreate` schema) | 일치 | 비고 |
|------|------|:---:|------|
| `corp_code: string` | `corp_code: str` (required, 8자리) | ✅ | |
| `project_name?: string` | `project_name: str \| None` | ✅ | |
| `im_style: IMStyle` | `im_style: str` (default="FULL") | ✅ | |
| `sections?: SectionId[]` | `sections: list[str]` (default=[]) | ✅ | |
| `industry?: IndustryId` | `industry: str` (default="general") | ✅ | |
| `webhook_url?: string` | `webhook_url: str \| None` | ✅ | UI 미노출 (의도적) |
| `pdf_password?: string` | `pdf_password: str \| None` (min 4) | ✅ | |

**총 7 필드 — 전부 일치 ✅**

### 3-5. API 엔드포인트 대조

| FE 훅 | HTTP | 경로 | BE 라우트 | 상태코드 | 결과 |
|--------|------|------|-----------|----------|------|
| `useDocuments` | GET | `/documents` | `list_documents` | 200 | ✅ |
| `useDocument` | GET | `/documents/{id}` | `get_document` | 200 | ✅ |
| `useCreateDocument` | POST | `/documents` | `create_document` | 202 | ✅ |
| `useDownloadDocument` | GET | `/documents/{id}/download?format=` | `download_document` | 200 | ✅ |
| `useCompany` | GET | `/companies/{corpCode}` | `get_company_data` | 200 | ✅ |
| `useFetchCompany` | POST | `/companies` | `fetch_company_data` | 202 | ✅ |

Vite 프록시: `/api/im` → `localhost:8002/api/v1` ✅

---

## 4. 기존 감사 결과 반영 확인

> 참조: `docs/20260212_1659_IM_FE_BE_Mismatch_Audit.md`

| # | 기존 이슈 | 현재 코드 확인 위치 | 반영 여부 |
|---|-----------|---------------------|:---------:|
| 1 | SectionId Title Case → snake_case 21개 | `types/document.ts:18-39` — 21개 snake_case 유니온 타입 | ✅ |
| 2 | CompanyFetchStatus "COLLECTING" → "REFRESHING" | `types/company.ts:1` — PENDING \| REFRESHING \| COMPLETED \| FAILED | ✅ |
| 3 | handleRegenerate에 industry 누락 | `DocumentDetailPage.tsx:83` — `industry: doc.industry \|\| undefined` | ✅ |
| 4 | 섹션 raw ID 그대로 렌더링 | `DocumentDetailPage.tsx:242` — `SECTION_LABEL_MAP[section]` 사용 | ✅ |
| 5 | Mock 데이터 유효하지 않은 섹션 ID | 감사 문서에서 수정 완료 보고됨 | ✅ |
| 6 | DocumentListResponse에 offset/limit 누락 | `useDocuments.ts:19` — `{ items, total, offset, limit }` | ✅ |
| 7 | DocumentListParams에 search 누락 | `types/document.ts:127` — `search?: string` | ✅ |

**기존 감사 7건 — 모두 코드에 반영 확인 ✅**

---

## 5. 코드 품질 소견

### 양호한 점

1. **폴링 설계**: `useDocument`와 `useCompany` 모두 `refetchInterval` 콜백으로 조건부 폴링을 구현. IN_PROGRESS 상태에서만 3초 간격 폴링하고 완료/실패 시 자동 중단. React Query가 언마운트 시 자동 정리하므로 메모리 누수 없음.

2. **다운로드 구현**: `useDownloadDocument`에서 Blob 응답 처리, Content-Disposition 파싱 (RFC 5987 UTF-8 대응), ObjectURL 생성/해제, 안전한 파일명 치환(`sanitizeFilename`)까지 견고하게 구현.

3. **타입 안전성**: FE 타입이 BE보다 더 strict (string 대신 union type 사용). `isIMStyle()`, `isIndustryId()` 타입 가드 함수로 런타임 검증 보완.

4. **접근성**: Step indicator에 `aria-current="step"`, `aria-label`, `role="progressbar"`, `aria-pressed` 등 적절한 ARIA 속성 적용. 스크린리더 전용 텍스트(`sr-only`) 사용.

5. **에러 바운더리**: `ImErrorBoundary`가 Sentry 연동으로 에러 자동 보고하고, 사용자에게 retry UI 제공.

6. **산업 자동 매핑**: DART 산업명 → IndustryId 매핑 테이블이 포괄적이며, direct match → DART map 순서로 2단계 매칭.

### 개선 권장

1. **TemplatesPage ↔ 백엔드 프리셋 동기화** (Issue #4): 현재 가장 큰 정합성 문제. 사용자에게 보여지는 섹션과 실제 생성 섹션이 다르면 신뢰도 하락.

2. **서버 사이드 status 필터** (Issue #3): 문서가 많아지면 클라이언트 사이드 필터로는 부족. `GET /documents?status=COMPLETED` 지원 권장.

3. **ProgressTracker 실패 표시** (Issue #1): 사용자 경험에 직접 영향. progress_pct 기반 실패 지점 추론 로직 추가 필요.

### 알려진 BE 제한 (FE 영향 없음)

| 항목 | 사유 |
|------|------|
| Celery 태스크가 Company.fetch_status 직접 미갱신 | 별도 callback/signal 메커니즘 필요. FE 폴링은 정상 동작하나, status 전이가 BE 내부에서 완결되지 않을 수 있음 |
| `generation_config`, `stage_details` JSONB 미노출 | 서버 내부 파이프라인 데이터 — 의도적 설계 |
| BE `dart_data`, `financial_summary`, `brand_assets` 미노출 | 서버 사이드 전용 캐시 |

---

## 리뷰 파일 목록

| 영역 | 파일 | 비고 |
|------|------|------|
| FE Pages | `DocumentListPage.tsx`, `CreateDocumentPage.tsx`, `DocumentDetailPage.tsx`, `TemplatesPage.tsx`, `SamplePage.tsx` | 5개 페이지 |
| FE Hooks | `useDocuments.ts`, `useCompanies.ts` | 2개 훅 |
| FE Components | `DocumentStatusBadge.tsx`, `ImErrorBoundary.tsx`, `ProgressTracker.tsx` | 3개 컴포넌트 |
| FE Types | `document.ts`, `company.ts` | 2개 타입 |
| FE Shared | `src/types/industry.ts` | 공유 산업 타입 |
| FE Routing | `ImRoutes.tsx` | 라우팅 |
| FE API | `src/api/imClient.ts` | API 클라이언트 |
| BE Routes | `documents.py`, `companies.py`, `health.py` | 3개 라우트 |
| BE Schemas | `documents.py`, `companies.py` | 2개 스키마 |
| BE Models | `document.py`, `company.py` | 2개 ORM 모델 |
| BE Tasks | `generate_im.py`, `fetch_company.py`, `progress.py` | 3개 태스크 |
| BE Config | `im_document.py` (SECTION_IDS, INDUSTRY_SECTION_IDS) | 섹션 정의 |
