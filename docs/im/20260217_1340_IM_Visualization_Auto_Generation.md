# IM 시각화 자료 자동생성 구현 완료

> 2026-02-17 13:27 (초기 작성)
> 2026-02-17 13:40 (전체 섹션 시각화 확장 업데이트)

---

## 1. 개요

IM(Investment Memorandum) 모듈의 `chart_engine`에는 10종 Plotly 차트 + 3종 Graphviz 다이어그램이 완전히 구현되어 있었으나, **파이프라인에서 차트 생성 단계가 누락**되어 `data.charts`가 항상 비어 있었다.

이번 작업으로 `DataTransformer.transform_all()` → `chart_embed.create_chart()` → `chart_to_png_bytes()` 호출 흐름을 파이프라인에 연결하여, IM 생성 시 **데이터 기반 시각화가 자동으로 포함**되도록 구현했다.

---

## 2. 핵심 문제 (Before)

```
IMDocumentData.charts = {}  (항상 비어 있음)
  → 섹션 렌더러가 data.charts.get(section_id) 참조
    → 빈 리스트 반환 → 차트 슬라이드 생성 안 됨
```

**원인**: `DataTransformer.transform_all()`이 정의만 되고 어디에서도 호출되지 않음.

---

## 3. 수정 내역 (After)

### Step 1: 파이프라인에 차트 생성 스텝 삽입

**파일**: `im/src/design_renderer/pipeline.py`

`IMPipeline.generate()` 메서드에 `_auto_generate_charts()` 메서드를 추가하고, `compute_derived_metrics()` 직후에 호출:

```python
# 1.5b. 차트 자동 생성 (data.charts가 비어 있으면 자동 채움)
if not data.charts:
    self._auto_generate_charts(data, result)
```

**흐름**:
1. `DataTransformer.transform_all(data)` → 섹션별 `ChartSpec[]` 생성
2. 각 `ChartSpec` → `create_chart()` → `go.Figure`
3. `go.Figure` → `chart_to_png_bytes()` → PNG bytes
4. `ChartData(data={"image_bytes": png_bytes})` → `data.charts[section_id]`에 저장

### Step 2: DataTransformer 확장

**파일**: `im/src/chart_engine/data_transformer.py`

- `transform_valuation()` 메서드 추가 (밸류에이션 민감도 히트맵)
- `transform_all()` 확장: `valuation_data` → `sensitivity_heatmap` 포함

### Step 3: chart_embed 디스패처 확장

**파일**: `im/src/design_renderer/components/chart_embed.py`

기존 6종 → **10종**으로 확장:

| # | 차트 유형 | 상태 |
|---|---------|------|
| 1 | `waterfall` | 기존 |
| 2 | `combo` | 기존 |
| 3 | `stacked_bar` | 기존 |
| 4 | `donut` | 기존 |
| 5 | `line` | 기존 |
| 6 | `hbar` | 기존 |
| 7 | `funnel` | **신규** |
| 8 | `heatmap` | **신규** |
| 9 | `cohort_heatmap` | **신규** |
| 10 | `treemap` | **신규** |

### Step 4: 차트 미소비 렌더러에 차트 슬롯 추가

**market_overview.py**:
- `render_html()`: 차트 이미지 base64 `<img>` 태그 + 별도 슬라이드
- `render_pptx()`: `add_chart_image()` 루프로 차트 슬라이드 추가

**shareholder_structure.py**:
- `render_html()`: 주주 구성 도넛 차트 이미지 + 별도 슬라이드
- `render_pptx()`: 차트 이미지 슬라이드 추가

### Step 5: Graphviz 다이어그램 통합

**company_overview.py** — 조직도 (Org Chart):
- `render_html()`: `data.org_structure` 존재 시 → `render_org_chart_html()` → SVG 인라인 삽입
- `render_pptx()`: `render_org_chart_pptx()` → 별도 슬라이드

**business_overview.py** — 가치사슬 플로우 다이어그램:
- `render_html()`: `data.company_overview.value_chain` ≥ 2 항목 시 → `create_flow_diagram()` → SVG 인라인
- `render_pptx()`: `graphviz_to_png()` → `add_chart_image()` → 별도 슬라이드

---

## 4. 섹션별 자동생성 시각화 전체 매핑

### 4.1 Plotly 차트 (10종)

