# KIIS 통합 계획서 — 진행 현황 + 잔여 로드맵

> **통합일**: 2026-02-09
> **원본 문서**: `KIIS_구현계획서.md`, `KIIS_실행계획_v2.md`, `Sprint3_구현계획서.md`
> **Git**: master 브랜치 (commit: `9e3551a`)

---

## 1. 전체 진행 현황 요약

### 1.1 Phase별 완료율

| Phase | 기간 | 상태 | 완료율 | 비고 |
|-------|------|------|--------|------|
| **Phase 1** | Week 1-4 | ✅ 완료 | **100%** | DART + KOFIA + 리츠 + Entity Resolution |
| **Phase 2** | Week 5-8 | ✅ 완료 | **100%** | 뉴스 + NLP + 평판 + 딜 소싱 |
| **Phase 3** | Week 9-12 | 🔲 미착수 | **0%** | P2 기능 + 검색 + 인증 + QA |

### 1.2 스프린트별 상세 현황

| 스프린트 | 주차 | 상태 | 완료 티켓 | 전체 티켓 |
|----------|------|------|-----------|-----------|
| Sprint 1 | W4 | ✅ 완료 | 14/14 | DB + Redis + 뉴스 수집 |
| Sprint 2 | W5 | ✅ 완료 | 10/10 | Entity Resolution + NLP |
| Sprint 3 | W6 | ✅ 완료 | 11/11 | 평판 스코어링 + 딜 소싱 |
| Sprint 4 | W7-8 | 🔲 미착수 | 0/15 | P2 기능 4개 (포트폴리오, KeyMan, 제재, DeepLink) |
| Sprint 5 | W9-10 | 🔲 미착수 | 0/15 | ElasticSearch + JWT + 대시보드 + 알림 |
| Sprint 6 | W11-12 | 🔲 미착수 | 0/7 | QA + 배포 |

### 1.3 구현 완료된 기능 (P1 핵심 기능 전부 완료)

#### Data Collection Layer (수집 계층)
- ✅ **DART API 연동** — 기업코드, 개황, 재무제표, 공시, 제재
- ✅ **KOFIA 크롤러** — 펀드 조회, 상세, 운용인력, 블라인드/프로젝트 분류, 만기 알림
- ✅ **리츠 파서** — 목록, 상세, 자산 구성, 자기관리/위탁관리 분류, 70% 자산비율 경고

#### Processing Layer (처리 계층)
- ✅ **뉴스 수집** — RSS 피드 3개 소스 (플래텀, 딜사이트, 벤처스퀘어), 중복 감지, HTML 정제
- ✅ **NLP 파이프라인** — kiwipiepy 형태소 분석, 감성 분석, NER 투자정보 추출
- ✅ **Entity Resolution** — 한글 자모 분해 유사도, 별칭 사전, 정규화

#### Intelligence Layer (분석 계층)
- ✅ **평판 스코어링** — KIIS 평판 지수 (트렌드 0.3 + 뉴스 0.4 + 성과 0.3), Rising/Stable/Risk 태그
- ✅ **딜 소싱 분석** — 섹터 분류 (11종), 투자 단계 추정 (7종), 연도별 트렌드

#### Infrastructure (인프라)
- ✅ **PostgreSQL 16 + Redis 7** — Docker Compose
- ✅ **Rate Limiter** — 토큰 버킷 (분/일 2중 제한)
- ✅ **Redis 캐싱** — @cache() 데코레이터, TTL 기반
- ✅ **테스트** — pytest-asyncio, 14개 파일 200+ 테스트 케이스

---

## 2. 구현 완료 상세

### 2.1 파일 목록 (전체 구현 파일)

#### Core (5개)
| 파일 | 설명 | 상태 |
|------|------|------|
| `app/main.py` | FastAPI 앱, CORS, lifespan, 라우터 등록 | ✅ |
| `app/core/config.py` | Pydantic Settings (.env) | ✅ |
| `app/core/database.py` | SQLAlchemy 2.0 async engine | ✅ |
| `app/core/redis.py` | Redis async 클라이언트 풀 | ✅ |
| `app/core/exceptions.py` | DARTAPIError, RateLimitExceededError | ✅ |

