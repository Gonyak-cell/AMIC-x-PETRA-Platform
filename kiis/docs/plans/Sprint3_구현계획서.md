# Sprint 3 구현 계획서: 평판 스코어링 + 딜 소싱

> **작성일**: 2026-02-08
> **Sprint**: 3 (Week 6)
> **목표**: P1 핵심 기능인 평판 지수와 딜 소싱 분석을 병렬 구현
> **선행 완료**: Sprint 1-2 (DB, 캐싱, 뉴스 수집, Entity Resolution, NLP)

---

## 1. 개요

### 1.1 Sprint 3 범위

| Track | 기능 | 티켓 |
|-------|------|------|
| **A** | 평판 스코어링 엔진 | S3-A-01 ~ S3-A-05 |
| **B** | 딜 소싱 시각화 API | S3-B-01 ~ S3-B-06 |

### 1.2 예상 산출물

- 신규 파일: 8개 (모델 2, 스키마 2, 서비스 2, 라우터 2)
- 수정 파일: 3개 (company.py, __init__.py, main.py)
- 테스트 파일: 2개 (~35개 테스트 케이스)
- 총 테스트: 165 + 35 = ~200개

---

## 2. Track A: 평판 스코어링 엔진

### 2.1 핵심 알고리즘

```
KIIS 평판 지수 = (트렌드 점수 × 0.3) + (뉴스 평판 × 0.4) + (성과 지표 × 0.3)
```

| 구성 요소 | 가중치 | 데이터 소스 | 설명 |
|-----------|--------|-------------|------|
| 트렌드 점수 | 30% | 뉴스 추세 | 이전 기간 대비 감성 변화 |
| 뉴스 평판 | 40% | 최근 6개월 뉴스 | NLP 감성 분석 평균 |
| 성과 지표 | 30% | 뉴스/공시 | 1년 내 엑시트 성공 횟수 |

### 2.2 상태 태그 분류

| 태그 | 조건 | 의미 |
|------|------|------|
| **Rising** | total ≥ 0.7 AND trend ≥ 0.6 | 상승세 |
| **Risk** | total < 0.4 | 리스크 |
| **Stable** | 기타 | 안정적 |

### 2.3 모델 설계: `app/models/reputation.py`

#### ReputationScore (현재 평판 스냅샷)

```python
class ReputationScore(TimestampMixin, Base):
    """기업 평판 점수 (company당 1개)"""

    __tablename__ = "reputation_scores"

    id: Mapped[int]
    company_id: Mapped[int]  # FK → companies.id, CASCADE, unique

    # 점수 (0.0 ~ 1.0)
    trend_score: Mapped[Decimal]      # 트렌드 점수
    news_score: Mapped[Decimal]       # 뉴스 감성 점수 (-1.0 ~ 1.0)
    performance_score: Mapped[Decimal] # 성과 지표 점수
    total_score: Mapped[Decimal]      # 총합 평판 지수

    # 상태
    status_tag: Mapped[str]           # rising/stable/risk
    scored_at: Mapped[datetime]       # 산출 시각

    # 메타 정보
    news_count: Mapped[int]           # 분석 뉴스 수
    exit_count: Mapped[int]           # 1년 내 엑시트 횟수

    # 관계
    company: Mapped["Company"] = relationship(back_populates="reputation_score")
```

#### ReputationHistory (시계열 이력)

```python
class ReputationHistory(TimestampMixin, Base):
    """평판 점수 변동 이력"""

    __tablename__ = "reputation_history"

    id: Mapped[int]
    company_id: Mapped[int]  # FK → companies.id, CASCADE

    total_score: Mapped[Decimal]
    status_tag: Mapped[str]
    trend_score: Mapped[Decimal]
    news_score: Mapped[Decimal]
    performance_score: Mapped[Decimal]
    recorded_at: Mapped[datetime]  # 기록 시각
```

### 2.4 스키마 설계: `app/schemas/analysis.py`

```python
# 평판 조회 응답
class ReputationScoreResponse(BaseModel):
    company_id: int
    corp_code: str
    corp_name: str
    trend_score: Decimal
    news_score: Decimal
    performance_score: Decimal
    total_score: Decimal
    status_tag: str  # rising/stable/risk
    scored_at: datetime
    news_count: int
    exit_count: int

# 이력 아이템
class ReputationHistoryItem(BaseModel):
    total_score: Decimal
    status_tag: str
    trend_score: Decimal
    news_score: Decimal
    performance_score: Decimal
    recorded_at: datetime

# 이력 응답
class ReputationHistoryResponse(BaseModel):
    corp_code: str
    corp_name: str
    total: int
    items: list[ReputationHistoryItem]

# 계산 요청
class ReputationCalculateRequest(BaseModel):
    months: int = Field(6, ge=1, le=24, description="뉴스 분석 기간 (개월)")
    save_history: bool = Field(True, description="이력 저장 여부")
```