| 섹션 | 차트 유형 | 조건 | 데이터 소스 |
|------|---------|------|-----------|
| `financial_analysis` | **Combo** (매출+영업이익률) | revenue + operating_income, years ≥ 2 | FinancialStatements |
| `financial_analysis` | **Waterfall** (영업이익 Bridge) | revenue + cogs/sga, 최신 연도 | FinancialStatements |
| `financial_analysis` | **Line** (EBITDA 추이) | ebitda, years ≥ 3 | FinancialStatements |
| `financial_analysis` | **Stacked Bar** (사업부별 매출) | segment_revenue 존재 시 | SegmentRevenue |
| `market_overview` | **Donut** (TAM/SAM/SOM) | tam + sam + som 모두 존재 | MarketData |
| `market_overview` | **Funnel** (시장 규모 퍼널) | tam + sam + som 모두 존재 | MarketData |
| `market_overview` | **HBar** (경쟁사 매출 비교) | competitors ≥ 2개 | MarketData.competitors |
| `shareholder_structure` | **Donut** (주주 구성) | shareholders + stake_pct 존재 | ShareholderInfo[] |
| `valuation` | **Heatmap** (민감도 분석) | sensitivity_data 존재 | ValuationData |
| (범용) | **Treemap** / **Cohort Heatmap** | 수동 데이터 주입 시 | 사용자 정의 |

### 4.2 Graphviz 다이어그램 (10종, 8개 섹션)

| 섹션 | 다이어그램 | 조건 | 데이터 소스 |
|------|----------|------|-----------|
| `company_overview` | **Org Chart** (조직도) | org_structure 존재 | IMDocumentData.org_structure |
| `shareholder_structure` | **Shareholding** (지배구조도) | shareholders ≥ 2 + 연결관계 | ShareholderInfo[] |
| `business_overview` | **Flow Diagram** (가치사슬) | value_chain ≥ 2 항목 | CompanyOverview.value_chain |
| `deal_overview` | **Flow Diagram** (거래 타임라인) | timeline ≥ 2 마일스톤 | DealStructure.timeline |
| `business_model` | **Flow Diagram** (밸류 체인) | value_chain ≥ 2 항목 | CompanyOverview.value_chain |
| `value_creation` | **Flow Diagram** (가치 창출 레버) | growth_strategy 카테고리 ≥ 2 | GrowthStrategy |
| `growth_strategy` | **Flow Diagram** (성장 로드맵) | roadmap ≥ 2 연도 | GrowthStrategy.roadmap |
| `transaction_structure` | **Flow Diagram** (거래 구조도) | seller 존재 | DealStructure |
| `management_team` | **Org Chart** (경영진 조직도) | org_structure 또는 members ≥ 2 | org_structure / ManagementMember[] |

### 4.3 차트 재활용 (Cross-Section Reuse)

| 섹션 | 재활용 차트 | 원본 섹션 | 조건 |
|------|-----------|----------|------|
| `executive_summary` | 첫 번째 차트 (보통 Combo) | `financial_analysis` | data.charts["financial_analysis"] 비어 있지 않음 |
| `business_model` | Stacked Bar (사업부별 매출) | `financial_analysis` | chart_type == "stacked_bar" |
| `investment_highlights` | 외부 주입 차트 슬롯 | (사용자 정의) | data.charts["investment_highlights"] 존재 시 |

---

## 5. 수정 파일 요약

| # | 파일 | 변경 내용 |
|---|------|---------|
| 1 | `im/src/design_renderer/pipeline.py` | `_auto_generate_charts()` 메서드 추가 + `generate()` 호출 |
| 2 | `im/src/chart_engine/data_transformer.py` | `transform_valuation()` 추가, `transform_all()` 확장 |
| 3 | `im/src/design_renderer/components/chart_embed.py` | funnel, heatmap, cohort_heatmap, treemap 디스패치 추가 |
| 4 | `im/src/design_renderer/section_renderers/market_overview.py` | HTML/PPTX 차트 슬라이드 루프 추가 |
| 5 | `im/src/design_renderer/section_renderers/shareholder_structure.py` | HTML/PPTX 차트 슬라이드 루프 추가 |
| 6 | `im/src/design_renderer/section_renderers/company_overview.py` | Graphviz 조직도 SVG/PNG 슬라이드 추가 |
| 7 | `im/src/design_renderer/section_renderers/business_overview.py` | Graphviz 가치사슬 플로우 SVG/PNG 슬라이드 추가 |
| 8 | `im/src/design_renderer/section_renderers/deal_overview.py` | Graphviz 거래 타임라인 플로우 SVG/PNG 슬라이드 추가 |
| 9 | `im/src/design_renderer/section_renderers/executive_summary.py` | financial_analysis 첫 번째 차트 재활용 슬라이드 추가 |
| 10 | `im/src/design_renderer/section_renderers/investment_highlights.py` | 외부 주입 차트 슬롯 추가 |
| 11 | `im/src/design_renderer/section_renderers/business_model.py` | Graphviz 밸류 체인 + stacked_bar 매출 구성 차트 추가 |
| 12 | `im/src/design_renderer/section_renderers/value_creation.py` | Graphviz 가치 창출 레버 플로우 다이어그램 추가 |
| 13 | `im/src/design_renderer/section_renderers/growth_strategy.py` | Graphviz 성장 로드맵 타임라인 다이어그램 추가 |
| 14 | `im/src/design_renderer/section_renderers/transaction_structure.py` | Graphviz 거래 구조 플로우 다이어그램 추가 |
| 15 | `im/src/design_renderer/section_renderers/management_team.py` | Graphviz 경영진 조직도 (org_structure 또는 자동 생성) 추가 |

