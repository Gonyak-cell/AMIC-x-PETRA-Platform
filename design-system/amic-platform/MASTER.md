# AMIC x PETRA Platform — Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/amic-platform/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** AMIC x PETRA Platform
**Generated:** 2026-02-21 23:16:10
**Category:** Fintech / M&A Deal Management / PE Platform
**Visual Identity:** Dealroom.net-inspired, Forest Green Dark, Glass Morphism

---

## Brand Identity

AMIC x PETRA는 프라이빗 에쿼티(PE) 딜 매니지먼트 플랫폼입니다.
신뢰감(Trust), 전문성(Expertise), 정밀함(Precision)을 시각적으로 전달해야 합니다.

**무드:** Professional, Data-driven, Confident, Premium
**기조:** 포레스트 그린 다크 모드 + 화이트 라이트 모드 (듀얼 톤)

---

## Color Palette

### Primary — AMIC Forest Green (10단계)

| Token | Hex | Usage |
|-------|-----|-------|
| `amic-50` | `#EDF5F3` | 라이트 모드 배경 하이라이트 |
| `amic-100` | `#D5E8E3` | 호버 배경, 선택 상태 |
| `amic-200` | `#A8D1C7` | 보조 강조 |
| `amic-300` | `#6BAA9B` | 비활성 텍스트 (다크 모드) |
| `amic-400` | `#3D7D6E` | 서브 아이콘 |
| `amic-500` | `#1A5A4C` | 중간 강조 |
| `amic-600` | `#0F3A32` | **Primary (DEFAULT)** — 사이드바, 테이블 헤더, Hero |
| `amic-700` | `#0B2D27` | 호버 다크 |
| `amic-800` | `#07201C` | Hero 그라디언트 시작 |
| `amic-900` | `#041411` | 최심부 배경 |

### Semantic Colors

| Role | Token | Hex | Usage |
|------|-------|-----|-------|
| Accent/CTA | `accent` | `#26C260` | 버튼, 링크, 긍정 지표 |
| Accent Hover | `accent-hover` | `#1FAA52` | 버튼 호버 |
| Accent Light | `accent-light` | `#E8F8ED` | 배지 배경, 서브 하이라이트 |
| Positive | `positive` | `#26C260` | 성공, 증가, 완료 |
| Negative | `negative` | `#BC2C1A` | 에러, 감소, 실패 |
| Caution | `caution` | `#EF6C00` | 경고, 주의 |

### Surface Colors

| Role | Token | Hex/Value | Usage |
|------|-------|-----------|-------|
| Body BG | `bg-cool` | `#F7F8FA` | 라이트 모드 전체 배경 |
| Light Green BG | `bg-light-green` | `#E8F8ED` | 카드 액센트 배경 |
| Hero Start | `hero-dark` | `#0A2B24` | Hero 그라디언트 시작점 |
| Hero End | `hero-end` | `#0F3A32` | Hero 그라디언트 끝점 |
| Glass White | `glass-white` | `rgba(255,255,255,0.06)` | 다크 섹션 glass 카드 |
| Glass Border | `glass-border` | `rgba(255,255,255,0.08)` | glass 카드 테두리 |
| Table Header | `table-header` | `#0F3A32` | DataTable 헤더 배경 |
| Table Alt Row | `table-alt` | `#F7F8FA` | 테이블 교차 행 |

### Text Colors

| Role | Token | Hex | Usage |
|------|-------|-----|-------|
| Primary Text | `text-dark` | `#1A1A1A` | 제목, 핵심 데이터 |
| Body Text | `text-body` | `#3D3D3D` | 본문, 설명 |
| Secondary | `text-secondary` | `#6B7280` | 부가 정보, 레이블 |
| Muted | `text-muted` | `#9CA3AF` | 플레이스홀더, 비활성 |
| On Dark (Hero) | — | `#FFFFFF` | 다크 배경 위 텍스트 |
| On Dark Muted | — | `rgba(255,255,255,0.7)` | 다크 배경 위 부가 텍스트 |

