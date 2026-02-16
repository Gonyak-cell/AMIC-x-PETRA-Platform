# IM Auto-Generator - 통합 개발 계획 (PLAN.md)

> 마지막 업데이트: 2026-02-11 21:44:06 (Multi-Model Routing 추가 — OpenAI + Anthropic Claude + Google Gemini 섹션별 라우팅)
> 통합 대상: PLAN.md, design-renderer-integration-plan.md, design-renderer-parallel-plan.md, remaining-phases-implementation-plan.md

---

## 프로젝트 개요

AI 기반 Information Memorandum(투자설명서) 자동 생성 시스템. Sample IM(TITAN/COVENANT) 양식 + AMIC 디자인 + Deal Radar 인프라를 결합하여 50~80페이지 IM을 PPTX/PDF로 자동 생성한다.

### 전체 아키텍처

```
auto-im-generator/
├── src/
│   ├── data_ingestor/       # Phase 2: 데이터 수집 (DART, 크롤링, 파싱)
│   ├── financial_engine/    # Phase 3: 재무 분석 엔진
│   ├── design_renderer/     # Phase 4: 시각화/디자인 (PPTX/PDF 듀얼 출력)
│   ├── narrative_generator/ # Phase 5: AI/내러티브 생성
│   ├── chart_engine/        # 차트 엔진 (Plotly/Graphviz 확장)
│   ├── brand_extractor/     # 브랜드 자산 추출 (로고/컬러)
│   └── api/                 # Phase 6: FastAPI + Celery 통합/배포
├── tests/
├── docs/plans/              # 세부 계획 문서
└── templates/
```