#### Models (7개)
| 파일 | 모델 | 상태 |
|------|------|------|
| `app/models/base.py` | Base, TimestampMixin | ✅ |
| `app/models/company.py` | Company, CompanyAlias | ✅ |
| `app/models/fund.py` | Fund, FundManager | ✅ |
| `app/models/reits.py` | REITs, REITsAsset | ✅ |
| `app/models/news.py` | NewsArticle | ✅ |
| `app/models/reputation.py` | ReputationScore, ReputationHistory | ✅ |
| `app/models/deal.py` | Deal, DealSector, DealStage | ✅ |

#### Services (7개)
| 파일 | 서비스 | 상태 |
|------|--------|------|
| `app/services/dart_service.py` | DART API 연동 | ✅ |
| `app/services/kofia_service.py` | KOFIA 크롤링 | ✅ |
| `app/services/reits_service.py` | 리츠 파싱 | ✅ |
| `app/services/news_service.py` | 뉴스 RSS 수집 | ✅ |
| `app/services/nlp_service.py` | 형태소/감성/NER | ✅ |
| `app/services/reputation_service.py` | 평판 스코어링 | ✅ |
| `app/services/deal_service.py` | 딜 소싱 분석 | ✅ |

#### Routers (8개)
| 파일 | 엔드포인트 | 상태 |
|------|-----------|------|
| `app/routers/dart.py` | `/api/v1/dart/*` | ✅ |
| `app/routers/kofia.py` | `/api/v1/kofia/*` | ✅ |
| `app/routers/reits.py` | `/api/v1/reits/*` | ✅ |
| `app/routers/company.py` | `/api/v1/companies/*` | ✅ |
| `app/routers/news.py` | `/api/v1/news/*` | ✅ |
| `app/routers/entity.py` | `/api/v1/entities/*` | ✅ |
| `app/routers/analysis.py` | `/api/v1/analysis/*` | ✅ |
| `app/routers/deals.py` | `/api/v1/deals/*` | ✅ |

#### Schemas (8개)
| 파일 | 상태 |
|------|------|
| `app/schemas/dart.py` | ✅ |
| `app/schemas/fund.py` | ✅ |
| `app/schemas/reits.py` | ✅ |
| `app/schemas/company.py` | ✅ |
| `app/schemas/news.py` | ✅ |
| `app/schemas/entity.py` | ✅ |
| `app/schemas/analysis.py` | ✅ |
| `app/schemas/deal.py` | ✅ |

#### Utilities (4개)
| 파일 | 설명 | 상태 |
|------|------|------|
| `app/utils/http_client.py` | httpx async + exponential backoff | ✅ |
| `app/utils/rate_limiter.py` | 토큰 버킷 Rate Limiter | ✅ |
| `app/utils/cache.py` | Redis 캐싱 데코레이터 | ✅ |
| `app/utils/entity_resolver.py` | 한글 유사도 + 별칭 매칭 | ✅ |

#### Tests (14개)
| 파일 | 상태 |
|------|------|
| `tests/conftest.py` | ✅ |
| `tests/test_dart_service.py` | ✅ |
| `tests/test_kofia_service.py` | ✅ |
| `tests/test_reits_service.py` | ✅ |
| `tests/test_news_service.py` | ✅ |
| `tests/test_nlp_service.py` | ✅ |
| `tests/test_reputation_service.py` | ✅ |
| `tests/test_deal_service.py` | ✅ |
| `tests/test_entity_resolver.py` | ✅ |
| `tests/test_cache.py` | ✅ |
| `tests/test_models.py` | ✅ |
| `tests/test_health.py` | ✅ |

### 2.2 API 엔드포인트 현황 (전체 24개)

