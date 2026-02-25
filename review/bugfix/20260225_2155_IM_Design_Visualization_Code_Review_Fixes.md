# IM 모듈 디자인/시각화 코드 리뷰 수정 리포트

> 수정 일시: 2026-02-25 21:55:00
> 기반 리뷰: `docs/code-review/20260225_2138_IM_Module_Design_Visualization_Code_Review_Report.md`
> 브랜치: `feat/ma-workflow`
> 빌드 검증: tsc ✅ + vite build ✅

---

## 수정 통계

| 우선순위 | 이슈 수 | 수정 완료 | 수정 파일 수 |
|---------|---------|----------|-------------|
| P0 | 1 | 1 | 1 |
| P1 | 6 | 6 | 8 |
| P2 | 7 | 7 | 9 |
| P3 | 4 | 4 | 6 |
| **합계** | **18** | **18** | **~20** |

---

## P0 수정 (1건)

### [IM-6.1a] `_parse_number()` 한국 통화 단위 승수 미적용

- **파일**: `im/src/api/services/checklist_to_imdata.py:499-511`
- **수정 내용**:
  - 승수 딕셔너리 `_UNIT_MULTIPLIER` 추가 (조원~원, 긴 접미사 우선 매칭)
  - `float(cleaned) * multiplier` 반환으로 변경
  - suffix 순서 버그 해결 (기존: "원"이 "백만원"보다 먼저 매칭)
- **영향**: IM 문서 재무 데이터 정확도 — "150억원" → 15,000,000,000 (기존: 150.0)

---

## P1 수정 (6건)

### [CP-1.1+CP-1.2] chart_embed/org_chart 중복 상수/어댑터 제거

- **파일**: `im/src/design_renderer/components/chart_embed.py`, `org_chart.py`
- **수정 내용**:
  - chart_embed.py: `CHART_DPI`, `DEFAULT_WIDTH`, `DEFAULT_HEIGHT`, `KOREAN_FONT`, `AMIC_CHART_COLORS` 삭제 → `config.py`에서 import
  - chart_embed.py + org_chart.py: 로컬 `_tokens_to_config()` → `chart_config_from_design_tokens()` 공통 어댑터 위임
  - `secondary`/`fresh` 필드 매핑 누락 해소 (공통 어댑터가 전체 14개 필드 매핑)

### [CP-1.4] `from_brand_assets()` partial reset

- **파일**: `im/src/design_renderer/design_tokens.py:247-252`
- **수정 내용**: `IMColorPalette` 생성 시 `table_header_bg=p`, `positive=a` 파생 필드 추가
- **영향**: 브랜드 오버라이드 시 테이블 헤더/긍정 색상이 primary/accent와 동기화

### [CP-2.1] management_team/shareholder_structure `set_font_with_ea` 적용

- **파일**: `management_team.py` (3곳), `shareholder_structure.py` (2곳)
- **수정 내용**: `r.font.name = t.font_body` → `set_font_with_ea(r, t.font_body)` 교체
- **영향**: `<a:ea>` 동아시아 폰트 태그 설정 — 후처리 의존 제거

### [IM-6.3a] Celery 태스크 3개 `time_limit` 설정

- **파일**: `generate_im.py`, `generate_im_from_checklist.py`, `vdr_extraction.py`
- **수정 내용**:
  - `generate_im`: `soft_time_limit=900, time_limit=960`
  - `generate_im_from_checklist`: `soft_time_limit=600, time_limit=660`
  - `extract_vdr_data`: `soft_time_limit=300, time_limit=360`
- **영향**: 워커 고갈 방지 — 무한 블로킹 태스크 강제 종료

### [IM-7.1a] pipeline.py `success` 판정 불일치

- **파일**: `im/src/design_renderer/pipeline.py:223-234, 277-283`
- **수정 내용**:
  - 폴백 성공 시 `errors` → `warnings`로 이동 (`result.errors.pop()` + `result.warnings.append(...)`)
  - 결과적으로 폴백으로 복구된 섹션은 `success=True` 판정
- **영향**: 모니터링에서 "실패" 건수 과대 보고 해소

---

## P2 수정 (7건)

### [CP-1.3] `get_color_sequence()` 시맨틱 컬러 혼입 제거

- **파일**: `im/src/chart_engine/plotly/themes.py:93-104`
- **수정**: caution(앰버)/negative(적색) → `gray_medium`/`text_secondary`/`bg_cool_grey` 중립 색상

### [CP-2.4] NanumGothic → Noto Sans KR 변경

- **파일**: `im/src/chart_engine/config.py:22`, `im/src/design_renderer/design_tokens.py:89`
- **수정**: `KOREAN_FONT = "Noto Sans KR"`, `font_chart = "Noto Sans KR"` (Docker에 `fonts-noto-cjk` 설치 대응)

### [CP-3.4] 폴백 슬라이드 에러 메시지 노출 방지

