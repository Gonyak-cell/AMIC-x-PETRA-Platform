# KIIS 구현 계획서
## 차세대 지능형 투자정보 통합 시스템 (Korea Investment Intelligence System)

---

## 1. 프로젝트 배경 및 목적

### 1.1 배경
대한민국 자본시장의 투자정보는 금융감독원(DART), 금융투자협회(KOFIA), 리츠정보시스템 등에 **파편화**되어 있다. 기관 투자자(LP)나 일반 투자자가 특정 운용사(GP)에 대한 심층 정보를 얻으려면 여러 시스템을 개별 탐색해야 하는 비효율이 존재한다.

### 1.2 목적
KIIS는 흩어진 **정형 데이터(공시)**와 **비정형 데이터(뉴스, 평판)**를 융합하여 '맥락(Context)'을 제공하는 투자정보 통합 플랫폼이다. 단순한 데이터 나열이 아닌, VC/PEF/REITs에 대한 **인텔리전스(Intelligence)**를 제공한다.

### 1.3 우선순위 체계

| 우선순위 | 기능 | 설명 |
|----------|------|------|
| **P1 (핵심)** | 업계 평판 | 뉴스 감성 + 생태계 리포트 + 성과 지표 기반 평판 지수 |
| **P1 (핵심)** | 최신 소식 | 금융 뉴스 수집 및 NLP 분석 |
| **P1 (핵심)** | 펀드 특징 | VC/PEF 펀드 구조, 블라인드/프로젝트 구분, 만기 관리 |
| **P1 (핵심)** | 5년 딜 소싱 | 투자 DNA 시각화, 섹터 분류, 투자 단계 추정 |
| **P2 (기반)** | 포트폴리오 | 피투자사 생존 분석, 유니콘 등극 알림 |
| **P2 (기반)** | 주요 구성원 | Key Man(심사역) 이동 추적, 휴먼 네트워크 |
| **P2 (기반)** | 금융 제재 | 제재 경중 분류 (주의/경고/위험) |
| **P2 (기반)** | 전자공시 링크 | DART/KOFIA 원문 PDF Deep Linking |

### 1.4 개발 범위 결정사항
- **Week 1부터 순서대로** 진행
- **백엔드 API + Swagger UI에 집중** (프론트엔드 React/Next.js는 추후 별도 진행)
- **Docker로 PostgreSQL + Redis 로컬 환경 구성** (로컬 미설치 상태)

---

## 2. 기술 아키텍처

### 2.1 기술 스택

| 영역 | 기술 |
|------|------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| **Database** | PostgreSQL 16, Redis 7 (캐싱), ElasticSearch (Phase 3 검색) |
| **데이터 처리** | pandas, numpy, konlpy (Okt), httpx (async HTTP), BeautifulSoup4, Playwright |
| **인프라** | Docker / docker-compose (PostgreSQL + Redis 로컬 환경) |
| **테스트** | pytest, pytest-asyncio, pytest-httpx |
| **패키지 관리** | uv (pip 대체) |
| **린트** | ruff |

### 2.2 데이터 소스

| 데이터 소스 | 유형 | 주요 정보 | 접근 방식 |
|-------------|------|-----------|-----------|
| **Open DART** (금융감독원) | API (JSON/XML) | 기업 개황, 재무제표, 공시, 제재 내역 | API 키 인증, Rate Limiting (분당 1000회) |
| **KOFIA** (금융투자협회) | API + 웹 크롤링 | 펀드 설정액, 운용 보수, 운용 전문인력 | OpenAPI + Playwright (동적 페이지) |
| **리츠정보시스템** (국토부) | 웹 크롤링 (HTML) | 리츠 인가 현황, 자산 구성, 주주 현황 | BeautifulSoup DOM 파싱 |
| **투자 미디어** (플래텀, 딜사이트) | RSS + 웹 크롤링 | 딜 소싱 뉴스, 심사역 평판, 엑시트 소식 | RSS 피드 + NLP 엔티티 추출 |
| **금융위원회** | 보도자료 | 금융 정책, 핀테크 규제 | 텍스트/HWP/PDF 파싱 |

### 2.3 시스템 아키텍처 (3계층)

