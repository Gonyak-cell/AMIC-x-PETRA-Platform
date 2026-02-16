# Auto-IM Generator: 미착수 Phase 통합 구현 계획

> 작성일: 2026-02-08 23:30:00
> 최종 수정: 2026-02-10 21:04:09
> 대상: Phase 2, 3, 5, 6 + Brand Extractor + Chart Engine
> 총 스프린트: 11개 (약 11주)
> 총 티켓: ~95개
> 상태: **전체 완료** (S1-S11: ~95개 티켓 전체 완료)

---

## 1. 개요

Design Renderer (Phase 4, v0.4.0) 완료 후 남은 6개 모듈에 대한 통합 구현 계획입니다.

| Phase | 모듈 | 주요 작업 | 스프린트 |
|-------|------|----------|---------|
| Phase 2 | Data Collection | DART API, 웹 크롤링, 문서 파싱 | S1-S2 |
| Phase 3 | Financial Engine | 계정 매핑, 정규화, 지표 계산 | S2-S3 |
| Phase 5 | AI/Narrative | RAG, 프롬프트, LLM 오케스트레이션 | S4-S6 |
| - | Chart Engine | Plotly 확장, Graphviz, 내보내기 | S7 |
| - | Brand Extractor | 로고/컬러 추출, Brandfetch | S8 |
| Phase 6 | Integration | FastAPI, Celery, DB, 배포 | S9-S11 |

### 1.1 프로젝트 전체 구조

```
auto-im-generator/
├── src/
│   ├── data_ingestor/       # Phase 2 ✅ 완료 (v0.2.1)
│   ├── financial_engine/    # Phase 3 ✅ 완료 (v0.3.0)
│   ├── narrative_generator/ # Phase 5 ✅ 완료 (v0.5.0)
│   ├── chart_engine/        # Chart Engine ✅ 완료 (v0.7.0)
│   ├── brand_extractor/     # Brand Extractor ✅ 완료 (v0.8.0)
│   ├── design_renderer/     # Phase 4 ✅ 완료 (v0.4.0)
│   └── api/                 # Phase 6 ✅ 완료 (S9-S11)
├── tests/
├── docs/
└── templates/
```

---

## 2. Phase 2: Data Collection (`src/data_ingestor/`)

### 2.1 모듈 구조

```
src/data_ingestor/
├── __init__.py              # Public API
├── exceptions.py            # DartAPIError, ParserError, CrawlerError
├── dart/
│   ├── __init__.py
│   ├── client.py           # DartAPIClient (httpx async)
│   ├── models.py           # DartCompanyInfo, DartFinancialStatement
│   ├── endpoints.py        # DART API 엔드포인트 정의
│   └── rate_limiter.py     # Token bucket (100 calls/min)
├── parsers/
│   ├── __init__.py
│   ├── pdf_parser.py       # PyMuPDF 기반 PDF 추출
│   ├── excel_parser.py     # openpyxl/pandas Excel 파싱
│   └── structured_extractor.py  # 공통 추출 패턴
├── crawler/
│   ├── __init__.py
│   ├── news_crawler.py     # 뉴스/시장 데이터
│   ├── company_crawler.py  # 회사 웹사이트
│   └── playwright_engine.py # JS 렌더링 크롤러
└── aggregator.py           # DataAggregator → IMDocumentData
```

### 2.2 핵심 클래스

```python
# dart/client.py
class DartAPIClient:
    """Open DART API 클라이언트 (100 calls/min 제한).

    Usage::
        async with DartAPIClient() as client:
            info = await client.get_company_info("00123456")
            fs = await client.get_financial_statements(
                corp_code="00123456",
                bsns_year="2024",
                reprt_code="11011",  # 사업보고서
                fs_div="CFS",  # 연결
            )
    """
    async def get_company_info(corp_code: str) -> DartCompanyInfo
    async def get_financial_statements(corp_code, bsns_year, reprt_code, fs_div) -> list[DartFinancialStatement]
    async def get_major_shareholders(corp_code: str) -> list[dict]
    async def search_company(company_name: str) -> list[tuple[str, str]]

# aggregator.py
class DataAggregator:
    """수집 데이터 → IMDocumentData 통합.

    Usage::
        aggregator = DataAggregator()
        aggregator.add_dart_company(dart_info)
        aggregator.add_dart_financials(dart_fs_list)
        aggregator.add_parsed_financials(parsed_data)
        im_data = aggregator.build()
    """
    def add_dart_company(info: DartCompanyInfo) -> None
    def add_dart_financials(statements: list) -> None
    def add_parsed_financials(data: dict) -> None
    def build() -> IMDocumentData
```

### 2.3 스프린트 S1: Foundation (5일) ✅

#### T-D01: exceptions.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Infrastructure |
| **의존성** | ← 없음 |
| **설명** | 커스텀 예외 계층 구현: DartAPIError, ParserError, CrawlerError |
| **산출물** | `src/data_ingestor/exceptions.py` |
| **검증** | 예외 클래스 임포트 테스트 (27 tests passed) |

#### T-D02: rate_limiter.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Infrastructure |
| **의존성** | ← 없음 |
| **설명** | Token Bucket 알고리즘 기반 100 calls/min 제한기 |
| **산출물** | `src/data_ingestor/dart/rate_limiter.py` |
| **소스** | `.claude/skills/rate-limiter/SKILL.md` 패턴 참조 |
| **검증** | 동시 요청 시 rate limit 동작 확인 (19 tests passed) |

#### T-D03: dart/models.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Data Models |
| **의존성** | ← 없음 |
| **설명** | Pydantic 기반 DART API 응답 모델: DartCompanyInfo, DartFinancialStatement |
| **산출물** | `src/data_ingestor/dart/models.py` |
| **검증** | JSON → 모델 직렬화/역직렬화 테스트 (16 tests passed) |

#### T-D04: dart/endpoints.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Data Models |
| **의존성** | ← 없음 |
| **설명** | DART API 엔드포인트 URL 상수 정의 |
| **산출물** | `src/data_ingestor/dart/endpoints.py` |
| **검증** | 모든 엔드포인트 상수 정의 확인 (34 tests passed) |

#### T-D05: requirements.txt 업데이트 ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Infrastructure |
| **의존성** | ← 없음 |
| **설명** | 신규 의존성 추가: aiofiles, respx, pytest-httpx |
| **산출물** | `requirements.txt` 업데이트 |
| **검증** | `pip install -r requirements.txt` 성공 |

