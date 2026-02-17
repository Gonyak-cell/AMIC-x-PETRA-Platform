# KIIS 펀드 검색 API 데이터 리서치 결과

> 작성일: 2026-02-17 18:10
> 최종 수정: 2026-02-17 18:25

## Context

KIIS 모듈에 펀드 검색 기능을 강화하기 위해, 현재 백엔드/프론트엔드 구현 현황과 외부 데이터 소스를 종합 분석한다.

---

## 1. 현재 데이터 소스 현황

### 1.1 KOFIA DIS (금융투자협회) — 주요 펀드 데이터 소스

| 서비스 ID | 용도 | 파라미터 |
|-----------|------|---------|
| `SDIS01006001000` | 펀드 목록 검색 | `companyNm`, `pageIndex`, `pageUnit` |
| `SDIS01006001001` | 펀드 상세 조회 | `fundCd` |
| `SDIS01008001000` | 운용 전문인력 | `fundCd`, `companyNm`, `pageIndex`, `pageUnit` |

- 통신: WebSquare POST (`/websquare/engine/proworks/callServletService.jsp`)
- Rate Limit: 분당 20회, 일일 1,000회, 최소 3초 간격
- 캐싱: 6시간 TTL (Redis)

### 1.2 DART (금융감독원) — 기업/공시 데이터

| 엔드포인트 | 용도 | 캐싱 |
|-----------|------|------|
| `corpCode.xml` | 기업 고유번호 | - |
| `company.json` | 기업 개황 (대표자, 업종, 주소 등) | 24시간 |
| `list.json` | 공시 목록 검색 | 1시간 |
| `fnlttSinglAcntAll.json` | 재무제표 (전체 단일회사) | 12시간 |
| `exctSttus.json` | 제재 내역 | - |

- 인증: API Key (`DART_API_KEY`)
- Rate Limit: 분당 900회, 일일 9,000회

### 1.3 REITs (부동산통합정보시스템) — 리츠 데이터

- HTML 크롤링 (BeautifulSoup)
- Rate Limit: 분당 20회, 일일 500회

### 1.4 RSS 뉴스 — 업계 뉴스

- 소스: platum, dealsite, venturesquare

---

## 2. KOFIA에서 가져오는 펀드 필드 (전체)

### 2.1 펀드 목록 (SDIS01006001000)

| KOFIA 필드 | 백엔드 필드 | 타입 | 검색 가능 | 설명 |
|-----------|-----------|------|---------|------|
| `fundCd` | fund_code | str(50) | PK | 펀드 표준코드 |
| `fundNm` | fund_name | str(300) | **인덱스** | 펀드명 |
| `companyNm` | company_name | str(200) | **인덱스, 검색 파라미터** | 운용사명 |
| `companyCd` | company_code | str(50) | - | 운용사 코드 |
| `totalAmt` | total_amount | Numeric(20,0) | - | 설정액 (원) |
| `establishedDt` | established_date | date | - | 설정일 (YYYYMMDD) |
| `maturityDt` | maturity_date | date | - | 만기일 (YYYYMMDD) |

### 2.2 펀드 상세 (SDIS01006001001) — 추가 필드

| KOFIA 필드 | 백엔드 필드 | 타입 | 설명 |
|-----------|-----------|------|------|
| `fundCategory` | fund_category | str(50) | 분류 (VC/PEF) |
| `mgmtFeeRate` | management_fee_rate | Numeric(5,2) | 운용보수율 (%) |
| `perfFeeRate` | performance_fee_rate | Numeric(5,2) | 성과보수율 (%) |
| `fundDesc` | description | Text | 펀드 설명 |
| `sourceUrl` | source_url | str(500) | 출처 URL |

### 2.3 자동 계산 필드

| 필드 | 로직 | 설명 |
|------|------|------|
| `fund_type` | 펀드명 키워드 분류 | blind/project (프로젝트/블라인드 키워드 매칭) |
| `vintage_year` | `established_date.year` | 빈티지 연도 |
| `is_maturity_alert` | 7~10년차 OR 만기 2년 이내 | 회수 집중 구간 경고 |

### 2.4 운용 전문인력 (SDIS01008001000)

