# KIIS FundDetailPage 강화 — 펀드 검색 + 평판 + 딜 + 투자성향 완성

> 작성: 2026-02-17 10:54 | 최종 업데이트: 2026-02-17 11:52
> 상태: ✅ **전체 구현 완료** (Phase A + B + C)

---

## Context

**목표**: "펀드 검색 → 해당 펀드(운용사)의 업계 평판, 최근 딜 내역, 투자 성향 파악" 기능의 완전한 구현.

**이전 작업** (Session 22): FundDetailPage에 corp_code 매핑, Reputation Score, Recent Deals, Investment Tendency 훅 연결 완료 (360줄).

**이번 작업** (Session 23): Tab UI 리팩토링, 펀드명 검색, 투자 규모 통계, Deal 모델 fund_id FK까지 전체 구현.

### 핵심 데이터 관계 변경

```
[변경 전]
Fund.company_id → Company.id → Deal.company_id
                                (운용사 전체 딜만 조회 가능)
❌ Fund → Deal 직접 관계 없음

[변경 후]
Fund.company_id → Company.id → Deal.company_id  (운용사 전체 딜)
Fund.id ← Deal.fund_id                          (펀드 단위 딜) ✅ NEW
```

---

## Phase A: Tab UI + DealTrendChart — ✅ 완료

### A-1. Tabs 컴포넌트 신규 생성

**파일**: `amic-platform/src/components/ui/Tabs.tsx` (신규)

- Props: `tabs`, `activeTab`, `onTabChange`, `variant` (underline/pill), `size` (sm/md)
- 접근성: `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`
- 키보드 내비게이션: Arrow Left/Right, Home, End
- 아이콘 + Badge 지원

### A-2. Barrel Export 추가

**파일**: `amic-platform/src/components/ui/index.ts`

- `Tabs`, `TabsProps`, `TabItem` export 추가

### A-3. FundDetailPage 탭 재구성

**파일**: `amic-platform/src/modules/kiis/pages/FundDetailPage.tsx`

스크롤 기반 → 4개 탭 전환:
```
PageHero + KPI Cards (항상 표시)
├── [Overview]    Reputation + DealTrendChart + Investment Stats
├── [Deal History] Fund Deals + Company Deals (분리)
├── [Investment Tendency] Sector + Stage 테이블
└── [Managers]    Fund Managers DataTable
```

- `DealTrendChart` Overview 탭에 통합
- 각 탭 패널에 `role="tabpanel"`, `aria-labelledby` 적용

---

## Phase B: 펀드명 검색 + 투자 규모 통계 — ✅ 완료

### B-1. 백엔드 펀드명 검색

| 파일 | 변경 |
|------|------|
| `kiis/app/routers/kofia.py` | `fund_name: str \| None = Query(None)` 파라미터 추가 |
| `kiis/app/services/kofia_service.py` | `search_funds()`에 `fund_name` 전달, Python 측 키워드 필터링 |

KOFIA DIS API 자체가 펀드명 검색을 지원하지 않아 클라이언트 측 필터링으로 해결:
```python
if fund_name:
    keyword = fund_name.lower()
    items = [f for f in items if keyword in f.fund_name.lower()]
```

### B-2. 프론트엔드 펀드명 검색

| 파일 | 변경 |
|------|------|
| `amic-platform/src/modules/kiis/types/fund.ts` | `FundListParams`에 `fund_name?: string` 추가 |
| `amic-platform/src/modules/kiis/pages/FundListPage.tsx` | Fund Name 검색 Input 추가 (기존 Company Name 옆) |

`useFunds` 훅은 `params`를 그대로 전달하므로 수정 불필요.

### B-3. 백엔드 투자 규모 통계 API

**새 엔드포인트**: `GET /api/v1/deals/stats?corp_code={code}&years={5}`

| 파일 | 변경 |
|------|------|
| `kiis/app/schemas/deal.py` | `AmountBucket`, `DealAmountStats` 스키마 추가 |
| `kiis/app/services/deal_service.py` | `get_amount_stats()` 메서드 추가 (SQL 집계 + Python 중앙값) |
| `kiis/app/routers/deals.py` | `GET /stats` 엔드포인트 추가 |

**금액 구간**: 10억 미만 / 10~50억 / 50~100억 / 100~300억 / 300~1000억 / 1000억 이상

**응답 스키마**:
```python
class DealAmountStats(BaseModel):
    total_deals: int
    total_amount: Decimal | None
    avg_amount: Decimal | None
    median_amount: Decimal | None   # Python 측 계산
    min_amount: Decimal | None
    max_amount: Decimal | None
    distribution: list[AmountBucket]
```

### B-4. 프론트엔드 투자 통계 연결

| 파일 | 변경 |
|------|------|
| `amic-platform/src/modules/kiis/types/deal.ts` | `AmountBucket`, `DealAmountStats` 인터페이스 추가 |
| `amic-platform/src/modules/kiis/hooks/useDeals.ts` | `useDealStats(corpCode, years)` 훅 추가 |
| `amic-platform/src/modules/kiis/pages/FundDetailPage.tsx` | Overview 탭에 KPI 4개 + `FinancialBarChart` 분포 차트 |

Overview 탭 통계 섹션:
- KPI: Total Deals / Avg Amount / Median Amount / Max Amount
- BarChart: Deal Size Distribution (categorical 색상)

---

## Phase C: Deal 모델 fund_id FK — ✅ 완료

### C-1. 데이터 모델 변경

| 파일 | 변경 |
|------|------|
| `kiis/app/models/deal.py` | `fund_id: Mapped[int \| None]` FK 추가 + `fund` relationship |
| `kiis/app/models/fund.py` | `deals: Mapped[list["Deal"]]` 역관계 추가 |
| `kiis/migrations/versions/8c2f8cc1babc_add_fund_id_to_deals.py` | **신규** 마이그레이션 |

