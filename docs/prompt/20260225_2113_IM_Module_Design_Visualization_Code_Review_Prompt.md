# IM 모듈 전체 코드 리뷰 프롬프트 — 디자인/시각화 특화

> 작성: 2026-02-25 21:13
> 대상 브랜치: `feat/ma-workflow`
> 모듈 범위: `im/` 백엔드 전체 + `amic-platform/src/modules/im/` 프론트엔드 + `im/src/design_renderer/` + `im/src/chart_engine/`

---

## 0. 사전 조건 및 프로토콜

### 0-A. VCP(Verified Claim Protocol) 필수 적용

> **이 리뷰의 모든 이슈는 VCP 6단계를 거쳐야 보고 가능하다.**
> 프로토콜 전문: `amic-platform/.claude/rules/verified-claim-protocol.md`

요약:
1. **Glob** — 파일 존재 확인
2. **Read** — 실제 코드 직접 읽기 (메모리/추측 금지)
3. **주장 검증** — "X가 없다" → Grep 전체 검색, "X가 잘못됨" → 주변 컨텍스트 확인
4. **Self-Challenge (SC-1~SC-6)** — 자기 반론으로 허위 양성 사전 제거
5. **증거 첨부** — Read 결과 그대로 인용 (라인 번호 정확)
6. **신뢰도 점수** — HIGH(90%+) / MEDIUM(60-89%) / LOW(<60%)

**허위 양성 방지 강화 규칙:**
- SC-1~SC-5 중 **하나라도 ✗이면 해당 이슈를 보고하지 않는다** (REJECT)
- 1개 이상 △이면 신뢰도 MEDIUM으로 하향, 2개 이상 △이면 LOW로 하향
- 거부된 가설은 리포트 말미 `검증 투명성` 섹션에 분류 기재
- **금지 패턴**: "~인 것 같다", "아마 ~일 것이다", 미확인 라인 번호, 메모리 기반 코드 인용

### 0-B. 기존 코드 리뷰와의 정합성 확인 (필수)

> **이전 리뷰 보고서에서 이미 발견·수정된 이슈를 중복 보고하지 않는다.**

**참조 문서**: `docs/code-review/20260225_2039_IM_Module_Code_Review_and_Fix_Report.md`

이전 리뷰에서 **수정 완료된 14건** (3건 허위 양성 포함):

| # | 이슈 | 상태 |
|---|------|------|
| 1 | `generate_im.py:299` — `_generation_config` 키 불일치 | ✅ 수정 |
| 2 | `document.ts:4` — DataSource에 "VDR" 누락 | ✅ 수정 |
| 3 | `CreateDocumentPage.tsx:26-31` — TEASER 스타일 옵션 누락 | ✅ 수정 |
| 5 | 섹션 렌더러 레지스트리 에러 처리 (`base.py`, `__init__.py`, `pipeline.py`) | ✅ 수정 |
| 6 | `im_ralph_session.py:90` — backref→back_populates | ✅ 수정 |
| 8 | 차트 엔진 색상 하드코딩 → `chart_config_from_design_tokens()` 추가 | ✅ 수정 |
| 9 | HTTPException→도메인 예외 교체 (`documents.py`, `ralph.py`) | ✅ 수정 |
| 10 | `design_tokens.py` — `footer_note` 설정화 | ✅ 수정 |
| 11 | `pipeline.py` — TM TOC 페이지 번호 검증 Phase 5 추가 | ✅ 수정 |
| 12 | `DocumentDetailPage.tsx` — 데이터소스 배지 색상 통일 | ✅ 수정 |
| 13 | `format_utils.py` 신규 + 5개 렌더러 import 교체 | ✅ 수정 |

**중기 보류 2건** (리뷰 대상에서 제외):
| 4 | Document Soft Delete | 보류 |
| 7 | JSONB 컬럼 스키마 검증 | 보류 |

**허위 양성 확정 3건** (재보고 금지):
- `models/__init__.py`에 IMChecklist 미등록 → 실제 등록 확인됨
- PPTX 폰트 오버라이드 불일치 → `font_helper.py:101-156`에서 title/body 분기 확인됨
- Ralph 수동 트리거 라우트 부재 → `ralph.py:105`에 존재 확인됨

