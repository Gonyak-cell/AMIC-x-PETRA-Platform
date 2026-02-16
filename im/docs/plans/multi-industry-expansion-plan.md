# IM Module 다산업 확장 및 기술 개선 계획

> 작성일: 2026-02-11 10:00:00
> 최종 수정: 2026-02-11 11:46:11
> 기반 문서: 모듈식 설계 전략 리서치, 기술 전략 리서치
> 상태: **Phase A1 + B 구현 완료 — 나머지 구현 대기**
>
> **문서 관리 규칙**: 본 문서 업데이트 시 PowerShell `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'`로 현재 시각을 확인하여 "최종 수정" 필드에 `yyyy-MM-dd HH:mm:ss` 형식으로 기재한다.

---

## 1. Context

### 1-1. 배경

두 개의 리서치 문서를 기반으로 현재 auto-im-generator 시스템을 업데이트하는 계획이다.

- **문서 1 (모듈식 설계 전략)**: PE IM의 공통 뼈대(12섹션, 60-70%) + 산업별 모듈(30-40%) 구조 정의. 제조업/IT-SaaS/헬스케어/물류 4개 산업별 고유 KPI, 슬라이드 구성, Value Creation 전략, 리스크 요인 상세화. 한국 PE 시장 특수성(규제, 재벌 카브아웃, 노동 리스크) Korea Overlay Module 제안.
- **문서 2 (기술 전략)**: python-pptx 한글 폰트 a:ea 누락 문제, 대규모 PPTX 성능, 에러 처리/매니페스트, 테스팅 전략(구조/시각/스냅샷/골든파일), 새 차트 타입(퍼널, 히트맵) 필요성.

### 1-2. 현재 시스템 상태

| 항목 | 수량 |
| --- | --- |
| 소스 파일 | 215 |
| 테스트 | 1180 (전체 통과) |
| 섹션 렌더러 | 18 (+2 산업별) |
| 차트 타입 | 6 (waterfall, combo, stacked_bar, donut, line, hbar) |
| 산업 변형 | 4 (tech, healthcare, manufacturing, logistics) — narrative + module + 재무 지표 |
| 재무 계산기 | 8 (profitability, growth, cash_flow, leverage + saas, manufacturing, healthcare, logistics) |

### 1-3. 결정 사항

- **구현 범위**: 전체 5 Phase 순차 구현 (E1->E2->C->A->B->D->E3->E4)
- **산업 구성**: 기존 financial_services 유지 + logistics 신규 추가 -> 총 5개 산업 (tech, healthcare, manufacturing, financial_services, logistics)

### 1-4. 코드베이스 검증 결과 — E1, E2 이미 구현 완료

코드베이스 탐색 결과, 원래 계획의 Phase E1과 E2는 이미 구현되어 있음을 확인했다.

| Phase | 상태 | 근거 |
| --- | --- | --- |
| E1: 한글 폰트 a:ea | **구현 완료** | `src/design_renderer/pptx_engine/font_helper.py` (163줄)에 `set_font_with_ea()`, `ensure_ea_fonts_on_slide()`, `ensure_ea_fonts_on_presentation()` 구현. `shape_builder.py`, `kpi_card.py` 전체에서 `set_font_with_ea()` 사용. `pipeline.py`에서 `ensure_ea_fonts_on_presentation()` 후처리 호출. `test_font_helper.py`에 16개 테스트 존재. |
| E2: 에러 처리 & 매니페스트 | **구현 완료** | `src/design_renderer/manifest.py` (151줄)에 `GenerationManifest` + `SlideManifestEntry` 구현. `section_renderers/fallback.py` (125줄)에 PPTX + HTML 폴백 슬라이드 생성. `pipeline.py`에 섹션별 try/catch + `continue_on_error=True` + 매니페스트 추적. |

**따라서 E1, E2를 제거하고 나머지 Phase만 실행한다.**

---

## 2. 정제된 실행 순서

