# Auto FDD 프론트엔드 디자인 구현 계획서

> **문서 버전**: v1.0
> **작성일**: 2026-02-08
> **프로젝트**: Auto FDD — Financial Due Diligence Automation
> **범위**: 프론트엔드 전면 리디자인 (AMIC 브랜드 스타일 적용)

---

## 1. 개요

### 1.1 현재 상태

Auto FDD 프론트엔드는 React 19 + TypeScript + Vite + Tailwind CSS로 구축된 MVP 수준의 UI이다.

- 기본 blue/gray 색상, 브라우저 기본 폰트 사용
- 플랫 헤더 내비게이션 + 수평 탭
- 디자인 시스템 없음, 컴포넌트 라이브러리 없음, 아이콘 없음
- 페이지별 중복 코드 (formatAmount, Badge, STATUS_COLORS 등)
- 11개 페이지, 35개 소스 파일

### 1.2 목표

AMIC 법무법인(법무법인 아믹 & PetraBridge Partners)의 브랜드 디자인 시스템을 적용하여,
**Big 4 / IB 수준의 전문적인 FDD 분석 도구** 느낌의 UI로 전면 리디자인한다.

### 1.3 디자인 레퍼런스

- **출처**: `IM Module/auto-im-generator/src/design_renderer/design_tokens.py`
- **브랜드**: AMIC Law & PetraBridge Partners
- **비주얼 톤**: 다크그린 기반, 금융 전문가용, 데이터 중심

---

## 2. AMIC 디자인 시스템 정의

### 2.1 컬러 팔레트

| 토큰             | HEX       | 용도                             |
| ---------------- | --------- | -------------------------------- |
| **Primary**      | `#0F3A32` | 사이드바, 헤더, 테이블 헤더, 제목 |
| **Accent**       | `#26C260` | CTA 버튼, 긍정 지표, 강조        |
| Text Body        | `#3D3D3D` | 본문 텍스트                       |
| Text Dark        | `#212121` | 진한 텍스트, 제목                 |
| Text Secondary   | `#777777` | 캡션, 부가 정보                   |
| Text White       | `#FFFFFF` | 다크 배경 위 텍스트               |
| BG White         | `#FFFFFF` | 카드, 메인 배경                   |
| BG Light Green   | `#E8F5E9` | 라이트 강조 배경                  |
| BG Lighter Green | `#F1F8E9` | 더 밝은 배경                      |
| BG Cool Grey     | `#F4F6F8` | 섹션 구분 배경, 페이지 배경       |
| Positive         | `#26C260` | 양수, 승인, 완료                  |
| Negative         | `#BC2C1A` | 음수, 거절, 에러                  |
| Caution          | `#EF6C00` | 주의, 대기                        |
| Table Header     | `#0F3A32` | 테이블 헤더 배경                  |
| Table Alt Row    | `#F4F6F8` | 테이블 짝수행 배경                |
| Gray Border      | `#E0E0E0` | 테두리, 구분선                    |

### 2.2 타이포그래피

| 용도               | 폰트                   | CSS Font Stack                                                        |
| ------------------ | ---------------------- | --------------------------------------------------------------------- |
| **제목 (영문)**     | Inter (weight 600-800) | `'Inter', 'Pretendard', 'Noto Sans KR', sans-serif`                   |
| **본문 (한글/영문)** | Pretendard             | `'Pretendard', 'Inter', 'Noto Sans KR', 'Malgun Gothic', sans-serif` |
| **숫자/KPI**        | IBM Plex Mono          | `'IBM Plex Mono', monospace`                                          |
| **폴백**            | Noto Sans KR           | 특수문자/광범위 한글                                                    |

### 2.3 타입 스케일