---

## Typography

### Font Stack

| Role | Font Family | Fallback | Usage |
|------|-------------|----------|-------|
| Heading | `Space Grotesk` | `SUITE Variable`, sans-serif | h1~h6, 페이지 타이틀, Hero |
| Body (한국어) | `SUITE Variable` | `SUITE`, `Space Grotesk`, sans-serif | 본문, 설명, UI 텍스트 |
| Mono/KPI | `IBM Plex Mono` | monospace | 숫자, KPI 값, 코드 |

### Font Size Scale

| Token | Size | Line Height | Weight | Usage |
|-------|------|-------------|--------|-------|
| `hero-title` | 2.5rem (40px) | 1.15 | 800 | Hero 메인 타이틀 |
| `hero-subtitle` | 1.125rem (18px) | 1.5 | 400 | Hero 부제목 |
| `page-title` | 1.75rem (28px) | 1.25 | 700 | 페이지 제목 |
| `section-number` | 2rem (32px) | 1 | 700 | KPI 큰 숫자 |
| `kpi-value` | 1.6875rem (27px) | 1.2 | 600 | KPI 카드 값 |
| `kpi-label` | 0.9375rem (15px) | 1.4 | 500 | KPI 카드 레이블 |
| `sub-header` | 1rem (16px) | 1.5 | 600 | 섹션 소제목 |
| `body-text` | 0.8125rem (13px) | 1.6 | 400 | 본문 텍스트 |
| `footnote` | 0.75rem (12px) | 1.5 | 400 | 주석, 작은 텍스트 |

### Typography Rules

- 한글 본문: `SUITE Variable` — 깔끔한 고딕체, 가독성 우수
- 영문 제목: `Space Grotesk` — 기하학적 산세리프, 모던/테크 무드
- 숫자/데이터: `IBM Plex Mono` — tabular-nums로 열 정렬
- Letter spacing: 제목 `-0.02em ~ -0.03em` (tight), 본문 기본값
- Line height: 본문 1.5~1.6, 제목 1.15~1.25

---

## Spacing & Layout

### Spacing Scale (Tailwind 기본 + 확장)

| Token | Value | Usage |
|-------|-------|-------|
| `1` | 4px | 아이콘-텍스트 gap |
| `2` | 8px | 인라인 gap, 배지 패딩 |
| `3` | 12px | 카드 내부 작은 gap |
| `4` | 16px | 카드 패딩, 섹션 gap |
| `5` | 20px | 카드 패딩 (generous) |
| `6` | 24px | 카드 패딩 (large), 섹션 gap |
| `8` | 32px | 섹션 마진 |
| `18` | 72px | 사이드바 너비 보정 |
| `22` | 88px | 헤더 높이 보정 |
| `26` | 104px | 대형 gap |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `corporate` | 6px | 레거시 (사용 최소화) |
| `dr-sm` | 8px | 버튼, 인풋, 배지 |
| `dr` | 12px | 카드, 모달, glass 카드 |
| `dr-lg` | 16px | 대형 카드, Hero 섹션 |

### Z-Index Scale

| Level | Value | Usage |
|-------|-------|-------|
| Base | 0 | 일반 콘텐츠 |
| Dropdown | 10 | 드롭다운, 팝오버 |
| Sticky | 20 | Sticky 헤더 |
| Sidebar | 30 | 사이드바 |
| Modal Overlay | 40 | 모달 배경 |
| Modal | 50 | 모달 콘텐츠 |
| Toast | 60 | 토스트 알림 |

---

