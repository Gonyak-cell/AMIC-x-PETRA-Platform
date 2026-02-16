# Frontend Phase 5-6 Implementation Plan
# 차트 컴포넌트 + 모바일/접근성

> **Version**: 1.0
> **Created**: 2026년 02월 08일 23시 39분 22초
> **Status**: Planning
> **Related**: [frontend-redesign-amic-style.md](frontend-redesign-amic-style.md)

---

## Overview

| Phase | 범위 | 예상 기간 |
|-------|------|-----------|
| **Phase 5** | Recharts 기반 차트 컴포넌트 (FinancialBarChart, TrendLineChart, WaterfallChart) | 3일 |
| **Phase 6** | 반응형 모바일 사이드바, 스켈레톤 로딩, 접근성 개선 | 2일 |

---

## Phase 5: Chart Components (Recharts 3.7.0)

### 5.1 파일 구조

```
frontend/src/components/charts/
├── chartColors.ts           # AMIC 컬러 상수
├── ChartTooltip.tsx         # 공통 툴팁 컴포넌트
├── FinancialBarChart.tsx    # 카테고리 비교 (QoE 조정항목, Peg 시나리오)
├── TrendLineChart.tsx       # 시계열 데이터 (NWC 월별 추이)
├── WaterfallChart.tsx       # 브릿지 분석 (EBITDA, Net Debt)
└── index.ts                 # Barrel export
```

### 5.2 컬러 팔레트 (chartColors.ts)

```typescript
export const CHART_COLORS = {
  // Primary
  primary: "#0F3A32",        // amic (dark teal)
  primaryLight: "#0B2D27",   // amic-700

  // Semantic (Waterfall)
  positive: "#26C260",       // 증가, add-back (accent green)
  negative: "#BC2C1A",       // 감소, deduction (red)
  caution: "#EF6C00",        // 경고, pending (amber)

  // Waterfall Specific
  waterfallTotal: "#0F3A32",       // 시작/종료 합계
  waterfallIncrease: "#26C260",    // Add-backs
  waterfallDecrease: "#BC2C1A",    // Deductions
  waterfallIntermediate: "#F4F6F8", // 중간 소계

  // Grid & Axis
  gridColor: "#E0E0E0",      // gray-border
  axisColor: "#777777",      // text-secondary

  // Tooltip
  tooltipBg: "#FFFFFF",
  tooltipBorder: "#E0E0E0",
} as const;

// 다중 카테고리용 색상 배열
export const CATEGORY_COLORS = [
  "#0F3A32", // amic
  "#26C260", // accent
  "#0091DA", // info blue
  "#EF6C00", // caution
  "#777777", // secondary
] as const;
```

### 5.3 FinancialBarChart

#### 용도
- QoE 조정 카테고리별 합계 비교
- Peg 시나리오 비교 (6가지 방법: LTM Average, TTM, Last Month, Max, Min, Custom)
- 일반적인 카테고리 비교 차트

#### Interface

```typescript
export interface BarChartDataPoint {
  name: string;           // 카테고리 라벨
  value: number;          // 숫자 값 (Decimal 문자열에서 변환)
  displayValue?: string;  // 포맷된 표시 값
  fill?: string;          // 커스텀 색상 (선택)
}

export interface FinancialBarChartProps {
  data: BarChartDataPoint[];
  height?: number;                                    // 기본값: 300
  showGrid?: boolean;                                 // 기본값: true
  showLegend?: boolean;                               // 기본값: false
  currency?: string;                                  // 기본값: "KRW"
  colorScheme?: "default" | "positive-negative" | "categorical";
  orientation?: "vertical" | "horizontal";            // 기본값: "vertical"
  barSize?: number;                                   // 기본값: 40
  animate?: boolean;                                  // 기본값: true
  className?: string;
  "aria-label"?: string;
}
```