| 토큰명          | 크기           | Weight | 용도             |
| --------------- | -------------- | ------ | ---------------- |
| `cover-title`   | 3.3rem (53px)  | 800    | 대형 타이틀       |
| `section-title` | 2.3rem (37px)  | 800    | 섹션 제목         |
| `slide-title`   | 1.3rem (21px)  | 700    | 페이지 제목       |
| `summary`       | 1.2rem (19px)  | 500    | 요약 텍스트       |
| `sub-header`    | 1rem (16px)    | 600    | 섹션 구분 바      |
| `kpi-label`     | 0.94rem (15px) | 500    | KPI 라벨          |
| `kpi-value`     | 1.7rem (27px)  | 600    | KPI 숫자 (Mono)   |
| `body-text`     | 0.81rem (13px) | 400    | 본문              |
| `footnote`      | 0.75rem (12px) | 400    | 각주/출처         |

---

## 3. 기술 스택 변경

### 3.1 신규 패키지

| 패키지         | 버전   | 목적                              | 사이즈        |
| -------------- | ------ | --------------------------------- | ------------- |
| `lucide-react` | latest | 아이콘 라이브러리 (tree-shakeable) | ~작음/아이콘당 |
| `recharts`     | latest | 재무 차트 (bar, line, waterfall)   | ~250KB        |
| `sonner`       | latest | 토스트 알림                        | ~15KB         |

### 3.2 폰트 로딩 전략

CDN 기반 (번들 사이즈 최소화):

```html
<!-- Inter + IBM Plex Mono (Google Fonts) -->
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />

<!-- Pretendard Variable (dynamic subset - 한글 글리프 온디맨드 로딩) -->
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet" />
```

### 3.3 기존 스택 유지

- React 19, React Router v7, TanStack Query v5, Axios — 변경 없음
- Tailwind CSS 3.4 — 확장 설정만 추가
- TypeScript 5.7 strict — 변경 없음

---

## 4. 파일 구조 (신규/변경)

### 4.1 신규 생성 파일 (~25개)

```text
frontend/src/
├── lib/
│   ├── cn.ts                     # className 병합 유틸리티
│   └── format.ts                 # formatAmount, formatPercent, formatDate (중복 제거)
│
├── components/
│   ├── ui/                       # ★ 재사용 UI 컴포넌트 라이브러리
│   │   ├── Button.tsx            # primary / secondary / ghost / danger / accent
│   │   ├── Badge.tsx             # success / warning / error / info / neutral
│   │   ├── Card.tsx              # 카드 래퍼 + 선택적 다크그린 헤더바
│   │   ├── KpiCard.tsx           # KPI 표시 (IBM Plex Mono, 트렌드)
│   │   ├── DataTable.tsx         # 전문 테이블 (다크그린 헤더, 줄무늬)
│   │   ├── Modal.tsx             # 다이얼로그 오버레이
│   │   ├── Input.tsx             # 스타일링된 텍스트 입력
│   │   ├── Select.tsx            # 스타일링된 셀렉트
│   │   ├── SectionHeader.tsx     # 다크그린 섹션 구분 바
│   │   ├── Skeleton.tsx          # 로딩 스켈레톤
│   │   ├── Spinner.tsx           # 로딩 스피너
│   │   ├── Breadcrumbs.tsx       # 네비게이션 경로
│   │   ├── EmptyState.tsx        # 빈 상태 표시
│   │   └── index.ts              # 배럴 익스포트
│   │
│   ├── layout/                   # ★ 레이아웃 컴포넌트 (Phase 2)
│   │   ├── Sidebar.tsx           # 다크그린 사이드바
│   │   ├── SidebarNavItem.tsx    # 사이드바 네비 아이템
│   │   ├── PageHeader.tsx        # 페이지 헤더 (breadcrumbs + actions)
│   │   └── WorkspaceSidebar.tsx  # 딜 워크스페이스 서브 네비
│   │
│   └── charts/                   # ★ 차트 컴포넌트 (Phase 5)
│       ├── FinancialBarChart.tsx  # 매출/이익 바 차트
│       ├── TrendLineChart.tsx    # NWC 월별 트렌드
│       └── WaterfallChart.tsx    # QoE/NetDebt 브리지
```

### 4.2 주요 수정 파일

