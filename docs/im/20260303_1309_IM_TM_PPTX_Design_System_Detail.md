# IM/TM PPTX 디자인 시스템 세부 기능 설명

> 작성: 2026-03-03 13:09

---

## 1. 시스템 개요

IM 모듈은 **3종 투자 문서**(IM/TM/DM)를 PPTX 형식으로 자동 생성하는 시스템이다. **32종 섹션 렌더러**가 레지스트리 패턴으로 동적 조합되며, AMIC 공식 디자인 시스템을 일관 적용한다.

---

## 2. 디자인 토큰 (`im/src/design_renderer/design_tokens.py`)

### 2.1 색상 시스템 — AMIC 5단계 그린 팔레트

| 토큰 | HEX | 용도 |
|------|-----|------|
| `primary` | `#0F3A32` | Signature Green — 표지, 헤더, 주요 강조 |
| `secondary` | `#1C8F57` | Solid Green — 보조 강조, 서브헤더 |
| `accent` | `#26C260` | Highlight Green — 긍정 지표, 테이블 헤더 |
| `fresh` | `#A3E96B` | Fresh Green — 그래디언트, 보조 차트 |
| `light` | `#E6FDD6` | Light Green — 배경, 카드, 강조행 |

### 2.2 타이포그래피 — 4개 폰트 체계

| 폰트 | 용도 | Weight |
|------|------|--------|
| **SUITE** | 제목 (커버, 섹션 타이틀) | Bold |
| **Pretendard** | 본문 전체 | Regular/Medium/SemiBold/Bold |
| **Noto Sans KR** | 특수문자/광범위 한글 폴백 | Variable |
| **NanumGothic** | Plotly/Kaleido 차트 전용 (Docker) | — |

### 2.3 폰트 크기 계층

| 용도 | 크기 |
|------|------|
| 표지 타이틀 | **40pt** |
| 표지 부제 | 24pt |
| 슬라이드 타이틀 | **16pt** |
| 상단 요약 | 14pt |
| 본문 / 테이블 헤더 | **10pt** |
| 재무제표 | 9pt |
| 각주 | 9pt |

### 2.4 슬라이드 레이아웃

- **크기**: 10.83" × 7.5" (Landscape Letter)
- **여백**: 좌우 0.5", 상단 0.6", 하단 1.0"
- **재무 테이블**: 첫 열 2.6" + 데이터 열 0.91" × 7개

### 2.5 불릿 스타일 — 3단계

| Level | 기호 | 용도 |
|-------|------|------|
| 1 | ü (체크마크) / § (큰 점) | 주요 항목 |
| 2 | - (하이픈) | 하위 항목 |
| Emphasis | → (화살표) | 결론/시사점 |

### 2.6 테이블 스타일 — 미니멀

- **세로선 없음**, 가로선만 (0.5pt)
- 헤더: `#26C260` 배경 + White 텍스트
- 강조행: `#E6FDD6` 배경

---

## 3. 5종 PPTX 레이아웃

| 레이아웃 | 인덱스 | 용도 |
|---------|--------|------|
| **BLANK** | 0 | 완전 빈 슬라이드 (면책/부록) |
| **FOREST** | 1 | 배경 이미지 + 녹색 오버레이 (표지/TOC/연락처) |
| **BLANK_PGNO** | 2 | 페이지 번호만 (full-width 재무표) |
| **MAIN** | 3 | 제목바 + 콘텐츠 + 페이지번호 (일반) |
| **MAIN_w/Andersen** | 4 | MAIN + 공동 브랜딩 |

---

## 4. PPTX 엔진 (4개 핵심 모듈)

### 4.1 SlideFactory (`pptx_engine/slide_factory.py`)

`add_blank_slide()`, `add_forest_slide()`, `add_content_slide(title)` 등으로 레이아웃 기반 슬라이드 생성.

### 4.2 ShapeBuilder (`pptx_engine/shape_builder.py`)

