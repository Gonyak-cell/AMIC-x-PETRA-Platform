# KIIS 전체 코드리뷰

> 작성: 2026-02-13 08:36
> 대상: KIIS 프론트엔드 + 백엔드 전체

## Context
KIIS(Korea Investment Intelligence System) 모듈의 프론트엔드(18 pages, 14 hooks, 14 types, 8 components)와 백엔드(16 routers, 17 services, 14 models)에 대한 전체 코드리뷰입니다.

---

## 1. 전체 아키텍처 평가

### 긍정적
- 프론트엔드/백엔드 모두 일관된 구조 (pages→hooks→types, routers→services→models)
- FDD 참조 구현 패턴을 잘 따름
- 크로스 백엔드 JWT 인증 지원 (FDD 토큰 호환)
- 적절한 미들웨어 스택 (CORS, GZip, Security Headers, Rate Limiting)
- Lifespan 패턴으로 Redis/ES/Scheduler 생명주기 관리

### 개선 필요
- 프론트엔드 KIIS 모듈 내 유닛 테스트 **0개** (E2E만 4개 테스트)
- 백엔드 테스트 파일 미확인 (test 디렉토리 없음)
- 프론트엔드-백엔드 API 계약(contract) 문서 부재

---

## 2. 백엔드 이슈 (심각도순)

### CRITICAL

#### 2.1 SECRET_KEY 하드코딩 기본값
- **파일**: `KIIS/app/core/config.py:10`
- **문제**: `SECRET_KEY: str = "change-this-to-a-random-secret-key"` — 기본값이 평문 문자열
- **위험**: `.env` 미설정 시 프로덕션에서도 이 값 사용 가능
- **수정**: 기본값 제거하고 환경변수 필수화, 또는 시작 시 검증 추가

#### 2.2 DB 세션 자동 커밋 패턴
- **파일**: `KIIS/app/core/database.py:28`
- **문제**: `get_db()`가 yield 후 자동 `commit()` → GET 요청에서도 불필요한 커밋 발생
- **위험**: 읽기 전용 요청에서 의도치 않은 DB 상태 변경 가능
- **수정**: 서비스에서 명시적 `commit()` 호출, `get_db()`는 세션만 제공

#### 2.3 reputation_service에서 이중 커밋
- **파일**: `KIIS/app/services/reputation_service.py:138`
- **문제**: `await db.commit()` 명시 호출 + `get_db()`의 자동 커밋 = 이중 커밋
- **위험**: 트랜잭션 경계 혼란, 부분 커밋 가능성

#### 2.4 ElasticSearch 검색 와일드카드 필드
- **파일**: `KIIS/app/services/search_service.py:56`
- **문제**: `"fields": ["*"]` — 모든 필드 대상 검색
- **위험**: 내부 필드(ID, 해시 등)까지 검색 대상에 포함, 성능 저하
- **수정**: 검색 대상 필드를 인덱스별로 명시 지정

### HIGH

#### 2.5 인증 없는 엔드포인트들
- **파일**: `KIIS/app/routers/company.py`, `dashboard.py`, `news.py` 등
- **문제**: 대부분의 GET 엔드포인트에 인증 의존성(Depends) 없음
- **위험**: 인증 없이 모든 데이터 조회 가능
- **참고**: 의도적 설계일 수 있으나 명시적 문서화 필요

#### 2.6 Reindex가 전체 테이블 로드
- **파일**: `KIIS/app/services/search_service.py:112-191`
- **문제**: `select(Company)` 등으로 전체 레코드를 메모리에 로드
- **위험**: 대량 데이터 시 OOM (Out of Memory)
- **수정**: 배치 처리(chunk) 또는 `yield_per()` 사용

#### 2.7 Rate Limiter 경쟁 조건
- **파일**: `KIIS/app/middleware/rate_limit.py:86-111`
- **문제**: `get` → 검사 → `incr` 사이에 경쟁 조건 (TOCTOU)
- **수정**: Redis `MULTI/EXEC` 또는 Lua 스크립트로 원자적 처리

#### 2.8 company.py에서 내부 import
- **파일**: `KIIS/app/routers/company.py:52`
- **문제**: `from fastapi import HTTPException`이 함수 내부에서 import
- **수정**: 파일 상단으로 이동

### MEDIUM

#### 2.9 SearchService가 매 요청마다 인스턴스 생성
- **파일**: `KIIS/app/routers/search.py:23-25`
- **문제**: `get_search_service()`가 매번 `SearchService()` 새로 생성
- **수정**: 싱글턴 또는 앱 상태에 바인딩