| 파일                                     | 변경 내용                                                    |
| ---------------------------------------- | ------------------------------------------------------------ |
| `tailwind.config.js`                     | AMIC 디자인 토큰 전체 등록 (colors, fontFamily, fontSize, boxShadow) |
| `index.html`                             | 폰트 CDN 링크 3개 추가, title 변경                            |
| `src/index.css`                          | base layer 폰트 설정, 스크롤바 스타일링                       |
| `src/main.tsx`                           | `<Toaster>` (sonner) 추가                                    |
| `src/components/layout/AppShell.tsx`     | 헤더 → 사이드바 레이아웃 전면 재작성                          |
| `src/pages/DealListPage.tsx`             | KpiCard + DataTable + Modal로 리디자인                        |
| `src/pages/DealWorkspacePage.tsx`        | 수평 탭 → WorkspaceSidebar 전환                               |
| `src/pages/LoginPage.tsx`               | AMIC 브랜딩 좌우 분할 레이아웃                                |
| `src/pages/QoEPage.tsx`                 | DataTable + KpiCard + 차트 적용                               |
| 나머지 6개 페이지                         | 동일 패턴 적용                                                |

---

## 5. UI 컴포넌트 상세 설계

### 5.1 Button

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant: "primary" | "secondary" | "ghost" | "danger" | "accent";
  size?: "sm" | "md" | "lg";
  icon?: LucideIcon;
  iconPosition?: "left" | "right";
  loading?: boolean;
}
```

| Variant   | 배경                     | 텍스트    | Hover       |
| --------- | ------------------------ | --------- | ----------- |
| primary   | `#0F3A32`                | white     | `#0B2D27`   |
| secondary | white + border `#0F3A32` | `#0F3A32` | `#E8F5E9`   |
| ghost     | transparent              | `#777777` | `#F4F6F8`   |
| danger    | `#BC2C1A`                | white     | darker red  |
| accent    | `#26C260`                | white     | `#1FAA52`   |

### 5.2 DataTable

```typescript
interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "center" | "right";
  width?: string;
  render?: (row: T, index: number) => ReactNode;
  mono?: boolean; // IBM Plex Mono (숫자 열)
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: string;
  loading?: boolean;
  emptyMessage?: string;
  striped?: boolean; // 짝수행 bg-table-alt
  compact?: boolean;
  onRowClick?: (row: T) => void;
  sectionHeaders?: { index: number; label: string }[];
  footer?: ReactNode;
}
```

**스타일링 규칙:**

- 헤더행: `bg-table-header text-white font-heading text-sub-header rounded-t`
- 본문: `font-body text-body-text`
- 짝수행: `bg-table-alt` (`#F4F6F8`)
- 숫자 셀: `font-mono tabular-nums text-right`
- 호버: `hover:bg-bg-light-green` (`#E8F5E9`)
- 외곽: `border border-gray-border rounded-lg overflow-hidden`

### 5.3 KpiCard

```typescript
interface KpiCardProps {
  label: string;
  value: string;
  trend?: "up" | "down" | "flat";
  trendValue?: string; // "+5.2%"
  variant?: "default" | "positive" | "negative" | "caution";
  subtitle?: string;
  icon?: LucideIcon;
}
```

**레이아웃:**

```text
+----------------------------------+
| [icon]  label (text-secondary)   |
|                                  |
| value (IBM Plex Mono, 27px)     |
|                                  |
| ↑ +5.2% YoY (trend color)      |
+----------------------------------+
```

### 5.4 Card

```typescript
interface CardProps {
  title?: string;
  headerBar?: boolean; // true → 다크그린 헤더바
  actions?: ReactNode;
  children: ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
}
```

`headerBar=true` 시: 상단에 `bg-amic text-white px-5 py-3` 바 렌더링

### 5.5 Badge

| Variant | 배경       | 텍스트    | 용도                          |
| ------- | ---------- | --------- | ----------------------------- |
| success | `#E8F5E9`  | `#26C260` | ACTIVE, APPROVED, COMPLETED   |
| warning | amber-50   | `#EF6C00` | DRAFT, PENDING, CANDIDATE     |
| error   | red-50     | `#BC2C1A` | FAILED, REJECTED, CRITICAL    |
| info    | blue-50    | blue-700  | 정보성 배지                    |
| neutral | `#F4F6F8`  | `#777777` | ARCHIVED, N/A                 |