| KOFIA 필드 | 백엔드 필드 | 타입 | 설명 |
|-----------|-----------|------|------|
| `managerNm` | manager_name | str(100) | 운용인력 이름 |
| `position` | position | str(100) | 직책 |
| `role` | role | str(100) | 역할 (펀드매니저/심사역) |
| `careerYears` | career_years | int | 경력 년수 |
| `education` | education | str(200) | 학력 |
| `certifications` | certifications | Text | 자격증 |
| `appointedDt` | appointed_date | date | 임명일 |
| `resignedDt` | resigned_date | date | 사임일 |

---

## 3. 프론트엔드-백엔드 GAP 분석 (핵심)

### 3.1 검색 파라미터 불일치 → 구현 완료 현황

| 파라미터 | 프론트엔드 | 백엔드 API | 필터 방식 | 상태 |
|---------|-----------|-----------|---------|------|
| `company_name` | FundListParams | Query param → KOFIA 서버 필터 | KOFIA `companyNm` | ✅ 정상 |
| `fund_type` | FundListParams | Query param → 쉼표→리스트 | 메모리 필터 (`in`) | ✅ **구현 완료** |
| `fund_name` | FundListParams | Query param | 메모리 필터 (부분 매칭) | ✅ **구현 완료** |
| `legal_type` | FundListParams | Query param → 쉼표→리스트 | 메모리 필터 (키워드 분류 후 `in`) | ✅ **구현 완료** |
| `asset_class` | FundListParams | Query param → 쉼표→리스트 | 메모리 필터 (키워드 분류 후 `in`) | ✅ **구현 완료** |
| `fund_status` | FundListParams | Query param → 쉼표→리스트 | 메모리 필터 (상태 추론 후 `in`) | ✅ **구현 완료** |
| `vintage_from/to` | FundListParams | Query param | 메모리 필터 (범위) | ✅ **구현 완료** |
| `amount_min/max` | FundListParams | Query param | 메모리 필터 (억원→원 변환 후 범위) | ✅ **구현 완료** |
| `sort_by/sort_order` | FundListParams | Query param | 메모리 정렬 (None 뒤로) | ✅ **구현 완료** |
| `page/size` | FundListParams | Query param | 서버 페이지네이션 | ✅ 정상 |

### 3.2 GAP 유형별 분류

**Type A — DB에 컬럼 있지만 API에서 필터 미지원** (즉시 구현 가능):
- `fund_name`: 펀드명 검색 (DB 인덱스 존재)
- `vintage_from/to`: 빈티지 범위 필터 (DB 컬럼 존재)
- `amount_min/max`: 설정액 범위 필터 (DB 컬럼 존재)

**Type B — DB에 컬럼 자체가 없음** (마이그레이션 + 분류 로직 필요):
- `legal_type`: 법률상 유형 (기관전용 사모/일반 사모/공모)
- `asset_class`: 자산 유형 (VC/PEF/부동산/인프라/메자닌/FoF)
- `fund_status`: 펀드 상태 (운용중/회수기간/청산)

**Type C — 동작하지만 비효율적**:
- `fund_type`: KOFIA에서 전체 조회 후 클라이언트 필터링 (서버 필터로 전환 필요)

---

## 4. KOFIA DIS API에서 제공하지 않는 데이터

| 필드 | KOFIA 제공 | 대안 |
|------|-----------|------|
| `legal_type` | **X** | 펀드명 키워드 분류 또는 수동 입력 |
| `asset_class` | **X** | fund_category(VC/PEF) 기반 매핑 또는 키워드 분류 |
| `fund_status` | **X** | is_active + is_maturity_alert + maturity_date 조합으로 추론 |

### 4.1 자동 분류 가능성 분석

**legal_type 추론 로직** (가능):
```
- "기관전용" / "전문투자자" 키워드 → professional_private
- "일반" / "PEF" 키워드 → general_private
- "공모" 키워드 → public
- 기본값: professional_private (대부분 기관전용)
```

**asset_class 추론 로직** (부분 가능):
```
- fund_category = "VC" → vc
- fund_category = "PEF" → pef
- "부동산" / "리얼티" 키워드 → real_estate
- "인프라" / "SOC" 키워드 → infra
- "메자닌" / "전환사채" 키워드 → mezzanine
- "재간접" / "FoF" / "모태" 키워드 → fund_of_funds
- 기본값: fund_category 기반
```

