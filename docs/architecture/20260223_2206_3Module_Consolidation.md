# FDD/IM → Deal Document Studio 통합 — 최상위 3모듈 체계 전환

> 작성: 2026-02-23 22:06:00

## 개요

최상위 모듈을 4개에서 3개로 축소하여 플랫폼 구조를 단순화했습니다.

| Before (4모듈) | After (3모듈) |
|----------------|---------------|
| Auto FDD (`/fdd`) | **M&A Deals** (`/ma`) |
| KIIS (`/kiis`) | **Deal Doc Studio** (`/docs`) — FDD + IM 포함 |
| Deal Doc Studio (`/docs`) | **KIIS** (`/kiis`) |
| M&A Deals (`/ma`) | |

## 방침: 라우트 유지 + UI 통합

- `/fdd/*` 라우트는 그대로 유지 (FDD 워크스페이스의 11개 서브라우트 + `useParams` 패턴 보존)
- UI 레이어(ModuleSwitcher, Sidebar, Dashboard)에서만 FDD를 "Deal Doc Studio" 하위로 표시
- `/im/*` → `/docs` 리다이렉트는 기존 유지

## 변경 파일 (14개)

### 핵심 변경 (8개)

| 파일 | 변경 내용 |
|------|----------|
| `src/components/layout/ModuleSwitcher.tsx` | MODULES 4→3개, `getCurrentModule()`에서 `/fdd`→Deal Doc Studio 매핑 |
| `src/components/layout/Sidebar.tsx` | `isDocs` 조건에 `isFdd` 추가, FDD 네비게이션을 Docs 블록 내부로 재구성 |
| `src/pages/DashboardPage.tsx` | 모듈 카드 4→3개 (M&A, Deal Doc Studio, KIIS), Quick Actions 조정 |
| `src/pages/__tests__/DashboardPage.test.tsx` | assertion을 3모듈 체계에 맞게 업데이트 |
| `src/pages/settings/ProfilePage.tsx` | MODULE_OPTIONS: Dashboard, M&A Deals, Deal Doc Studio, KIIS |
| `src/types/settings.ts` | `defaultModule` 타입: `"/" \| "/ma/transactions" \| "/docs" \| "/kiis"` |
| `src/hooks/useDashboard.ts` | Health 라벨: "FDD Engine", "IM Engine" (4개 서비스 체크 유지) |
| `src/modules/fdd/pages/DealListPage.tsx` + `DealSetupWizard.tsx` | 버그 수정: `/deals/${id}` → `/fdd/deals/${id}` |

### 레거시 문자열 정리 (6개)

| 파일 | 변경 내용 |
|------|----------|
| `src/components/analytics/ModuleKpiSection.tsx` | "Auto FDD" → "FDD", "IM Generator" → "IM" |
| `src/pages/help/HelpPage.tsx` | 3모듈 설명 (Deal Doc Studio, KIIS, M&A Deals) |
| `e2e/pages/sidebar.page.ts` | `switchModule()` 파라미터를 `"ma" \| "docs" \| "kiis"`로 변경 |
| `e2e/pages/analytics.page.ts` | heading selector "FDD", "IM"으로 업데이트 |
| `e2e/tests/analytics-deep.spec.ts` | "FDD" heading 참조 |
| `e2e/tests/dashboard.spec.ts` | "Deal Doc Studio" 카드 클릭, "New Document" quick action |

## 변경하지 않은 파일

- `App.tsx` — `/fdd/*` 라우트 유지
- `FddRoutes.tsx` — FDD 내부 라우트 구조 유지
- `DocsRoutes.tsx` — 이미 `/docs/new?type=fdd` 지원
- `StudioHomePage.tsx` — 이미 FDD Deals 테이블 통합
- 백엔드 4개 마이크로서비스 — 독립 구조 유지

## Sidebar 네비게이션 흐름

```
Deal Doc Studio 선택 시:
├── Documents          (/docs)
├── New Document       (/docs/new)
├── Templates          (/docs/templates)
└── FDD (collapsible)
    └── Deals          (/fdd/deals)

FDD 워크스페이스 진입 시 (/fdd/deals/:dealId):
├── Documents / New Document / Templates (위와 동일)
├── FDD > Deals
├── Workflow > Overview
├── Setup > Deal Setup, VDR, Uploads
├── Analysis > Definitions, Mapping, QoE, NWC, Net Debt, Issues
└── Report > Report
```

## 코드 리뷰 결과

- **허위 양성 1건 기각**: `isDocs = ... || isFdd` 로직은 FDD를 Deal Doc Studio 하위로 통합하기 위한 의도된 동작
- **실제 이슈**: 없음
- **FDD 내부 버그 2건 수정**: `navigate('/deals/${id}')` → `navigate('/fdd/deals/${id}')`

## 검증

- `tsc --noEmit` — 타입 에러 없음 ✅
- `vitest run` — 98/98 통과 ✅