### 5.6 SectionHeader

전체 폭 다크그린 바 (페이지 내 섹션 구분):

```text
┌─ bg-amic text-white px-5 py-2.5 rounded-t ─────────┐
│ Section Title                            [Action]    │
└──────────────────────────────────────────────────────┘
```

### 5.7 Modal

```typescript
interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg";
}
```

오버레이 + 중앙 정렬 다이얼로그, 제목에 AMIC 다크그린 강조선

---

## 6. 레이아웃 설계

### 6.1 전체 레이아웃 (Phase 2)

```text
+----------+--------------------------------------------------+
|          | PageHeader                                        |
| Sidebar  | ┌─ Breadcrumbs: Deals > Project Alpha > QoE ─┐   |
| (w-64)   | │                                 [Actions]   │   |
| bg-amic  | └─────────────────────────────────────────────┘   |
|          +--------------------------------------------------+
| [Logo]   |                                                  |
| ───────  |  Main Content Area                               |
| [nav]    |  (bg-bg-cool, max-w-full, p-6)                  |
|  Deals   |                                                  |
|  ─────── |  ┌─ KPI Cards ──────────────────────┐            |
|  딜 서브  |  └─────────────────────────────────────┘          |
|  Overview |                                                  |
|  Defs     |  ┌─ DataTable / Charts ────────────┐            |
|  Upload   |  │                                  │            |
|  Mapping  |  │                                  │            |
|  QoE      |  └──────────────────────────────────┘            |
|  NWC      |                                                  |
|  NetDebt  |                                                  |
|  Issues   |                                                  |
|  Report   |                                                  |
| ───────  |                                                  |
| [User]   |                                                  |
| [Logout] |                                                  |
+----------+--------------------------------------------------+
```

### 6.2 사이드바 상세

```text
+----------------------------------+
| ┌──────────────────────────────┐ |
| │ AMIC 법무법인 아믹             │ |  ← bg-amic, 로고
| │ Auto FDD                     │ |
| └──────────────────────────────┘ |
|                                  |
| ◈ Dashboard                     |  ← Lucide: LayoutDashboard
| ◈ Deals                         |  ← Lucide: Briefcase
|                                  |
| ─── CURRENT DEAL ───            |  ← /deals/:id 진입 시만 표시
| ◈ Overview                      |  ← Lucide: Eye
| ◈ Definitions                   |  ← Lucide: FileText
| ◈ Uploads                       |  ← Lucide: Upload
| ◈ Mapping                       |  ← Lucide: GitMerge
| ◈ QoE Bridge                    |  ← Lucide: TrendingUp
| ◈ Net Working Capital            |  ← Lucide: Wallet
| ◈ Net Debt                      |  ← Lucide: Landmark
| ◈ Issues                        |  ← Lucide: AlertTriangle
| ◈ Report                        |  ← Lucide: FileOutput
|                                  |
| ────────────────────────         |
| [avatar] User Name               |
|          ANALYST                  |  ← Badge
| ◈ Sign Out                      |
+----------------------------------+
```

**활성 링크 스타일**: `bg-white/10` + 좌측 `border-l-2 border-accent`
**모바일**: 화면 < 768px 시 햄버거 토글 → 드로어 오버레이

### 6.3 로그인 페이지 레이아웃

```text
+---------------------------+----------------------------+
|                           |                            |
|   bg-amic (#0F3A32)      |   bg-white                 |
|                           |                            |
|   [AMIC Logo - White]     |   Welcome                  |
|                           |   Sign in to Auto FDD      |
|   Financial Due           |                            |
|   Diligence               |   ┌──── Email ────────┐    |
|   Automation              |   └────────────────────┘    |
|   Platform                |   ┌──── Password ─────┐    |
|                           |   └────────────────────┘    |
|   ─────                   |                            |
|   "전문적이고 체계적인       |   [   Sign In (accent)  ]  |
|    FDD 분석을 위한           |                            |
|    올인원 플랫폼"            |                            |
|                           |                            |
+---------------------------+----------------------------+
```

