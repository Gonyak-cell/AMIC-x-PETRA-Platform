# 백엔드 코드베이스 종합 평가 + 검증 보고서

> **작성일**: 2026-02-24 11:19:00
> **검증 방법**: 분석 에이전트 도출 주장 → 실제 소스 코드 1:1 대조
> **대상**: FDD, deal-mgmt, KIIS, IM 백엔드 4개 모듈

---

## 1. 모듈별 구조 요약

| 모듈 | 역할 | Python | DB 방식 | 라우터 수 | 주요 특징 |
|------|------|--------|---------|----------|----------|
| **FDD** | 재무실사 (QoE/NWC/Debt) | 3.12 | SQLAlchemy 동기 | 25 | 순수 함수 계산 엔진, RFC 7807, slowapi |
| **deal-mgmt** | M&A 거래 생명주기 | 3.11 | SQLAlchemy 비동기 | 23 | 7단계 워크플로우 상태 머신, Ralph Loop |
| **KIIS** | 기업/펀드 정보 | 3.11 | SQLAlchemy 비동기 | 17 | ElasticSearch, APScheduler, 평판 스코어링 |
| **IM** | 투자설명서 자동생성 | 3.11+ | SQLAlchemy 비동기 | 6 | Celery Chord, 멀티 LLM, RAG, Fact Check |

---

## 2. 카테고리별 평가

### 2.1 아키텍처 설계 — 8.5/10

**강점:**
- 4개 모듈 모두 Router → Service → Model 계층 분리 일관
- deal-mgmt: 7단계 워크플로우 상태 머신 (Phase 전제조건 + 리스크/컴플라이언스 게이트)
- IM: Celery Chord 5단계 파이프라인 (병렬 데이터 수집 → 분석 → 생성 → 렌더링)
- 모듈 간 HTTP 기반 느슨한 결합 (fdd_client, im_client, kiis_client)
- Cross-backend JWT Federation (FDD 토큰 → 타 모듈 자동 수용 + 사용자 자동 생성)

**약점:**
- FDD만 동기식 (psycopg2), 나머지 3개는 비동기 (asyncpg) — 불일치
- Python 버전 혼재 (3.11 vs 3.12)

### 2.2 데이터 레이어 — 8.0/10

**강점:**
- SQLAlchemy 2.0 `Mapped[T]` 타입 힌트 전체 적용
- UUID PK + TimestampMixin + 소프트 삭제 패턴 통일
- JSONB 활용 (감사 로그, AI 분석 결과, 설정 저장)
- IM: Partial Unique Index로 TOCTOU 동시성 방어
- 커넥션 풀 설정 적절 (pool_size=10~20, pre_ping, recycle)

**약점:**
- deal-mgmt 테스트가 SQLite in-memory — PostgreSQL 전용 기능(JSONB, Partial Index) 미검증
- KIIS: joinedload 누락으로 N+1 쿼리 위험 가능

### 2.3 API 설계 — 8.5/10

**강점:**
- RESTful `/api/v1/{resource}` 명명 규칙 일관
- Pydantic v2 + `@field_validator` + `@model_validator`
- FDD: RFC 7807 Problem Details (`application/problem+json`, ErrorCode 1000~9999)
- 페이지네이션 표준 (items, total, limit, offset)

**약점:**
- 에러 응답 포맷 모듈마다 상이:
  - FDD: `type/title/status/detail/code/severity` (RFC 7807)
  - deal-mgmt: `detail/code/timestamp`
  - KIIS: `detail/code/timestamp` + DART `dart_status`
  - IM: `error/details`

### 2.4 인증/인가 — 8.0/10

**강점:**
- FDD: Permission 열거형 기반 RBAC (`deal:create`, `deal:read` 등)
- deal-mgmt: JWT 클레임만 사용 (DB 조회 없음 — 경량)
- IM: RS256 비대칭키 지원 + Token Blacklist (로그아웃)
- KIIS: 2단계 Rate Limiting (미들웨어 IP + 서비스 Token Bucket)
- FDD: 가장 엄격한 CORS (메서드 6개 + 헤더 3개 명시, max_age=3600)

**약점:**
- deal-mgmt/KIIS: `allow_methods=["*"]`, `allow_headers=["*"]` (FDD보다 느슨)
- CSRF 보호 없음 (SPA + 쿠키 인증 시 필요 가능)

### 2.5 비즈니스 로직 — 9.0/10