```text
Phase C  (차트 4종)     ─┬─ 병렬 시작 가능
Phase A1 (산업 인프라)   ─┘  ✅ 완료 (v0.1.0)
                          ↓
Phase A2 (산업 모듈 4종 + 물류 내러티브 + 렌더러)  ← A1 의존  ✅ 완료
                          ↓
Phase B  (산업별 재무 계산기)                      ← A2 의존  ✅ 완료 (v0.4.0)
                          ↓
Phase D1 (밸류에이션) ─┬─ 병렬 가능               ← B, C 의존
Phase D2 (Korea Overlay) ─┘                       ← A2 의존
                          ↓
Phase E3 (테스트 강화) ─┬─ 병렬 가능              ← 전체 기능 완료 후
Phase E4 (이미지 최적화) ─┘
```

---

## 3. Phase A: 산업 모듈 시스템 (Industry Module System) — ✅ A1 + A2 완료

**목표**: 산업별 지원을 내러티브 전용 -> 전체 파이프라인(렌더링, 차트, 재무, 섹션 구성)으로 확장

### 3-1. A1: 산업 인프라 레이어 (Foundation) — ✅ 완료 (v0.1.0, 22 tests)

**의존성**: 없음 (Phase C와 병렬 시작 가능)
**참조 패턴**: `src/design_renderer/section_renderers/__init__.py`의 `@register_renderer` + `RENDERER_REGISTRY`

#### 산업 레지스트리 & 설정 모델 생성

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 생성 | `src/industry/__init__.py` | 패키지 초기화 + exports |
| 생성 | `src/industry/registry.py` | `IndustryModuleRegistry`, `@register_industry` 데코레이터 |
| 생성 | `src/industry/base.py` | `IndustryModule` ABC — `get_kpis()`, `get_financial_weights()`, `get_chart_recommendations()`, `get_narrative_variant()` |
| 생성 | `src/industry/models.py` | `IndustryKPI`, `IndustryContext`, `IndustryChartRecommendation`, `RiskCategory` dataclass |
| 생성 | `src/industry/exceptions.py` | `IndustryError`, `UnsupportedIndustryError` |

#### 핵심 설계

```python
# src/industry/base.py
class IndustryModule(ABC):
    """산업 모듈 추상 기반 클래스."""

    industry_id: str
    industry_name_kr: str
    industry_name_en: str

    @abstractmethod
    def get_kpis(self) -> list[IndustryKPI]:
        """산업별 핵심 KPI 정의 반환."""

    @abstractmethod
    def get_financial_weights(self) -> dict[str, float]:
        """산업별 재무 지표 가중치 반환."""

    @abstractmethod
    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        """산업별 추천 차트 사양 반환."""

    @abstractmethod
    def get_narrative_variant(self) -> IndustryVariant:
        """기존 내러티브 변형 객체 반환."""
```

#### IMDocumentData 수정

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 수정 | `src/design_renderer/im_document.py` | `IMDocumentData`에 `industry: str = ""`, `industry_data: dict[str, Any]` 필드 추가. `SECTION_IDS`에 산업별 섹션 ID 추가. `get_active_sections()`이 산업별 섹션도 포함하도록 수정. |

#### 산업별 섹션 렌더러 기반

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 수정 | `src/design_renderer/section_renderers/__init__.py` | 산업별 렌더러 conditional import + 레지스트리 등록 |
| 수정 | `src/design_renderer/pipeline.py` | `IMPipeline.generate()`에서 industry 모듈 resolve -> 산업별 섹션 merge |

**예상**: ~7 파일 (5 생성, 2 수정), ~15 테스트

---

### 3-2. A2: 4개 산업 모듈 구현 — ✅ 완료 (4개 산업 + 렌더러 + 물류 내러티브)

**의존성**: A1 완료 필수
**참조 패턴**: `src/narrative_generator/prompts/industry_variants/tech.py` (TechVariant)

#### 산업 모듈 4종