```
┌─────────────────────────────────────────────────────┐
│                서비스 레이어 (Application)            │
│   FastAPI REST API  ←→  Swagger UI                  │
│   JWT 인증  /  ElasticSearch 검색                    │
├─────────────────────────────────────────────────────┤
│                처리 레이어 (Processing)               │
│   NLP 감성분석  /  평판 스코어링  /  Entity Resolution │
│   딜 소싱 DNA 분석  /  섹터 자동 분류                  │
├─────────────────────────────────────────────────────┤
│                수집 레이어 (Ingestion)                │
│   DART API  /  KOFIA 크롤러  /  리츠 파서            │
│   뉴스 크롤러  /  Rate Limiter  /  Redis 캐싱        │
└─────────────────────────────────────────────────────┘
         ↕                    ↕
    PostgreSQL 16          Redis 7
```

### 2.4 프로젝트 디렉토리 구조

```
kiis-project/
├── CLAUDE.md                    # 프로젝트 핵심 규칙 (150줄 이내)
├── .gitignore
├── .env.example                 # DART_API_KEY, DATABASE_URL 등
├── pyproject.toml               # uv 기반 의존성 관리
├── alembic.ini                  # DB 마이그레이션 설정
├── docker-compose.yml           # PostgreSQL + Redis 컨테이너
│
├── .claude/
│   ├── settings.json            # Claude Code 권한 설정
│   ├── rules/                   # 모듈형 규칙
│   │   ├── api-design.md
│   │   ├── database.md
│   │   ├── testing.md
│   │   └── security.md
│   ├── skills/                  # 자동 활성화 스킬
│   │   ├── dart-api/SKILL.md
│   │   ├── news-nlp/SKILL.md
│   │   ├── database-ops/SKILL.md
│   │   └── kofia-crawler/SKILL.md
│   └── agents/                  # 커스텀 에이전트
│       ├── data-collector.md
│       └── code-reviewer.md
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 앱 진입점
│   ├── core/
│   │   ├── config.py            # pydantic-settings 기반 설정
│   │   ├── database.py          # SQLAlchemy 2.0 async engine
│   │   ├── redis.py             # Redis 연결 풀
│   │   ├── dependencies.py      # FastAPI Depends() 의존성
│   │   └── exceptions.py        # 전역 예외 핸들러
│   ├── models/
│   │   ├── base.py              # TimestampMixin (created_at, updated_at)
│   │   ├── company.py           # 통합 Company (법인등록번호 PK)
│   │   ├── fund.py              # Fund, FundManager
│   │   ├── reits.py             # REITs, REITsAsset
│   │   ├── financial.py         # FinancialStatement, Disclosure
│   │   ├── news.py              # NewsArticle
│   │   └── reputation.py        # ReputationScore, ReputationHistory
│   ├── schemas/                 # Pydantic 요청/응답 스키마
│   │   ├── company.py
│   │   ├── fund.py
│   │   ├── reits.py
│   │   ├── news.py
│   │   └── analysis.py
│   ├── routers/                 # API 라우터 (기능별 분리)
│   │   ├── dart.py              # /api/v1/dart/*
│   │   ├── kofia.py             # /api/v1/kofia/*
│   │   ├── reits.py             # /api/v1/reits/*
│   │   ├── news.py              # /api/v1/news/*
│   │   ├── analysis.py          # /api/v1/analysis/*
│   │   └── deals.py             # /api/v1/deals/*
│   ├── services/                # 비즈니스 로직
│   │   ├── dart_service.py      # DART API 연동
│   │   ├── kofia_service.py     # KOFIA 크롤링
│   │   ├── reits_service.py     # 리츠 크롤링
│   │   ├── news_service.py      # 뉴스 수집
│   │   ├── nlp_service.py       # 형태소 분석, 감성 분석
│   │   ├── reputation_service.py # 평판 스코어링
│   │   └── deal_service.py      # 딜 소싱 분석
│   ├── utils/
│   │   ├── http_client.py       # httpx 비동기 클라이언트
│   │   ├── rate_limiter.py      # 토큰 버킷 Rate Limiter
│   │   ├── cache.py             # Redis 캐싱 데코레이터
│   │   └── entity_resolver.py   # Entity Resolution
│   └── data/
│       ├── stopwords_ko.txt     # 한국어 불용어 사전
│       └── finance_sentiment_dict.json  # 금융 감성 사전
│
├── migrations/
│   └── versions/                # Alembic 마이그레이션 파일
├── tests/
│   ├── conftest.py              # pytest fixtures
│   ├── test_dart_service.py
│   ├── test_kofia_service.py
│   ├── test_reits_service.py
│   ├── test_news_service.py
│   └── test_nlp_service.py
└── docs/
    ├── api-design.md
    ├── data-pipeline.md
    └── erd.md                   # Mermaid ERD 다이어그램
```

