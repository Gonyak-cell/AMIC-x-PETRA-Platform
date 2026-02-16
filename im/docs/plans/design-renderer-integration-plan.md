# IM Module 통합 계획: Deal Radar 인프라 + Sample IM 양식 + AMIC 디자인

> 작성일: 2026-02-08
> 최종 수정: 2026-02-10 21:05:56
> 상태: ✅ 전체 구현 완료 (v0.4.0, 51+ 소스 파일, 107 테스트 통과)

## Context

IM Module은 AI 기반 Information Memorandum(투자설명서) 자동 생성 시스템이다. **최종 목표**는:

1. **Sample IM의 양식/구조** (Project TITAN, Project Covenant)를 그대로 따르되
2. **AMIC 디자인** (Inter, Pretendard, IBM Plex Mono, Noto Sans KR 폰트 + AMIC 컬러)을 적용하고
3. **Deal & Regulation Radar**에서 검증된 HTML→PDF 인프라를 재사용하여 개발 속도를 높인다

IM Module은 Deal Radar(3~5페이지 주간 브리핑)보다 훨씬 복잡한 리포트(6~8섹션, 50~80페이지, 재무테이블, 차트, 조직도 등)를 생성해야 하므로, 확장 가능한 아키텍처로 재설계한다.

### 참조 프로젝트

| 프로젝트 | 경로 | 역할 |
|---------|------|------|
| Deal & Regulation Radar | `../Deal & Regulation Radar/` | HTML→PDF 인프라, AMIC 폰트/에셋 시스템 |
| Sample IM - TITAN | `sample IM/TITAN - IM - vF 251201.pptx` (59슬라이드) | SL Template 레이아웃, 섹션 구조 참조 |
| Sample IM - COVENANT | `sample IM/COVENANT - IM (KOR) - 250704 vSHARE2_feedback_JK_v4.pptx` (77슬라이드) | SL Template 레이아웃, 섹션 구조 참조 |

---

## 0. Sample IM 분석 결과 (TITAN & COVENANT)

### 0-1. 공통 레이아웃 사양 (SL Template)

TITAN(59슬라이드)과 COVENANT(77슬라이드)는 **동일한 SL Template**을 사용한다:

| 항목 | 값 |
|------|-----|
| 슬라이드 크기 | **10.83" x 7.5"** (Letter Landscape, 비율 1.444) |
| 레이아웃 3종 | `COVER` (표지 1장), `BLANK` (TOC 구분자/면책), `MAIN` (콘텐츠 전체) |
| MAIN 플레이스홀더 | idx=11 제목, idx=12 각주, idx=13 페이지번호 |
| 콘텐츠 영역 | left=0.5", top=1.07" -> right=10.33", bottom=6.5" (9.83" x 5.43") |
| 여백 | 좌우 0.5", 상단 0.6", 하단 ~1.0" (각주/페이지번호 포함) |

### 0-2. 섹션 구조 패턴

**TITAN (5섹션):**

1. Executive Summary (2 slides)
2. Investment Highlights (13 slides)
3. Market Opportunities (6 slides)
4. Business Overview (5 slides + Operations Detail 13 slides + SI Business 6 slides)
5. Financial Summary (4 slides)

**COVENANT (6섹션):**

1. Executive Summary (15 slides)
2. Investment Highlights (13 slides)
3. Value Creation Plan (14 slides)
4. Company Overview (8 slides)
5. Market Overview (6 slides)
6. Financials & Return (12 slides)

**공통 패턴:**

- 각 섹션 시작 전 **TOC 구분 슬라이드** (BLANK 레이아웃, 현재 섹션 대문자 하이라이트)
- Cover -> Disclaimer -> [TOC -> 섹션]xN -> Contact/End
- TOC 테이블: 2열 (번호 + 섹션명), 현재 섹션만 ALL CAPS

### 0-3. 타이포그래피 (SL Template 원본 -> AMIC 대체)

| 용도 | 원본 폰트 | AMIC 대체 폰트 |
|------|----------|---------------|
| 제목 (Major) | Outfit ExtraBold | **Inter** (weight 800) |
| 본문 (Minor) | Pretendard | **Pretendard** (동일 유지) |
| 콜아웃/KPI | KoPub Dotum Bold | **IBM Plex Mono** |
| 한글 본문 | Pretendard | **Pretendard** (동일 유지) |
| 특수문자 폴백 | - | **Noto Sans KR** |
| 차트 한글 텍스트 | NanumGothic (Plotly 기본) | **NanumGothic** (Plotly/Kaleido 전용, 시스템 설치 필요) |

### 0-4. 폰트 사이즈 체계 (TITAN/COVENANT 공통)

| 용도 | 크기 | 비고 |
|------|------|------|
| 섹션 대제목 (Cover) | 40pt | Inter 800 |
| 섹션 구분 제목 | 28-30pt | TOC 슬라이드 |
| TOC 타이틀 | 24pt | "TABLE OF CONTENT" |
| 슬라이드 제목 | **16pt** | MAIN 레이아웃 idx=11 |
| 요약/설명 텍스트 | **14pt Bold** | 슬라이드 상단 설명문 |
| 섹션 서브헤더 바 | **12pt Bold White** | 컬러 배경 직사각형 위 |
| KPI 라벨 | **11pt** | 주요 지표 라벨 |
| **본문 텍스트** | **10pt** | 가장 빈번 (1,600+ 사용) |
| 각주/소스 | **9pt** | 슬라이드 하단 |
| 소형 라벨/데이터 | **8pt** | 퍼센트, 수치 라벨 |
| 최소 텍스트 | 7pt | 저작권 등 |

### 0-5. 컬러 팔레트 (SL Template -> AMIC 오버레이)

| 용도 | SL 원본 | AMIC 적용 |
|------|---------|----------|
| 본문 텍스트 | `#3D3D3D` | 유지 (가독성 좋음) |
| 헤더/제목 | `#11244A` (네이비) | `#0F3A32` (AMIC 다크그린) |
| 강조 액센트 | `#539DFF` (블루) | `#26C260` (AMIC 그린) |
| 다크 네이비 | `#0A1A39` | `#0F3A32` (AMIC 다크그린) |
| 긍정 지표 | `#5CCFA0` | `#26C260` (AMIC 그린) |
| 경고/부정 | `#F25353` | `#BC2C1A` (AMIC 레드) |
| 테이블 헤더 bg | `#1E1E3E` | `#0F3A32` |
| 라이트 배경 | `#F3F9FF` | `#E8F5E9` (AMIC 라이트그린) |
| 서브헤더 바 bg | `#11244A` | `#0F3A32` |

---

## 1. 재사용 가능한 컴포넌트 분류

### 그대로 재사용 (복사 + 최소 수정)

| 컴포넌트 | 소스 | 이유 |
|---------|------|------|
| 폰트 관리 | `radar/reporting/assets.py` | AMIC 폰트 로직 100% 동일 |
| 폰트 파일 | `radar/reporting/assets/fonts/` | Inter, Pretendard, IBM Plex Mono, Noto Sans KR |
| 이미지 처리 | `radar/reporting/image_processor.py` | 모델 의존성 없는 범용 모듈 |
| WOFF2 압축 | `assets.py` 내 `_compress_font_to_woff2()` | fontTools 기반, 범용 |
| SL Template PPTX | `sample IM/TITAN - IM - vF 251201.pptx` | 마스터 레이아웃 추출용 |