**정합성 확인 절차:**
1. 새 이슈 발견 시, 위 테이블의 수정 파일·라인과 대조
2. 이미 수정된 위치와 겹치면 → **현재 코드를 Read로 다시 확인**하여 수정이 실제 적용되었는지 검증
3. 수정이 적용되었으면 → 이슈로 보고하지 않음
4. 수정이 불완전하거나 새로운 변형이면 → "이전 수정 후 잔존" 태그로 보고

### 0-C. 디자인/시각화 우선순위 기준

| 등급 | 기준 | 예시 |
|------|------|------|
| **P0** (90+) | 컬러/폰트 불일치로 PPTX 출력물이 시각적으로 깨짐 | 한글 폰트 미적용, 컬러 코드 오류 |
| **P1** (60-89) | 차트 한글 깨짐, 레이아웃 오버플로우, 데이터 표시 오류 | 축 라벨 잘림, KPI 값 형식 오류 |
| **P2** (30-59) | 디자인 토큰 중복 정의, 불필요한 하드코딩, 코드 구조 개선 | SSOT 위반, 어댑터 중복 |
| **P3** (<30) | 문서화 불일치, 미사용 코드, 미적 개선 제안 | docstring 오류, 미사용 import |

---

## 1. 디자인 토큰 및 컬러 시스템 일관성 [Critical]

### 리뷰 대상 파일
```
im/src/design_renderer/design_tokens.py           (~270L) — 컬러/폰트/레이아웃 SSOT
im/src/chart_engine/config.py                     (~120L) — ChartColorConfig, AMIC_CHART_COLORS
im/src/chart_engine/plotly/themes.py              (122L)  — AMIC_THEME, get_color_sequence()
im/src/design_renderer/components/chart_embed.py  (~220L) — AMIC_CHART_COLORS (중복 정의), _tokens_to_config()
im/src/design_renderer/pptx_engine/style_applier.py       — 프레젠테이션 스타일 적용
im/src/brand_extractor/models.py                  (~91L)  — BrandAssets 기본 색상
```

### 체크포인트

**CP-1.1: AMIC_CHART_COLORS 중복 정의 + 값 불일치 검증**

두 파일에 AMIC_CHART_COLORS가 별도 정의됨. 값이 다른지 문자열 비교 필수:

- `chart_embed.py:41-45`:
  ```python
  AMIC_CHART_COLORS = [
      "#0F3A32", "#26C260", "#3D3D3D", "#777777",
      "#E8F5E9", "#EF6C00", "#BC2C1A", "#4CAF50",
      "#2196F3", "#9C27B0",
  ]
  ```
- `config.py:24-35`:
  ```python
  AMIC_CHART_COLORS = [
      "#0F3A32", "#1C8F57", "#26C260", "#A3E96B",
      "#000000", "#777777", "#EF6C00", "#BC2C1A",
      "#E6FDD6", "#F4F6F8",
  ]
  ```

**검증 방법**: 두 리스트를 원소별 비교. `#3D3D3D`, `#E8F5E9`, `#4CAF50`, `#2196F3`, `#9C27B0`은 `config.py`에 없음 → SSOT 위반 확인 또는 의도된 분리인지 확인.

**CP-1.2: _tokens_to_config() vs chart_config_from_design_tokens() 중복 어댑터**

- `chart_embed.py:53-80`의 `_tokens_to_config()` → **secondary, fresh 필드 누락**
- `config.py:87-119`의 `chart_config_from_design_tokens()` → **gray_medium, gray_border 필드 누락**
- 두 함수 중 어느 것이 정규(canonical)인지 확인. 호출 경로 추적 필수.

**CP-1.3: 시맨틱 컬러 혼용**
- `themes.py`의 `get_color_sequence()`가 `caution`(EF6C00)과 `negative`(BC2C1A)를 데이터 시퀀스에 포함하는지 확인
- 시맨틱 색상은 상태 표시용인데 차트 데이터 색상으로 쓰이면 의미 혼란

