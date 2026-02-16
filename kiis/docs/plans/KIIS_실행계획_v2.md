# KIIS 실행 계획서 v2 — 병렬화 기반 스프린트 계획 (Week 4~12)

> **기준일:** 2026-02-08
> **전제 조건:** Week 1(DART API) ✅, Week 2(KOFIA 크롤러) ✅, Week 3(리츠 파서) 완료 가정
> **원본 계획:** [KIIS_구현계획서.md](KIIS_구현계획서.md)

---

## 1. 병렬화 전략 개요

### 1.1 기존 계획의 문제점

기존 계획은 **주 단위 순차 실행**(Week 4 → 5 → 6 → ... → 12)으로 설계되어 있으나,
실제로는 독립적인 작업 스트림이 다수 존재하여 **병렬 실행**이 가능하다.

| 기존 | 구조 | 비효율 |
|------|------|--------|
| Week 5 (뉴스 수집) | Week 4 완료 후 시작 | 뉴스 수집은 DB 스키마와 독립적으로 시작 가능 |
| Week 7 (평판) → Week 8 (딜) | 순차 | 평판과 딜 소싱은 서로 독립적 → 병렬 가능 |
| Week 9-10 (P2 기능 일괄) | 하나의 덩어리 | 4개 P2 기능은 각각 독립적 → 모두 병렬 가능 |

### 1.2 재구성 원칙

1. **의존성 기반 스케줄링:** 선행 작업이 완료되어야만 시작 가능한 작업만 순차 배치
2. **독립 작업 병렬화:** 선행 의존이 같거나 없는 작업은 같은 스프린트 내 병렬 트랙으로 배치
3. **티켓 단위 관리:** 모든 작업을 추적 가능한 세부 티켓(ID)으로 분해

---

## 2. 작업 의존성 그래프

```
Week 1-3 (완료)
  ├── DART API ✅
  ├── KOFIA 크롤러 ✅
  └── 리츠 파서 (✅ 가정)
        │
        ▼
┌─── Sprint 1 (Week 4) ───────────────────────────────────┐
│  Track A: 통합 DB 스키마 + Alembic                       │
│  Track B: Redis 캐싱 레이어                ← (A와 병렬)  │
│  Track C: 뉴스 수집 서비스 (모델+서비스+라우터) ← (독립)  │
└──────────────────────────────────────────────────────────┘
        │                          │
        ▼                          ▼
┌─── Sprint 2 (Week 5) ───────────────────────────────────┐
│  Track A: Entity Resolution      ← (DB 스키마 의존)      │
│  Track B: NLP 파이프라인          ← (뉴스 수집 의존)      │
│     (형태소 분석 + 감성 분석 + NER)                       │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌─── Sprint 3 (Week 6) ───────────────────────────────────┐
│  Track A: 평판 스코어링 엔진     ← (NLP + DB 의존)       │
│  Track B: 딜 소싱 시각화 API     ← (DB + NLP 의존, 병렬) │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌─── Sprint 4 (Week 7-8) ─────────────────────────────────┐
│  Track A: 포트폴리오 생존 분석   ← (DART + DB)           │
│  Track B: Key Man 심사역 추적    ← (KOFIA + DB)          │
│  Track C: 금융 제재 모니터링     ← (DART + DB)           │
│  Track D: 전자공시 Deep Linking  ← (독립)                │
│  (4개 P2 기능 전부 병렬)                                  │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌─── Sprint 5 (Week 9-10) ────────────────────────────────┐
│  Track A: ElasticSearch 통합 검색  ← (전체 모델 의존)     │
│  Track B: JWT 인증 시스템          ← (독립)               │
│  Track C: 대시보드 요약 API        ← (전체 서비스 의존)   │
│  Track D: 알림 시스템 (Watchlist)  ← (DB + 뉴스 의존)    │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌─── Sprint 6 (Week 11-12) ───────────────────────────────┐
│  통합 테스트 / Docker 최종화 / QA / 문서화                │
└──────────────────────────────────────────────────────────┘
```