| 도메인 | Method | Path | 상태 |
|--------|--------|------|------|
| **DART** | GET | `/api/v1/dart/companies` | ✅ |
| | GET | `/api/v1/dart/companies/{corp_code}` | ✅ |
| | GET | `/api/v1/dart/companies/{corp_code}/financials` | ✅ |
| | GET | `/api/v1/dart/disclosures` | ✅ |
| | GET | `/api/v1/dart/sanctions` | ✅ |
| **KOFIA** | GET | `/api/v1/kofia/funds` | ✅ |
| | GET | `/api/v1/kofia/funds/{fund_code}` | ✅ |
| | GET | `/api/v1/kofia/managers` | ✅ |
| **REITs** | GET | `/api/v1/reits/` | ✅ |
| | GET | `/api/v1/reits/{reits_code}` | ✅ |
| | GET | `/api/v1/reits/{reits_code}/assets` | ✅ |
| **Company** | GET | `/api/v1/companies/` | ✅ |
| | GET | `/api/v1/companies/{corp_code}` | ✅ |
| **News** | GET | `/api/v1/news/` | ✅ |
| | POST | `/api/v1/news/collect` | ✅ |
| | POST | `/api/v1/news/analyze_sentiment` | ✅ |
| **Entity** | POST | `/api/v1/entities/resolve` | ✅ |
| | POST | `/api/v1/entities/aliases` | ✅ |
| **Analysis** | GET | `/api/v1/analysis/reputation` | ✅ |
| | GET | `/api/v1/analysis/reputation/{corp_code}` | ✅ |
| | GET | `/api/v1/analysis/reputation/{corp_code}/history` | ✅ |
| | POST | `/api/v1/analysis/calculate` | ✅ |
| **Deals** | GET | `/api/v1/deals/by-company/{corp_code}` | ✅ |
| | GET | `/api/v1/deals/by-sector` | ✅ |
| | GET | `/api/v1/deals/by-stage` | ✅ |
| | GET | `/api/v1/deals/trends` | ✅ |

---

## 3. 미구현 잔여 작업 (Phase 3: Sprint 4-6)

### 3.1 Sprint 4 — P2 기능 일괄 병렬 구현 (Week 7-8)

> **목표:** 4개 P2 기능을 모두 병렬 진행하여 2주 내 완성

#### Track A: 포트폴리오 생존 분석

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S4-A-01 | Portfolio 모델 설계 | M | PortfolioCompany(investor, investee, exit_type, valuation_status) | `app/models/portfolio.py` |
| S4-A-02 | 생존 분석 서비스 | L | DART 감사보고서 확인, 폐업 공시 감지, 유니콘 트래킹 | `app/services/portfolio_service.py` |
| S4-A-03 | 포트폴리오 API | M | `/api/v1/portfolio/{corp_code}`, `/api/v1/portfolio/{corp_code}/survival` | `app/routers/portfolio.py` |
| S4-A-04 | 스키마 + 테스트 | M | 생존 판별 + 유니콘 감지 테스트 | `app/schemas/portfolio.py`, `tests/test_portfolio_service.py` |

#### Track B: Key Man (심사역) 추적

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S4-B-01 | KeyPerson 모델 설계 | M | KeyPerson + PersonMoveEvent | `app/models/key_person.py` |
| S4-B-02 | 심사역 이동 감지 서비스 | L | KOFIA 스크래핑 + 소속 변경 감지 + 프로파일링 | `app/services/key_person_service.py` |
| S4-B-03 | 심사역 API | M | `/api/v1/people`, `/api/v1/people/{id}`, `/api/v1/people/moves` | `app/routers/people.py` |
| S4-B-04 | 스키마 + 테스트 | M | 이동 감지 + 프로파일링 테스트 | `app/schemas/people.py`, `tests/test_key_person_service.py` |

#### Track C: 금융 제재 모니터링

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S4-C-01 | Sanction 분류 모델 | S | SanctionRecord + severity enum (Caution/Warning/Critical) | `app/models/sanction.py` |
| S4-C-02 | 제재 경중 분류 서비스 | M | 행정 착오 → Caution, 업무 정지 → Warning, 횡령/배임 → Critical | `app/services/sanction_service.py` |
| S4-C-03 | 제재 모니터링 API | S | `/api/v1/sanctions/{corp_code}`, `/api/v1/sanctions/recent` | `app/routers/sanctions.py` |
| S4-C-04 | 스키마 + 테스트 | S | 경중 분류 정확도 테스트 | `app/schemas/sanction.py`, `tests/test_sanction_service.py` |

#### Track D: 전자공시 Deep Linking

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S4-D-01 | Deep Link URL 생성 | S | DART rcept_no → PDF URL, KOFIA 원문 URL | `app/utils/deep_link.py` |
| S4-D-02 | Deep Link API | S | `/api/v1/links/dart/{rcept_no}`, `/api/v1/links/kofia/{fund_code}` | `app/routers/links.py` |
| S4-D-03 | 테스트 | XS | URL 생성 로직 단위 테스트 | `tests/test_deep_link.py` |

