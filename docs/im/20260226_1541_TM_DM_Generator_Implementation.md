# TM/DM 생성기 구현 보고서

> 2026-02-26 15:41 작성

## 목표

IM 모듈의 TM(Teaser Memorandum)과 DM(Discussion Memorandum) 생성기를 IM 생성기와 동일한 5단계 Celery 파이프라인(수집→분석→내러티브→렌더링→완료)으로 동작하도록 구현.

---

## 1. DM (Discussion Memorandum) — 신규 구현

### 구조 (8슬라이드)

| # | Section ID | 슬라이드 제목 | 렌더러 |
|---|-----------|-------------|--------|
| 1 | `cover` | Cover | 기존 CoverRenderer 재사용 |
| 2 | `dm_market_trends` | Market & Transaction Trends | **신규** |
| 3 | `dm_deal_structure` | Deal Structure Considerations | **신규** |
| 4 | `dm_investment_thesis` | Investment Thesis | **신규** |
| 5 | `dm_valuation` | Valuation Analysis | **신규** (자체 구현) |
| 6 | `dm_risk_assessment` | Risk Assessment | **신규** |
| 7 | `dm_summary` | Summary & Recommendations | **신규** |
| 8 | `contact` | Contact | 기존 ContactRenderer 재사용 |

### 구현 내역

| 구분 | 파일 | 변경 |
|------|------|------|
| 데이터 모델 | `im/src/design_renderer/im_document.py` | IMStyle.DM, DM_SECTION_IDS, DM_SECTIONS, ALL_SECTION_IDS, __post_init__ DM 분기 |
| 렌더러 6개 | `im/src/design_renderer/section_renderers/dm_*.py` | 신규 6파일 |
| 렌더러 등록 | `im/src/design_renderer/section_renderers/__init__.py` | DM import 블록 + __all__ |
| 프롬프트 5개 | `im/src/narrative_generator/prompts/section_prompts/discussion.py` | 신규 (투자위원회용 분석적 어조) |
| 프롬프트 등록 | `im/src/narrative_generator/prompts/__init__.py` | DM 5개 등록 (총 28개: IM 15 + TM 8 + DM 5) |
| API 스키마 | `im/src/api/schemas/documents.py` | `_VALID_IM_STYLES`에 "DM" 추가 |
| 파이프라인 | `im/src/design_renderer/pipeline.py` | 독스트링만 업데이트 (로직 변경 없음) |
| 프론트 타입 | `amic-platform/src/modules/im/types/document.ts` | IMStyle, SectionId, SECTION_LABEL_MAP에 DM 추가 |
| 프론트 페이지 | `amic-platform/src/modules/im/pages/CreateDocumentPage.tsx` | DM 스타일 옵션 |
| 프론트 페이지 | `amic-platform/src/modules/im/pages/CreateFromVdrPage.tsx` | DM 스타일 옵션 |
| 테스트 | `im/tests/test_design_renderer/test_dm_pipeline.py` | 신규 47개 테스트 |

### 파이프라인 동작

DM은 표준 순차 렌더링(for loop)을 사용. TM 전용 2-pass TOC는 `if data.im_style == IMStyle.TEASER` 분기이므로 DM에 영향 없음. 기존 파이프라인 로직 변경 불필요.

---

## 2. TM (Teaser Memorandum) — 버그 수정 + 테스트 추가

### 기존 구현 현황 (이미 완료)

- 8개 TM 전용 렌더러 (target_positioning, market_outlook, demand_driver, supply_driver, target_overview, target_highlights, proforma_plan, proforma_financials)
- 8개 TM 프롬프트 (`teaser.py`)
- 2-pass TOC 렌더링 파이프라인 (`_render_tm_sections`)
- 4개 그룹 구조 (Executive Summary → Market Opportunity → Target Highlights → Financial Summary)
- 프론트엔드 TEASER 옵션

### 발견된 버그 (2건)

#### 버그 1: `shape_bottom_inches` ImportError

`shape_builder.py`에 정의되지 않은 `shape_bottom_inches` 함수를 TM 렌더러 3개 파일 12곳에서 import/사용 → PPTX 렌더링 시 즉시 크래시.

| 파일 | 영향 범위 |
|------|----------|
| `tm_aliases.py` | import 2곳 + 사용 2곳 |
| `target_positioning.py` | import 1곳 + 사용 1곳 |
| `market_drivers.py` | import 3곳 + 사용 3곳 |

**수정**: `shape_builder.py`에 유틸 함수 1개 추가.

```python
def shape_bottom_inches(shape: Any) -> float:
    """shape 하단 위치를 inches로 반환 — (top + height) / 914400 EMU."""
    return (shape.top + shape.height) / 914400
```

이 1줄 함수 추가로 TM 3개 파일이 **코드 변경 없이** 동작.

#### 버그 2: `render_html()` NotImplementedError

