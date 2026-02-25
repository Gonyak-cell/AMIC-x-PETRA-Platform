# List Pages — Design Override

> Overrides `MASTER.md` for all list/table pages
> Applies to: TransactionList, DealList, FundList, GPList, DocumentList, CompanyList, etc.

---

## Layout

- **PageHero**: compact variant (`py-6`)
- **Filter Bar**: `bg-white rounded-dr shadow-card p-4 flex flex-wrap gap-3`
- **DataTable**: MASTER.md DataTable 스펙 따름
- **Pagination**: 하단 고정, `flex items-center justify-between`

## Filter Bar

```
Container:  bg-white rounded-dr shadow-card p-4 mb-4
Search:     flex-1 min-w-[200px] — MASTER.md Input 스펙
Filters:    flex flex-wrap gap-2
Button:     bg-amic-50 text-amic rounded-dr-sm px-3 py-2 text-sm
            hover:bg-amic-100 transition-colors duration-150
Active:     bg-amic text-white
Sort:       flex items-center gap-2 text-sm text-text-secondary
```

## Card Grid (GP 목록 등)

```
Grid:       grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4
Card:       MASTER.md Card Default + hover-glow
            p-5 cursor-pointer
Title:      text-text-dark font-heading font-semibold
Subtitle:   text-text-secondary text-sm
Badge:      bg-accent-light text-accent text-xs px-2 py-0.5 rounded-full font-medium
Stats:      font-mono tabular-nums text-kpi-value
```

## Pagination

```
Container:  flex items-center justify-between px-1 py-3
Info:       text-text-secondary text-sm
Buttons:    flex items-center gap-1
Page Btn:   w-8 h-8 rounded-dr-sm text-sm font-medium
  - Default: text-text-secondary hover:bg-amic-50
  - Active:  bg-amic text-white
  - Disabled: text-text-muted cursor-not-allowed opacity-50
```

## Empty State

```
Container:  flex flex-col items-center justify-center py-16
Icon:       w-12 h-12 text-text-muted mb-4
Title:      text-text-dark font-heading text-lg font-semibold mb-2
Message:    text-text-secondary text-sm mb-6
CTA:        MASTER.md Primary Button
```

## Specific Rules

- 로딩 상태: DataTable 영역에 스켈레톤 행 5개
- 에러 상태: 빨간 배경 카드 + 재시도 버튼
- 빈 상태: 아이콘 + 메시지 + CTA 버튼
- 정렬 아이콘: `ArrowUpDown` (Lucide) — 정렬 가능 컬럼 헤더에 표시