---

## 3. 구현 로드맵

### 3.0 단계 간 의존성

```
Phase 1 (Weeks 1-4): 데이터 수집기
  Week 1: 프로젝트 초기화 + DART API
  Week 2: KOFIA 펀드 크롤러
  Week 3: 리츠 데이터 파서
  Week 4: 통합 DB 스키마 + Entity Resolution
       │
       ▼
Phase 2 (Weeks 5-8): 분석 엔진 (P1 핵심)
  Week 5: 미디어 수집 + 전처리
  Week 6: NLP 엔티티 추출 + 감성 분석
  Week 7: 평판 스코어링 엔진
  Week 8: 딜 소싱 시각화 API
       │
       ▼
Phase 3 (Weeks 9-12): 통합 + P2 기능
  Week 9-10: 백엔드 고도화 + P2 구현
  Week 11: 알림 시스템 + 자동화
  Week 12: QA + 배포
```

---

### 3.1 Phase 1: 데이터 인프라 및 수집기 구축 (Weeks 1-4)

> **목표:** DART, KOFIA, 리츠정보시스템의 정형 데이터를 100% 자동 수집하는 파이프라인 완성

#### Week 1: 프로젝트 초기화 + Open DART API 연동

**생성할 파일:**

| 파일 | 설명 |
|------|------|
| `pyproject.toml` | uv 기반 의존성 정의 (FastAPI, SQLAlchemy, httpx, pydantic-settings, alembic, pytest, ruff, redis) |
| `docker-compose.yml` | PostgreSQL 16 + Redis 7 컨테이너 |
| `CLAUDE.md` | 프로젝트 핵심 규칙 (가이드 문서 참조, 150줄 이내) |
| `.claude/settings.json` | Claude Code 권한 설정 (allow/ask/deny) |
| `.claude/rules/*.md` | api-design, database, testing, security 규칙 |
| `.claude/skills/*/SKILL.md` | dart-api, news-nlp, database-ops, kofia-crawler 스킬 |
| `.claude/agents/*.md` | data-collector, code-reviewer 에이전트 |
| `.env.example` | DART_API_KEY, DATABASE_URL, REDIS_URL, SECRET_KEY |
| `.gitignore` | .env, __pycache__, .venv, CLAUDE.local.md 등 |
| `app/main.py` | FastAPI 진입점, lifespan, CORS, GET /health |
| `app/core/config.py` | pydantic-settings BaseSettings (.env 자동 로드) |
| `app/core/database.py` | SQLAlchemy 2.0 async engine + AsyncSession |
| `app/utils/http_client.py` | httpx 비동기 클라이언트 (재시도 exponential backoff, 타임아웃) |
| `app/utils/rate_limiter.py` | asyncio 토큰 버킷 Rate Limiter |
| `app/services/dart_service.py` | DART API 클래스 |
| `app/routers/dart.py` | DART REST API 엔드포인트 |
| `tests/conftest.py` | pytest fixtures, AsyncClient |
| `tests/test_dart_service.py` | DART 서비스 단위 테스트 |

**핵심 작업:**

1. `git init` → `uv init` → `uv sync` → 전체 디렉토리 구조 생성
2. `docker-compose.yml` 작성 및 `docker-compose up -d` (PostgreSQL 16 + Redis 7)
3. FastAPI 서버 구동 확인: `uv run uvicorn app.main:app --reload --port 8000` → `GET /health → {"status": "ok"}`
4. DART API 연동:
   - 기업 고유번호 목록: `/corpCode.xml` (ZIP → XML 파싱)
   - 기업 개황: `/company.json`
   - 공시 검색: `/list.json` (날짜 범위, 기업코드, 페이지네이션)
   - 재무제표: `/fnlttSinglAcntAll.json` (연결/별도 구분)
   - 제재 내역 API
