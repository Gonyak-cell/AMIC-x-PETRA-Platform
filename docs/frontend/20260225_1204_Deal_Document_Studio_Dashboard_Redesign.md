# Deal Document Studio 대시보드 리디자인

> 작성: 2026-02-25 12:04
> 브랜치: `feat/ma-workflow`

## 배경

StudioHomePage가 플랫폼 전체 체계와 불일치하는 4가지 문제를 해결.

| # | 문제 | 해결 |
|---|------|------|
| 1 | "Deal" = FDD Deal로 표시 | MA 파이프라인 거래(Transaction)가 중심 |
| 2 | FDD/IM이 병렬 독립 테이블 | 스튜디오의 하위 기능으로 통합 |
| 3 | 카테고리 아이콘 다색상 (blue/emerald/amber/cyan) | AMIC teal 단색 팔레트로 통일 |
| 4 | 비표준 레이아웃 (5-KPI, 2테이블) | PageHero → KPI 4-grid → Filter → DataTable → Pagination 표준 패턴 |

## 변경 전후 비교

```
[변경 전]                              [변경 후]
PageHero                               PageHero (compact)
CategoryCard × 4 (다색상, 상단)        ─ 하단 "문서 유형 바로가기"로 이동
KpiCard × 5 (비표준 5-grid)            KpiCard × 4 (표준 4-grid)
Status Filter (ALL/IN_PROGRESS/...)    Filter Card (검색 + 단계 + 상태 Select)
IM/TM Documents 테이블 (IM 백엔드)     거래별 문서 현황 통합 테이블 (MA 백엔드)
FDD Deals 테이블 (FDD 백엔드)          ─ 제거 (거래 테이블에 흡수)
```

## 수정 파일

### 1. `amic-platform/src/modules/docs/types/studio-categories.ts`

- 4개 카테고리 + 12개 서브타입의 아이콘 색상 전부 단색화
- `colorCls`: 모두 `"text-text-secondary"` (기존: text-blue-600, text-emerald-600, text-amber-600, text-cyan-600 등)
- `bgCls`: 카테고리 `"bg-gray-100"`, 서브타입 `"bg-gray-50"` (기존: bg-blue-100, bg-emerald-100 등)

### 2. `amic-platform/src/modules/docs/components/CategoryCard.tsx`

- 헤더 아이콘: 동적 `category.colorCls` → 고정 `text-text-secondary`
- 호버 시: `group-hover/card:text-amic` + `group-hover/card:bg-amic/10` 전환
- 서브타입 아이콘: 동적 `sub.colorCls` → 고정 `text-text-secondary`
- 서브타입 호버: `group-hover:text-amic` + `group-hover:bg-amic/10`

### 3. `amic-platform/src/modules/docs/pages/StudioHomePage.tsx` (전면 재작성)

**데이터 소스 전환**:
- Before: `useDocuments()` (IM 백엔드) + `useFDDDeals()` (FDD 백엔드)
- After: `useTransactions()` (MA deal-mgmt 백엔드)

**레이아웃** (TransactionListPage 표준 패턴):
1. PageHero (compact) + "New Document" 버튼
2. KPI 4-grid: 전체 거래 / 문서 연결됨 / 진행 중 / 이번 달
3. Filter Card: 검색 Input + 단계 Select + 상태 Select
4. DataTable: Code, 거래명+대상기업, 단계, 문서 현황(IM/FDD 배지), 상태, 생성일
5. Pagination
6. 문서 유형 바로가기 (CategoryCard × 4, 하단 컴팩트 배치)

**테이블 컬럼**:

| 컬럼 | width | 렌더링 |
|------|-------|--------|
| Code | 120px | `font-mono text-accent` |
| 거래명 | auto | 거래명 + 대상기업 (sub-text) |
| 단계 | 100px | PHASE_LABELS 매핑 |
| 문서 현황 | 200px | `im_document_id` → IM 배지, `fdd_deal_id` → FDD 배지 |
| 상태 | 100px | Badge variant (success/warning/error/info/neutral) |
| 생성일 | 120px | toLocaleDateString |

**행 클릭**: `/ma/transactions/{id}` 거래 워크스페이스로 이동

**재사용 컴포넌트**:
- `useTransactions()` (`modules/ma/hooks/useTransactions.ts`)
- `PHASE_CONFIG`, `TRANSACTION_STATUS_OPTIONS` (`modules/ma/constants.ts`)
- `PageHero`, `KpiCard`, `Card`, `DataTable`, `Badge`, `Pagination`, `Input`, `Select`, `EmptyState` (`components/ui/`)
- `useScrollReveal` (`hooks/useScrollReveal.ts`)

## 검증

- `tsc --noEmit` — 타입 에러 없음 ✅
- `eslint` — 린트 통과 ✅
