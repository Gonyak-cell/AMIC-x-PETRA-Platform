# Remaining Phases Implementation Plan (S4-S11)

## Context
Phase 2(Data Ingestor), 3(Financial Engine), 4(Design Renderer) 완료 (525 tests, 95 source files).
남은 4개 모듈을 8개 스프린트(S4-S11)에 걸쳐 구현한다: **Narrative Generator → Chart Engine + Brand Extractor (병렬) → API Integration**.
총 ~61 티켓, ~99 소스 파일, ~51 테스트 파일, 157+ 테스트 케이스 추가 예상.

---

## Timeline Overview

```
Week 4:  S4 — Narrative RAG Infrastructure (6 tickets)
Week 5:  S5 — Narrative Prompts (6 tickets)
Week 6:  S6 — Narrative Engine + Fact Checker (7 tickets)
Week 7-8: S7 + S8 병렬 — Chart Engine (9) + Brand Extractor (10)
Week 9:  S9 — API Foundation + DB (6 tickets)
Week 10: S10 — Auth + Celery (8 tickets)
Week 11: S11 — Routes + Deployment (9 tickets)
```

---

## Critical Files (참조/수정 대상)

| File | Role |
|------|------|
| `src/design_renderer/im_document.py` | IMDocumentData 중앙 데이터 모델 (.narratives, .charts, .brand_assets) |
| `src/design_renderer/design_tokens.py` | IMDesignTokens.from_brand_assets() — Brand Extractor 출력 계약 |
| `src/design_renderer/components/chart_embed.py` | 기존 6종 Plotly 차트 → chart_engine으로 리팩토링 |
| `src/financial_engine/processor.py` | Processor/Config/Result 패턴 참조 |
| `src/design_renderer/pipeline.py` | IMPipeline — Celery Stage 4에서 호출 |

---

## Established Patterns (모든 신규 파일 준수)

1. **Exception**: `ModuleError(Exception)` + `__init__(message, details={})` + 도메인 서브클래스
2. **Config**: `@dataclass(frozen=True)` + nested sub-config + `from_env()` classmethod
3. **Result**: `@dataclass` + warnings/errors/duration + `@property` helpers
4. **`__init__.py`**: explicit `__all__`, `__version__`, grouped imports
5. **Imports**: `from __future__ import annotations`, `TYPE_CHECKING` guards
6. **Logging**: `logger = logging.getLogger(__name__)` with %-formatting
7. **Async**: Context manager (`__aenter__`/`__aexit__`) for network-bound classes
8. **Tests**: `tests/test_[module]/` mirrors src, per-module conftest.py, markers for optional deps

---

## Phase 5: Narrative Generator (S4-S6, 19 tickets)

### S4: RAG Infrastructure (6 tickets)

**병렬 구조**: T-N01 + T-N04 + T-N06 동시 → T-N02 + T-N03 (N01 이후) → T-N05 (N02+N03 이후)

| Ticket | File | Description | Depends |
|--------|------|-------------|---------|
| T-N01 | `src/narrative_generator/config.py` | NarrativeConfig(frozen) — OpenAI/Pinecone/LLM 설정, from_env() | — |
| T-N02 | `src/narrative_generator/rag/embedder.py` | OpenAIEmbedder — text-embedding-3-small, async embed/embed_query | N01 |
| T-N03 | `src/narrative_generator/rag/vector_store.py` | PineconeVectorStore — async context manager, upsert/query/delete | N01 |
| T-N04 | `src/narrative_generator/rag/chunker.py` | DocumentChunker — tiktoken 기반, max_tokens=512, overlap=50 | — |
| T-N05 | `src/narrative_generator/rag/retriever.py` | RAGRetriever — embedder+store 결합, industry filter, reranking | N02,N03 |
| T-N06 | `src/narrative_generator/korean_finance/terminology.py` | 80+ EN↔KR 금융용어 매핑, annotate_text() | — |

**+ exceptions.py**: NarrativeGeneratorError → {EmbeddingError, VectorStoreError, RetrievalError, PromptError, LLMError, TokenBudgetError, FactCheckError}

**+ korean_finance/tone_adapter.py**: "사실적 낙관주의" 톤 조정기

**Tests**: `tests/test_narrative_generator/conftest.py` + test_config, test_chunker, test_embedder, test_vector_store, test_retriever, test_terminology