5. Rate Limiter: 분당 900회, 일 9000회 (공식 한도의 90%로 여유 확보)
6. DART 상태 코드별 에러 처리: "000"(정상), "010"(미등록 키), "011"(사용 제한), "013"(결과 없음)

**DART API 엔드포인트 설계:**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/dart/companies` | 기업 목록 조회 |
| GET | `/api/v1/dart/companies/{corp_code}` | 기업 개황 상세 |
| GET | `/api/v1/dart/companies/{corp_code}/financials` | 재무제표 조회 |
| GET | `/api/v1/dart/disclosures` | 공시 검색 (날짜/기업 필터) |
| GET | `/api/v1/dart/sanctions` | 제재 내역 조회 |

#### Week 2: KOFIA 펀드 데이터 크롤러

**생성할 파일:**

| 파일 | 설명 |
|------|------|
| `app/models/fund.py` | Fund, FundManager SQLAlchemy 모델 |
| `app/schemas/fund.py` | 펀드 요청/응답 Pydantic 스키마 |
| `app/services/kofia_service.py` | KOFIA 크롤링 서비스 (Playwright 헤드리스) |
| `app/routers/kofia.py` | 펀드 API 엔드포인트 |
| `tests/test_kofia_service.py` | KOFIA 서비스 테스트 |

**핵심 작업:**

1. KOFIA OpenAPI 연동: 펀드 설정액, 운용 보수, 운용 전문인력 현황
2. 동적 로딩 페이지 대응: Playwright 헤드리스 브라우저로 JavaScript 렌더링 후 데이터 추출
3. 펀드 유형 자동 구분: **블라인드 펀드** vs **프로젝트 펀드**
4. 펀드 빈티지(Vintage Year) 관리 및 만기 임박 시 **"회수 집중 구간"** 알림 로직
5. 요청 간격 3초 이상 유지, robots.txt 준수

**KOFIA API 엔드포인트:**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/kofia/funds` | 펀드 목록 (필터: 운용사, 유형) |
| GET | `/api/v1/kofia/funds/{fund_code}` | 펀드 상세 정보 |
| GET | `/api/v1/kofia/managers` | 운용 전문인력 목록 |

#### Week 3: 리츠 데이터 파서

**생성할 파일:**

| 파일 | 설명 |
|------|------|
| `app/models/reits.py` | REITs, REITsAsset SQLAlchemy 모델 |
| `app/schemas/reits.py` | 리츠 Pydantic 스키마 |
| `app/services/reits_service.py` | 리츠정보시스템 크롤러 |
| `app/routers/reits.py` | 리츠 API 엔드포인트 |
| `tests/test_reits_service.py` | 리츠 서비스 테스트 |

**핵심 작업:**

1. 리츠정보시스템(reits.molit.go.kr) HTML 파싱 (BeautifulSoup4)
2. 리츠 형태 자동 분류:

| 분류 | 자기관리 리츠 | 위탁관리 리츠 | 검증 로직 |
|------|--------------|--------------|-----------|
| 실체 | 실체 회사 (임직원 상근) | 명목 회사 | 임직원 현황 조회 |
| 자산 요건 | 부동산 70% 이상 | 부동산 70% 이상 | 자산 비율 계산 검증 |
| 법인세 | 과세 대상 | 90% 이상 배당 시 공제 | 배당 성향 데이터 확인 |

3. **경고(Flagging)** 기능: 부동산 자산 70% 미달 리츠 자동 감지
4. 배당 성향 데이터 (배당금/당기순이익) 확인