| 함수 | 용도 |
|------|------|
| `add_summary_textbox()` | 14pt Bold 요약 텍스트 |
| `add_sub_header_bar()` | 다크그린 배경 + White 텍스트 헤더바 |
| `add_body_textbox()` | 10pt 본문 |
| `add_bullet_list()` | 3단계 불릿 리스트 |
| `add_financial_table()` | 재무 테이블 |
| `add_kpi_cards()` | KPI 카드 |
| `add_chart_image()` | Plotly/GraphViz 차트 이미지 삽입 |
| `add_org_chart()` | 조직도 |

### 4.3 FontHelper (`pptx_engine/font_helper.py`)

python-pptx의 `run.font.name`은 `<a:latin>` 요소만 설정하므로, **lxml로 `<a:ea>` (East Asian) 폰트를 직접 추가**하여 한글 렌더링을 보장한다.

```python
set_font_with_ea(run, "Pretendard")           # Latin + EA 폰트 동시 설정
ensure_ea_fonts_on_slide(slide)                # 슬라이드 전체 후처리
ensure_ea_fonts_on_presentation(prs)           # 프레젠테이션 전체 후처리
```

### 4.4 StyleApplier (`pptx_engine/style_applier.py`)

- **워터마크**: "CONFIDENTIAL" 45도 반투명 대각선 (opacity 0.2)
- **편집 제한**: SHA-512 + salt, 100,000 iterations 비밀번호 보호

```python
add_watermark(prs, text="CONFIDENTIAL", opacity=0.2, angle=-45)
set_edit_restriction(prs, read_only=True, password="...")
```

---

## 5. 32종 섹션 렌더러

### 5.1 렌더러 아키텍처

모든 렌더러는 `BaseSectionRenderer`를 상속하며 `@register_renderer` 데코레이터로 자동 등록된다.

```python
@register_renderer
class CoverRenderer(BaseSectionRenderer):
    section_id = "cover"

    def render_html(data, *, tokens=None) -> list[str]     # 레거시 호환
    def render_pptx(factory, data, *, prs, tokens=None) -> list[Any]  # 실제 출력
```

### 5.2 공통 렌더러 (IM/TM/DM 공유, 18종)

| 카테고리 | 렌더러 | 슬라이드 수 | 핵심 기능 |
|---------|--------|-----------|----------|
| **Core** | cover | 1 | FOREST 배경, 프로젝트명/날짜 |
| | disclaimer | 1 | 면책조항 (FOREST) |
| | toc_divider | 1 | 목차 간지 (자동 생성) |
| | contact | 1 | 연락처 |
| **회사/거래** | deal_overview | 1-3 | 거래 유형, 타임라인, 밸류에이션 |
| | executive_summary | 2-3 | 내러티브 + KPI |
| | company_overview | 1-2 | 회사 기본 정보 |
| | business_overview | 1-2 | 사업부별 매출, 주요 고객 |
| **전략** | investment_highlights | **1-5** | 2개 이하→1장, 3개 이상→Overview+개별 |
| | market_overview | 1-2 | TAM/SAM/SOM, 산업 트렌드 |
| | value_creation | 2-3 | 가치 창출 전략 |
| | growth_strategy | 2-3 | 성장 전략 + KPI |
| **재무** | financial_analysis | **2-10** | KPI 대시보드, P&L, B/S, CF, 차트 |
| | valuation | **5 (고정)** | KPI→시나리오→민감도→워터폴→Exit |
| | transaction_structure | 1-2 | 구주/신주, 밸류에이션 |
| | shareholder_structure | 1-2 | 지분율 테이블 + 바 차트 |
| **기타** | management_team | 1-2 | 경영진 카드 |
| | business_model | 1-2 | 비즈니스 모델 구조도 |

### 5.3 TM 전용 렌더러 (8종, 4그룹 구조)