## Box Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `card` | `0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.03)` | 기본 카드 |
| `card-hover` | `0 4px 12px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04)` | 카드 호버 |
| `elevated` | `0 8px 24px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06)` | 모달, 드롭다운 |
| `dr-sm` | `0 2px 8px rgba(15,58,50,0.08)` | 미세한 리프트 (그린 틴트) |
| `dr-md` | `0 8px 24px rgba(15,58,50,0.10), ...` | 카드 (그린 틴트) |
| `dr-lg` | `0 16px 48px rgba(15,58,50,0.14), ...` | 호버 카드 (그린 틴트) |
| `dr-xl` | `0 24px 64px rgba(15,58,50,0.18), ...` | 모달 (그린 틴트) |
| `glow-green` | `0 0 20px rgba(38,194,96,0.15), ...` | CTA 버튼 글로우 |
| `glow-teal` | `0 0 20px rgba(15,58,50,0.20), ...` | 사이드바 글로우 |

**핵심 원칙:** 그림자에 AMIC 그린(`rgba(15,58,50,...)`) 틴트를 넣어 브랜드 일관성 유지

---

## Component Specifications

### Buttons

```
Primary:   bg-accent text-white rounded-dr-sm px-5 py-2.5 font-semibold
           hover:bg-accent-hover active:scale-[0.98] shadow-glow-green transition-all duration-200
Secondary: bg-transparent text-amic border-2 border-amic rounded-dr-sm px-5 py-2.5
           hover:bg-amic hover:text-white transition-all duration-200
Ghost:     bg-transparent text-text-secondary rounded-dr-sm px-3 py-2
           hover:bg-amic-50 hover:text-amic transition-colors duration-200
```

### Cards

```
Default:   bg-white rounded-dr shadow-card border border-gray-border p-6
           hover:shadow-dr-md transition-all duration-200
Hero:      bg-white rounded-dr shadow-dr-md border-0 p-8
Glass:     bg-white/[0.06] border border-white/[0.08] backdrop-blur-sm rounded-dr p-6
           (다크 배경 전용)
KPI:       bg-white rounded-dr shadow-card p-5 hover:shadow-dr-md
           border-l-[3px] border-l-accent (선택적)
```

### Inputs

```
Default:   bg-white border border-gray-border rounded-dr-sm px-4 py-3 text-body-text
           focus:border-amic focus:ring-2 focus:ring-accent/30 transition-all duration-200
           placeholder:text-text-muted
```

### DataTable

```
Header:    bg-gradient-to-r from-amic-600 to-amic-500 text-white font-heading
           text-xs uppercase tracking-wider px-4 py-3
Row:       border-b border-gray-border hover:bg-accent/5 transition-colors duration-150
Alt Row:   bg-table-alt
```

### Modal

```
Overlay:   bg-black/50 backdrop-blur-sm
Content:   bg-white rounded-dr-lg shadow-dr-xl p-8 max-w-lg w-[90%]
           animate-fade-in-up
```

### Sidebar

```
Background: linear-gradient(180deg, #0F3A32 0%, #0A2B24 100%)
Nav Item:   text-white/70 hover:bg-white/[0.07] hover:text-white rounded-dr-sm px-3 py-2
Active:     bg-white/10 text-white border-l-2 border-accent
Divider:    bg-gradient-to-r from-transparent via-white/10 to-transparent h-px
```

### PageHero

```
Container:  hero-gradient rounded-b-dr-lg px-6 py-8 md:px-8 md:py-10
Title:      text-white font-heading text-hero-title
Subtitle:   text-white/70 text-hero-subtitle
Variant:    compact (py-6) | full (py-10)
```

---

## Utility Classes (index.css)

| Class | Purpose |
|-------|---------|
| `.hover-lift` | translateY(-2px) + shadow-card-hover on hover |
| `.hover-glow` | translateY(-3px) + shadow-dr-lg on hover |
| `.hover-glow-green` | translateY(-3px) + shadow-glow-green on hover |
| `.glass-card` | Glass morphism (다크 배경 전용) |
| `.hero-gradient` | Linear gradient: hero-dark → amic-600 → amic-500 |
| `.hero-gradient-radial` | Radial + linear (그린 글로우 포인트) |
| `.stagger > *` | Children에 순차 fade-in-up (75ms 간격) |
| `.section-divider-line` | 그라디언트 수평 구분선 |
| `.link-curtain` | 밑줄 슬라이드-인 호버 효과 |
| `.label-uppercase` | uppercase tracking-wide xs semibold |
| `.text-confidential` | 기밀 문서 워터마크 스타일 |
| `.tabular-nums` | 숫자 열 정렬 (font-variant-numeric) |
| `.scrollbar-hide` | 스크롤바 숨기기 (탭 등) |