### 2.4 스프린트 S2: Core Clients (5일) ✅

#### T-D06: DartAPIClient 기본 구조 ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: DART Integration |
| **의존성** | ← T-D02, T-D03, T-D04 |
| **설명** | httpx 기반 비동기 클라이언트 기본 구조 (컨텍스트 매니저, 에러 핸들링) |
| **산출물** | `src/data_ingestor/dart/client.py` |
| **검증** | 클라이언트 초기화 및 종료 테스트 |

#### T-D07: get_company_info() ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: DART Integration |
| **의존성** | ← T-D06 |
| **설명** | DART company.json API 호출 구현 |
| **산출물** | `client.py` 내 메서드 |
| **검증** | 실제 API 호출 또는 모킹 테스트 |

#### T-D08: get_financial_statements() ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: DART Integration |
| **의존성** | ← T-D06 |
| **설명** | DART fnlttSinglAcnt.json API 호출 (별도/연결, 연간/분기) |
| **산출물** | `client.py` 내 메서드 |
| **검증** | 3~5개년 재무제표 조회 테스트 |

#### T-D09: get_major_shareholders() ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: DART Integration |
| **의존성** | ← T-D06 |
| **설명** | DART majorstock.json API 호출 |
| **산출물** | `client.py` 내 메서드 |
| **검증** | 주요주주 목록 조회 테스트 |

#### T-D10: pdf_parser.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Document Parsing |
| **의존성** | ← T-D01 |
| **설명** | PyMuPDF 기반 PDF 테이블/텍스트 추출 |
| **산출물** | `src/data_ingestor/parsers/pdf_parser.py` |
| **검증** | 샘플 사업보고서 PDF 테이블 추출 |

#### T-D11: excel_parser.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Document Parsing |
| **의존성** | ← T-D01 |
| **설명** | openpyxl/pandas 기반 재무 템플릿 Excel 파싱 |
| **산출물** | `src/data_ingestor/parsers/excel_parser.py` |
| **검증** | 샘플 재무 Excel 파싱 테스트 |

#### T-D12: playwright_engine.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Web Crawling |
| **의존성** | ← T-D02 |
| **설명** | Playwright 기반 JS 렌더링 크롤러 엔진 |
| **산출물** | `src/data_ingestor/crawler/playwright_engine.py` |
| **검증** | JS 기반 페이지 크롤링 테스트 |

#### T-D13: news_crawler.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Web Crawling |
| **의존성** | ← T-D12 |
| **설명** | 뉴스/시장 데이터 크롤러 (Naver/Google News) |
| **산출물** | `src/data_ingestor/crawler/news_crawler.py` |
| **검증** | 기업명 기반 뉴스 검색 테스트 |

#### T-D14: company_crawler.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Web Crawling |
| **의존성** | ← T-D12 |
| **설명** | 회사 홈페이지 크롤러 (about, 제품, IR 정보) |
| **산출물** | `src/data_ingestor/crawler/company_crawler.py` |
| **검증** | 샘플 기업 홈페이지 크롤링 테스트 |

#### T-D15: aggregator.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | F: Aggregation |
| **의존성** | ← T-D07~T-D14 |
| **설명** | 수집 데이터 → IMDocumentData 통합 |
| **산출물** | `src/data_ingestor/aggregator.py` |
| **검증** | DART + 파싱 + 크롤링 데이터 통합 테스트 |

#### T-D16: 테스트 (15+ tests) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-D15 |
| **설명** | data_ingestor 모듈 단위/통합 테스트 |
| **산출물** | `tests/test_data_ingestor/` (15+ 테스트) |
| **검증** | pytest 전체 통과, 커버리지 80%+ |

---

## 3. Phase 3: Financial Engine (`src/financial_engine/`)

### 3.1 모듈 구조

```
src/financial_engine/
├── __init__.py              # Public API
├── exceptions.py            # MappingError, ValidationError
├── mapper/
│   ├── __init__.py
│   ├── account_mapper.py   # 퍼지 매칭 (rapidfuzz)
│   ├── chart_of_accounts.py # 표준 계정과목 코드
│   └── korean_accounts.py  # 한글 계정명 동의어 (200+)
├── normalizer/
│   ├── __init__.py
│   ├── unit_normalizer.py  # 천원/백만원/억원 → 원
│   ├── currency_converter.py # USD/EUR → KRW
│   └── period_aligner.py   # 회계기간 정렬
├── calculator/
│   ├── __init__.py
│   ├── profitability.py    # GPM, OPM, NPM, ROA, ROE
│   ├── growth.py           # YoY, CAGR
│   ├── cash_flow.py        # EBITDA, FCF, NWC
│   └── leverage.py         # D/E, ICR
├── validator/
│   ├── __init__.py
│   ├── balance_checker.py  # A = L + E 검증
│   ├── consistency_checker.py # 다기간 일관성
│   └── outlier_detector.py # 이상치 탐지
└── processor.py            # FinancialProcessor 오케스트레이션
```

### 3.2 핵심 클래스

```python
# mapper/account_mapper.py
class AccountMapper:
    """한글 계정명 → 표준 코드 퍼지 매칭.

    Usage::
        mapper = AccountMapper()
        result = mapper.map("매출액")
        # AccountMapping(original_name="매출액", standard_code="REVENUE", ...)

        mapped = mapper.map_all({
            "매출액": {"2023": 10000, "2024": 15000},
            "영업이익": {"2023": 1500, "2024": 2200},
        })
    """
    def map(account_name: str) -> AccountMapping | None
    def map_all(data: dict) -> dict  # 키를 표준코드로 변환
    def add_synonym(korean_name: str, standard_code: str) -> None

# processor.py
class FinancialProcessor:
    """재무 데이터 처리 파이프라인.

    Usage::
        processor = FinancialProcessor()
        result = processor.process(
            raw_data={"매출액": {"2024": "1500억원"}, ...},
            source_unit="억원",
            target_unit="백만원",
        )
        fs = result.to_financial_statements()
    """
    def process(raw_data, source_unit, target_unit) -> ProcessingResult
    def validate(financial_statements) -> ValidationResult

@dataclass
class ProcessingResult:
    mapped_data: dict[str, dict[str, Decimal]]
    profitability: ProfitabilityMetrics
    growth: GrowthMetrics
    cash_flow: CashFlowMetrics
    leverage: LeverageMetrics
    validation: ValidationResult
    def to_financial_statements() -> FinancialStatements
```

### 3.3 스프린트 S3: Financial Engine (5일) ✅