#### 주요 기능
- 양수/음수에 따른 자동 색상 적용 (`positive-negative` 모드)
- `formatCompact()` 사용한 축 라벨 (1M, 1B 형태)
- IBM Plex Mono 폰트로 숫자 표시
- ResponsiveContainer로 반응형 지원

### 5.4 TrendLineChart

#### 용도
- NWC 월별 추이 시각화 (`monthly_trend` 데이터)
- Current Assets, Current Liabilities, NWC 다중 라인

#### Interface

```typescript
export interface TrendDataPoint {
  period: string;           // 기간 (예: "2025-01", "2025-02")
  value: number;            // 주요 메트릭 값
  displayValue?: string;    // 포맷된 표시 값
  secondary?: number;       // 보조 라인 값 (선택)
  secondaryDisplay?: string;
}

export interface TrendLineChartProps {
  data: TrendDataPoint[];
  height?: number;                  // 기본값: 300
  showGrid?: boolean;               // 기본값: true
  showDots?: boolean;               // 기본값: true
  showArea?: boolean;               // 기본값: false (영역 채우기)
  currency?: string;                // 기본값: "KRW"
  target?: number;                  // 목표선 (선택)
  targetLabel?: string;             // 목표선 라벨
  lineColor?: string;               // 주요 라인 색상
  secondaryLineColor?: string;      // 보조 라인 색상
  animate?: boolean;                // 기본값: true
  className?: string;
  "aria-label"?: string;
}
```

#### 주요 기능
- Reference line으로 목표 NWC 표시
- 다중 라인 지원 (주요 + 보조)
- 영역 채우기 옵션 (`showArea`)
- `formatDate()` 사용한 월별 라벨

### 5.5 WaterfallChart (가장 복잡)

#### 용도
- EBITDA Bridge: Reported EBITDA → Adjustments → Adjusted EBITDA
- Net Debt Bridge: Gross Debt → Cash → Net Debt → Debt-Like → Adjusted Net Debt

#### Interface

```typescript
export type WaterfallItemType = "start" | "increase" | "decrease" | "subtotal" | "total";

export interface WaterfallDataPoint {
  name: string;               // 라벨 (예: "Reported EBITDA")
  value: number;              // 금액
  displayValue?: string;      // 포맷된 표시 값
  type: WaterfallItemType;    // 항목 유형
}

export interface WaterfallChartProps {
  data: WaterfallDataPoint[];
  height?: number;              // 기본값: 400
  showGrid?: boolean;           // 기본값: true
  showConnectors?: boolean;     // 연결선 표시 (기본값: true)
  currency?: string;            // 기본값: "KRW"
  barWidth?: number;            // 기본값: 60
  animate?: boolean;            // 기본값: true
  className?: string;
  "aria-label"?: string;
}
```

#### 구현 패턴: Stacked Bar + Invisible Base

Recharts는 네이티브 워터폴 차트를 지원하지 않으므로, **스택 바 + 투명 베이스** 패턴 사용:

```typescript
interface ProcessedWaterfallData {
  name: string;
  invisibleBase: number;    // 투명 바 (위치 조정용)
  visibleValue: number;     // 실제 보이는 바
  originalValue: number;    // 원본 값 (툴팁용)
  displayValue: string;
  type: WaterfallItemType;
}

function processWaterfallData(data: WaterfallDataPoint[]): ProcessedWaterfallData[] {
  let runningTotal = 0;

  return data.map((item) => {
    const processed = { /* ... */ };

    switch (item.type) {
      case "start":
        processed.invisibleBase = 0;
        processed.visibleValue = item.value;
        runningTotal = item.value;
        break;
      case "increase":
        processed.invisibleBase = runningTotal;  // 이전 합계 위에 쌓기
        processed.visibleValue = item.value;
        runningTotal += item.value;
        break;
      case "decrease":
        processed.invisibleBase = runningTotal - Math.abs(item.value);
        processed.visibleValue = Math.abs(item.value);
        runningTotal -= Math.abs(item.value);
        break;
      case "subtotal":
      case "total":
        processed.invisibleBase = 0;
        processed.visibleValue = runningTotal;
        break;
    }

    return processed;
  });
}
```

