# Cross-Module Analytics 페이지 — MA 모듈 추가 및 에러 핸들링 개선

> 작성: 2026-02-25 10:35

## 배경

Cross-Module Analytics 페이지(`/analytics`)가 FDD, KIIS, IM 3개 모듈만 표시하고 있었으며, 플랫폼의 핵심 모듈인 **MA가 완전히 누락**되어 있었다. IM 백엔드가 다운된 상태에서 500 에러 메시지가 표시되고, 모듈 건강 체크 없이 바로 API를 호출하여 다운된 백엔드에 불필요한 타임아웃 대기가 발생하는 문제도 있었다.

## 변경 사항

### 수정 파일 6개

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/types/analytics.ts` | `MaAnalytics` 타입 추가, `AnalyticsModule`에 `"ma"` 추가, `AnalyticsKpis`에 `ma` 필드 추가 |
| `amic-platform/src/hooks/useAnalytics.ts` | MA `/dashboard/stats` 쿼리 추가, 시계열 `/transactions` 페이지네이션 쿼리 추가, `useModuleHealth` 건강 체크 연동 |
| `amic-platform/src/components/analytics/AnalyticsFilterBar.tsx` | MODULES 배열에 M&A 탭 추가 (첫 번째 위치) |
| `amic-platform/src/components/analytics/ModuleKpiSection.tsx` | MA KPI 카드 4개 추가 (Total Transactions, Active Deals, Deal Value, Recent Activity) |
| `amic-platform/src/components/analytics/AnalyticsChartPanel.tsx` | MA 차트 2개 추가 (월별 거래 추이, 단계별 분포) |
| `amic-platform/src/pages/analytics/AnalyticsPage.tsx` | MA 데이터 연결, subtitle 업데이트, `useModuleHealth` 연동 |

### 기능 추가 상세

#### 1. MA KPI 카드 (ModuleKpiSection)
- **Total Transactions** — Handshake 아이콘
- **Active Deals** — TrendingUp, variant="positive"
- **Total Deal Value** — DollarSign, variant="caution", ₩십억 단위 포맷
- **Recent Activity (7d)** — Activity 아이콘

#### 2. MA 차트 (AnalyticsChartPanel)
- **M&A Transactions Created (Monthly)** — TrendLineChart
- **M&A Transactions by Phase** — FinancialBarChart

#### 3. 에러 핸들링 개선
- `useModuleHealth()` 결과를 `useAnalyticsKpis`와 `useAnalyticsTimeSeries`에 전달
- `isModuleUp()` 헬퍼로 다운된 모듈은 쿼리 자체를 스킵 (`enabled: false`)
- 기존: 다운된 백엔드에 5초 타임아웃 대기 → 개선: 즉시 에러 박스 표시

#### 4. 시계열 페이지네이션
- 백엔드 `/transactions` limit 최대 100건 제한 발견
- 프론트엔드에서 100건씩 페이지네이션 병렬 요청 (최대 1000건)

### 필터 탭 순서
```
All Modules → M&A → FDD → KIIS → IM
```

### 재사용한 기존 리소스
- `maApi` 클라이언트 (`amic-platform/src/api/maClient.ts`)
- MA `/dashboard/stats` API (`deal-mgmt/app/routers/dashboard.py`)
- `useModuleHealth` 훅 (`amic-platform/src/hooks/useDashboard.ts`)
- `KpiCard`, `TrendLineChart`, `FinancialBarChart` 컴포넌트

## 코드 리뷰 결과

### 프론트엔드 ↔ 백엔드 스키마 교차 검증

| 프론트엔드 (`MaDashboardStatsResponse`) | 백엔드 (`DashboardStats`) | 일치 |
|----------------------------------------|--------------------------|------|
| `total_transactions: number` | `total_transactions: int` | ✅ |
| `active_transactions: number` | `active_transactions: int` | ✅ |
| `total_deal_value: number \| null` | `total_deal_value: float \| None` | ✅ |
| `by_phase: Array<{phase, count, total_value}>` | `by_phase: list[PhaseSummary]` | ✅ |
| `by_status: Record<string, number>` | `by_status: dict[str, int]` | ✅ |
| `by_side: Record<string, number>` | `by_side: dict[str, int]` | ✅ |
| `recent_activity_count: number` | `recent_activity_count: int` | ✅ |

**7/7 필드 완전 일치.**

### 검증 결과

| 항목 | 결과 |
|------|------|
| `tsc --noEmit` | ✅ 통과 |
| `vite build` | ✅ 12.43s 통과 |
| 기존 코드 무파괴 | ✅ DashboardPage 영향 없음 |
| 허위 리뷰 | 없음 |

## 추가 변경 (같은 세션)

- `TransactionWorkspacePage.tsx:2718` — `+ IM` → `+ Information (IM)` 버튼 텍스트 수정 (Teaser (TM), Discussion (DM)과 동일 형식 통일)