### 2.5 서비스 설계: `app/services/reputation_service.py`

```python
class ReputationService:
    """평판 스코어링 서비스"""

    WEIGHT_TREND = 0.3
    WEIGHT_NEWS = 0.4
    WEIGHT_PERFORMANCE = 0.3

    def __init__(self):
        self.nlp_service = NLPService()  # 감성 분석 활용

    async def calculate_reputation(
        self, db: AsyncSession, company_id: int, months: int = 6
    ) -> ReputationScore:
        """평판 지수 계산"""
        # 1. 뉴스 점수: 최근 N개월 NewsArticle.sentiment_score 평균
        news_score = await self._calculate_news_score(db, company_id, months)

        # 2. 성과 점수: 뉴스에서 "엑시트", "IPO" 키워드 카운트
        performance_score, exit_count = await self._calculate_performance_score(db, company_id)

        # 3. 트렌드 점수: 이전 기간 대비 감성 변화
        trend_score = await self._calculate_trend_score(db, company_id, months)

        # 4. 총합 계산
        normalized_news = (news_score + 1.0) / 2.0  # -1~1 → 0~1
        total_score = (
            trend_score * self.WEIGHT_TREND +
            normalized_news * self.WEIGHT_NEWS +
            performance_score * self.WEIGHT_PERFORMANCE
        )

        # 5. 상태 태그 결정
        status_tag = self._determine_status_tag(total_score, trend_score)

        return ReputationScore(...)

    async def get_reputation(self, db: AsyncSession, corp_code: str) -> ReputationScore | None:
        """현재 평판 조회"""
        ...

    async def get_reputation_history(
        self, db: AsyncSession, corp_code: str, limit: int = 30
    ) -> list[ReputationHistory]:
        """평판 이력 조회"""
        ...
```

### 2.6 API 설계: `app/routers/analysis.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/analysis/reputation/{corp_code}` | 현재 평판 조회 |
| GET | `/api/v1/analysis/reputation/{corp_code}/history` | 시계열 이력 조회 |
| POST | `/api/v1/analysis/reputation/{corp_code}/calculate` | 평판 (재)계산 |

---

## 3. Track B: 딜 소싱 시각화 API

### 3.1 섹터 분류 체계

| 섹터 코드 | 표시명 | 분류 키워드 |
|-----------|--------|-------------|
| `ai_deeptech` | AI/딥테크 | AI, 인공지능, 딥러닝, 머신러닝, 자율주행, 로봇 |
| `bio_health` | 바이오/헬스케어 | 바이오, 헬스케어, 의료, 제약, 디지털헬스 |
| `saas` | SaaS | SaaS, 클라우드, B2B, 소프트웨어, 플랫폼 |
| `consumer` | 컨슈머 | 소비재, 뷰티, 패션, F&B, 라이프스타일 |
| `fintech` | 핀테크 | 핀테크, 금융, 페이, 결제, 자산관리 |
| `mobility` | 모빌리티 | 모빌리티, 전기차, 충전, 배터리, 물류 |
| `ecommerce` | 이커머스 | 이커머스, 쇼핑, 유통, 마켓플레이스 |
| `content` | 콘텐츠/미디어 | 콘텐츠, 미디어, 게임, OTT, 웹툰 |
| `proptech` | 프롭테크 | 프롭테크, 부동산, 건설 |
| `edtech` | 에드테크 | 에드테크, 교육, 이러닝 |
| `other` | 기타 | (분류 불가) |

### 3.2 투자 단계 추정 기준

| 단계 | 금액 범위 (억원) | 텍스트 패턴 |
|------|-----------------|-------------|
| **Seed** | 0 ~ 10 | 시드, Seed |
| **Pre-A** | 10 ~ 30 | 프리A, Pre-A |
| **Series A** | 30 ~ 100 | 시리즈A, Series A |
| **Series B** | 100 ~ 300 | 시리즈B, Series B |
| **Series C+** | 300 ~ 1,000 | 시리즈C/D, Series C/D |
| **Pre-IPO** | 1,000+ | Pre-IPO, 프리IPO |
| **Bridge** | - | 브릿지, Bridge |

### 3.3 모델 설계: `app/models/deal.py`