#### Sprint 4 완료 기준

- [ ] 피투자사 생존 분석 + 유니콘 감지 API 동작
- [ ] 심사역 이동 감지 + 전문분야 프로파일링 API 동작
- [ ] 금융 제재 Caution/Warning/Critical 자동 분류 동작
- [ ] DART/KOFIA 원문 Deep Link URL 생성 동작
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### 3.2 Sprint 5 — 시스템 통합 + 고도화 (Week 9-10)

> **목표:** 검색, 인증, 대시보드, 알림으로 제품 완성도 확보

#### Track A: ElasticSearch 통합 검색

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S5-A-01 | ES 인프라 설정 | M | docker-compose에 ES 8 추가, 인덱스 매핑 | `app/core/elasticsearch.py` |
| S5-A-02 | 데이터 인덱싱 서비스 | L | Company/News/Deal 인덱싱 (증분 + 벌크) | `app/services/search_service.py` |
| S5-A-03 | 통합 검색 API | M | `/api/v1/search?q=&type=&page=&size=` (하이라이팅, 자동완성) | `app/routers/search.py` |
| S5-A-04 | 검색 테스트 | M | 인덱싱 + 쿼리 + 필터링 테스트 | `tests/test_search_service.py` |

#### Track B: JWT 인증 시스템

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S5-B-01 | User 모델 + 인증 스키마 | M | User(email, hashed_password, role), TokenPair | `app/models/user.py`, `app/schemas/auth.py` |
| S5-B-02 | JWT 발급/검증 서비스 | M | access(30분), refresh(7일), RBAC 기본 구조 | `app/services/auth_service.py`, `app/core/security.py` |
| S5-B-03 | 인증 API | M | `/api/v1/auth/register`, `/login`, `/refresh`, `/me` | `app/routers/auth.py` |
| S5-B-04 | 인증 테스트 | M | 가입, 로그인, 토큰 갱신, 만료 처리 테스트 | `tests/test_auth.py` |

#### Track C: 대시보드 요약 API

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S5-C-01 | 대시보드 집계 서비스 | M | 기업 수, 뉴스 수, 평판 변동 TOP 5, 최근 딜 TOP 10 | `app/services/dashboard_service.py` |
| S5-C-02 | 대시보드 API | S | `/api/v1/dashboard/summary`, `/recent-changes` | `app/routers/dashboard.py` |
| S5-C-03 | 대시보드 테스트 | S | 집계 로직 정확도 테스트 | `tests/test_dashboard_service.py` |

#### Track D: 알림 시스템

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S5-D-01 | Watchlist 모델 + API | M | Watchlist(user_id, corp_code), CRUD API | `app/models/watchlist.py`, `app/routers/watchlist.py` |
| S5-D-02 | 알림 이벤트 서비스 | L | 신규 공시/뉴스/평판변동 감지, Redis pub/sub | `app/services/notification_service.py` |
| S5-D-03 | 배치 수집 스케줄러 | L | asyncio 배경 태스크 (DART 1h, 뉴스 30m, KOFIA 6h) | `app/services/scheduler_service.py` |
| S5-D-04 | 알림 API + 테스트 | M | `/api/v1/notifications`, 이벤트 감지 테스트 | `app/routers/notifications.py`, `tests/test_notification_service.py` |

#### Sprint 5 완료 기준

- [ ] ElasticSearch 통합 검색 동작
- [ ] JWT 인증 + 토큰 갱신 동작
- [ ] 대시보드 요약 API 동작
- [ ] Watchlist + 알림 이벤트 감지 동작
- [ ] 배치 스케줄러 주기적 수집 동작
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### 3.3 Sprint 6 — QA + 배포 (Week 11-12)