#### T-F01: chart_of_accounts.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Account Mapping |
| **의존성** | ← 없음 |
| **설명** | 표준 계정과목 코드 정의 (50+ 계정) |
| **산출물** | `src/financial_engine/mapper/chart_of_accounts.py` |
| **검증** | 필수 계정 (REVENUE, COGS, OP_INCOME 등) 존재 확인 |

#### T-F02: korean_accounts.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Account Mapping |
| **의존성** | ← 없음 |
| **설명** | 한글 계정명 동의어 사전 (200+ 매핑) |
| **산출물** | `src/financial_engine/mapper/korean_accounts.py` |
| **검증** | "매출액", "영업수익", "순매출" → REVENUE 매핑 확인 |

#### T-F03: account_mapper.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Account Mapping |
| **의존성** | ← T-F01, T-F02 |
| **설명** | rapidfuzz 기반 퍼지 매칭 엔진 |
| **산출물** | `src/financial_engine/mapper/account_mapper.py` |
| **검증** | 매핑 정확도 90%+ 테스트 |

#### T-F04: unit_normalizer.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Normalization |
| **의존성** | ← 없음 |
| **설명** | 단위 정규화기 (천원/백만원/억원 → 원) |
| **산출물** | `src/financial_engine/normalizer/unit_normalizer.py` |
| **검증** | "1,500백만원" → Decimal("1500000000") 변환 테스트 |

#### T-F05: currency_converter.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Normalization |
| **의존성** | ← 없음 |
| **설명** | 통화 변환기 (USD/EUR → KRW, 환율 API 연동) |
| **산출물** | `src/financial_engine/normalizer/currency_converter.py` |
| **검증** | 환율 조회 및 변환 테스트 |

#### T-F06: profitability.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Calculation |
| **의존성** | ← 없음 |
| **설명** | 수익성 지표 계산 (GPM, OPM, NPM, ROA, ROE) |
| **산출물** | `src/financial_engine/calculator/profitability.py` |
| **검증** | 샘플 데이터 마진 계산 검증 |

#### T-F07: growth.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Calculation |
| **의존성** | ← 없음 |
| **설명** | 성장 지표 계산 (YoY, 3Y/5Y CAGR) |
| **산출물** | `src/financial_engine/calculator/growth.py` |
| **검증** | CAGR 공식 검증 (start=100, end=150, years=3) |

#### T-F08: cash_flow.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Calculation |
| **의존성** | ← 없음 |
| **설명** | 현금흐름 지표 계산 (EBITDA, FCF, NWC) |
| **산출물** | `src/financial_engine/calculator/cash_flow.py` |
| **검증** | EBITDA = 영업이익 + 감가상각비 검증 |

#### T-F09: leverage.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Calculation |
| **의존성** | ← 없음 |
| **설명** | 레버리지 지표 계산 (D/E, Interest Coverage) |
| **산출물** | `src/financial_engine/calculator/leverage.py` |
| **검증** | 부채비율 계산 검증 |

#### T-F10: balance_checker.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Validation |
| **의존성** | ← 없음 |
| **설명** | 재무상태표 균형 검증 (A = L + E, 허용 오차 설정) |
| **산출물** | `src/financial_engine/validator/balance_checker.py` |
| **검증** | 균형/불균형 케이스 테스트 |

#### T-F11: consistency_checker.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Validation |
| **의존성** | ← T-F10 |
| **설명** | 다기간 일관성 검증 (이익잉여금 연속성, 이상 변동 탐지) |
| **산출물** | `src/financial_engine/validator/consistency_checker.py` |
| **검증** | 50%+ 변동 항목 탐지 테스트 |

#### T-F12: processor.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Orchestration |
| **의존성** | ← T-F03~T-F11 |
| **설명** | FinancialProcessor 오케스트레이션 파이프라인 |
| **산출물** | `src/financial_engine/processor.py` |
| **검증** | raw_data → ProcessingResult → FinancialStatements |

#### T-F13: 테스트 (20+ tests) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-F12 |
| **설명** | financial_engine 모듈 단위/통합 테스트 |
| **산출물** | `tests/test_financial_engine/` (20+ 테스트) |
| **검증** | pytest 전체 통과, 커버리지 90%+ |

#### T-F14: E2E: DART → Financial → IMDocumentData ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-D15, T-F12 |
| **설명** | data_ingestor + financial_engine E2E 통합 테스트 |
| **산출물** | `tests/test_integration/test_dart_to_im.py` |
| **검증** | DART API → 정규화 → IMDocumentData 생성 확인 |

---

## 4. Phase 5: AI/Narrative (`src/narrative_generator/`)

### 4.1 모듈 구조

```
src/narrative_generator/
├── __init__.py
├── config.py               # Pinecone, OpenAI 설정
├── rag/
│   ├── __init__.py
│   ├── embedder.py        # OpenAI embedding (text-embedding-3-small)
│   ├── vector_store.py    # Pinecone 클라이언트
│   ├── retriever.py       # 컨텍스트 검색 + 리랭킹
│   └── chunker.py         # 문서 청킹 전략
├── prompts/
│   ├── __init__.py        # 프롬프트 레지스트리
│   ├── base.py            # BasePrompt 추상 클래스
│   ├── section_prompts/   # 18개 섹션별 프롬프트
│   │   ├── executive_summary.py
│   │   ├── investment_highlights.py
│   │   ├── company_overview.py
│   │   ├── market_overview.py
│   │   ├── financial_analysis.py
│   │   └── ... (13개 더)
│   └── industry_variants/ # 산업별 변형
│       ├── tech.py
│       ├── healthcare.py
│       ├── manufacturing.py
│       └── financial_services.py
├── engine/
│   ├── __init__.py
│   ├── orchestrator.py    # LangChain 오케스트레이션
│   ├── token_budget.py    # 토큰 예산 관리
│   └── structured_output.py # 구조화된 출력 파싱
├── fact_checker/
│   ├── __init__.py
│   ├── validator.py       # 수치 클레임 검증
│   ├── consistency.py     # 내러티브 간 일관성
│   └── confidence.py      # 신뢰도 점수
└── korean_finance/
    ├── __init__.py
    ├── terminology.py     # 한국 금융 용어
    └── tone_adapter.py    # "Factual optimism" 톤
```

### 4.2 핵심 클래스