**강점:**
- FDD: 순수 함수 엔진 (부작용 없는 QoE/NWC/Debt 계산, Decimal 정밀도)
- deal-mgmt: 상태 머신 + 전제조건 게이트 + 리스크/컴플라이언스 Closing 게이트
- KIIS: 평판 스코어링 (트렌드×0.3 + 뉴스×0.4 + 성과×0.3) + ElasticSearch Nori 한국어 검색
- IM: 멀티 프로바이더 LLM 라우팅 (섹션별 최적 모델) + RAG + Fact Check + 토큰 버짓

### 2.6 테스트 — 7.5/10

**강점:**
- deal-mgmt: 85/85 통과 (워크플로우/Closing/통합)
- KIIS: 25개 파일, pytest-httpx 외부 API 모킹
- IM: 마커 기반 조건부 실행 (slow, requires_browser, requires_plotly, golden)

**약점:**
- 전체적으로 커버리지 수치 미측정 (CI 리포트 없음)
- deal-mgmt SQLite 테스트 → PostgreSQL 고유 기능 미검증
- 엣지 케이스 (네트워크 실패, 타임아웃, 동시 요청) 테스트 부족

### 2.7 보안 — 8.0/10

**강점:**
- SQL Injection 자동 방지 (ORM)
- Pydantic 입력 검증 + 화이트리스트 업데이트 (`_UPDATABLE_FIELDS`)
- KIIS: 보안 헤더 자동 추가 (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection)
- FDD: Decimal 타입 금전 정밀도 보장
- 프로덕션 시크릿 가드 전 모듈 적용 (RuntimeError)
- CORS 오리진은 전 모듈 명시적 (와일드카드 아님)

**약점:**
- deal-mgmt JWT 기본 시크릿: 빈 문자열이 아니어서 프로덕션 가드 통과 가능
- deal-mgmt/KIIS CORS 메서드/헤더 와일드카드
- CSRF 보호 미적용

### 2.8 코드 품질 — 8.0/10

**강점:**
- 타입 힌트 거의 100% (Python 3.11+ `|` 문법)
- Ruff 린터/포매터 적용
- DRY 원칙 준수 (감사 로그 통합, 서비스 레이어 분리)
- FDD: mypy strict 모드

**약점:**
- 페이지네이션 코드 4개 모듈에서 동일 패턴 반복
- 일부 서비스가 `dict` 반환 (Pydantic 모델로 통일 필요)
- CPU 집약적 작업 (정규표현식, NLP)이 비동기 함수 내에서 블로킹

---

## 3. 허위 리뷰 검증 결과

### 검증 방법

분석 에이전트가 도출한 주요 주장 18건을 실제 소스 코드와 1:1 대조.

### ❌ 허위 양성 (False Positive) — 1건

