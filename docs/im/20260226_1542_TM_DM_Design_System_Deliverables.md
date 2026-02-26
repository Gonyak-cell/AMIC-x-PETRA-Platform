# TM/DM PPT 디자인 시스템 — 산출물 생성 보고서

> 작성: 2026-02-26 15:42

## 개요

4개 원본 PPTX 템플릿(NX3 Games DM, SPICY TM, SWITCH TM, YTN Structure DM)을 python-pptx XML 파싱으로 재분석하여 3가지 산출물을 생성/갱신하였다.

### 분석 대상

| 파일명 | 슬라이드 | 차트 | 표 |
|--------|---------|------|-----|
| SPICY - TM - 260219 vSHARE.pptx | 25 | 10 | 18 |
| SWITCH - TM - 260119.pptx | 24 | 7 | 15 |
| NX3 Games - DM - 260116.pptx | 7 | 3 | 0 |
| YTN - Structure DM - 260116.pptx | 6 | 0 | 3 |

---

## 산출물 3종

| # | 산출물 | 경로 | 상태 |
|---|--------|------|------|
| 1 | 디자인 시스템 매뉴얼 | `docs/im/20260226_1521_TM_DM_Design_System_Manual.md` | 재작성 |
| 2 | 디자인 토큰 코드 | `im/src/design_renderer/design_tokens.py` | 보정 |
| 3 | 빈 TM/DM 템플릿 PPTX | `im/templates/AMIC_TM_Template.pptx` (25슬라이드), `im/templates/AMIC_DM_Template.pptx` (7슬라이드) | 재생성 |

---

## 이전 분석 대비 보정 사항 (5건)

### 1. 섹션 바 배경색 보정
- **이전**: `#3D3D3D` (텍스트 색상과 혼동)
- **보정**: `#0F3A32` (실측: rect fill `#0F3A32` 60건 최다)
- **수정 파일**: `design_tokens.py` → `IMColorPalette.section_bar_bg`

### 2. 테이블 테두리 상세화
- **이전**: "테두리 없음"
- **보정**: 가로선 존재 — `0.5pt #6A6A6A`, 헤더 하단 solid / 데이터 행 하단 dash / 마지막 행 solid
- **수정 파일**: `design_tokens.py` → `IMTableStyle` 5개 필드 추가
  - `border_color`, `border_width_pt`, `header_border_style`, `data_border_style`, `last_row_border_style`

### 3. TOC 테이블 좌표
- **이전**: 미포함
- **보정**: `l=0.957cm, t=6.024cm, w=9.80cm, h=4.40cm` (4행×2열, col0=1.50cm/col1=8.30cm)
- **수정 파일**: `design_tokens.py` → `IMDualPanelLayout` 4개 필드 추가, `generate_blank_templates.py` → `_add_toc_table()` 신규

### 4. 재무제표 시작 Y
- **이전**: 일반 콘텐츠와 동일 (`6.024cm`)
- **보정**: `3.325cm` (타이틀 바 없이 직접 시작, 최대 세로 공간 확보)
- **수정 파일**: `design_tokens.py` → `IMDualPanelLayout.financial_start_y`, `generate_blank_templates.py` → 재무 슬라이드 4개

### 5. 커버/TOC 줄간격
- **이전**: 본문 110% 일괄 적용
- **보정**: 표지 프로젝트명/날짜 `90%`, 문서유형 `110%`, TOC 제목 `24pt` (40pt 아님)
- **수정 파일**: `generate_blank_templates.py` → `_add_forest_slide()` 줄간격 파라미터, `_add_toc_slide()` 직접 생성으로 전환

---

## 수정 파일 상세

### 1. `im/src/design_renderer/design_tokens.py`

| 클래스 | 수정 내용 |
|--------|----------|
| `IMColorPalette` | `section_bar_bg: "#0F3A32"` (보정), `table_border: "#6A6A6A"` (신규) |
| `IMTableStyle` | 테두리 5개 필드 추가 (`border_color`, `border_width_pt`, `header_border_style`, `data_border_style`, `last_row_border_style`) |
| `IMDualPanelLayout` | TOC 4개 필드 (`toc_x/y/width/height`), `financial_start_y` 추가 |
| `IMFontSizes` | 표 폰트 4개 필드 (`table_header=10`, `table_body=10`, `table_financial=9`, `table_small=8`) |

### 2. `im/scripts/generate_blank_templates.py`

| 함수/상수 | 수정 내용 |
|-----------|----------|
| 상수 추가 | `TOC_TABLE_X/Y/W/H`, `FINANCIAL_START_Y` |
| `_add_textbox()` | `line_spacing_pct` 파라미터 추가 (XML `a:spcPct` 직접 설정) |
| `_add_forest_slide()` | 표지 줄간격 90%/110% 적용 |
| `_add_toc_table()` | **신규** — 실측 좌표 테이블 생성, 투명 셀/테두리 없음 |
| `_add_toc_slide()` | `_add_forest_slide` 호출 제거 → FOREST 직접 생성, 제목 Y=3.80/24pt |
| 재무 슬라이드 (21~24) | `CONTENT_START_Y` → `FINANCIAL_START_Y`, 섹션바 제거, 전체 너비 |

### 3. `docs/im/20260226_1521_TM_DM_Design_System_Manual.md`

6개 카테고리 + 사전확인 3항으로 구성된 전체 매뉴얼:
1. 슬라이드 규격 및 마스터 레이아웃 (27.517×19.050cm, 5 레이아웃)
2. 타이포그래피 (16종 폰트 매핑)
3. 텍스트 상자 및 불릿 포인트 (4종 불릿, 3단계 수준)
4. 표 서식 (5종 표 유형, 헤더 `#26C260`, 테두리 상세)
5. 시각적 개체 (9종 도형, 10색 체계)
6. 차트 (4종 차트 타입, 6종 배치 좌표)

---

## 검증 결과

### design_tokens import
```
section_bar_bg: #0F3A32 ✅
table_border: #6A6A6A ✅
table_style.border_color: #6A6A6A ✅
dual_panel.toc_x: 0.957 ✅
dual_panel.financial_start_y: 3.325 ✅
font_sizes.table_header: 10 ✅
```

### PPTX 메타데이터
```
AMIC_TM_Template.pptx: 25 slides, 27.517 × 19.050 cm, 5 layouts ✅
AMIC_DM_Template.pptx: 7 slides, 27.517 × 19.050 cm, 5 layouts ✅
```

### TOC 슬라이드 좌표 검증 (원본 vs 생성)
| 요소 | 원본 실측 | 생성 결과 |
|------|----------|----------|
| 제목 위치 | (1.26, 3.80) | (1.26, 3.80) ✅ |
| 제목 크기 | 9.02×1.06 | 9.02×1.06 ✅ |
| 테이블 위치 | (0.96, 6.02) | (0.96, 6.02) ✅ |
| 테이블 크기 | 9.80×4.40 | 9.80×4.40 ✅ |
| col0 너비 | 1.50cm | 1.50cm ✅ |
| col1 너비 | 8.30cm | 8.30cm ✅ |
