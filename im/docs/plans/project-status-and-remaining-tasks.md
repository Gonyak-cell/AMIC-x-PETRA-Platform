# Auto-IM Generator 프로젝트 현황 및 남은 작업

> 마지막 수정: 2026-02-11 17:30:00

---

## 1. 프로젝트 개요

- **프로젝트명**: Auto-IM Generator (Information Memorandum 자동 생성 시스템)
- **목적**: M&A/투자 피치용 50~80페이지 IM을 AI 기반으로 자동 생성 (PPTX + PDF)
- **기술 스택**: Python 3.11+ / FastAPI / Celery / Redis / PostgreSQL / LangChain / OpenAI / Pinecone / python-pptx / WeasyPrint / Plotly / Graphviz

---

## 2. 전체 진행률: **약 99%** (백엔드 100% 완료, 프론트엔드 미구현)

| Phase | 모듈 | 버전 | 소스 파일 | 테스트 | 완료율 | 상태 |
| ----- | ---- | ---- | -------- | ------ | ------ | ---- |
| Phase 2 | Data Ingestor | v0.2.1 | 17개 | 223개 | 100% | ✅ 완료 |
| Phase 3 | Financial Engine | v0.4.0 | 23개 | 268개 | 100% | ✅ 완료 |
| Phase 4 | Design Renderer | v0.4.0 | 58개 | 210개 | 100% | ✅ 완료 |
| Phase 5 | Narrative Generator | v0.5.0 | 33개 | 44개 | 100% | ✅ 완료 |
| Sprint S7 | Chart Engine | v0.7.0 | 23개 | 77개 | 100% | ✅ 완료 |
| Sprint S8 | Brand Extractor | v0.8.0 | 16개 | 66개 | 100% | ✅ 완료 |
| Phase 6 | API & Integration | v1.0.0 | 52개 | 263개 | 100% | ✅ 완료 |
| Phase A1 | Industry Module | v0.3.0 | 14개 | 80개 | 100% | ✅ 완료 |
| Phase B | Industry Financial Metrics | v0.4.0 | 4개(+3수정) | 93개 | 100% | ✅ 완료 |
| Phase D1 | Valuation & Returns | v0.1.0 | 3개(+8수정) | 38개 | 100% | ✅ 완료 |
| Phase D2 | Korea Overlay | v0.1.0 | 5개(+4수정) | 33개 | 100% | ✅ 완료 |
| Phase E3 | Testing Enhancement | v0.1.0 | 2개(+1수정) | 30개 | 100% | ✅ 완료 |
| Phase E4 | Image Optimizer | v0.1.0 | 1개(+2수정) | 8개 | 100% | ✅ 완료 |

**코드 통계**: 237 소스 파일 / 129개 테스트 파일 / 1289 테스트 (전체 통과)

---

## 3. 완료된 모듈 상세

### Phase 2: Data Ingestor (v0.2.1) ✅

- DART API 클라이언트 (비동기, Rate Limiting 분당 100건, Circuit Breaker)
- PDF/Excel 파서 (PyMuPDF, openpyxl)
- 웹 크롤러 (Playwright 기반 JS 렌더링, 네이버/구글 뉴스, IR 문서)
- CacheManager (Redis 폴백), DataAggregator (Builder 패턴)
- 우선순위: REQUIRED / IMPORTANT / OPTIONAL

### Phase 3 + B: Financial Engine (v0.4.0) ✅

- StandardAccount enum (85개 계정, 한국어 매핑 376건)
- Fuzzy 매칭 (rapidfuzz 90%+ 정확도)
- 단위 변환 (천원/백만원/억원 → 원), 통화 변환 (USD/EUR → KRW)
- 수익성 지표: GPM, OPM, NPM, ROA, ROE
- 성장성 지표: YoY, 3Y/5Y CAGR
- 현금흐름: EBITDA, FCF, NWC
- 재무 건전성 검증 (A = L + E), 다기간 일관성 검증
- **산업별 재무 지표 (Phase B)**:
  - SaaS: ARR, MRR, NRR, Gross/Net Churn, LTV, CAC, LTV/CAC, Rule of 40, CAC Payback
  - 제조업: OEE, CAPA 가동률, 수율, 재고회전율, CAPEX/Revenue
  - 헬스케어: rNPV, 단계별 성공률, 특허 잔여기간, R&D/Revenue
  - 물류: 정시 배송률, Fleet 가동률, 톤km당 매출, 건당 비용
- Processor 통합: `industry_id` 파라미터로 산업별 계산기 자동 디스패치

### Phase 4: Design Renderer (v0.4.0) ✅