- `fund_id`는 **nullable** → 기존 데이터 영향 없음 (모두 NULL)
- `ondelete="SET NULL"` → 펀드 삭제 시 딜 유지
- 인덱스 추가 (`ix_deals_fund_id`)

### C-2. 백엔드 펀드 단위 딜 API

**새 엔드포인트**: `GET /api/v1/deals/by-fund/{fund_code}`

| 파일 | 변경 |
|------|------|
| `kiis/app/schemas/deal.py` | `DealItem`에 `fund_id`, `fund_code`, `fund_name` 필드 추가. `DealExtractRequest`에 `fund_code` 추가 |
| `kiis/app/services/deal_service.py` | `get_deals_by_fund()` 메서드 추가. `extract_deal_from_news()`에 `fund_code` → `fund_id` 매핑 |
| `kiis/app/routers/deals.py` | `GET /by-fund/{fund_code}` 엔드포인트 + extract에 `fund_code` 전달 |

### C-3. 프론트엔드 펀드 딜 연결

| 파일 | 변경 |
|------|------|
| `amic-platform/src/modules/kiis/types/deal.ts` | `DealItem`에 `fund_id`, `fund_code`, `fund_name` 추가. `DealByFundParams` 추가 |
| `amic-platform/src/modules/kiis/hooks/useDeals.ts` | `useDealsByFund(fundCode)` 훅 추가 |
| `amic-platform/src/modules/kiis/pages/FundDetailPage.tsx` | 딜 탭 2섹션 분리: "Fund Deals" + "Company Deals" |

---

## 전체 수정 파일 총괄 (16개 고유 파일)

| # | 파일 | Phase | 작업 |
|---|------|-------|------|
| 1 | `amic-platform/src/components/ui/Tabs.tsx` | A | **신규** — 재사용 Tabs 컴포넌트 |
| 2 | `amic-platform/src/components/ui/index.ts` | A | Tabs export 추가 |
| 3 | `amic-platform/src/modules/kiis/pages/FundDetailPage.tsx` | A+B+C | 탭 재구성 → 통계 → 펀드딜 |
| 4 | `amic-platform/src/modules/kiis/pages/FundListPage.tsx` | B | 펀드명 검색 Input |
| 5 | `amic-platform/src/modules/kiis/types/fund.ts` | B | `FundListParams.fund_name` |
| 6 | `amic-platform/src/modules/kiis/types/deal.ts` | B+C | Stats 타입 + fund 필드 + `DealByFundParams` |
| 7 | `amic-platform/src/modules/kiis/hooks/useDeals.ts` | B+C | `useDealStats` + `useDealsByFund` 훅 |
| 8 | `kiis/app/routers/kofia.py` | B | `fund_name` 파라미터 |
| 9 | `kiis/app/services/kofia_service.py` | B | `fund_name` 필터링 |
| 10 | `kiis/app/schemas/deal.py` | B+C | `AmountBucket`, `DealAmountStats`, fund 필드, `fund_code` |
| 11 | `kiis/app/services/deal_service.py` | B+C | `get_amount_stats()` + `get_deals_by_fund()` + `fund_code` 매핑 |
| 12 | `kiis/app/routers/deals.py` | B+C | `GET /stats` + `GET /by-fund/{fund_code}` |
| 13 | `kiis/app/models/deal.py` | C | `fund_id` FK + `fund` 관계 |
| 14 | `kiis/app/models/fund.py` | C | `deals` 역관계 |
| 15 | `kiis/migrations/versions/8c2f8cc1babc_add_fund_id_to_deals.py` | C | **신규** 마이그레이션 |

---

## 신규 API 엔드포인트 요약

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/deals/stats` | 투자 규모 통계 (평균, 중앙값, 분포) |
| GET | `/api/v1/deals/by-fund/{fund_code}` | 펀드 단위 딜 목록 |
| GET | `/api/v1/kofia/funds?fund_name=...` | 펀드명 검색 (기존 확장) |

---

## 신규 React 훅 요약

| 훅 | 파일 | 용도 |
|---|------|------|
| `useDealStats(corpCode, years)` | `useDeals.ts` | 투자 규모 통계 조회 |
| `useDealsByFund(fundCode, params)` | `useDeals.ts` | 펀드 단위 딜 목록 조회 |

---

## 검증 결과

- `npx tsc --noEmit` — ✅ 타입 에러 없음
- `npm run build` — ✅ 6.10초 빌드 성공

---

## 배포 전 체크리스트

### 필수
- [ ] `alembic upgrade head` — fund_id 마이그레이션 실행 (DB 연결 후)
- [ ] `alembic downgrade -1` — 롤백 가능 확인

### 기능 검증
- [ ] FundListPage: 펀드명 검색 → 필터 동작
- [ ] FundDetailPage: 4개 탭 전환 (키보드 포함)
- [ ] Overview 탭: Reputation + DealTrendChart + Stats KPI + BarChart
- [ ] Deal History 탭: "Fund Deals" (초기에는 빈 목록) + "Company Deals"
- [ ] `GET /api/v1/deals/stats?corp_code=...` → JSON 정상
- [ ] `GET /api/v1/deals/by-fund/{fund_code}` → 빈 목록 (기존 데이터는 fund_id=NULL)
- [ ] `POST /api/v1/deals/extract` (fund_code 포함) → deal.fund_id 할당 확인

### 비고
- 기존 딜의 fund_id는 모두 NULL (자동 역방향 매핑 미실시)
- 새로 추출되는 딜부터 fund_code 지정 시 fund_id 자동 기록