> **목표:** 시스템 안정화, 통합 테스트, 배포 준비

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 |
|---------|------|------|------|--------|
| S6-01 | 통합 테스트 시나리오 | L | E2E: DART → DB → 뉴스 → NLP → 평판 → API (3개 시나리오) | `tests/test_integration.py` |
| S6-02 | docker-compose 최종화 | M | FastAPI + PG + Redis + ES, health check, 볼륨 | `docker-compose.yml` |
| S6-03 | Alembic 마이그레이션 정리 | S | 전체 모델 반영, upgrade/downgrade 왕복 테스트 | `migrations/versions/` |
| S6-04 | 코드 품질 최종 검사 | M | ruff 0건, pytest --cov 리포트, 타입 힌트 점검 | 린트/커버리지 |
| S6-05 | API 문서 정리 | M | Swagger UI 설명, 예제 응답값 추가 | 라우터 docstring |
| S6-06 | 보안 점검 | S | .env, CORS, SQL Injection, Rate Limit, 의존성 취약점 | 보안 체크리스트 |
| S6-07 | 성능 기준선 측정 | M | p50/p95/p99 응답시간, 캐시 hit rate, 슬로우 쿼리 | 성능 리포트 |

#### Sprint 6 완료 기준

- [ ] 통합 테스트 전체 시나리오 통과
- [ ] `docker-compose up -d` 원클릭 전체 시스템 구동
- [ ] Alembic upgrade/downgrade 왕복 성공
- [ ] 린트 오류 0건, 테스트 전체 통과
- [ ] Swagger UI에서 전체 API 테스트 가능
- [ ] 보안 체크리스트 완료

---

## 4. 의존성 그래프 (잔여 작업)

```
현재 완료 (Sprint 1-3)
  ├── DART API ✅
  ├── KOFIA 크롤러 ✅
  ├── 리츠 파서 ✅
  ├── DB + Redis + 뉴스 수집 ✅
  ├── Entity Resolution + NLP ✅
  └── 평판 + 딜 소싱 ✅
        │
        ▼
┌─── Sprint 4 (Week 7-8) ──── 다음 단계 ────────────┐
│  Track A: 포트폴리오 생존 분석   ← (DART + DB)      │
│  Track B: Key Man 심사역 추적    ← (KOFIA + DB)     │
│  Track C: 금융 제재 모니터링     ← (DART + DB)      │
│  Track D: 전자공시 Deep Linking  ← (독립)           │
│  (4개 P2 기능 전부 병렬)                             │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌─── Sprint 5 (Week 9-10) ────────────────────────────┐
│  Track A: ElasticSearch 통합 검색  ← (전체 모델)     │
│  Track B: JWT 인증 시스템          ← (독립)          │
│  Track C: 대시보드 요약 API        ← (전체 서비스)   │
│  Track D: 알림 시스템 (Watchlist)  ← (DB + 뉴스)    │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌─── Sprint 6 (Week 11-12) ───────────────────────────┐
│  통합 테스트 / Docker 최종화 / QA / 문서화            │
└──────────────────────────────────────────────────────┘
```

---

## 5. 잔여 티켓 요약

### 5.1 스프린트별

| 스프린트 | 트랙 수 | 티켓 수 | 신규 파일 | 핵심 산출물 |
|----------|---------|---------|-----------|-------------|
| Sprint 4 | 4 (병렬) | 15 | ~12개 | P2 4개 기능 |
| Sprint 5 | 4 (병렬) | 15 | ~14개 | 검색, 인증, 대시보드, 알림 |
| Sprint 6 | 1 | 7 | ~2개 | 통합 테스트, QA |
| **합계** | | **37** | **~28개** | |

### 5.2 우선순위별

| 우선순위 | 티켓 | 스프린트 |
|----------|------|----------|
| **P2 (기반)** | S4-A~D 전체 (15) | Sprint 4 |
| **P3 (고도화)** | S5-A~D 전체 (15) | Sprint 5 |
| **P3 (마무리)** | S6-01~07 (7) | Sprint 6 |

### 5.3 크리티컬 패스

```
Sprint 4 → Sprint 5 → Sprint 6
(2주)       (2주)       (2주)
= 총 6주 잔여
```

Sprint 4의 4개 Track은 모두 독립적 → 병렬 실행 가능
Sprint 5의 Track B(JWT)와 Track D(알림)은 Sprint 4와 독립 → 일부 선행 가능

---

## 6. 기술적 참고 사항

### 6.1 현재 구현된 핵심 알고리즘

#### 평판 스코어링