| 작업 | 파일 | 핵심 섹션/KPI |
| --- | --- | --- |
| 생성 | `src/industry/tech_saas.py` | ARR Bridge, NRR/Churn 대시보드, 코호트 분석, TAM/SAM/SOM 퍼널, 가격 최적화, GTM |
| 생성 | `src/industry/manufacturing.py` | CAPA/가동률, 원가구조 워터폴, 공급망 맵, CAPEX 분리, Lean/자동화, Buy-and-Build |
| 생성 | `src/industry/healthcare.py` | 파이프라인 차트, rNPV 밸류에이션, 임상 데이터, 특허 수명주기, 시장접근성 |
| 생성 | `src/industry/logistics.py` | 네트워크 맵, Fleet 프로파일, 운영 KPI(정시 배송률, 가동률), 자동화, 디지털 전환 |

#### 산업별 섹션 렌더러

| 작업 | 파일 | 대상 산업 |
| --- | --- | --- |
| 생성 | `src/design_renderer/section_renderers/industry_kpi.py` | 공통 (산업별 KPI 카드를 동적 구성) |
| 생성 | `src/design_renderer/section_renderers/industry_overview.py` | 공통 (산업별 운영 분석: 제조->CAPA, SaaS->ARR, 헬스케어->파이프라인, 물류->네트워크) |

#### 내러티브 물류 변형 추가

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 생성 | `src/narrative_generator/prompts/industry_variants/logistics.py` | `LogisticsVariant(IndustryVariant)` — 물동량, 3PL, 콜드체인 컨텍스트 |
| 수정 | `src/narrative_generator/prompts/industry_variants/__init__.py` | 물류 변형 등록 |

#### 수정 파일

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 수정 | `src/design_renderer/im_document.py` | `SECTION_IDS`에 `"industry_kpi"`, `"industry_overview"` 추가 (18 -> 20) |
| 수정 | `src/design_renderer/section_renderers/__init__.py` | 2개 신규 렌더러 import + 등록 |

**예상**: ~9 파일 (7 생성, 2 수정), ~40 테스트

---

## 4. Phase B: 산업별 재무 지표 (Industry Financial Metrics) — ✅ 완료 (93 tests)

**목표**: 기존 4종 calculator(profitability/growth/cash_flow/leverage) 외에 산업별 고유 지표 추가
**의존성**: A2 완료 필수
**참조 패턴**: `src/financial_engine/calculator/profitability.py` — `@dataclass(frozen=True)` result + 순수 함수형 계산기

### 4-1. B1: SaaS 지표

| 작업 | 파일 | 주요 지표 |
| --- | --- | --- |
| 생성 | `src/financial_engine/calculator/saas.py` | `SaaSMetrics` — ARR, MRR, NRR, Gross/Net Churn, LTV, CAC, LTV/CAC, Rule of 40, CAC Payback |

### 4-2. B2: 제조업 지표

| 작업 | 파일 | 주요 지표 |
| --- | --- | --- |
| 생성 | `src/financial_engine/calculator/manufacturing_metrics.py` | `ManufacturingMetrics` — OEE, 가동률, 수율, 재고회전율, CAPEX/Revenue, 유지보수 vs 성장 CAPEX |

### 4-3. B3: 헬스케어 & 물류 지표

| 작업 | 파일 | 주요 지표 |
| --- | --- | --- |
| 생성 | `src/financial_engine/calculator/healthcare_metrics.py` | `HealthcareMetrics` — rNPV, Phase별 성공률, 특허 잔여기간, R&D/Revenue, Pipeline Value |
| 생성 | `src/financial_engine/calculator/logistics_metrics.py` | `LogisticsMetrics` — 정시 배송률, Fleet 가동률, 톤km당 매출, 건당 비용, 창고 가동률 |

### 4-4. B4: 통합

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 수정 | `src/financial_engine/processor.py` | `ProcessingResult`에 `industry_metrics` 필드 추가. `process()`에 `industry_id` 파라미터 -> 조건부 산업 calculator 실행 |
| 수정 | `src/financial_engine/calculator/__init__.py` | 신규 계산기 export |

### 구현 패턴 (필수)