```python
# rag/retriever.py
class RAGRetriever:
    """산업별 필터링 + 리랭킹 컨텍스트 검색.

    Usage::
        retriever = RAGRetriever(embedder, vector_store)
        contexts = await retriever.retrieve(
            query="executive summary for tech company",
            section_id="executive_summary",
            industry="tech",
            top_k=5,
        )
    """
    async def retrieve(query, section_id, industry, top_k) -> list[RetrievedContext]

# engine/orchestrator.py
class NarrativeOrchestrator:
    """LangChain 기반 내러티브 생성.

    Usage::
        orchestrator = NarrativeOrchestrator(llm, retriever, prompt_registry)
        narrative = await orchestrator.generate_narrative(
            section_id="executive_summary",
            data=im_data,
            industry="tech",
        )

        all_narratives = await orchestrator.generate_all_narratives(im_data, "tech")
    """
    async def generate_narrative(section_id, data, industry) -> str
    async def generate_all_narratives(data, industry) -> dict[str, str]

# fact_checker/validator.py
class NarrativeValidator:
    """수치 클레임 검증.

    Usage::
        validator = NarrativeValidator(tolerance=0.01)
        results = validator.validate(narrative_text, source_im_data)
        for r in results:
            if not r.is_valid:
                print(f"Claim '{r.claim}' invalid: {r.explanation}")
    """
    def validate(narrative, source_data) -> list[FactCheckResult]
```

### 4.3 스프린트 S4: RAG Infrastructure (5일) ✅

#### T-N01: config.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Infrastructure |
| **의존성** | ← 없음 |
| **설명** | Pydantic Settings 기반 설정 (Pinecone, OpenAI API 키) |
| **산출물** | `src/narrative_generator/config.py` |
| **검증** | 환경변수 로딩 테스트 |

#### T-N02: embedder.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: RAG |
| **의존성** | ← T-N01 |
| **설명** | OpenAI text-embedding-3-small 래퍼 (EmbedderProtocol 인터페이스) |
| **산출물** | `src/narrative_generator/rag/embedder.py` |
| **검증** | 임베딩 차원 (1536) 검증 |

#### T-N03: vector_store.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: RAG |
| **의존성** | ← T-N01 |
| **설명** | Pinecone 클라이언트 래퍼 (upsert, query) |
| **산출물** | `src/narrative_generator/rag/vector_store.py` |
| **검증** | 벡터 업서트/쿼리 테스트 |

#### T-N04: chunker.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: RAG |
| **의존성** | ← 없음 |
| **설명** | 문서 청킹 유틸리티 (토큰 기반, 오버랩 청킹) |
| **산출물** | `src/narrative_generator/rag/chunker.py` |
| **검증** | 청크 크기/오버랩 검증 |

#### T-N05: retriever.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: RAG |
| **의존성** | ← T-N02, T-N03 |
| **설명** | RAGRetriever (산업별 필터링, 리랭킹) |
| **산출물** | `src/narrative_generator/rag/retriever.py` |
| **검증** | 컨텍스트 검색 품질 테스트 |

#### T-N06: korean_finance/terminology.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Korean Finance |
| **의존성** | ← 없음 |
| **설명** | 한국 금융 용어 매핑 (영문 → 한글, 약어 풀이) |
| **산출물** | `src/narrative_generator/korean_finance/terminology.py` |
| **검증** | "EBITDA" → "EBITDA (상각전영업이익)" 변환 |

### 4.4 스프린트 S5: Prompts (5일) ✅

#### T-N07: base.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Prompts |
| **의존성** | ← 없음 |
| **설명** | BasePrompt 추상 클래스 + 프롬프트 레지스트리 |
| **산출물** | `src/narrative_generator/prompts/base.py` |
| **검증** | 추상 메서드 강제 구현 확인 |

#### T-N08: Core 프롬프트 (4개) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Prompts |
| **의존성** | ← T-N07 |
| **설명** | executive_summary, company_overview, business_overview, deal_overview |
| **산출물** | `prompts/section_prompts/` (4개 파일) |
| **검증** | 프롬프트 렌더링 테스트 |

#### T-N09: Financial 프롬프트 (3개) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Prompts |
| **의존성** | ← T-N07 |
| **설명** | financial_analysis, transaction_structure, shareholder_structure |
| **산출물** | `prompts/section_prompts/` (3개 파일) |
| **검증** | 재무 데이터 포맷팅 테스트 |

#### T-N10: Strategy 프롬프트 (4개) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Prompts |
| **의존성** | ← T-N07 |
| **설명** | investment_highlights, market_overview, value_creation, growth_strategy |
| **산출물** | `prompts/section_prompts/` (4개 파일) |
| **검증** | 프롬프트 렌더링 테스트 |

#### T-N11: Supporting 프롬프트 (4개) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Prompts |
| **의존성** | ← T-N07 |
| **설명** | management_team, business_model, appendix, contact |
| **산출물** | `prompts/section_prompts/` (4개 파일) |
| **검증** | 프롬프트 렌더링 테스트 |

#### T-N12: Industry variants (4개) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Prompts |
| **의존성** | ← T-N08~T-N11 |
| **설명** | tech, healthcare, manufacturing, financial_services 산업별 변형 |
| **산출물** | `prompts/industry_variants/` (4개 파일) |
| **검증** | 산업별 톤/용어 차이 확인 |

### 4.5 스프린트 S6: Engine + Fact Checker (5일) ✅

#### T-N13: orchestrator.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Engine |
| **의존성** | ← T-N05, T-N07~T-N12 |
| **설명** | LangChain 기반 NarrativeOrchestrator |
| **산출물** | `src/narrative_generator/engine/orchestrator.py` |
| **검증** | 단일/전체 내러티브 생성 테스트 |

#### T-N14: token_budget.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Engine |
| **의존성** | ← T-N13 |
| **설명** | 섹션별 토큰 예산 관리 (tiktoken) |
| **산출물** | `src/narrative_generator/engine/token_budget.py` |
| **검증** | 예산 초과 시 truncate 동작 |

#### T-N15: structured_output.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Engine |
| **의존성** | ← T-N13 |
| **설명** | LLM 출력 → 구조화된 형식 파싱 |
| **산출물** | `src/narrative_generator/engine/structured_output.py` |
| **검증** | JSON/마크다운 파싱 테스트 |

#### T-N16: validator.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | F: Fact Checker |
| **의존성** | ← T-N13 |
| **설명** | 수치 클레임 추출 및 검증 |
| **산출물** | `src/narrative_generator/fact_checker/validator.py` |
| **검증** | 잘못된 수치 탐지 테스트 |