```python
class DealSector(str, Enum):
    """투자 섹터"""
    AI_DEEPTECH = "ai_deeptech"
    BIO_HEALTH = "bio_health"
    SAAS = "saas"
    CONSUMER = "consumer"
    FINTECH = "fintech"
    MOBILITY = "mobility"
    ECOMMERCE = "ecommerce"
    CONTENT = "content"
    PROPTECH = "proptech"
    EDTECH = "edtech"
    OTHER = "other"


class DealStage(str, Enum):
    """투자 단계"""
    SEED = "seed"
    PRE_A = "pre_a"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    PRE_IPO = "pre_ipo"
    BRIDGE = "bridge"


class Deal(TimestampMixin, Base):
    """딜(투자 거래) 모델"""

    __tablename__ = "deals"

    id: Mapped[int]

    # 투자사 정보
    company_id: Mapped[int | None]  # FK → companies.id, SET NULL

    # 피투자사 정보
    target_company: Mapped[str]      # 피투자사명
    target_company_id: Mapped[int | None]  # FK → companies.id, SET NULL

    # 투자 정보
    amount: Mapped[Decimal | None]   # 투자 금액 (원)
    amount_display: Mapped[str | None]  # "100억원"
    round_stage: Mapped[str | None]  # seed/series_a/...
    sector: Mapped[str | None]       # ai_deeptech/bio_health/...
    sector_keywords: Mapped[str | None]  # 분류 근거 키워드 (JSON)

    # 날짜
    deal_date: Mapped[date | None]
    deal_year: Mapped[int | None]    # 집계용

    # 출처
    source_url: Mapped[str | None]
    source_type: Mapped[str | None]  # news/disclosure/manual
    news_article_id: Mapped[int | None]  # FK → news_articles.id

    # 추가 정보
    is_lead_investor: Mapped[bool]   # 리드 투자사 여부
    co_investors: Mapped[str | None]  # 공동 투자사 (JSON)
    description: Mapped[str | None]

    # 관계
    investor_company: Mapped["Company | None"]
    target: Mapped["Company | None"]
    news_article: Mapped["NewsArticle | None"]
```

### 3.4 스키마 설계: `app/schemas/deal.py`

```python
# 딜 상세
class DealItem(BaseModel):
    id: int
    company_id: int | None
    investor_name: str | None
    target_company: str
    amount: Decimal | None
    amount_display: str | None
    round_stage: str | None
    sector: str | None
    deal_date: date | None
    deal_year: int | None
    source_url: str | None
    is_lead_investor: bool

# 딜 목록 응답
class DealListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[DealItem]

# 섹터별 집계
class SectorAggregation(BaseModel):
    sector: str
    sector_name: str
    deal_count: int
    total_amount: Decimal | None

class SectorAggregationResponse(BaseModel):
    total_deals: int
    items: list[SectorAggregation]

# 단계별 집계
class StageAggregation(BaseModel):
    stage: str
    stage_name: str
    deal_count: int
    total_amount: Decimal | None

class StageAggregationResponse(BaseModel):
    total_deals: int
    items: list[StageAggregation]

# 연도별 트렌드
class YearlyTrend(BaseModel):
    year: int
    deal_count: int
    total_amount: Decimal | None

class TrendResponse(BaseModel):
    corp_code: str | None
    corp_name: str | None
    items: list[YearlyTrend]
```

### 3.5 서비스 설계: `app/services/deal_service.py`

```python
class DealService:
    """딜 소싱 분석 서비스"""

    SECTOR_KEYWORDS = {
        "ai_deeptech": ["AI", "인공지능", "딥러닝", "머신러닝", ...],
        "bio_health": ["바이오", "헬스케어", "의료", "제약", ...],
        # ...
    }

    STAGE_AMOUNT_RANGES = {  # 억원 단위
        "seed": (0, 10),
        "pre_a": (10, 30),
        "series_a": (30, 100),
        "series_b": (100, 300),
        "series_c": (300, 1000),
        "pre_ipo": (1000, float('inf')),
    }

    def __init__(self):
        self.nlp_service = NLPService()

    def classify_sector(self, text: str, keywords: list[str] | None = None) -> tuple[str, list[str]]:
        """섹터 자동 분류"""
        # 텍스트 + 키워드에서 SECTOR_KEYWORDS 매칭
        # 가장 많이 매칭된 섹터 반환
        ...

    def estimate_stage(self, amount: Decimal | None, round_text: str | None) -> str:
        """투자 단계 추정"""
        # 1. 라운드 텍스트 우선 매칭
        # 2. 금액 범위 기반 추정
        ...

    async def extract_deal_from_news(self, db: AsyncSession, news_article: NewsArticle) -> Deal | None:
        """뉴스에서 딜 정보 추출"""
        # NLPService.extract_investment_info() 활용
        ...

    async def get_deals_by_company(self, db: AsyncSession, company_id: int, years: int = 5) -> list[Deal]:
        """운용사별 딜 조회"""
        ...

    async def aggregate_by_sector(self, db: AsyncSession, company_id: int | None = None) -> list[dict]:
        """섹터별 집계"""
        ...

    async def aggregate_by_stage(self, db: AsyncSession, company_id: int | None = None) -> list[dict]:
        """단계별 집계"""
        ...

    async def get_yearly_trends(self, db: AsyncSession, company_id: int | None = None) -> list[dict]:
        """연도별 트렌드"""
        ...
```

