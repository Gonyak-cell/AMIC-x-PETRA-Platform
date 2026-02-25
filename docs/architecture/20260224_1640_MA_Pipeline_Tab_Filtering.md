# MA 파이프라인 단계별 탭 필터링 구현

> 작성: 2026-02-24 16:40
> 브랜치: `feat/ma-workflow`

## 배경

TransactionWorkspacePage에서 17개 탭이 모든 파이프라인 단계에서 무조건 표시되어, 현재 단계와 무관한 탭이 혼재하는 UX 문제가 있었음. 각 단계에 해당하는 탭만 보이도록 필터링하여 워크플로우 집중도를 개선.

## 변경 파일

| 파일 | 변경 요약 |
|------|-----------|
| `amic-platform/src/modules/ma/constants.ts` | `ALWAYS_VISIBLE_TABS`, `PHASE_VISIBLE_TABS`, `LONG_LIST_STATUSES`, `SHORT_LIST_STATUSES` 상수 추가 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx` | 탭 필터링, VDR 플레이스홀더, Buyers Long/Short List 서브탭, 리다이렉트 가드 |

## 단계별 탭 매핑

| 단계 | Phase 값 | 단계별 탭 |
|------|----------|-----------|
| 1. 수임 | ENGAGEMENT | engagement, team |
| 2. 준비 | PREPARATION | ndas, vdr(신규), marketing-materials |
| 3. 마케팅 | MARKETING | buyers (Long List/Short List 서브탭) |
| 4. 입찰/DD | BIDDING_DD | bids, dd-checklist |
| 5. 계약/협상 | NEGOTIATION | contracts |
| 6. Closing | CLOSING | closing, timeline |
| 7. Post-Closing | POST_CLOSING | pmi, earnout |

**전 단계 공통 탭** (항상 표시): overview, risks, compliance, notes-approvals, ai-quality

## 구현 상세

### 1. constants.ts — 매핑 상수

```typescript
export const ALWAYS_VISIBLE_TABS = [
  "overview", "risks", "compliance", "notes-approvals", "ai-quality",
] as const;

export const PHASE_VISIBLE_TABS: Record<TransactionPhase, readonly string[]> = {
  ENGAGEMENT:   [...ALWAYS_VISIBLE_TABS, "engagement", "team"],
  PREPARATION:  [...ALWAYS_VISIBLE_TABS, "ndas", "vdr", "marketing-materials"],
  MARKETING:    [...ALWAYS_VISIBLE_TABS, "buyers"],
  BIDDING_DD:   [...ALWAYS_VISIBLE_TABS, "bids", "dd-checklist"],
  NEGOTIATION:  [...ALWAYS_VISIBLE_TABS, "contracts"],
  CLOSING:      [...ALWAYS_VISIBLE_TABS, "closing", "timeline"],
  POST_CLOSING: [...ALWAYS_VISIBLE_TABS, "pmi", "earnout"],
};
```

### 2. 매수자 Long List / Short List 분류

BuyerStatus 14개를 M&A 실무 기준으로 분리:

- **Long List** (4개): IDENTIFIED, CONTACTED, NDA_SENT, NDA_SIGNED
- **Short List** (10개): CIM_SENT 이후 모든 상태

서브탭은 `<Tabs variant="pill" size="sm">` 패턴 사용 (DD/Checklist 서브탭과 동일).

### 3. VDR 플레이스홀더

`PREPARATION` 단계에 VDR (Virtual Data Room) 탭을 빈 상태로 추가. `FolderLock` 아이콘 + EmptyState 컴포넌트 활용.

### 4. 엣지 케이스 처리

- **페이즈 변경 시 숨겨진 탭에 있을 때**: useEffect로 overview 자동 리다이렉트
- **URL 직접 접근**: 동일 useEffect가 처리
- **PipelineFlow 클릭 가드**: 현재 단계에서 보이지 않는 탭이면 overview로 이동

## 코드 리뷰 결과

### 백엔드-프론트엔드 정합성 — 5/5 통과

| 항목 | 결과 |
|------|------|
| TransactionPhase 7개 값 (`enums.py` ↔ `transaction.ts`) | ✅ |
| BuyerStatus 14개 값 (`enums.py` ↔ `buyer.ts`) | ✅ |
| LONG_LIST + SHORT_LIST = 14개 전체 (누락·중복 없음) | ✅ |
| Phase 진행 순서 (`workflow_engine.py` ↔ `PHASE_CONFIG`) | ✅ |
| PHASE_VISIBLE_TABS 탭 ID 전부 allTabs에 존재 | ✅ |

### UI 컴포넌트 패턴 — 5/5 통과

| 항목 | 결과 |
|------|------|
| Tabs variant/size props | ✅ |
| EmptyState icon/title/description props | ✅ |
| Column align 타입 | ✅ |
| FolderLock 아이콘 (lucide-react 0.563.0) | ✅ |
| PipelineFlow onPhaseClick 타입 `(phase: TransactionPhase)` | ✅ |

### React 안전성 — Critical 이슈 없음

| 항목 | 결과 |
|------|------|
| Hooks 호출 순서 (early return 이전) | ✅ |
| 리다이렉트 무한루프 방지 | ✅ |
| `as TransactionPhase` 캐스트 안전성 | ✅ |

### 적용된 개선

- P2: useEffect 의존성 `txn?.phase` → `txn` 변경 (ESLint 경고 방지)

## 검증

- `tsc --noEmit` 타입 체크 통과
- 브라우저에서 각 파이프라인 단계 전환 시 탭 필터링 동작 확인 필요