#### T-N17: consistency.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | F: Fact Checker |
| **의존성** | ← T-N16 |
| **설명** | 내러티브 간 일관성 검증 |
| **산출물** | `src/narrative_generator/fact_checker/consistency.py` |
| **검증** | 섹션 간 모순 탐지 테스트 |

#### T-N18: confidence.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | F: Fact Checker |
| **의존성** | ← T-N16 |
| **설명** | 클레임별 신뢰도 점수 |
| **산출물** | `src/narrative_generator/fact_checker/confidence.py` |
| **검증** | 점수 범위 (0-1) 검증 |

#### T-N19: 테스트 (25+ tests) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-N13~T-N18 |
| **설명** | narrative_generator 모듈 단위/통합 테스트 |
| **산출물** | `tests/test_narrative_generator/` (25+ 테스트) |
| **검증** | pytest 전체 통과, 커버리지 85%+ |

---

## 5. Chart Engine (`src/chart_engine/`)

### 5.1 모듈 구조

```
src/chart_engine/
├── __init__.py            # create_chart(), export_chart()
├── config.py              # ChartConfig (DPI, 폰트)
├── plotly/
│   ├── __init__.py
│   ├── waterfall.py      # 영업이익 브릿지
│   ├── combo.py          # 매출 + 마진 듀얼축
│   ├── stacked_bar.py    # 세그먼트 매출
│   ├── donut.py          # 시장점유율
│   ├── line.py           # KPI 추이
│   ├── hbar.py           # 경쟁사 비교
│   └── themes.py         # AMIC 테마 팩토리
├── graphviz/
│   ├── __init__.py
│   ├── org_chart.py      # 조직도
│   ├── flow_diagram.py   # 거래 구조도
│   └── shareholding.py   # 주주 구조도
├── export/
│   ├── __init__.py
│   ├── png_exporter.py   # 300 DPI PNG (Kaleido)
│   ├── svg_exporter.py   # SVG for PDF
│   └── pptx_embed.py     # PPTX 이미지 삽입
└── data_transformer.py    # IMDocumentData → ChartData
```

### 5.2 스프린트 S7: Chart Engine (4일) ✅

#### T-C01: 모듈 구조 리팩토링 ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Structure |
| **의존성** | ← 없음 |
| **설명** | 기존 chart_embed.py → plotly/ 서브패키지 분리 |
| **산출물** | `src/chart_engine/plotly/` 구조 |
| **검증** | 기존 기능 동작 확인 |

#### T-C02: themes.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Plotly |
| **의존성** | ← T-C01 |
| **설명** | AMIC 테마 팩토리 (create_amic_theme(tokens)) |
| **산출물** | `src/chart_engine/plotly/themes.py` |
| **검증** | IMDesignTokens → Plotly layout 변환 |

#### T-C03: graphviz/org_chart.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Graphviz |
| **의존성** | ← T-C01 |
| **설명** | 기존 org_chart.py 확장 (스타일링, AMIC 테마) |
| **산출물** | `src/chart_engine/graphviz/org_chart.py` |
| **검증** | 조직도 SVG 생성 테스트 |

#### T-C04: graphviz/flow_diagram.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Graphviz |
| **의존성** | ← T-C01 |
| **설명** | 거래 구조 다이어그램 (매도인→대상회사→매수인) |
| **산출물** | `src/chart_engine/graphviz/flow_diagram.py` |
| **검증** | 샘플 거래 구조 렌더링 |

#### T-C05: graphviz/shareholding.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Graphviz |
| **의존성** | ← T-C01 |
| **설명** | 주주 구조 다이어그램 (지분율 표시) |
| **산출물** | `src/chart_engine/graphviz/shareholding.py` |
| **검증** | 샘플 주주 구조 렌더링 |

#### T-C06: data_transformer.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Data |
| **의존성** | ← T-C01 |
| **설명** | IMDocumentData → ChartData 변환기 |
| **산출물** | `src/chart_engine/data_transformer.py` |
| **검증** | 재무 데이터 → 차트 데이터 변환 |

#### T-C07: export/png_exporter.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Export |
| **의존성** | ← T-C01 |
| **설명** | 300 DPI PNG 내보내기 (Kaleido) |
| **산출물** | `src/chart_engine/export/png_exporter.py` |
| **검증** | 이미지 DPI 검증 |

#### T-C08: export/svg_exporter.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Export |
| **의존성** | ← T-C01 |
| **설명** | PDF용 SVG 내보내기 |
| **산출물** | `src/chart_engine/export/svg_exporter.py` |
| **검증** | SVG 유효성 검증 |

#### T-C09: 테스트 (15+ tests) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-C01~T-C08 |
| **설명** | chart_engine 모듈 단위/통합 테스트 |
| **산출물** | `tests/test_chart_engine/` (15+ 테스트) |
| **검증** | 6개 Plotly + 3개 Graphviz 차트 렌더링 |

---

## 6. Brand Extractor (`src/brand_extractor/`)

### 6.1 모듈 구조

```
src/brand_extractor/
├── __init__.py           # extract_brand() 공개 API
├── config.py             # Brandfetch API 키
├── models.py             # BrandAssets 데이터클래스
├── extractors/
│   ├── __init__.py
│   ├── brandfetch.py    # Brandfetch API 래퍼
│   ├── website.py       # 웹사이트 로고/컬러 추출
│   └── fallback.py      # AMIC 기본값 폴백
├── logo/
│   ├── __init__.py
│   ├── detector.py      # HTML 로고 탐지
│   ├── scorer.py        # 이미지 품질 점수
│   └── processor.py     # 리사이즈/포맷 변환
└── color/
    ├── __init__.py
    ├── extractor.py     # K-Means 클러스터링
    ├── classifier.py    # Primary/Secondary 분류
    └── token_mapper.py  # → IMDesignTokens
```

### 6.2 스프린트 S8: Brand Extractor (5일) ✅

#### T-B01: models.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Models |
| **의존성** | ← 없음 |
| **설명** | BrandAssets 데이터클래스 (로고 경로, 컬러 hex) |
| **산출물** | `src/brand_extractor/models.py` |
| **검증** | 데이터클래스 직렬화 테스트 |

#### T-B02: brandfetch.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Extractors |
| **의존성** | ← T-B01 |
| **설명** | Brandfetch API 클라이언트 |
| **산출물** | `src/brand_extractor/extractors/brandfetch.py` |
| **검증** | API 모킹 테스트 |