- **파일**: `im/src/design_renderer/section_renderers/fallback.py`
- **수정**: `show_error_detail` 파라미터 추가 (PPTX + HTML 양쪽). 기본값 `False` → 프로덕션에서 "해당 섹션의 데이터를 처리 중입니다." 표시. 좌표도 `IMPageLayout` 참조로 변경.

### [CP-4.1] combo chart `line_values` 타입 검증

- **파일**: `im/src/chart_engine/plotly/combo.py:60`
- **수정**: `line_values = [float(v) if v is not None else 0.0 for v in line_values]` — None 포함 시 TypeError 방지

### [m-X1] ChecklistItemRow 키보드 접근성

- **파일**: `amic-platform/src/modules/im/components/ChecklistItemRow.tsx:191`
- **수정**: `focus-visible:opacity-100` 클래스 추가 (WCAG 2.1 SC 2.4.7)

### [IM-6.5d] UniqueConstraint `fiscal_year` 추가

- **파일**: `im/src/api/db/models/im_checklist_item.py:178-182`
- **수정**: `UniqueConstraint("checklist_id", "field_key")` → `UniqueConstraint("checklist_id", "field_key", "fiscal_year")`
- **마이그레이션**: `im/alembic/versions/008_checklist_item_unique_fiscal_year.py` 신규 생성

---

## P3 수정 (4건)

### [CP-2.3] kpi_card.py docstring 불일치

- **파일**: `im/src/design_renderer/components/kpi_card.py:3,147`
- **수정**: "IBM Plex Mono" → "Pretendard ExtraBold" (실제 코드와 일치)

### [CP-3.1] 폴백 슬라이드 좌표 하드코딩

- CP-3.4 수정 시 함께 해결 — `Inches(1.5)` 등 → `lay.content_left`, `lay.content_top + 1.0`, `lay.content_width`

### [CP-3.2] TM 2-pass `factory._manager` private 멤버 접근

- **파일**: `im/src/design_renderer/pptx_engine/slide_factory.py` + `pipeline.py:376`
- **수정**: `SlideFactory.add_blank_slide()` public 메서드 추가, `factory._manager.add_slide("blank", prs)` → `factory.add_blank_slide(prs)` 교체

### [L-R1] DataSource 배지 2곳 중복

- **파일**: `amic-platform/src/modules/im/types/document.ts`, `DocumentListPage.tsx`, `DocumentDetailPage.tsx`
- **수정**: `DATA_SOURCE_BADGE` 공통 상수를 `document.ts`에 추출, 2개 페이지에서 import 사용

---

## 미수정 (테스트 작성 — IM-7.6a)

P1 이슈 [IM-7.6a]의 테스트 작성(7개 서비스 2,773라인)은 별도 세션에서 진행 필요:
- `test_checklist_to_imdata.py` — P0 `_parse_number()` 검증 최우선
- `test_vdr_analysis_service.py`
- `test_checklist_routes.py`

---

## 수정 파일 전체 목록

| # | 파일 | 변경 유형 |
|---|------|----------|
| 1 | `im/src/api/services/checklist_to_imdata.py` | 수정 (P0) |
| 2 | `im/src/design_renderer/components/chart_embed.py` | 수정 (P1) |
| 3 | `im/src/design_renderer/components/org_chart.py` | 수정 (P1) |
| 4 | `im/src/design_renderer/design_tokens.py` | 수정 (P1+P2) |
| 5 | `im/src/design_renderer/section_renderers/management_team.py` | 수정 (P1) |
| 6 | `im/src/design_renderer/section_renderers/shareholder_structure.py` | 수정 (P1) |
| 7 | `im/src/api/tasks/generate_im.py` | 수정 (P1) |
| 8 | `im/src/api/tasks/generate_im_from_checklist.py` | 수정 (P1) |
| 9 | `im/src/api/tasks/vdr_extraction.py` | 수정 (P1) |
| 10 | `im/src/design_renderer/pipeline.py` | 수정 (P1+P3) |
| 11 | `im/src/chart_engine/plotly/themes.py` | 수정 (P2) |
| 12 | `im/src/chart_engine/config.py` | 수정 (P2) |
| 13 | `im/src/design_renderer/section_renderers/fallback.py` | 수정 (P2+P3) |
| 14 | `im/src/chart_engine/plotly/combo.py` | 수정 (P2) |
| 15 | `amic-platform/src/modules/im/components/ChecklistItemRow.tsx` | 수정 (P2) |
| 16 | `im/src/api/db/models/im_checklist_item.py` | 수정 (P2) |
| 17 | `im/alembic/versions/008_checklist_item_unique_fiscal_year.py` | 신규 (P2) |
| 18 | `im/src/design_renderer/components/kpi_card.py` | 수정 (P3) |
| 19 | `im/src/design_renderer/pptx_engine/slide_factory.py` | 수정 (P3) |
| 20 | `amic-platform/src/modules/im/types/document.ts` | 수정 (P3) |
| 21 | `amic-platform/src/modules/im/pages/DocumentListPage.tsx` | 수정 (P3) |
| 22 | `amic-platform/src/modules/im/pages/DocumentDetailPage.tsx` | 수정 (P3) |
