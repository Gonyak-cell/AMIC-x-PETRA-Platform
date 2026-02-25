# IM 모듈 코드 리뷰 리포트 (디자인/시각화 특화)

> 리뷰 일시: 2026-02-25 21:38
> 프롬프트: `docs/code-review/20260225_2113_IM_Module_Design_Visualization_Code_Review_Prompt.md`
> 대상 브랜치: `feat/ma-workflow`
> 프로토콜: VCP v1.1 (Verified Claim Protocol) 전체 적용

---

## 개요

- **리뷰 범위**: 7개 섹션, ~50개 파일
- **검증한 가설**: 42건
- **거부된 가설 (허위 양성 사전 제거)**: 14건
- **보고된 이슈**: 18건 (P0: 1, P1: 6, P2: 7, P3: 4)
- **이전 리뷰 정합성**: 14건 수정 중 5건 직접 확인 — 모두 적용 완료
- **거부율**: 33%

---

## P0 이슈 (즉시 수정)

### [IM-6.1a] `_parse_number()`가 한국 통화 단위를 제거만 하고 승수를 적용하지 않음 — [Critical/HIGH] — Priority: P0

- **파일**: `im/src/api/services/checklist_to_imdata.py:496-511`
- **검증 추적**:
  1. ✓ Read: checklist_to_imdata.py 전문 512라인 확인
  2. ✓ 코드 분석: `_parse_number("150억원")` → `cleaned = "150"` → `float("150")` = `150.0`
  3. ✓ 호출 추적: `_convert_financial`, `_convert_market`, `_convert_deal`, `_convert_shareholders` 4곳에서 사용
  4. ✓ suffix 순서 버그 확인: `("원", "백만원", ...)` → "백만원"이 "원"에 먼저 매칭
  5. ✓ Self-Challenge: SC-1~SC-6 모두 ✓ → PASS
- **증거**:
```python
# 라인 496-511
for suffix in ("원", "백만원", "억원", "천원", "만원"):
    if cleaned.endswith(suffix):
        cleaned = cleaned[:-len(suffix)]
# → "150억원" → "150" → float("150") = 150.0
# 실제 의미: 150억 = 15,000,000,000
```
- **이슈**: 단위 접미사를 **제거만** 하고 **승수를 곱하지 않음**. 추가로 suffix 순서가 `("원", "백만원", ...)`이어서 "백만원"이 "원"에 먼저 매칭되는 버그도 존재.
- **영향**: IM 문서의 모든 재무 데이터가 10억~1조배 축소됨. 매출 1,500억원 기업이 1,500원으로 표시.
- **수정안**:
```python
_UNIT_MULTIPLIER: dict[str, float] = {
    "조원": 1_000_000_000_000,
    "억원": 100_000_000,
    "백만원": 1_000_000,
    "만원": 10_000,
    "천원": 1_000,
    "원": 1,
}

@staticmethod
def _parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace(",", "").replace(" ", "")
    multiplier = 1.0
    for suffix, mult in _UNIT_MULTIPLIER.items():  # 긴 suffix부터
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
            multiplier = mult
            break
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None
```

---

## P1 이슈 (스프린트 우선)

### [CP-1.1] AMIC_CHART_COLORS 중복 정의 — 10개 중 9개 불일치 — [Moderate/HIGH] — Priority: P1

- **파일**: `im/src/design_renderer/components/chart_embed.py:41-45` vs `im/src/chart_engine/config.py:24-35`
- **증거**: chart_embed.py에 Material Design 컬러(`#4CAF50`, `#2196F3`, `#9C27B0`, `#E8F5E9`) 4개가 AMIC 공식 팔레트에 없는 값으로 혼재. **현재 dead code** (chart_embed.py 내부에서 이 변수를 참조하는 함수 없음).
- **영향**: 외부 코드가 `from chart_embed import AMIC_CHART_COLORS` 하면 잘못된 팔레트 사용.
- **수정안**: chart_embed.py의 `AMIC_CHART_COLORS` + 중복 상수 (`CHART_DPI`, `DEFAULT_WIDTH`, `DEFAULT_HEIGHT`, `KOREAN_FONT`) 삭제. 필요시 `config.py`에서 import.

### [CP-1.4] `from_brand_assets()` partial reset — 24개 필드 중 2개만 오버라이드 — [Moderate/HIGH] — Priority: P1