#### T-B03: logo/detector.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Logo |
| **의존성** | ← 없음 |
| **설명** | HTML에서 로고 URL 탐지 (og:image, favicon, <img>) |
| **산출물** | `src/brand_extractor/logo/detector.py` |
| **검증** | 샘플 HTML 로고 탐지 |

#### T-B04: logo/scorer.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Logo |
| **의존성** | ← T-B03 |
| **설명** | 이미지 품질 점수 (해상도, 포맷, 투명도) |
| **산출물** | `src/brand_extractor/logo/scorer.py` |
| **검증** | 품질 점수 범위 (0-1) 검증 |

#### T-B05: color/extractor.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Color |
| **의존성** | ← 없음 |
| **설명** | K-Means 클러스터링 기반 색상 추출 |
| **산출물** | `src/brand_extractor/color/extractor.py` |
| **검증** | 샘플 이미지 5개 색상 추출 |

#### T-B06: color/classifier.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Color |
| **의존성** | ← T-B05 |
| **설명** | Primary/Secondary/Accent 색상 분류 |
| **산출물** | `src/brand_extractor/color/classifier.py` |
| **검증** | 밝기/채도 기반 분류 테스트 |

#### T-B07: color/token_mapper.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Color |
| **의존성** | ← T-B06 |
| **설명** | BrandAssets → IMDesignTokens.from_brand_assets() |
| **산출물** | `src/brand_extractor/color/token_mapper.py` |
| **검증** | 토큰 오버라이드 검증 |

#### T-B08: website.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Extractors |
| **의존성** | ← T-B03, T-B05 |
| **설명** | Playwright + 로고 + 컬러 통합 추출 |
| **산출물** | `src/brand_extractor/extractors/website.py` |
| **검증** | 웹사이트 크롤링 → BrandAssets |

#### T-B09: fallback.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Extractors |
| **의존성** | ← T-B01 |
| **설명** | AMIC 기본값 폴백 |
| **산출물** | `src/brand_extractor/extractors/fallback.py` |
| **검증** | 추출 실패 시 기본값 반환 |

#### T-B10: 테스트 (12+ tests) ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-B01~T-B09 |
| **설명** | brand_extractor 모듈 단위/통합 테스트 |
| **산출물** | `tests/test_brand_extractor/` (12+ 테스트) |
| **검증** | API 모킹, K-Means 추출 테스트 |

---

## 7. Phase 6: Integration (`src/api/`)

### 7.1 모듈 구조

```
src/api/
├── __init__.py            # FastAPI 앱 팩토리
├── main.py                # 애플리케이션 진입점
├── config.py              # Pydantic Settings
├── dependencies.py        # DI (get_current_user, get_db)
├── routes/
│   ├── __init__.py
│   ├── documents.py      # POST/GET /api/v1/documents
│   ├── companies.py      # POST/GET /api/v1/companies
│   ├── health.py         # 헬스체크
│   └── webhooks.py       # 웹훅 관리
├── schemas/
│   ├── __init__.py
│   ├── documents.py      # DocumentCreate, DocumentResponse
│   ├── companies.py      # CompanyRequest, CompanyResponse
│   ├── common.py         # Pagination, ErrorResponse
│   └── im_data.py        # IMDocumentDataSchema
├── services/
│   ├── __init__.py
│   ├── document_service.py
│   ├── company_service.py
│   └── webhook_service.py
├── security/
│   ├── __init__.py
│   ├── auth.py           # JWT 토큰
│   ├── api_keys.py       # API 키 관리
│   ├── rbac.py           # 역할 기반 접근제어
│   └── tenant.py         # 멀티테넌트 격리
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py     # Celery 설정
│   ├── generate_im.py    # generate_im_task
│   ├── fetch_company.py  # fetch_company_data_task
│   └── narrative.py      # generate_narrative_task
├── db/
│   ├── __init__.py
│   ├── base.py           # SQLAlchemy Base, 엔진
│   ├── session.py        # Async 세션 팩토리
│   └── models/
│       ├── __init__.py
│       ├── document.py   # Document 모델
│       ├── company.py    # Company 모델
│       └── user.py       # User 모델
└── middleware/
    ├── __init__.py
    ├── rate_limit.py     # SlowAPI
    ├── cors.py           # CORS 설정
    └── logging.py        # 요청/응답 로깅
```

### 7.2 API 엔드포인트

| Method | Endpoint | 설명 | 응답 |
|--------|----------|------|------|
| POST | `/api/v1/documents` | IM 문서 생성 작업 시작 | 202 Accepted |
| GET | `/api/v1/documents/{id}` | 작업 상태/결과 조회 | 200 OK |
| GET | `/api/v1/documents/{id}/download` | PPTX/PDF 다운로드 | 200 OK (binary) |
| POST | `/api/v1/companies` | DART에서 기업 데이터 가져오기 | 202 Accepted |
| GET | `/api/v1/companies/{corp_code}` | 캐시된 기업 정보 조회 | 200 OK |

### 7.3 Celery 작업 흐름