### 5.6 페이지 통합

| 페이지 | 차트 유형 | 데이터 소스 | 변환 함수 |
|--------|-----------|-------------|-----------|
| **QoEPage** | WaterfallChart | `QoECalculationRead` | `transformQoEToWaterfall()` |
| **QoEPage** | FinancialBarChart | `category_breakdown` | `transformAdjustmentsByCategory()` |
| **NWCPage** | TrendLineChart | `monthly_trend` | `transformMonthlyTrend()` |
| **NWCPage** | FinancialBarChart | Peg scenarios | `transformPegScenarios()` |
| **NetDebtPage** | WaterfallChart | `NetDebtBridgeSummary` | `transformNetDebtToWaterfall()` |

#### 데이터 변환 예시 (QoEPage)

```typescript
// QoE → Waterfall 변환
function transformQoEToWaterfall(qoe: QoECalculationRead): WaterfallDataPoint[] {
  const approvedAdjs = qoe.adjustments.filter((a) => a.status === "APPROVED");

  return [
    { name: "Reported EBITDA", value: Number(qoe.reported_ebitda), type: "start" },
    ...approvedAdjs.map((adj) => ({
      name: adj.description.slice(0, 15),
      value: Number(adj.amount),
      type: (Number(adj.amount) >= 0 ? "increase" : "decrease") as WaterfallItemType,
    })),
    { name: "Adjusted EBITDA", value: Number(qoe.adjusted_ebitda), type: "total" },
  ];
}

// 카테고리별 조정 합계
function transformAdjustmentsByCategory(qoe: QoECalculationRead): BarChartDataPoint[] {
  const categoryTotals: Record<string, number> = {};
  qoe.adjustments
    .filter((a) => a.status === "APPROVED")
    .forEach((adj) => {
      categoryTotals[adj.category] = (categoryTotals[adj.category] || 0) + Number(adj.amount);
    });

  return Object.entries(categoryTotals).map(([category, total]) => ({
    name: CATEGORY_LABELS[category as AdjustmentCategory],
    value: total,
  }));
}
```

### 5.7 ChartTooltip 컴포넌트

```typescript
interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: Record<string, unknown> }>;
  label?: string;
  currency?: string;
}

export function ChartTooltip({ active, payload, label, currency = "KRW" }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-white border border-gray-border rounded-lg shadow-card p-3">
      <p className="text-text-dark font-medium text-sm mb-1">{label}</p>
      {payload.map((entry, index) => (
        <p key={index} className="font-mono text-sm text-text-body">
          {entry.payload.displayValue || formatAmount(entry.value, currency)}
        </p>
      ))}
    </div>
  );
}
```

---

## Phase 6: Mobile + Skeleton + Accessibility

### 6.1 파일 변경/생성 목록

```
frontend/src/components/layout/
├── AppShell.tsx             # 수정: 모바일 상태 관리, skip navigation, context
├── Sidebar.tsx              # 수정: drawer mode, ARIA 속성
├── SidebarNavItem.tsx       # 수정: aria-current="page"
├── MobileMenuButton.tsx     # 신규: 햄버거/X 토글 버튼
└── SidebarOverlay.tsx       # 신규: 반투명 오버레이 백드롭

frontend/src/components/ui/
├── Skeleton.tsx             # 확장: PageSkeleton, ChartSkeleton, KpiCardSkeleton
└── LiveRegion.tsx           # 신규: 스크린 리더 동적 알림
```

### 6.2 반응형 모바일 사이드바

#### 브레이크포인트 전략

| 뷰포트 | 사이드바 동작 |
|--------|---------------|
| **Desktop** (≥768px) | 고정 w-64 사이드바, 항상 표시 |
| **Mobile** (<768px) | 숨김, 햄버거 메뉴로 drawer 오픈 |

#### AppShell Context