**CP-1.4: 브랜드 오버라이드 partial reset**
- `design_tokens.py:247-258`의 `from_brand_assets()` → `IMColorPalette(primary=..., accent=...)` 2개 필드만 오버라이드 시 나머지(secondary, fresh, light 등) 클래스 기본값으로 리셋되는지 확인
- `brand_extractor/models.py:81` — `secondary_color="#26C260"` (이것은 IMColorPalette.accent 값, .secondary=#1C8F57과 다름)

### 예상 이슈 유형
- `DES-COLOR-001`: AMIC_CHART_COLORS 값 불일치 (P2)
- `DES-COLOR-002`: 어댑터 함수 필드 누락 불일치 (P2)
- `DES-COLOR-003`: 브랜드 오버라이드 partial reset (P1)
- `DES-COLOR-004`: 시맨틱 컬러 데이터 혼용 (P3)

---

## 2. 폰트 시스템 및 한글 렌더링 [High]

### 리뷰 대상 파일
```
im/src/design_renderer/design_tokens.py  — IMTypography, IMFontSizes
im/src/design_renderer/pptx_engine/font_helper.py — a:ea 동아시아 폰트 후처리
im/src/design_renderer/pptx_engine/style_applier.py — 프레젠테이션 스타일
im/src/design_renderer/components/kpi_card.py     — KPI 카드 (docstring 불일치 알려짐)
im/src/chart_engine/config.py                     — KOREAN_FONT="NanumGothic"
im/src/design_renderer/assets/fonts/              — 폰트 파일 존재 확인
```

### 체크포인트

**CP-2.1: 폰트 계층 준수 전수 검사**
- 계층: SUITE(font_heading)=제목, Pretendard(font_body)=본문, Pretendard(font_mono)=숫자
- `Grep "font_heading\|font_body\|font_mono\|SUITE\|Pretendard"` 전체 `section_renderers/` 검색
- 각 렌더러에서 제목에 font_heading, 본문에 font_body를 사용하는지 확인
- **주의**: `font_helper.py:101-156`에서 title/body 분기가 이미 구현되었으므로 (이전 리뷰 허위 양성 확인됨), 이 분기 로직이 **모든 슬라이드**에 적용되는지가 핵심

**CP-2.2: pipeline.py a:ea 후처리 경로**
- `pipeline.py:253-254`에서 `ea_font=self._tokens.typography.font_body`만 전달
- `ensure_ea_fonts_on_presentation()`이 제목 폰트(SUITE)도 올바르게 처리하는지 `font_helper.py` 내부 로직 확인
- **이전 리뷰 정합성**: #허위양성 "PPTX 폰트 오버라이드 불일치" → `font_helper.py:101-156`에서 title_ph_idx 기반 분기 확인됨. 이 분기가 `ensure_ea_fonts_on_presentation()`에서도 동작하는지 재확인 필요

**CP-2.3: kpi_card.py docstring vs 실제 코드**
- `kpi_card.py:2`: docstring "IBM Plex Mono" 명시
- 실제 코드: `t.font_mono` → `IMTypography.font_mono="Pretendard"`
- IBM Plex Mono 폰트는 assets/fonts/에 존재함 → font_mono 설정이 의도적으로 Pretendard인지, 변경 누락인지 확인

**CP-2.4: 차트 폰트 vs PPTX 폰트 불일치**
- 차트: `config.py:22` → `KOREAN_FONT="NanumGothic"`
- PPTX: Pretendard/SUITE
- 차트 이미지를 PPTX에 임베딩 시 폰트 스타일 불일치가 시각적으로 눈에 띄는지 평가
- NanumGothic 폰트가 assets/fonts/에 없음 → 시스템 폰트 의존

**CP-2.5: 폰트 사이즈 스케일 적절성**
- `IMFontSizes.minimum=7pt` — 10.83" x 7.5" 슬라이드에서 가독성 확인
- 각 렌더러에서 minimum 사이즈를 실제로 사용하는 위치 확인

### 예상 이슈 유형
- `DES-FONT-001`: kpi_card.py docstring vs font_mono 불일치 (P3)
- `DES-FONT-002`: NanumGothic 시스템 폰트 의존 (P1)
- `DES-FONT-003`: 차트-PPTX 간 폰트 스타일 불일치 (P2)

---

## 3. PPTX 레이아웃 및 슬라이드 구조 [High]

### 리뷰 대상 파일
```
im/src/design_renderer/pipeline.py                (480L) — E2E 파이프라인
im/src/design_renderer/pptx_engine/slide_factory.py       — 슬라이드 생성
im/src/design_renderer/pptx_engine/template_manager.py    — 템플릿 관리
im/src/design_renderer/pptx_engine/toc_builder.py         — TOC 생성
im/src/design_renderer/section_renderers/financial_analysis.py (583L) — 가장 복잡
im/src/design_renderer/section_renderers/executive_summary.py  (337L)
im/src/design_renderer/section_renderers/market_drivers.py     (433L)
im/src/design_renderer/section_renderers/cover.py             (75L)
im/src/design_renderer/section_renderers/fallback.py          (124L)
im/src/design_renderer/im_document.py             (622L) — IMStyle 프리셋
```

### 체크포인트

**CP-3.1: IMPageLayout 좌표 일관성**
- `design_tokens.py`의 `IMPageLayout`(content_top, content_bottom, margin_left 등) 값 확인
- `financial_analysis.py`에서 하드코딩 좌표(예: `y += 1.6`) 검색 → `IMPageLayout` 참조로 대체 가능한지
- `Grep "Inches\("`으로 모든 렌더러의 하드코딩 좌표 수 세기

**CP-3.2: TM 2-pass 렌더링 캡슐화**
- `pipeline.py:371`: `factory._manager.add_slide("blank", prs)` → private 멤버 직접 접근
- SlideFactory에 public 메서드로 대체 가능한지 확인
- **이전 리뷰 정합성**: #11에서 Phase 5 TOC 검증 추가됨 → 현재 코드에 실제 적용되었는지 Read로 확인

**CP-3.3: 콘텐츠 오버플로우 방지**
- `financial_analysis.py`의 동적 슬라이드 수 결정 로직 (데이터 양에 따라 1~10슬라이드)
- 단일 슬라이드에 과도한 행이 배치될 때 `content_bottom` 초과 여부 체크 로직 존재 확인
- 다른 렌더러(executive_summary, market_drivers 등)도 동일 검증

**CP-3.4: 폴백 슬라이드 프로덕션 노출**
- `pipeline.py:113`: `continue_on_error=True` 기본값
- 섹션 렌더링 실패 시 `fallback.py`의 에러 메시지 슬라이드가 최종 PPTX에 포함
- 프로덕션 환경에서 적절한지 검토 → `continue_on_error=False`로 변경하거나, 폴백 슬라이드 시각 품질 개선 필요성

**CP-3.5: TEASER vs FULL 섹션 중복 실행 방지**
- `pipeline.py:174-179`: TM 모드 시 `active_sections = []`으로 치환하여 for 루프 스킵
- `TEASER_SECTIONS`에 `toc_divider`가 4번 포함되지만 실제로는 `_render_tm_sections()`에서만 처리
- 두 경로가 동시에 실행되지 않는지 확인

### 예상 이슈 유형
- `DES-LAYOUT-001`: `_manager` private 멤버 직접 접근 (P3)
- `DES-LAYOUT-002`: 콘텐츠 오버플로우 방지 로직 부재 (P1)
- `DES-LAYOUT-003`: 폴백 슬라이드 프로덕션 포함 가능 (P2)

---

## 4. 차트 엔진 품질 및 시각화 [High]

### 리뷰 대상 파일
```
im/src/chart_engine/plotly/combo.py               — 콤보 차트
im/src/chart_engine/plotly/waterfall.py            — 워터폴 차트
im/src/chart_engine/plotly/stacked_bar.py          — 누적 막대 차트
im/src/chart_engine/plotly/donut.py                — 도넛 차트
im/src/chart_engine/plotly/line.py                 — 꺾은선 차트
im/src/chart_engine/plotly/hbar.py                 — 수평 막대 차트
im/src/chart_engine/plotly/treemap.py              — 트리맵
im/src/chart_engine/plotly/funnel.py               — 퍼널 차트
im/src/chart_engine/plotly/sensitivity_heatmap.py  — 민감도 히트맵
im/src/chart_engine/plotly/cohort_heatmap.py       — 코호트 히트맵
im/src/chart_engine/plotly/themes.py               — Plotly 테마
im/src/chart_engine/data_transformer.py            — 데이터 변환
im/src/chart_engine/export/png_exporter.py         — PNG 내보내기
im/src/chart_engine/export/svg_exporter.py         — SVG 내보내기
im/src/chart_engine/graphviz/org_chart.py          — 조직도
im/src/chart_engine/graphviz/shareholding.py       — 주주 구조도
im/src/chart_engine/graphviz/flow_diagram.py       — 플로우 다이어그램
im/src/design_renderer/components/chart_embed.py   — 차트 임베딩 어댑터
im/src/design_renderer/image_optimizer.py          — 이미지 압축
```

### 체크포인트

**CP-4.1: 차트 데이터 타입 검증**
- `combo.py`의 `line_values` 파라미터에 str 타입이 섞여 있을 때 `f"{v * 100:.1f}%"` 에서 TypeError 발생 가능
- 10종 차트 각각의 입력 검증 로직 확인: ChartDataError 발생 조건이 충분한지
- 빈 데이터(`[]`, `{}`)가 주어졌을 때 각 차트 함수가 안전하게 처리하는지

**CP-4.2: Plotly 한글 렌더링 경로**
- `themes.py:67`의 `font=dict(family=font, ...)` 설정이 Kaleido 렌더링에 반영되는지
- Kaleido가 시스템에 설치된 NanumGothic 폰트를 찾을 수 있는지 (Docker 환경 포함)
- 긴 한글 카테고리명이 차트 축에서 잘리는 경우 처리 로직

**CP-4.3: PNG 압축 품질**
- `image_optimizer.py`의 `compress_png()` 알고리즘 (양자화 수준, 손실 여부)
- 300DPI 차트 이미지(900px * 3 = 2700px)의 압축 후 품질 훼손 여부
- PPTX 삽입 시 `width=9.0"` 대비 해상도 충분성

**CP-4.4: Graphviz 시스템 의존성**
- `org_chart.py`, `shareholding.py`, `flow_diagram.py`가 Graphviz 바이너리 의존
- Docker 이미지에 Graphviz 설치 여부 확인 (`docker-compose.yml` 또는 `Dockerfile`)
- Graphviz에서 한글 노드 라벨 렌더링 품질

**CP-4.5: 차트 종류별 디자인 토큰 적용 일관성**
- 10종 차트 모두 `themes.py`의 `AMIC_THEME`을 사용하는지
- 차트별 하드코딩 색상이 있는지 Grep으로 확인

### 예상 이슈 유형
- `DES-CHART-001`: combo chart 타입 미검증 TypeError 위험 (P1)
- `DES-CHART-002`: NanumGothic 시스템 폰트 Docker 미설치 가능 (P1)
- `DES-CHART-003`: Graphviz 시스템 의존성 미문서화 (P2)

---

## 5. 프론트엔드 IM 모듈 UX 및 컴포넌트 품질 [Medium]

### 리뷰 대상 파일
```
amic-platform/src/modules/im/ImRoutes.tsx
amic-platform/src/modules/im/pages/ChecklistReviewPage.tsx    (~350L)
amic-platform/src/modules/im/pages/CreateFromVdrPage.tsx
amic-platform/src/modules/im/pages/DocumentListPage.tsx
amic-platform/src/modules/im/pages/CreateDocumentPage.tsx
amic-platform/src/modules/im/pages/DocumentDetailPage.tsx
amic-platform/src/modules/im/pages/TemplatesPage.tsx
amic-platform/src/modules/im/components/ChecklistTable.tsx
amic-platform/src/modules/im/components/ChecklistItemRow.tsx
amic-platform/src/modules/im/components/ChecklistProgressBar.tsx
amic-platform/src/modules/im/components/SourceDocumentLink.tsx
amic-platform/src/modules/im/components/DocumentStatusBadge.tsx
amic-platform/src/modules/im/components/ProgressTracker.tsx
amic-platform/src/modules/im/components/ImErrorBoundary.tsx
amic-platform/src/modules/im/hooks/useChecklist.ts
amic-platform/src/modules/im/hooks/useDocuments.ts
amic-platform/src/modules/im/hooks/useIMRalphLoop.ts
amic-platform/src/modules/im/hooks/useVdrDocumentSelector.ts
amic-platform/src/modules/im/hooks/useCompanies.ts
amic-platform/src/modules/im/types/checklist.ts
amic-platform/src/modules/im/types/document.ts
amic-platform/src/modules/im/types/ralph.ts
amic-platform/src/modules/im/types/company.ts
```

### 체크포인트

**CP-5.1: 체크리스트 워크플로우 상태 전이 UX**
- 상태: EXTRACTING → REVIEW → COMPLETED → FAILED
- 각 상태에서 시각적 피드백(배지, 색상, 아이콘)이 일관적인지
- `useChecklist` 훅에 `refetchInterval` 설정 확인 (처리 중 polling)
- **이전 리뷰 긍정 평가**: "React Query 조건부 폴링 (처리 중일 때만 3초 간격)" → 현재 코드에 실제 적용되었는지 확인

**CP-5.2: 접근성 (a11y)**
- `ChecklistTable`에 `aria-label` 적용 확인
- `ChecklistReviewPage`의 `tabpanel` role과 `aria-labelledby` 매칭
- `ChecklistProgressBar`의 `role="progressbar"` + `aria-valuenow` 확인
- 인라인 편집 시 키보드 네비게이션 (Tab, Enter, Escape)

**CP-5.3: 프로젝트 디자인 시스템 일관성**
- IM 모듈이 `@/components/ui/`의 공통 컴포넌트(Button, Card, Modal, Tabs, PageHero, DataTable)를 사용하는지
- 커스텀 Tailwind 색상(`text-amic`, `bg-bg-cool`, `text-positive`, `text-negative`)이 `tailwind.config.js`에 정의되어 있는지
- `ChecklistReviewPage`의 sticky bottom bar 스타일이 다른 모듈과 일관적인지
- **이전 리뷰 정합성**: #12 데이터소스 배지 색상 통일이 적용되었는지 `DocumentDetailPage.tsx`, `DocumentListPage.tsx` 재확인

**CP-5.4: 타입 안전성 (FE-BE 동기화)**
- `checklist.ts`의 `ChecklistCategory`, `ChecklistItemStatus` 타입이 백엔드 `im/src/api/schemas/checklist.py`와 일치하는지
- `document.ts`의 `DataSource` 타입이 백엔드 enum과 일치하는지
- **이전 리뷰 정합성**: #2 DataSource에 "VDR" 추가됨 → 현재 코드에 적용 확인

**CP-5.5: 로딩/에러/빈 상태 일관성**
- 6개 페이지 모두 로딩 Spinner, 에러 Alert, 빈 상태 처리 확인
- React Query의 `retry`, `staleTime`, `gcTime` 설정 일관성

### 예상 이슈 유형
- `FE-UX-001`: tabpanel aria-labelledby 불일치 가능 (P2)
- `FE-TYPE-001`: FE-BE 타입 동기화 미검증 항목 (P2)
- `FE-A11Y-001`: 인라인 편집 키보드 네비게이션 미구현 (P2)

---

## 6. 백엔드 서비스 로직 및 API [Medium]

### 리뷰 대상 파일
```
im/src/api/routes/documents.py
im/src/api/routes/checklist.py
im/src/api/routes/ralph.py
im/src/api/routes/audit.py
im/src/api/services/document_service.py           (270L)
im/src/api/services/checklist_to_imdata.py         (511L) — 핵심 변환 로직
im/src/api/services/checklist_field_registry.py    (204L)
im/src/api/services/vdr_analysis_service.py        (627L) — VDR 파싱 엔진
im/src/api/tasks/generate_im.py
im/src/api/tasks/generate_im_from_checklist.py
im/src/api/tasks/ralph_loop.py
im/src/api/tasks/vdr_extraction.py
im/src/api/db/models/im_checklist.py
im/src/api/db/models/im_checklist_item.py
im/src/api/db/models/document.py
im/src/api/schemas/checklist.py
im/src/api/schemas/documents.py
im/src/api/config.py
im/src/api/exceptions.py
im/src/api/dependencies.py
im/src/api/middleware/cors.py
```

### 체크포인트

**CP-6.1: checklist_to_imdata 변환 정확성**
- `_parse_number()` 함수: 한국 단위("억원", "백만원") 접미사 제거 후 → 숫자만 반환
- **핵심 이슈**: "150억원"에서 "억원" 제거 시 150 반환 → 실제 값 15,000,000,000과 차이
- 이 함수의 호출 위치와 컨텍스트 확인 → 단위 정보가 별도 처리되는지

**CP-6.2: VDR 분석 서비스**
- `YEAR_PATTERNS` 하드코딩 범위 확인 (2022-2026만?)
- `KEYWORD_MAP` 한/영 매핑이 다양한 VDR 문서 표기를 커버하는지
- Excel 파싱에서 다중 시트, 병합 셀 처리 견고성
- `confidence` 점수 계산 로직의 합리성

**CP-6.3: Celery 태스크 안전성**
- 장시간 실행 태스크 타임아웃 설정 (`soft_time_limit`, `time_limit`)
- 동일 document에 대한 중복 태스크 방지 (잠금 메커니즘)
- 태스크 실패 시 체크리스트 상태 FAILED 전이 보장

**CP-6.4: API 보안**
- CORS 설정(`middleware/cors.py`)에서 `allow_origins=["*"]` 여부
- 체크리스트 CRUD 엔드포인트 인증/인가 확인
- 에러 응답에 내부 스택 트레이스 노출 여부 (`exceptions.py`)
- **이전 리뷰 정합성**: #9 HTTPException→도메인 예외 교체 적용 확인

**CP-6.5: DB 모델**
- N+1 쿼리 방지 (`selectinload` / `joinedload` 사용 여부)
- FK 컬럼 인덱스 설정 (checklist_id, document_id)
- **이전 리뷰 정합성**: #6 back_populates 교체 적용 확인

### 예상 이슈 유형
- `BE-DATA-001`: _parse_number() 단위 변환 미수행 (P1)
- `BE-DATA-002`: YEAR_PATTERNS 하드코딩 (P2)
- `BE-SEC-001`: CORS allow_origins=["*"] 가능 (P1)
- `BE-TASK-001`: Celery 중복 실행 방지 부재 (P2)

---

## 7. 통합 파이프라인 및 테스트 커버리지 [Medium]

### 리뷰 대상 파일
```
im/src/design_renderer/pipeline.py       — E2E 파이프라인 (이전 리뷰 #5, #11 수정 적용 확인)
im/src/design_renderer/manifest.py       — 생성 매니페스트
im/src/design_renderer/security.py       — 보안 옵션 (워터마크, 편집 제한)
im/src/design_renderer/image_processor.py — 이미지 처리
im/src/narrative_generator/engine/orchestrator.py — LLM 오케스트레이터
im/src/narrative_generator/prompts/__init__.py    — 섹션별 프롬프트
im/src/data_ingestor/pipeline.py                  — 데이터 인제스트
im/alembic/env.py
im/alembic/versions/001_initial_schema.py ~ 007_im_ralph_sessions.py
```

### 체크포인트

**CP-7.1: E2E 파이프라인 result.success 판정**
- `pipeline.py:280`: `result.success = len(result.errors) == 0`
- `continue_on_error=True`일 때 에러가 errors 리스트에 추가되므로 success=False 될 수 있음
- 경고(warnings)만 있을 때는 success=True → 이 판정이 올바른지

**CP-7.2: PPTX 보안 옵션**
- `security.py`의 `SecurityOptions` 데이터클래스 구조
- `style_applier.py`의 `set_edit_restriction()` — SHA-512 해싱, spin_count 값이 OOXML 스펙 준수하는지
- 워터마크 투명도 계산: `alpha_val = int((1.0 - opacity) * 100000)` 정확성

**CP-7.3: render_html() 미구현 잔재**
- `BaseSectionRenderer`가 `render_html()` 추상 메서드 정의
- 모든 렌더러에서 `NotImplementedError` raise 여부 전수 확인
- PDF 출력 제거 후 이 메서드가 불필요한지 → 제거 또는 Optional 변경 권장

**CP-7.4: 내러티브 생성기 품질**
- `orchestrator.py`의 LLM 호출 에러 핸들링 (타임아웃, rate limit, 응답 형식 검증)
- 프롬프트 템플릿의 한국어 품질 및 금융 용어 정확성
- LLM 응답이 IMDocumentData.narratives에 안전하게 저장되는지

**CP-7.5: Alembic 마이그레이션 안전성**
- 7개 마이그레이션(001~007)의 `downgrade()` 함수 존재 및 안전성
- 외래키 제약조건, 인덱스 설정 적절성
- 마이그레이션 순서 의존성 (revision chain) 정합성

**CP-7.6: 테스트 커버리지**
- `Glob "im/tests/**/*.py"` 또는 `im/src/**/test_*.py` → 테스트 파일 존재 확인
- 핵심 서비스(`checklist_to_imdata`, `vdr_analysis_service`)의 단위 테스트 존재 여부
- 디자인 렌더러 파이프라인 통합 테스트 존재 여부

### 예상 이슈 유형
- `INT-PIPE-001`: render_html() 추상 메서드 전체 미구현 잔재 (P3)
- `INT-PIPE-002`: continue_on_error=True 기본값 재고 (P2)
- `INT-TEST-001`: 핵심 서비스 테스트 커버리지 부족 (P2)

---

## 8. 리뷰 실행 지침

### 8-A. 실행 순서

1. **섹션 1~4** (디자인/시각화 코어) 먼저 — P0/P1 이슈 집중
2. **섹션 5** (프론트엔드 UX) — 디자인 일관성 확인
3. **섹션 6~7** (백엔드/통합) — 데이터 정합성, 보안

### 8-B. 이슈 보고 형식

VCP 표준 출력 형식 사용 (`verified-claim-protocol.md` 참조):

```
### [{SEVERITY_INITIAL}-{CATEGORY_INITIAL}{NUMBER}] {제목} — [{심각도}/{신뢰도}] — Priority: {P0/P1/P2/P3}

- **파일**: {경로}:{라인}
- **검증 추적**:
  1. ✓ Glob: ...
  2. ✓ Read: ...
  3. ✓ Grep: ...
  4. ✓ Context: ...
  5. ✓ Self-Challenge: SC-1(✓) SC-2(✓) SC-3(✓) SC-4(✓) SC-5(✓) SC-6(✓) → PASS
- **추론 근거**: ...
- **증거**: {Read 결과 그대로}
- **이슈**: ...
- **영향**: ...
- **수정안**: ...
```

### 8-C. 디자인 시스템 건강도 점수

리뷰 완료 후 아래 4개 축으로 건강도 점수(1~10) 부여:

| 축 | 평가 기준 |
|----|----------|
| **컬러 일관성** | SSOT 준수율, 하드코딩 색상 수, 시맨틱 컬러 올바른 사용 |
| **폰트 일관성** | 계층 준수율, a:ea 후처리 완성도, 차트-PPTX 통일성 |
| **레이아웃 견고성** | IMPageLayout 참조율, 오버플로우 방지, 동적 슬라이드 안전성 |
| **차트 품질** | 디자인 토큰 적용률, 한글 렌더링, 데이터 검증 |

### 8-D. 최종 리포트 구조

```markdown
# IM 모듈 코드 리뷰 리포트 (디자인/시각화 특화)

## 개요
- 리뷰 범위: 7개 섹션, ~N개 파일
- 기존 리뷰 정합성: 이전 14건 수정 적용 확인 여부

## P0 이슈 (즉시 수정)
...

## P1 이슈 (스프린트 우선)
...

## P2 이슈 (개선 권장)
...

## P3 이슈 (저우선)
...

## 이전 리뷰 수정 적용 확인
| # | 이슈 | 적용 확인 | 비고 |
|---|------|----------|------|
| 1 | generate_im.py 키 수정 | ✅/❌ | ... |
| ... | ... | ... | ... |

## 디자인 시스템 건강도 요약
| 축 | 점수 | 근거 |
|----|------|------|
| 컬러 일관성 | X/10 | ... |
| 폰트 일관성 | X/10 | ... |
| 레이아웃 견고성 | X/10 | ... |
| 차트 품질 | X/10 | ... |

## 검증 투명성

### 검증 통계
- 검증한 가설: N건
- 거부된 가설 (사전 제거): N건
- 보고된 이슈: N건
- 거부율: X%

### 거부 사유 분류
| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | N | ... |
| Self-Challenge 기각 | N | ... |
| 이미 수정됨 | N | 이전 리뷰에서 수정 확인 |
| ... | ... | ... |
```

---

## 부록: 핵심 파일 요약

| 파일 | 줄 수 | 역할 | 리뷰 섹션 |
|------|-------|------|----------|
| `im/src/design_renderer/design_tokens.py` | ~270 | 컬러/폰트/레이아웃 SSOT | 1, 2 |
| `im/src/design_renderer/pipeline.py` | 480 | E2E 파이프라인 오케스트레이터 | 3, 7 |
| `im/src/design_renderer/im_document.py` | 622 | 통합 입력 스키마 (4개 프리셋) | 3 |
| `im/src/design_renderer/section_renderers/financial_analysis.py` | 583 | 가장 복잡한 렌더러 | 3 |
| `im/src/design_renderer/section_renderers/market_drivers.py` | 433 | TM 전용 렌더러 | 3 |
| `im/src/design_renderer/components/chart_embed.py` | ~220 | 차트-PPTX 임베딩 어댑터 | 1, 4 |
| `im/src/chart_engine/plotly/themes.py` | 122 | 차트 테마 | 1, 4 |
| `im/src/chart_engine/config.py` | ~120 | 차트 설정 + 어댑터 | 1, 4 |
| `im/src/api/services/checklist_to_imdata.py` | 511 | 체크리스트→IMData 변환 | 6 |
| `im/src/api/services/vdr_analysis_service.py` | 627 | VDR 파싱 엔진 | 6 |
| `amic-platform/src/modules/im/pages/ChecklistReviewPage.tsx` | ~350 | 체크리스트 리뷰 UI | 5 |
| `im/src/design_renderer/pptx_engine/font_helper.py` | - | a:ea 폰트 후처리 | 2 |
| `im/src/brand_extractor/models.py` | ~91 | 브랜드 에셋 기본값 | 1 |