```
POST /api/v1/documents
        │
        ▼
┌───────────────────────────────────────────────────────┐
│  generate_im_task (chord)                              │
├───────────────────────────────────────────────────────┤
│                                                       │
│  Stage 1: Data Collection (group) ─────── progress 25%│
│    ├─ fetch_financial_statements_task                 │
│    ├─ fetch_company_info_task                         │
│    └─ crawl_web_data_task                             │
│                                                       │
│  Stage 2: Analysis (chain) ────────────── progress 40%│
│    └─ analyze_financials_task                         │
│                                                       │
│  Stage 3: Content Gen (group) ─────────── progress 70%│
│    ├─ generate_narrative_task (×18 sections)          │
│    └─ generate_charts_task                            │
│                                                       │
│  Stage 4: Render (chain) ──────────────── progress 95%│
│    └─ render_document_task ← IMPipeline.generate()    │
│                                                       │
│  Stage 5: Finalize (callback) ─────────── progress 100%│
│    ├─ Upload to storage (S3/local)                    │
│    ├─ Update DB (status = COMPLETED)                  │
│    └─ Trigger webhook (if configured)                 │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### 7.4 스프린트 S9: Foundation (5일) ✅

#### T-I01: main.py, __init__.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Foundation |
| **의존성** | ← 없음 |
| **설명** | FastAPI 앱 팩토리 및 진입점 |
| **산출물** | `src/api/main.py`, `src/api/__init__.py` |
| **검증** | uvicorn 실행 테스트 |

#### T-I02: config.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | A: Foundation |
| **의존성** | ← 없음 |
| **설명** | Pydantic Settings (DB, Redis, 외부 API 키) |
| **산출물** | `src/api/config.py` |
| **검증** | 환경변수 로딩 테스트 |

#### T-I03: db/base.py, session.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Database |
| **의존성** | ← T-I02 |
| **설명** | SQLAlchemy async 엔진 및 세션 팩토리 |
| **산출물** | `src/api/db/base.py`, `src/api/db/session.py` |
| **검증** | DB 연결 테스트 |

#### T-I04: db/models/ ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Database |
| **의존성** | ← T-I03 |
| **설명** | User, Document, Company SQLAlchemy 모델 |
| **산출물** | `src/api/db/models/` (3개 파일) |
| **검증** | 모델 정의 및 관계 테스트 |

#### T-I05: Alembic 설정 ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | B: Database |
| **의존성** | ← T-I04 |
| **설명** | Alembic 마이그레이션 초기화 |
| **산출물** | `alembic.ini`, `alembic/` |
| **검증** | 마이그레이션 실행 테스트 |

#### T-I06: health.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Routes |
| **의존성** | ← T-I01 |
| **설명** | 헬스체크 엔드포인트 (/health, /ready) |
| **산출물** | `src/api/routes/health.py` |
| **검증** | 200 OK 응답 확인 |

### 7.5 스프린트 S10: Auth + Celery (5일) ✅

#### T-I07: security/auth.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Security |
| **의존성** | ← T-I02 |
| **설명** | JWT 토큰 생성/검증 (RS256) |
| **산출물** | `src/api/security/auth.py` |
| **검증** | 토큰 발급/검증 테스트 |

#### T-I08: security/api_keys.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Security |
| **의존성** | ← T-I04 |
| **설명** | API 키 관리 (SHA-256 해시 저장) |
| **산출물** | `src/api/security/api_keys.py` |
| **검증** | API 키 생성/검증 테스트 |

#### T-I09: security/rbac.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | D: Security |
| **의존성** | ← T-I07 |
| **설명** | 역할 기반 접근제어 (ADMIN, MANAGER, USER) |
| **산출물** | `src/api/security/rbac.py` |
| **검증** | 권한 체크 테스트 |

#### T-I10: dependencies.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Routes |
| **의존성** | ← T-I07, T-I08 |
| **설명** | FastAPI DI (get_current_user, get_db) |
| **산출물** | `src/api/dependencies.py` |
| **검증** | 의존성 주입 테스트 |

#### T-I11: tasks/celery_app.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Celery |
| **의존성** | ← T-I02 |
| **설명** | Celery 앱 설정 (Redis 브로커, 결과 백엔드) |
| **산출물** | `src/api/tasks/celery_app.py` |
| **소스** | `.claude/skills/celery-task/SKILL.md` 패턴 참조 |
| **검증** | Celery worker 시작 테스트 |

#### T-I12: tasks/generate_im.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Celery |
| **의존성** | ← T-I11 |
| **설명** | generate_im_task (chord 패턴) |
| **산출물** | `src/api/tasks/generate_im.py` |
| **검증** | 작업 실행 및 진행률 업데이트 테스트 |

#### T-I13: tasks/fetch_company.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Celery |
| **의존성** | ← T-I11, T-D06 |
| **설명** | fetch_company_data_task (DART API 연동) |
| **산출물** | `src/api/tasks/fetch_company.py` |
| **검증** | DART 데이터 조회 작업 테스트 |

#### T-I14: tasks/narrative.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | E: Celery |
| **의존성** | ← T-I11, T-N13 |
| **설명** | generate_narrative_task (LLM 연동) |
| **산출물** | `src/api/tasks/narrative.py` |
| **검증** | 내러티브 생성 작업 테스트 |

### 7.6 스프린트 S11: Routes + Deployment (5일) ✅

#### T-I15: schemas/ ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Routes |
| **의존성** | ← 없음 |
| **설명** | Pydantic v2 스키마 (documents, companies, im_data) |
| **산출물** | `src/api/schemas/` (4개 파일) |
| **검증** | 스키마 검증 테스트 |

#### T-I16: routes/documents.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Routes |
| **의존성** | ← T-I10, T-I12, T-I15 |
| **설명** | Document CRUD 엔드포인트 |
| **산출물** | `src/api/routes/documents.py` |
| **검증** | API 테스트 (POST, GET, GET/download) |

#### T-I17: routes/companies.py ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | C: Routes |
| **의존성** | ← T-I10, T-I13, T-I15 |
| **설명** | Company 엔드포인트 |
| **산출물** | `src/api/routes/companies.py` |
| **검증** | API 테스트 (POST, GET) |

#### T-I18: services/ ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | F: Services |
| **의존성** | ← T-I16, T-I17 |
| **설명** | document_service, company_service, webhook_service |
| **산출물** | `src/api/services/` (3개 파일) |
| **검증** | 서비스 로직 단위 테스트 |

#### T-I19: 파이프라인 통합 ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | F: Services |
| **의존성** | ← 모든 이전 티켓 |
| **설명** | 전체 모듈 통합 (data_ingestor → financial_engine → narrative → chart → brand → design_renderer) |
| **산출물** | 통합된 generate_im_task |
| **검증** | E2E 파이프라인 테스트 |

#### T-I20: middleware/ ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Middleware |
| **의존성** | ← T-I01 |
| **설명** | rate_limit, cors, logging 미들웨어 |
| **산출물** | `src/api/middleware/` (3개 파일) |
| **검증** | Rate limit 동작 테스트 |

#### T-I21: Dockerfile ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | H: Deployment |
| **의존성** | ← 없음 |
| **설명** | Multi-stage Dockerfile (builder → runtime) |
| **산출물** | `Dockerfile` |
| **검증** | 이미지 빌드 성공 |

#### T-I22: docker-compose.yml ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | H: Deployment |
| **의존성** | ← T-I21 |
| **설명** | 로컬 개발용 docker-compose (API, Celery, Redis, Postgres) |
| **산출물** | `docker-compose.yml` |
| **검증** | `docker-compose up` 성공 |

#### T-I23: E2E 테스트 ✅

| 항목 | 내용 |
|------|------|
| **워크스트림** | G: Testing |
| **의존성** | ← T-I19 |
| **설명** | E2E 통합 테스트 (API → Celery → PPTX/PDF) |
| **산출물** | `tests/test_api/test_e2e.py` |
| **검증** | 문서 생성 전체 흐름 검증 |

---

## 8. 통합 의존성 그래프

```
                     ┌─────────────────────┐
                     │  ✅ Phase 2         │
                     │  Data Collection    │
                     │     (S1-S2)         │
                     └──────────┬──────────┘
                                │
                     ┌──────────▼──────────┐
                     │  ✅ Phase 3         │
                     │  Financial Engine   │
                     │       (S3)          │
                     └──────────┬──────────┘
                                │
                     ┌──────────▼──────────┐
                     │  ✅ Phase 5         │
                     │    AI/Narrative     │
                     │     (S4-S6)         │
                     └──────────┬──────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
    ┌─────────▼─────────┐      │      ┌─────────▼─────────┐
    │ ✅ Chart Engine   │      │      │ ✅ Brand Extractor │
    │       (S7)        │      │      │       (S8)        │
    └─────────┬─────────┘      │      └─────────┬─────────┘
              │                 │                │
              └─────────────────┼────────────────┘
                                │
                     ┌──────────▼──────────┐
                     │  ✅ Phase 6         │
                     │    Integration      │
                     │     (S9-S11)        │
                     └──────────┬──────────┘
                                │
                     ┌──────────▼──────────┐
                     │  ✅ Production      │
                     │     Deployment      │
                     └─────────────────────┘