```typescript
export interface AppShellContextValue {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  isMobile: boolean;
}

const AppShellContext = createContext<AppShellContextValue | null>(null);

export function useAppShell() {
  const context = useContext(AppShellContext);
  if (!context) throw new Error("useAppShell must be used within AppShell");
  return context;
}
```

#### AppShell 주요 로직

```typescript
export default function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // 768px 브레이크포인트 감지
  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const handleChange = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      if (!e.matches) setSidebarOpen(false); // 데스크탑 전환 시 닫기
    };

    setIsMobile(mediaQuery.matches);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  // ESC 키로 사이드바 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && sidebarOpen) setSidebarOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [sidebarOpen]);

  // 모바일 사이드바 열릴 때 body 스크롤 잠금
  useEffect(() => {
    if (isMobile && sidebarOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [isMobile, sidebarOpen]);

  return (
    <AppShellContext.Provider value={{ sidebarOpen, setSidebarOpen, isMobile }}>
      {/* Skip Navigation */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100]
                   focus:bg-amic focus:text-white focus:px-4 focus:py-2 focus:rounded-lg"
      >
        Skip to main content
      </a>

      <div className="flex min-h-screen">
        {/* Desktop Sidebar */}
        <div className="hidden md:block">
          <Sidebar />
        </div>

        {/* Mobile Sidebar (Drawer) */}
        {isMobile && (
          <>
            <SidebarOverlay isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
            <div
              className={cn(
                "fixed inset-y-0 left-0 z-50 transform transition-transform duration-300",
                sidebarOpen ? "translate-x-0" : "-translate-x-full"
              )}
            >
              <Sidebar onNavItemClick={() => setSidebarOpen(false)} />
            </div>
          </>
        )}

        {/* Main Content */}
        <main id="main-content" className="flex-1 bg-bg-cool">
          {/* Mobile Header */}
          {isMobile && (
            <div className="sticky top-0 z-40 flex items-center gap-4 bg-amic px-4 py-3">
              <MobileMenuButton
                isOpen={sidebarOpen}
                onClick={() => setSidebarOpen(!sidebarOpen)}
              />
              <span className="text-white font-heading font-semibold">Auto FDD</span>
            </div>
          )}
          <div className="max-w-7xl mx-auto px-4 py-4 md:px-6 md:py-6">
            {children}
          </div>
        </main>
      </div>
    </AppShellContext.Provider>
  );
}
```

#### MobileMenuButton 컴포넌트

```typescript
export interface MobileMenuButtonProps {
  isOpen: boolean;
  onClick: () => void;
  className?: string;
}

export function MobileMenuButton({ isOpen, onClick, className }: MobileMenuButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "p-2 rounded-lg text-white hover:bg-white/10 transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-white/50",
        className
      )}
      aria-expanded={isOpen}
      aria-controls="mobile-sidebar"
      aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
    >
      {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
    </button>
  );
}
```

#### SidebarOverlay 컴포넌트

```typescript
export interface SidebarOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SidebarOverlay({ isOpen, onClose }: SidebarOverlayProps) {
  return (
    <div
      className={cn(
        "fixed inset-0 z-40 bg-black/50 transition-opacity duration-300",
        isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
      )}
      onClick={onClose}
      aria-hidden="true"
    />
  );
}
```

### 6.3 스켈레톤 로딩 확장

#### PageSkeleton (전체 페이지 로딩)

```typescript
export function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" role="status" aria-label="Loading page content">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-lg border border-gray-border p-5">
        <Skeleton className="h-6 w-1/4 mb-4" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      </div>

      <span className="sr-only">Loading...</span>
    </div>
  );
}
```

#### ChartSkeleton (차트 로딩)

