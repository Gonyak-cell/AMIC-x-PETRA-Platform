"""Brand Extractor 데이터 모델 (T-B01).

> 마지막 수정: 2026-02-10 22:00:00

BrandAssets, LogoCandidate, ExtractedColor 등 브랜드 추출 결과를 표현하는
데이터 클래스를 정의한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractedColor:
    """K-Means로 추출된 단일 색상.

    Attributes:
        hex: HEX 컬러 코드 (예: "#FF5733").
        rgb: (R, G, B) 튜플 (0-255).
        hsv: (H, S, V) 튜플 — H: 0-360, S: 0-1, V: 0-1.
        ratio: 이미지 내 해당 색상의 비율 (0-1).
        role: 분류 결과 ("primary" | "secondary" | "accent" | "").
    """

    hex: str
    rgb: tuple[int, int, int]
    hsv: tuple[float, float, float]
    ratio: float
    role: str = ""


@dataclass
class LogoCandidate:
    """로고 후보.

    Attributes:
        url: 로고 이미지 URL.
        source: 탐지 출처 ("og:image" | "apple-touch-icon" | "favicon" | "css-selector" | "brandfetch").
        width: 이미지 너비 (px). 0이면 미확인.
        height: 이미지 높이 (px). 0이면 미확인.
        has_transparency: 투명 배경 여부 (PNG alpha).
        format: 이미지 포맷 ("png" | "svg" | "jpeg" | "ico").
        score: 품질 점수 (0-1). LogoScorer가 부여.
    """

    url: str
    source: str
    width: int = 0
    height: int = 0
    has_transparency: bool = False
    format: str = ""
    score: float = 0.0


@dataclass
class BrandAssets:
    """브랜드 자산 — 모듈 최종 출력.

    IMDesignTokens.from_brand_assets()에서 getattr로 접근하는 필드:
    - primary_color, secondary_color, company_name
    - logo_dark_path, logo_white_path, cover_bg_path

    Attributes:
        company_name: 기업명.
        primary_color: 1차 브랜드 색상 HEX.
        secondary_color: 2차 브랜드 색상 HEX.
        logo_dark_path: 어두운 배경용 로고 로컬 경로.
        logo_white_path: 밝은 배경용 로고 로컬 경로.
        cover_bg_path: 커버 배경 이미지 경로.
        logo_url: 원본 로고 URL.
        favicon_url: 파비콘 URL.
        confidence: 추출 신뢰도 (0-1).
        source: 추출 출처 ("brandfetch" | "website" | "fallback").
        additional_colors: 추가 추출 색상 HEX 리스트.
        warnings: 추출 과정에서 발생한 경고 메시지.
    """

    company_name: str = ""
    primary_color: str = "#0F3A32"
    secondary_color: str = "#26C260"
    logo_dark_path: str = ""
    logo_white_path: str = ""
    cover_bg_path: str = ""
    logo_url: str = ""
    favicon_url: str = ""
    confidence: float = 0.0
    source: str = "fallback"
    additional_colors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