```
Group 1: Executive Summary
  ├─ target_overview      (← company_overview 별칭, 타이틀만 변경)
  ├─ target_highlights    (← business_overview 별칭, 타이틀만 변경)
  └─ target_positioning   (타겟 시장 포지셔닝)

Group 2: Market Opportunity
  ├─ market_outlook       (시장 전망 KPI + 산업 트렌드)
  ├─ demand_driver        (수요 요인)
  └─ supply_driver        (공급 요인)

Group 3: Target Highlights
  └─ (Group 1 렌더러 재사용)

Group 4: Financial Summary
  ├─ proforma_plan        (Pro-Forma 사업계획)
  └─ proforma_financials  (Pro-Forma 재무제표)
```

### 5.4 DM 전용 렌더러 (6종, 순차 구조)

| 렌더러 | 용도 |
|--------|------|
| `dm_market_trends` | 시장 & 거래 트렌드 분석 |
| `dm_deal_structure` | 거래 구조 고려사항 |
| `dm_investment_thesis` | 투자 논거 및 핵심 논점 |
| `dm_valuation` | 밸류에이션 분석 요약 |
| `dm_risk_assessment` | 위험 평가 |
| `dm_summary` | 최종 요약 & 권고 |

### 5.5 산업별 렌더러 (2종, Phase A1)

| 렌더러 | 용도 |
|--------|------|
| `industry_overview` | 산업 개요 내러티브 + 운영 분석 차트 |
| `industry_kpi` | 산업별 KPI (NRR, ARR, CAC 등) |

---

## 6. 3종 문서 비교 (IM vs TM vs DM)

| 항목 | IM (Information) | TM (Teaser) | DM (Discussion) |
|------|-----------------|-------------|-----------------|
| **슬라이드 수** | 20~40+ | ~25 | ~8 |
| **대상** | 모든 이해관계자 | 초기 시장 타겟 (광범위) | 투자위원회 (내부 심사) |
| **톤** | 중립적, 포괄적 | 전략적, 마케팅 | 분석적, 비판적 |
| **섹션 수** | 18종 FULL | 8종 (4그룹) | 6종 (순차) |
| **프리셋** | TITAN/COVENANT/FULL/CUSTOM | TEASER (고정) | DM (고정) |

### 문서별 섹션 구성

**IM (FULL, 18섹션)**:
```
Cover → Executive Summary → Investment Highlights → Company Overview →
Business Model → Market Overview → Business Overview → Value Creation →
Growth Strategy → Financial Analysis → Valuation → Management Team →
Shareholder Structure → Transaction Structure → Appendix → Contact
```

**TM (4그룹 + 표지/면책/연락처)**:
```
Cover → Disclaimer → [TOC → 섹션] × 4그룹 → Contact
```

**DM (순차)**:
```
Cover → Market & Transaction Trends → Deal Structure → Investment Thesis →
Valuation Analysis → Risk Assessment → Summary & Recommendations → Contact
```

---

## 7. 차트 엔진

### 7.1 Plotly 차트 (10종)

| 차트 | 용도 |
|------|------|
| `waterfall` | MOIC 브릿지, 가치 창출 과정 |
| `combo` | 매출 + 영업이익률 이중축 |
| `stacked_bar` | 사업부별/세그먼트별 매출 |
| `donut` | 지분/매출 구성 |
| `line` | 추세선 (성장률, ROE) |
| `hbar` | 경쟁사 벤치마크 |
| `funnel` | 기금 모집 전환 깔때기 |
| `sensitivity_heatmap` | 민감도 분석 (Exit Multiple × EBITDA Growth) |
| `cohort_heatmap` | 코호트 분석 |
| `treemap` | 계층적 비교 |

### 7.2 GraphViz 다이어그램 (3종)

| 다이어그램 | 용도 | 노드 스타일 |
|---------|------|-----------|
| `shareholding` | 지배구조도 | company=사각형, person=타원, fund=육각형 |
| `org_chart` | 조직도 | 경영 계층 구조 |
| `flow_diagram` | 흐름도 | 프로세스 흐름 |

### 7.3 PPTX 네이티브 차트

Plotly PNG 래스터 대신 **편집 가능한 PPTX 차트** 생성 (donut, hbar, line, stacked_bar).

