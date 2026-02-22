# GP(운용사) 중심 검색 전환 구현 보고서

> **작성일**: 2026-02-17 21:36
> **세션**: Session 23
> **상태**: Phase 1~4 완료, `tsc --noEmit` 통과

---

## 1. 배경 및 목적

기존 KIIS 모듈에서 펀드는 개별 단위로 검색/조회되어, 특정 운용사(GP)의 역량을 평가하려면 펀드를 하나하나 들어가야 했다. 실무에서는 **GP 단위로 운용펀드, 업계 평판, 투자경향을 종합 평가**하는 것이 자연스러운 워크플로우이므로, Funds 메뉴를 GP 중심으로 전환했다.

### Funds vs Companies 통합 결론: **분리 유지**

| 비교 항목 | Funds (→ GP 전환) | Companies |
|-----------|-------------------|-----------|
| 데이터 소스 | KOFIA ProFrame API (외부 실시간) | DART 전자공시 + PostgreSQL |
| 사용 목적 | GP 운용 역량 평가 (LP 관점) | 피투자사 실사, 상장사 재무 분석 |
| 핵심 엔티티 | 운용사 → 펀드 → 딜 | 법인 → 재무제표 → 공시 |
| 식별자 | company_code + fund_code (KOFIA) | corp_code (DART 8자리) |

---

## 2. 라우팅 변경

```
변경 전:
/kiis/funds           → 펀드 개별 목록 (FundListPage)
/kiis/funds/:fundCode → 펀드 상세 (FundDetailPage)

변경 후:
/kiis/funds                    → GP(운용사) 목록 (GPListPage) ★ 변경
/kiis/funds/all                → 전체 펀드 목록 (FundListPage) ★ 신규
/kiis/funds/gp/:companyCode    → GP 상세 (GPDetailPage) ★ 신규
/kiis/funds/:fundCode          → 펀드 상세 (FundDetailPage) — 유지
```

사이드바 메뉴: `"Funds"` → `"GPs & Funds"` (순서 1번)

---

## 3. 변경 파일 목록

### 신규 파일 (4개)

| 파일 | 설명 |
|------|------|
| `amic-platform/src/modules/kiis/types/gp.ts` | GPListItem, GPListResponse, GPListParams, GPSortField 타입 |
| `amic-platform/src/modules/kiis/hooks/useGPs.ts` | TanStack Query 훅 (`GET /kofia/gp`) |
| `amic-platform/src/modules/kiis/pages/GPListPage.tsx` | GP 카드 그리드 목록 페이지 |
| `amic-platform/src/modules/kiis/pages/GPDetailPage.tsx` | GP 상세 5탭 페이지 |

### 수정 파일 (6개)

| 파일 | 변경 내용 |
|------|----------|
| `kiis/app/schemas/fund.py` | `GPListItem`, `GPListResponse` Pydantic 모델 추가 |
| `kiis/app/services/kofia_service.py` | `get_gp_list()` 메서드 추가 (KOFIA 캐시 메모리 그룹화) |
| `kiis/app/routers/kofia.py` | `GET /gp` 엔드포인트 추가 |
| `kiis/tests/test_kofia_service.py` | GP 관련 유닛 테스트 6건 추가 |
| `amic-platform/src/modules/kiis/KiisRoutes.tsx` | GP 라우트 3개 추가, lazy import |
| `amic-platform/src/components/layout/Sidebar.tsx` | KIIS_RESEARCH 메뉴 레이블/순서 변경 |