---

## Animation & Motion

### Timing

| Duration | Usage |
|----------|-------|
| 150ms | 마이크로 인터랙션 (hover color, focus ring) |
| 200ms | 버튼, 카드 호버, 입력 포커스 |
| 300ms | 카드 리프트, glass 효과 |
| 500ms | 페이지 등장 (fade-in-up) |

### Easing

| Token | Value | Usage |
|-------|-------|-------|
| `ease-forest` | `cubic-bezier(0.25, 0.1, 0.25, 1)` | 카드 리프트, 깊이감 있는 전환 |
| `ease-out` | Tailwind 기본 | 등장 애니메이션 |

### Keyframes

```
fade-in-up:  opacity 0→1, translateY(12px→0), 500ms ease-out
stagger:     각 자식 75ms 간격 순차 실행 (최대 6개)
```

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

---

## Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 640px | 1 column, 사이드바 숨김, 햄버거 메뉴 |
| Tablet | 640px~1023px | 2 column 가능, 사이드바 오버레이 |
| Desktop | 1024px+ | 사이드바 고정, 멀티 컬럼, 전체 레이아웃 |
| Wide | 1440px+ | max-w-7xl 컨테이너, 여유 패딩 |

### 반응형 원칙

- 모바일 퍼스트 (`min-width` 기반)
- DataTable: `overflow-x-auto` 가로 스크롤
- 탭 5개 이상: `overflow-x-auto scrollbar-hide`
- 카드 그리드: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`
- 버튼 그룹: `flex-wrap` 사용 (모바일 줄바꿈)

---

## Anti-Patterns (사용 금지)

- **Emoji를 아이콘으로 사용 금지** — Lucide React 사용
- **순수 검정(#000) 배경** — `amic-900` 또는 `hero-dark` 사용
- **cursor:pointer 누락** — 모든 클릭 가능 요소에 필수
- **레이아웃 깨지는 hover** — scale 대신 translateY 사용
- **명도 대비 4.5:1 미만** — WCAG AA 준수
- **순간 상태 변화** — 최소 150ms transition 필수
- **포커스 링 숨기기** — 키보드 접근성 필수
- **light 배경에 glass-card** — glass-card는 다크 배경 전용
- **AMIC 그린 없는 그림자** — 범용 gray 대신 `rgba(15,58,50,...)` 틴트

---

## Icon System

- **라이브러리:** Lucide React (`lucide-react`)
- **기본 크기:** `w-5 h-5` (20px)
- **소형:** `w-4 h-4` (16px) — 배지, 인라인
- **대형:** `w-6 h-6` (24px) — 네비게이션, Hero
- **색상:** `text-current` 또는 시맨틱 컬러 (`text-accent`, `text-negative`)
- **Stroke:** 기본 2px (Lucide 기본값)

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] Lucide React 아이콘만 사용 (emoji 사용 금지)
- [ ] 모든 클릭 가능 요소에 `cursor-pointer`
- [ ] 호버 시 smooth transition (150~300ms)
- [ ] 텍스트 대비 4.5:1 이상 (WCAG AA)
- [ ] 키보드 포커스 링 visible
- [ ] `prefers-reduced-motion` 존중
- [ ] 반응형: 375px, 768px, 1024px, 1440px 확인
- [ ] 고정 요소 뒤 콘텐츠 가려지지 않음
- [ ] 모바일 가로 스크롤 없음
- [ ] AMIC 그린 색조 그림자 사용 (`shadow-dr-*`)
- [ ] Space Grotesk(heading) + SUITE(body) + IBM Plex Mono(numbers) 일관성
- [ ] 다크 섹션의 glass-card에 `backdrop-blur-sm` 적용