**fund_status 추론 로직** (가능):
```
- is_active=False → liquidated
- is_maturity_alert=True → harvest
- 그 외 → active
```

---

## 5. 데이터 흐름 (현재 vs 개선 후)

### 5.1 현재 흐름

```
프론트엔드 → GET /api/kiis/kofia/funds?company_name=...&fund_type=...
                    ↓
              FastAPI Router (company_name, fund_type, page, size만 수락)
                    ↓
              KOFIAService.search_funds() → KOFIA DIS API 직접 호출
                    ↓
              응답 파싱 → fund_type 클라이언트 필터링 → 반환
```

**문제점**:
1. DB를 거치지 않고 매번 KOFIA API 직접 호출
2. legal_type, asset_class, fund_status 필터 무시됨
3. 범위 검색(빈티지, 설정액) 불가
4. fund_type도 전체 데이터를 가져온 후 클라이언트에서 필터링

### 5.2 개선 후 흐름 (제안)

```
프론트엔드 → GET /api/kiis/kofia/funds?전체 파라미터
                    ↓
              FastAPI Router (모든 필터 파라미터 수락)
                    ↓
              [DB 우선 조회] → funds 테이블 SQL 쿼리
              ├─ WHERE company_name ILIKE %keyword%
              ├─ AND fund_name ILIKE %keyword%
              ├─ AND fund_type = 'blind'
              ├─ AND legal_type = 'professional_private'
              ├─ AND asset_class IN ('vc', 'pef')
              ├─ AND fund_status = 'active'
              ├─ AND vintage_year BETWEEN 2018 AND 2023
              ├─ AND total_amount BETWEEN 10000000000 AND 50000000000
              └─ ORDER BY established_date DESC
                    ↓
              DB 결과가 없으면 → KOFIA DIS API 호출 → DB 저장 → 재쿼리
                    ↓
              FundListResponse 반환
```

---

## 6. 추가 활용 가능한 외부 데이터

### 6.1 DART 기업 정보 연계

| 데이터 | DART 엔드포인트 | 활용 |
|--------|---------------|------|
| 대표자명, 설립일, 주소 | company.json | 운용사 상세 정보 |
| 재무제표 | fnlttSinglAcntAll.json | 운용사 재무 건전성 |
| 공시 목록 | list.json | 운용사 공시 이력 |
| 제재 내역 | exctSttus.json | 운용사 리스크 평가 |

### 6.2 운용인력 역검색

현재: 펀드 → 운용인력 (정방향만)
추가: 운용인력명 → 관련 펀드 목록 (역방향 검색 가능)

---

## 7. 검색 필드 우선순위 (구현 난이도별)

### Tier 1 — ✅ 구현 완료 (메모리 필터링 기반)
1. ✅ `fund_name` 검색 (부분 매칭, 대소문자 무시)
2. ✅ `vintage_from/to` 범위 필터
3. ✅ `amount_min/max` 범위 필터 (억원 단위 → 원 단위 변환)
4. ✅ 정렬 기능 (`sort_by`, `sort_order` — None 값 뒤로)
5. ✅ `fund_type` 복수 선택 (쉼표 구분 → 리스트 `in` 매칭)
6. ✅ `legal_type` 키워드 자동 분류 + 복수 선택 필터
7. ✅ `asset_class` 키워드/카테고리 매핑 + 복수 선택 필터
8. ✅ `fund_status` 상태 추론 + 복수 선택 필터

### Tier 2 — 미구현 (DB 컬럼 추가 + 서버 사이드 필터)
9. DB 우선 조회 패턴 (KOFIA API → DB 캐시 → SQL 필터)
10. legal_type, asset_class, fund_status DB 컬럼 영속화 (현재는 요청마다 재분류)

### Tier 3 — 미구현 (아키텍처 변경)
11. 운용인력 역검색 (매니저명 → 펀드 목록)
12. ElasticSearch 풀텍스트 통합 검색

---

## 8. 핵심 파일 경로