### 기존 대비 단축 효과

| 구간 | 기존 (순차) | 신규 (병렬) | 단축 |
|------|-------------|-------------|------|
| DB + 뉴스 수집 | 2주 (W4 → W5) | 1주 (동시) | **1주** |
| 평판 + 딜 소싱 | 2주 (W7 → W8) | 1주 (동시) | **1주** |
| P2 기능 4개 | 2주 (W9-10 순차) | 2주 (전부 병렬) | 동일 but 밀도↑ |
| **총 예상** | **9주** (W4-12) | **~7-8주** | **1~2주** |

---

## 3. 스프린트별 상세 티켓

> **티켓 ID 규칙:** `S{스프린트}-T{트랙}-{번호}`
> **크기 기준:** XS(~1h) / S(~2-4h) / M(~4-8h) / L(~1-2일) / XL(2일+)

---

### Sprint 1 — 데이터 인프라 + 뉴스 수집 (Week 4)

> **목표:** 통합 DB 기반 확립, 캐싱 레이어 구축, 뉴스 데이터 소스 추가

#### Track A: 통합 DB 스키마 + Alembic

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S1-A-01 | 통합 Company 모델 설계 | M | 법인등록번호(PK) 기반 Company 모델. Fund/REITs FK 관계 정의. 기존 Fund 모델에 company FK 추가 | `app/models/company.py` 수정 | Week 1-3 |
| S1-A-02 | 기존 모델 관계 정리 | M | Fund ↔ Company, REITs ↔ Company 관계 설정. 기존 `fund.py`, `reits.py` 모델 수정 | `app/models/fund.py`, `reits.py` 수정 | S1-A-01 |
| S1-A-03 | Alembic 초기 마이그레이션 | S | `alembic revision --autogenerate -m "initial tables"` → `alembic upgrade head`. 전체 모델 반영 | `migrations/versions/` | S1-A-02 |
| S1-A-04 | Company 스키마 + 라우터 | M | Company CRUD 스키마, 통합 조회 API `GET /api/v1/companies`, `GET /api/v1/companies/{corp_code}` | `app/schemas/company.py`, `app/routers/company.py` | S1-A-01 |
| S1-A-05 | DB 통합 테스트 | M | SQLite async 기반 모델 CRUD 테스트. Company ↔ Fund ↔ REITs 관계 검증 | `tests/test_models.py` | S1-A-03 |

#### Track B: Redis 캐싱 레이어 (Track A와 병렬)

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S1-B-01 | Redis 연결 풀 구현 | S | `redis.asyncio` 기반 연결 풀. FastAPI lifespan에서 초기화/종료. `get_redis` 의존성 | `app/core/redis.py`, `app/core/dependencies.py` | - |
| S1-B-02 | 캐싱 데코레이터 구현 | M | `@cache(ttl=)` 데코레이터. JSON 직렬화/역직렬화. 키 생성 전략 (함수명+인자 해시) | `app/utils/cache.py` | S1-B-01 |
| S1-B-03 | 기존 서비스에 캐싱 적용 | S | DART 기업개황(24h), 재무제표(12h), 공시(1h), KOFIA 펀드(6h) TTL 설정 | `app/services/dart_service.py`, `kofia_service.py` 수정 | S1-B-02 |
| S1-B-04 | 캐싱 단위 테스트 | S | 캐시 hit/miss, TTL 만료, 키 생성 로직 테스트 | `tests/test_cache.py` | S1-B-02 |

