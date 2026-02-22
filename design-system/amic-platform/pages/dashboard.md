# Dashboard Page — Design Override

> Overrides `MASTER.md` for Dashboard pages (`/`, `/dashboard`)

---

## Layout

- **Hero Section**: `hero-gradient-radial` + compact variant (py-6)
- **KPI Cards**: `glass-card` 위에 white 텍스트 (Hero 내부 배치)
- **Module Cards**: 그리드 `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` + 그라디언트 배경
- **Activity Feed**: 하단 카드, 최대 5개 항목

## KPI Card (Dashboard 전용)

```
Container: glass-card p-5 hover:bg-white/[0.10] transition-all duration-300
Label:     text-white/60 text-kpi-label uppercase tracking-wider
Value:     text-white text-kpi-value font-mono tabular-nums
Trend:     text-accent (positive) | text-red-400 (negative) text-sm font-medium
```

## Module Card (Dashboard 전용)

```
Container: rounded-dr overflow-hidden hover-glow-green cursor-pointer
Gradient:  각 모듈별 고유 색상
  - FDD: from-amic-600 to-amic-500
  - KIIS: from-blue-600 to-blue-500
  - IM: from-purple-600 to-purple-500
  - MA: from-amber-600 to-amber-500
Title:     text-white font-heading text-lg font-semibold
Badge:     bg-white/20 text-white text-xs px-2 py-0.5 rounded-full
```

## Specific Rules

- KPI 로딩 시 각 모듈 독립 스켈레톤 (한 모듈 실패해도 나머지 표시)
- 에러 상태: `text-red-400` + "연결 불가" 텍스트 (KPI 값 위치)
- `stagger` 클래스로 KPI 카드 순차 등장