### 7.4 AMIC 테마 (`AMICThemeFactory`)

- 배경 투명화, AMIC 5단계 그린 색상 시퀀스
- 시맨틱 컬러: positive(`#26C260`), negative(`#BC2C1A`), caution(`#EF6C00`)
- 폰트: Noto Sans KR (본문 10pt, 제목 14pt)

---

## 8. 동적 슬라이드 수 결정

### 8.1 Investment Highlights (1-5장)

```python
# 2개 이하 포인트 → 1슬라이드 (기존 레이아웃)
# 3개 이상 포인트 → Overview 1장 + 개별 Highlight 최대 5장
def render_pptx(self, factory, data, *, prs, tokens=None):
    if len(highlights) <= 2:
        return _render_single_slide(...)
    else:
        return _render_multi_slides(...)   # 최대 6슬라이드
```

### 8.2 Financial Analysis (2-10장)

데이터 유무에 따라 동적으로 슬라이드 추가/제거:

| 슬라이드 | 조건 |
|---------|------|
| KPI 대시보드 | 항상 |
| P&L 요약 | 재무제표 있으면 |
| 매출 추이 | 매출 데이터 있으면 |
| 수익성 분석 | 마진율 데이터 있으면 |
| 대차대조표 | B/S 데이터 있으면 |
| 현금흐름 | CF 데이터 있으면 |
| 운전자본 | 운전자본 데이터 있으면 |
| CAPEX | CAPEX 데이터 있으면 |
| 비율 대시보드 | 부채비율 데이터 있으면 |
| 차트 | 차트 이미지들 |

### 8.3 Valuation (고정 5장)

1. KPI 요약 + 내러티브
2. IRR/MOIC 시나리오 테이블
3. 민감도 히트맵 (Plotly)
4. MOIC 워터폴 차트 (Plotly)
5. Exit 전략 비교 테이블

---

## 9. 렌더링 파이프라인 흐름

```
IMDocumentData (입력)
  │
  ▼
IMPipeline.generate_pptx()
  │
  ├─ 1. TemplateManager: PPTX 마스터 로드 → Presentation 생성
  ├─ 2. SlideFactory 초기화
  ├─ 3. get_active_sections() → 섹션 ID 리스트
  ├─ 4. 각 섹션별 루프:
  │     ├─ get_renderer(section_id) → 렌더러 조회
  │     └─ renderer.render_pptx() → [Slide] 반환
  ├─ 5. TOC 빌드 (2-pass 렌더링, TM 전용)
  ├─ 6. 후처리:
  │     ├─ ensure_ea_fonts_on_presentation() → 한글 폰트 보장
  │     ├─ apply_presentation_style() → 스타일 일괄 적용
  │     ├─ add_watermark() → 워터마크 (선택)
  │     └─ set_edit_restriction() → 편집 제한 (선택)
  └─ 7. prs.save(output_path)
```

---

## 10. 데이터 모델 (`im_document.py`)

```python
@dataclass
class IMDocumentData:
    # 기본 정보
    project_name: str              # "Project TITAN"
    company_name_kr: str           # "대상회사"
    date: str                      # "2026-02-08"

    # 섹션 구성
    im_style: IMStyle              # TITAN/COVENANT/FULL/TEASER/DM/CUSTOM
    sections: list[str]            # 활성 섹션 ID 리스트

    # 재무 데이터
    financial_statements: FinancialStatements
    segment_revenue: SegmentRevenue | None

    # 정성 데이터
    company_overview: CompanyOverview | None
    market_data: MarketData | None
    investment_highlights: list[str]

    # AI 내러티브 (LLM 생성)
    narratives: dict[str, str]     # {"executive_summary": "...", ...}

    # 차트 데이터
    charts: dict[str, list[ChartData]]

    # 브랜딩 & 보안
    brand_assets: BrandAssets | None
    number_format: NumberFormatConfig
    disclaimer_text: str
```

---

## 11. 확장성 & 커스터마이제이션