#### Track C: 뉴스 수집 서비스 (Track A/B와 병렬)

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S1-C-01 | NewsArticle 모델 정의 | S | title, content, source, author, published_at, url, url_hash, sentiment_score, keywords(JSON), company_code(FK) | `app/models/news.py` | - |
| S1-C-02 | 뉴스 Pydantic 스키마 | S | NewsItem, NewsListResponse (페이지네이션), NewsCreateRequest | `app/schemas/news.py` | - |
| S1-C-03 | RSS 피드 수집기 구현 | L | feedparser 기반 RSS 수집. 플래텀, 딜사이트 등 소스별 파서. 중복 감지(URL 해시). 본문 전처리(HTML 제거) | `app/services/news_service.py` | S1-C-01 |
| S1-C-04 | 뉴스 API 라우터 | M | `GET /api/v1/news` (필터: source, date_from/to, company), `GET /api/v1/news/{id}` | `app/routers/news.py` | S1-C-02, S1-C-03 |
| S1-C-05 | 뉴스 수집 테스트 | M | RSS 파싱 모킹, 중복 감지, 본문 전처리 로직 테스트 | `tests/test_news_service.py` | S1-C-03 |

#### Sprint 1 완료 기준

- [ ] Company 통합 모델 + Fund/REITs 관계 설정 완료
- [ ] Alembic 초기 마이그레이션 생성 및 적용 성공
- [ ] Redis 캐싱 데코레이터 동작 확인
- [ ] 뉴스 RSS 수집 + 중복 감지 동작 확인
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### Sprint 2 — Entity Resolution + NLP 파이프라인 (Week 5)

> **목표:** 동일 법인 식별 체계 확립, 뉴스 텍스트에서 정보 추출

#### Track A: Entity Resolution (DB 스키마 의존)

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S2-A-01 | 별칭 사전 테이블 설계 | S | CompanyAlias 모델: (alias_name, canonical_corp_code). "한투파" → "한국투자파트너스" 매핑 | `app/models/company.py` 추가 | S1-A-01 |
| S2-A-02 | 유사도 매칭 알고리즘 | L | 한글 기업명 정규화(주식회사/㈜ 제거), 자모 분리 유사도, Levenshtein distance. threshold 기반 후보 추출 | `app/utils/entity_resolver.py` | S2-A-01 |
| S2-A-03 | Entity Resolution API | M | `POST /api/v1/entities/resolve` (name → corp_code), `POST /api/v1/entities/aliases` (수동 매핑 등록) | `app/routers/entity.py` | S2-A-02 |
| S2-A-04 | Entity Resolution 테스트 | M | 정규화, 유사도 계산, 별칭 매칭, 모호한 케이스 테스트 | `tests/test_entity_resolver.py` | S2-A-02 |

#### Track B: NLP 파이프라인 (뉴스 수집 의존)

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S2-B-01 | 한국어 불용어 사전 작성 | XS | 조사, 접속사, 일반동사 등 금융 도메인 불용어 목록 | `app/data/stopwords_ko.txt` | - |
| S2-B-02 | 금융 감성 사전 구축 | M | 긍정어(엑시트 성공, 펀드 결성, 흑자 전환 등), 부정어(투자 철회, 인력 이탈, 적자 전환 등). 가중치 포함 JSON | `app/data/finance_sentiment_dict.json` | - |
| S2-B-03 | 형태소 분석 + 키워드 추출 | L | konlpy Okt 기반 형태소 분석. 불용어 제거 → 명사/고유명사 추출 → TF-IDF 상위 N개 키워드. (konlpy 설치 실패 시 kiwi 대안) | `app/services/nlp_service.py` | S2-B-01 |
| S2-B-04 | 감성 분석 엔진 | M | 금융 감성 사전 기반 점수 산출 (-1.0 ~ +1.0). 문장 단위 분석 → 기사 전체 가중 평균 | `app/services/nlp_service.py` 추가 | S2-B-02, S2-B-03 |
| S2-B-05 | NER (투자 정보 추출) | L | 뉴스에서 `[투자사, 피투자사, 투자금액, 라운드, 날짜]` 추출. 정규식 + 패턴 매칭 규칙 기반 | `app/services/nlp_service.py` 추가 | S2-B-03 |
| S2-B-06 | NLP 서비스 테스트 | L | 형태소 분석, 키워드 추출, 감성 점수 계산, NER 추출 정확도 테스트. 샘플 뉴스 기사 3-5개 | `tests/test_nlp_service.py` | S2-B-03, S2-B-04, S2-B-05 |