```typescript
export interface ChartSkeletonProps {
  height?: number;
  type?: "bar" | "line" | "waterfall";
}

export function ChartSkeleton({ height = 300, type = "bar" }: ChartSkeletonProps) {
  return (
    <div
      className="bg-white rounded-lg border border-gray-border p-5 animate-pulse"
      role="status"
      aria-label="Loading chart"
    >
      <Skeleton className="h-5 w-32 mb-4" />
      <div className="relative" style={{ height: `${height}px` }}>
        {/* Y-axis */}
        <div className="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-3 w-8" />)}
        </div>

        {/* Chart area */}
        <div className="ml-14 h-full flex items-end gap-2 pb-6">
          {type === "bar" || type === "waterfall"
            ? [...Array(6)].map((_, i) => (
                <div key={i} className="flex-1 flex flex-col items-center">
                  <Skeleton className="w-full" style={{ height: `${30 + Math.random() * 50}%` }} />
                </div>
              ))
            : <Skeleton className="w-full h-full" />
          }
        </div>
      </div>
      <span className="sr-only">Loading chart...</span>
    </div>
  );
}
```

### 6.4 접근성 개선

#### 접근성 체크리스트

| 항목 | 구현 방법 | 파일 |
|------|-----------|------|
| **Skip Navigation** | `<a href="#main-content">` (sr-only, focus 시 표시) | AppShell.tsx |
| **Sidebar ARIA** | `role="navigation"`, `aria-label="Main navigation"` | Sidebar.tsx |
| **Active Nav** | `aria-current="page"` on NavLink | SidebarNavItem.tsx |
| **Mobile Menu** | `aria-expanded`, `aria-controls="mobile-sidebar"` | MobileMenuButton.tsx |
| **Charts** | `role="img"`, `aria-label` | 모든 차트 컴포넌트 |
| **Focus Trap** | Modal 열릴 때 포커스 이동, 닫힐 때 복귀 | Modal.tsx |
| **Keyboard Nav** | DataTable Arrow/Enter 키 지원 | DataTable.tsx |
| **Live Region** | 동적 콘텐츠 변경 알림 | LiveRegion.tsx |

#### LiveRegion Provider

```typescript
interface LiveRegionContextValue {
  announce: (message: string, assertive?: boolean) => void;
}

export function LiveRegionProvider({ children }: { children: ReactNode }) {
  const [politeMessage, setPoliteMessage] = useState("");
  const [assertiveMessage, setAssertiveMessage] = useState("");

  const announce = useCallback((message: string, assertive = false) => {
    if (assertive) {
      setAssertiveMessage("");
      setTimeout(() => setAssertiveMessage(message), 100);
    } else {
      setPoliteMessage("");
      setTimeout(() => setPoliteMessage(message), 100);
    }
  }, []);

  return (
    <LiveRegionContext.Provider value={{ announce }}>
      {children}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {politeMessage}
      </div>
      <div aria-live="assertive" aria-atomic="true" className="sr-only">
        {assertiveMessage}
      </div>
    </LiveRegionContext.Provider>
  );
}

// 사용 예시
const announce = useLiveAnnounce();
announce("Adjustment approved successfully");
announce("Error: Failed to save", true); // assertive
```

---

## 구현 순서

### Phase 5 (3일)

| Day | 작업 |
|-----|------|
| **Day 1** | `chartColors.ts`, `ChartTooltip.tsx` 생성 |
| **Day 1-2** | `FinancialBarChart.tsx` 구현 + 테스트 |
| **Day 2** | `TrendLineChart.tsx` 구현 + 테스트 |
| **Day 2-3** | `WaterfallChart.tsx` 구현 (stacked bar 패턴) + 테스트 |
| **Day 3** | `index.ts` barrel export, QoEPage/NWCPage/NetDebtPage 통합 |

### Phase 6 (2일)

| Day | 작업 |
|-----|------|
| **Day 1** | `MobileMenuButton.tsx`, `SidebarOverlay.tsx` 생성 |
| **Day 1** | `AppShell.tsx` 모바일 상태 관리 + skip navigation 추가 |
| **Day 1-2** | `Sidebar.tsx`, `SidebarNavItem.tsx` ARIA 개선 |
| **Day 2** | `Skeleton.tsx` 확장 (PageSkeleton, ChartSkeleton) |
| **Day 2** | `LiveRegion.tsx` 생성, 접근성 E2E 테스트 |