| # | 주장 | 실제 코드 | 판정 |
|---|------|----------|------|
| 1 | **"deal-mgmt CORS `*` 모든 오리진 허용 — P0 Critical"** | `allow_origins=settings.ALLOWED_ORIGINS` → `["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]` ([config.py:21](deal-mgmt/app/core/config.py#L21)) | ❌ **허위**. `allow_methods=["*"]`, `allow_headers=["*"]`는 사실이나 오리진 와일드카드 아님 |

### ⚠️ 과장/부정확 — 3건

| # | 주장 | 실제 코드 | 판정 |
|---|------|----------|------|
| 2 | **"JWT 시크릿 P0 Critical"** | FDD: `RuntimeError` if `ENV=production` + dev secret ([config.py:40-48](fdd/backend/app/config.py#L40-L48)). deal-mgmt: 빈 문자열이 아닌 기본값 → 가드 통과 가능 ([config.py:11](deal-mgmt/app/core/config.py#L11)). KIIS: `RuntimeError` if non-DEBUG + insecure SECRET_KEY ([main.py:56-61](kiis/app/main.py#L56-L61)) | ⚠️ **과장**. P0→P1. 대부분 가드 존재, deal-mgmt만 약간의 위험 |
| 3 | **"deal-mgmt 22개 라우터"** | 실제 23개 (ldd_reports 2개 포함, [main.py:131-153](deal-mgmt/app/main.py#L131-L153)) | ⚠️ 근소 오차 |
| 4 | **"KIIS 18개 라우터"** | 실제 17개 (alerts 2개 서브라우터 포함, [main.py:148-164](kiis/app/main.py#L148-L164)) | ⚠️ 근소 오차 |

### ✅ 정확 — 14건

| # | 주장 | 검증 결과 | 근거 파일 |
|---|------|----------|----------|
| 5 | FDD RFC 7807 에러 포맷 | ✅ `application/problem+json` | [exceptions.py:109-115](fdd/backend/app/core/exceptions.py#L109-L115) |
| 6 | deal-mgmt 커스텀 에러 | ✅ `detail/code/timestamp` | [exceptions.py:53-73](deal-mgmt/app/core/exceptions.py#L53-L73) |
| 7 | KIIS 커스텀 에러 | ✅ `detail/code/timestamp/dart_status` | [exceptions.py:38-63](kiis/app/core/exceptions.py#L38-L63) |
| 8 | IM 커스텀 에러 | ✅ `error/details` | [__init__.py:49-54](im/src/api/__init__.py#L49-L54) |
| 9 | FDD 동기식 SQLAlchemy | ✅ `create_engine()`, `sessionmaker()` | [database.py:6-14](fdd/backend/app/database.py#L6-L14) |
| 10 | deal-mgmt/KIIS/IM 비동기 | ✅ `create_async_engine()` | [database.py:7-22](kiis/app/core/database.py#L7-L22) |
| 11 | KIIS SecurityHeaders | ✅ X-Content-Type-Options 등 | [main.py:38-46](kiis/app/main.py#L38-L46) |
| 12 | FDD slowapi Limiter | ✅ 60/minute 기본 | [main.py:43](fdd/backend/app/main.py#L43) |
| 13 | KIIS RateLimitMiddleware | ✅ Redis, 로그인 5회/분 | [main.py:136-142](kiis/app/main.py#L136-L142) |
| 14 | FDD CORS 엄격 | ✅ 6개 메서드 + 3개 헤더 명시 | [main.py:71-78](fdd/backend/app/main.py#L71-L78) |
| 15 | deal-mgmt/KIIS `methods=*` | ✅ `allow_methods=["*"]` | [main.py:94-100](deal-mgmt/app/main.py#L94-L100) |
| 16 | Cross-backend JWT | ✅ FDD JWT → 타 모듈 자동 수용 | 검증 완료 |
| 17 | deal-mgmt Alembic 자동 | ✅ lifespan `_run_alembic_upgrade()` | [main.py:18-33](deal-mgmt/app/main.py#L18-L33) |
| 18 | FDD 25개 라우터 ("22+") | ✅ "22+"는 25 포함 | [main.py:80-106](fdd/backend/app/main.py#L80-L106) |

### 검증 통계

```
총 검증 항목: 18건
├── ✅ 정확:       14건 (78%)
├── ⚠️ 과장/오차:  3건  (17%)
└── ❌ 허위 양성:  1건  (5%)
```

---

## 4. 검증 후 최종 점수

| 카테고리 | 초기 | 검증 후 | 변경 사유 |
|---------|------|--------|----------|
| 아키텍처 설계 | 8.5 | 8.5 | — |
| 데이터 레이어 | 8.0 | 8.0 | — |
| API 설계 | 8.5 | 8.5 | — |
| 인증/인가 | 8.0 | 8.0 | — |
| 비즈니스 로직 | 9.0 | 9.0 | — |
| 테스트 | 7.5 | 7.5 | — |
| 보안 | 7.5 | **8.0** | CORS P0 허위 양성 제거, JWT 가드 확인 |
| 코드 품질 | 8.0 | 8.0 | — |

### **검증 후 최종 점수: 8.3 / 10**

---

## 5. 검증된 개선 우선순위

| 우선순위 | 항목 | 비고 |
|---------|------|------|
| ~~P0~~ | ~~deal-mgmt CORS `*`~~ | ❌ 허위 양성 — 제거 |
| **P1** | deal-mgmt JWT 기본 시크릿 가드 강화 | 기본값이 빈 문자열 아니어서 가드 통과 가능 |
| **P1** | 에러 응답 포맷 RFC 7807 통일 | 4개 모듈 포맷 상이 |
| **P1** | KIIS N+1 쿼리 최적화 | joinedload 추가 필요 (미검증) |
| **P2** | deal-mgmt/KIIS CORS 메서드/헤더 명시 | FDD 수준으로 강화 |
| **P2** | 페이지네이션 공통 헬퍼 추출 | 4개 모듈 코드 중복 |
| **P2** | 테스트 커버리지 측정 + CI | pytest-cov 설정은 있으나 리포트 없음 |
| **P3** | FDD 동기→비동기 전환 | 일관성 향상 |
| **P3** | CPU 작업 asyncio.to_thread() | 비동기 블로킹 방지 |