```

---

## 9. 검증 계획

### 9.1 단위 테스트

| 모듈 | 테스트 파일 | 주요 검증 항목 |
|------|------------|---------------|
| data_ingestor | `test_data_ingestor/` | DART API 응답 파싱, rate limiting, 파서 |
| financial_engine | `test_financial_engine/` | 계정 매핑 정확도 (>90%), 지표 계산 |
| narrative_generator | `test_narrative_generator/` | 임베딩, RAG 검색, 프롬프트 렌더링 |
| chart_engine | `test_chart_engine/` | 6개 Plotly + 3개 Graphviz 차트 |
| brand_extractor | `test_brand_extractor/` | API 모킹, K-Means 컬러 추출 |
| api | `test_api/` | 엔드포인트, 인증, Celery 작업 |

### 9.2 통합 테스트

| 테스트 | 설명 |
|--------|------|
| `test_dart_to_im.py` | DART API → IMDocumentData |
| `test_financial_pipeline.py` | raw data → ProcessingResult |
| `test_narrative_to_render.py` | Narrative → Section Renderer |
| `test_full_pipeline.py` | E2E (API → Celery → PPTX/PDF) |

### 9.3 성능 벤치마크

| 항목 | 목표 |
|------|------|
| DART API 호출 | rate limit (100/min) 내 |
| LLM 토큰 예산 | 섹션당 2,000 토큰 이하 |
| PPTX/PDF 생성 | < 30초 (18개 섹션 기준) |

---

## 10. 핵심 파일 참조

| 파일 | 용도 |
|------|------|
| `src/design_renderer/im_document.py` | IMDocumentData 스키마 (모든 모듈의 데이터 계약) |
| `src/design_renderer/pipeline.py` | IMPipeline.generate() (Celery 작업에서 호출) |
| `src/design_renderer/design_tokens.py` | IMDesignTokens.from_brand_assets() 팩토리 |
| `src/design_renderer/components/chart_embed.py` | 기존 차트 구현 (확장 기반) |
| `.claude/skills/rate-limiter/SKILL.md` | Token Bucket 패턴 |
| `.claude/skills/celery-task/SKILL.md` | Celery 작업 패턴 |
| `.claude/skills/api-endpoint-builder/SKILL.md` | FastAPI 컨벤션 |

---

## 11. 위험 완화

| 위험 | 영향 | 완화 방안 |
|------|------|----------|
| DART API rate limit 초과 | 데이터 수집 실패 | Token bucket + Circuit breaker |
| LLM 환각 (hallucination) | 잘못된 내러티브 | Fact checker 검증 레이어 |
| 한글 폰트 렌더링 | 차트 깨짐 | 폰트 폴백 체인 + 테스트 |
| Brandfetch API 제한 | 브랜드 추출 실패 | 웹사이트 추출 폴백 |
| 토큰 예산 초과 | 내러티브 잘림 | 섹션별 예산 모니터링 |
| Playwright 브라우저 설치 | 크롤러 실패 | Docker 이미지에 사전 설치 |

---

## 12. 일정 요약

| 스프린트 | 기간 | 주요 산출물 | 티켓 수 | 파일 수 | 테스트 수 | 상태 |
|---------|------|------------|--------|--------|----------|------|
| S1 | Week 1 | Data Collection Foundation | 5 | - | 96 | ✅ 완료 |
| S2 | Week 2 | DART Client + Parsers + Aggregator | 11 | ~17 | 127 | ✅ 완료 |
| S3 | Week 3 | Financial Engine 전체 | 14 | ~18 | 187 | ✅ 완료 |
| S4 | Week 4 | RAG Infrastructure | 6 | - | - | ✅ 완료 |
| S5 | Week 5 | 18개 섹션 프롬프트 | 6 | - | - | ✅ 완료 |
| S6 | Week 6 | LLM Engine + Fact Checker | 7 | ~29 | 43 | ✅ 완료 |
| S7 | Week 7 | Chart Engine 확장 | 9 | ~18 | 61 | ✅ 완료 |
| S8 | Week 8 | Brand Extractor | 10 | ~16 | 66 | ✅ 완료 |
| S9 | Week 9 | API Foundation + DB | 6 | - | 61 | ✅ 완료 |
| S10 | Week 10 | Auth + Celery | 8 | - | 83 | ✅ 완료 |
| S11 | Week 11 | Routes + Deployment | 9 | ~40 | 63 | ✅ 완료 |
| **Total** | **11주** | **189+ source files, 88 test files** | **~95** | **~103** | **902 (전체 통과)** | **~97% 완료** |

---

## 13. 의존성 추가

다음 패키지를 `requirements.txt`에 추가:

```
# Phase 2: Data Ingestor
aiofiles==24.1.0          # Async file I/O
respx==0.21.0             # httpx mocking for tests
pytest-httpx==0.30.0      # httpx pytest plugin

# Phase 5: Narrative Generator
tiktoken>=0.7.0           # Token counting
sentence-transformers>=2.2.0  # Optional: local embeddings

# Phase 6: Integration
slowapi>=0.1.9            # Rate limiting for FastAPI
```

---

**전체 완료: 189+ source files, 88 test files, 902 tests (전체 통과), ~97% 완료**