### 패턴 재사용 (아키텍처 차용, 내용 재작성)

| 컴포넌트 | 소스 | 변경 사항 |
|---------|------|----------|
| 디자인 토큰 | `amic_design_tokens.py` | dataclass 구조 동일, AMIC 컬러 + TITAN/COVENANT 레이아웃 수치 |
| PDF 엔진 | `amic_report.py:1264-1352` | Playwright/WeasyPrint 이중엔진 + **Landscape Letter** 기본값 |
| CSS 생성 | `amic_report.py:138-722` | 기본 리셋/그리드/인쇄 규칙 재사용, IM 섹션용 CSS 신규 |
| TOC 구분자 | TITAN/COVENANT 패턴 | 섹션 간 TOC 슬라이드, 현재 섹션 하이라이트 |
| 슬라이드 구조 | TITAN/COVENANT `MAIN` 레이아웃 | 제목+서브헤더바+콘텐츠+각주+페이지번호 |

---

## 2. 목표 디렉토리 구조

```text
src/design_renderer/
├── __init__.py
│
├── # ── 공유 인프라 (Radar에서 이식) ──
├── assets.py                    # 폰트/이미지 base64 관리
├── assets/
│   ├── fonts/                   # AMIC 폰트 (Radar에서 복사)
│   │   ├── Inter-Variable.ttf
│   │   ├── Pretendard-{Regular,Medium,SemiBold,Bold}.otf
│   │   ├── IBMPlexMono-{Regular,Medium,SemiBold,Bold}.otf
│   │   └── NotoSansKR-Variable.ttf
│   ├── images/                  # AMIC 브랜딩 이미지
│   │   ├── amic_cover_bg.jpeg
│   │   ├── amic_logo_dark.png
│   │   └── amic_logo_white.png
│   └── templates/               # PPTX 마스터 템플릿
│       └── amic_im_template.pptx
├── image_processor.py           # 이미지 다운로드/리사이즈 (Radar 복사)
├── pdf_engine.py                # 듀얼 PDF 엔진 (Radar 추출+일반화)
│
├── # ── 디자인 시스템 (AMIC 컬러 + SL Template 수치) ──
├── design_tokens.py             # IMDesignTokens
│
├── # ── 듀얼 출력 엔진 ──
├── pptx_engine/                 # PPTX 생성 엔진
│   ├── __init__.py
│   ├── template_manager.py      # .pptx 마스터 템플릿 로드/관리
│   ├── slide_factory.py         # 레이아웃별 슬라이드 생성 (Cover/TOC/Main)
│   ├── shape_builder.py         # 텍스트박스/테이블/차트 삽입
│   ├── toc_builder.py           # TOC 구분 슬라이드 (섹션 하이라이트)
│   └── style_applier.py         # AMIC 폰트/컬러 일괄 적용
│
├── pdf_output/                  # HTML→PDF 변환 엔진
│   ├── __init__.py
│   ├── css_generator.py         # 모듈형 CSS (TITAN/COVENANT 레이아웃 재현)
│   ├── html_builder.py          # 전체 HTML 조립 + 페이지 번호
│   └── section_renderers/       # 섹션별 HTML 렌더러
│       ├── __init__.py
│       ├── cover.py
│       ├── disclaimer.py
│       ├── toc_divider.py       # TOC 구분 페이지 (섹션별 반복)
│       ├── deal_overview.py         # 거래 개요 (매각주체, 지분율, 거래 배경)
│       ├── executive_summary.py
│       ├── investment_highlights.py
│       ├── market_overview.py
│       ├── company_overview.py
│       ├── business_overview.py
│       ├── value_creation.py
│       ├── business_model.py         # SPEC 14섹션: 사업 모델
│       ├── management_team.py        # SPEC 14섹션: 조직 및 경영진
│       ├── shareholder_structure.py  # SPEC 14섹션: 주주 구성
│       ├── growth_strategy.py        # SPEC 14섹션: 성장 전략
│       ├── transaction_structure.py  # SPEC 14섹션: 거래 구조
│       ├── financial_analysis.py
│       ├── appendix.py               # SPEC 14섹션: 부록
│       └── contact.py
│
├── # ── 재사용 컴포넌트 (PPTX/PDF 공용) ──
├── components/
│   ├── __init__.py
│   ├── financial_table.py       # 재무제표 (계정계층, 다년도, CAGR)
│   ├── chart_embed.py           # Plotly/Kaleido 차트 임베딩 (Waterfall, Dual-Axis 콤보 등)
│   ├── number_formatter.py      # 숫자 표기 규칙 엔진 (단위 통일, 천단위 구분, 반올림)
│   ├── source_citation.py       # 출처 메타데이터 → 각주 자동 생성
│   ├── timeline.py              # 기업 연혁 타임라인 시각화
│   ├── kpi_card.py              # 핵심 지표 카드
│   ├── sub_header_bar.py        # 컬러 서브헤더 직사각형 (TITAN 패턴)
│   ├── org_chart.py             # Graphviz 기반 지배구조도/조직도
│   ├── content_overflow.py      # 콘텐츠 오버플로우 감지 및 자동 분할
│   └── page_elements.py         # 헤더/푸터/구분선
│
├── templates.py                 # Jinja2 템플릿 관리
├── im_document.py               # IMDocumentData 입력 스키마 정의
│
├── # ── 테스트 ──
tests/test_design_renderer/
├── __init__.py
├── test_design_tokens.py        # 디자인 토큰 단위 테스트
├── test_pptx_engine.py          # PPTX 생성 통합 테스트
├── test_pdf_output.py           # PDF 생성 통합 테스트
├── test_components.py           # 컴포넌트 단위 테스트 (테이블, KPI, 차트)
├── test_section_renderers.py    # 섹션별 렌더러 테스트
├── test_content_overflow.py     # 콘텐츠 오버플로우 처리 테스트
└── conftest.py                  # 공유 픽스처 (샘플 IMDocumentData 등)
```

---

## 3. 단계별 구현 계획

### Phase 1: 공유 인프라 이식 + PPTX 마스터 템플릿 생성

**3-1. 폰트 파일 복사** ✅ 완료 (2026-02-08)

- 소스: `Deal & Regulation Radar/radar/reporting/assets/fonts/`
- 대상: `src/design_renderer/assets/fonts/`
- 10개 파일: Inter-Variable.ttf, Pretendard x4, IBMPlexMono x4, NotoSansKR-Variable.ttf

**3-2. assets.py 이식**

- Radar `assets.py` 복사 -> `IMAGE_FILES`를 AMIC용으로 교체
- 폰트 로직 (`generate_font_face_css()` 등) 100% 유지

**3-3. image_processor.py 이식** ✅ 완료 (2026-02-08)

- 직접 복사 + `max_width`/`max_height` 파라미터화 + `embed_local_image()` + `embed_local_image_with_size()` 추가

**3-4. PPTX 마스터 템플릿 생성 (핵심)**

