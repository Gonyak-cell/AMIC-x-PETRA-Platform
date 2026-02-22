# Transaction Workspace Page — Design Override

> Overrides `MASTER.md` for MA Transaction Workspace (`/ma/transactions/:id`)

---

## Layout

- **PageHero**: compact variant + WorkflowStepper 내장
- **Tabs**: 8탭 (Overview, Engagement, Team, Buyers, NDA, Bids, DD Checklist, Timeline)
- **Content Area**: 탭별 독립 컨텐츠, 카드 기반

## WorkflowStepper

```
Container:  flex items-center gap-0 overflow-x-auto scrollbar-hide py-2
Step:       flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium
  - Completed: bg-accent/20 text-accent
  - Current:   bg-white/20 text-white ring-2 ring-accent
  - Upcoming:  bg-white/5 text-white/40
Connector:  w-6 h-px bg-white/20 (completed: bg-accent/40)
```

## Inline Status Edit

```
Select:     native <select> with bg-transparent border-0 text-sm
            focus:ring-2 focus:ring-accent/30 rounded-dr-sm
Status Badge:
  - DRAFT:      bg-gray-100 text-gray-700
  - ACTIVE:     bg-accent/10 text-accent
  - ON_HOLD:    bg-caution/10 text-caution
  - COMPLETED:  bg-blue-100 text-blue-700
  - TERMINATED: bg-negative/10 text-negative
```

## Specific Rules

- 탭 5개 이상이므로 `overflow-x-auto scrollbar-hide` 필수
- 모달 (수임 추가, 매수자 추가 등): MASTER.md 모달 스펙 따름
- DataTable 내 인라인 편집: 셀 클릭 시 native select 표시
- Delete 버튼: `text-negative hover:bg-negative/10 rounded-dr-sm`
