# 회사 정보 카드 법인등기부/사업자등록증 분리 표시 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** M&A Overview 탭의 회사 정보 카드를 법인등기부/사업자등록증 두 섹션으로 분리하고, 각 섹션에 독립 업로드 상태를 표시한다.

**Architecture:** 백엔드(MERGE 이미 구현)·DB 변경 없음. 프론트엔드 3개 파일만 수정. `CompanyInfoCard`가 `corporate_info` 필드를 두 섹션으로 나눠 표시하며, 각 섹션은 업로드 여부를 key field 존재로 판단한다.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, lucide-react

---

## Task 1: `document_extraction.ts` — "종목" → "사업 목적" 레이블 변경

**Files:**
- Modify: `amic-platform/src/modules/ma/types/document_extraction.ts:268`

**Step 1: 변경**

```ts
// 변경 전 (line 268)
business_item: "종목",

// 변경 후
business_item: "사업 목적",
```

**Step 2: tsc 확인**

```bash
cd amic-platform && npx tsc --noEmit 2>&1 | head -20
```
Expected: 0 errors

**Step 3: Commit**

```bash
git add amic-platform/src/modules/ma/types/document_extraction.ts
git commit -m "fix(ma/overview): '종목' 레이블을 '사업 목적'으로 변경"
```

---

## Task 2: `CompanyInfoCard.tsx` — 두 섹션으로 분리

**Files:**
- Modify: `amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx`

### 변경 사항 전체 코드

기존 파일을 아래 내용으로 **전체 교체**:

```tsx
import { useState } from "react";
import { UploadCloud, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { Transaction } from "@/modules/ma/types/transaction";
import type {
  CorporateDocsExtractedData,
  CorporateDirector,
} from "@/modules/ma/types/document_extraction";
import { sortDirectorsByPosition } from "@/modules/ma/types/document_extraction";
import EngagementDocUpload from "./EngagementDocUpload";

interface Props {
  txn: Transaction;
}

// ── 유틸 ──────────────────────────────────────────────────

function formatKRW(amount: number): string {
  if (amount >= 1_0000_0000) {
    const eok = amount / 1_0000_0000;
    return `${eok.toLocaleString(undefined, { maximumFractionDigits: 1 })}억 원`;
  }
  if (amount >= 1_0000) {
    const man = amount / 1_0000;
    return `${man.toLocaleString(undefined, { maximumFractionDigits: 1 })}만 원`;
  }
  return `${amount.toLocaleString()}원`;
}

// ── 공통 컴포넌트 ──────────────────────────────────────────

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-text-muted text-sm">{label}</dt>
      <dd className="text-sm">{value ?? "-"}</dd>
    </>
  );
}

// ── 섹션 헤더 ──────────────────────────────────────────────

interface SectionHeaderProps {
  title: string;
  isComplete: boolean;
  docName: string;
  uploadOpen: boolean;
  onUploadToggle: () => void;
}

function SectionHeader({
  title,
  isComplete,
  docName,
  uploadOpen,
  onUploadToggle,
}: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h4 className="text-xs font-semibold text-text-secondary uppercase">
        {title}
      </h4>
      {isComplete ? (
        <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
          <CheckCircle2 className="h-3.5 w-3.5" />
          업로드 완료
        </span>
      ) : (
        <button
          type="button"
          onClick={onUploadToggle}
          className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary transition-colors"
        >
          <UploadCloud className="h-3 w-3" />
          {uploadOpen ? "닫기" : `${docName}를 업로드하세요`}
        </button>
      )}
    </div>
  );
}

// ── 법인등기부 섹션 ────────────────────────────────────────

function RegistryBasicInfoSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
      <FieldRow label="상호" value={ci.company_name} />
      <FieldRow label="대표이사" value={ci.representative_name} />
      <FieldRow label="설립일" value={ci.establishment_date} />
      <FieldRow
        label="법인등록번호"
        value={
          ci.corporate_registration_number && (
            <span className="font-mono text-xs">
              {ci.corporate_registration_number}
            </span>
          )
        }
      />
      <FieldRow label="본점 소재지" value={ci.head_office_address} />
      <FieldRow label="사업 목적" value={ci.business_item} />
    </dl>
  );
}

function CapitalSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <div className="border-t border-gray-border pt-4">
      <h4 className="text-xs font-semibold text-text-secondary uppercase mb-3">
        자본 및 주식
      </h4>
      <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
        <FieldRow
          label="자본금"
          value={
            ci.capital_amount != null && (
              <span className="font-mono">{formatKRW(ci.capital_amount)}</span>
            )
          }
        />
        <FieldRow
          label="발행주식총수"
          value={
            ci.total_shares_issued != null && (
              <span className="font-mono">
                {ci.total_shares_issued.toLocaleString()}주
              </span>
            )
          }
        />
        <FieldRow
          label="1주 금액"
          value={
            ci.par_value_per_share != null && (
              <span className="font-mono">
                {ci.par_value_per_share.toLocaleString()}원
              </span>
            )
          }
        />
        <FieldRow
          label="보통주"
          value={
            ci.common_shares != null && (
              <span className="font-mono">
                {ci.common_shares.toLocaleString()}주
              </span>
            )
          }
        />
        <FieldRow
          label="종류주"
          value={
            ci.preferred_shares != null && (
              <span className="font-mono">
                {ci.preferred_shares.toLocaleString()}주
              </span>
            )
          }
        />
      </dl>
    </div>
  );
}

function DirectorBadge({ position }: { position: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amic-50 text-amic-600 shrink-0">
      {position}
    </span>
  );
}

function DirectorsSection({ directors }: { directors: CorporateDirector[] }) {
  const sorted = sortDirectorsByPosition(directors);
  if (sorted.length === 0) return null;

  return (
    <div className="border-t border-gray-border pt-4">
      <h4 className="text-xs font-semibold text-text-secondary uppercase mb-3">
        임원 정보
      </h4>
      <div className="space-y-1.5">
        {sorted.map((d, i) => (
          <div key={i} className="flex items-baseline gap-2 text-sm">
            <DirectorBadge position={d.position} />
            <span className="font-medium">{d.name}</span>
            {d.birth_date && (
              <span className="text-text-muted text-xs">{d.birth_date}</span>
            )}
            {d.appointment_date && (
              <span className="text-text-muted text-xs">
                취임 {d.appointment_date}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function PurposeSection({ purpose }: { purpose: string }) {
  return (
    <div className="border-t border-gray-border pt-4">
      <h4 className="text-xs font-semibold text-text-secondary uppercase mb-3">
        목적사항
      </h4>
      <p className="text-sm text-text-secondary whitespace-pre-line leading-relaxed">
        {purpose}
      </p>
    </div>
  );
}

// ── 사업자등록증 섹션 ──────────────────────────────────────

function BizRegInfoSection({ ci }: { ci: CorporateDocsExtractedData }) {
  return (
    <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5">
      <FieldRow
        label="사업자등록번호"
        value={
          ci.business_registration_number && (
            <span className="font-mono text-xs">
              {ci.business_registration_number}
            </span>
          )
        }
      />
      <FieldRow label="업태" value={ci.business_type} />
    </dl>
  );
}

// ── 카드 헤더 배지 ─────────────────────────────────────────

function BothCompleteActions() {
  return (
    <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
      <CheckCircle2 className="h-3.5 w-3.5" />
      법인등기부/사업자등록증 업로드 완료
    </span>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────

export default function CompanyInfoCard({ txn }: Props) {
  const ci = txn.corporate_info as unknown as CorporateDocsExtractedData | null;
  const [showRegistryUpload, setShowRegistryUpload] = useState(false);
  const [showBizRegUpload, setShowBizRegUpload] = useState(false);

  const hasRegistry = !!(
    ci?.corporate_registration_number ||
    ci?.company_name
  );
  const hasBizReg = !!(ci?.business_registration_number || ci?.business_type);
  const bothComplete = hasRegistry && hasBizReg;

  return (
    <Card
      title="회사 정보"
      headerBar
      variant="accent-left"
      actions={bothComplete ? <BothCompleteActions /> : undefined}
    >
      <div className="space-y-4 p-1">

        {/* ── 법인등기부 섹션 ── */}
        <div>
          <SectionHeader
            title="법인등기부"
            isComplete={hasRegistry}
            docName="법인등기부"
            uploadOpen={showRegistryUpload}
            onUploadToggle={() => setShowRegistryUpload((v) => !v)}
          />
          {hasRegistry && ci ? (
            <div className="space-y-4">
              <RegistryBasicInfoSection ci={ci} />
              <CapitalSection ci={ci} />
              <DirectorsSection directors={ci.directors ?? []} />
              {ci.corporate_purpose && (
                <PurposeSection purpose={ci.corporate_purpose} />
              )}
            </div>
          ) : (
            showRegistryUpload && (
              <div className="mt-3">
                <EngagementDocUpload
                  txnId={txn.id}
                  docCategoryHint="CORPORATE_DOCS"
                />
              </div>
            )
          )}
        </div>

        {/* ── 구분선 ── */}
        <hr className="border-gray-border" />

        {/* ── 사업자등록증 섹션 ── */}
        <div>
          <SectionHeader
            title="사업자등록증"
            isComplete={hasBizReg}
            docName="사업자등록증"
            uploadOpen={showBizRegUpload}
            onUploadToggle={() => setShowBizRegUpload((v) => !v)}
          />
          {hasBizReg && ci ? (
            <div className="mt-3">
              <BizRegInfoSection ci={ci} />
            </div>
          ) : (
            showBizRegUpload && (
              <div className="mt-3">
                <EngagementDocUpload
                  txnId={txn.id}
                  docCategoryHint="CORPORATE_DOCS"
                />
              </div>
            )
          )}
        </div>

      </div>
    </Card>
  );
}
```