- TITAN PPTX에서 SL Template의 슬라이드 마스터/레이아웃 3종 추출
- python-pptx로 새 `amic_im_template.pptx` 생성:
  - **레이아웃 구조**: TITAN과 동일 (COVER, BLANK, MAIN)
  - **플레이스홀더**: 동일 idx 체계 (11=제목, 12=각주, 13=페이지번호)
  - **테마 폰트 교체**: Outfit ExtraBold -> Inter, Pretendard -> Pretendard (유지)
  - **테마 컬러 교체**: SL Navy -> AMIC Dark Green, SL Blue -> AMIC Green
  - **AMIC 로고** 삽입 (마스터 레벨 푸터 영역)
- 이 템플릿은 모든 IM 생성의 기반이 됨

**3-5. 의존성 추가** ✅ 완료 (2026-02-08)

기존 `requirements.txt`에 아래 패키지 추가 (이미 존재하는 패키지는 버전 확인만):

```text
# 신규 추가
fonttools>=4.47.0    # WOFF2 압축
brotli>=1.1.0        # WOFF2 백엔드
graphviz>=0.20.3     # 지배구조도/조직도 렌더링

# 기존 requirements.txt에 이미 존재 — 버전 호환성 확인
python-pptx==1.0.0   # PPTX 생성 엔진
weasyprint==62.0      # PDF 생성 (HTML→PDF 폴백)
playwright==1.48.0    # PDF 생성 (HTML→PDF 우선) + 브랜드 크롤링
Jinja2==3.1.4         # HTML 템플릿 렌더링
plotly==5.24.0        # 차트 생성
kaleido==0.2.1        # Plotly 정적 이미지 수출 (300DPI)
Pillow==10.4.0        # 이미지 리사이즈/처리
```

> **참고**: `setup_project.py`의 `DIRECTORIES` 리스트도 `src/design_renderer/` 하위 서브패키지 구조를 반영하도록 업데이트 필요 (Section 6 참조).

### Phase 2: 디자인 시스템 + 듀얼 엔진

**3-6. design_tokens.py 생성** ✅ 완료 (2026-02-08)

- `amic_design_tokens.py` dataclass 패턴 차용
- **TITAN/COVENANT 레이아웃 수치** 반영:
  - `IMPageLayout`: **Landscape Letter** (10.83" x 7.5") -- Portrait A4 아님!
  - 여백: left=0.5", top=0.6", right=0.5", bottom=1.0"
  - 콘텐츠 영역: 9.83" x 5.43"
- **AMIC 컬러**: `#0F3A32` (다크그린), `#26C260` (그린), `#3D3D3D` (본문)
- **AMIC 타이포그래피**: Inter(제목), Pretendard(본문), IBM Plex Mono(숫자), Noto Sans KR(폴백)
- **TITAN/COVENANT 폰트 사이즈 체계** 그대로 유지 (16pt 제목, 14pt 요약, 10pt 본문 등)
- PPTX와 PDF에서 **동일한 토큰**을 공유

**브랜드 확장 구조**:

- `IMDesignTokens`는 **기본값으로 AMIC 디자인**을 사용하되, `brand_extractor` 모듈과 연동하여 **클라이언트별 브랜딩 오버라이드**를 지원
- `from_brand_assets(brand: BrandAssets) -> IMDesignTokens` 팩토리 메서드 제공
- `BrandAssets`는 `src/brand_extractor/`에서 추출한 로고, Primary/Secondary Color, 보조색 팔레트를 포함
- 오버라이드 범위: 컬러 팔레트 전체, 로고 이미지 (폰트 체계는 AMIC 고정)
- 브랜드 미지정 시 AMIC 기본 테마로 폴백

```python
@dataclass
class IMDesignTokens:
    # 컬러 (AMIC 기본값, 브랜드별 오버라이드 가능)
    color_primary: str = "#0F3A32"        # AMIC 다크그린
    color_accent: str = "#26C260"         # AMIC 그린
    color_text: str = "#3D3D3D"           # 본문
    color_negative: str = "#BC2C1A"       # 경고/부정
    color_light_bg: str = "#E8F5E9"       # 라이트 배경
    # 폰트 (AMIC 고정)
    font_heading: str = "Inter"
    font_body: str = "Pretendard"
    font_mono: str = "IBM Plex Mono"
    font_fallback: str = "Noto Sans KR"
    font_chart: str = "NanumGothic"       # Plotly/Kaleido 전용
    # 레이아웃 (TITAN/COVENANT 고정)
    page_width: float = 10.83             # inches
    page_height: float = 7.5              # inches
    ...

    @classmethod
    def from_brand_assets(cls, brand: "BrandAssets") -> "IMDesignTokens":
        """brand_extractor 결과로 컬러/로고를 오버라이드"""
        ...
```

**3-7. pdf_engine.py 생성**

- Radar `amic_report.py:1264-1352` 에서 추출
- 기본값: **Landscape Letter** (10.83" x 7.5") -- TITAN/COVENANT과 동일
- Playwright 우선 + WeasyPrint 폴백

**3-8. pptx_engine/ 생성 (핵심)**

| 파일 | 역할 |
|------|------|
| `template_manager.py` | `amic_im_template.pptx` 로드, 레이아웃 참조 반환 |
| `slide_factory.py` | Cover/TOC/Main 슬라이드 생성, 플레이스홀더 값 주입 |
| `shape_builder.py` | 텍스트박스, 테이블, 이미지, 차트 shape 추가 |
| `toc_builder.py` | TOC 구분 슬라이드 생성 (현재 섹션 ALL CAPS 하이라이트) |
| `style_applier.py` | AMIC 폰트/컬러를 모든 run에 일괄 적용 |

`slide_factory.py` 핵심 API:

```python
def add_cover_slide(prs, project_name, subtitle, date, tokens) -> Slide
def add_disclaimer_slide(prs, disclaimer_text, tokens) -> Slide
def add_toc_divider(prs, sections, active_section_idx, tokens) -> Slide
def add_content_slide(prs, title, tokens) -> Slide  # 빈 MAIN 슬라이드 반환
def add_contact_slide(prs, contact_info, tokens) -> Slide
```

`shape_builder.py` 핵심 API (TITAN/COVENANT에서 추출한 shape 패턴):

```python
def add_summary_textbox(slide, text, tokens)        # top=1.07", 14pt Bold
def add_sub_header_bar(slide, text, tokens)          # 컬러 직사각형 + 12pt Bold White
def add_body_textbox(slide, text, left, top, w, h)   # 10pt 본문
def add_financial_table(slide, data, tokens)          # col1=2.6" + 7x0.91" 패턴
def add_kpi_grid(slide, metrics, tokens)              # 지표 카드 그리드
def add_chart_image(slide, image_path, left, top, w, h)  # 차트 이미지 삽입
```

### Phase 3: CSS/HTML 프레임워크 (PDF 출력용)

**3-9. css_generator.py -- TITAN/COVENANT 레이아웃을 HTML/CSS로 재현**