`TargetOverviewRenderer`와 `TargetHighlightsRenderer`의 `render_html()`이 각각 `CompanyOverviewRenderer`, `BusinessOverviewRenderer`에 위임하는데, 위임 대상이 `NotImplementedError("PDF output removed")`를 발생시킴.

**수정**: 두 렌더러의 `render_html()`을 자체 구현으로 전환.
- `TargetOverviewRenderer`: 회사 정보 카드 + 내러티브 + 제품 리스트
- `TargetHighlightsRenderer`: 내러티브 + 고객 리스트

### 추가 개선: DM 렌더러 동적 레이아웃 복원

DM 구현 시 `shape_bottom_inches` 부재로 `y += 0.6` 고정 오프셋을 사용했으나, 함수 추가 후 5개 DM 렌더러를 동적 레이아웃(`y = shape_bottom_inches(shape) + 0.1`)으로 복원.

### TM 수정 파일

| 구분 | 파일 | 변경 |
|------|------|------|
| 유틸 추가 | `im/src/design_renderer/pptx_engine/shape_builder.py` | `shape_bottom_inches()` 함수 1개 추가 |
| TM 렌더러 | `im/src/design_renderer/section_renderers/tm_aliases.py` | `render_html()` 2개 자체 구현으로 전환 |
| DM 렌더러 5개 | `im/src/design_renderer/section_renderers/dm_*.py` | 동적 레이아웃 복원 |
| 테스트 | `im/tests/test_design_renderer/test_tm_pipeline.py` | 신규 60개 테스트 |

---

## 3. 테스트 결과

| 테스트 스위트 | 결과 | 시간 |
|-------------|------|------|
| TM 파이프라인 (`test_tm_pipeline.py`) | **60/60 통과** | 0.89s |
| DM 파이프라인 (`test_dm_pipeline.py`) | **47/47 통과** | 0.78s |
| **합계** | **107/107 통과** | 1.02s |

### TM 테스트 구성 (60개)

- 데이터 모델: 4개 (TEASER_SECTIONS 프리셋, 구조, 활성 섹션, DM 미포함)
- 렌더러 등록: 16개 (8 section_id × 등록 + 인스턴스)
- PPTX 렌더러: 16개 (8 section_id × 최소/전체 데이터)
- HTML 렌더러: 16개 (8 section_id × 최소/전체 데이터)
- 파이프라인 통합: 2개 (전체/최소 데이터 → 17슬라이드 이상)
- 회귀: 3개 (FULL/DM/TITAN 스타일 불변)
- 프롬프트: 3개 (등록/extract_data/토큰 범위)

### DM 테스트 구성 (47개)

- 데이터 모델: 3개
- 렌더러 등록: 12개
- PPTX 렌더러: 12개
- HTML 렌더러: 12개
- 파이프라인 통합: 2개 (8슬라이드 정확)
- 회귀: 3개 (FULL/TEASER/TITAN 불변)
- 프롬프트: 3개

### 기존 테스트 (297 passed, 20 failed)

20개 실패는 모두 기존 이슈 (TM/DM 변경과 무관):
- `ValuationRenderer.render_html()` NotImplementedError (5개)
- golden snapshot 불일치 (4개)
- fallback renderer 관련 (3개)
- 레지스트리 카운트 불일치 (3개)
- E2E 파이프라인 (2개)
- industry section ID (1개)
- 기타 (2개)

---

## 4. 아키텍처 요약

### IM 모듈 렌더러 전체 구성 (32종)

| 카테고리 | 렌더러 수 | 섹션 |
|---------|----------|------|
| IM 공통 | 18종 | cover, disclaimer, toc_divider, deal_overview, executive_summary, investment_highlights, company_overview, business_model, market_overview, business_overview, value_creation, growth_strategy, financial_analysis, valuation, management_team, shareholder_structure, transaction_structure, contact |
| TM 전용 | 8종 | target_positioning, market_outlook, demand_driver, supply_driver, target_overview, target_highlights, proforma_plan, proforma_financials |
| DM 전용 | 6종 | dm_market_trends, dm_deal_structure, dm_investment_thesis, dm_valuation, dm_risk_assessment, dm_summary |

### 프롬프트 전체 구성 (28종)

| 카테고리 | 프롬프트 수 | 어조 |
|---------|-----------|------|
| IM | 15종 | 투자 제안서 (공식적, 설득적) |
| TM | 8종 | 마케팅 (투자자 초청용) |
| DM | 5종 | 분석적 (내부 투자위원회용) |

### 파이프라인 분기

```
IMPipeline.generate(data)
├── TEASER → _render_tm_sections() [2-pass TOC, 4그룹]
├── DM → 표준 for loop [순차, 8슬라이드]
└── TITAN/COVENANT/FULL/CUSTOM → 표준 for loop [순차]
```

---

## 5. DB 마이그레이션

불필요. `im_style`은 VARCHAR, `sections`는 JSONB — 새 enum 값은 애플리케이션 레벨에서만 처리.