#### Sprint 2 완료 기준

- [ ] "한투파" → "한국투자파트너스" 등 별칭 기반 Entity Resolution 동작
- [ ] 뉴스 기사에서 키워드 추출 및 감성 점수 산출 정상 동작
- [ ] NER로 투자사/피투자사/금액/라운드 추출 가능
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### Sprint 3 — 분석 엔진: 평판 + 딜 소싱 (Week 6)

> **목표:** P1 핵심 기능인 평판 지수와 딜 소싱 분석을 병렬 구현

#### Track A: 평판 스코어링 엔진 (NLP + DB 의존)

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S3-A-01 | Reputation 모델 설계 | M | ReputationScore(company_code, trend_score, news_score, performance_score, total_score, status_tag, scored_at). ReputationHistory(시계열) | `app/models/reputation.py` | S1-A-01 |
| S3-A-02 | 평판 지수 산출 알고리즘 | L | `KIIS 평판 = 트렌드(0.3) + 뉴스평판(0.4) + 성과지표(0.3)`. 뉴스 감성 6개월 집계, 엑시트 횟수 카운트. 상태 태그: Rising/Stable/Risk | `app/services/reputation_service.py` | S2-B-04, S3-A-01 |
| S3-A-03 | 평판 분석 API | M | `GET /api/v1/analysis/reputation/{corp_code}` (현재 평판), `GET /api/v1/analysis/reputation/{corp_code}/history` (시계열 추이) | `app/routers/analysis.py` | S3-A-02 |
| S3-A-04 | 평판 스키마 정의 | S | ReputationResponse, ReputationHistoryItem, StatusTag enum | `app/schemas/analysis.py` | S3-A-01 |
| S3-A-05 | 평판 스코어링 테스트 | M | 가중치 계산, 상태 태그 변환, 시계열 데이터 생성 테스트 | `tests/test_reputation_service.py` | S3-A-02 |

#### Track B: 딜 소싱 시각화 API (DB + NLP 의존, Track A와 병렬)

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S3-B-01 | Deal 모델 설계 | M | Deal(company_code, target_company, amount, round_stage, sector, deal_date, source_url). Sector enum, Stage enum | `app/models/deal.py` | S1-A-01 |
| S3-B-02 | 섹터 자동 분류 로직 | M | NLP 키워드 기반 섹터 분류: AI/딥테크, 바이오, SaaS, 컨슈머, 핀테크 등. 키워드 사전 + 규칙 기반 | `app/services/deal_service.py` | S2-B-03 |
| S3-B-03 | 투자 단계 추정 로직 | M | 투자금액 범위 + 지분율 역산 → Seed/Series A/B/Pre-IPO 추정. 금액 구간별 기본 규칙 | `app/services/deal_service.py` 추가 | S3-B-01 |
| S3-B-04 | 딜 소싱 집계 API | L | `GET /api/v1/deals/by-company/{corp_code}` (5년 딜), `GET /api/v1/deals/by-sector` (섹터별), `GET /api/v1/deals/by-stage` (단계별), `GET /api/v1/deals/trends` (연도별) | `app/routers/deals.py` | S3-B-02, S3-B-03 |
| S3-B-05 | 딜 소싱 스키마 정의 | S | DealItem, DealAggregation, SectorSummary, StageSummary, TrendData | `app/schemas/deal.py` | S3-B-01 |
| S3-B-06 | 딜 소싱 테스트 | M | 섹터 분류 정확도, 단계 추정, 집계 API 응답 형태 테스트 | `tests/test_deal_service.py` | S3-B-02, S3-B-03 |

#### Sprint 3 완료 기준

- [ ] KIIS 평판 지수 산출 및 API 조회 가능 (Rising/Stable/Risk 태그)
- [ ] 평판 시계열 추이 데이터 조회 가능
- [ ] 5년 딜 소싱 섹터별/단계별/연도별 API 조회 가능
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### Sprint 4 — P2 기능 일괄 병렬 구현 (Week 7-8)