**리츠 API 엔드포인트:**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/reits/` | 리츠 목록 (필터: 유형, 상태) |
| GET | `/api/v1/reits/{reits_code}` | 리츠 상세 (자산 구성 포함) |
| GET | `/api/v1/reits/{reits_code}/assets` | 자산 내역 |

#### Week 4: 통합 DB 스키마 설계 + Entity Resolution

**생성할 파일:**

| 파일 | 설명 |
|------|------|
| `app/models/base.py` | TimestampMixin (created_at, updated_at) |
| `app/models/company.py` | 통합 Company 모델 (법인등록번호 PK) |
| `app/utils/entity_resolver.py` | Entity Resolution 로직 |
| `app/core/redis.py` | Redis 연결 풀 (redis.asyncio) |
| `app/utils/cache.py` | Redis 캐싱 데코레이터 (TTL 설정) |
| `app/core/dependencies.py` | FastAPI Depends() (get_db, get_redis) |
| `migrations/versions/` | 초기 Alembic 마이그레이션 |
| `docs/erd.md` | Mermaid ERD 다이어그램 |

**핵심 작업:**

1. 통합 DB 스키마 설계: `Company(법인등록번호 PK)` ↔ `Fund` ↔ `REITs` ↔ `News` 관계형 구조
2. **Entity Resolution** 구현: "한투파" = "한국투자파트너스 주식회사" 동일 개체 식별
   - 유사도 매칭 알고리즘 + 수동 매핑 테이블 병행
3. Alembic 초기 마이그레이션: `alembic revision --autogenerate -m "initial tables"` → `alembic upgrade head`
4. Redis 캐싱 레이어: 기업 개황 24h TTL, 재무제표 12h, 공시 1h

**Phase 1 완료 기준:**
- [ ] DART API로 기업 개황, 재무제표, 공시 목록 수집 가능
- [ ] KOFIA에서 펀드 정보 크롤링 및 DB 저장 가능
- [ ] 리츠정보시스템에서 리츠 데이터 파싱 및 DB 저장 가능
- [ ] Entity Resolution으로 동일 법인 식별 가능
- [ ] `http://localhost:8000/docs` Swagger UI에서 모든 API 테스트 가능
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### 3.2 Phase 2: 지능형 분석 엔진 (Weeks 5-8) — P1 핵심 기능

> **목표:** 비정형 텍스트(뉴스, 리포트)에서 평판과 딜 정보를 추출하여 P1 기능 완성

#### Week 5: 미디어 수집 및 전처리

**생성할 파일:**

| 파일 | 설명 |
|------|------|
| `app/models/news.py` | NewsArticle 모델 (title, content, source, published_at, sentiment_score, keywords) |
| `app/schemas/news.py` | 뉴스 Pydantic 스키마 |
| `app/services/news_service.py` | 뉴스 크롤러 (RSS + 웹) |
| `app/routers/news.py` | 뉴스 API 엔드포인트 |
| `tests/test_news_service.py` | 뉴스 서비스 테스트 |

**핵심 작업:**

1. RSS 피드 수집: 플래텀(`platum.kr`), 딜사이트(`dealsite.co.kr`) 등
2. 기사 본문 전처리 파이프라인: 광고/HTML 태그 제거, 텍스트 정규화
3. 크롤링 윤리: robots.txt 준수, 요청 간격 2-3초, User-Agent 헤더 설정
4. 중복 기사 감지: URL 해시 또는 제목 유사도 기반

#### Week 6: NLP 엔티티 추출 (NER) + 감성 분석

**생성할 파일:**

| 파일 | 설명 |
|------|------|
| `app/services/nlp_service.py` | NLP 파이프라인 (konlpy Okt 형태소 분석기) |
| `app/data/stopwords_ko.txt` | 한국어 불용어 사전 (조사, 접속사, 일반 동사) |
| `app/data/finance_sentiment_dict.json` | 금융 도메인 감성 사전 |
| `tests/test_nlp_service.py` | NLP 서비스 테스트 |

**핵심 작업:**

1. **NER (Named Entity Recognition):** 투자 뉴스에서 `[투자사, 피투자사, 투자금액, 라운드, 날짜]` JSON 추출
2. **금융 감성 사전 구축:**
   - 긍정어: 성공적 엑시트, 대규모 펀드 결성, 매출 증가, 흑자 전환, 상향 조정
   - 부정어: 투자 철회, 경영권 분쟁, 운용 인력 이탈, 적자 전환, 하향 조정
3. **감성 점수 산출** (-1.0 ~ +1.0): 키워드 매칭 + 문맥 분석
4. **키워드 추출:** konlpy Okt 형태소 분석 → 불용어 제거 → TF-IDF 상위 N개