**핵심 인터페이스**:
```python
@dataclass(frozen=True)
class NarrativeConfig:
    openai_api_key: str = ""
    pinecone_api_key: str = ""
    embedder: EmbedderConfig = field(default_factory=EmbedderConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    default_industry: str = "general"
    fact_check_enabled: bool = True
    confidence_threshold: float = 0.7

    @classmethod
    def from_env(cls) -> NarrativeConfig: ...
```

### S5: Prompts (6 tickets)

**병렬 구조**: T-N07 먼저 → T-N08~N11 동시 → T-N12 (N08-11 이후)

| Ticket | Files | Description | Depends |
|--------|-------|-------------|---------|
| T-N07 | `prompts/base.py` | BasePrompt ABC + PROMPT_REGISTRY + @register_prompt decorator | — |
| T-N08 | `prompts/section_prompts/` (4) | Core: executive_summary, company_overview, business_overview, deal_overview | N07 |
| T-N09 | `prompts/section_prompts/` (3) | Financial: financial_analysis, transaction_structure, shareholder_structure | N07 |
| T-N10 | `prompts/section_prompts/` (4) | Strategy: investment_highlights, market_overview, value_creation, growth_strategy | N07 |
| T-N11 | `prompts/section_prompts/` (4) | Supporting: management_team, business_model, appendix, contact | N07 |
| T-N12 | `prompts/industry_variants/` (4) | IndustryVariant: tech, healthcare, manufacturing, financial_services | N08-11 |

**BasePrompt 핵심 인터페이스** (design_renderer의 RENDERER_REGISTRY 패턴 미러링):
```python
class BasePrompt(ABC):
    section_id: str
    default_token_budget: int = 2000
    def render_system_prompt(self, *, industry: str = "general") -> str: ...
    def render_user_prompt(self, data: IMDocumentData, *, contexts: list[str] | None = None) -> str: ...

PROMPT_REGISTRY: dict[str, type[BasePrompt]] = {}

@register_prompt  # decorator
class ExecutiveSummaryPrompt(BasePrompt):
    section_id = "executive_summary"
    ...
```

**IndustryVariant**:
```python
class IndustryVariant:
    industry_id: str
    key_metrics: list[str]           # e.g., ["ARR", "MRR", "NDR"] for tech
    tone_modifiers: dict[str, str]
    terminology_overrides: dict[str, str]
```

### S6: Engine + Fact Checker (7 tickets)

**병렬 구조**: T-N13 먼저 → {T-N14, T-N15} + {T-N16, T-N17, T-N18} 동시 → T-N19(통합 테스트)

| Ticket | File | Description | Depends |
|--------|------|-------------|---------|
| T-N13 | `engine/orchestrator.py` | NarrativeOrchestrator — async context manager, generate_all_narratives() → NarrativeResult | S4+S5 |
| T-N14 | `engine/token_budget.py` | TokenBudgetManager — 18 섹션 토큰 예산 배분, tiktoken | N13 |
| T-N15 | `engine/structured_output.py` | StructuredOutputParser — LLM 출력 파싱, claim 추출 | N13 |
| T-N16 | `fact_checker/validator.py` | NarrativeValidator — 수치 claim 추출+검증 vs source data | N13 |
| T-N17 | `fact_checker/consistency.py` | ConsistencyChecker — 섹션 간 수치 모순 탐지 | N13 |
| T-N18 | `fact_checker/confidence.py` | ConfidenceScorer — narrative 신뢰도 0-1 | N13 |
| T-N19 | Tests | 25+ tests — orchestrator, token_budget, validator, consistency, confidence | All |

**NarrativeOrchestrator (핵심 클래스)**:
```python
@dataclass
class NarrativeResult:
    narratives: dict[str, str]       # section_id → text
    token_usage: dict[str, int]
    fact_check_results: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def success(self) -> bool: ...
    @property
    def failed_sections(self) -> list[str]: ...

class NarrativeOrchestrator:
    def __init__(self, config: NarrativeConfig | None = None) -> None: ...
    async def __aenter__(self) -> NarrativeOrchestrator: ...
    async def __aexit__(self, *args) -> None: ...
    async def generate_narrative(self, section_id: str, data: IMDocumentData, *, industry: str = "general") -> str: ...
    async def generate_all_narratives(self, data: IMDocumentData, *, industry: str = "general", sections: list[str] | None = None) -> NarrativeResult: ...
```