> **목표:** 4개 P2 기능을 **모두 병렬** 진행하여 2주 내 완성

#### Track A: 포트폴리오 생존 분석

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S4-A-01 | Portfolio 모델 설계 | M | PortfolioCompany(investor_corp_code, investee_corp_code, invested_date, is_alive, exit_type, exit_date, valuation_status). exit_type: IPO/M&A/매각/폐업 | `app/models/portfolio.py` | S1-A-01 |
| S4-A-02 | 생존 분석 서비스 | L | DART 감사보고서 제출 여부로 생존 확인. 폐업 공시 감지. 유니콘 등극(기업가치 1조+) 트래킹 | `app/services/portfolio_service.py` | S4-A-01 |
| S4-A-03 | 포트폴리오 API | M | `GET /api/v1/portfolio/{corp_code}` (피투자사 목록), `GET /api/v1/portfolio/{corp_code}/survival` (생존율 통계) | `app/routers/portfolio.py` | S4-A-02 |
| S4-A-04 | 포트폴리오 스키마 + 테스트 | M | 스키마 정의 + 생존 판별 로직 테스트, 유니콘 감지 테스트 | `app/schemas/portfolio.py`, `tests/test_portfolio_service.py` | S4-A-02 |

#### Track B: Key Man (심사역) 추적

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S4-B-01 | KeyPerson 모델 설계 | M | KeyPerson(name, current_company, position, specialty, career_history(JSON)). PersonMoveEvent(person_id, from_company, to_company, detected_at) | `app/models/key_person.py` | S1-A-01 |
| S4-B-02 | 심사역 이동 감지 서비스 | L | KOFIA 운용인력 공시 주기적 스크래핑. 이전 스냅샷 대비 소속 변경 감지. 전문 분야 프로파일링(관여 딜 목록 연결) | `app/services/key_person_service.py` | S4-B-01 |
| S4-B-03 | 심사역 API | M | `GET /api/v1/people` (심사역 목록), `GET /api/v1/people/{id}` (상세 + 딜 이력), `GET /api/v1/people/moves` (이동 이벤트 목록) | `app/routers/people.py` | S4-B-02 |
| S4-B-04 | 심사역 스키마 + 테스트 | M | 스키마 정의 + 이동 감지 로직, 프로파일링 테스트 | `app/schemas/people.py`, `tests/test_key_person_service.py` | S4-B-02 |

#### Track C: 금융 제재 모니터링

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S4-C-01 | Sanction 분류 모델 설계 | S | SanctionRecord(corp_code, sanction_type, severity, description, sanction_date, source_url). severity enum: Caution/Warning/Critical | `app/models/sanction.py` | S1-A-01 |
| S4-C-02 | 제재 경중 분류 서비스 | M | DART 제재 API 데이터 기반 자동 분류. 행정 착오 과태료 → Caution, 업무 정지 → Warning, 횡령/배임 → Critical. 키워드 규칙 기반 | `app/services/sanction_service.py` | S4-C-01 |
| S4-C-03 | 제재 모니터링 API | S | `GET /api/v1/sanctions/{corp_code}` (분류된 제재 목록), `GET /api/v1/sanctions/recent` (최근 전체 제재) | `app/routers/sanctions.py` | S4-C-02 |
| S4-C-04 | 제재 스키마 + 테스트 | S | 스키마 정의 + 경중 분류 정확도 테스트 | `app/schemas/sanction.py`, `tests/test_sanction_service.py` | S4-C-02 |

#### Track D: 전자공시 Deep Linking

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S4-D-01 | Deep Link URL 생성 로직 | S | DART `rcept_no` → 원문 PDF URL 동적 생성. KOFIA 펀드 공시 원문 URL 매핑 | `app/utils/deep_link.py` | - |
| S4-D-02 | Deep Link API | S | `GET /api/v1/links/dart/{rcept_no}` (DART 원문), `GET /api/v1/links/kofia/{fund_code}` (KOFIA 원문) | `app/routers/links.py` | S4-D-01 |
| S4-D-03 | Deep Link 테스트 | XS | URL 생성 로직 단위 테스트 | `tests/test_deep_link.py` | S4-D-01 |