```python
@dataclass(frozen=True)
class SaaSMetrics:
    """SaaS 핵심 지표."""

    arr: dict[str, float | None]
    mrr: dict[str, float | None]
    nrr: dict[str, float | None]
    ltv_cac_ratio: dict[str, float | None]
    rule_of_40: dict[str, float | None]
    churn_rate: dict[str, float | None]


def calculate_saas_metrics(
    revenue: dict[str, Decimal | None],
    subscription_revenue: dict[str, Decimal | None],
    new_arr: dict[str, Decimal | None],
    churned_arr: dict[str, Decimal | None],
    expansion_arr: dict[str, Decimal | None],
    customer_count: dict[str, int | None],
    cac: dict[str, Decimal | None],
) -> SaaSMetrics:
    """SaaS 핵심 지표를 산출한다."""
```

**예상**: ~6 파일 (4 생성, 2 수정), ~60 테스트

---

## 5. Phase C: 새 차트 타입 (New Chart Types)

**목표**: 산업 모듈이 활용할 새 차트 타입 4종 추가 (기존 CHART_DISPATCH 패턴 준수)
**의존성**: 없음 (Phase A1과 병렬 시작 가능)
**참조 패턴**: `src/chart_engine/plotly/waterfall.py` — 표준 차트 시그니처

### 5-1. C1: 퍼널 차트 (Funnel)

| 작업 | 파일 | 용도 |
| --- | --- | --- |
| 생성 | `src/chart_engine/plotly/funnel.py` | TAM/SAM/SOM 퍼널, 영업 파이프라인, 환자 분류 |
| 수정 | `src/chart_engine/plotly/__init__.py` | `CHART_DISPATCH["funnel"] = create_funnel_chart` |
| 수정 | `src/chart_engine/data_transformer.py` | `transform_market()` — 퍼널 차트 자동 생성 옵션 |

### 5-2. C2: 민감도 히트맵 (Sensitivity Heatmap)

| 작업 | 파일 | 용도 |
| --- | --- | --- |
| 생성 | `src/chart_engine/plotly/sensitivity_heatmap.py` | IRR/MOIC 민감도 테이블, Entry/Exit Multiple 매트릭스 |
| 수정 | `src/chart_engine/plotly/__init__.py` | `CHART_DISPATCH["heatmap"] = create_sensitivity_heatmap` |

### 5-3. C3: 코호트 히트맵 & 트리맵

| 작업 | 파일 | 용도 |
| --- | --- | --- |
| 생성 | `src/chart_engine/plotly/cohort_heatmap.py` | SaaS 리텐션 코호트 분석 |
| 생성 | `src/chart_engine/plotly/treemap.py` | 매출 세그먼트 구성, 비용 구조 분해 |
| 수정 | `src/chart_engine/plotly/__init__.py` | `CHART_DISPATCH` 등록 |

### 구현 패턴 (필수)

```python
def create_funnel_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """퍼널 차트 생성. TAM/SAM/SOM 또는 파이프라인 시각화.

    > 마지막 수정: YYYY-MM-DD HH:MM:SS
    """
```

- `ChartConfig`에서 `AMICThemeFactory` 생성
- `ChartDataError` 예외로 데이터 유효성 검증
- `theme.apply_layout(fig, ...)` 호출로 일관된 레이아웃
- 모든 차트 함수 동일 시그니처

**예상**: ~6 파일 (4 생성, 2 수정), ~28 테스트

---

## 6. Phase D: Valuation & Returns + Korea Overlay

### 6-1. D1: Valuation & Returns 섹션

**목표**: 밸류에이션 계산기 + "valuation" 섹션 렌더러
**의존성**: B (재무 엔진 확장), C2 (sensitivity_heatmap 차트) 활용

#### 밸류에이션 계산기

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 생성 | `src/financial_engine/calculator/valuation.py` | `ValuationMetrics` — EV/EBITDA, P/E, EV/Revenue, IRR 시나리오(Base/Upside/Downside), MOIC 시나리오, Exit Multiple. `calculate_irr()`, `calculate_moic()`, `build_sensitivity_table()` |