---

## 6. 아키텍처 다이어그램 (구현 후)

```
IMDocumentData
  ├─ compute_derived_metrics()
  │
  ├─ _auto_generate_charts()               ← ✅ 신규 연결
  │    ├─ DataTransformer.transform_all()
  │    │    ├─ transform_financial()        → combo, waterfall, line
  │    │    ├─ transform_segment()          → stacked_bar
  │    │    ├─ transform_market()           → donut, funnel, hbar
  │    │    ├─ transform_shareholders()     → donut
  │    │    └─ transform_valuation()        → heatmap  ← ✅ 신규
  │    │
  │    └─ create_chart() → go.Figure → chart_to_png_bytes() → PNG
  │         └─ data.charts[section_id] = [ChartData(image_bytes=...)]
  │
  ├─ 섹션 렌더러 (HTML/PPTX)
  │    ├─ financial_analysis    → data.charts["financial_analysis"]   ✅ 기존
  │    ├─ valuation             → data.charts["valuation"]            ✅ 기존
  │    ├─ market_overview       → data.charts["market_overview"]      ✅ 신규 슬롯
  │    ├─ shareholder_structure → data.charts["shareholder_structure"] ✅ 신규 슬롯
  │    ├─ company_overview      → Graphviz org_chart                  ✅ 신규
  │    ├─ business_overview     → Graphviz flow_diagram               ✅ 신규
  │    ├─ deal_overview         → Graphviz timeline flow              ✅ 확장
  │    ├─ executive_summary     → financial_analysis 차트 재활용      ✅ 확장
  │    ├─ investment_highlights → 외부 주입 차트 슬롯                 ✅ 확장
  │    ├─ business_model        → Graphviz 밸류 체인 + stacked_bar    ✅ 확장
  │    ├─ value_creation        → Graphviz 가치 창출 레버             ✅ 확장
  │    ├─ growth_strategy       → Graphviz 로드맵 타임라인            ✅ 확장
  │    ├─ transaction_structure → Graphviz 거래 구조 플로우            ✅ 확장
  │    └─ management_team       → Graphviz 경영진 조직도              ✅ 확장
  │
  └─ 듀얼 출력 (PPTX + PDF)
```

---

## 7. 검증 방법

1. **단위 테스트**: `DataTransformer.transform_all(mock_data)` → 섹션별 ChartSpec 확인
2. **통합 테스트**: `IMPipeline.generate(data)` → `data.charts`에 PNG bytes 존재 확인
3. **PPTX 출력**: 생성된 PPTX에서 차트 슬라이드 시각적 확인
4. **PDF 출력**: 생성된 PDF에서 차트 이미지 렌더링 확인
5. **엣지 케이스**: 데이터 부족 시 차트 미생성 (에러 없이 스킵) 확인
6. **Graphviz 의존성**: `graphviz` 패키지 설치 확인 (`pip install graphviz` + 시스템 Graphviz)

---

## 8. 의존성 요구사항

| 패키지 | 용도 | 설치 |
|--------|------|------|
| `plotly` | 10종 차트 생성 | `pip install plotly` |
| `kaleido` | Plotly → PNG/SVG 변환 (300 DPI) | `pip install kaleido` |
| `graphviz` (Python) | Graphviz DOT 생성 | `pip install graphviz` |
| Graphviz (시스템) | DOT → SVG/PNG 렌더링 | OS별 설치 필요 |

---

## 9. 추가 섹션별 시각화 상세 (2026-02-17 확장)

### 9.1 deal_overview — 거래 타임라인 다이어그램

- **조건**: `DealStructure.timeline` 딕셔너리에 ≥ 2개 마일스톤
- **방향**: LR (좌→우) 타임라인 플로우
- **노드 구성**: `{마일스톤명}\n{날짜}` 형태, 첫 번째=start, 마지막=end, 중간=process
- **HTML**: SVG 인라인 (`graphviz_to_svg`)
- **PPTX**: PNG 300DPI (`graphviz_to_png`) → `add_chart_image()`

### 9.2 executive_summary — 재무 차트 재활용

- **조건**: `data.charts["financial_analysis"]`가 비어 있지 않음
- **동작**: 첫 번째 차트(보통 매출+영업이익률 Combo)를 재활용
- **HTML**: base64 PNG `<img>` 태그
- **PPTX**: `add_chart_image()` — 별도 "핵심 재무지표" 슬라이드
- **참고**: 중복 생성 없음 (원본 참조만)