### 백엔드
- `kiis/app/routers/kofia.py` — 펀드 API 엔드포인트 (3개)
- `kiis/app/services/kofia_service.py` — KOFIA 연동 서비스
- `kiis/app/models/fund.py` — Fund, FundManager ORM 모델
- `kiis/app/schemas/fund.py` — Pydantic 스키마
- `kiis/app/services/dart_service.py` — DART 연동 서비스
- `kiis/app/services/reits_service.py` — REITs 크롤링 서비스

### 프론트엔드
- `amic-platform/src/modules/kiis/types/fund.ts` — TypeScript 타입
- `amic-platform/src/modules/kiis/hooks/useFunds.ts` — API 훅 (3개)
- `amic-platform/src/modules/kiis/hooks/useFundFilters.ts` — 필터 상태 관리
- `amic-platform/src/modules/kiis/pages/FundListPage.tsx` — 목록 페이지
- `amic-platform/src/modules/kiis/pages/FundDetailPage.tsx` — 상세 페이지
- `amic-platform/src/modules/kiis/components/FundFilterPanel.tsx` — 필터 UI
- `amic-platform/src/modules/kiis/constants/fundFilters.ts` — 필터 상수

### 마이그레이션
- `kiis/migrations/versions/380a3e3f150d_add_legal_type_asset_class_to_funds.py` — legal_type, asset_class 추가 (이미 존재)

---

## 9. 구현 세부사항 (2026-02-17 완료)

### 9.1 백엔드 변경

**kofia.py** (라우터):
- `fund_type`, `legal_type`, `asset_class`, `fund_status` — 쉼표 구분 문자열 쿼리 파라미터
- `_csv()` 헬퍼: 쉼표 구분 문자열 → `list[str] | None` 변환
- 복수 선택 파라미터는 OR 로직으로 동작 (하나라도 매칭되면 포함)

**kofia_service.py** (서비스 레이어):
- `classify_legal_type()`: 펀드명 키워드 → professional_private / general_private / public
- `classify_asset_class()`: 펀드명+카테고리 키워드 → vc / pef / real_estate / infra / mezzanine / fund_of_funds
- `determine_fund_status()`: is_active + is_maturity_alert → active / harvest / liquidated
- `_parse_fund_list()`: 파싱 시 3개 분류 필드 자동 계산
- `search_funds()`: 로컬 필터 있을 시 KOFIA에서 100건 가져와 메모리 필터링 후 페이지네이션 재적용
- `_apply_filters()`: fund_types, legal_types, asset_classes, fund_statuses — `in` 연산자 매칭
- `_apply_sort()`: 4개 필드 정렬 지원, None 값은 항상 뒤로

### 9.2 프론트엔드 변경

**fund.ts**: `FundSortField`, `FundListParams` 완전 타입 정의
**useFundFilters.ts**: URL searchParams ↔ API params 양방향 동기화
**fundFilters.ts**: 필터 옵션 상수, 라벨 매핑, 설정액 프리셋 파서
**FundFilterPanel.tsx**: 검색 + 칩 토글 + 빈티지 드롭다운 + 설정액 프리셋 + 태그 표시
**FundListPage.tsx**: 필터 패널 + DataTable + Pagination 통합

### 9.3 데이터 흐름 (최종)

```
사용자 → FundFilterPanel (Chip 토글)
  → URL searchParams (쉼표 구분: "vc,pef")
  → useFundFilters → FundListParams
  → useFunds → GET /kofia/funds?asset_class=vc,pef&...
  → kofia.py: _csv("vc,pef") → ["vc", "pef"]
  → search_funds(asset_classes=["vc", "pef"])
  → KOFIA DIS API (100건 fetch)
  → _parse_fund_list (classify_asset_class 자동 분류)
  → _apply_filters (f.asset_class in ["vc", "pef"])
  → _apply_sort → 페이지네이션 → FundListResponse
```

### 9.4 한계점

1. **KOFIA API 100건 제한**: 로컬 필터 사용 시 KOFIA에서 최대 100건만 가져옴 → 전체 데이터 대상 필터링 불가
2. **분류 정확도**: 키워드 기반 자동 분류는 100% 정확하지 않음 (예: "블라인드" 키워드가 없는 블라인드 펀드)
3. **실시간 재분류**: 매 요청마다 분류 재계산 (DB 영속화 없음)
4. **정렬**: KOFIA 서버 정렬이 아닌 메모리 정렬 → 100건 내에서만 정렬됨