#### 핵심 설계

```python
@dataclass(frozen=True)
class ValuationMetrics:
    """밸류에이션 핵심 지표."""

    ev_ebitda_range: tuple[float, float] | None       # (하한, 상한)
    per_range: tuple[float, float] | None             # (하한, 상한)
    ev_revenue_range: tuple[float, float] | None      # (하한, 상한)
    irr_scenarios: dict[str, float | None]            # {"base": 0.22, "upside": 0.30, "downside": 0.15}
    moic_scenarios: dict[str, float | None]           # {"base": 2.5, "upside": 3.2, "downside": 1.8}
    sensitivity_table: dict[str, list[list[float]]]   # WACC x Terminal Growth 매트릭스
    football_field: dict[str, tuple[float, float]]    # {방법론: (하한, 상한)}
```

#### 섹션 렌더러

| 작업 | 파일 | 슬라이드 구성 |
| --- | --- | --- |
| 생성 | `src/design_renderer/section_renderers/valuation.py` | 1) Valuation Summary KPI 카드, 2) IRR/MOIC 시나리오 테이블, 3) 민감도 히트맵 (Phase C), 4) MOIC Bridge 워터폴, 5) Exit 전략 비교 |

#### 수정 파일

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 수정 | `src/design_renderer/im_document.py` | `"valuation"` -> SECTION_IDS 추가 (20 -> 21), `ValuationData` sub-dataclass |
| 수정 | `src/design_renderer/section_renderers/__init__.py` | 렌더러 등록 |
| 수정 | `src/financial_engine/processor.py` | `ProcessingResult`에 `valuation` 필드 추가 |

#### 내러티브 프롬프트

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 수정 | `src/narrative_generator/prompts/section_prompts/` | 밸류에이션 섹션 프롬프트 추가/수정 |

**예상**: ~5 파일 (2 생성, 3 수정), ~35 테스트

---

### 6-2. D2: Korea Overlay Module

**목표**: 한국 PE 시장 특수성(규제, 재벌 카브아웃, 노동, K-IFRS) 자동 분석 및 IM 반영
**의존성**: A2 완료 권장

#### 한국 PE 특수 데이터 모델

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 생성 | `src/industry/korea/__init__.py` | Korea Overlay 패키지 |
| 생성 | `src/industry/korea/models.py` | `KoreaOverlayData` — 규제 리스크(MRFTA, FSCMA, 외투법), 재벌 카브아웃(TSA, 특수관계인), 노동 리스크, K-IFRS 조정사항 |
| 생성 | `src/industry/korea/regulatory.py` | 산업별 규제 맵 — 딜 규모/산업/소유구조 기반 규제 리스크 자동 평가 |
| 생성 | `src/industry/korea/kifrs.py` | K-IFRS 조정사항 (매출인식기준, 리스회계, 충당부채 등) |
| 생성 | `src/industry/korea/labor_esg.py` | 노동법 준수, ESG 공시 (KCGS, TCFD), FDI/크로스보더 이슈 |

#### IndustryModule 확장

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 수정 | `src/industry/base.py` | `IndustryModule`에 `get_korea_overlay()` 메서드 추가 |

#### 용어 확장

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 수정 | `src/narrative_generator/korean_finance/terminology.py` | `TermCategory`에 `INDUSTRY_LOGISTICS` 추가, 물류 용어 30+ 항목 |

**예상**: ~7 파일 (5 생성, 2 수정), ~25 테스트

---

## 7. Phase E: 기술 개선 (Technical Improvements)

### ~~E1: 한글 폰트 a:ea 수정~~ — 구현 완료

~~문제: run.font.name은 `<a:latin>`만 설정 -> 한글이 시스템 기본 폰트로 렌더링됨~~

**이미 구현 완료:**