### 9.3 investment_highlights — 외부 주입 차트 슬롯

- **조건**: `data.charts["investment_highlights"]`에 차트 존재 시
- **동작**: 자동 생성 없음, 외부(사용자/파이프라인)에서 주입된 차트만 표시
- **용도**: 커스텀 투자 포인트 시각화 (경쟁력 비교, 시장 위치 등)

### 9.4 business_model — 밸류 체인 + 매출 구성

1. **Graphviz 밸류 체인 플로우**: `value_chain` ≥ 2 항목 → LR 플로우 다이어그램
2. **Stacked Bar 매출 구성**: `data.charts["financial_analysis"]`에서 `chart_type == "stacked_bar"` 필터링
- 두 시각화 모두 별도 슬라이드로 추가

### 9.5 value_creation — 가치 창출 프레임워크

- **조건**: GrowthStrategy에서 유기적 성장/신규 사업/M&A 중 ≥ 2개 카테고리 존재
- **방향**: TB (위→아래) 팬-아웃/팬-인 구조
- **구조**: `투자` → `[유기적 성장, 신규 사업, M&A]` → `가치 창출`
- **파라미터**: `rankdir="TB"` (상단→하단)

### 9.6 growth_strategy — 성장 로드맵

- **조건**: `GrowthStrategy.roadmap` 딕셔너리에 ≥ 2개 연도
- **방향**: LR (좌→우) 타임라인
- **노드 구성**: `{연도}\n{목표1}  {목표2}` (최대 2개 목표 표시)
- **정렬**: 연도 기준 오름차순 정렬

### 9.7 transaction_structure — 거래 구조도

- **조건**: `DealStructure.seller` 존재
- **구조**: 3노드 플로우 — 매도자(start) → 거래(decision) → 매수자/투자자(end)
- **라벨**: 거래 유형 + 구주/신주 규모 표시
  - 예: `"경영권 매각\n(구주 500억, 신주 200억)"`
- **엣지 라벨**: "지분 매각", "지분 인수"

### 9.8 management_team — 경영진 조직도

- **우선순위 1**: `data.org_structure` 존재 시 → `render_org_chart_html/pptx()` 어댑터 사용
- **우선순위 2**: `management_team` 리스트 ≥ 2명 시 → 자동 생성
  - **구조**: 스타 토폴로지 — 첫 번째 멤버(CEO)가 나머지 모두와 연결
  - **노드 정보**: `name` + `role` (없으면 `title`)
  - `create_org_chart()` 사용 (flow_diagram이 아닌 org_chart)

---

## 10. 섹션별 시각화 커버리지 요약

| 섹션 | Plotly 차트 | Graphviz | 차트 재활용 | 총 시각화 |
|------|-----------|----------|-----------|----------|
| `cover` | — | — | — | 0 (구조적) |
| `toc` | — | — | — | 0 (구조적) |
| `executive_summary` | — | — | ✅ 1종 | 1 |
| `deal_overview` | — | ✅ 1종 | — | 1 |
| `investment_highlights` | — | — | 슬롯 | 0~N |
| `company_overview` | — | ✅ 1종 | — | 1 |
| `business_overview` | — | ✅ 1종 | — | 1 |
| `business_model` | — | ✅ 1종 | ✅ 1종 | 2 |
| `management_team` | — | ✅ 1종 | — | 1 |
| `financial_analysis` | ✅ 4종 | — | — | 4 |
| `industry_kpi` | ✅ 차트슬롯 | — | — | 0~N |
| `industry_overview` | ✅ 차트슬롯 | — | — | 0~N |
| `market_overview` | ✅ 3종 | — | — | 3 |
| `shareholder_structure` | ✅ 1종 | ✅ 1종 | — | 2 |
| `growth_strategy` | — | ✅ 1종 | — | 1 |
| `value_creation` | — | ✅ 1종 | — | 1 |
| `transaction_structure` | — | ✅ 1종 | — | 1 |
| `valuation` | ✅ 1종 | — | — | 1 |
| `risk_factors` | — | — | — | 0 |
| `appendix` | — | — | — | 0 (부록) |
| `disclaimer` | — | — | — | 0 (구조적) |
| **합계** | **9+종** | **10종** | **2종** | **~21종** |

---

## 11. 주의사항

- `data.charts`가 이미 채워져 있으면 자동 생성을 건너뜀 (`if not data.charts:`)
- 개별 차트 생성 실패 시 `logger.warning` 후 계속 진행 (전체 파이프라인 중단 안 함)
- `chart_engine` 임포트 실패 시 경고만 발생 (Plotly/Kaleido 미설치 환경 대응)
- Graphviz 미설치 시 다이어그램 슬라이드만 스킵 (렌더러 내 try/except)