#### Week 7: 평판 스코어링 엔진 (P1 핵심)

**생성할 파일:**

| 파일 | 설명 |
|------|------|
| `app/services/reputation_service.py` | KIIS 평판 지수 알고리즘 |
| `app/models/reputation.py` | ReputationScore, ReputationHistory 모델 |
| `app/routers/analysis.py` | 분석 API 엔드포인트 |

**핵심 작업: KIIS 평판 지수(Reputation Index) 산출**

```
KIIS 평판 지수 = (트렌드 점수 × 0.3) + (뉴스 평판 × 0.4) + (성과 지표 × 0.3)
```

| 구성 요소 | 가중치 | 데이터 소스 | 설명 |
|-----------|--------|-------------|------|
| 트렌드 점수 | 30% | 스타트업얼라이언스, 플래텀 리포트 | 생태계 리포트 내 순위 |
| 뉴스 평판 | 40% | 최근 6개월 뉴스 기사 | 뉴스 감성 지수 집계 |
| 성과 지표 | 30% | DART 공시 + 뉴스 | 1년 내 엑시트 성공 횟수 |

- 상태 태그 변환: **"상승세(Rising)"** / **"안정적(Stable)"** / **"리스크(Risk)"**
- 시계열 평판 추이 분석 API 제공

#### Week 8: 딜 소싱 시각화 API (P1 핵심)

**생성할 파일:**

| 파일 | 설명 |
|------|------|
| `app/services/deal_service.py` | 딜 소싱 분석 서비스 |
| `app/routers/deals.py` | 딜 데이터 API 엔드포인트 |

**핵심 작업:**

1. **5년치 투자 데이터** 연도별/산업별 집계 SQL 최적화
2. **섹터 자동 분류** (NLP 기반): AI/딥테크, 바이오/헬스케어, SaaS, 컨슈머, 핀테크 등
3. **투자 단계(Stage) 추정:** 투자 금액 + 지분율 역산 → Seed / Series A / Series B / Pre-IPO
4. FastAPI 엔드포인트: 차트 데이터 형태로 JSON 반환

