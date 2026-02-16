"""IM Design Tokens — AMIC 디자인 + SL Template (TITAN/COVENANT) 레이아웃.

PPTX와 PDF에서 동일한 토큰을 공유하여 시각적 일관성을 보장한다.
Radar 프로젝트 amic_design_tokens.py dataclass 패턴 차용.
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
    """AMIC IM 컬러 팔레트.

    SL Template의 네이비/블루를 AMIC 그린 계열로 오버레이.
    """

    # Primary
    primary: str = "#0F3A32"  # AMIC 다크그린 (헤더/제목/서브헤더 바/테이블 헤더)
    accent: str = "#26C260"  # AMIC 그린 (긍정 지표/강조/액센트)

    # Text
    text_body: str = "#3D3D3D"  # 본문 텍스트 (SL 원본 유지)
    text_dark: str = "#212121"  # 진한 텍스트
    text_secondary: str = "#777777"  # 캡션/출처
    text_white: str = "#FFFFFF"  # 서브헤더 바 위 텍스트

    # Background
    bg_white: str = "#FFFFFF"
    bg_light_green: str = "#E8F5E9"  # 라이트 배경
    bg_lighter_green: str = "#F1F8E9"  # 더 밝은 배경
    bg_cool_grey: str = "#F4F6F8"  # 섹션 구분 배경

    # Alert / Indicator
    positive: str = "#26C260"  # 양수/긍정 (녹색)
    negative: str = "#BC2C1A"  # 음수/부정/경고 (적색)
    caution: str = "#EF6C00"  # 주의/보통 (앰버)

    # Table
    table_header_bg: str = "#0F3A32"  # 테이블 헤더 배경
    table_alt_row_bg: str = "#F4F6F8"  # 테이블 줄무늬 배경

    # Gray scale
    gray_medium: str = "#757575"
    gray_dark: str = "#333333"
    gray_border: str = "#E0E0E0"  # 테이블 테두리


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMTypography:
    """AMIC IM 타이포그래피.

    폰트 체계:
    - 제목(영어): Inter (weight 800)
    - 본문(한글/영어): Pretendard
    - 숫자/KPI: IBM Plex Mono (고정폭)
    - 폴백: Noto Sans KR (특수문자/광범위 한글)
    - 차트 한글: NanumGothic (Plotly/Kaleido 전용)
    """

    # 개별 폰트명 (PPTX 테마/run 설정용)
    font_heading: str = "Inter"
    font_body: str = "Pretendard"
    font_mono: str = "IBM Plex Mono"
    font_fallback: str = "Noto Sans KR"
    font_chart: str = "NanumGothic"  # Plotly/Kaleido 전용

    # CSS font-stack (PDF 출력용)
    css_heading: str = "'Inter', 'Pretendard', 'Noto Sans KR', sans-serif"
    css_body: str = "'Pretendard', 'Inter', 'Noto Sans KR', 'Malgun Gothic', sans-serif"
    css_mono: str = "'IBM Plex Mono', monospace"
    css_fallback: str = "'Noto Sans KR', 'Pretendard', 'Malgun Gothic', sans-serif"


# ---------------------------------------------------------------------------
# Font Sizes (pt)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IMFontSizes:
    """TITAN/COVENANT 공통 폰트 사이즈 체계 (pt 단위)."""

    cover_title: int = 40  # 표지 타이틀
    toc_section_title: int = 28  # TOC 구분 슬라이드 섹션 제목
    toc_heading: int = 24  # "TABLE OF CONTENT"
    slide_title: int = 16  # MAIN 레이아웃 idx=11
    summary_text: int = 14  # 슬라이드 상단 요약/설명 (Bold)
    sub_header_bar: int = 12  # 서브헤더 바 (Bold White)
    kpi_label: int = 11  # KPI 라벨
    kpi_value: int = 20  # KPI 숫자 (IBM Plex Mono)
    body: int = 10  # 본문 (가장 빈번)
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
    """SL Template PPTX 레이아웃 이름 및 인덱스."""

    cover: str = "COVER"
    blank: str = "BLANK"  # TOC 구분자/면책/연락처
    main: str = "MAIN"  # 콘텐츠 전체


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
    cover_bg_path: str = "amic_cover_bg.jpeg"

    @classmethod
    def from_brand_assets(cls, brand: Any) -> IMDesignTokens:
        """brand_extractor 결과로 컬러/로고를 오버라이드.

        Args:
            brand: BrandAssets 인스턴스. primary_color, secondary_color,
                   logo_dark_path, logo_white_path 속성을 참조.

        Returns:
            브랜드 오버라이드가 적용된 IMDesignTokens 인스턴스.
        """
        colors = IMColorPalette(
            primary=getattr(brand, "primary_color", IMColorPalette.primary),
            accent=getattr(brand, "secondary_color", IMColorPalette.accent),
        )
        return cls(
            colors=colors,
            company_name=getattr(brand, "company_name", cls.company_name),
            logo_dark_path=getattr(brand, "logo_dark_path", cls.logo_dark_path),
            logo_white_path=getattr(brand, "logo_white_path", cls.logo_white_path),
            cover_bg_path=getattr(brand, "cover_bg_path", cls.cover_bg_path),
        )


# ---------------------------------------------------------------------------
# Singleton default
# ---------------------------------------------------------------------------

DEFAULT_TOKENS = IMDesignTokens()