| 기능 | 설명 |
|------|------|
| **브랜드 오버라이드** | `IMDesignTokens.from_brand_assets()` — 클라이언트 컬러/로고 교체 |
| **섹션 동적 구성** | `IMStyle.CUSTOM` + `data.sections = [...]` — 원하는 섹션만 선택 |
| **숫자 표기 설정** | 통화(KRW), 단위(억원), 소수점, 음수 형식 등 |
| **TM 별칭 패턴** | 기존 렌더러의 타이틀만 변경하여 재사용 (코드 중복 제거) |
| **새 렌더러 추가** | `@register_renderer` 데코레이터로 자동 등록 — 다른 부분 영향 없음 |

---

## 12. 기술 스택

| 계층 | 기술 |
|------|------|
| PPTX 제작 | python-pptx 1.0.2 + lxml (XML 직접 조작) |
| 차트 | Plotly → Kaleido (PNG), Graphviz (다이어그램) |
| 폰트 | SUITE, Pretendard, Noto Sans KR, Inter, IBM Plex Mono |
| 이미지 | Pillow (처리), base64 data URI (임베딩) |
| 색상 추출 | Brandfetch API + K-Means 클러스터링 |
| 데이터 모델 | Pydantic (입력 검증) + dataclass (내부) |
| 비동기 | Celery + Redis (5-stage 파이프라인) |

---

## 13. 파일 구조 요약

```
im/src/design_renderer/
├── design_tokens.py                 ← 색상/폰트/레이아웃 토큰
├── im_document.py                   ← IMDocumentData 스키마
├── pipeline.py                      ← E2E 오케스트레이션
├── assets.py                        ← 폰트/이미지 경로 관리
│
├── section_renderers/               ← 32종 렌더러
│   ├── __init__.py                  (레지스트리 + get_renderer)
│   ├── base.py                      (BaseSectionRenderer ABC)
│   ├── format_utils.py              (fmt_amount, fmt_pct, fmt_multiple)
│   ├── tm_aliases.py                (TargetOverview, TargetHighlights)
│   ├── cover.py, disclaimer.py, contact.py, toc_divider.py
│   ├── deal_overview.py, executive_summary.py
│   ├── company_overview.py, business_overview.py
│   ├── investment_highlights.py     (1-5 슬라이드 동적)
│   ├── financial_analysis.py        (2-10 슬라이드 동적)
│   ├── valuation.py                 (5 슬라이드 고정)
│   ├── market_drivers.py            (Demand/Supply/MarketOutlook)
│   ├── proforma.py                  (ProformaPlan, ProformaFinancials)
│   ├── target_positioning.py
│   ├── dm_*.py                      (6종 DM 렌더러)
│   └── industry_overview.py, industry_kpi.py
│
├── pptx_engine/
│   ├── slide_factory.py             ← 5종 레이아웃 기반 슬라이드 생성
│   ├── shape_builder.py             ← add_* 컴포넌트 빌더
│   ├── font_helper.py               ← 한글 폰트 EA 설정
│   ├── template_manager.py          ← PPTX 템플릿 관리
│   ├── toc_builder.py               ← 목차 구분 슬라이드
│   ├── style_applier.py             ← 워터마크, 편집 제한
│   └── create_template.py
│
└── chart_engine/
    ├── plotly/                      ← 10종 Plotly 차트
    │   ├── themes.py                (AMICThemeFactory)
    │   ├── waterfall.py, combo.py, stacked_bar.py
    │   ├── donut.py, line.py, hbar.py, funnel.py
    │   └── sensitivity_heatmap.py, cohort_heatmap.py, treemap.py
    ├── graphviz/                    ← 3종 다이어그램
    │   ├── shareholding.py, org_chart.py, flow_diagram.py
    ├── pptx_native/                 ← 편집 가능 네이티브 차트
    │   ├── donut.py, hbar.py, line_chart.py, stacked_bar.py
    ├── config.py                    (ChartConfig, ChartColorConfig)
    └── data_transformer.py          (IMDocumentData → ChartSpec)
```