**Step 1: tsc 확인**

```bash
cd amic-platform && npx tsc --noEmit 2>&1 | head -30
```
Expected: 0 errors

**Step 2: Commit**

```bash
git add amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx
git commit -m "feat(ma/overview): 회사 정보 카드 법인등기부/사업자등록증 섹션 분리"
```

---

## Task 3: `TransactionOverviewTab.tsx` — 외부 조건부 렌더링 제거

**Files:**
- Modify: `amic-platform/src/modules/ma/components/overview/TransactionOverviewTab.tsx:476-483`

**Step 1: 변경 (라인 476-483)**

```tsx
// 변경 전
{txn.corporate_info ? (
  <CompanyInfoCard txn={txn} />
) : (
  <Card title="회사 정보" headerBar>
    <EngagementDocUpload txnId={id} docCategoryHint="CORPORATE_DOCS" />
  </Card>
)}

// 변경 후
<CompanyInfoCard txn={txn} />
```

**Step 2: 사용하지 않는 import 정리**

`TransactionOverviewTab.tsx`에서 `EngagementDocUpload`가 이 위치에서만 사용되었는지 확인. 다른 위치에서 사용되지 않으면 import 제거.

```bash
grep -n "EngagementDocUpload" amic-platform/src/modules/ma/components/overview/TransactionOverviewTab.tsx
```

사용처가 이 한 곳뿐이면 import도 제거.

**Step 3: tsc 확인**

```bash
cd amic-platform && npx tsc --noEmit 2>&1 | head -30
```
Expected: 0 errors

**Step 4: Commit**

```bash
git add amic-platform/src/modules/ma/components/overview/TransactionOverviewTab.tsx
git commit -m "refactor(ma/overview): CompanyInfoCard 내부에서 업로드 UI 관리로 이전"
```

---

## Verification

1. `corporate_info = null` 상태: 두 섹션 모두 "업로드하세요" 텍스트 표시, 클릭 시 업로드 UI 펼침 확인
2. 법인등기부 업로드 후: 법인등기부 섹션 ✓ 완료 배지, 사업자등록증 섹션 업로드 텍스트 유지 확인
3. 사업자등록증 추가 업로드 후: 양 섹션 완료 + 카드 헤더 "법인등기부/사업자등록증 업로드 완료" 배지 확인
4. "사업 목적" 레이블이 법인등기부 섹션에 표시되는지 확인
5. VC 매핑(SIMappingPanel)에서 법인등록번호 자동 적용 확인 — 기존 기능 그대로 작동

---

## Critical Files

| 파일 | 변경 |
|------|------|
| `amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx` | 전체 재작성 |
| `amic-platform/src/modules/ma/components/overview/TransactionOverviewTab.tsx` | 라인 476-483 조건부 제거 |
| `amic-platform/src/modules/ma/types/document_extraction.ts:268` | "종목" → "사업 목적" |