- `@page { size: 10.83in 7.5in; }` -- PPTX와 동일 크기
- Radar 재사용: 리셋, 12-column 그리드, print-color-adjust, page-break
- TITAN 패턴 CSS 신규:
  - `.slide` 클래스: 10.83"x7.5" 고정, overflow hidden
  - `.slide-title`: top=0.6", 16pt Inter 800, AMIC 다크그린
  - `.sub-header-bar`: AMIC 다크그린 bg, 12pt Bold White
  - `.summary-text`: top=1.07", 14pt Bold
  - `.content-area`: top=1.07"~bottom=6.5"
  - `.slide-footer`: 각주(left=1.86", 8pt) + 페이지번호(right=10", 10pt)
  - `.toc-slide`: 전체 배경 + 2열 테이블 + 현재 섹션 하이라이트

**3-10. section_renderers/ -- TITAN/COVENANT 섹션 구조 기반**

- 섹션 목록은 프로젝트마다 다를 수 있으므로 **동적 구성** 지원
- **전체 섹션 목록** (SPEC 14섹션 + TITAN/COVENANT 합집합, 프로젝트별 동적 선택):

  | # | 섹션 | 렌더러 파일 | 출처 | 비고 |
  |---|------|-----------|------|------|
  | 1 | Cover | `cover.py` | 공통 | 표지 1장 |
  | 2 | Disclaimer | `disclaimer.py` | 공통 | 면책조항 |
  | 3 | TOC Divider | `toc_divider.py` | TITAN/COVENANT | 섹션별 반복 |
  | 4 | Deal Overview | `deal_overview.py` | SPEC + 공통 | 매각주체, 지분율, 거래 배경, 일정 |
  | 5 | Executive Summary | `executive_summary.py` | TITAN/COVENANT | 다중 슬라이드 |
  | 6 | Investment Highlights | `investment_highlights.py` | TITAN/COVENANT | 다중 슬라이드 |
  | 7 | Company Overview | `company_overview.py` | TITAN/COVENANT + SPEC | 연혁, 비즈니스모델 |
  | 8 | Business Model | `business_model.py` | SPEC | 수익 구조, 밸류체인 |
  | 9 | Market Overview | `market_overview.py` | TITAN/COVENANT | TAM/SAM/SOM, 경쟁 |
  | 10 | Business Overview | `business_overview.py` | TITAN | 사업부별 상세 |
  | 11 | Value Creation Plan | `value_creation.py` | COVENANT | 선택적 |
  | 12 | Growth Strategy | `growth_strategy.py` | SPEC | 확장→신규→M&A |
  | 13 | Financial Analysis | `financial_analysis.py` | TITAN/COVENANT + SPEC | 가장 복잡, 다중 슬라이드 |
  | 14 | Management Team | `management_team.py` | SPEC | 조직도 (Graphviz) 포함 |
  | 15 | Shareholder Structure | `shareholder_structure.py` | SPEC | 지분구조, 지배구조도 |
  | 16 | Transaction Structure | `transaction_structure.py` | SPEC | 딜 구조, 밸류에이션 |
  | 17 | Appendix | `appendix.py` | SPEC | 상세 재무제표, 보조 자료 |
  | 18 | Contact | `contact.py` | 공통 | 연락처/종료 |

- 각 섹션: `render_html()` + `render_pptx()` 듀얼 메서드
- **동적 구성**: 프로젝트별로 `IMDocumentData.sections` 리스트에서 포함할 섹션을 선택. TITAN식(5섹션), COVENANT식(6섹션), SPEC 전체(14섹션) 등 유연 대응

### Phase 4: 컴포넌트 + 통합

**3-11. components/ -- PPTX와 PDF 공용**

| 컴포넌트 | 역할 | TITAN/COVENANT 참고 |
|---------|------|-------------------|
| `financial_table.py` | 재무제표 테이블 | col1=2.6"(라벨) + 7x0.91"(기간), row=0.26" |
| `chart_embed.py` | Plotly→이미지→삽입 (금융 특수 차트 포함) | 아래 3-11a 참조 |
| `number_formatter.py` | 숫자 표기 규칙 엔진 | 아래 3-15 참조 |
| `source_citation.py` | 출처 메타데이터→각주 자동 생성 | 아래 3-16 참조 |
| `timeline.py` | 기업 연혁 타임라인 시각화 | Matplotlib/SVG 기반, 연도별 이벤트 배치 |
| `kpi_card.py` | 핵심 지표 카드 | 11pt 라벨, 20pt 숫자 (IBM Plex Mono) |
| `sub_header_bar.py` | 컬러 서브헤더 | AMIC 다크그린 bg, 12pt Bold White |
| `page_elements.py` | 헤더/푸터/구분선 | idx=11/12/13 플레이스홀더 패턴 |
| `org_chart.py` | Graphviz 기반 지배구조도/조직도 | PPTX: SVG→PNG 삽입, PDF: SVG 인라인 |
| `content_overflow.py` | 콘텐츠 오버플로우 감지 및 자동 분할 | 아래 3-13 참조 |

**3-11a. chart_embed.py -- 금융 특수 차트 유형**

Plotly/Kaleido 기반으로 IM에 필수적인 금융 차트 유형을 명시적으로 지원한다:

| 차트 유형 | Plotly 모듈 | 용도 | 참고 |
|---------|-----------|------|------|
| **Waterfall** | `plotly.graph_objects.Waterfall` | 영업이익 변동 원인 분석 (매출 증가/원가 상승/판관비 효과) | SPEC 리서치 PDF에서 필수 언급 |
| **Dual-Axis Combo** (막대+꺾은선) | `make_subplots(specs=secondary_y)` | 매출(막대) + 이익률(꺾은선) 동시 표현, Operating Leverage 시각화 | 좌축 금액, 우축 % |
| **Stacked Bar** | `plotly.express.bar` | 사업부별/채널별 매출 구성비 추이 | 세그먼트 분석 |
| **Donut/Pie** | `plotly.express.pie` | 시장 점유율, 매출 구성비 | hole=0.4 도넛 기본 |
| **Line (Multi-series)** | `plotly.graph_objects.Scatter` | 다년도 KPI 추이 (CAGR 표기 포함) | 데이터 레이블 자동 배치 |
| **Horizontal Bar** | `plotly.express.bar_horizontal` | 경쟁사 비교, 벤치마크 지표 | 순위형 시각화 |

```python
# components/chart_embed.py 핵심 API
def create_waterfall_chart(data: dict, tokens: IMDesignTokens) -> bytes:
    """영업이익 Bridge 차트 (PNG 300DPI)"""
    ...

def create_combo_chart(bar_data: dict, line_data: dict, tokens: IMDesignTokens) -> bytes:
    """이중축 콤보 차트: 좌축 막대(금액) + 우축 꺾은선(비율)"""
    ...

def create_chart(chart_type: str, data: dict, tokens: IMDesignTokens) -> bytes:
    """범용 차트 생성 팩토리. chart_type: waterfall|combo|stacked_bar|donut|line|hbar"""
    ...

def embed_chart_pptx(slide, chart_bytes: bytes, left, top, w, h):
    """PPTX 슬라이드에 차트 이미지 삽입"""
    ...

def embed_chart_html(chart_bytes: bytes) -> str:
    """HTML용 base64 <img> 태그 생성"""
    ...
```

모든 차트는 `IMDesignTokens`의 컬러 팔레트를 적용하고, 한글 축 라벨에는 NanumGothic 폰트를 사용한다.