**딜 소싱 API 엔드포인트:**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/deals/by-company/{corp_code}` | 특정 운용사 5년 딜 목록 |
| GET | `/api/v1/deals/by-sector` | 섹터별 투자 집계 |
| GET | `/api/v1/deals/by-stage` | 투자 단계별 집계 |
| GET | `/api/v1/deals/trends` | 연도별 투자 트렌드 |

**Phase 2 완료 기준:**
- [ ] 뉴스 기사에서 NER 추출 및 감성 분석 정상 동작
- [ ] 운용사별 KIIS 평판 지수 산출 및 API 조회 가능
- [ ] 평판 상태 태그(Rising/Stable/Risk) 정상 변환
- [ ] 5년 딜 소싱 데이터 섹터별/단계별 API 조회 가능
- [ ] `uv run pytest tests/ -v` 전체 통과

---

### 3.3 Phase 3: 시스템 통합 + P2 기능 (Weeks 9-12)

> **목표:** P2 기능 구현, 시스템 고도화, 알림 자동화, QA 및 배포

#### Week 9-10: 백엔드 고도화 + P2 기능 구현

**핵심 작업:**

1. **ElasticSearch 도입** → docker-compose에 추가, 통합 검색 API 구현
2. **JWT 기반 인증** → 사용자 등록/로그인/토큰 발급
3. **P2 - 포트폴리오 생존 분석:**
   - DART 감사보고서 제출 여부로 피투자사 생존 확인
   - 폐업 공시 감지
   - 유니콘 등극(기업가치 1조원 이상) 시 트랙레코드 강조
4. **P2 - Key Man(심사역) 추적:**
   - KOFIA 운용 전문인력 공시를 주기적 스크래핑
   - 소속 변경 이벤트 감지: "김철수 심사역: A투자 → B벤처 이직"
   - 심사역별 관여 딜 목록 연결 → 전문 분야 프로파일링
5. **P2 - 금융 제재 모니터링:**
   - DART 제재 내역 API 연동
   - 제재 경중 분류: **주의(Caution)** / **경고(Warning)** / **위험(Critical)**
   - 행정 착오 과태료 vs 횡령/배임 중징계 구분
6. **P2 - 전자공시 Deep Linking:**
   - DART `rcept_no`(접수번호)로 원문 PDF 직링크 URL 동적 생성
   - KOFIA 펀드 공시 원문 연결
7. **대시보드 요약 API:** `GET /api/v1/dashboard/summary` (수집 기업 수, 뉴스 수, 최근 분석 결과)

#### Week 11: 알림 시스템 및 자동화

**핵심 작업:**

1. **관심 운용사 Watchlist** 설정 기능
2. **신규 공시/뉴스 알림:** 관심 운용사의 새 공시 또는 뉴스 발생 시 Slack/이메일 알림
3. **데이터 수집 스케줄러:** asyncio 기반 백그라운드 태스크로 주기적 배치 수집
4. **평판 지수 변동 알림:** 평판 등급 변경(예: Stable → Risk) 시 알림

#### Week 12: QA + 배포

**핵심 작업:**

1. **전체 시스템 통합 테스트:** DART 수집 → DB 저장 → 뉴스 수집 → NLP 분석 → API 조회 전체 흐름
2. **docker-compose 최종화:** FastAPI + PostgreSQL + Redis + ElasticSearch 통합 환경
3. **코드 품질 검사:** `uv run ruff check .` / `uv run pytest tests/ -v --cov`
4. **API 문서 정리:** Swagger UI 기반 전체 엔드포인트 문서화

**Phase 3 완료 기준:**
- [ ] P2 기능 (포트폴리오, Key Man, 제재, Deep Link) 모두 API 동작
- [ ] ElasticSearch 기반 통합 검색 동작
- [ ] Watchlist 알림 시스템 동작
- [ ] docker-compose로 전체 시스템 원클릭 구동 가능
- [ ] 전체 테스트 통과, 린트 오류 없음

---

## 4. 검증 방법

| 검증 항목 | 명령어 / 방법 |
|-----------|--------------|
| 단위 테스트 | `uv run pytest tests/ -v` (외부 API 모킹) |
| 통합 테스트 | `uv run pytest tests/ -v -m integration` (실제 API 키 사용) |
| 린트 검사 | `uv run ruff check .` |
| 서버 구동 | `uv run uvicorn app.main:app --reload --port 8000` |
| API 문서 | `http://localhost:8000/docs` (Swagger UI) |
| DB 마이그레이션 | `uv run alembic upgrade head` |
| Docker 환경 | `docker-compose up -d` (PostgreSQL + Redis) |

---

## 5. 위험 요소 및 대응 방안

| 위험 요소 | 영향도 | 대응 방안 |
|-----------|--------|-----------|
| **konlpy/JDK 설치** (Windows) | 높음 | Phase 1에서 konlpy 설치 환경을 미리 검증. Windows JDK 경로 설정 가이드 준비 |
| **KOFIA 동적 페이지** | 중간 | httpx+BS4 우선 시도 → 실패 시 Playwright 헤드리스 브라우저 도입 |
| **DART 일일 호출 제한** (10,000회) | 중간 | Redis 캐싱 적극 활용 + 토큰 버킷 Rate Limiter + 개발 시 모킹 |
| **Entity Resolution 정확도** | 중간 | 유사도 매칭 알고리즘 + 수동 매핑 테이블(별칭 사전) 병행 |
| **리츠정보시스템 구조 변경** | 중간 | 크롤링 셀렉터를 설정 파일(JSON)로 외부화하여 코드 수정 없이 대응 |
| **async SQLAlchemy 복잡성** | 중간 | SQLAlchemy 2.0 async 패턴을 Phase 1에서 확실히 검증. `expire_on_commit=False` 등 문서화 |

---

## 6. 참고 자료

- [Open DART API](https://opendart.fss.or.kr/intro/main.do) - 금융감독원 전자공시
- [KOFIA OpenAPI](http://openapi.kofia.or.kr/) - 금융투자협회 오픈 API
- [리츠정보시스템](https://reits.molit.go.kr/) - 국토교통부
- 프로젝트 가이드 문서: `compass_artifact_wf-78b20a18-20a0-4785-b2d8-da82bf276efc_text_markdown.md`
- 로드맵 원본: `VC 정보 분석 시스템 개발 로드맵.md`