---

## 7. 페이지별 리디자인 명세

### 7.1 DealListPage (예시 페이지 — Phase 1에서 구현)

```text
+------------------------------------------------------------------+
| PageHeader: [Deals]                                 [+ New Deal]  |
+------------------------------------------------------------------+
|                                                                    |
| ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              |
| │Total Deals│ │  Active  │ │  Draft   │ │ Archived │  ← KpiCard  |
| │   12     │ │    8     │ │    3     │ │    1     │     x4       |
| │ Briefcase│ │ ✓ green  │ │ ⚠ amber  │ │ ■ gray   │              |
| └──────────┘ └──────────┘ └──────────┘ └──────────┘              |
|                                                                    |
| ┌─ Card [headerBar: "All Deals"] ───────────────────────────────┐ |
| │ ┌─ DataTable ───────────────────────────────────────────────┐ │ |
| │ │ Deal Name  │ Type                │ Currency │ Ref Date │ Status│
| │ │────────────│─────────────────────│──────────│──────────│───────│
| │ │ Alpha      │ Completion Accounts │ KRW      │ 2026-01  │ACTIVE │
| │ │ Beta       │ Locked Box          │ USD      │ 2026-02  │DRAFT  │
| │ │ Gamma      │ Completion Accounts │ EUR      │ 2026-03  │ACTIVE │
| │ └───────────────────────────────────────────────────────────┘ │ |
| └───────────────────────────────────────────────────────────────┘ |
|                                                                    |
| Modal [Create New Deal] ← 버튼 클릭 시                              |
| ┌───────────────────────────────────────┐                          |
| │ Deal Name:  [________________]        │                          |
| │ Type:       [Completion Accounts ▼]   │                          |
| │ Currency:   [KRW ▼]                   │                          |
| │ Ref Date:   [____-__-__]              │                          |
| │                                       │                          |
| │             [Cancel] [Create Deal]    │                          |
| └───────────────────────────────────────┘                          |
+--------------------------------------------------------------------+
```

### 7.2 QoEPage

```text
+------------------------------------------------------------------+
| PageHeader: [Deals > Alpha > QoE Bridge]           [Calculate QoE]|
+------------------------------------------------------------------+
|                                                                    |
| KPI Row:                                                           |
| ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              |
| │ Revenue  │ │ EBITDA   │ │ Adj EBITDA│ │ Margin   │              |
| │ 15,000   │ │  3,200   │ │  3,450   │ │  23.0%   │              |
| │ +12% YoY │ │  +8% YoY │ │          │ │          │              |
| └──────────┘ └──────────┘ └──────────┘ └──────────┘              |
|                                                                    |
| ┌─ SectionHeader: "QoE Bridge" ────────────────────────┐          |
| │ DataTable (다크그린 헤더, 줄무늬, 금액 우측정렬 모노)    │          |
| │ Account        │ FY2023  │ FY2024  │ FY2025E │ Note   │          |
| │───────────────│─────────│─────────│─────────│────────│          |
| │ Revenue        │ 12,500  │ 13,800  │ 15,000  │        │          |
| │ COGS           │ (8,200) │ (8,900) │ (9,600) │        │          |
| │ ...            │         │         │         │        │          |
| │ EBITDA (bold)  │  3,000  │  3,100  │  3,200  │        │          |
| └──────────────────────────────────────────────────────┘          |
|                                                                    |
| ┌─ SectionHeader: "Adjustments" ──────── [+ Add Adjustment] ──┐  |
| │ DataTable (조정 항목)                                         │  |
| │ Description     │ Category    │ Amount  │ Status    │ Action │  |
| │────────────────│────────────│─────────│──────────│────────│  |
| │ 일회성 소송비용  │ Non-recur.  │   250   │ APPROVED  │ [Edit] │  |
| │ 임대료 정상화    │ Normalize   │   (50)  │ CANDIDATE │ [Edit] │  |
| └──────────────────────────────────────────────────────────────┘  |
|                                                                    |
| ┌─ WaterfallChart: "EBITDA Bridge" ────────────────────────────┐  |
| │  [Recharts 기반 워터폴 차트]                                    │  |
| │  Revenue → COGS → SGA → D&A → Adj → EBITDA                   │  |
| └──────────────────────────────────────────────────────────────┘  |
+------------------------------------------------------------------+
```