#### Sprint 4 완료 기준

- [ ] 피투자사 생존 분석 + 유니콘 감지 API 동작
- [ ] 심사역 이동 감지 + 전문분야 프로파일링 API 동작
- [ ] 금융 제재 Caution/Warning/Critical 자동 분류 동작
- [ ] DART/KOFIA 원문 Deep Link URL 생성 동작
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### Sprint 5 — 시스템 통합 + 고도화 (Week 9-10)

> **목표:** 검색, 인증, 대시보드, 알림으로 제품 완성도 확보

#### Track A: ElasticSearch 통합 검색

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S5-A-01 | ElasticSearch 인프라 설정 | M | docker-compose에 ES 8 추가. 인덱스 매핑 정의(company, news, deal). 연결 클라이언트 래퍼 | `docker-compose.yml` 수정, `app/core/elasticsearch.py` | Sprint 4 |
| S5-A-02 | 데이터 인덱싱 서비스 | L | Company/News/Deal 데이터 ES 인덱싱. 증분 인덱싱 + 벌크 초기 인덱싱 지원 | `app/services/search_service.py` | S5-A-01 |
| S5-A-03 | 통합 검색 API | M | `GET /api/v1/search?q=&type=&page=&size=` (기업/뉴스/딜 통합 검색). 하이라이팅, 자동완성 | `app/routers/search.py`, `app/schemas/search.py` | S5-A-02 |
| S5-A-04 | 검색 테스트 | M | 인덱싱 로직 + 검색 쿼리 + 필터링 테스트 | `tests/test_search_service.py` | S5-A-02 |

#### Track B: JWT 인증 시스템 (독립)

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S5-B-01 | User 모델 + 인증 스키마 | M | User(email, hashed_password, is_active, role). TokenPair(access_token, refresh_token). 비밀번호 해싱(bcrypt) | `app/models/user.py`, `app/schemas/auth.py` | - |
| S5-B-02 | JWT 발급/검증 서비스 | M | access_token(30분), refresh_token(7일) 발급. 토큰 검증 미들웨어. 역할 기반 접근 제어(RBAC) 기본 구조 | `app/services/auth_service.py`, `app/core/security.py` | S5-B-01 |
| S5-B-03 | 인증 API | M | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `GET /api/v1/auth/me` | `app/routers/auth.py` | S5-B-02 |
| S5-B-04 | 인증 테스트 | M | 회원가입, 로그인, 토큰 갱신, 만료 처리, 보호 엔드포인트 접근 테스트 | `tests/test_auth.py` | S5-B-02 |

#### Track C: 대시보드 요약 API

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S5-C-01 | 대시보드 집계 서비스 | M | 수집 기업 수, 뉴스 수, 최근 분석 결과, 평판 변동 TOP 5, 최근 딜 TOP 10 집계 | `app/services/dashboard_service.py` | Sprint 4 |
| S5-C-02 | 대시보드 API | S | `GET /api/v1/dashboard/summary`, `GET /api/v1/dashboard/recent-changes` | `app/routers/dashboard.py`, `app/schemas/dashboard.py` | S5-C-01 |
| S5-C-03 | 대시보드 테스트 | S | 집계 로직 정확도 테스트 | `tests/test_dashboard_service.py` | S5-C-01 |