- **파일**: `im/src/design_renderer/design_tokens.py:247-250`
- **증거**: `IMColorPalette(primary=..., accent=...)` 2개만 설정 → 나머지 22개(secondary, fresh, table_header_bg, positive 등) AMIC 기본값으로 리셋. 클라이언트 브랜딩 적용 시 primary는 파란색인데 secondary/table_header는 AMIC 녹색인 하이브리드 팔레트 생성.
- **영향**: 브랜드 오버라이드 시 문서 전체의 색상 일관성 깨짐.
- **수정안**: `table_header_bg=p`, `positive=a` 등 파생 필드를 primary/accent에서 동기화.

### [CP-2.1] management_team/shareholder_structure — `set_font_with_ea` 미사용 (5곳) — [Moderate/HIGH] — Priority: P1

- **파일**: `im/src/design_renderer/section_renderers/management_team.py:156,165,176` + `shareholder_structure.py:174,204-205`
- **증거**: `r.font.name = t.font_body`로 `<a:latin>`만 설정. `<a:ea>` 동아시아 폰트 누락. 현재는 pipeline 후처리(`ensure_ea_fonts_on_presentation`)에서 커버됨.
- **영향**: 현재 런타임 영향 없음. 후처리 제거/변경 시 한글 깨짐. 코드 패턴 불일치.
- **수정안**: 5곳 모두 `set_font_with_ea(r, t.font_body)`로 교체.

### [IM-6.3a] 3개 Celery 태스크에 `soft_time_limit`/`time_limit` 미설정 — [Moderate/HIGH] — Priority: P1

- **파일**: `im/src/api/tasks/generate_im.py:74`, `generate_im_from_checklist.py:40-46`, `vdr_extraction.py:154-160`
- **증거**: `ralph_loop.py`는 `soft_time_limit=600, time_limit=660` 올바르게 설정됨. 나머지 3개 태스크는 미설정. 외부 API + LLM 호출 포함 태스크가 무한 블로킹 가능.
- **영향**: 워커 고갈 → 전체 Celery 큐 정체.
- **수정안**: `generate_im`(900/960s), `generate_im_from_checklist`(600/660s), `extract_vdr_data`(300/360s) 설정.

### [IM-7.1a] `continue_on_error=True`에서 `result.success` 판정 불일치 — [Moderate/HIGH] — Priority: P1

- **파일**: `im/src/design_renderer/pipeline.py:280`
- **증거**: 26개 섹션 중 1개 실패 + 폴백 성공 → PPTX 파일은 유효하지만 `success=False`. 호출처(generate_im_from_checklist.py)는 warning만 남기고 `COMPLETED`로 마킹 → 모니터링에서 "실패" 건수 과대 보고.
- **수정안**: 폴백 성공한 에러는 `warnings`로 이동하거나, `partial_success` 플래그 도입.

### [IM-7.6a] 신규 서비스 7개 (2,773라인)에 테스트 전무 — [Moderate/HIGH] — Priority: P1

- **파일**: `checklist_to_imdata.py`(512L), `vdr_analysis_service.py`(628L), `checklist_field_registry.py`(200L), `generate_im_from_checklist.py`(313L), `ralph_loop.py`(302L), `vdr_extraction.py`(323L), `routes/checklist.py`(495L)
- **이슈**: VDR 기반 체크리스트 워크플로우 전체에 테스트 0개. P0 버그(`_parse_number`)는 단위 테스트 1개로 사전 방지 가능했음.
- **수정안**: 최소 `test_checklist_to_imdata.py` (P0 검증), `test_vdr_analysis_service.py`, `test_checklist_routes.py` 3개 작성.

---

## P2 이슈 (개선 권장)

### [CP-1.2] `_tokens_to_config()` 3중 중복 + secondary/fresh 필드 누락 — [Minor/HIGH] — Priority: P2

- **파일**: `chart_embed.py:53-80`, `org_chart.py:25-46`, `config.py:87-119`
- **이슈**: 동일 역할 어댑터 3곳 중복. 실제 사용되는 2곳에서 `secondary`/`fresh` 필드 미매핑. 완전한 매핑을 가진 `chart_config_from_design_tokens()`는 호출처 0건 (dead code).
- **수정안**: chart_embed/org_chart의 로컬 `_tokens_to_config()` 삭제, config.py의 함수를 공통 어댑터로 사용.

### [CP-1.3] `get_color_sequence()`에 시맨틱 컬러(caution/negative) 혼입 — [Minor/MEDIUM] — Priority: P2

- **파일**: `im/src/chart_engine/plotly/themes.py:93-104`
- **이슈**: 5번째 데이터 시리즈에 `caution`(앰버), 6번째에 `negative`(적색) 자동 할당. 재무 차트에서 해당 사업부에 문제가 있다는 오해 유발. `get_semantic_colors()`가 별도 존재하므로 역할 분리 가능.
- **수정안**: 시맨틱 컬러를 AMIC 그린 계열 중간 색조 또는 중립 색상으로 대체.

