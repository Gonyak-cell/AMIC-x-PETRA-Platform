# SI Mapping Upload Card Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `SIMappingPanel`에서 법인 문서가 없을 때 섹션을 숨기는 대신 `EngagementDocUpload` 컴포넌트를 임베딩하여 모달 안에서 바로 업로드 → AI 추출 → Value Chain 매핑까지 완결.

**Architecture:** `SIMappingPanel.tsx` 한 파일만 수정. `hasRegNo`가 `false`일 때 amber 테두리 카드 안에 `EngagementDocUpload`를 렌더링. 업로드 확정 시 `useConfirmExtraction`이 이미 `["ma", "transactions", txnId]`를 invalidate하므로 Overview와 SIMappingPanel 모두 자동 갱신.

**Tech Stack:** React, TypeScript, TanStack Query (React Query), Tailwind CSS

---

### Task 1: EngagementDocUpload 임포트 추가 및 조건부 렌더링 변경

**Files:**
- Modify: `amic-platform/src/modules/ma/components/si-mapping/SIMappingPanel.tsx`

**Step 1: `EngagementDocUpload` import 추가**

파일 상단 (라인 19 `VcMappingResult` import 아래)에 추가:

```ts
import EngagementDocUpload from "@/modules/ma/components/overview/EngagementDocUpload";
```

**Step 2: 조건부 렌더링 변경 (라인 232-266)**

현재 코드:
```tsx
{/* VC 자동 매핑 (법인정보 기반) */}
{hasRegNo && (
  <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50/30 p-4">
    <h3 className="mb-2 text-sm font-semibold text-emerald-800">
      법인정보 기반 Value Chain 매핑
    </h3>
    <div className="mb-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-emerald-700">
      {corpRegNo && <span>법인등록번호: {corpRegNo}</span>}
      {bizRegNo && <span>사업자등록번호: {bizRegNo}</span>}
    </div>
    {!vcResult && (
      <button
        type="button"
        onClick={handleVcMapping}
        disabled={vcMapMutation.isPending}
        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {vcMapMutation.isPending
          ? "매핑 중..."
          : "Value Chain 매핑 실행"}
      </button>
    )}
    {vcMapMutation.isError && (
      <p role="alert" className="mt-2 text-sm text-red-600">
        {vcMapMutation.error.message}
      </p>
    )}
    {vcResult && (
      <VcMappingResult
        txnId={txnId}
        company={vcResult.company}
        mapping={vcResult.mapping}
      />
    )}
  </div>
)}
```

변경 후 코드 (전체 블록 교체):
```tsx
{/* VC 자동 매핑 (법인정보 기반) */}
{hasRegNo ? (
  <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50/30 p-4">
    <h3 className="mb-2 text-sm font-semibold text-emerald-800">
      법인정보 기반 Value Chain 매핑
    </h3>
    <div className="mb-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-emerald-700">
      {corpRegNo && <span>법인등록번호: {corpRegNo}</span>}
      {bizRegNo && <span>사업자등록번호: {bizRegNo}</span>}
    </div>
    {!vcResult && (
      <button
        type="button"
        onClick={handleVcMapping}
        disabled={vcMapMutation.isPending}
        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {vcMapMutation.isPending
          ? "매핑 중..."
          : "Value Chain 매핑 실행"}
      </button>
    )}
    {vcMapMutation.isError && (
      <p role="alert" className="mt-2 text-sm text-red-600">
        {vcMapMutation.error.message}
      </p>
    )}
    {vcResult && (
      <VcMappingResult
        txnId={txnId}
        company={vcResult.company}
        mapping={vcResult.mapping}
      />
    )}
  </div>
) : (
  <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50/30 p-4">
    <div className="mb-3">
      <h3 className="mb-0.5 text-sm font-semibold text-amber-800">
        법인정보 기반 Value Chain 매핑
      </h3>
      <p className="text-xs text-amber-700">
        자동 매핑을 위해 법인등기부등본 또는 사업자등록증을 업로드하세요.
        업로드 후 Overview의 법인 정보도 자동으로 업데이트됩니다.
      </p>
    </div>
    <EngagementDocUpload txnId={txnId} />
  </div>
)}
```

**Step 3: 타입 체크 실행**

```bash
cd "c:/Users/서지원/OneDrive/Documents/Coding/AMIC x PETRA Platform/amic-platform"
npx tsc --noEmit
```

Expected: 에러 없음 (0 errors)

**Step 4: 커밋**

```bash
git add amic-platform/src/modules/ma/components/si-mapping/SIMappingPanel.tsx
git commit -m "feat(platform/ma): SI 자동 매핑 모달에 법인 문서 업로드 카드 추가"
```

---

## 검증 체크리스트

1. **업로드 카드 표시**: 법인 문서 없는 딜 → SI 자동 매핑 모달 열기 → amber 테두리 박스 + 업로드 UI 표시
2. **기존 딜 영향 없음**: 법인 문서 있는 딜 → 기존 emerald 테두리 VC 매핑 섹션 그대로
3. **업로드 플로우**: 파일 업로드 → 4단계 진행 상태 표시 → ExtractionReviewModal 열림
4. **자동 갱신**: 확정 클릭 → VC 섹션 자동 표시 + Overview 법인정보 반영

---

## 데이터 흐름 참고

```
EngagementDocUpload (in SIMappingPanel)
  → 파일 업로드 → AI 추출 → ExtractionReviewModal
  → "확정" 클릭 → useConfirmExtraction.onSuccess
      → invalidate ["ma", "transactions", txnId]
  → BuyersTab.useTransaction refetch
      → corporateInfo 갱신 → hasRegNo = true → VC 섹션 표시
      → TransactionOverviewTab.txn 갱신 → CompanyInfoCard 업데이트
```