#### 2.10 스케줄러 작업 에러 핸들링 미확인
- **파일**: `KIIS/app/tasks/scheduler.py`
- **문제**: 개별 작업(run_dart_sync 등) 내부 에러 핸들링이 누락되면 스케줄러 전체에 영향
- **수정**: 각 작업에 try/except + 로깅 보장

#### 2.11 `_InMemoryStore` 메모리 누수
- **파일**: `KIIS/app/middleware/rate_limit.py:120-158`
- **문제**: 만료된 키가 다음 접근 시에만 삭제됨 → 접근되지 않는 키는 영구 보존
- **수정**: 주기적 정리(TTL sweep) 또는 maxsize 제한 추가

---

## 3. 프론트엔드 이슈 (심각도순)

### CRITICAL

#### 3.1 시맨틱 HTML 위반
- **파일**: `kiis/pages/NewsListPage.tsx:108`
- **문제**: `<div role="button" tabIndex={0}>` — 실제 `<button>` 요소 미사용
- **영향**: 키보드 접근성 저하 (Enter/Space 키 미지원 가능)
- **수정**: `<button>` 또는 `<a>` 태그로 변경

#### 3.2 DashboardPage 하드코딩 라벨 매칭
- **파일**: `kiis/pages/DashboardPage.tsx:18-20`
- **문제**:
  ```ts
  const LABEL_COMPANIES = "기업";
  const LABEL_FUNDS = "펀드";
  const LABEL_DEALS = "딜";
  ```
  백엔드 문자열에 의존 → 백엔드가 한 글자만 바꿔도 깨짐
- **수정**: ID 기반 매칭 또는 인덱스 기반 접근

#### 3.3 SearchBar 타입 캐스팅
- **파일**: `kiis/components/SearchBar.tsx:84`
- **문제**: `item.index as DisplayType` — 런타임 검증 없는 타입 단언
- **수정**: 검증 함수 또는 Zod 스키마로 파싱

### HIGH

#### 3.4 페이지네이션 UI 중복 (6개 페이지)
- **파일**: `CompanyListPage`, `NewsListPage`, `SanctionListPage`, `WatchlistPage`, `ManagerListPage`, `DisclosurePage`
- **문제**: 동일한 페이지네이션 버튼 마크업이 6곳에 복사-붙여넣기
- **수정**: `<Pagination>` 공유 컴포넌트 추출

#### 3.5 variant 맵 중복 (8+ 파일)
- **파일**: `CompanyDetailPage`, `WatchlistPage`, `SanctionListPage` 등
- **문제**: `Record<string, "error" | "warning" | "info">` 형태의 매핑이 반복
- **수정**: `kiis/constants/variants.ts`로 중앙화

#### 3.6 CompanyDetailPage 5개 독립 쿼리
- **파일**: `kiis/pages/CompanyDetailPage.tsx`
- **문제**: reputation, disclosures, deals, sanctions, watchlist 등 5개 `useQuery`가 개별 로딩 상태
- **영향**: 부분 렌더링으로 UI 깜빡임, 사용자 경험 저하
- **수정**: `useSuspenseQueries` 또는 로딩 상태 통합

#### 3.7 useNews/useDisclosures에서 `null` body 전달
- **파일**: `kiis/hooks/useNews.ts:35`, `useDisclosures.ts:36`
- **문제**: `kiisApi.post("/news/collect", null, { params })` — null이 직렬화됨
- **수정**: `undefined` 또는 빈 객체로 변경

#### 3.8 테스트 부재
- **위치**: `src/modules/kiis/` 내 테스트 파일 0개
- **문제**: 훅, 컴포넌트, 페이지에 대한 유닛 테스트 전무
- **영향**: 리그레션 탐지 불가
- **권장**: 최소한 핵심 훅(useCompanies, useSearch, useWatchlist) 테스트 추가

### MEDIUM

#### 3.9 접근성 미비
| 위치 | 이슈 |
|------|------|
| `ReputationBadge.tsx` | 숫자 점수에 `aria-label` 없음 |
| `SentimentIndicator.tsx` | 점수 해석 미설명 |
| `WatchlistPage.tsx:143` | 테이블 내 인라인 버튼 레이블 없음 |
| 여러 페이지 | 로딩 상태를 스크린 리더에 알리지 않음 |

#### 3.10 입력 검증 부재
- `ValuationModal.tsx:74` — 숫자 형식/범위 미검증
- `EntityResolutionPage.tsx:75` — trim 후 빈 문자열 통과 가능