### 3.6 API 설계: `app/routers/deals.py`

| Method | Path | Query Params | Description |
|--------|------|--------------|-------------|
| GET | `/api/v1/deals/by-company/{corp_code}` | years, sector, stage, page, size | 운용사별 5년 딜 목록 |
| GET | `/api/v1/deals/by-sector` | corp_code, year | 섹터별 집계 |
| GET | `/api/v1/deals/by-stage` | corp_code, year | 단계별 집계 |
| GET | `/api/v1/deals/trends` | corp_code, years | 연도별 트렌드 |
| POST | `/api/v1/deals/extract` | news_article_id | 뉴스에서 딜 추출 |

---

## 4. 파일 수정 목록

### 4.1 수정 필요 파일

#### `app/models/company.py` (라인 31-34 이후 추가)

```python
# 기존 관계
funds: Mapped[list["Fund"]] = relationship(back_populates="company")
reits_list: Mapped[list["REITs"]] = relationship(back_populates="company")
news_articles: Mapped[list["NewsArticle"]] = relationship(back_populates="company")
aliases: Mapped[list["CompanyAlias"]] = relationship(...)

# 추가할 관계
reputation_score: Mapped["ReputationScore | None"] = relationship(
    back_populates="company", uselist=False
)
deals_as_investor: Mapped[list["Deal"]] = relationship(
    foreign_keys="Deal.company_id", back_populates="investor_company"
)
deals_as_target: Mapped[list["Deal"]] = relationship(
    foreign_keys="Deal.target_company_id", back_populates="target"
)
```

#### `app/models/__init__.py`

```python
# 기존 export
from app.models.base import Base, TimestampMixin
from app.models.company import Company, CompanyAlias
from app.models.fund import Fund, FundManager
from app.models.news import NewsArticle
from app.models.reits import REITs, REITsAsset

# 추가할 export
from app.models.reputation import ReputationScore, ReputationHistory
from app.models.deal import Deal, DealSector, DealStage

__all__ = [
    # 기존...
    "ReputationScore",
    "ReputationHistory",
    "Deal",
    "DealSector",
    "DealStage",
]
```

#### `app/main.py` (라인 10, 46-51)

```python
# 라인 10: import 추가
from app.routers import analysis, company, dart, deals, entity, kofia, news, reits

# 라인 51 이후: 라우터 등록 추가
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(deals.router, prefix="/api/v1/deals", tags=["Deals"])
```

---

## 5. 구현 순서

### Phase 1: 모델 (의존성 없음)

1. `app/models/reputation.py` - ReputationScore, ReputationHistory
2. `app/models/deal.py` - Deal, DealSector, DealStage
3. `app/models/__init__.py` - export 추가
4. `app/models/company.py` - relationship 추가

### Phase 2: 스키마 (모델 의존)

5. `app/schemas/analysis.py` - 평판 스키마
6. `app/schemas/deal.py` - 딜 스키마

### Phase 3: 서비스 (모델, 스키마, NLPService 의존)

7. `app/services/reputation_service.py` - 평판 계산 로직
8. `app/services/deal_service.py` - 딜 분석 로직

### Phase 4: 라우터 (서비스, 스키마 의존)

9. `app/routers/analysis.py` - 평판 API
10. `app/routers/deals.py` - 딜 API
11. `app/main.py` - 라우터 등록

### Phase 5: 테스트 (전체 의존)

12. `tests/test_reputation_service.py` - ~15개 테스트
13. `tests/test_deal_service.py` - ~20개 테스트

### Phase 6: DB 마이그레이션

14. `uv run alembic revision --autogenerate -m "add reputation and deal tables"`
15. `uv run alembic upgrade head`

