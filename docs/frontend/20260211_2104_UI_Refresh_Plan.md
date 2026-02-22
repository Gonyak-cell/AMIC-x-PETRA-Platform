# dealroom.net 스타일 플랫폼 UI 리프레시 계획

> **작성일:** 2026-02-11 21:00:14
> **참조:** [dealroom.net](https://dealroom.net/)
> **샘플 페이지:** `/samples/design-refresh`

## Context

현재 AMIC x PETRA Platform은 깔끔하지만 다소 평면적인(flat) 디자인. dealroom.net의 세련되고 프리미엄한 M&A 자문사 분위기(다크 Hero 섹션, 깊이감 있는 쉐도우, 풍부한 호버 효과, 여유 있는 여백)를 차용하여 플랫폼 전체의 시각적 품질을 끌어올리되, **기존 AMIC 브랜드 컬러(#0F3A32 + #26C260)는 유지**한다.

**핵심 차용 요소:**

- 다크 Hero 섹션 (대시보드, 주요 랜딩 페이지 상단)
- Corporate-yet-modern 톤 (깊이감, 세련된 호버, 여유 있는 여백)

**제약:**

- 기존 컴포넌트 API(props) 유지 — 호출자 코드 깨짐 없음
- 폰트 스택 유지 (Space Grotesk, SUITE, IBM Plex Mono)
- 반응형(모바일-퍼스트) 유지

---

## Phase 1: 디자인 토큰 확장 (Foundation) — COMPLETE

> 모든 후속 Phase의 기반. 시각적 변화 없이 토큰만 추가.

### 1A. `amic-platform/tailwind.config.js`

**Border Radius 확장:**

```js
borderRadius: {
  corporate: "6px",      // 기존 유지 (하위호환)
  dr: "12px",            // 신규: 카드, 모달 기본
  "dr-lg": "16px",       // 신규: Hero 카드, 큰 컨테이너
  "dr-sm": "8px",        // 신규: 버튼, 인풋, 뱃지
}
```

**Box Shadow 확장 (AMIC 틸 기반):**

```js
boxShadow: {
  // 기존 전부 유지 + 아래 추가
  "dr-sm": "0 2px 8px -2px rgba(15,58,50,0.08)",
  "dr-md": "0 8px 24px -4px rgba(15,58,50,0.10), 0 4px 8px -4px rgba(15,58,50,0.06)",
  "dr-lg": "0 16px 48px -8px rgba(15,58,50,0.14), 0 8px 16px -4px rgba(15,58,50,0.08)",
  "dr-xl": "0 24px 64px -12px rgba(15,58,50,0.18), 0 12px 24px -4px rgba(15,58,50,0.10)",
  "glow-green": "0 0 20px rgba(38,194,96,0.15), 0 8px 32px -8px rgba(38,194,96,0.20)",
  "glow-teal": "0 0 20px rgba(15,58,50,0.20), 0 8px 32px -8px rgba(15,58,50,0.25)",
}
```

**Hero 전용 색상 토큰:**

```js
colors: {
  "hero-dark": "#0A2B24",
  "hero-end": "#0F3A32",
  "glass-white": "rgba(255,255,255,0.06)",
  "glass-border": "rgba(255,255,255,0.08)",
}
```

**Hero 전용 폰트 사이즈:**

```js
fontSize: {
  "hero-title": ["2.5rem", { lineHeight: "1.15", fontWeight: "800", letterSpacing: "-0.03em" }],
  "hero-subtitle": ["1.125rem", { lineHeight: "1.5", fontWeight: "400" }],
  "page-title": ["1.75rem", { lineHeight: "1.25", fontWeight: "700", letterSpacing: "-0.02em" }],
}
```

**키프레임 + 애니메이션:**

```js
keyframes: {
  "fade-in-up": {
    "0%": { opacity: "0", transform: "translateY(12px)" },
    "100%": { opacity: "1", transform: "translateY(0)" },
  },
},
animation: {
  "fade-in-up": "fade-in-up 0.5s ease-out forwards",
},
```

### 1B. `amic-platform/src/index.css` — 유틸리티 클래스 추가

```css
.hero-gradient { ... }
.hero-gradient-radial { ... }
.glass-card { ... }
.hover-glow { ... }
.hover-glow-green { ... }
.stagger > * { ... }
.section-divider-line { ... }
```

---

## Phase 2: 코어 UI 컴포넌트 업그레이드

> 기존 props 시그니처 유지. 내부 클래스만 변경하여 시각적 품질 향상.

### 2A. `src/components/ui/Card.tsx`

- `CardVariant`에 `"hero"` 추가 (union 확장, 하위호환)
- 기본 `rounded-corporate` → `rounded-dr` (12px)
- `shadow-card` → `shadow-dr-sm`
- `hero` variant: `"bg-white/[0.06] border-white/[0.08] backdrop-blur-sm shadow-dr-md"`
- `forest-lift` hover: `hover-lift` → `hover-glow`
- `hoverEffect` true일 때: `hover:shadow-card-hover` → `hover:shadow-dr-md`

### 2B. `src/components/ui/Button.tsx`

- `rounded-corporate` → `rounded-dr-sm` (8px)
- `primary`: `shadow-sm` → `shadow-dr-sm hover:shadow-dr-md`
- `accent`: 기존 + `hover:shadow-glow-green`
- 전체: `active:scale-[0.98]` 추가 (클릭 피드백)
- `lg` 사이즈: `px-5 py-2.5` → `px-6 py-3`

### 2C. `src/components/ui/KpiCard.tsx`

- `rounded-corporate` → `rounded-dr`
- `shadow-card` → `shadow-dr-sm`
- `hoverLift` true일 때: `hover-lift` → `hover-glow`
- `transition-all duration-300` 추가
- `generous` 패딩: `p-6` → `p-7`

### 2D. `src/components/ui/Modal.tsx`

- `rounded-corporate` → `rounded-dr`
- backdrop: `bg-black/50` → `bg-amic-900/70 backdrop-blur-sm`
- 콘텐츠 wrapper: `animate-fade-in-up` 추가
- shadow 업그레이드: `shadow-dr-xl`

### 2E. `src/components/ui/Input.tsx` + `Select.tsx`

- `rounded-corporate` → `rounded-dr-sm`
- `shadow-sm` 추가 (미묘한 깊이감)
- 포커스 링: `focus:ring-accent/30`

### 2F. `src/components/ui/Badge.tsx`

- `rounded` → `rounded-md`
- `font-medium tracking-wide` 추가

### 2G. `src/components/ui/SectionHeader.tsx`

- `rounded-t-lg` → `rounded-t-dr`

### 2H. `src/components/ui/DataTable.tsx`

- 외부 wrapper: `rounded-lg` → `rounded-dr`
- 헤더: `bg-table-header` → `bg-gradient-to-r from-amic to-amic-500`
- hover row: `hover:bg-accent/5` (은은한 그린 틴트)

**수정 파일:** 9개

---

## Phase 3: 레이아웃 쉘 업그레이드

### 3A. `src/components/layout/Sidebar.tsx`

- flat `bg-amic` → `bg-gradient-to-b from-amic-800 via-amic to-amic-700`
- 로고 섹션 하단: 그라디언트 디바이더 추가
- 유저 아바타: `bg-accent/20` → `bg-accent/25` + `ring-1 ring-accent/30`

### 3B. `src/components/layout/SidebarNavItem.tsx`

- Active 상태: glow 바 추가 (`before:shadow-[0_0_8px_rgba(38,194,96,0.4)]`)
- Hover: `hover:bg-white/5` → `hover:bg-white/[0.07]`

### 3C. `src/components/DesktopHeader.tsx`

- glass 효과: `bg-white/80 backdrop-blur-md border-b border-gray-border/50`
- sticky: `sticky top-0 z-30`
- 검색 버튼: `rounded-dr shadow-dr-sm`으로 업그레이드

### 3D. `src/components/layout/AppShell.tsx`

- 모바일 헤더: `backdrop-blur-md` 추가
- 데스크톱 콘텐츠 패딩: `md:px-6` → `md:px-8` (약간 더 여유)

### 3E. `src/components/layout/ModuleSwitcher.tsx`

- 드롭다운: `shadow-dr-lg rounded-dr` 적용

**수정 파일:** 5개

---

## Phase 4: 페이지 레벨 — Hero 섹션 도입 (핵심)

> 가장 큰 시각적 임팩트. 다크 Hero 섹션이 플랫폼의 톤을 결정.

### 4A. 신규: `src/components/ui/PageHero.tsx`

재사용 가능한 다크 Hero 섹션 컴포넌트:

```tsx
interface PageHeroProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  compact?: boolean;
  className?: string;
}
```

구현:

- `hero-gradient-radial` 배경
- 화이트 타이포 (`text-hero-title` / `text-hero-subtitle`)
- negative margin으로 AppShell 콘텐츠 영역 브레이크아웃
- `children` 슬롯에 glass-card 스타일 KPI 영역
- `compact` 모드: 줄어든 패딩 (`py-8` vs `py-12`)

### 4B. `src/pages/DashboardPage.tsx` — 대대적 리디자인

**After:**

- 다크 HERO 섹션: Welcome + 날짜 + glass-card KPI 4개 (stagger 애니메이션)
- Quick Actions: hover-glow-green 카드
- Module Status: 슬림 바
- Modules: 그라디언트 배경 카드

### 4C. `src/pages/LoginPage.tsx`

- 좌측 패널: 이미지 위에 다크 그라디언트 오버레이
- 오버레이 위에 화이트 브랜딩 텍스트 추가
- 우측 폼 래퍼: `shadow-dr-lg rounded-dr-lg` 적용
- 로그인 버튼: `variant="accent"` (그린 글로우 효과)

### 4D. 주요 랜딩 페이지에 `<PageHero compact>` 적용

- `src/pages/analytics/AnalyticsPage.tsx` — "Cross-Module Analytics"
- `src/pages/exports/ExportsPage.tsx` — "Data Export Hub"
- `src/pages/calendar/CalendarPage.tsx` — "Calendar & Timeline"
- `src/pages/help/HelpPage.tsx` — "Help Center"

**수정 파일:** 1개 신규 + 6개 수정 = 7개

---

## Phase 5: 모듈 페이지 일괄 적용 + 폴리시

### 5A. 모듈 랜딩 페이지 Hero 적용

- `src/modules/fdd/` 내 DealListPage 등 — `<PageHero compact>`
- `src/modules/kiis/` 내 DashboardPage 등
- `src/modules/im/` 내 DocumentListPage 등

### 5B. 디테일/워크스페이스 페이지 헤더 통일

- 기존 `text-2xl font-heading font-bold` → `text-page-title font-heading` + 그라디언트 배경

### 5C. 스크롤바 + 포커스 링 업데이트 (`src/index.css`)

### 5D. Toast 스타일 (`src/main.tsx`)

### 5E. `src/components/ui/index.ts` — `PageHero` barrel export 추가

**수정 파일:** ~15개

---

## 실행 순서 & 의존성

```text
Phase 1 (토큰) → Phase 2 (컴포넌트) → Phase 3 (레이아웃) → Phase 4 (Hero 페이지) → Phase 5 (일괄 적용)
```

각 Phase는 이전 Phase 완료 후 진행. Phase 1은 모든 후속의 전제조건.

## 총 범위

| Phase          | 수정 파일 | 신규 파일 | 영향도                      |
| -------------- | --------- | --------- | --------------------------- |
| 1. 토큰        | 2         | 0         | Foundation                  |
| 2. 컴포넌트    | 9         | 0         | 중 (미묘한 품질 향상)       |
| 3. 레이아웃    | 5         | 0         | 중                          |
| 4. Hero 페이지 | 6         | 1         | **높음** (핵심 시각 변화)   |
| 5. 일괄+폴리시 | ~15       | 0         | 중                          |
| **합계**       | **~37**   | **1**     |                             |

## 검증 방법

1. `npm run dev` → `/samples/design-refresh` 접속하여 새 디자인 확인
2. 각 섹션(Hero, Cards, Buttons, Glass 등) 시각적 렌더링 확인
3. 모바일 뷰포트에서 반응형 깨짐 없는지 확인
4. `npm run build` → 빌드 에러 없음 확인
5. `npm run test` → 기존 테스트 통과 확인