- `src/design_renderer/pptx_engine/font_helper.py` — `set_font_with_ea(run, font, ea_font)` lxml로 `<a:ea typeface="Pretendard"/>` 직접 삽입. `ensure_ea_fonts_on_slide(slide)` 후처리.
- `src/design_renderer/pptx_engine/shape_builder.py` — 모든 텍스트 생성에서 `set_font_with_ea()` 사용
- `src/design_renderer/components/kpi_card.py` — 동일 적용
- `src/design_renderer/pipeline.py` — 렌더링 후 `ensure_ea_fonts_on_presentation()` 후처리
- `tests/test_design_renderer/test_font_helper.py` — 16개 테스트

### ~~E2: 슬라이드별 에러 처리 & 생성 매니페스트~~ — 구현 완료

**이미 구현 완료:**

- `src/design_renderer/manifest.py` — `GenerationManifest`, `SlideManifestEntry` — 슬라이드별 성공/실패/시간 기록
- `src/design_renderer/section_renderers/fallback.py` — 섹션 실패 시 "데이터 없음" 플레이스홀더 슬라이드
- `src/design_renderer/pipeline.py` — 섹션 렌더링 루프에 try/except + 매니페스트 기록 + 폴백 슬라이드

---

### 7-1. E3: 테스팅 강화

**목표**: PPTX XML 구조 검증 + golden file 스냅샷 테스팅 프레임워크 구축
**의존성**: 전체 기능 완료 후 (A + B + C + D)

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 생성 | `tests/test_design_renderer/test_pptx_structure.py` | PPTX XML 파싱 구조 테스트 — 타이틀 존재, a:ea 폰트 설정, 이미지 경계 |
| 생성 | `tests/test_design_renderer/test_golden_snapshots.py` | 골든 파일 스냅샷 테스팅 프레임워크 |
| 수정 | `tests/conftest.py` | 공유 `sample_im_data()` 픽스처 (완전한 IMDocumentData) |

**예상**: ~3 파일 (2 생성, 1 수정), ~30 테스트

---

### 7-2. E4: 이미지 최적화 & 성능

**목표**: 차트 PNG 사전 압축으로 PPTX 파일 크기 감소 및 생성 성능 개선
**의존성**: C (차트 확장) 완료 후

| 작업 | 파일 | 설명 |
| --- | --- | --- |
| 생성 | `src/design_renderer/image_optimizer.py` | `compress_chart_image()`, `optimize_pptx_images()` — 차트 PNG 사전 압축, JPEG 85% |
| 수정 | `src/design_renderer/components/chart_embed.py` | 차트 임베드 전 이미지 압축 적용 |
| 수정 | `src/chart_engine/export/png_exporter.py` | 내보내기 후 압축 단계 추가 |

**예상**: ~3 파일 (1 생성, 2 수정), ~8 테스트

---

## 8. 실행 순서 & 의존성 그래프

```text
Phase C (새 차트 타입)    ─────────────────────────────┐
Phase A1 (산업 인프라)    ─── Phase A2 (4개 산업 구현) ─┤
                                                       ↓
                          Phase B (산업별 재무 지표)  Phase D (Valuation + Korea)
                                                       ↓
                          Phase E3-E4 (테스팅 + 성능) ── 최종 검증
```

### 권장 순서

1. ~~**C + A1** (병렬) — 새 차트 4종 + 산업 인프라~~ → **A1 완료 ✅**
2. ~~**A2** — 4개 산업 모듈 + 물류 내러티브 + 렌더러~~ → **A2 완료 ✅**
3. ~~**B** — 산업별 재무 지표~~ → **B 완료 ✅ (93 tests, 1180 total)**
4. **C + D1 + D2** (병렬) — 새 차트 4종 + Valuation & Returns + Korea Overlay (다음 단계)
5. **E3 + E4** (병렬) — 테스팅 강화 + 이미지 최적화 (마지막 안정화)

---

## 9. 총 예상 규모

### 원래 계획 vs 정제된 계획

| 항목 | 원래 계획 (E1+E2 포함) | 정제된 계획 |
| --- | --- | --- |
| 신규 파일 | ~48 | **~31** |
| 수정 파일 | ~24 | **~17** |
| 신규 테스트 | ~337 | **~241** |
| Phase 수 | 5 (A-E 전체) | **4 (A-D) + E3, E4** |