### 7.3 기타 페이지 (동일 패턴)

| 페이지         | KPI 카드                    | DataTable  | 차트           | 특이사항                  |
| -------------- | --------------------------- | ---------- | -------------- | ------------------------- |
| NWCPage        | CA / CL / NWC / Target      | 라인 아이템 | TrendLineChart | Peg 시뮬레이션 테이블     |
| NetDebtPage    | Gross Debt / Cash / Net Debt | 항목별     | WaterfallChart | 브리지 요약               |
| MappingPage    | Mapped / Unmapped / Tie-out  | 매핑 제안  | —              | Confidence 배지           |
| UploadPage     | Total / Processing / Complete | 파일 목록  | —              | DropZone, 프로그레스바     |
| DefinitionPage | —                            | —          | —              | TagInput, 버전 카드       |
| IssuesPage     | Total / Critical / Open      | 이슈 목록  | —              | Severity 배지, 확장 행    |
| ReportPage     | —                            | 미리보기   | —              | 옵션 체크박스, 생성 진행률 |

---

## 8. Tailwind 설정 변경 상세

### `tailwind.config.js` 전체

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        amic: {
          DEFAULT: "#0F3A32",
          50: "#E8F5E9",
          100: "#F1F8E9",
          200: "#C8E6C9",
          300: "#A5D6A7",
          400: "#66BB6A",
          500: "#26C260",
          600: "#0F3A32",
          700: "#0B2D27",
          800: "#07201C",
          900: "#041411",
        },
        accent: { DEFAULT: "#26C260", hover: "#1FAA52" },
        positive: "#26C260",
        negative: "#BC2C1A",
        caution: "#EF6C00",
        "text-body": "#3D3D3D",
        "text-dark": "#212121",
        "text-secondary": "#777777",
        "bg-cool": "#F4F6F8",
        "bg-light-green": "#E8F5E9",
        "table-header": "#0F3A32",
        "table-alt": "#F4F6F8",
        "gray-border": "#E0E0E0",
      },
      fontFamily: {
        heading: [
          "'Inter'",
          "'Pretendard'",
          "'Noto Sans KR'",
          "sans-serif",
        ],
        body: [
          "'Pretendard'",
          "'Inter'",
          "'Noto Sans KR'",
          "'Malgun Gothic'",
          "sans-serif",
        ],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      fontSize: {
        "kpi-value": [
          "1.6875rem",
          { lineHeight: "1.2", fontWeight: "600" },
        ],
        "kpi-label": [
          "0.9375rem",
          { lineHeight: "1.4", fontWeight: "500" },
        ],
        "sub-header": ["1rem", { lineHeight: "1.5", fontWeight: "600" }],
        "body-text": [
          "0.8125rem",
          { lineHeight: "1.6", fontWeight: "400" },
        ],
        footnote: ["0.75rem", { lineHeight: "1.5", fontWeight: "400" }],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgba(0,0,0,0.08), 0 1px 2px -1px rgba(0,0,0,0.04)",
        "card-hover":
          "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.06)",
      },
    },
  },
  plugins: [],
};
```

---

## 9. 색상 마이그레이션 매핑

기존 Tailwind 클래스 → AMIC 클래스 치환 가이드:

| 기존                         | AMIC 대체                         | 용도             |
| ---------------------------- | --------------------------------- | ---------------- |
| `blue-600`                   | `amic`                            | 주요 액션, 브랜딩 |
| `blue-700`                   | `amic-700`                        | hover 상태       |
| `blue-100` / `blue-50`      | `amic-50` / `bg-light-green`     | 밝은 강조        |
| `green-600` / `green-700`   | `positive`                        | 성공, 승인       |
| `red-500` / `red-600`       | `negative`                        | 에러, 거절       |
| `yellow-700`                 | `caution`                         | 경고, 대기       |
| `gray-50`                    | `bg-cool`                         | 페이지 배경      |
| `gray-200`                   | `gray-border`                     | 테두리           |
| `gray-900`                   | `text-dark`                       | 진한 텍스트      |
| `gray-600` / `gray-500`     | `text-body` / `text-secondary`   | 본문/부가 텍스트 |

---

## 10. 구현 단계 (6 Phase)

### Phase 1: 디자인 시스템 기반 + 예시 페이지

- [ ] npm install (lucide-react, recharts, sonner)
- [ ] index.html 폰트 CDN 추가
- [ ] tailwind.config.js AMIC 토큰 등록
- [ ] index.css base layer 스타일
- [ ] lib/cn.ts, lib/format.ts 생성
- [ ] UI 컴포넌트 14개 생성
- [ ] main.tsx에 Toaster 추가
- [ ] **DealListPage.tsx 리디자인** (예시 페이지)

### Phase 2: 레이아웃 전환

- [ ] Sidebar.tsx, SidebarNavItem.tsx
- [ ] PageHeader.tsx, WorkspaceSidebar.tsx
- [ ] AppShell.tsx 재작성 (헤더 → 사이드바)
- [ ] DealWorkspacePage.tsx (탭 → 사이드바)
- [ ] App.tsx 라우팅 조정

### Phase 3: 핵심 페이지 리디자인

- [ ] LoginPage (AMIC 브랜딩 좌우 분할)
- [ ] DealWorkspace Overview (KPI + 진행률)
- [ ] QoEPage (DataTable + KpiCard)
- [ ] NWCPage (DataTable + TrendChart)
- [ ] NetDebtPage (DataTable + Bridge)

### Phase 4: 나머지 페이지 리디자인

- [ ] MappingPage, UploadPage, DefinitionPage
- [ ] IssuesPage, ReportPage

### Phase 5: 차트 시각화

- [ ] FinancialBarChart.tsx
- [ ] TrendLineChart.tsx
- [ ] WaterfallChart.tsx
- [ ] 각 페이지에 차트 통합

### Phase 6: 폴리시

- [ ] sonner 토스트 전 페이지 적용
- [ ] 스켈레톤 로딩 전 페이지 적용
- [ ] 반응형 (모바일 사이드바 드로어)
- [ ] 접근성 (ARIA, focus)
- [ ] 최종 QA

---

## 11. 검증 방법

| 단계            | 명령어                          | 기준                     |
| --------------- | ------------------------------- | ------------------------ |
| TypeScript 컴파일 | `cd frontend && npx tsc -b`    | 에러 0                   |
| ESLint          | `cd frontend && npm run lint`   | 에러 0                   |
| 빌드            | `cd frontend && npm run build`  | 성공                     |
| 시각 확인       | `npm run dev` → 브라우저         | AMIC 스타일 적용 확인     |
| E2E             | `npx playwright test`           | 기존 39 시나리오 통과     |

---

## 12. 리스크 및 대응

| 리스크                         | 대응                                                   |
| ------------------------------ | ------------------------------------------------------ |
| Pretendard 폰트 크기 (~2MB)    | dynamic-subset CDN 사용 (온디맨드 글리프 로딩)          |
| Recharts 워터폴 차트 미지원     | stacked bar + invisible base 커스텀 래퍼                |
| 400줄 PR 제한 vs 대형 페이지    | 페이지 당 별도 PR, 컴포넌트 추출 → 스타일링 분리        |
| E2E 셀렉터 변경 가능성          | data-testid 속성 유지/추가                              |
| 모바일 사이드바 UX              | 768px 이하: 오버레이 드로어 + 햄버거 토글               |