**NarrativeValidator (팩트체커)**:
```python
@dataclass
class NumericalClaim:
    value: float
    unit: str
    context: str
    source_field: str | None = None

@dataclass
class FactCheckResult:
    claim: NumericalClaim
    is_valid: bool
    confidence: float    # 0-1
    explanation: str = ""

class NarrativeValidator:
    def validate(self, narrative: str, source_data: IMDocumentData) -> list[FactCheckResult]: ...
    def validate_all(self, narratives: dict[str, str], source_data: IMDocumentData) -> dict[str, list[FactCheckResult]]: ...
```

**`__init__.py`** (S6 완료 후): `__version__ = "0.5.0"`, exports: NarrativeConfig, NarrativeOrchestrator, NarrativeResult, NarrativeValidator, RAGRetriever, DocumentChunker

**환경 설정**: OPENAI_API_KEY, PINECONE_API_KEY (.env), Pinecone index `im-narratives` 생성 (dim=1536, cosine), tiktoken 추가

---

## Chart Engine (S7, 9 tickets) — S8과 병렬

**핵심 전략**: chart_embed.py(543줄) 기존 코드를 chart_engine으로 추출/리팩토링. chart_embed.py는 thin wrapper로 유지 (기존 107 tests 호환).

**병렬 구조**: T-C01 먼저 → {T-C02~C06} 동시 → {T-C07, T-C08} 동시 → T-C09(tests)

| Ticket | File(s) | Description | Depends |
|--------|---------|-------------|---------|
| T-C01 | Module scaffold | config.py, exceptions.py, `__init__.py`, 디렉토리 구조 | — |
| T-C02 | `plotly/themes.py` | AMICThemeFactory — _apply_amic_layout 추출, get_color_sequence | C01 |
| T-C03 | `plotly/{waterfall,combo,stacked_bar,donut,line,hbar}.py` | 6종 Plotly 차트 — chart_embed.py에서 추출+개선 | C01 |
| T-C04 | `graphviz/org_chart.py` | design_renderer/components/org_chart.py에서 리팩토링 | C01 |
| T-C05 | `graphviz/{flow_diagram,shareholding}.py` | 신규: 거래구조도(Transaction Structure), 주주구조도 | C01 |
| T-C06 | `data_transformer.py` | ChartDataTransformer — IMDocumentData → dict[str, list[ChartData]] | C01 |
| T-C07 | `export/png_exporter.py` | Plotly→PNG(300DPI, Kaleido) + Graphviz→PNG | C01 |
| T-C08 | `export/svg_exporter.py` | Plotly→SVG + Graphviz→SVG (PDF용) | C01 |
| T-C09 | Tests (15+) | test_themes, test_waterfall~hbar, test_org_chart, test_transformer, test_export | All |

**핵심 인터페이스**:
```python
@dataclass(frozen=True)
class ChartConfig:
    dpi: int = 300
    default_width: int = 900
    default_height: int = 500
    scale: int = 3
    font_korean: str = "NanumGothic"
    output_format: str = "png"   # "png" | "svg"

class AMICThemeFactory:
    @staticmethod
    def create_theme(tokens: IMDesignTokens) -> dict: ...
    @staticmethod
    def get_color_sequence(tokens: IMDesignTokens) -> list[str]: ...
    @staticmethod
    def apply_theme(fig: go.Figure, tokens: IMDesignTokens, *, title: str = "") -> None: ...

class ChartDataTransformer:
    def transform_financial_analysis(self, data: IMDocumentData) -> list[ChartData]: ...
    def transform_market_overview(self, data: IMDocumentData) -> list[ChartData]: ...
    def transform_shareholder_structure(self, data: IMDocumentData) -> list[ChartData]: ...
    def transform_all(self, data: IMDocumentData) -> dict[str, list[ChartData]]: ...
```

**Backward Compatibility**: chart_embed.py를 thin wrapper로 변환:
```python
# design_renderer/components/chart_embed.py (updated)
from src.chart_engine import create_waterfall_chart, create_combo_chart, ...
# Re-export for backward compat — 기존 107 tests 유지
```

**출력 계약**: `IMDocumentData.charts: dict[str, list[ChartData]]` 채움
**`__init__.py`**: `__version__ = "0.7.0"`, ChartConfig, AMICThemeFactory, ChartDataTransformer, export functions

