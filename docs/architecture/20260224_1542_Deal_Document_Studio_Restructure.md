# Deal Document Studio 체계 재구성

> **작성일**: 2026-02-24 15:42
> **브랜치**: `feat/ma-workflow`
> **상태**: ✅ 완료 (tsc + vite build 통과)

---

## 배경

기존 Deal Document Studio는 5개 카테고리(NDA, Marketing Materials, Legal Documents, Due Diligence, Checklists)로 구성되어 있었으나, 실무 워크플로우에 맞게 4개 카테고리로 재구성함.

- NDA를 독립 카테고리에서 Legal 하위로 이동
- SPA/SHA/BTA/SSA를 "Deal Contracts" 서브타입으로 통합
- Signing Checklist 제거, Deal Checklist & Timeline 추가

---

## 변경 전/후 비교

### Before (5개 카테고리)

```
1. NDA
   ├── Bilateral NDA (coming_soon)
   └── Unilateral NDA (coming_soon)
2. Marketing Materials
   ├── TM (available)
   ├── IM (available)
   └── DM (coming_soon)
3. Legal Documents
   ├── SPA (available)
   ├── SHA (available)
   ├── BTA (available)
   ├── SSA (available)
   └── MOU (available)
4. Due Diligence
   ├── FDD (available)
   ├── LDD (available)
   └── TDD (coming_soon)
5. Checklists
   ├── Closing Checklist (requires_context)
   ├── Signing Checklist (coming_soon)
   └── Deal Timeline (coming_soon)
```

### After (4개 카테고리)

```
1. Marketing
   ├── TM — Teaser Memorandum (available)
   ├── IM — Information Memorandum (available)
   └── DM — Discussion Memorandum (coming_soon)
2. Legal
   ├── NDA — 비밀유지계약 (coming_soon)
   ├── MOU — 양해각서 (available)
   └── Deal Contracts — SPA/SHA/BTA/SSA (available)
3. Due Diligence
   ├── FDD — 재무실사 (available)
   ├── LDD — 법률실사 (available)
   └── TDD — 기술실사 (coming_soon)
4. Checklist & Timeline
   ├── Closing Checklist (requires_context)
   └── Deal Checklist & Timeline (requires_context)
```

---

## 변경 파일

| # | 파일 | 변경 유형 | 설명 |
|---|------|----------|------|
| 1 | `amic-platform/src/modules/docs/types/studio-categories.ts` | **수정** | 5→4 카테고리 재구성 (NDA→Legal 이동, Deal Contracts 통합) |
| 2 | `amic-platform/src/components/layout/Sidebar.tsx` | **수정** | 기존 flat DOCS_NAV 3링크 → Studio Home + Marketing/Legal/Due Diligence/Checklist & Timeline 4개 collapsible 섹션 |
| 3 | `amic-platform/src/modules/docs/pages/CategoryDocumentsPage.tsx` | **신규** | 카테고리별 문서 목록/안내 페이지 (Marketing: 문서 테이블, Legal/DD: 생성 안내, Checklists: 거래 워크스페이스 안내) |
| 4 | `amic-platform/src/modules/docs/DocsRoutes.tsx` | **수정** | `/docs/marketing`, `/docs/legal`, `/docs/dd`, `/docs/checklists` 라우트 추가 |

---

## 사이드바 구조 변경

### Before
```
Deal Document Studio
├── Documents        → /docs
├── New Document     → /docs/new
├── Templates        → /docs/templates
└── [FDD Section]
    └── Deals        → /fdd/deals
```

### After
```
Deal Document Studio
├── Studio Home              → /docs
├── [Marketing Section]
│   ├── Overview             → /docs/marketing
│   ├── TM                   → /docs/new?type=teaser
│   └── IM                   → /docs/new?type=im
├── [Legal Section]
│   ├── Overview             → /docs/legal
│   ├── MOU                  → /docs/legal/new?type=MOU
│   └── Deal Contracts       → /docs/legal/new
├── [Due Diligence Section]
│   ├── Overview             → /docs/dd
│   ├── FDD                  → /fdd/deals
│   └── LDD                  → /docs/ldd/new
├── [FDD Workspace]          (조건부: FDD 딜 내부일 때만 표시)
│   ├── Workflow
│   ├── Setup
│   ├── Analysis
│   └── Report
└── [Checklist & Timeline Section]
    ├── Overview             → /docs/checklists
    ├── Closing Checklist    → /docs/checklists
    └── Deal Timeline        → /docs/checklists
```

---

## 라우팅 변경

| 라우트 | 페이지 | 상태 |
|--------|--------|------|
| `/docs` | StudioHomePage | 기존 유지 (4개 카테고리 카드 자동 반영) |
| `/docs/marketing` | CategoryDocumentsPage (marketing) | **신규** |
| `/docs/legal` | CategoryDocumentsPage (legal) | **신규** |
| `/docs/dd` | CategoryDocumentsPage (due_diligence) | **신규** |
| `/docs/checklists` | CategoryDocumentsPage (checklists) | **신규** |
| `/docs/new` | CreateDocumentPage | 기존 유지 |
| `/docs/legal/new` | CreateLegalDocumentPage | 기존 유지 |
| `/docs/ldd/new` | CreateLDDReportPage | 기존 유지 |
| `/docs/documents/:id` | DocumentDetailPage | 기존 유지 |
| `/docs/templates` | TemplatesPage | 기존 유지 |

---

## 변경하지 않은 항목

- **백엔드**: deal-mgmt, im, fdd, kiis 모든 백엔드 변경 없음
- **기존 Hooks**: useDocuments, useLegalDocuments, useLDDReports 등 변경 없음
- **기존 Create 페이지**: CreateDocumentPage, CreateLegalDocumentPage, CreateLDDReportPage 변경 없음
- **CategoryCard 컴포넌트**: STUDIO_CATEGORIES 참조하므로 자동 반영
- **StudioHomePage**: STUDIO_CATEGORIES를 map하므로 자동으로 4개 카테고리 표시

---

## 검증 결과

- `npx tsc --noEmit` — ✅ 통과 (에러 0)
- `npx vite build` — ✅ 통과 (14.27s)