### 업데이트 파일 (2개)

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/modules/kiis/pages/FundDetailPage.tsx` | Breadcrumb에 GP 상세 링크 추가 (3단계) |
| `amic-platform/src/modules/kiis/pages/FundListPage.tsx` | 타이틀 "All Funds", "← GP 목록으로" 링크 추가 |

---

## 4. 백엔드 설계 상세

### 4-1. GP 집계 API (`GET /api/v1/kofia/gp`)

**쿼리 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|-------|------|
| `company_name` | str | - | 운용사명 검색 (부분 일치) |
| `asset_class` | str | - | 자산 클래스 필터 (콤마 구분) |
| `sort_by` | str | `total_aum` | 정렬 필드 (total_aum, fund_count, company_name) |
| `sort_order` | str | `desc` | 정렬 방향 (asc, desc) |
| `page` | int | 1 | 페이지 번호 |
| `size` | int | 20 | 페이지 크기 |

**응답 (GPListResponse):**

```json
{
  "total": 89,
  "page": 1,
  "size": 20,
  "items": [
    {
      "company_name": "삼성자산운용",
      "company_code": "A001",
      "fund_count": 15,
      "active_fund_count": 12,
      "total_aum": "2500000000000",
      "asset_classes": ["vc", "pef", "real_estate"],
      "vintage_range": "2018~2024",
      "has_maturity_alert": false
    }
  ]
}
```

**핵심 로직:**
- 기존 `_get_all_fund_prices()` 6시간 Redis 캐시 재사용 (추가 KOFIA 호출 없음)
- `company_name`별 메모리 그룹화 → 집계 (AUM, 펀드 수, 자산 클래스, 빈티지 범위)
- `tmpV13` 필드에서 company_code 추출

### 4-2. 테스트 (6건)

| 테스트 | 검증 내용 |
|--------|----------|
| `test_get_gp_list_basic` | 기본 조회, AUM desc 정렬 |
| `test_get_gp_list_company_name_filter` | 운용사명 검색 필터 |
| `test_get_gp_list_aum_and_vintage` | AUM 합산, 빈티지 범위 계산 |
| `test_get_gp_list_asset_class_filter` | 자산 클래스 필터 (real_estate) |
| `test_get_gp_list_pagination` | size=2 페이지네이션 |
| `test_get_gp_list_sort_by_fund_count` | 펀드 수 내림차순 정렬 |

---

## 5. 프론트엔드 설계 상세

### 5-1. GP 목록 페이지 (GPListPage.tsx)

- **검색**: 운용사명 디바운스 검색 (300ms)
- **필터**: 자산유형 Chip 토글 (다중 선택)
- **정렬**: AUM순 / 펀드 수순 / 이름순 (토글 asc/desc)
- **카드 그리드**: 1~3열 반응형 (`grid-cols-1 md:grid-cols-2 xl:grid-cols-3`)
- **카드 내용**: 운용사명, 펀드 수 (active), 총 AUM, 자산 클래스 Badge, 빈티지 범위, 만기 경고
- **페이지네이션**: URL searchParams 기반 (`useGPFilters` 커스텀 훅)
- **"전체 펀드 보기 →"** 링크 → `/kiis/funds/all`

### 5-2. GP 상세 페이지 (GPDetailPage.tsx)

**5탭 구조:**

| 탭 | 콘텐츠 | 재사용 컴포넌트 | API |
|----|--------|----------------|-----|
| Overview | 업계 평판 + 딜 트렌드 + 투자 통계 | `ReputationSummary`, `DealTrendChart`, `KpiCard`, `FinancialBarChart` | `/analysis/reputation/{corpCode}/qualitative`, `/deals/trends`, `/deals/stats` |
| Funds | GP 펀드 목록 DataTable | `DataTable`, `Pagination` | `/kofia/funds?company_name=X` |
| Deals | 투자 이력 DataTable | `DataTable` | `/deals/by-company/{corpCode}` |
| Tendency | 투자 성향 정성 분석 | `TendencySummary` | `/deals/tendency-summary?corp_code=X` |
| News | 관련 뉴스 목록 | 뉴스 카드 UI | `/news?company_id=X` |

**corp_code 확보 흐름:**
1. URL `companyCode` + query param `name` → `gpName` 확보
2. `useCompanies({ search: gpName, size: 1 })` → DART company 검색
3. `corp_name`에 `gpName` 접두사 포함 확인 → `corp_code` 추출
4. `hasCorpCode = /^\d{8}$/.test(corpCode)` — 미매칭 시 분석 탭 비활성화

**기존 컴포넌트 100% 재사용** — `ReputationSummary`, `TendencySummary`, `DealTrendChart`는 `corp_code` 기반이므로 코드 변경 없이 삽입.

### 5-3. Breadcrumb 업그레이드

**FundDetailPage:**
```
변경 전: Funds > {fund_name}
변경 후: GPs & Funds > {company_name} > {fund_name}
```

---

## 6. 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| `tsc --noEmit` | 통과 (신규 코드 에러 0) |
| `tsc -b` | 기존 에러 3건 (신규 코드 무관) |
| 기존 에러 1 | `useAuth.test.tsx`: mockViewerUser export 누락 (기존) |
| 기존 에러 2 | `TendencySummary.tsx`: 미사용 import (기존) |

---

## 7. Session 24 보완 (2026-02-17 21:54)

### 7-1. 백엔드 테스트 — 40/40 통과

```
pytest kiis/tests/test_kofia_service.py -v → 40 passed in 3.70s
GP 테스트 6건 포함 전체 통과
```

### 7-2. E2E 네비게이션 흐름 검증

| 경로 | 페이지 | 전환 액션 |
|------|--------|----------|
| `/kiis/funds` | GPListPage | GP 카드 클릭 → GP 상세 |
| `/kiis/funds/gp/:companyCode` | GPDetailPage | 펀드 행 클릭 → 펀드 상세 |
| `/kiis/funds/:fundCode` | FundDetailPage | Breadcrumb 클릭 → 상위 이동 |
| `/kiis/funds/all` | FundListPage | "← GP 목록으로" 클릭 |

라우트 순서: `gp` 정적 세그먼트가 `:fundCode` 동적보다 먼저 매칭 → 충돌 없음

### 7-3. GP ↔ Company 교차 링크 구현

| 페이지 | 변경 내용 |
|--------|----------|
| **GPDetailPage** | PageHero에 "DART 기업 정보" 버튼 (corp_code 매칭 시), Breadcrumb에 "DART Profile →" 링크 |
| **CompanyDetailPage** | `useGPs` 훅으로 GP 매칭, "KOFIA 펀드 (N)" 링크 버튼 추가 |

### 7-4. 모바일 반응형 개선

| 파일 | 수정 내용 |
|------|----------|
| `PageHero.tsx` | actions에 `flex-wrap` 추가 (버튼 줄바꿈) |
| `GPListPage.tsx` | 정렬 바에 `flex-wrap` 추가 |
| `Tabs.tsx` | `overflow-x-auto scrollbar-hide` 가로 스크롤 |
| `DataTable.tsx` | `overflow-hidden` → `overflow-x-auto` (테이블 가로 스크롤) |
| `index.css` | `.scrollbar-hide` 유틸리티 클래스 추가 |

### 7-5. TypeScript 컴파일

`tsc --noEmit` 에러 0건 확인

---

## 8. 향후 과제

- [x] ~~백엔드 테스트 실행~~ (Session 24 완료)
- [x] ~~GP 상세 ↔ Company 상세 교차 링크~~ (Session 24 완료)
- [x] ~~모바일 반응형 뷰 확인~~ (Session 24 완료)
- [x] ~~E2E 시나리오 테스트~~ (Session 24 완료)
- [ ] 기관전용 사모펀드 GP 데이터소스 확보 (KOFIA DIS에 미포함 운용사)
- [ ] GP 카드에 미니 스파크라인 차트 추가 (AUM 추이)
- [ ] GP 비교 기능 (2~3개 GP 나란히 비교)