---

## Brand Extractor (S8, 10 tickets) — S7과 병렬

**병렬 구조**: {T-B01, T-B09} 동시 → {T-B02, T-B03, T-B05} 동시 → T-B04(B03후), T-B06→T-B07(B05후) → T-B08(B03+B05후) → T-B10(tests)

| Ticket | File | Description | Depends |
|--------|------|-------------|---------|
| T-B01 | `models.py` | BrandAssets dataclass — primary_color, logo paths, confidence, source | — |
| T-B02 | `extractors/brandfetch.py` | BrandfetchClient — async API wrapper | B01 |
| T-B03 | `logo/detector.py` | LogoDetector — HTML에서 logo URL 탐지 (og:image, apple-touch-icon, favicon, img.logo) | B01 |
| T-B04 | `logo/scorer.py` | LogoScorer — 해상도(>=256px), 비율, 투명도(PNG) 기반 0-1 점수 | B03 |
| T-B05 | `color/extractor.py` | ColorExtractor — K-Means(scikit-learn) 색상 추출 (n_colors=5) | B01 |
| T-B06 | `color/classifier.py` | ColorClassifier — primary/secondary/accent 분류 (채도/명도 기반) | B05 |
| T-B07 | `color/token_mapper.py` | BrandTokenMapper → IMDesignTokens 매핑 | B06 |
| T-B08 | `extractors/website.py` | WebsiteExtractor — Playwright 기반 통합 추출 (logo + color pipeline) | B03,B05 |
| T-B09 | `extractors/fallback.py` | FallbackExtractor — AMIC 기본값 (#0F3A32, #26C260) | — |
| T-B10 | Tests (12+) | 전체 테스트 — mock Brandfetch, sample HTML/images | All |

**핵심 인터페이스**:
```python
@dataclass
class BrandAssets:
    company_name: str = ""
    primary_color: str = "#0F3A32"       # AMIC default
    secondary_color: str = "#26C260"     # AMIC default
    logo_dark_path: str = ""
    logo_white_path: str = ""
    cover_bg_path: str = ""
    logo_url: str = ""
    favicon_url: str = ""
    confidence: float = 0.0              # 0-1
    source: str = "fallback"             # "brandfetch" | "website" | "fallback"
    additional_colors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class BrandExtractorConfig:
    brandfetch_api_key: str = ""
    timeout: int = 30
    min_logo_size: int = 64              # px
    max_colors: int = 5
    fallback_enabled: bool = True
```

**Extraction Priority Chain**: Brandfetch API → Website crawl → AMIC fallback

**출력 계약**: BrandAssets → `IMDocumentData.brand_assets` → `IMDesignTokens.from_brand_assets(brand)`
- `from_brand_assets()` expects: primary_color, secondary_color, company_name, logo_dark_path, logo_white_path, cover_bg_path

**Exceptions**: BrandExtractorError → {BrandfetchAPIError, LogoDetectionError, ColorExtractionError, WebsiteAccessError}

**`__init__.py`**: `__version__ = "0.8.0"`, BrandAssets, BrandExtractorConfig, WebsiteExtractor, FallbackExtractor

**환경**: BRANDFETCH_API_KEY (.env, optional — fallback 가용)

---

## Phase 6: API Integration (S9-S11, 23 tickets)

### S9: Foundation + DB (6 tickets)

**병렬**: {T-I01, T-I02} 동시 → T-I03 → T-I04 → T-I05, T-I06(I01후)

| Ticket | File(s) | Description | Depends |
|--------|---------|-------------|---------|
| T-I01 | `main.py` + `__init__.py` | FastAPI app factory — create_app(), router/middleware 등록 | — |
| T-I02 | `config.py` | Pydantic Settings — DB/Redis/JWT/API keys, port 5434/6380 | — |
| T-I03 | `db/base.py` + `db/session.py` | SQLAlchemy async engine + session factory | I02 |
| T-I04 | `db/models/{user,document,company}.py` | ORM: User(RBAC), Document(status/progress), Company(cache) | I03 |
| T-I05 | `alembic/` | Alembic 설정 + initial migration (users, documents, companies) | I04 |
| T-I06 | `routes/health.py` | GET /health, GET /ready (DB+Redis connectivity 체크) | I01 |

**핵심 인터페이스**:
```python
# config.py
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/imgen"
    redis_url: str = "redis://localhost:6380/0"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "RS256"
    openai_api_key: str = ""
    pinecone_api_key: str = ""
    dart_api_key: str = ""
    brandfetch_api_key: str = ""
    debug: bool = False
    allowed_origins: list[str] = ["*"]
    rate_limit: str = "100/minute"
    class Config:
        env_file = ".env"

# db/models/document.py
class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]           # FK → users
    company_corp_code: Mapped[str]
    status: Mapped[str]                   # PENDING → PROCESSING → COMPLETED / FAILED
    progress: Mapped[int]                 # 0-100
    im_style: Mapped[str]                # TITAN / COVENANT / FULL
    celery_task_id: Mapped[str | None]
    pptx_path: Mapped[str | None]
    pdf_path: Mapped[str | None]
    error_message: Mapped[str | None]
    config_json: Mapped[dict]             # JSONB
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### S10: Auth + Celery (8 tickets)

**병렬**: {T-I07, T-I08, T-I09} 동시 → T-I10 → T-I11 → {T-I12, T-I13, T-I14} 동시

| Ticket | File | Description | Depends |
|--------|------|-------------|---------|
| T-I07 | `security/auth.py` | JWTAuthenticator — RS256, create_access_token/verify_token | — |
| T-I08 | `security/api_keys.py` | APIKeyManager — SHA-256 hash, generate/verify | — |
| T-I09 | `security/rbac.py` | Role enum (ADMIN/MANAGER/USER), require_role() FastAPI dependency | — |
| T-I10 | `dependencies.py` | get_db(), get_current_user(), get_current_active_user() | I07,I08 |
| T-I11 | `tasks/celery_app.py` | Celery config — Redis broker(6380/0), backend(6380/1), JSON serializer | — |
| T-I12 | `tasks/generate_im.py` | generate_im_task — chord pattern (5-stage pipeline) | I11 |
| T-I13 | `tasks/fetch_company.py` | fetch_company_data_task — DataCollectionPipeline 호출 | I11 |
| T-I14 | `tasks/narrative.py` | generate_narrative_task — NarrativeOrchestrator 호출 | I11 |

**Celery 5-Stage Pipeline (generate_im_task)**:
```
Stage 1: Data Collection (DataCollectionPipeline.collect) → 25%
Stage 2: Financial Analysis (FinancialProcessor.process) → 40%
Stage 3: group(                                          → 70%
    generate_narrative_task,    # NarrativeOrchestrator
    create_charts_task,         # ChartDataTransformer
    extract_brand_task,         # WebsiteExtractor/FallbackExtractor
)  ← 병렬 실행
Stage 4: Document Render (IMPipeline.generate) → 95%
Stage 5: Finalize + webhook notification → 100%
```

### S11: Routes + Deployment (9 tickets)

**병렬**: {T-I15, T-I20, T-I21} 동시 → {T-I16, T-I17} → T-I18 → T-I19(통합) → T-I22, T-I23

| Ticket | File(s) | Description | Depends |
|--------|---------|-------------|---------|
| T-I15 | `schemas/{documents,companies,common,im_data}.py` | Pydantic v2 request/response 모델 | — |
| T-I16 | `routes/documents.py` | POST/GET/download /api/v1/documents | I15,I10 |
| T-I17 | `routes/companies.py` | POST/GET /api/v1/companies | I15,I10 |
| T-I18 | `services/{document,company,webhook}_service.py` | 비즈니스 로직 레이어 | I16,I17 |
| T-I19 | Full pipeline integration | 전 모듈 연결 → generate_im_task 완성 | I18+All |
| T-I20 | `middleware/{rate_limit,cors,logging}.py` | SlowAPI, CORS, request/response logging | — |
| T-I21 | `Dockerfile` | Multi-stage: Python 3.11-slim + Playwright + Graphviz + WeasyPrint | — |
| T-I22 | `docker-compose.yml` 확장 | api, celery_worker, celery_beat 서비스 추가 | I21 |
| T-I23 | E2E Tests | POST document → poll status → download 전체 플로우 | I19 |

**API Endpoints**:
```
POST   /api/v1/documents              → 202 Accepted (Celery task 시작)
GET    /api/v1/documents/{id}         → status + progress
GET    /api/v1/documents/{id}/download → PPTX/PDF 파일
POST   /api/v1/companies              → DART 데이터 수집 시작
GET    /api/v1/companies/{corp_code}  → 캐시된 기업 정보
GET    /health                        → 서비스 상태
GET    /ready                         → DB+Redis 연결 확인
```

**Schemas**:
```python
class DocumentCreate(BaseModel):
    corp_code: str
    company_name: str
    im_style: str = "FULL"
    industry: str = "general"
    sections: list[str] | None = None

class DocumentResponse(BaseModel):
    id: str
    status: str     # PENDING, PROCESSING, COMPLETED, FAILED
    progress: int   # 0-100
    created_at: datetime
    download_url: str | None = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    per_page: int
```

**Exceptions**: APIError → {AuthenticationError, AuthorizationError, NotFoundError, ValidationError, TaskError}

**`__init__.py`**: `__version__ = "1.0.0"`

---

## Cross-Module Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Data Ingestor  │────→│ Financial Engine  │────→│  IMDocumentData  │
│   (Phase 2) ✅  │     │   (Phase 3) ✅   │     │  (Central Model) │
└─────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                          │
                    ┌─────────────────────────────────────┼──────────────────────┐
                    │                                     │                      │
                    ▼                                     ▼                      ▼
        ┌───────────────────┐             ┌───────────────────┐     ┌──────────────────┐
        │ Narrative Generator│             │   Chart Engine    │     │ Brand Extractor   │
        │    (Phase 5)      │             │     (S7)          │     │    (S8)           │
        │                   │             │                   │     │                   │
        │ → .narratives     │             │ → .charts         │     │ → .brand_assets   │
        └───────┬───────────┘             └──────┬────────────┘     └────────┬──────────┘
                │                                │                           │
                └────────────────────────────────┼───────────────────────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │   Design Renderer     │
                                     │    (Phase 4) ✅       │
                                     │                       │
                                     │ IMPipeline.generate() │
                                     │ → PPTX + PDF          │
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │   API Integration     │
                                     │    (Phase 6)          │
                                     │                       │
                                     │ FastAPI + Celery      │
                                     │ → REST endpoints      │
                                     └───────────────────────┘
```

---

## Dependency Graph (병렬 실행 가능 구간)

```
S4 (RAG)
├── [Parallel] T-N01 + T-N04 + T-N06
├── [After N01] T-N02 + T-N03
└── [After N02+N03] T-N05
     │
     ▼
S5 (Prompts)
├── T-N07
├── [Parallel after N07] T-N08 + T-N09 + T-N10 + T-N11
└── [After N08-11] T-N12
     │
     ▼
S6 (Engine + Fact Checker)
├── T-N13
├── [Parallel] {T-N14, T-N15} + {T-N16, T-N17, T-N18}
└── T-N19 (tests)
     │
     ▼
S7 (Chart Engine) ────── PARALLEL ────── S8 (Brand Extractor)
├── T-C01                                ├── {T-B01, T-B09}
├── [Par] T-C02~C06                      ├── [Par] T-B02, T-B03, T-B05
├── [Par] T-C07, T-C08                   ├── T-B04 (after B03)
└── T-C09 (tests)                        ├── T-B06→T-B07 (after B05)
                                         ├── T-B08 (after B03+B05)
                                         └── T-B10 (tests)
     │                                        │
     └──────────────┬─────────────────────────┘
                    ▼
S9 (API Foundation)
├── [Parallel] T-I01 + T-I02
├── T-I03 → T-I04 → T-I05
└── T-I06 (after I01)
     │
     ▼
S10 (Auth + Celery)
├── [Parallel] T-I07 + T-I08 + T-I09
├── T-I10 (after I07+I08)
├── T-I11
└── [Parallel after I11] T-I12 + T-I13 + T-I14
     │
     ▼
S11 (Routes + Deploy)
├── [Parallel] T-I15 + T-I20 + T-I21
├── T-I16 + T-I17 (after I15+I10)
├── T-I18 (after I16+I17)
├── T-I19 (full integration)
├── T-I22 (after I21)
└── T-I23 (E2E tests)
```

---

## Risk Mitigation

| Risk | Sprint | 대응 |
|------|--------|------|
| OpenAI API rate limits | S4-S6 | 테스트에서 LLM 호출 전체 Mock, `@pytest.mark.requires_openai` live 테스트 분리 |
| Pinecone cold start | S4 | 인덱스 사전 생성, 테스트는 mocked store 사용 |
| tiktoken encoding drift | S6 | tiktoken 버전 고정, expected count snapshot |
| chart_embed.py 리팩토링 → design_renderer 테스트 깨짐 | S7 | chart_embed.py를 thin re-export wrapper 유지, 기존 107 tests 먼저 실행 확인 |
| Brandfetch API quota | S8 | fallback 항상 가용, 테스트는 mock only |
| Celery/Redis 연결 테스트 | S10 | `celery.contrib.testing` fixtures, mock Redis |
| Alembic migration 충돌 | S9 | single initial migration, 병렬 schema 변경 없음 |
| JWT RS256 key 관리 | S10 | conftest.py에서 test key 생성, prod는 env 변수 |

---

## Environment Setup Checklist

### Phase 5 (S4 시작 전)
- [ ] `OPENAI_API_KEY` → `.env`
- [ ] `PINECONE_API_KEY` → `.env`
- [ ] Pinecone 인덱스 생성: `im-narratives` (dimension=1536, metric=cosine)
- [ ] `tiktoken>=0.7.0` → requirements-flexible.txt (필요시)

### S7-S8 (Chart Engine + Brand Extractor)
- [ ] Graphviz 바이너리 설치 확인 (`graphviz --version`)
- [ ] Kaleido 설치 확인 (Plotly static export)
- [ ] `BRANDFETCH_API_KEY` → `.env` (optional, fallback 가용)

### Phase 6 (S9 시작 전)
- [ ] Docker 컨테이너 기동: `docker compose up -d` (PostgreSQL 5434, Redis 6380)
- [ ] Alembic 설정 및 initial migration
- [ ] RS256 JWT key pair 생성
- [ ] 모든 외부 API keys `.env` 확인

---

## pyproject.toml 추가 markers

```toml
[tool.pytest.ini_options]
markers = [
    # 기존
    "slow: 느린 테스트",
    "requires_browser: Playwright 브라우저 필요",
    "requires_plotly: Plotly + Kaleido 필요",
    "requires_weasyprint: WeasyPrint + cairo/pango 필요",
    # 신규
    "requires_openai: OpenAI API key 필요",
    "requires_pinecone: Pinecone API key 필요",
    "requires_graphviz: Graphviz 바이너리 필요",
    "requires_brandfetch: Brandfetch API key 필요",
    "requires_db: PostgreSQL 연결 필요",
    "requires_redis: Redis 연결 필요",
]
```

---

## Verification Plan

### Per-Sprint
```bash
# 각 스프린트 완료 시
pytest tests/test_[module]/ -v --tb=short
pytest tests/ -v --tb=short  # 기존 525 tests regression 확인
```

### Per-Module Completion
- **Narrative Generator (S6 후)**: `NarrativeOrchestrator.generate_all_narratives(sample_data)` → 18 섹션 dict 반환
- **Chart Engine (S7 후)**: `ChartDataTransformer.transform_all(sample_data)` → dict[str, list[ChartData]] + PNG bytes
- **Brand Extractor (S8 후)**: `FallbackExtractor.extract()` → BrandAssets → `IMDesignTokens.from_brand_assets()` 성공
- **API (S11 후)**: `POST /api/v1/documents` → 202 → poll → COMPLETED → download

### Final Integration (S11)
```bash
# Docker 전체 기동
docker compose up -d
alembic upgrade head
uvicorn src.api.main:app --port 8001
celery -A src.api.tasks.celery_app worker --loglevel=info

# E2E: document 생성 → 상태 폴링 → 다운로드
pytest tests/test_api/test_e2e.py -v
pytest tests/ -v  # 전체 682+ tests 통과
```

---

## Summary

| Module | Sprint | Tickets | New Files | Tests |
|--------|--------|---------|-----------|-------|
| Narrative Generator | S4-S6 | 19 | ~39 | 75+ |
| Chart Engine | S7 | 9 | ~30 | 20+ |
| Brand Extractor | S8 | 10 | ~22 | 15+ |
| API Integration | S9-S11 | 23 | ~44 | 47+ |
| **Total** | **8 sprints** | **61** | **~135** | **157+** |

최종: ~230 source files, ~92 test files, ~682+ tests, **v1.0.0**