#### 3.11 매직 넘버
- `ReputationBadge.tsx:11-15` — 점수 임계값(80, 60, 40) 하드코딩
- `SentimentIndicator.tsx:46` — 0~1 범위 가정, 미검증
- `SearchBar.tsx` — 디바운스 300ms 미문서화

#### 3.12 DataTable 컬럼 정의 미메모화
- **파일**: `CompanyFinancials.tsx:43-72` 등
- **문제**: 컬럼 정의가 매 렌더 시 재생성
- **수정**: `useMemo`로 래핑

#### 3.13 KiisRoutes에서 Lazy Loading 미적용
- **파일**: `kiis/KiisRoutes.tsx:1-19`
- **문제**: 18개 페이지를 모두 정적 import → 초기 번들 크기 증가
- **수정**: `React.lazy()` + `Suspense`로 각 페이지 지연 로딩

### LOW

#### 3.14 유사도 백분율 계산 반복
- `EntityResolutionPage.tsx:46,206` — `(row.similarity * 100).toFixed(1)` 중복
- **수정**: 유틸 함수 추출

#### 3.15 모달 상태 stale 가능성
- `PortfolioPage.tsx:56` — `modalItem`이 데이터 리페치 시 구 데이터 참조 가능

---

## 4. FE-BE 정합성 이슈

| 프론트엔드 | 백엔드 | 이슈 |
|-----------|--------|------|
| `useCompanies` → `GET /companies` | `company.py` — 인증 없음 | 의도적이라면 문서화 필요 |
| `useNews` → `POST /news/collect` body=null | 확인 필요 | null vs undefined 동작 차이 |
| `DashboardPage` — 라벨 문자열 매칭 | `dashboard.py` — 라벨 반환 형태 | 타이트 커플링 위험 |
| `useSearch` — `params.q.length >= 2` | `search.py` — `min_length=1` | 검증 기준 불일치 (FE=2, BE=1) |

---

## 5. E2E 테스트 분석

### 현황
- `kiis-deep.spec.ts`: 4개 테스트 (company table, badge, columns, empty state)
- `kiis-companies.page.ts`: Page Object 패턴 사용

### 커버리지 갭
| 페이지 | E2E 테스트 | 상태 |
|--------|-----------|------|
| CompanyListPage | O (4개) | 양호 |
| DashboardPage | X | **미구현** |
| NewsListPage | X | **미구현** |
| WatchlistPage | X | **미구현** |
| SanctionListPage | X | **미구현** |
| 나머지 13개 | X | 미구현 |

---

## 6. 권장 개선 우선순위

### Phase 1 — 보안/안정성 (즉시)
1. `SECRET_KEY` 기본값 제거 + 시작 시 검증
2. `get_db()` 자동 커밋 제거 → 명시적 커밋
3. 인증 필요 엔드포인트 명시적 구분 및 문서화
4. ES 검색 필드 와일드카드 제거

### Phase 2 — 코드 품질 (단기)
5. `<Pagination>` 공유 컴포넌트 추출
6. variant 맵 중앙화 (`kiis/constants/`)
7. SearchBar 타입 검증 강화
8. 시맨틱 HTML 수정 (div→button)

### Phase 3 — 테스트 (중기)
9. 핵심 훅 유닛 테스트 추가 (useCompanies, useWatchlist, useSearch)
10. 주요 페이지 E2E 테스트 추가 (Dashboard, News, Watchlist)
11. 백엔드 서비스 유닛 테스트 추가

### Phase 4 — 성능/UX (장기)
12. KiisRoutes 지연 로딩 적용
13. CompanyDetailPage 로딩 상태 통합
14. DataTable 컬럼 정의 메모화
15. 접근성 개선 (aria-label, 로딩 알림)

---

## 7. 긍정적 평가 요약

- `any` 타입 사용 **0건** — 훌륭한 타입 안전성
- TanStack Query v5 패턴 일관성 높음
- 쿼리 키 네이밍 `["kiis", resource, ...]` 규칙 준수
- `enabled` 가드로 의존적 쿼리 정확히 제어
- 백엔드 Pydantic v2 + FastAPI 패턴 적절
- Rate Limiting + Redis 폴백 견고한 설계
- 크로스 백엔드 JWT (FDD↔KIIS) 호환 구현 우수
- APScheduler 기반 백그라운드 작업 체계적 구성
- Security Headers 미들웨어 적용