---

## 6. 테스트 케이스

### 6.1 test_reputation_service.py (~15개)

```python
class TestCalculateReputation:
    async def test_calculate_with_news(...)      # 뉴스 있는 경우
    async def test_calculate_no_news(...)        # 뉴스 없는 경우
    async def test_news_score_positive(...)      # 긍정 뉴스
    async def test_news_score_negative(...)      # 부정 뉴스
    async def test_news_score_mixed(...)         # 혼합 뉴스

class TestStatusTag:
    def test_status_rising(...)                  # Rising 조건
    def test_status_stable(...)                  # Stable 조건
    def test_status_risk(...)                    # Risk 조건

class TestNormalization:
    def test_normalize_news_score(...)           # -1~1 → 0~1

class TestHistory:
    async def test_save_history(...)             # 이력 저장
    async def test_get_history(...)              # 이력 조회
```

### 6.2 test_deal_service.py (~20개)

```python
class TestSectorClassification:
    def test_classify_ai_sector(...)             # AI 섹터
    def test_classify_bio_sector(...)            # 바이오 섹터
    def test_classify_saas_sector(...)           # SaaS 섹터
    def test_classify_fintech_sector(...)        # 핀테크 섹터
    def test_classify_other_sector(...)          # 기타 섹터
    def test_classify_multiple_keywords(...)     # 다중 키워드

class TestStageEstimation:
    def test_estimate_seed_by_text(...)          # 텍스트 기반 시드
    def test_estimate_series_a_by_text(...)      # 텍스트 기반 시리즈A
    def test_estimate_series_b_by_amount(...)    # 금액 기반 시리즈B
    def test_estimate_pre_ipo_by_amount(...)     # 금액 기반 Pre-IPO
    def test_estimate_bridge(...)                # 브릿지

class TestDealExtraction:
    async def test_extract_from_news(...)        # 뉴스에서 추출
    async def test_extract_no_amount(...)        # 금액 없는 경우

class TestAggregation:
    async def test_aggregate_by_sector(...)      # 섹터별 집계
    async def test_aggregate_by_stage(...)       # 단계별 집계
    async def test_yearly_trends(...)            # 연도별 트렌드
    async def test_filter_by_company(...)        # 회사별 필터
```

---

## 7. 검증 방법

```bash
# 1. 린트 검사
uv run ruff check app/models/reputation.py app/models/deal.py
uv run ruff check app/services/reputation_service.py app/services/deal_service.py
uv run ruff check app/routers/analysis.py app/routers/deals.py

# 2. 신규 테스트 실행
uv run pytest tests/test_reputation_service.py tests/test_deal_service.py -v

# 3. 전체 테스트
uv run pytest tests/ -v

# 4. 서버 구동 + Swagger UI 확인
uv run uvicorn app.main:app --reload --port 8000
# http://localhost:8000/docs

# 5. API 테스트 (Swagger UI)
# - GET /api/v1/analysis/reputation/{corp_code}
# - GET /api/v1/analysis/reputation/{corp_code}/history
# - POST /api/v1/analysis/reputation/{corp_code}/calculate
# - GET /api/v1/deals/by-company/{corp_code}
# - GET /api/v1/deals/by-sector
# - GET /api/v1/deals/by-stage
# - GET /api/v1/deals/trends
```

---

## 8. 핵심 의존성 참조

| 기능 | 파일 | 함수/클래스 | 용도 |
|------|------|-------------|------|
| 감성 분석 | `app/services/nlp_service.py:105-173` | `analyze_sentiment()` | 뉴스 평판 점수 |
| 키워드 추출 | `app/services/nlp_service.py:64-103` | `extract_keywords()` | 섹터 분류 |
| 투자 정보 추출 | `app/services/nlp_service.py:175-232` | `extract_investment_info()` | 딜 추출 |
| 모델 기본 | `app/models/base.py:13-19` | `TimestampMixin` | 타임스탬프 |
| DB 의존성 | `app/core/database.py` | `get_db` | 세션 주입 |

---

## 9. 완료 기준

- [ ] KIIS 평판 지수 산출 및 API 조회 가능 (Rising/Stable/Risk 태그)
- [ ] 평판 시계열 추이 데이터 조회 가능
- [ ] 5년 딜 소싱 섹터별/단계별/연도별 API 조회 가능
- [ ] 뉴스에서 딜 정보 자동 추출 가능
- [ ] `uv run pytest tests/ -v` 전체 통과
- [ ] `uv run ruff check .` 린트 오류 0건