- PPTX: 마스터 템플릿 엔진, 18개 섹션 렌더러, Slide Factory, TOC 빌더
- PDF: HTML→PDF 변환 (Playwright + WeasyPrint 이중 엔진), CSS 생성기
- 시각 컴포넌트: 재무 테이블, KPI 카드, 타임라인, 조직도, 차트 임베딩
- 보안: PDF 암호화 (AES-256), 워터마크, PPTX 편집 제한 (SHA-512)
- 디자인 토큰: AMIC 브랜딩 (Dark Green #0F3A32, Green #26C260)
- 스타일 프리셋: TITAN (5섹션) / COVENANT (6섹션) / FULL (18섹션)

### Phase 5: Narrative Generator (v0.5.0) ✅

- RAG 파이프라인: DocumentChunker → TextEmbedder → VectorStore → ContextRetriever (MMR 리랭킹)
- 프롬프트 체계: 15개 섹션별 BasePrompt 구현 + PromptRegistry
- 산업별 변형: tech (ARR/MRR/NRR), healthcare (R&D), manufacturing (CAPEX), financial_services (NIM/NPL)
- 엔진: NarrativeOrchestrator (8단계 파이프라인), TokenBudgetManager, 구조화 출력 파싱
- Fact Checker: FactValidator (수치 대조), ConsistencyChecker (섹션 간 일관성), ConfidenceScorer
- 한국어 금융: 80+ 용어 매핑 (영⇄한), ToneAdapter (Factual Optimism)
- 예외 계층: 13개 도메인별 예외 클래스

### Sprint S7: Chart Engine (v0.7.0) ✅

- Plotly 6종 차트: waterfall, combo, stacked_bar, donut, line, hbar + AMICThemeFactory
- Graphviz 3종 다이어그램: org_chart, flow_diagram, shareholding
- DataTransformer: 재무/시장/주주 데이터 → ChartSpec 자동 변환
- PNG 내보내기 (Kaleido 300 DPI) + SVG 내보내기
- design_renderer 하위 호환: chart_embed.py · org_chart.py thin adapter 유지

### Sprint S8: Brand Extractor (v0.8.0) ✅

- 3단계 우선순위 체인: Brandfetch API → Website crawl → AMIC fallback
- 로고 파이프라인: LogoDetector (og:image, favicon) → LogoScorer → LogoProcessor
- 색상 파이프라인: K-Means ColorExtractor → ColorClassifier (Primary/Secondary) → BrandTokenMapper
- 예외: BrandExtractorError, BrandfetchAPIError, LogoDetectionError, ColorExtractionError, WebsiteAccessError
- 테스트: 13개 파일, 66개 테스트 (전체 통과)

### Phase 6: API & Integration (v1.0.0) ✅

- **Sprint S9 Foundation**: FastAPI create_app 팩토리, APIConfig (Pydantic Settings), SQLAlchemy 2.0 async (User/Document/Company/APIKey 모델), /health + /ready 엔드포인트 — 61 tests
- **Sprint S10 Auth + Celery**: JWT RS256/HS256 듀얼 인증, API 키 SHA-256, RBAC (ADMIN/MANAGER/USER), Celery chord 5단계 파이프라인, ProgressTracker — 83 tests
- **Sprint S11 Routes + Deployment**: Pydantic v2 스키마, documents/companies 라우트, DocumentService/CompanyService/WebhookService, CORS/Rate Limit/Logging 미들웨어, Dockerfile (multi-stage) + docker-compose (5 services) — 63 tests
- **Sprint S11+ Auth/User/APIKey Routes**: auth (login/refresh/logout), users (CRUD + RBAC 7개 엔드포인트), api-keys (create/list/revoke) — 49 tests 추가
- **인프라**: Alembic 마이그레이션 (4 테이블), CI/CD (GitHub Actions), Nginx, Gunicorn, 배포 스크립트
- **API 전체 테스트**: 28개 파일, 256개 테스트 (전체 통과)

### Phase A1: Industry Module (v0.2.0) ✅

- IndustryModule ABC: `get_kpis()`, `get_financial_weights()`, `get_chart_recommendations()`, `get_narrative_variant()`
- Registry 패턴: `@register_industry` 데코레이터 + `INDUSTRY_REGISTRY` dict
- 4개 산업 모듈: TechSaaSModule, ManufacturingModule, HealthcareModule, LogisticsModule
- IMDocumentData 통합: `industry`, `industry_data` 필드 + 파이프라인 step 1.5
- 테스트: 22개 (전체 통과)

### Phase B: Industry Financial Metrics (v0.4.0) ✅

- SaaSMetrics: 10개 지표 (ARR, MRR, NRR, Gross/Net Churn, LTV, CAC, LTV/CAC, Rule of 40, CAC Payback)
- ManufacturingMetrics: 5개 지표 (OEE, CAPA 가동률, 수율, 재고회전율, CAPEX/Revenue)
- HealthcareMetrics: 4개 지표 (rNPV, 단계별 성공률, 특허 잔여기간, R&D/Revenue)
- LogisticsMetrics: 4개 지표 (정시 배송률, Fleet 가동률, 톤km당 매출, 건당 비용)
- Processor 통합: `process()` → `_calculate_industry_metrics()` 디스패치 (4개 산업)
- IndustryMetrics 타입 별칭: `SaaSMetrics | ManufacturingMetrics | HealthcareMetrics | LogisticsMetrics`
- 테스트: 93개 추가 (B1: 32, B2: 20, B3: 37, B4: 4)

### Phase D1: Valuation & Returns (v0.1.0) ✅

- ValuationMetrics calculator: EV/EBITDA, P/E, EV/Revenue 멀티플 산출
- IRR 솔버: pure Python Newton-Raphson 반복법
- MOIC 계산, Exit Analysis (3개 시나리오: Base/Bull/Bear)
- Processor 통합: `process(valuation_config=...)` Step 4f
- ValuationRenderer: 5-slide (KPI summary, IRR/MOIC table, heatmap chart, waterfall chart, exit comparison)
- 테스트: 38개 추가 (전체 통과)

### Phase D2: Korea Overlay (v0.1.0) ✅

- 규제 항목 14개 (4 공통 + 산업별), K-IFRS 조정사항 8개
- 노동법 6개, ESG 요구사항 8개 (KCGS/TCFD/K-Taxonomy/CSRD)
- `get_korea_overlay_data()` 산업별 필터링 집계 함수
- IndustryModule.get_korea_overlay() concrete 메서드
- 물류 산업 용어 30개 추가 (terminology.py)
- 테스트: 33개 추가 (전체 통과)

### Phase E3: Testing Enhancement (v0.1.0) ✅

- PPTX XML 구조 검증 테스트 (lxml 기반 shape/font/color 검증)
- Golden file 스냅샷 테스트 (`--update-golden` CLI 옵션)
- 테스트: 30개 추가 (전체 통과)

### Phase E4: Image Optimizer (v0.1.0) ✅

- compress_png: Pillow 기반 PNG 압축 (품질/크기 설정)
- optimize_pptx_images: PPTX 내 이미지 일괄 최적화
- 테스트: 8개 추가 (전체 통과)

---

## 4. 잔여 작업 (~1개 항목)

> 모든 백엔드 모듈 및 인프라 구현 완료. 프론트엔드만 남음.

### 4.1 인증 및 사용자 관리 라우트 ✅ 완료

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

### 4.2 Alembic 마이그레이션 ✅ 완료

- [x] `alembic/` 디렉토리 생성 (async 환경)
- [x] `alembic/env.py` 설정 (SQLAlchemy async 연동)
- [x] 초기 마이그레이션 생성 (`001_initial_schema.py` — users, api_keys, companies, documents 4개 테이블)

### 4.3 CI/CD ✅ 완료 / 프론트엔드 ❌ 미구현

- [x] GitHub Actions CI 워크플로우 (lint + test + build)
- [x] GitHub Actions CD 워크플로우 (staging + production deploy)
- [ ] **프론트엔드 웹 UI** (현재 REST API만 존재, `docs/plans/unified-frontend-integration-plan.md` 참조)

---

## 5. 완료된 인프라

### 배포 환경

- **Docker**: `Dockerfile` (multi-stage, python:3.11-slim) + `docker-compose.yml` (5 서비스) + `docker-compose.production.yml`
- **Nginx**: `nginx/conf.d/` 리버스 프록시 설정
- **Gunicorn**: `gunicorn.conf.py` WSGI 서버 설정
- **배포 스크립트**: `scripts/` (backup-db.sh, health-check.sh, generate-self-signed.sh, init-letsencrypt.sh, renew-ssl.sh)
- **환경 템플릿**: `.env.example`, `.env.staging.example`, `.env.production.example`

### CI/CD 파이프라인

- **CI** (`.github/workflows/ci.yml`): Black + Flake8 + MyPy → pytest + coverage → Docker build
- **CD** (`.github/workflows/cd.yml`): GHCR push → SSH deploy (staging: main push, production: tag push)

---

## 6. 의존 관계 (전체 완료)

```text
[Data Ingestor] ──┐
                   ├──→ [Narrative Generator] ──→ [API & Integration] ✅
[Financial Engine] ┘         │
        │                    ↓
        ▼          [Design Renderer] ←── [Chart Engine] ✅
[Industry Module] ✅                           │
        │                           [Brand Extractor] ✅
        ▼
[Industry Financial Metrics] ✅
```

---

## 7. 프로덕션 준비 체크리스트

- [x] 1289 테스트 전체 통과 확인 (2026-02-11)
- [x] 인증 라우트 구현 (login, refresh, logout, users, api-keys)
- [x] Alembic 마이그레이션 생성
- [x] CI/CD 파이프라인 구성 (GitHub Actions)
- [x] Docker 프로덕션 환경 구성
- [ ] `.env` 파일에 실제 API 키 설정 (DART_API_KEY, OPENAI_API_KEY, PINECONE_API_KEY, BRANDFETCH_API_KEY)
- [ ] Docker 빌드 테스트 (`docker-compose up`)
- [ ] GitHub Actions 시크릿 설정 (STAGING_HOST, PROD_HOST, SSH_KEY)
- [ ] 프론트엔드 웹 UI 구현

---

## 8. 참고 문서

- [PLAN.md](../../PLAN.md) — 통합 개발 계획 (S1-S11 + A1 + B + D1-D2 + E3-E4, 155+ 티켓)
- [SPEC.md](../../SPEC.md) — 시스템 사양
- [CLAUDE.md](../../CLAUDE.md) — 개발 규칙
- `docs/plans/` — 스프린트별 상세 계획 (9개 파일)
