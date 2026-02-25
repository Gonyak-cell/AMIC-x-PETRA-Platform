# MOU 파이프라인 독립 그룹 이동

> **작성일**: 2026-02-24 16:21:00
> **분류**: UI 개선
> **브랜치**: `feat/ma-workflow`

## 변경 사유

M&A 워크플로우상 MOU(양해각서)는 마케팅 단계 종료 후, DD(실사) 시작 전에 체결되는 문서다. 기존에는 "계약/협상 → 법률문서" 하위에 SPA/SHA/BTA/SSA와 함께 묶여 있었으나, 워크플로우 순서에 맞게 마케팅과 DD 사이에 독립 그룹으로 배치했다.

## 변경 파일

### 1. `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx`

| 항목 | 내용 |
|------|------|
| `Handshake` 아이콘 import | lucide-react에서 추가 |
| `useLegalDocuments` 훅 import | MOU 연결 상태 확인용 |
| `useLegalDocuments(id)` 호출 | 데이터 로드 섹션에 추가 |
| `svcGroups` 배열 | MARKETING과 BIDDING_DD 사이에 MOU 그룹 삽입 |

**MOU 그룹 구조**:
```typescript
{
  key: "MOU", phase: "MARKETING", label: "MOU",
  items: [{
    key: "mou", label: "양해각서 (MOU)", icon: Handshake,
    tab: "contracts",
    connected: !!(legalDocs?.some((d) => d.doc_type === "MOU")),
    createUrl: `/docs/legal/new?txn_id=${id}&type=MOU&return_url=...`,
  }],
}
```

- `phase: "MARKETING"` → BIDDING_DD 진입 시 "과거"(체크마크)로 표시
- `connected` → legalDocs에서 MOU 문서 존재 여부로 판별
- `createUrl` → `?type=MOU`로 타입 피커 건너뛰고 MOU 파라미터 폼 직접 진입

### 2. `amic-platform/src/modules/docs/components/LegalDocumentsTab.tsx`

- subtitle: `"SPA, SHA, BTA, SSA, MOU 생성 및 다운로드"` → `"SPA, SHA, BTA, SSA 생성 및 다운로드"`
- 빠른 생성 버튼 배열: MOU 제거 → `["SPA", "SHA", "BTA", "SSA"]`
- 빈 상태 문구: `"SPA, MOU 등"` → `"SPA, SHA 등"`
- `DOC_TYPE_BADGE`의 MOU 항목은 유지 (기존 MOU 문서 테이블 렌더링용)

### 3. `amic-platform/src/modules/docs/components/LegalDocTypePicker.tsx`

- types 배열: `["SPA", "SHA", "BTA", "SSA", "MOU"]` → `["SPA", "SHA", "BTA", "SSA"]`
- ICONS/COLORS/BG_SELECTED의 MOU 항목은 유지 (타입 안전성)

## 변경하지 않은 항목

- **백엔드** (deal-mgmt): LegalDocType enum, 모델, API 변경 없음
- **legal_document.ts**: LegalDocType에 MOU 유지, LEGAL_DOC_META 유지
- **CreateLegalDocumentPage.tsx**: `?type=MOU` URL 파라미터 처리 기존 구현 활용
- **LegalParamsForm.tsx**: MOUForm 컴포넌트 유지

## 서비스 연동 사이드바 (변경 후)

```
준비      (0/2) → [KIIS 기업 인텔리전스, NDA]
마케팅    (0/3) → [TM, DM, IM]
MOU       (0/1) → [양해각서 (MOU)]        ← 신규
DD        (0/3) → [FDD, LDD, TDD]
계약/협상 (0/1) → [법률 문서 (SPA/SHA/BTA/SSA)]
Closing
```

## 검증

- `npx tsc --noEmit` 통과 (타입 에러 없음)