**3-12. 엔드투엔드 파이프라인**

```text
IMDocumentData
    ├─> pptx_engine/ -> amic_im_template.pptx 기반 -> .pptx 출력
    └─> pdf_output/  -> HTML+CSS 생성 -> pdf_engine.py -> .pdf 출력
```

두 경로 모두 **동일한 design_tokens.py**와 **동일한 components/**를 사용하므로 시각적 일관성 보장.

**3-13. 콘텐츠 오버플로우 및 동적 레이아웃 처리**

TITAN/COVENANT에서 콘텐츠 영역은 9.83"×5.43"로 고정되어 있다. AI가 생성한 콘텐츠가 이 영역을 초과할 경우의 처리 전략:

| 전략 | 조건 | 동작 |
|------|------|------|
| **자동 분할** | 텍스트/테이블이 콘텐츠 영역 높이 초과 | 다음 슬라이드로 자동 분할, 제목에 "(cont'd)" 추가 |
| **폰트 축소** | 콘텐츠가 영역의 110~130% | 10pt→9pt→8pt 단계적 축소 (7pt 하한) |
| **테이블 분할** | 재무 테이블 행 수 초과 | 행 기준으로 분할, 헤더 반복 |
| **차트 리사이즈** | 차트+텍스트 조합 | 차트 높이를 콘텐츠 영역의 60%로 제한 |

```python
# components/content_overflow.py 핵심 API
def estimate_content_height(elements: list, tokens: IMDesignTokens) -> float:
    """콘텐츠 요소들의 예상 높이(inches) 계산"""
    ...

def split_content_to_slides(elements: list, max_height: float, tokens: IMDesignTokens) -> list[list]:
    """콘텐츠를 슬라이드 단위로 분할"""
    ...

def auto_adjust_font_size(elements: list, max_height: float, min_pt: int = 7) -> int:
    """영역에 맞도록 폰트 크기 자동 조정, 최소 7pt"""
    ...
```

**3-15. 숫자 표기 규칙 엔진 (number_formatter.py)**

IM 문서 전체에서 숫자의 가독성과 전문성을 보장하는 포맷팅 모듈. SPEC PDF("완전 자동화 IM 제작 시스템 설계 및 구현 요건") 섹션 7의 요건을 구현한다.

| 규칙 | 설명 | 예시 |
|------|------|------|
| **단위 통일** | 보고서 전체에서 금액 단위를 일관 적용 (억원/백만원/$M) | `5,243,000,000` → `5,243억원` |
| **천단위 구분** | 3자리마다 콤마 삽입 | `1234567` → `1,234,567` |
| **소수점/반올림** | 백만 이상은 소수 1자리, 퍼센트는 소수 1자리 통일 | `12.37%` → `12.4%` |
| **유효숫자** | 추정치는 2~3자리 유효숫자, "약" 접두사 | `4,351,287$` → `약 4.4백만$` |
| **오른쪽 정렬** | 표 내 숫자는 우측 정렬로 자릿수 시각 비교 용이 | CSS/PPTX 셀 정렬 |
| **조건부 포맷팅** | 양수=녹색↑, 음수=적색↓, N/A 통일 | YoY `+15.2%` (녹), `-3.1%` (적) |
| **통화 기호** | 원화(₩)/달러($)/유로(€) 일관 표기 | 문서 설정에 따라 전역 적용 |

```python
# components/number_formatter.py 핵심 API
@dataclass
class NumberFormatConfig:
    """문서 전역 숫자 표기 설정"""
    currency: str = "KRW"                # KRW | USD | EUR
    scale: str = "억원"                   # 억원 | 백만원 | $M | $B
    decimal_places_pct: int = 1           # 퍼센트 소수 자릿수
    decimal_places_amount: int = 0        # 금액 소수 자릿수
    thousands_sep: str = ","              # 천단위 구분자
    negative_format: str = "minus"        # minus (-100) | parens ((100))
    na_display: str = "N/A"              # 값 없음 표시

def format_currency(value: float, config: NumberFormatConfig) -> str:
    """금액 포맷팅: 1_234_567_890 → '12.3억원'"""
    ...

def format_percentage(value: float, config: NumberFormatConfig) -> str:
    """퍼센트 포맷팅: 0.1237 → '12.4%'"""
    ...

def format_growth_indicator(value: float, config: NumberFormatConfig) -> tuple[str, str]:
    """성장률 포맷팅 + 색상 반환: ('+15.2%', 'positive') or ('-3.1%', 'negative')"""
    ...

def format_number(value: float, config: NumberFormatConfig, unit: str = "") -> str:
    """범용 숫자 포맷팅"""
    ...

def apply_table_number_format(table_data: list[list], config: NumberFormatConfig) -> list[list]:
    """테이블 전체에 숫자 포맷 일괄 적용"""
    ...
```

`NumberFormatConfig`는 `IMDocumentData` 생성 시 전역 설정으로 지정되며, `financial_table.py`, `kpi_card.py`, 각 `section_renderer`에서 공유한다.

**3-16. 출처 메타데이터 → 각주 자동 생성 (source_citation.py)**

IM 문서의 신뢰성을 높이기 위해, 크롤링/API로 수집된 데이터의 출처를 각주로 자동 삽입하는 모듈. SPEC PDF에서 "출처 표기와 각주"를 신뢰성 제고 핵심 요소로 명시.

```python
# components/source_citation.py 핵심 API
@dataclass
class SourceCitation:
    """출처 메타데이터"""
    source_name: str          # "금융감독원 전자공시시스템", "네이버 뉴스"
    url: str | None           # 원본 URL (있는 경우)
    access_date: str          # 접근일 "2026-02-08"
    document_title: str | None  # 리포트명 등

def format_footnote(citations: list[SourceCitation], style: str = "compact") -> str:
    """각주 텍스트 생성: '출처: DART (2026.02), 한국은행 경제통계시스템'"""
    ...

def assign_footnote_numbers(slide_citations: list[SourceCitation]) -> dict[int, str]:
    """슬라이드별 각주 번호 매핑: {1: 'DART', 2: '통계청'}"""
    ...

def render_footnote_pptx(slide, citations: list[SourceCitation], tokens: IMDesignTokens):
    """PPTX idx=12 각주 플레이스홀더에 출처 삽입 (9pt)"""
    ...

def render_footnote_html(citations: list[SourceCitation], tokens: IMDesignTokens) -> str:
    """HTML .slide-footer 영역에 출처 각주 HTML 생성"""
    ...
```

각 섹션 렌더러는 사용한 데이터의 `SourceCitation` 리스트를 반환하고, `page_elements.py`의 푸터 렌더링에서 `source_citation.py`를 호출하여 각주를 자동 배치한다.

**3-17. 데이터 리액티브 업데이트 메커니즘**

IM 문서에서 동일 데이터가 여러 섹션에 걸쳐 참조된다 (예: 매출 CAGR이 Executive Summary, Investment Highlights, Financial Analysis에 모두 등장). 재무 데이터 변경 시 관련 차트/텍스트/KPI가 자동 갱신되어야 한다.

**설계 원칙**: `IMDocumentData`를 **단일 진실 원천(Single Source of Truth)**으로 사용하고, 렌더러는 항상 원본 데이터에서 실시간으로 값을 읽는다.

| 전략 | 구현 방식 | 대상 |
|------|---------|------|
| **지연 바인딩** | 렌더러가 `IMDocumentData`에서 값을 캐시하지 않고, 렌더링 시점에 항상 참조 | 모든 섹션 |
| **파생 지표 중앙 계산** | CAGR, YoY, 마진율 등은 `number_formatter.py`에서 계산 후 `IMDocumentData.derived_metrics`에 저장 | 재무 관련 섹션 |
| **교차 검증** | 렌더링 완료 후 동일 지표가 여러 슬라이드에 다른 값으로 표기되었는지 검사 | E2E 파이프라인 |

```python
# im_document.py에 추가
@dataclass
class IMDocumentData:
    ...
    # ── 파생 지표 (자동 계산, 렌더러 간 공유) ──
    derived_metrics: dict | None = None   # {"revenue_cagr_3y": 0.152, "ebitda_margin": 0.234, ...}

    def compute_derived_metrics(self) -> None:
        """financial_statements에서 CAGR, YoY, 마진율 등 파생 지표 일괄 계산"""
        ...

    def validate_consistency(self, rendered_values: dict[str, list]) -> list[str]:
        """렌더링된 슬라이드들에서 동일 지표의 값 불일치 검출. 경고 메시지 리스트 반환"""
        ...
```

**3-14. IMDocumentData 입력 스키마** ✅ 완료 (2026-02-08)

모든 렌더러의 입력이 되는 통합 데이터 모델. SPEC.md의 필수 입력 필드를 모두 포함:

```python
# im_document.py
@dataclass
class IMDocumentData:
    # ── 기본 정보 ──
    project_name: str                    # 프로젝트명 (예: "Project TITAN")
    company_name_kr: str                 # 기업명 (한글)
    company_name_en: str                 # 기업명 (영문)
    corp_code: str                       # 법인등록번호 (DART용)
    website_url: str                     # 홈페이지 URL (브랜드 추출용)
    date: str                            # IM 작성일

    # ── 섹션 구성 ──
    sections: list[str]                  # 포함할 섹션 ID 리스트 (동적 구성)
    # 예: ["executive_summary", "investment_highlights", "company_overview",
    #       "market_overview", "financial_analysis", "contact"]

    # ── 재무 데이터 ──
    financial_statements: dict           # 연결/별도 재무제표 (3~5년)
    management_financials: dict | None   # 관리회계 기준 상세 재무
    segment_revenue: dict | None         # 사업부별 매출 내역
    key_customers: list[str] | None      # 주요 고객사

    # ── 딜 구조 ──
    deal_structure: dict | None          # 구주/신주 규모, 밸류에이션 범위
    transaction_type: str | None         # "M&A" | "IPO" | "투자유치" 등

    # ── 정성 데이터 ──
    company_overview: dict | None        # 연혁, 사업모델, 조직 등
    market_data: dict | None             # 시장 규모, 성장률, 경쟁사
    investment_highlights: list[str] | None  # 핵심 투자 포인트
    growth_strategy: dict | None         # 성장 전략

    # ── 인적 자원 ──
    management_team: list[dict] | None   # 경영진 정보
    org_structure: dict | None           # 조직도 데이터 (Graphviz용)
    shareholder_structure: dict | None   # 지분 구조

    # ── AI 생성 내러티브 ──
    narratives: dict[str, str] | None    # 섹션별 AI 생성 텍스트

    # ── 브랜딩 ──
    brand_assets: "BrandAssets | None"   # 브랜드 추출 결과 (None이면 AMIC 기본)

    # ── 차트 데이터 ──
    charts: dict[str, Any] | None        # 섹션별 차트 데이터/이미지 경로

    # ── 숫자 표기 설정 ──
    number_format: "NumberFormatConfig | None"  # None이면 KRW/억원 기본값

    # ── 출처 메타데이터 ──
    source_citations: dict[str, list["SourceCitation"]] | None  # 섹션별 출처 리스트

    # ── 파생 지표 (자동 계산) ──
    derived_metrics: dict | None = None  # compute_derived_metrics()로 일괄 계산
```

---

## 4. 핵심 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 페이지 크기 | **Landscape Letter (10.83"x7.5")** | TITAN/COVENANT SL Template과 동일 (Portrait A4 아님) |
| 출력 형식 | **PPTX (1차) + PDF (2차)** | 실무에서 PPTX 편집 후 PDF 공유가 표준 워크플로우 |
| PPTX 생성 방식 | **마스터 템플릿 기반** python-pptx | SL Template의 레이아웃/플레이스홀더를 그대로 활용 |
| PDF 생성 방식 | **HTML->PDF** (Playwright/WeasyPrint) | Radar에서 검증된 파이프라인 재사용 |
| 폰트 시스템 | **AMIC 폰트** (Inter, Pretendard, IBM Plex Mono, Noto Sans KR) | PPTX: 테마 폰트로 설정, PDF: WOFF2 base64 임베딩 |
| 컬러 시스템 | **AMIC 컬러** (다크그린/그린/레드) | SL Template 네이비/블루를 AMIC 그린 계열로 교체 |
| 섹션 구성 | **동적** (프로젝트별 섹션 선택 가능) | TITAN 5섹션, COVENANT 6섹션 등 유연 대응 |
| TOC 패턴 | **TITAN/COVENANT 방식** 그대로 | 섹션 시작마다 TOC 구분 슬라이드, 현재 섹션 하이라이트 |
| 코드 공유 | Radar에서 복사 후 독립 진화 | 프로젝트 방향이 크게 다름 |
| 차트 삽입 방식 | **이미지 삽입** (Plotly→PNG 300DPI→삽입) | 네이티브 PPTX 차트는 스타일 제어 한계, Plotly 이미지가 시각적 일관성 우수. 네이티브 차트는 향후 편집 가능 옵션으로 고려 |
| 차트 한글 폰트 | **NanumGothic** (Plotly/Kaleido 전용) | 본문 Pretendard와 별도로, Plotly 렌더링 호환성이 검증된 NanumGothic 사용 |
| 브랜딩 전략 | **AMIC 기본 + 클라이언트 오버라이드** | `IMDesignTokens`는 AMIC 기본값, `brand_extractor` 결과로 컬러/로고 오버라이드 가능. 폰트 체계는 AMIC 고정 |
| 조직도/구조도 | **Graphviz DOT→SVG/PNG** | 지배구조도·조직도를 Graphviz로 생성, PPTX: PNG 삽입, PDF: SVG 인라인 |
| 콘텐츠 오버플로우 | **자동 분할 + 폰트 축소** | AI 생성 콘텐츠가 슬라이드 영역 초과 시 자동 분할 (7pt 하한) |
| IM 섹션 범위 | **SPEC 14섹션 풀셋** (동적 선택) | TITAN 5섹션, COVENANT 6섹션은 서브셋. 렌더러는 14섹션 전체 구현, 프로젝트별 선택 |
| 출력물 보안 | **PDF 암호화 + 워터마크 옵션** | 민감 재무 데이터 보호: PDF 비밀번호, "CONFIDENTIAL" 워터마크, PPTX 편집 제한 |
| 숫자 표기 | **전역 NumberFormatConfig** | 단위 통일(억원/$M), 천단위 구분, 소수점 반올림, 조건부 포맷팅을 문서 전체에 일관 적용 |
| 금융 차트 유형 | **6종 명시 지원** (Waterfall/Combo/Stacked/Donut/Line/HBar) | SPEC 리서치 PDF에서 필수 요구. Plotly `Waterfall` + `make_subplots(secondary_y)` 이중축 콤보 |
| 출처 각주 | **source_citation.py 자동 생성** | 크롤링/API 데이터의 출처 메타데이터를 각 슬라이드 각주(idx=12)에 자동 삽입, 문서 신뢰성 제고 |
| 데이터 일관성 | **지연 바인딩 + 교차 검증** | IMDocumentData를 단일 진실 원천으로, 파생 지표 중앙 계산, 렌더링 후 동일 지표 값 불일치 검사 |
| 기업 연혁 시각화 | **timeline.py 타임라인 컴포넌트** | 연도별 이벤트를 수평/수직 타임라인으로 자동 시각화 (Company Overview 섹션용) |
| Deal Overview 섹션 | **deal_overview.py 신규 렌더러** | 표준 IM 목차의 첫 번째 섹션. 매각주체, 지분율, 거래 배경, 일정 등을 템플릿 문장으로 구성 |

---

## 5. 검증 방법

1. **PPTX 템플릿 검증**: `amic_im_template.pptx`를 PowerPoint에서 열어 3종 레이아웃 확인, AMIC 폰트/컬러 적용 확인
2. **TITAN 비교 테스트**: TITAN IM과 동일 데이터로 PPTX 생성 -> 레이아웃/폰트사이즈/위치가 일치하는지 시각 비교
3. **폰트 렌더링 테스트**: 한글(Pretendard), 영어(Inter), 숫자(IBM Plex Mono), 특수문자(Noto Sans KR)
4. **PDF<->PPTX 일관성**: 동일 데이터 -> PPTX와 PDF 출력물의 시각적 일관성 비교
5. **PDF 엔진 테스트**: Playwright와 WeasyPrint 각각으로 동일 HTML 변환
6. **섹션 동적 구성 테스트**: 5섹션(TITAN식), 6섹션(COVENANT식) 각각 생성 확인
7. **재무 테이블 테스트**: 다년도 재무제표가 col1=2.6" + 7x0.91" 패턴으로 정확히 렌더링되는지
8. **콘텐츠 오버플로우 테스트**: 긴 텍스트/대형 테이블이 자동 분할되는지, 폰트 축소 하한(7pt) 준수 확인
9. **브랜드 오버라이드 테스트**: AMIC 기본 테마와 커스텀 브랜드 테마 각각으로 출력물 생성
10. **조직도/구조도 테스트**: Graphviz로 생성한 조직도가 PPTX/PDF에 정상 삽입되는지
11. **보안 테스트**: PDF 암호화, 워터마크 적용, PPTX 편집 제한 기능 동작 확인
12. **숫자 포맷팅 테스트**: `NumberFormatConfig` 설정별로 금액/퍼센트/성장률이 올바르게 포맷팅되는지 (KRW 억원, USD $M 등)
13. **금융 차트 테스트**: Waterfall, Dual-Axis Combo 등 6종 차트가 AMIC 컬러로 300DPI 렌더링되는지
14. **출처 각주 테스트**: `SourceCitation` 메타데이터가 각 슬라이드 각주 영역에 올바르게 삽입되는지
15. **데이터 일관성 테스트**: 동일 지표(매출 CAGR 등)가 여러 섹션에서 같은 값으로 표기되는지 `validate_consistency()` 검증
16. **타임라인 테스트**: 기업 연혁 데이터가 수평/수직 타임라인으로 PPTX/PDF에 정상 렌더링되는지
17. **Deal Overview 테스트**: 거래 개요 섹션이 매각주체, 지분율, 배경 등 필수 필드로 정상 생성되는지

### 5-1. 자동화 테스트 파일 매핑

| 테스트 파일 | 검증 대상 | 핵심 테스트 케이스 |
|------------|----------|-----------------|
| `tests/test_design_renderer/test_design_tokens.py` | `design_tokens.py` | AMIC 기본값, 브랜드 오버라이드, 폰트/컬러 유효성 |
| `tests/test_design_renderer/test_pptx_engine.py` | `pptx_engine/` 전체 | Cover/TOC/Main 슬라이드 생성, 플레이스홀더 주입, 레이아웃 좌표 |
| `tests/test_design_renderer/test_pdf_output.py` | `pdf_output/` 전체 | HTML 조립, CSS 페이지 크기, Playwright/WeasyPrint 듀얼 변환 |
| `tests/test_design_renderer/test_components.py` | `components/` | 재무 테이블 열 너비, KPI 카드 레이아웃, 차트 삽입 |
| `tests/test_design_renderer/test_section_renderers.py` | `section_renderers/` | 14섹션 각각 HTML+PPTX 렌더링, 동적 섹션 조합 |
| `tests/test_design_renderer/test_content_overflow.py` | `content_overflow.py` | 높이 초과 감지, 자동 분할, 폰트 축소 (하한 7pt) |
| `tests/test_design_renderer/test_number_formatter.py` | `number_formatter.py` | KRW/USD 포맷, 천단위, 소수점, 조건부 색상, 테이블 일괄 적용 |
| `tests/test_design_renderer/test_source_citation.py` | `source_citation.py` | 각주 번호 매핑, PPTX/HTML 각주 렌더링, 빈 출처 처리 |
| `tests/test_design_renderer/test_chart_types.py` | `chart_embed.py` | Waterfall, Dual-Axis Combo, Donut 등 6종 차트 렌더링 |
| `tests/test_design_renderer/test_data_consistency.py` | `im_document.py` | 파생 지표 계산, 교차 검증, 값 불일치 검출 |
| `tests/test_design_renderer/conftest.py` | 공유 픽스처 | 샘플 `IMDocumentData`, 테스트용 재무 데이터, `NumberFormatConfig` |

---

## 6. 수정 대상 파일 목록

### Radar에서 복사/이식

- `Deal & Regulation Radar/radar/reporting/assets.py` -> `src/design_renderer/assets.py`
- `Deal & Regulation Radar/radar/reporting/assets/fonts/` -> `src/design_renderer/assets/fonts/`
- `Deal & Regulation Radar/radar/reporting/image_processor.py` -> `src/design_renderer/image_processor.py`
- `Deal & Regulation Radar/radar/reporting/amic_report.py` (PDF 엔진 부분만) -> `src/design_renderer/pdf_engine.py`
- `Deal & Regulation Radar/radar/reporting/amic_design_tokens.py` (구조만) -> `src/design_renderer/design_tokens.py`

### Sample IM에서 추출

- `sample IM/TITAN - IM - vF 251201.pptx` -> 마스터 레이아웃 추출 -> `assets/templates/amic_im_template.pptx`

### 신규 생성 파일

- `src/design_renderer/design_tokens.py` -- AMIC 컬러 + TITAN/COVENANT 수치
- `src/design_renderer/pdf_engine.py`
- `src/design_renderer/pptx_engine/__init__.py`
- `src/design_renderer/pptx_engine/template_manager.py`
- `src/design_renderer/pptx_engine/slide_factory.py`
- `src/design_renderer/pptx_engine/shape_builder.py`
- `src/design_renderer/pptx_engine/toc_builder.py`
- `src/design_renderer/pptx_engine/style_applier.py`
- `src/design_renderer/pdf_output/__init__.py`
- `src/design_renderer/pdf_output/css_generator.py`
- `src/design_renderer/pdf_output/html_builder.py`
- `src/design_renderer/pdf_output/section_renderers/*.py`
- `src/design_renderer/components/*.py` (10개 + `__init__.py` — financial_table, chart_embed, number_formatter, source_citation, timeline, kpi_card, sub_header_bar, org_chart, content_overflow, page_elements)
- `src/design_renderer/templates.py`
- `src/design_renderer/im_document.py` -- IMDocumentData 입력 스키마
- `src/design_renderer/pdf_output/section_renderers/business_model.py`
- `src/design_renderer/pdf_output/section_renderers/management_team.py`
- `src/design_renderer/pdf_output/section_renderers/shareholder_structure.py`
- `src/design_renderer/pdf_output/section_renderers/growth_strategy.py`
- `src/design_renderer/pdf_output/section_renderers/transaction_structure.py`
- `src/design_renderer/pdf_output/section_renderers/appendix.py`
- `src/design_renderer/pdf_output/section_renderers/business_overview.py`
- `src/design_renderer/pdf_output/section_renderers/deal_overview.py`
- `src/design_renderer/components/number_formatter.py`
- `src/design_renderer/components/source_citation.py`
- `src/design_renderer/components/timeline.py`

### 신규 테스트 파일

- `tests/test_design_renderer/__init__.py`
- `tests/test_design_renderer/conftest.py`
- `tests/test_design_renderer/test_design_tokens.py`
- `tests/test_design_renderer/test_pptx_engine.py`
- `tests/test_design_renderer/test_pdf_output.py`
- `tests/test_design_renderer/test_components.py`
- `tests/test_design_renderer/test_section_renderers.py`
- `tests/test_design_renderer/test_content_overflow.py`
- `tests/test_design_renderer/test_number_formatter.py`
- `tests/test_design_renderer/test_source_citation.py`
- `tests/test_design_renderer/test_chart_types.py`
- `tests/test_design_renderer/test_data_consistency.py`

### 수정 파일

- `requirements.txt` -- `fonttools>=4.47.0`, `brotli>=1.1.0`, `graphviz>=0.20.3` 추가 (기존 패키지 버전 호환성 확인)
- `setup_project.py` -- `DIRECTORIES` 리스트에 `src/design_renderer/` 하위 서브패키지 반영 (`pptx_engine/`, `pdf_output/`, `pdf_output/section_renderers/`, `components/`, `assets/fonts/`, `assets/images/`, `assets/templates/`), `init_dirs` 리스트 업데이트

---

## 7. 마일스톤 및 타임라인 매핑

본 계획의 Phase 1~4는 전체 프로젝트 로드맵(IM_개발_로드맵.xlsx)의 **Phase 4: 시각화/디자인** (W11~W17)에 해당한다.

| 본 계획 Phase | 전체 로드맵 매핑 | 목표 주차 | 관련 마일스톤 |
|-------------|--------------|---------|------------|
| Phase 1: 공유 인프라 이식 + PPTX 템플릿 | 로드맵 P4 시작 | W11~W12 | — |
| Phase 2: 디자인 시스템 + 듀얼 엔진 | 로드맵 P4 중반 | W12~W13 | — |
| Phase 3: CSS/HTML 프레임워크 | 로드맵 P4 중반 | W13~W15 | **M4: 차트 엔진 완성** (W14) |
| Phase 4: 컴포넌트 + 통합 | 로드맵 P4 완료 | W15~W17 | **M5: PPTX IM 초안 생성** (W17) |

### 선행 의존성

- **Phase 1 시작 전 필요**: Phase 1 환경 구축 완료 (M1, W3), Radar 프로젝트 접근 가능
- **Phase 3 렌더러 구현 시 필요**: Financial Engine MVP (M3, W11) — 재무 테이블 렌더러에 실제 데이터 필요
- **Phase 4 통합 테스트 시 필요**: Chart Engine 완성 (M4, W14) — 차트 임베딩 테스트
- **전체 E2E 테스트**: AI 내러티브 생성 (M6, W21) + 전체 파이프라인 (M7, W24)

### 프로그레스 트래커 대응

프로그레스 트래커(IM_프로그레스_트래커.xlsx)의 **P4_시각화디자인** 시트 태스크와의 매핑:

| 트래커 태스크 | 본 계획 대응 |
|-------------|-----------|
| [4-C] PPTX 마스터 템플릿 (14→15) | Phase 1: 3-4 PPTX 마스터 템플릿 생성 |
| [4-D] 슬라이드 팩토리 (17) | Phase 2: 3-8 pptx_engine/ |
| [4-D] 차트 이미지 삽입 (18) | Phase 4: components/chart_embed.py |
| [4-D] 동적 레이아웃 조정 (19) | Phase 4: 3-13 콘텐츠 오버플로우 |
| [4-D] PPTX 문서 조립 (20) | Phase 4: 3-12 엔드투엔드 파이프라인 |
| [4-E] HTML 템플릿 설계 (22) | Phase 3: 3-9 css_generator.py |
| [4-E] WeasyPrint PDF 변환 (23) | Phase 2: 3-7 pdf_engine.py |

---

## 8. 보안 고려사항

IM 문서에는 비공개 재무 데이터, 딜 구조, 밸류에이션 등 **극비 정보**가 포함된다. design_renderer에서 적용할 보안 대책:

### 8-1. PDF 출력물 보안

| 기능 | 구현 위치 | 설명 |
|------|---------|------|
| PDF 비밀번호 보호 | `pdf_engine.py` | 열람/편집 비밀번호 설정 (PyPDF2/pikepdf) |
| "CONFIDENTIAL" 워터마크 | `pdf_output/html_builder.py` | CSS `@page` 배경 워터마크 또는 별도 레이어 |
| 인쇄/복사 제한 | `pdf_engine.py` | PDF 권한 플래그로 인쇄/복사 제한 |

### 8-2. PPTX 출력물 보안

| 기능 | 구현 위치 | 설명 |
|------|---------|------|
| 편집 제한 모드 | `pptx_engine/style_applier.py` | python-pptx로 읽기 전용/수정 제한 설정 |
| 워터마크 슬라이드 | `pptx_engine/slide_factory.py` | 마스터 레벨에 반투명 "CONFIDENTIAL" 텍스트 |

### 8-3. 데이터 처리 보안

- 렌더링 과정에서 `IMDocumentData`의 재무 데이터를 **메모리 내에서만** 처리, 임시 파일 미생성
- HTML 중간 산출물은 렌더링 완료 후 즉시 삭제 (PDF 변환 시)
- base64 인코딩된 폰트/이미지는 외부 URL 참조 없이 HTML에 인라인
- 로그에 재무 수치 노출 금지 (민감 필드 마스킹)
