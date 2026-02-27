"""디자인 상수 — Forest 테마 색상, 폰트, 레이아웃.

memo_generator.py의 디자인 상수를 공유하되,
template_engine 전용 상수를 추가 정의한다.
"""

# ── 색상 (hex, # 없이) ───────────────────────────────────────

COLOR_GREEN_PRIMARY = "0F3A32"  # 섹션 헤더 배경 (진한 녹색)
COLOR_GREEN_ACCENT = "1C8F57"  # 필드명 강조 (중간 녹색)
COLOR_GREEN_BRIGHT = "26C260"  # 밝은 녹색
COLOR_GREEN_FRESH = "A3E96B"  # 그라데이션, 보조 차트
COLOR_GREEN_LIGHT = "E6FDD6"  # 교대 행 배경

COLOR_TEXT_DARK = "3D3D3D"  # 본문 텍스트
COLOR_TEXT_BLACK = "000000"
COLOR_TEXT_WHITE = "FFFFFF"
COLOR_TEXT_GRAY = "808080"
COLOR_GRAY_MID = "6A6A6A"
COLOR_NEGATIVE = "BC2C1A"  # 음수 빨간색

# ── 폰트 ──────────────────────────────────────────────────────

FONT_HEADING = "SUITE"  # 제목용 (Bold)
FONT_BODY = "SUIT Medium"  # 본문/데이터용
FONT_FALLBACK = "맑은 고딕"  # 시스템 폴백

# ── 스케일링 ──────────────────────────────────────────────────

SCALE_WON_TO_THOUSAND = 1e-3  # 원 → 천원 (÷1,000)
SCALE_WON_TO_MILLION = 1e-6  # 원 → 백만원 (÷1,000,000)
SCALE_WON_TO_BILLION = 1e-8  # 원 → 억원 (÷100,000,000)

# ── 폰트 크기 (pt) ────────────────────────────────────────────

FONT_SIZE_TITLE = 18
FONT_SIZE_BODY = 10
FONT_SIZE_FOOTNOTE = 8
MIN_FONT_SIZE = 7  # 폰트 축소 하한

# ── 레이아웃 (inches) ─────────────────────────────────────────

SLIDE_WIDTH = 10.8333
SLIDE_HEIGHT = 7.5
CONTENT_LEFT = 0.4954
CONTENT_TOP = 1.25
CONTENT_WIDTH = 9.8425

# ── 테이블 ────────────────────────────────────────────────────

TABLE_ROW_HEIGHT = 0.26  # inches
TABLE_LABEL_COL_WIDTH = 2.6  # inches
TABLE_DATA_COL_WIDTH = 0.91  # inches
MAX_ROWS_PER_SLIDE = 20  # 페이지 분할 기준

# ── 숫자 서식 ─────────────────────────────────────────────────

NUMBER_FORMAT_THOUSANDS = "#,##0"
NUMBER_FORMAT_NEGATIVE_PARENS = '#,##0;(#,##0);"-"'
THOUSANDS_SEPARATOR = ","
NA_DISPLAY = "N/A"