```
KIIS 평판 = (트렌드 × 0.3) + (뉴스 감성 × 0.4) + (성과 지표 × 0.3)

상태 태그:
- Rising: total ≥ 0.7 AND trend ≥ 0.6
- Risk:   total < 0.4
- Stable: 기타
```

#### 섹터 분류 (11종)

| 코드 | 표시명 | 키워드 |
|------|--------|--------|
| `ai_deeptech` | AI/딥테크 | AI, 인공지능, 딥러닝, 머신러닝, 자율주행 |
| `bio_health` | 바이오/헬스케어 | 바이오, 헬스케어, 의료, 제약 |
| `saas` | SaaS | SaaS, 클라우드, B2B, 소프트웨어 |
| `consumer` | 컨슈머 | 소비재, 뷰티, 패션, F&B |
| `fintech` | 핀테크 | 핀테크, 금융, 페이, 결제 |
| `mobility` | 모빌리티 | 모빌리티, 전기차, 물류 |
| `ecommerce` | 이커머스 | 이커머스, 쇼핑, 유통 |
| `content` | 콘텐츠/미디어 | 콘텐츠, 미디어, 게임, OTT |
| `proptech` | 프롭테크 | 프롭테크, 부동산 |
| `edtech` | 에드테크 | 에드테크, 교육 |
| `other` | 기타 | (분류 불가) |

#### 투자 단계 추정

| 단계 | 금액 범위 (억원) |
|------|-----------------|
| Seed | 0 ~ 10 |
| Pre-A | 10 ~ 30 |
| Series A | 30 ~ 100 |
| Series B | 100 ~ 300 |
| Series C+ | 300 ~ 1,000 |
| Pre-IPO | 1,000+ |

### 6.2 추가 필요 의존성 (Sprint 4+)

| 패키지 | 용도 | 스프린트 |
|--------|------|----------|
| `elasticsearch[async]` | ES 비동기 클라이언트 | Sprint 5 |
| `python-jose[cryptography]` | JWT 토큰 | Sprint 5 |
| `passlib[bcrypt]` | 비밀번호 해싱 | Sprint 5 |

### 6.3 주의사항

1. `migrations/versions/` — 현재 비어 있음. Sprint 4 시작 전 초기 마이그레이션 생성 필요
2. 모든 코드 async/await 패턴 유지 (동기 함수 금지)
3. `expire_on_commit=False` 필수 (SQLAlchemy 세션)
4. httpx AsyncClient `aclose()` 사용 (`close()` 제거됨)
5. pytest-httpx 0.36+ `url=re.compile()` 패턴 매칭

---

## 7. 리스크 및 대응

| 리스크 | 영향 스프린트 | 영향도 | 대응 방안 |
|--------|-------------|--------|-----------|
| ElasticSearch 메모리 부족 | Sprint 5 | 중간 | `ES_JAVA_OPTS=-Xms512m -Xmx512m` 또는 PostgreSQL FTS 대체 |
| JWT 보안 취약점 | Sprint 5 | 높음 | python-jose + bcrypt 조합, 토큰 만료 관리 철저 |
| 통합 테스트 복잡도 | Sprint 6 | 중간 | 시나리오별 격리, 모킹 레이어 재활용 |
| Docker Desktop 리소스 | Sprint 5-6 | 중간 | ES 추가 시 메모리 4GB+ 필요, 리소스 제한 설정 |

---

## 부록: 원본 문서 참조

| 문서 | 경로 | 역할 | 비고 |
|------|------|------|------|
| 구현계획서 (마스터) | `docs/plans/KIIS_구현계획서.md` | 12주 전체 계획 | 아키텍처, 데이터소스, Week별 상세 |
| 실행계획 v2 | `docs/plans/KIIS_실행계획_v2.md` | 병렬화 스프린트 | 72개 티켓, 의존성 그래프 |
| Sprint 3 계획서 | `docs/plans/Sprint3_구현계획서.md` | 평판+딜 상세 | 모델/스키마/서비스 코드 설계 |
| VC 로드맵 원본 | `VC 정보 분석 시스템 개발 로드맵.md` | 기능 요구사항 원본 | P1/P2 상세 스펙 |
| **본 문서** | `docs/plans/KIIS_통합계획서.md` | **통합 현황 + 잔여 계획** | **최신 기준** |