### 핵심 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 페이지 크기 | Landscape Letter (10.83"×7.5") | TITAN/COVENANT SL Template 동일 |
| 출력 형식 | PPTX (1차) + PDF (2차) | 실무 편집→공유 워크플로우 |
| PDF 생성 | HTML→PDF (Playwright/WeasyPrint) | Radar 검증 파이프라인 재사용 |
| 폰트 | AMIC (Inter/Pretendard/IBM Plex Mono/Noto Sans KR) | 일관된 브랜드 |
| 컬러 | AMIC (다크그린 #0F3A32 / 그린 #26C260) | SL→AMIC 교체 |
| 섹션 구성 | 동적 (TITAN 5섹션/COVENANT 6섹션/SPEC 14섹션 전체) | 유연 대응 |
| 차트 | Plotly→PNG 300DPI→삽입 | 시각적 일관성 |
| 보안 | PDF 암호화 + 워터마크 + PPTX 편집 제한 | 극비 재무 데이터 보호 |

---

## 전체 진행 현황 요약

| Phase | 모듈 | 스프린트 | 상태 | 완료율 |
|-------|------|---------|------|--------|
| Phase 1 | 환경 구축 | — | ✅ 부분 완료 | 60% |
| Phase 2 | Data Collection (`data_ingestor`) | S1-S3 | ✅ v0.2.1 완료 | 100% |
| Phase 3 | Financial Engine (`financial_engine`) | S3 | ✅ v0.3.0 완료 | 100% |
| Phase 4 | Design Renderer (`design_renderer`) | Sprint 1-5 | ✅ v0.4.0 완료 | 100% |
| Phase 5 | AI/Narrative (`narrative_generator`) | S4-S6 | ✅ v0.5.0 완료 | 100% |
| — | Chart Engine (`chart_engine`) | S7 | ✅ v0.7.0 완료 | 100% |
| — | Brand Extractor (`brand_extractor`) | S8 | ✅ v0.8.0 완료 | 100% |
| Phase 6 | Integration (`api`) | S9-S11+ | ✅ v1.0.0 완료 | 100% |
| Phase A1 | Industry Module (`industry`) | — | ✅ v0.1.0 완료 | 100% |
| Phase B | Industry Financial Metrics (`financial_engine/calculator`) | B1-B4 | ✅ v0.4.0 완료 | 100% |

**전체 프로젝트 진행률: ~99%** (~155/155 백엔드 티켓 완료 — 프론트엔드만 미구현)

---

## Phase 1: 환경 구축

- [x] 프로젝트 폴더 구조 생성 (setup_project.py 실행)
- [ ] Python 가상환경 생성 및 활성화
- [x] requirements.txt 패키지 설치
- [ ] .env 파일 생성 (API 키 설정)
- [ ] Git 초기화 및 첫 커밋
- [x] Claude Code CLI 설치 및 연결
- [x] 스킬/에이전트/훅 파일 동작 확인

---

## Phase 2: 데이터 수집 (`src/data_ingestor/`) — ✅ v0.2.1 완료

> 세부 계획: `docs/plans/remaining-phases-implementation-plan.md` Section 2

### 모듈 구조

```
src/data_ingestor/
├── __init__.py              # Public API
├── exceptions.py            # DartAPIError, ParserError, CrawlerError
├── dart/
│   ├── client.py           # DartAPIClient (httpx async)
│   ├── models.py           # DartCompanyInfo, DartFinancialStatement (Pydantic)
│   ├── endpoints.py        # DART API 엔드포인트 정의
│   └── rate_limiter.py     # Token bucket (분당 1000회) + Circuit Breaker
├── parsers/
│   ├── pdf_parser.py       # PyMuPDF 기반 PDF 추출
│   └── excel_parser.py     # openpyxl 기반 Excel 파싱
├── crawler/
│   ├── playwright_engine.py # JS 렌더링 크롤러
│   ├── news_crawler.py     # Naver/Google 뉴스
│   └── company_crawler.py  # 회사 웹사이트 IR 문서
└── aggregator.py           # DataAggregator → IMDocumentData (Builder 패턴)
```

### Sprint 1: Foundation ✅ (2026-02-08)

| 티켓 | 내용 | 산출물 |
|------|------|--------|
| T-D01 | 커스텀 예외 계층 | `exceptions.py` — DataIngestorError, DartAPIError, ParserError, CrawlerError |
| T-D02 | Token Bucket Rate Limiter | `dart/rate_limiter.py` — 분당 1000회 제한, Circuit Breaker 통합 |
| T-D03 | Pydantic 모델 | `dart/models.py` — DartCompanyInfo, DartFinancialStatement 등 |
| T-D04 | DART API 엔드포인트 상수 | `dart/endpoints.py` — URL, 상태 코드, 기본값 |
| T-D05 | 테스트 96개 | `tests/test_data_ingestor/` — 5개 파일 |

### Sprint 2: Core Clients ✅ (2026-02-09)

| 티켓 | 내용 | 산출물 |
|------|------|--------|
| T-D06 | DartAPIClient 기본 구조 | `dart/client.py` — async context manager, rate limiting, circuit breaker |
| T-D07 | get_company_info() | 기업 개요 조회 API |
| T-D08 | get_financial_statements() | 재무제표 조회 API |
| T-D09 | get_major_shareholders() | 주요주주 조회 API |
| T-D10 | PDF 파서 | `parsers/pdf_parser.py` — PyMuPDF 기반 |
| T-D11 | Excel 파서 | `parsers/excel_parser.py` — openpyxl 기반 |
| T-D12 | Playwright 엔진 | `crawler/playwright_engine.py` — JS 렌더링 |
| T-D13 | 뉴스 크롤러 | `crawler/news_crawler.py` — Naver/Google 뉴스 |
| T-D14 | 기업 크롤러 | `crawler/company_crawler.py` — IR 문서 수집 |
| T-D15 | Aggregator | `aggregator.py` — Builder 패턴 데이터 통합 |
| T-D16 | 테스트 +65개 (총 161개) | 4개 테스트 파일 추가 |

**테스트 현황**: 223 tests passed

### Sprint 3: Integration & Pipeline ✅ (2026-02-09)

- [x] E2E 데이터 수집 파이프라인 (`pipeline.py`)
- [x] 캐싱 레이어 (`cache.py` — CacheManager, CachedDartClient, Redis/메모리 폴백)
- [x] 에러 복구 전략 (DataPriority REQUIRED/IMPORTANT/OPTIONAL, _safe_step)
- [x] 예외 추가 (CacheError, PipelineError)
- [x] 테스트 +62개 (test_cache.py, test_pipeline.py)

**총 테스트 현황**: 223 tests (11개 테스트 파일), 17개 소스 파일, v0.2.1

---

## Phase 3: 재무 분석 엔진 (`src/financial_engine/`) — ✅ v0.3.0 완료

> 세부 계획: `docs/plans/remaining-phases-implementation-plan.md` Section 3

### 모듈 구조 (18개 파일)

```
src/financial_engine/
├── __init__.py              # 공개 API (전체 exports)
├── exceptions.py            # 13개 예외 클래스
├── processor.py             # FinancialProcessor 오케스트레이션
├── mapper/
│   ├── account_mapper.py   # rapidfuzz 퍼지 매칭 (정확도 90%+)
│   ├── chart_of_accounts.py # StandardAccount enum (85개, 메타데이터)
│   └── korean_accounts.py  # KOREAN_ACCOUNT_MAP (376개 한글 매핑)
├── normalizer/
│   ├── unit_normalizer.py  # 천원/백만원/억원 → 원
│   └── currency_converter.py # USD/EUR → KRW
├── calculator/
│   ├── profitability.py    # GPM, OPM, NPM, ROA, ROE
│   ├── growth.py           # YoY, CAGR
│   ├── cash_flow.py        # EBITDA, FCF, NWC
│   └── leverage.py         # D/E, ICR
└── validator/
    ├── balance_checker.py  # A = L + E 검증
    └── consistency_checker.py # 다기간 일관성
```

### 스프린트 S3 (14개 티켓) ✅ 전체 완료

- [x] T-F01: chart_of_accounts.py — StandardAccount enum 85개 + 메타데이터
- [x] T-F02: korean_accounts.py — KOREAN_ACCOUNT_MAP 376개 한글 매핑
- [x] T-F03: account_mapper.py — rapidfuzz 퍼지 매칭 (선택적 의존성)
- [x] T-F04: unit_normalizer.py — 단위 정규화 (천원/백만원/억원 → 원)
- [x] T-F05: currency_converter.py — 통화 변환 (USD/EUR → KRW)
- [x] T-F06: profitability.py — 수익성 지표 (GPM, OPM, NPM, ROA, ROE)
- [x] T-F07: growth.py — 성장 지표 (YoY, 3Y/5Y CAGR)
- [x] T-F08: cash_flow.py — 현금흐름 (EBITDA, FCF, NWC)
- [x] T-F09: leverage.py — 레버리지 (D/E, ICR)
- [x] T-F10: balance_checker.py — 재무상태표 균형 검증
- [x] T-F11: consistency_checker.py — 다기간 일관성 검증
- [x] T-F12: processor.py — FinancialProcessor 파이프라인
- [x] T-F13: 테스트 195개 (12개 파일)
- [x] T-F14: E2E — DART → Financial → IMDocumentData

**테스트 현황**: 195 tests, 12 파일 (모두 통과)

**주요 구현 사항**:
- Decimal 내부 계산, float 변환은 to_financial_statements()에서만
- rapidfuzz는 선택적 의존성 (없으면 fuzzy 단계 스킵)
- korean_accounts.py enum 이름 수정 완료 (COGS→COST_OF_GOODS_SOLD 등 8건)

---

## Phase 4: 시각화/디자인 (`src/design_renderer/`) — ✅ v0.4.0 완료

> 세부 설계: `docs/plans/design-renderer-integration-plan.md`
> 병렬 실행: `docs/plans/design-renderer-parallel-plan.md` (7 워크스트림 × 5 스프린트, 47개 티켓)

### 모듈 구조 (51개 파일)

```
src/design_renderer/
├── __init__.py, design_tokens.py, im_document.py, image_processor.py
├── assets.py, templates.py, pdf_engine.py, pipeline.py, security.py
├── assets/fonts/ (10개), assets/images/ (3개), assets/templates/ (1개)
├── components/ (10개: financial_table, chart_embed, number_formatter,
│                source_citation, timeline, kpi_card, sub_header_bar,
│                org_chart, content_overflow, page_elements)
├── pptx_engine/ (5개: template_manager, slide_factory, shape_builder,
│                 toc_builder, style_applier, create_template)
├── pdf_output/ (css_generator, html_builder)
└── section_renderers/ (19개: base + 18섹션)
    cover, disclaimer, toc_divider, contact,
    deal_overview, executive_summary, company_overview, business_overview,
    investment_highlights, market_overview, value_creation, growth_strategy,
    financial_analysis, transaction_structure, shareholder_structure,
    management_team, business_model, appendix
```

### Sprint 1: Foundation ✅ (2026-02-08)

- [x] T-INF-1: 의존성 추가 + 프로젝트 구조 업데이트
- [x] T-A1: 폰트 파일 복사 (Radar → assets/fonts/, 10개)
- [x] T-A4: image_processor.py 이식 (embed_local_image 추가)
- [x] T-B1: design_tokens.py (IMDesignTokens, 5개 sub-dataclass, from_brand_assets)
- [x] T-B2: IMDocumentData (14개 sub-dataclass, TITAN/COVENANT/FULL 프리셋)

### Sprint 2: Core Systems ✅ (2026-02-08)

- [x] T-A2: assets.py (폰트 CSS/WOFF2 압축)
- [x] T-A3: PPTX 마스터 템플릿 (amic_im_template.pptx, 3종 레이아웃)
- [x] T-B3: number_formatter.py (5개 공개 API, ▲/▼ 성장지표)
- [x] T-B4: source_citation.py (중복 출처 동일 번호, PPTX/HTML 렌더링)
- [x] T-B5: 파생 지표 + 교차검증 (compute_derived_metrics 9개 지표)
- [x] T-D2: css_generator.py (12개 서브함수, 토큰 기반 동적 CSS)
- [x] T-D4: templates.py (Jinja2 환경, 글로벌 변수 8개, 필터 5개)
- [x] T-E2: chart_embed.py (6종 금융 차트, AMIC 컬러 시퀀스)
- [x] T-E4: sub_header_bar.py (PPTX + HTML 듀얼)
- [x] T-E5: timeline.py (수평/수직 타임라인, PNG/SVG)
- [x] T-E6: org_chart.py (Graphviz, SVG + HTML fallback)
- [x] T-E7: content_overflow.py (7pt 하한, 테이블 헤더 반복 분할)

### Sprint 3: Engines ✅ (2026-02-08)

- [x] T-C1~C5: PPTX 엔진 5개 모듈 (template_manager, slide_factory, shape_builder, style_applier, toc_builder)
- [x] T-D1: pdf_engine.py (Playwright/WeasyPrint 이중엔진)
- [x] T-D3: html_builder.py (@font-face 자동, 페이지 번호 주입)
- [x] T-E1: financial_table.py (PPTX Table + HTML, CAGR 조건부 색상)
- [x] T-E3: kpi_card.py (4종 포맷, ▲/▼ 변동 지표)
- [x] T-E8: page_elements.py (7개 API, source_citation 연동)

### Sprint 4: Section Renderers ✅ (2026-02-08)

- [x] F-α Core: cover, disclaimer, toc_divider, contact (4종)
- [x] F-β Deal/Company: deal_overview, executive_summary, company_overview, business_overview (4종)
- [x] F-γ Strategy: investment_highlights, market_overview, value_creation, growth_strategy (4종)
- [x] F-δ Financial: financial_analysis, transaction_structure, shareholder_structure (3종)
- [x] F-ε Supporting: management_team, business_model, appendix (3종)

### Sprint 5: Integration + Security ✅ (2026-02-08)

- [x] T-G1: E2E 파이프라인 (IMPipeline, PipelineResult)
- [x] T-G2: PDF 보안 (pikepdf AES-256, PyPDF2 폴백, CSS 워터마크)
- [x] T-G3: PPTX 보안 (add_watermark + SHA-512 set_edit_restriction)
- [x] T-G4: 통합 테스트 스위트 (12개 파일, Tier 1/2/3 분류)

### Phase 4 잔여 작업

- [x] Plotly 차트 엔진 확장 → chart_engine v0.7.0 완료 (S7)
- [x] 브랜드 자산 추출 → brand_extractor v0.8.0 완료 (S8)

---

## Phase 5: AI/내러티브 (`src/narrative_generator/`) — ✅ v0.5.0 완료

> 세부 계획: `docs/plans/remaining-phases-implementation-plan.md` Section 4

### 모듈 구조

```
src/narrative_generator/
├── config.py               # OpenAI, Anthropic, Google, Pinecone, Routing 설정
├── rag/                    # RAG 파이프라인
│   ├── embedder.py        # OpenAI text-embedding-3-small
│   ├── vector_store.py    # Pinecone 클라이언트
│   ├── retriever.py       # 컨텍스트 검색 + 리랭킹
│   └── chunker.py         # 문서 청킹
├── prompts/               # 프롬프트 레지스트리
│   ├── base.py            # BasePrompt 추상 클래스
│   ├── section_prompts/   # 18개 섹션별 프롬프트
│   └── industry_variants/ # tech, healthcare, manufacturing, financial_services
├── engine/
│   ├── orchestrator.py    # NarrativeOrchestrator (Multi-Model Routing)
│   ├── llm_provider.py    # LLMProvider Protocol + LLMResponse + ProviderName
│   ├── model_router.py    # ModelRouter (섹션→프로바이더 매핑 + Fallback)
│   ├── router_factory.py  # create_model_router() 팩토리
│   ├── providers/         # LLM 프로바이더 구현체
│   │   ├── openai_provider.py     # GPT-4o (수치/재무 섹션)
│   │   ├── anthropic_provider.py  # Claude (전략 서술 섹션)
│   │   └── google_provider.py     # Gemini (사실 개요/보조 섹션)
│   ├── token_budget.py    # tiktoken 토큰 예산 관리
│   └── structured_output.py
├── fact_checker/
│   ├── validator.py       # 수치 클레임 검증
│   ├── consistency.py     # 내러티브 간 일관성
│   └── confidence.py      # 신뢰도 점수
└── korean_finance/
    ├── terminology.py     # 한국 금융 용어 영↔한
    └── tone_adapter.py    # "Factual optimism" 톤
```

### Multi-Model Routing (2026-02-11 추가)

섹션별 최적 LLM 프로바이더를 배정하는 라우팅 시스템:

| 섹션 카테고리 | 프로바이더 | 근거 |
| --- | --- | --- |
| 수치/재무 (financial_analysis, transaction/shareholder_structure) | OpenAI GPT-4o | 수치 정확도, 정형 출력 |
| 전략 서술 (executive_summary, investment_highlights, value/growth) | Anthropic Claude | 장문 일관성, 뉘앙스 |
| 사실 개요 (company/business/deal/market_overview) | Google Gemini | 정보 합성, 비용 효율 |
| 보조 (management_team, business_model, appendix, contact) | Google Gemini | 비용 효율 |

- Fallback: OpenAI → Anthropic → Google (키 누락 시 자동 전환)
- 하위 호환: OpenAI만 설정 시 기존 단일 클라이언트 경로 유지
- 환경변수 `LLM_ROUTING_MAP` (JSON)으로 커스텀 라우팅 가능

### 스프린트 S4: RAG Infrastructure (6개 티켓) ✅

- [x] T-N01: config.py (Pydantic Settings)
- [x] T-N02: embedder.py (OpenAI text-embedding-3-small)
- [x] T-N03: vector_store.py (Pinecone)
- [x] T-N04: chunker.py (토큰 기반 오버랩 청킹)
- [x] T-N05: retriever.py (산업별 필터링 + MMR 리랭킹)
- [x] T-N06: korean_finance/terminology.py (80+ 용어) + tone_adapter.py

### 스프린트 S5: Prompts (6개 티켓) ✅

- [x] T-N07: base.py (BasePrompt + PromptRegistry)
- [x] T-N08: Core 프롬프트 4개 (executive_summary, company_overview, business_overview, deal_overview)
- [x] T-N09: Financial 프롬프트 3개 (financial_analysis, transaction_structure, shareholder_structure)
- [x] T-N10: Strategy 프롬프트 4개 (investment_highlights, market_overview, value_creation, growth_strategy)
- [x] T-N11: Supporting 프롬프트 4개 (management_team, business_model, appendix, contact)
- [x] T-N12: Industry variants 4개 (tech, healthcare, manufacturing, financial_services)

### 스프린트 S6: Engine + Fact Checker (7개 티켓) ✅

- [x] T-N13: orchestrator.py (NarrativeOrchestrator — 8단계 파이프라인)
- [x] T-N14: token_budget.py (섹션별 토큰 예산, tiktoken)
- [x] T-N15: structured_output.py (LLM→구조화 파싱, 수치 클레임 추출)
- [x] T-N16: validator.py (수치 클레임 추출/검증, ±1% 허용)
- [x] T-N17: consistency.py (내러티브 간 일관성, ±2% 허용)
- [x] T-N18: confidence.py (신뢰도 점수 0-1, 가중 평균)
- [x] T-N19: 테스트 43개 (목표 25+ 초과 달성)

---

## Chart Engine (`src/chart_engine/`) — ✅ v0.7.0 완료

> design_renderer의 chart_embed.py를 독립 모듈로 확장

### 모듈 구조

```
src/chart_engine/
├── __init__.py, config.py, exceptions.py
├── plotly/                # 6종 차트 + 디스패처
│   ├── charts.py         # waterfall, combo, stacked_bar, donut, line, hbar
│   └── themes.py         # AMICThemeFactory
├── graphviz/              # 3종 다이어그램
│   ├── org_chart.py      # 조직도
│   ├── flow_diagram.py   # 거래 구조도
│   └── shareholding.py   # 주주 구조도
├── export/
│   ├── png_exporter.py   # Kaleido 300 DPI
│   └── svg_exporter.py   # XML 선언 제거
└── data_transformer.py    # IMDocumentData → ChartSpec 자동 변환
```

### 스프린트 S7 (9개 티켓) ✅ 전체 완료

- [x] T-C01: 모듈 구조 리팩토링 (chart_embed.py → plotly/ 분리)
- [x] T-C02: themes.py (AMIC 테마 팩토리)
- [x] T-C03: graphviz/org_chart.py (조직도 확장)
- [x] T-C04: graphviz/flow_diagram.py (거래 구조 다이어그램)
- [x] T-C05: graphviz/shareholding.py (주주 구조)
- [x] T-C06: data_transformer.py (IMDocumentData → ChartData)
- [x] T-C07: export/png_exporter.py (300 DPI)
- [x] T-C08: export/svg_exporter.py (PDF용)
- [x] T-C09: 테스트 61개 (8개 파일, 목표 15+ 초과 달성)

**테스트 현황**: 61 tests, 8개 파일 (모두 통과)

**주요 구현 사항**:
- Plotly 6종 차트 + AMICThemeFactory (AMIC 컬러 시퀀스)
- Graphviz 3종: org_chart, flow_diagram, shareholding
- DataTransformer: 재무/시장/주주 데이터 → ChartSpec 자동 변환
- PNG (Kaleido 300 DPI) + SVG 내보내기
- design_renderer 하위 호환: chart_embed.py · org_chart.py thin adapter 유지

---

## Brand Extractor (`src/brand_extractor/`) — ✅ v0.8.0 완료

### 모듈 구조 (16개 파일)

```
src/brand_extractor/
├── __init__.py          # extract_brand() 공개 API + 3단계 우선순위 체인
├── config.py            # BrandExtractorConfig (Pydantic Settings)
├── exceptions.py        # BrandExtractorError 외 5개 예외
├── models.py            # BrandAssets, LogoCandidate, ExtractedColor
├── extractors/
│   ├── brandfetch.py   # Brandfetch API 클라이언트
│   ├── website.py      # Playwright 웹사이트 크롤링 추출
│   └── fallback.py     # AMIC 기본값 폴백
├── logo/
│   ├── detector.py     # HTML 로고 URL 탐지 (og:image, favicon)
│   ├── scorer.py       # 이미지 품질 점수
│   └── processor.py    # 리사이즈/포맷 변환
└── color/
    ├── extractor.py    # K-Means 색상 클러스터링
    ├── classifier.py   # Primary/Secondary 분류
    └── token_mapper.py # → IMDesignTokens.from_brand_assets()
```

### 스프린트 S8 (10개 티켓) ✅ 전체 완료

- [x] T-B01: models.py (BrandAssets dataclass)
- [x] T-B02: brandfetch.py (Brandfetch API 클라이언트)
- [x] T-B03: logo/detector.py (HTML 로고 URL 탐지)
- [x] T-B04: logo/scorer.py (이미지 품질 점수)
- [x] T-B05: color/extractor.py (K-Means 색상 추출)
- [x] T-B06: color/classifier.py (Primary/Secondary 분류)
- [x] T-B07: color/token_mapper.py (→ IMDesignTokens)
- [x] T-B08: website.py (Playwright 통합 추출)
- [x] T-B09: fallback.py (AMIC 기본값)
- [x] T-B10: 테스트 66개 (12개 파일, 목표 12+ 초과 달성)

**테스트 현황**: 66 tests, 12개 파일 (모두 통과)

**주요 구현 사항**:
- 3단계 우선순위 체인: Brandfetch API → Website crawl → AMIC fallback
- LogoDetector + LogoScorer + LogoProcessor 파이프라인
- K-Means 색상 클러스터링 + Primary/Secondary 자동 분류
- BrandTokenMapper → IMDesignTokens 연동

---

## Phase 6: 통합/배포 (`src/api/`) — ✅ v1.0.0 완료

### 모듈 구조 (40개 파일)

```
src/api/
├── __init__.py            # create_app() 팩토리 + 미들웨어/라우터 등록
├── main.py                # FastAPI 앱 진입점 (uvicorn)
├── config.py              # APIConfig (Pydantic Settings)
├── dependencies.py        # DI (get_current_user, get_current_active_user, get_async_session)
├── exceptions.py          # APIError, AuthenticationError 등
├── routes/
│   ├── health.py         # /health (liveness), /ready (readiness)
│   ├── documents.py      # /api/v1/documents (CRUD + download)
│   └── companies.py      # /api/v1/companies (fetch + cache)
├── schemas/
│   ├── common.py         # PaginationParams
│   ├── documents.py      # DocumentCreate, DocumentResponse, DocumentListResponse
│   └── companies.py      # CompanyRequest, CompanyResponse
├── services/
│   ├── document_service.py  # DB + Celery 오케스트레이션
│   ├── company_service.py   # 기업 데이터 CRUD
│   └── webhook_service.py   # 웹훅 관리
├── security/
│   ├── auth.py           # JWT RS256/HS256 듀얼 인증
│   ├── api_keys.py       # API 키 SHA-256 해싱
│   └── rbac.py           # UserRole enum (ADMIN/MANAGER/USER)
├── tasks/
│   ├── celery_app.py     # Celery 앱 팩토리 (Redis 브로커, JSON only)
│   ├── generate_im.py    # Chord 5단계 파이프라인 오케스트레이션
│   ├── fetch_company.py  # DART 데이터 수집 태스크
│   ├── narrative.py      # LLM 내러티브 생성 태스크
│   ├── progress.py       # ProgressTracker (Redis 기반)
│   └── serializers.py    # 커스텀 Celery 직렬화기
├── db/
│   ├── base.py           # SQLAlchemy declarative base
│   ├── session.py        # async engine + AsyncSession
│   └── models/
│       ├── user.py       # User 모델
│       ├── document.py   # Document 모델 (DocumentStatus enum)
│       ├── company.py    # Company 모델
│       └── api_key.py    # APIKey 모델
└── middleware/
    ├── cors.py           # CORS 설정
    ├── logging.py        # 요청/응답 로깅
    └── rate_limit.py     # SlowAPI Redis 기반 Rate Limiting
```

### API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | 서버 상태 (liveness probe) |
| GET | `/ready` | DB/Redis 연결 (readiness probe) |
| POST | `/api/v1/documents` | IM 문서 생성 (202 Accepted + Celery task) |
| GET | `/api/v1/documents/{id}` | 작업 상태/결과 조회 |
| GET | `/api/v1/documents/{id}/download` | PPTX/PDF 다운로드 |
| GET | `/api/v1/documents` | 문서 목록 (페이지네이션, RBAC) |
| POST | `/api/v1/companies` | DART에서 기업 데이터 수집 (202 Accepted) |
| GET | `/api/v1/companies/{corp_code}` | 캐시된 기업 정보 |

### Celery 파이프라인

```
POST /api/v1/documents → generate_im_task (chord)
  Stage 1: Data Collection (group)        → 25%
    ├─ fetch_dart_task
    ├─ fetch_web_task
    └─ extract_brand_task
  Stage 2: merge_collected_data            → 40%
  Stage 3: analyze_financials_task (chain) → 70%
  Stage 4: generate_content_task           → 95%
  Stage 5: render_document_task + finalize → 100%
```

### 스프린트 S9: Foundation (6개 티켓) ✅ 전체 완료

- [x] T-I01: main.py, __init__.py (FastAPI 앱 팩토리)
- [x] T-I02: config.py (Pydantic Settings)
- [x] T-I03: db/base.py, session.py (SQLAlchemy async)
- [x] T-I04: db/models/ (User, Document, Company, APIKey)
- [x] T-I05: alembic.ini 설정 (마이그레이션 파일은 미생성)
- [x] T-I06: health.py (/health, /ready)

**Sprint S9 테스트 현황**: 61 tests (모두 통과)

### 스프린트 S10: Auth + Celery (8개 티켓) ✅ 전체 완료

- [x] T-I07: security/auth.py (JWT RS256/HS256 듀얼)
- [x] T-I08: security/api_keys.py (SHA-256)
- [x] T-I09: security/rbac.py (ADMIN/MANAGER/USER)
- [x] T-I10: dependencies.py (get_current_user, get_current_active_user)
- [x] T-I11: tasks/celery_app.py (Redis 브로커, JSON only)
- [x] T-I12: tasks/generate_im.py (chord 5단계 파이프라인)
- [x] T-I13: tasks/fetch_company.py (DART 연동)
- [x] T-I14: tasks/narrative.py (LLM 연동)

**Sprint S10 테스트 현황**: 83 tests (모두 통과)

### 스프린트 S11: Routes + Deployment (9개 티켓) ✅ 전체 완료

- [x] T-I15: schemas/ (Pydantic v2)
- [x] T-I16: routes/documents.py (CRUD + download + 페이지네이션)
- [x] T-I17: routes/companies.py (fetch + cache)
- [x] T-I18: services/ (DocumentService, CompanyService, WebhookService)
- [x] T-I19: 전체 모듈 파이프라인 통합 (E2E 검증)
- [x] T-I20: middleware/ (CORS, Rate Limiting, Request Logging)
- [x] T-I21: Dockerfile (multi-stage: builder + runtime)
- [x] T-I22: docker-compose.yml (PostgreSQL, Redis, API, Celery Worker, Celery Beat)
- [x] T-I23: E2E 테스트 (18개 파일, 63개 테스트)

**Sprint S11 테스트 현황**: 63 tests (모두 통과)
**API 전체 테스트**: 256 tests (모두 통과)

### Sprint S11+: Auth/User/APIKey Routes + Alembic + CI/CD ✅ 전체 완료

- [x] `POST /api/v1/auth/login` (이메일/비밀번호 → JWT 발급)
- [x] `POST /api/v1/auth/refresh` (리프레시 토큰 → 새 JWT)
- [x] `POST /api/v1/auth/logout` (토큰 블랙리스트)
- [x] `POST /api/v1/users` (회원가입, Admin 전용)
- [x] `GET /api/v1/users/me` (현재 사용자 정보)
- [x] `PATCH /api/v1/users/me` (프로필 수정)
- [x] `GET /api/v1/users` (사용자 목록, Admin 전용)
- [x] `GET /api/v1/users/{user_id}` (사용자 조회, Admin 전용)
- [x] `PATCH /api/v1/users/{user_id}` (사용자 수정, Admin 전용)
- [x] `DELETE /api/v1/users/{user_id}` (사용자 삭제, Admin 전용)
- [x] `POST /api/v1/api-keys` (API 키 발급)
- [x] `GET /api/v1/api-keys` (사용자의 API 키 목록)
- [x] `DELETE /api/v1/api-keys/{key_id}` (API 키 폐기)
- [x] Alembic 마이그레이션 (`alembic/` 디렉토리, env.py, 001_initial_schema.py — 4개 테이블)
- [x] CI/CD 파이프라인 (`.github/workflows/ci.yml` + `cd.yml`)

**Sprint S11+ 테스트 현황**: 49 tests 추가 (모두 통과)

---

## Phase A1: Industry Module (`src/industry/`) — ✅ v0.1.0 완료

> 세부 계획: `docs/plans/multi-industry-expansion-plan.md` Section 3

### 모듈 구조 (5개 파일)

```
src/industry/
├── __init__.py          # 패키지 초기화 + exports (v0.2.0)
├── base.py              # IndustryModule ABC (4 abstract + 2 concrete methods)
├── models.py            # IndustryKPI, IndustryChartRecommendation, RiskCategory, IndustryContext, KPIUnit
├── registry.py          # INDUSTRY_REGISTRY, @register_industry, get_industry_module()
├── exceptions.py        # IndustryError, UnsupportedIndustryError
├── tech_saas.py         # TechSaaSModule (tech)
├── manufacturing.py     # ManufacturingModule (manufacturing)
├── healthcare.py        # HealthcareModule (healthcare)
└── logistics.py         # LogisticsModule (logistics)
```

### 구현 사항

- [x] IndustryModule ABC — `get_kpis()`, `get_financial_weights()`, `get_chart_recommendations()`, `get_narrative_variant()` 추상 메서드
- [x] Registry 패턴: `@register_industry` 데코레이터 + `INDUSTRY_REGISTRY` dict + `get_industry_module()`
- [x] 4개 구체 산업 모듈: tech, manufacturing, healthcare, logistics
- [x] IMDocumentData 통합: `industry: str`, `industry_data: dict[str, Any]` 필드 추가
- [x] Pipeline 통합: step 1.5에서 산업 모듈 resolve (lazy import, graceful fallback)
- [x] SECTION_IDS (18) vs INDUSTRY_SECTION_IDS (2) vs ALL_SECTION_IDS (20) 분리

**테스트 현황**: 22 tests (모두 통과)

---

## Phase B: 산업별 재무 지표 (`src/financial_engine/calculator/`) — ✅ v0.4.0 완료

> 세부 계획: `docs/plans/multi-industry-expansion-plan.md` Section 4

### 추가된 모듈 (4개 신규 source + 3개 수정)

```
src/financial_engine/calculator/
├── saas.py                    # SaaSMetrics (10개 지표: ARR, MRR, NRR, Churn, LTV, CAC 등)
├── manufacturing_metrics.py   # ManufacturingMetrics (5개 지표: OEE, CAPA 가동률, 수율 등)
├── healthcare_metrics.py      # HealthcareMetrics (4개 지표: rNPV, 성공률, 특허, R&D/Revenue)
└── logistics_metrics.py       # LogisticsMetrics (4개 지표: 정시 배송률, Fleet, 톤km, 건당 비용)
```

### Sprint B1: SaaS 지표 ✅

- [x] `saas.py` — SaaSMetrics dataclass + 10개 순수 함수형 계산기 + orchestrator
- [x] 테스트 32개: NRR > 100%, net churn 음수, churn_rate==0 LTV 제외, Rule of 40 등

### Sprint B2: 제조업 지표 ✅

- [x] `manufacturing_metrics.py` — ManufacturingMetrics + 5개 계산기
- [x] OEE 자동 감지 (0-1 소수 vs 0-100 백분율)
- [x] 테스트 20개: OEE 입력 감지, CAPEX abs() 처리, 재고회전율 등

### Sprint B3: 헬스케어 + 물류 지표 ✅

- [x] `healthcare_metrics.py` — HealthcareMetrics + 4개 계산기 (rNPV, 단계별 성공률, 특허, R&D/매출)
- [x] `logistics_metrics.py` — LogisticsMetrics + 4개 계산기 (정시 배송률, Fleet 가동률, 톤km당 매출, 건당 비용)
- [x] 테스트 37개 (healthcare 19 + logistics 18)

### Sprint B4: 통합 ✅

- [x] `calculator/__init__.py` — IndustryMetrics 타입 별칭 + 4개 calculator export
- [x] `processor.py` — `process()` 시그니처에 `industry_id`, `industry_data` 추가, `_calculate_industry_metrics()` 디스패치, `ProcessingResult.industry_metrics` 필드
- [x] `financial_engine/__init__.py` — 신규 타입 re-export
- [x] 통합 테스트 4개: SaaS/Manufacturing/미제공/미등록 ID

**테스트 현황**: 93 tests 추가 (B1: 32, B2: 20, B3: 37, B4: 4), 전체 1180 tests 통과

---

## 통합 의존성 그래프

```
Phase 2: Data Collection (S1-S3) ✅ v0.2.1 완료
        │
        ▼
Phase 3: Financial Engine (S3) ✅ v0.3.0 완료
        │
        ▼
Phase 5: AI/Narrative (S4-S6) ✅ v0.5.0 완료
        │
   ┌────┴────┐
   ▼         ▼
Chart      Brand
Engine     Extractor
(S7) ✅    (S8) ✅
   └────┬────┘
        ▼
Phase 4: Design Renderer ✅ v0.4.0 완료 (이미 선행 구현)
        │
        ▼
Phase 6: Integration (S9-S11+) ✅ v1.0.0 완료
        │
        ▼
Phase A1: Industry Module ✅ v0.1.0 완료
        │
        ▼
Phase B: Industry Financial Metrics ✅ v0.4.0 완료
        │
        ▼
   Production Deployment ⏳ (프론트엔드만 미구현)
```

> **참고**: Phase 4(Design Renderer)는 다른 Phase에 앞서 구현 완료됨.
> Chart Engine과 Brand Extractor는 Design Renderer의 기존 컴포넌트를 확장하는 형태.
> Phase A1(Industry Module)과 Phase B(산업별 재무 지표)는 Phase 3 위에 확장 구현.

---

## 일정 요약

| 스프린트 | Phase | 기간 | 주요 산출물 | 티켓 수 | 상태 |
|---------|-------|------|------------|--------|------|
| S1 | P2 | Week 1 | Data Collection Foundation | 5 | ✅ |
| S2 | P2 | Week 2 | DART Client + Parsers + Aggregator | 11 | ✅ |
| S2.5 | P2 | Week 2 | E2E Pipeline + Cache + Error Recovery | 3 | ✅ |
| S3 | P3 | Week 3 | Financial Engine 전체 | 14 | ✅ |
| S4 | P5 | Week 4 | RAG Infrastructure | 6 | ✅ |
| S5 | P5 | Week 5 | 15개 섹션 프롬프트 + 4 산업 변형 | 6 | ✅ |
| S6 | P5 | Week 6 | LLM Engine + Fact Checker | 7 | ✅ |
| S7 | — | Week 7 | Chart Engine 확장 | 9 | ✅ |
| S8 | — | Week 8 | Brand Extractor | 10 | ✅ |
| S9 | P6 | Week 9 | API Foundation + DB | 6 | ✅ |
| S10 | P6 | Week 10 | Auth + Celery | 8 | ✅ |
| S11 | P6 | Week 11 | Routes + Deployment | 9 | ✅ |
| S11+ | P6 | Week 11 | Auth/User/APIKey Routes + Alembic + CI/CD | 6 | ✅ |
| A1 | PA1 | Week 12 | Industry Module Foundation (레지스트리 + ABC + 4개 산업) | 5 | ✅ |
| B1-B4 | PB | Week 12 | Industry Financial Metrics (SaaS/제조/헬스케어/물류) | 8 | ✅ |
| **합계** | | **~12주** | | **~117** | **117/117 완료** |

> Phase 4 (Design Renderer)는 별도 47개 티켓으로 이미 완료 (Sprint 1-5).
> 총 프로젝트 티켓: ~155개 (Phase 4 47 + 나머지 117), **완료: ~155개 (~99%)** — 프론트엔드만 미구현

---

## 테스트 현황

| 모듈 | 파일 수 | 테스트 수 | 상태 |
|------|---------|----------|------|
| data_ingestor | 11 | 223 | ✅ 통과 |
| financial_engine | 18 | 280 | ✅ 통과 |
| design_renderer | 13 | 107 | ✅ Tier 1/2/3 |
| narrative_generator | 10 | 43 | ✅ 통과 |
| chart_engine | 8 | 61 | ✅ 통과 |
| brand_extractor | 12 | 66 | ✅ 통과 |
| api | 28 | 256 | ✅ 통과 |
| industry | 6 | 136 | ✅ 통과 |
| integration | 2 | 8 | ✅ 통과 |
| **합계** | **113** | **1180** | **✅ 전체 통과** |

---

## 잔여 작업

| # | 항목 | 설명 | 우선순위 | 상태 |
|---|------|------|----------|------|
| ~~1~~ | ~~인증 라우트~~ | ~~login/refresh/logout~~ | ~~HIGH~~ | ✅ 완료 |
| ~~2~~ | ~~사용자 관리 라우트~~ | ~~CRUD + RBAC 7개 엔드포인트~~ | ~~HIGH~~ | ✅ 완료 |
| ~~3~~ | ~~API 키 관리 라우트~~ | ~~create/list/revoke~~ | ~~MEDIUM~~ | ✅ 완료 |
| ~~4~~ | ~~Alembic 마이그레이션~~ | ~~4개 테이블 초기 스키마~~ | ~~HIGH~~ | ✅ 완료 |
| ~~5~~ | ~~CI/CD 파이프라인~~ | ~~GitHub Actions (ci.yml + cd.yml)~~ | ~~MEDIUM~~ | ✅ 완료 |
| 6 | 프론트엔드 | 웹 UI — 현재 REST API만 존재 (`docs/plans/unified-frontend-integration-plan.md` 참조) | LOW | ❌ 미구현 |

---

## 위험 완화

| 위험 | 영향 | 완화 방안 |
|------|------|----------|
| DART API rate limit 초과 | 데이터 수집 실패 | Token bucket + Circuit breaker (구현 완료) |
| LLM 환각 (hallucination) | 잘못된 내러티브 | Fact checker 검증 레이어 (✅ 구현 완료) |
| 한글 폰트 렌더링 | 차트 깨짐 | 폰트 폴백 체인 + NanumGothic |
| Brandfetch API 제한 | 브랜드 추출 실패 | 웹사이트 추출 폴백 |
| 토큰 예산 초과 | 내러티브 잘림 | 섹션별 예산 모니터링 (✅ TokenBudgetManager 구현) |
| Playwright 브라우저 설치 | 크롤러/PDF 실패 | Docker 이미지에 사전 설치 |

---

## 세부 계획 문서 참조

| 문서 | 위치 | 내용 |
|------|------|------|
| Design Renderer 통합 설계 | `docs/plans/design-renderer-integration-plan.md` | Phase 4 상세 설계 (컴포넌트, 검증, 보안) |
| Design Renderer 병렬 실행 | `docs/plans/design-renderer-parallel-plan.md` | 7 워크스트림 × 5 스프린트 47개 티켓 |
| 미착수 Phase 통합 계획 | `docs/plans/remaining-phases-implementation-plan.md` | Phase 2,3,5,6 + Chart/Brand (~95개 티켓) |

---

## 메모

- 2026-02-08: Design Renderer Sprint 1 (Foundation) 완료 — 5개 티켓 전부 병렬 완료
- 2026-02-08: Sprint 2~4 완료 — 52개 모듈, 18/18 섹션 렌더러 등록
- 2026-02-08: Sprint 5 완료 — E2E 파이프라인 + 보안 + 통합 테스트 (v0.4.0)
- 2026-02-08~09: Data Ingestor Sprint 1-2 완료 — 161 tests, 15개 모듈
- 2026-02-09: Plan 문서 통합 — 4개 분산 문서를 PLAN.md로 통합
- 2026-02-09: Financial Engine v0.3.0 완료 — 18개 파일, 195 tests, 14티켓 전체 완료
- 2026-02-09: PLAN.md 현황 갱신 — Phase 3 완료 반영, 전체 진행률 ~54%
- 2026-02-09: Phase 2 Sprint 3 완료 확인 — cache.py + pipeline.py 구현, 223 tests, v0.2.1
- 2026-02-09: 전체 진행현황 점검 — 소스 95파일, 테스트 41파일, 525 tests 전체 통과, ~55%
- 2026-02-10: Narrative Generator v0.5.0 완료 — 29개 소스, 43 tests, 19티켓 전체 완료 (S4-S6)
- 2026-02-10: Chart Engine v0.7.0 완료 — 18개 소스, 61 tests, 9티켓 전체 완료 (S7)
- 2026-02-10: Brand Extractor v0.8.0 완료 — 16개 소스, 66 tests, 10티켓 전체 완료 (S8)
- 2026-02-10: API Sprint S9 Foundation 완료 — 12개 소스, 61 tests, 6티켓 전체 완료
- 2026-02-10: API Sprint S10 Auth+Celery 완료 — 12개 소스, 83 tests, 8티켓 전체 완료
- 2026-02-10: API Sprint S11 Routes+Deployment 완료 — 19개 소스, 63 tests, Docker 배포 구성
- 2026-02-10: 전체 프로젝트 ~97% 완료 — 902 tests 전체 통과, 문서 현황 갱신
- 2026-02-10: Sprint S11+ 완료 — Auth 라우트 (login/refresh/logout), User 라우트 (CRUD+RBAC 7개), API Key 라우트 (create/list/revoke), 49 tests 추가
- 2026-02-10: Alembic 마이그레이션 완료 — alembic/ 디렉토리, env.py (async), 001_initial_schema.py (users/api_keys/companies/documents 4개 테이블)
- 2026-02-10: CI/CD 파이프라인 완료 — .github/workflows/ci.yml (lint+test+build) + cd.yml (staging+prod deploy)
- 2026-02-10: 인프라 완료 — Docker (multi-stage), docker-compose (5 services), Nginx, Gunicorn, 배포 스크립트, 환경 템플릿
- 2026-02-10: 전체 프로젝트 ~99% 완료 — 206 소스, 102 테스트 파일, 951 tests 전체 통과, 백엔드 100% 완료
- 2026-02-11: .claude/RULES.md 생성 — 4단계 Plan Mode Review 체크리스트 (Architecture → Code Quality → Tests → Performance)
- 2026-02-11: PLAN.md 업데이트 내역 반영 — S11+ 완료, 진행률 ~99%, 테스트 951개, 잔여 작업 프론트엔드만
- 2026-02-11: Phase A1 Industry Module v0.1.0 완료 — 레지스트리 패턴, IndustryModule ABC, 4개 산업 모듈, 22 tests
- 2026-02-11: Phase B Industry Financial Metrics 완료 — SaaS(32t)/Manufacturing(20t)/Healthcare(19t)/Logistics(18t)/통합(4t) = 93 tests 추가
- 2026-02-11: Financial Engine v0.4.0 — 산업별 계산기 4종 + IndustryMetrics 타입 + Processor 통합, 전체 1180 tests 통과
