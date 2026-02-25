# IM (Information Memorandum) 리포트 생성 워크플로우 분석

> 2026-02-17 02:34 | IM 모듈 백엔드 파이프라인 + 프론트엔드 UI 구현 현황

---

## 1. 시스템 개요

IM 모듈은 한국 상장기업의 **투자유치/M&A용 기업소개서(Information Memorandum)를 자동 생성**하는 엔드-투-엔드 시스템입니다. DART 공시 API + 웹 크롤링을 통한 자동 데이터 수집, LLM 멀티 프로바이더를 활용한 내러티브 자동 생성, PPTX/PDF 듀얼 출력을 제공합니다.

---

## 2. 전체 파이프라인 개요

```
사용자 입력 → API 요청 → Celery 비동기 파이프라인 (5단계) → 파일 다운로드

[Stage 1] 데이터 수집 (병렬)     → 25%
[Stage 2] 재무 분석              → 40%
[Stage 3] 내러티브 LLM 생성      → 55~70%
[Stage 4] PPTX/PDF 렌더링       → 80~95%
[Stage 5] 완료 처리              → 100%
```

---

## 3. Stage 0: 사용자 입력

**엔드포인트:** `POST /api/v1/documents` → 202 Accepted

| 항목 | 설명 | 필수 |
|------|------|------|
| `corp_code` | DART 법인코드 8자리 | O |
| `project_name` | 프로젝트명 | X |
| `im_style` | TITAN / COVENANT / FULL / CUSTOM | O |
| `sections` | 포함할 섹션 ID 리스트 (CUSTOM만) | 조건부 |
| `industry` | tech / healthcare / manufacturing / logistics / financial_services | O |
| `pdf_password` | PDF 암호화 비밀번호 (4자 이상) | X |
| `webhook_url` | 완료 시 호출할 웹훅 | X |

**UI:** `CreateDocumentPage.tsx` — 3단계 위자드
- Step 0: 회사 선택 (법인코드 → DART 조회)
- Step 1: IM 설정 (스타일, 산업, 섹션)
- Step 2: 확인 + PDF 비밀번호

---

## 4. Stage 1: 데이터 수집 (Celery Chord — 병렬 3태스크)

**상태:** `COLLECTING`, **진행률:** 0% → 25%

| 태스크 | 소스 | 수집 데이터 | 재시도 |
|--------|------|------------|--------|
| `fetch_dart_task` | DART 공시 API | 기업정보, 재무제표(3~5년), 주주정보, 배당정보 | 3회 |
| `fetch_web_task` | 웹 크롤링 | 뉴스, 회사 추가정보 | 3회 |
| `extract_brand_task` | Brandfetch API | 로고 URL, 브랜드 컬러 | 3회 (비필수) |

3개 태스크 **동시 실행** → `merge_collected_data`에서 결과 병합.

**핵심 파일:**
- `im/src/data_ingestor/pipeline.py`
- `im/src/data_ingestor/dart/client.py`

---

## 5. Stage 2: 재무 분석

**상태:** `ANALYZING`, **진행률:** 25% → 40%

1. 재무제표 정규화 (한국 회계 규칙, KRW 단위 통일)
2. 계정과목 매핑 (한국 표준)
3. 균형 검증 (자산 = 부채 + 자본)
4. **파생지표 산출:**
   - 수익성: ROE, ROA, 영업마진율, 순마진율
   - 성장: YoY 성장률, 3년 CAGR
   - 유동성: 유동비율, 당좌비율
   - 레버리지: 부채비율, 이자보상배수

**핵심 파일:**
- `im/src/financial_engine/processor.py`
- `im/src/financial_engine/calculator/`

---

## 6. Stage 3: 내러티브 생성 (LLM) — 핵심 단계

**상태:** `GENERATING`, **진행률:** 40% → 70%

### 처리 흐름 (섹션별 반복)

```
14개 콘텐츠 섹션 각각에 대해:
  1. 프롬프트 조회 (PromptRegistry)
  2. RAG 컨텍스트 검색 (Pinecone, 선택적)
  3. 시스템/유저 프롬프트 조립 (산업별 컨텍스트 포함)
  4. LLM 호출 (ModelRouter → OpenAI/Anthropic/Google 중 선택)
  5. 응답 파싱 (JSON 구조화 → SectionNarrative)
  6. 토큰 예산 검사 (초과 시 자르기)
  7. 팩트 체크 (수치 정합성 검증)
  8. 신뢰도 평가 (confidence scoring, 임계값 0.7)
→ 모든 섹션 완료 후: 섹션 간 일관성 검사
```

### 멀티-LLM 라우팅

- `ModelRouter`가 섹션별 최적 프로바이더 선택
- 폴백 순서: OpenAI → Anthropic → Google
- 비용 추적: 프로바이더별 토큰 사용량 + 누적 비용

### 14개 콘텐츠 섹션

executive_summary, company_overview, market_overview, business_overview, financial_analysis, growth_strategy, investment_highlights, business_model, market_opportunity, competitive_positioning, value_creation, management_team, transaction_structure, shareholder_structure

### NarrativeConfig 주요 설정

