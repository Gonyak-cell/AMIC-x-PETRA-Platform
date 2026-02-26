"""IM Design Tokens — AMIC 공식 디자인 시스템 + SL Template 레이아웃.

AMIC Design vF.pdf 기반 공식 컬러 팔레트, SUITE/Pretendard 폰트 체계 적용.
PPTX 전용 출력 (PDF 제거).

TM/DM 실측 데이터 반영 (2026-02-26):
- 4개 PPTX 템플릿(NX3 DM, SPICY TM, SWITCH TM, YTN DM) XML 파싱 결과 적용
- 불릿, 테이블, 듀얼 패널 레이아웃 사양 추가
- 문서: docs/im/20260226_1436_TM_DM_Design_System_Manual.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


# ---------------------------------------------------------------------------
# Color Palette
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMColorPalette:
    """AMIC 공식 컬러 팔레트 (AMIC Design vF.pdf 기준).

    5단계 그린 시스템:
    - Signature Green → 헤더/테이블 헤더/표지
    - Solid Green → 보조 강조/차트 보조색
    - Highlight Green → 긍정 지표/메인 하이라이터
    - Fresh Green → 그래디언트/보조 차트색
    - Light Green → 연한 배경/카드 배경
    """

    # AMIC 그린 5단계
    primary: str = "#0F3A32"  # Signature Green (표지/헤더/테이블 헤더)
    secondary: str = "#1C8F57"  # Solid Green (보조 강조/차트 보조색)
    accent: str = "#26C260"  # Highlight Green (긍정 지표/메인 하이라이터)
    fresh: str = "#A3E96B"  # Fresh Green (그래디언트/보조 차트색)
    light: str = "#E6FDD6"  # Light Green (연한 배경/카드 배경)

    # Text (TM/DM 실측: #3D3D3D 본문, #2A2A2A 테마 dk1)
    text_body: str = "#3D3D3D"  # 본문 텍스트 (TM/DM 실측)
    text_dark: str = "#2A2A2A"  # 진한 텍스트 (테마 dk1 일치)
    text_secondary: str = "#777777"  # 캡션/출처
    text_white: str = "#FFFFFF"  # 어두운 배경 위 텍스트

    # Background
    bg_white: str = "#FFFFFF"
    bg_light_green: str = "#E6FDD6"  # AMIC Light Green
    bg_lighter_green: str = "#F1F8E9"  # 더 밝은 배경
    bg_cool_grey: str = "#F4F6F8"  # 섹션 구분 배경

    # Alert / Indicator
    positive: str = "#26C260"  # Highlight Green (양수/긍정)
    negative: str = "#BC2C1A"  # 음수/부정/경고 (적색)
    caution: str = "#EF6C00"  # 주의/보통 (앰버)
    warning_red: str = "#FF3838"  # TM/DM 경고/주의 표시

    # Table (TM/DM 실측: 헤더 #26C260, 강조행 #E6FDD6)
    table_header_bg: str = "#26C260"  # Highlight Green 테이블 헤더 (TM/DM 실측)
    table_alt_row_bg: str = "#E6FDD6"  # Light Green 강조행 (TM/DM 실측)

    # Gray scale
    gray_medium: str = "#757575"
    gray_dark: str = "#333333"
    gray_border: str = "#E0E0E0"  # 테이블 테두리
    gray_arrow: str = "#B0B0B0"  # 비활성 화살표/연결선

    # Section bar
    section_bar_bg: str = "#0F3A32"  # 섹션 타이틀 바 배경 (실측: rect fill #0F3A32 최다)

    # Table border
    table_border: str = "#6A6A6A"  # 테이블 가로선 색상 (실측: 0.5pt solid/dash)


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMTypography:
    """AMIC 공식 타이포그래피 (AMIC Design vF.pdf 기준).

    폰트 체계:
    - 제목: SUITE (Bold) — 한국어/영어 공용 제목 폰트
    - 본문: Pretendard (Regular/Medium) — 한국어/영어 공용 본문 폰트
    - KPI 숫자: Pretendard (ExtraBold) — 대형 숫자 표시
    - 폴백: Noto Sans KR (특수문자/광범위 한글)
    - 차트 한글: NanumGothic (Plotly/Kaleido 전용)
    """

    # 개별 폰트명 (PPTX 테마/run 설정용)
    font_heading: str = "SUITE"
    font_body: str = "Pretendard"
    font_mono: str = "Pretendard"  # KPI 숫자도 Pretendard ExtraBold
    font_fallback: str = "Noto Sans KR"
    font_chart: str = "Noto Sans KR"  # Plotly/Kaleido 전용 (Docker에 fonts-noto-cjk 설치)
    font_cover_subtitle: str = "SUIT Medium"  # 표지 부제/날짜 전용 (TM/DM 실측)

    # CSS font-stack (PDF 미사용, 호환성 유지)
    css_heading: str = "'SUITE', 'Pretendard', 'Noto Sans KR', sans-serif"
    css_body: str = "'Pretendard', 'SUITE', 'Noto Sans KR', 'Malgun Gothic', sans-serif"
    css_mono: str = "'Pretendard', monospace"
    css_fallback: str = "'Noto Sans KR', 'Pretendard', 'Malgun Gothic', sans-serif"


# ---------------------------------------------------------------------------
# Font Sizes (pt)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMFontSizes:
    """TITAN/COVENANT 공통 폰트 사이즈 체계 (pt 단위)."""

    cover_title: int = 40  # 표지 타이틀 (SUITE Heavy)
    cover_subtitle: int = 24  # 표지 부제 (SUIT Medium, TM/DM 실측)
    cover_date: int = 16  # 표지 날짜 (SUIT Medium, TM/DM 실측)
    confidential: int = 10  # Confidential 문구 (SUITE Heavy, TM/DM 실측)
    toc_section_title: int = 14  # TOC 항목 (TM/DM 실측: 14pt)
    toc_heading: int = 24  # "TABLE OF CONTENT" 제목
    slide_title: int = 16  # MAIN 레이아웃 idx=11
    summary_text: int = 14  # 슬라이드 상단 요약/설명 (Bold)
    sub_header_bar: int = 12  # 서브헤더 바 (Bold White)
    kpi_label: int = 11  # KPI 라벨
    kpi_value: int = 20  # KPI 숫자 (IBM Plex Mono)
    body: int = 10  # 본문 (가장 빈번)
    table_header: int = 10  # 테이블 헤더 (실측: bold white on #26C260)
    table_body: int = 10  # 테이블 데이터 (실측)
    table_financial: int = 9  # 재무제표 표 (실측: P&L, BS)
    table_small: int = 8  # DM 소형 표 / 캡테이블 (실측: YTN)
    footnote: int = 9  # 각주/소스
    small_label: int = 8  # 소형 라벨/데이터
    minimum: int = 7  # 최소 텍스트 (저작권 등, 오버플로우 하한)
    page_number: int = 10  # 페이지 번호


# ---------------------------------------------------------------------------
# Page Layout (inches)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMPageLayout:
    """SL Template 레이아웃 — Landscape Letter (10.83" × 7.5").

    TITAN과 COVENANT 모두 동일한 SL Template을 사용한다.
    """

    # 슬라이드/페이지 크기
    page_width: float = 10.83  # inches
    page_height: float = 7.5  # inches

    # 여백
    margin_left: float = 0.5  # inches
    margin_right: float = 0.5  # inches
    margin_top: float = 0.6  # inches
    margin_bottom: float = 1.0  # inches (각주/페이지번호 포함)

    # 콘텐츠 영역 (계산값)
    @property
    def content_left(self) -> float:
        return self.margin_left

    @property
    def content_top(self) -> float:
        """콘텐츠 시작 y — 제목 아래."""
        return 1.07  # inches (제목 영역 고려)

    @property
    def content_width(self) -> float:
        return self.page_width - self.margin_left - self.margin_right

    @property
    def content_height(self) -> float:
        """콘텐츠 영역 높이 (제목~각주 사이)."""
        return 6.5 - self.content_top  # bottom=6.5"

    @property
    def content_right(self) -> float:
        return self.page_width - self.margin_right

    @property
    def content_bottom(self) -> float:
        return 6.5  # inches

    # PPTX 플레이스홀더 idx
    ph_title_idx: int = 11
    ph_footnote_idx: int = 12
    ph_page_number_idx: int = 13

    # 재무 테이블 열 레이아웃 (TITAN/COVENANT 패턴)
    table_label_col_width: float = 2.6  # inches (첫 번째 열: 계정명)
    table_data_col_width: float = 0.91  # inches (데이터 열 7개)
    table_row_height: float = 0.26  # inches


# ---------------------------------------------------------------------------
# PPTX Layout Names
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMPPTXLayouts:
    """SL Template PPTX 레이아웃 이름 및 인덱스 (TM/DM 실측 5종).

    NOTE: 현재 레이아웃 조회는 create_template._PURPOSE_TO_INDEX를 통해 수행됨.
    이 클래스는 레이아웃 이름 상수 참조용으로 유지. 향후 통합 가능.
    """

    blank: str = "BLANK"  # 레이아웃 0: 완전 빈 슬라이드
    forest: str = "FOREST"  # 레이아웃 1: 표지/TOC/간지/면책/연락처 (배경 이미지)
    blank_pgno: str = "BLANK_PGNO"  # 레이아웃 2: 페이지 번호만
    main: str = "MAIN"  # 레이아웃 3: 일반 콘텐츠 (타이틀+푸터+페이지번호)
    main_andersen: str = "MAIN_w/Andersen"  # 레이아웃 4: Andersen 공동 브랜딩
    cover: str = "FOREST"  # 하위 호환 alias (기존 코드 호환)


# ---------------------------------------------------------------------------
# Bullet Point Style (TM/DM 실측)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMBulletStyle:
    """TM/DM 불릿 포인트 체계 (4개 PPTX 실측 기반).

    3단계 불릿 시스템:
    - Level 1 Primary: Wingdings ü (체크마크) 또는 § (큰 점)
    - Level 2 Secondary: Pretendard - (하이픈)
    - Emphasis: Pretendard → (화살표, 결론/시사점)
    """

    # Level 1 (primary)
    level1_char: str = "\u00fc"  # Wingdings ü (체크마크)
    level1_alt_char: str = "\u00a7"  # Wingdings § (큰 점)
    level1_font: str = "Wingdings"
    level1_indent_cm: float = -0.476  # 내어쓰기 (-171,450 EMU)
    level1_margin_left_cm: float = 0.476  # 왼쪽 여백 (171,450 EMU)

    # Level 2 (secondary)
    level2_char: str = "-"  # 하이픈
    level2_font: str = "Pretendard"
    level2_indent_cm: float = -0.476
    level2_margin_left_cm: float = 0.997  # L1 marL + 0.521cm

    # Emphasis
    emphasis_char: str = "\u2192"  # → 화살표 (결론/시사점)
    emphasis_font: str = "Pretendard"

    # Spacing
    line_spacing: float = 1.1  # TM 기본 줄 간격
    space_before_emu: int = 38100  # ≈3pt
    space_after_emu: int = 38100  # ≈3pt


# ---------------------------------------------------------------------------
# Table Style (TM/DM 실측)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMTableStyle:
    """TM/DM 테이블 서식 체계 (4개 PPTX 실측 기반).

    특징: 미니멀 디자인 — 세로선 없음, 가로선 최소화.
    """

    cell_margin_lr_cm: float = 0.1  # 셀 좌/우 여백
    cell_margin_tb_cm: float = 0.0  # 셀 상/하 여백
    vertical_borders: bool = False  # 세로선 없음 (좌/우 lnL/lnR = noFill)
    header_anchor: str = "ctr"  # 헤더 수직 중앙
    data_anchor: str = "ctr"  # 데이터 수직 중앙
    sub_item_margin_left_cm: float = 0.4  # 재무제표 하위 항목 들여쓰기
    first_row: bool = True  # 헤더 행 별도 스타일
    band_row: bool = True  # 줄무늬 행

    # 테두리 상세 (실측: 가로선만 존재, 세로선 없음)
    border_color: str = "#6A6A6A"  # 가로선 색상
    border_width_pt: float = 0.5  # 가로선 두께
    header_border_style: str = "solid"  # 헤더 하단 실선
    data_border_style: str = "dash"  # 데이터 행 하단 대시선
    last_row_border_style: str = "solid"  # 마지막 행 하단 실선 복귀


# ---------------------------------------------------------------------------
# Dual Panel Layout (TM/DM 실측)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMDualPanelLayout:
    """듀얼 패널 레이아웃 좌표 (cm 단위, 4개 PPTX 실측 기반).

    좌/우 동일 너비(12.2cm) 패널 구조, 섹션 바 + 콘텐츠 영역.
    """

    left_x: float = 1.258  # 좌측 패널 시작 X
    right_x: float = 14.058  # 우측 패널 시작 X
    panel_width: float = 12.2  # 각 패널 너비
    full_width: float = 25.0  # 전폭 너비
    gap: float = 0.6  # 패널 간 간격 (14.058 - 1.258 - 12.2)
    section_bar_y: float = 4.723  # 섹션 바 Y 좌표
    section_bar_height: float = 0.8  # 섹션 바 높이
    content_start_y: float = 6.024  # 콘텐츠 시작 Y
    content_end_y: float = 16.5  # 콘텐츠 하단 Y (근사)
    content_height: float = 10.5  # 가용 높이 (근사)

    # TOC 테이블 좌표 (실측: FOREST 레이아웃 내 목차)
    toc_title_y: float = 3.80  # TOC 제목 Y (실측)
    toc_x: float = 0.957  # TOC 테이블 X
    toc_y: float = 6.024  # TOC 테이블 Y
    toc_width: float = 9.8  # TOC 테이블 너비
    toc_height: float = 4.4  # TOC 테이블 높이

    # 커버 슬라이드 좌표 (실측: FOREST 배경 위)
    cover_margin_x: float = 1.258  # 커버 좌측 마진
    cover_title_y: float = 6.0  # 프로젝트명 Y
    cover_subtitle_y: float = 9.5  # 부제/날짜 Y

    # 재무제표 시작 Y (타이틀 바 없이 직접 시작)
    financial_start_y: float = 3.325


# ---------------------------------------------------------------------------
# Integrated Design Tokens
# ---------------------------------------------------------------------------


@dataclass
class IMDesignTokens:
    """IM 문서 통합 디자인 토큰.

    AMIC 디자인을 기본값으로 사용하되, brand_extractor 모듈과 연동하여
    클라이언트별 브랜딩 오버라이드를 지원한다.

    오버라이드 범위: 컬러 팔레트 전체, 로고 이미지.
    폰트 체계와 레이아웃은 AMIC/SL Template 고정.
    """

    colors: IMColorPalette = field(default_factory=IMColorPalette)
    typography: IMTypography = field(default_factory=IMTypography)
    font_sizes: IMFontSizes = field(default_factory=IMFontSizes)
    layout: IMPageLayout = field(default_factory=IMPageLayout)
    pptx_layouts: IMPPTXLayouts = field(default_factory=IMPPTXLayouts)
    bullets: IMBulletStyle = field(default_factory=IMBulletStyle)
    table_style: IMTableStyle = field(default_factory=IMTableStyle)
    dual_panel: IMDualPanelLayout = field(default_factory=IMDualPanelLayout)

    # 브랜딩 메타
    company_name: str = "AMIC Law & PetraBridge Partners"
    logo_text: str = "AMIC & PETRABRIDGE PARTNERS"
    footer_note: str = (
        "본 자료는 기밀 정보를 포함하고 있으며, 수신인 이외의 자에 대한 "
        "공개, 배포 또는 복사를 금합니다."
    )

    # 로고 이미지 경로 (assets/images/ 기준 상대 경로)
    logo_dark_path: str = "amic_logo_dark.png"
    logo_white_path: str = "amic_logo_white.png"
    cover_bg_path: str = "forest_cover.jpg"  # AMIC 공식 Forest Cover

    # SVG 로고 경로 (assets/images/logos/ 기준)
    logo_main_svg: str = "logos/AMIC_Main.svg"
    logo_combined_svg: str = "logos/AMIC_n_PETRA_Main_KR.svg"
    logo_petra_svg: str = "logos/PETRA_Main_Simple.svg"

    @classmethod
    def from_brand_assets(cls, brand: Any) -> IMDesignTokens:
        """brand_extractor 결과로 컬러/로고를 오버라이드.

        Args:
            brand: BrandAssets 인스턴스. primary_color, secondary_color,
                   logo_dark_path, logo_white_path 속성을 참조.

        Returns:
            브랜드 오버라이드가 적용된 IMDesignTokens 인스턴스.
        """
        p = getattr(brand, "primary_color", IMColorPalette.primary)
        a = getattr(brand, "secondary_color", IMColorPalette.accent)
        colors = IMColorPalette(
            primary=p,
            accent=a,
            table_header_bg=p,
            positive=a,
        )
        return cls(
            colors=colors,
            company_name=getattr(brand, "company_name", cls.company_name),
            footer_note=getattr(brand, "footer_note", cls.footer_note),
            logo_dark_path=getattr(brand, "logo_dark_path", cls.logo_dark_path),
            logo_white_path=getattr(brand, "logo_white_path", cls.logo_white_path),
            cover_bg_path=getattr(brand, "cover_bg_path", cls.cover_bg_path),
        )


# ---------------------------------------------------------------------------
# Singleton default
# ---------------------------------------------------------------------------

DEFAULT_TOKENS = IMDesignTokens()