### Phase별 상세

| Phase | 신규 파일 | 수정 파일 | 신규 테스트 | 상태 |
| --- | --- | --- | --- | --- |
| A1 (산업 인프라) | 5 | 2 | 22 | ✅ 완료 |
| A2 (산업 모듈) | 7 | 2 | ~40 | ✅ 완료 |
| B (재무 지표) | 4 | 3 | 93 | ✅ 완료 |
| C (차트 타입) | 4 | 2 | ~28 | ⏳ 대기 |
| D1 (Valuation) | 2 | 3 | ~35 | ⏳ 대기 |
| D2 (Korea Overlay) | 5 | 2 | ~25 | ⏳ 대기 |
| E3 (테스팅) | 2 | 1 | ~30 | ⏳ 대기 |
| E4 (이미지 최적화) | 1 | 2 | ~8 | ⏳ 대기 |
| **합계** | **~31** | **~17** | **~281** | **3/8 완료** |

**현재 실적**: 215 소스파일, 1180 테스트 (전체 통과)
**결과 예상**: 215 -> ~240 소스파일, 1180 -> ~1,300+ 테스트

---

## 10. 핵심 수정 파일 (모든 Phase에서 반복 접근)

| 파일 | 관련 Phase | 수정 내용 |
| --- | --- | --- |
| `src/design_renderer/im_document.py` | A1, A2, D1 | industry 필드, 새 섹션 ID, 산업별 데이터 모델, ValuationData |
| `src/design_renderer/pipeline.py` | A1 | 산업 resolve, 산업별 섹션 merge |
| `src/design_renderer/section_renderers/__init__.py` | A2, D1 | 신규 렌더러 등록 (industry_kpi, industry_overview, valuation) |
| `src/chart_engine/plotly/__init__.py` | C | CHART_DISPATCH에 4개 차트 타입 추가 (funnel, heatmap, cohort, treemap) |
| `src/financial_engine/processor.py` | B, D1 | 산업별 calculator 조건부 실행, valuation 단계, industry_metrics 필드 |

---

## 11. 핵심 주의사항

1. **기존 패턴 엄수**: 모든 신규 코드는 기존 코드베이스의 패턴을 정확히 따를 것
   - 계산기: `@dataclass(frozen=True)` result + 순수 함수형
   - 렌더러: `@register_renderer` 데코레이터 + `BaseSectionRenderer` 상속
   - 차트: `CHART_DISPATCH` dict 등록 + 동일 시그니처
   - 산업 모듈: `@register_industry` 데코레이터 (신규 패턴, 기존 registry 모방)

2. **IMDocumentData 확장 최소화**: SECTION_IDS에 최소한의 추가만 (industry_kpi, industry_overview, valuation = 3개)

3. **한국어 컨텍스트 유지**: 모든 docstring Google-style 한국어, 에러 메시지 한국어, `> 마지막 수정:` 타임스탬프 필수

4. **TDD**: 재무 계산 로직은 반드시 테스트 먼저 작성

5. **기존 951개 테스트 불가침**: 새 코드가 기존 테스트를 깨뜨리지 않을 것

6. **재무 데이터 정확성**: 근사치 금지, Decimal 연산 필수 (기존 calculator 패턴 준수)

---

## 12. 검증 방법

1. **단위 테스트**: 각 Phase별 `pytest tests/ -v --tb=short`
2. **기존 테스트 무결성**: 전체 951개 테스트 통과 확인 (`pytest --tb=short -q`)
3. **통합 테스트**: `IMPipeline.generate()`로 각 산업별 FULL IM 생성 확인
4. **구조 테스트 (E3)**: 생성된 PPTX XML 파싱으로 a:ea 폰트, 슬라이드 수, 차트 데이터 검증
5. **수동 검증**: 생성된 PPTX를 PowerPoint에서 열어 한글 렌더링, 차트 편집 가능 여부, 레이아웃 확인