```python
narrative_model_name: str = "gpt-4o"
anthropic_model_name: str = "claude-sonnet-4-5-20250929"
google_model_name: str = "gemini-2.0-flash"
narrative_temperature: float = 0.3
narrative_max_tokens: int = 4096
fact_check_enabled: bool = True
confidence_threshold: float = 0.7
```

**핵심 파일:**
- `im/src/narrative_generator/engine/orchestrator.py`
- `im/src/narrative_generator/engine/model_router.py`
- `im/src/narrative_generator/config.py`
- `im/src/narrative_generator/prompts/`

---

## 7. Stage 4: 문서 렌더링 (PPTX + PDF)

**상태:** `RENDERING`, **진행률:** 70% → 95%

### PPTX 생성 (python-pptx)

18개 섹션 순차 렌더링 → 한글 폰트(NanumGothic) 적용 → 스타일/워터마크 → 저장

### PDF 생성 (WeasyPrint)

HTML/CSS 생성 (Jinja2 + 디자인 토큰) → WeasyPrint PDF 변환 → 암호화/편집 제한

### 18개 섹션 렌더러

| # | 섹션 | 내용 |
|---|------|------|
| 1 | cover | 표지 (회사명, 프로젝트명, 로고) |
| 2 | disclaimer | 면책 문구 |
| 3 | toc_divider | 목차 구분선 |
| 4 | executive_summary | 핵심 수치 + 투자 포인트 |
| 5 | company_overview | 회사 개요 |
| 6 | business_overview | 사업 개요 |
| 7 | market_overview | 시장 현황 |
| 8 | business_model | 비즈니스 모델 |
| 9 | investment_highlights | 투자 하이라이트 |
| 10 | financial_analysis | 재무 분석 (차트, 표) |
| 11 | growth_strategy | 성장 전략 |
| 12 | value_creation | 가치 창출 |
| 13 | market_opportunity | 시장 기회 |
| 14 | competitive_positioning | 경쟁 포지셔닝 |
| 15 | management_team | 경영진 |
| 16 | transaction_structure | 거래 구조 |
| 17 | shareholder_structure | 주주 구성 |
| 18 | contact | 연락처 |

**핵심 파일:**
- `im/src/design_renderer/pipeline.py`
- `im/src/design_renderer/section_renderers/`

---

## 8. Stage 5: 완료 처리

**상태:** `COMPLETED`, **진행률:** 100%

- DB 업데이트 (pptx_path, pdf_path, completed_at)
- Webhook 호출 (설정된 경우)

---

## 9. 진행률 추적 메커니즘

1. **Celery 상태 업데이트:** `update_state(state=stage, meta={...})`
2. **DB Document 업데이트:** 동기 엔진으로 직접 UPDATE
3. **클라이언트 폴링:** 3초 간격 `GET /documents/{id}` → refetchInterval

**상태 전이:** `PENDING → COLLECTING → ANALYZING → GENERATING → RENDERING → COMPLETED (또는 FAILED)`

---

## 10. 에러 처리

| 태스크 | max_retries | 백오프 |
|--------|------------|--------|
| fetch_dart_task | 3 | 30s × (n+1) |
| fetch_web_task | 3 | 30s × (n+1) |
| extract_brand_task | 3 | 30s × (n+1) |
| analyze_financials_task | 3 | 30s × (n+1) |
| generate_content_task | 2 | 30s × (n+1) |
| render_document_task | 2 | 30s × (n+1) |
| finalize_document_task | 0 | (없음) |

2중 안전장치: `PipelineTask.on_failure` + Chord/Chain `on_error` 콜백

---

## 11. UI 페이지 구현 현황

| 워크플로우 단계 | UI 페이지 | 구현 상태 |
|---------------|----------|----------|
| 문서 목록 조회 | `DocumentListPage.tsx` | ✅ 완전 구현 (KPI, 필터, 페이지네이션) |
| 템플릿 선택 | `TemplatesPage.tsx` | ✅ 완전 구현 (4개 템플릿 카드) |
| 생성 위자드 | `CreateDocumentPage.tsx` | ✅ 완전 구현 (3단계 위자드) |
| 진행 모니터링 | `DocumentDetailPage.tsx` | ✅ 완전 구현 (6단계 진행률 + 3초 폴링) |
| 파일 다운로드 | DocumentDetailPage 내 | ✅ 완전 구현 (PPTX/PDF, 한글 파일명) |
| 샘플 페이지 | `SamplePage.tsx` | ✅ 완전 구현 (개발용) |
| 갤러리 | `GallerySamplePage.tsx` | ❌ 미구현 (라우트만 정의) |

**사용자 플로우:** 목록 → 생성 위자드 → 모니터링 → 다운로드 **100% 구현 완료**

---

## 12. 핵심 특징

- **완전 자동 파이프라인**: 한번 시작하면 끝까지 자동 진행
- **멀티-LLM 라우팅**: 섹션별 최적 모델 선택 + 폴백 체인
- **산업별 맞춤**: 프롬프트 컨텍스트 수준에서 산업별 차별화
- **DART API 캐싱**: 동일 기업 반복 호출 시 대역폭 절감
- **토큰 예산 관리**: 섹션별 토큰 한도 + 비용 한도
- **보안**: PDF 암호화, 편집 제한, 권한 검증