---

## 재사용할 기존 코드

| 유틸리티 | 경로 | 용도 |
|----------|------|------|
| `formatAmount()` | `frontend/src/lib/format.ts` | 차트 툴팁/라벨 금액 포맷 |
| `formatCompact()` | `frontend/src/lib/format.ts` | 축 라벨 (1M, 1B) |
| `formatDate()` | `frontend/src/lib/format.ts` | 월별 라벨 ("month" 포맷) |
| `cn()` | `frontend/src/lib/cn.ts` | 조건부 클래스 조합 |
| `Skeleton` | `frontend/src/components/ui/Skeleton.tsx` | 기존 스켈레톤 확장 |
| `Card` | `frontend/src/components/ui/Card.tsx` | 차트 컨테이너 래퍼 |
| AMIC 컬러 | `frontend/tailwind.config.js` | 차트 색상 (amic, accent, positive, negative) |

---

## 검증 방법

### Phase 5 검증

```bash
# 1. TypeScript 컴파일
cd frontend && npx tsc -b

# 2. Lint 확인
npm run lint

# 3. 개발 서버 실행
npm run dev

# 4. 브라우저에서 시각적 확인
# - /deals/{id}/qoe → EBITDA Waterfall + Category Bar Chart
# - /deals/{id}/nwc → Monthly Trend Line + Peg Scenario Bar Chart
# - /deals/{id}/net-debt → Net Debt Waterfall

# 5. 반응형 확인
# DevTools > 모바일 뷰포트에서 ResponsiveContainer 동작 확인
```

### Phase 6 검증

```bash
# 1. 모바일 반응형 테스트 (Chrome DevTools)
# - 375x667 뷰포트에서 햄버거 메뉴 표시 확인
# - 메뉴 클릭 → drawer 슬라이드 확인
# - ESC 키 / 오버레이 클릭 → 닫기 확인

# 2. 키보드 접근성
# - Tab 키 → skip link 포커스 확인 (첫 번째 탭)
# - Enter → main content로 스크롤
# - 사이드바 nav items 탭 순환 확인

# 3. 스크린 리더 테스트
# NVDA/VoiceOver로:
# - aria-current="page" 읽기 확인
# - 차트 aria-label 읽기 확인
# - LiveRegion 알림 확인

# 4. E2E 접근성 테스트
cd e2e && npx playwright test accessibility.spec.ts mobile-responsive.spec.ts
```

---

## 리스크 완화

| 리스크 | 완화 방법 |
|--------|-----------|
| Recharts 워터폴 복잡성 | 검증된 stacked-bar + invisible base 패턴 사용 |
| 모바일 drawer 애니메이션 성능 | CSS transform 사용 (width 애니메이션 대신) |
| 터치 타겟 크기 미달 | 44px 최소 크기 보장 (WCAG 2.5.5) |
| 포커스 관리 누락 | 모바일 메뉴 닫힐 때 트리거 버튼으로 포커스 복귀 |
| 작은 화면에서 차트 가독성 | ResponsiveContainer + 조건부 축 라벨 포맷팅 |

---

## 주요 파일 경로

| 용도 | 경로 |
|------|------|
| 레이아웃 | `frontend/src/components/layout/AppShell.tsx` |
| 사이드바 | `frontend/src/components/layout/Sidebar.tsx` |
| 스켈레톤 | `frontend/src/components/ui/Skeleton.tsx` |
| QoE 페이지 | `frontend/src/pages/QoEPage.tsx` |
| NWC 페이지 | `frontend/src/pages/NWCPage.tsx` |
| Net Debt 페이지 | `frontend/src/pages/NetDebtPage.tsx` |
| 포맷 유틸 | `frontend/src/lib/format.ts` |
| Tailwind 설정 | `frontend/tailwind.config.js` |