#### Track D: 알림 시스템

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S5-D-01 | Watchlist 모델 + API | M | Watchlist(user_id, corp_code). `POST /api/v1/watchlist`, `GET /api/v1/watchlist`, `DELETE /api/v1/watchlist/{id}` | `app/models/watchlist.py`, `app/routers/watchlist.py` | S5-B-01 |
| S5-D-02 | 알림 이벤트 서비스 | L | 신규 공시/뉴스/평판변동 이벤트 감지. 알림 큐(Redis pub/sub). 이벤트 타입별 알림 템플릿 | `app/services/notification_service.py` | S5-D-01 |
| S5-D-03 | 배치 수집 스케줄러 | L | asyncio 백그라운드 태스크로 주기적 데이터 수집 (DART 1시간, 뉴스 30분, KOFIA 6시간). 스케줄러 상태 관리 | `app/services/scheduler_service.py` | Sprint 4 |
| S5-D-04 | 알림 API + 테스트 | M | `GET /api/v1/notifications` (내 알림), `PATCH /api/v1/notifications/{id}/read`. 이벤트 감지 + 알림 생성 테스트 | `app/routers/notifications.py`, `tests/test_notification_service.py` | S5-D-02 |

#### Sprint 5 완료 기준

- [ ] ElasticSearch 통합 검색 동작 (기업/뉴스/딜)
- [ ] JWT 인증 + 토큰 갱신 동작
- [ ] 대시보드 요약 API 동작
- [ ] Watchlist + 알림 이벤트 감지 동작
- [ ] 배치 스케줄러 주기적 수집 동작
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### Sprint 6 — QA + 배포 (Week 11-12)

> **목표:** 시스템 안정화, 통합 테스트, 배포 준비

| 티켓 ID | 제목 | 크기 | 설명 | 산출물 | 선행 |
|---------|------|------|------|--------|------|
| S6-01 | 통합 테스트 시나리오 작성 | L | E2E 흐름: DART 수집 → DB 저장 → 뉴스 수집 → NLP 분석 → 평판 산출 → API 조회. 최소 3개 시나리오 | `tests/test_integration.py` | Sprint 5 |
| S6-02 | docker-compose 최종화 | M | FastAPI + PostgreSQL + Redis + ElasticSearch 통합. health check, 볼륨, 네트워크 설정 완비 | `docker-compose.yml` 최종 | Sprint 5 |
| S6-03 | Alembic 마이그레이션 정리 | S | 전체 모델 반영 마이그레이션 확인. upgrade/downgrade 왕복 테스트 | `migrations/versions/` 검증 | Sprint 5 |
| S6-04 | 코드 품질 최종 검사 | M | `ruff check .` 린트 오류 0건. `pytest --cov` 커버리지 리포트. 타입 힌트 누락 점검 | 린트/커버리지 리포트 | Sprint 5 |
| S6-05 | API 문서 정리 | M | Swagger UI 전체 엔드포인트 설명, 예제 응답값 추가. FastAPI `description`, `response_model` 정리 | 각 라우터 docstring 보강 | Sprint 5 |
| S6-06 | 보안 점검 | S | .env 노출 방지, CORS 설정, SQL Injection 방어, Rate Limit 적정성, 의존성 취약점 스캔 | 보안 체크리스트 | Sprint 5 |
| S6-07 | 성능 기준선 측정 | M | 주요 API 응답 시간 측정 (p50/p95/p99). 캐시 hit rate 확인. 슬로우 쿼리 식별 | 성능 리포트 | Sprint 5 |

#### Sprint 6 완료 기준

- [ ] 통합 테스트 전체 시나리오 통과
- [ ] `docker-compose up -d` 원클릭 전체 시스템 구동
- [ ] Alembic upgrade/downgrade 왕복 성공
- [ ] 린트 오류 0건, 테스트 전체 통과
- [ ] Swagger UI에서 전체 API 테스트 가능
- [ ] 보안 체크리스트 완료

---

## 4. 전체 티켓 요약

### 스프린트별 티켓 수

| 스프린트 | 주차 | 트랙 수 | 티켓 수 | 핵심 산출물 |
|----------|------|---------|---------|-------------|
| Sprint 1 | W4 | 3 (병렬) | 14 | DB 스키마, Redis 캐싱, 뉴스 수집 |
| Sprint 2 | W5 | 2 (병렬) | 10 | Entity Resolution, NLP 파이프라인 |
| Sprint 3 | W6 | 2 (병렬) | 11 | 평판 지수, 딜 소싱 API |
| Sprint 4 | W7-8 | 4 (병렬) | 15 | P2 4개 기능 전부 |
| Sprint 5 | W9-10 | 4 (병렬) | 15 | 검색, 인증, 대시보드, 알림 |
| Sprint 6 | W11-12 | 1 | 7 | QA, 배포, 문서화 |
| **합계** | | | **72** | |