### [CP-2.4] NanumGothic 폰트 미번들 — Docker/CI 한글 깨짐 — [Minor/MEDIUM] — Priority: P2

- **파일**: `im/src/chart_engine/config.py:22`, `im/src/design_renderer/assets/fonts/`
- **이슈**: 차트 렌더링에 NanumGothic 지정하지만 assets/fonts/에 미포함. Docker에 `fonts-noto-cjk`만 설치 (`fonts-nanum` 없음). Kaleido가 NanumGothic을 찾지 못하면 대체 폰트 렌더링.
- **수정안**: (A) `fonts-nanum` 패키지 추가, (B) `font_chart`를 번들된 `NotoSansKR`로 변경, (C) assets/fonts/에 NanumGothic 추가.

### [CP-3.4] 폴백 슬라이드에 내부 에러 메시지가 클라이언트 PPTX에 노출 — [Moderate/HIGH] — Priority: P2

- **파일**: `im/src/design_renderer/section_renderers/fallback.py:77-78`, `pipeline.py:112`
- **이슈**: `continue_on_error=True`(기본값)로 프로덕션에서도 활성화. 에러 메시지에 Python traceback 일부, 파일 경로가 포함될 수 있으며 고객 PPTX에 삽입됨.
- **수정안**: `show_error_detail` 파라미터 추가, 프로덕션에서는 "해당 섹션의 데이터를 처리 중입니다."로 대체.

### [CP-4.1] combo 차트 `line_values` 타입 미검증 — RuntimeError TypeError 가능 — [Moderate/HIGH] — Priority: P2

- **파일**: `im/src/chart_engine/plotly/combo.py:85`
- **이슈**: `line_values` 빈 검증도 타입 검증도 없음. `None`이 포함되면 `None * 100` → TypeError. `bar_values`는 검증 있음.
- **수정안**: `if line_values: line_values = [float(v) if v is not None else 0.0 for v in line_values]`

### [m-X1] ChecklistItemRow 편집 버튼 키보드 접근성 제한 — [Moderate/HIGH] — Priority: P2

- **파일**: `amic-platform/src/modules/im/components/ChecklistItemRow.tsx:191`
- **이슈**: Edit 버튼이 `opacity-0 group-hover:opacity-100`으로 마우스 호버 시에만 표시. 키보드 Tab 포커스 시 `opacity-0` 유지 → WCAG 2.1 SC 2.4.7 위반.
- **수정안**: `focus-visible:opacity-100` 클래스 추가.

### [IM-6.5d] IMChecklistItem UniqueConstraint에 `fiscal_year` 누락 — [Moderate/MEDIUM] — Priority: P2

- **파일**: `im/src/api/db/models/im_checklist_item.py:178-184`
- **이슈**: `UniqueConstraint("checklist_id", "field_key")`로 같은 field_key의 다중 연도 데이터(revenue 2022, 2023, 2024) 저장 불가. field_key에 연도 포함 시 `fiscal_year` 컬럼과 데이터 이중화.
- **수정안**: `UniqueConstraint("checklist_id", "field_key", "fiscal_year")`로 변경 + Alembic 마이그레이션.

---

## P3 이슈 (저우선)

### [CP-2.3] kpi_card.py docstring "IBM Plex Mono" vs 실제 코드 "Pretendard" 불일치 — [Minor/HIGH] — Priority: P3

- **파일**: `im/src/design_renderer/components/kpi_card.py:2-3,114,147`
- **이슈**: 3곳의 docstring/주석이 "IBM Plex Mono" 명시하지만 실제 `font_mono="Pretendard"`. `assets/fonts/IBMPlexMono-*.otf` 4개 미사용.

### [CP-3.1] 폴백 슬라이드 좌표 하드코딩 — [Minor/HIGH] — Priority: P3

- **파일**: `im/src/design_renderer/section_renderers/fallback.py:52-57`
- **이슈**: `Inches(1.5)`, `Inches(2.5)`, `Inches(7.0)` 하드코딩. 26개 렌더러 중 유일하게 IMPageLayout 미참조.

### [CP-3.2] TM 2-pass에서 SlideFactory._manager private 멤버 접근 — [Minor/HIGH] — Priority: P3

- **파일**: `im/src/design_renderer/pipeline.py:371`
- **이슈**: `factory._manager.add_slide("blank", prs)` — blank 슬라이드 추가용 public 메서드 없음.

### [L-R1] DataSource 배지 정의 2곳 중복 — [Minor/HIGH] — Priority: P3