### 우선순위별 분류

| 우선순위 | 티켓 | 스프린트 |
|----------|------|----------|
| **P0 (인프라)** | S1-A-01~05, S1-B-01~04 | Sprint 1 |
| **P1 (핵심)** | S1-C-*, S2-B-*, S3-A-*, S3-B-* | Sprint 1-3 |
| **P1 (핵심)** | S2-A-* (Entity Resolution) | Sprint 2 |
| **P2 (기반)** | S4-A~D 전체 | Sprint 4 |
| **P3 (고도화)** | S5-A~D 전체 | Sprint 5 |
| **P3 (마무리)** | S6-01~07 | Sprint 6 |

### 크리티컬 패스 (최장 의존 경로)

```
S1-A-01 → S1-A-02 → S1-A-03 → S2-A-01 → S2-A-02
                                    ↕
S1-C-03 → S2-B-03 → S2-B-04 → S3-A-02 → S3-A-03
                        ↓
                    S2-B-05 → S3-B-02 → S3-B-04
```

**크리티컬 패스 소요:** Sprint 1 → 2 → 3 (3주)
이후 Sprint 4-6은 병렬화로 크리티컬 패스에서 분리됨.

---

## 5. 리스크 및 대응 (Week 4+ 관점)

| 리스크 | 영향 스프린트 | 영향도 | 대응 방안 |
|--------|-------------|--------|-----------|
| konlpy/JDK 설치 실패 (Windows) | Sprint 2 | 높음 | **대안:** `kiwipiepy` (순수 Python, JDK 불필요). S2-B-03에서 konlpy 실패 시 즉시 전환 |
| ElasticSearch 메모리 부족 | Sprint 5 | 중간 | ES 최소 메모리 설정 (`ES_JAVA_OPTS=-Xms512m -Xmx512m`). 또는 PostgreSQL FTS로 대체 |
| Entity Resolution 정확도 부족 | Sprint 2 | 중간 | 유사도 threshold 튜닝 + 수동 매핑 보완. 초기엔 수동 매핑 우선, 자동 매칭은 점진 개선 |
| 뉴스 소스 차단/구조 변경 | Sprint 1-2 | 중간 | RSS 피드 우선 사용(안정적). 크롤링 셀렉터 외부 설정화. 소스 3개 이상 확보 |
| NER 추출 정확도 부족 | Sprint 2 | 중간 | 규칙 기반으로 시작 → 패턴 DB 점진 확장. 정확도 메트릭 모니터링 추가 |
| Docker Desktop 미설치 | Sprint 1 | 높음 | Sprint 1 시작 전 Docker Desktop 설치 필수. 또는 SQLite + fakeredis로 로컬 개발 |

---

## 6. 부록: 신규 의존성 목록

Sprint 진행 시 추가 필요한 패키지:

| 패키지 | 용도 | 스프린트 |
|--------|------|----------|
| `feedparser` | RSS 피드 파싱 | Sprint 1 (뉴스) |
| `kiwipiepy` | 한국어 형태소 분석 (konlpy 대안) | Sprint 2 (NLP) |
| `python-Levenshtein` 또는 `rapidfuzz` | 문자열 유사도 | Sprint 2 (Entity Resolution) |
| `scikit-learn` | TF-IDF 키워드 추출 | Sprint 2 (NLP) |
| `elasticsearch[async]` | ES 비동기 클라이언트 | Sprint 5 |
| `python-jose[cryptography]` | JWT 토큰 발급/검증 | Sprint 5 |
| `passlib[bcrypt]` | 비밀번호 해싱 | Sprint 5 |
| `fakeredis[aioredis]` | Redis 테스트 모킹 | Sprint 1 (테스트) |