- **파일**: `amic-platform/src/modules/im/pages/DocumentListPage.tsx:43-48` + `DocumentDetailPage.tsx:147-152`
- **이슈**: 동일 badge Record가 2개 파일에 인라인 정의. 새 DataSource 추가 시 2곳 동기화 필요.

---

## 이전 리뷰 수정 적용 확인

| # | 이슈 | 적용 확인 | 비고 |
|---|------|----------|------|
| 1 | `generate_im.py` _generation_config 키 수정 | ✅ | `doc.generation_config or {}` None 안전 처리 확인 |
| 2 | `document.ts` DataSource에 "VDR" 추가 | ✅ | FE `"DART" \| "MANUAL" \| "EXCEL" \| "VDR"` + BE `_VALID_DATA_SOURCES` 일치 |
| 3 | `CreateDocumentPage.tsx` TEASER 스타일 옵션 | — | 직접 확인 미수행 (프롬프트 범위 외) |
| 5 | 섹션 렌더러 에러 처리 3계층 | ✅ | RendererNotFoundError + 폴백 + continue_on_error 분기 확인 |
| 6 | `im_ralph_session.py` back_populates | ✅ | im_checklist.py, document.py 양방향 매핑 확인 |
| 8 | 차트 엔진 `chart_config_from_design_tokens()` | ✅ | config.py:87-119에 존재. 단, 호출처 0건 (CP-1.2 참조) |
| 9 | HTTPException → 도메인 예외 교체 | ✅ | documents.py에 HTTPException import 없음. ValidationError 사용 확인 |
| 10 | `design_tokens.py` footer_note 설정화 | — | 직접 확인 미수행 |
| 11 | `pipeline.py` TM TOC Phase 5 검증 | ✅ | 라인 398-412에 page_num > total_slides 검증 + 로깅 확인 |
| 12 | DocumentDetailPage 배지 색상 통일 | ✅ | 4개 DataSource 일관된 배지 색상 확인 |
| 13 | `format_utils.py` 신규 + 렌더러 import 교체 | — | 직접 확인 미수행 |

---

## 디자인 시스템 건강도 요약

| 축 | 점수 | 근거 |
|----|------|------|
| **컬러 일관성** | 6/10 | AMIC_CHART_COLORS 2곳 9/10 불일치(dead code), 어댑터 3중 중복, 브랜드 오버라이드 시 22개 필드 리셋. 단 실제 차트 13개는 모두 디자인 토큰 참조 (하드코딩 hex 0건). |
| **폰트 일관성** | 7/10 | 26개 렌더러 중 2개에서 set_font_with_ea 미사용 (후처리로 커버). NanumGothic 미번들. kpi_card docstring 불일치. IBM Plex Mono 4개 미사용 파일 잔존. |
| **레이아웃 견고성** | 8/10 | 26개 중 24개가 IMPageLayout 정상 참조. TEASER/FULL 분기 안전. fallback.py 1곳만 하드코딩. market_overview 경쟁사 다수 시 오버플로우 가능. |
| **차트 품질** | 8/10 | 13개 차트(Plotly 10 + Graphviz 3) 모두 디자인 토큰 참조. combo chart line_values 타입 미검증 1건. Graphviz Docker 설치 완비. PNG 압축 안전장치 견고. |

---

## 검증 투명성

### 검증 통계
- 검증한 가설: **42건**
- 거부된 가설 (사전 제거): **14건**
- 보고된 이슈: **18건**
- 거부율: **33%**

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 (코드로 확인) | 5 | ChecklistTable aria-label 존재 확인, progressbar role 존재 확인, Graphviz Docker 설치 확인, CORS config 기반 확인, N+1 방지 selectinload 확인 |
| Self-Challenge 기각 | 3 | 하위 프로그레스바 progressbar 중복 불필요, YEAR_PATTERNS 범위 적절, Excel merged cell 처리 정상 |
| 이미 수정됨 | 3 | DataSource "VDR" 추가(#2), back_populates(#6), HTTPException 교체(#9) |
| 설계 의도 확인 | 2 | render_html() ABC 인터페이스 유지 (미호출이지만 계약), Celery 중복 방지는 DB 상태 전이로 간접 수행 |
| 오판 | 1 | useChecklistSummary refetchInterval 불필요 — invalidate 패턴 사용 |

### 이전 리뷰 허위 양성 재확인 (재보고 하지 않음)
- `models/__init__.py`에 IMChecklist 미등록 → 실제 등록 확인됨 ✓
- PPTX 폰트 오버라이드 불일치 → `font_helper.py:101-156` title/body 분기 확인됨 ✓
- Ralph 수동 트리거 라우트 부재 → `ralph.py:105`에 존재 확인됨 ✓
