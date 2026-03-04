"""Brand Extractor 테스트 공통 fixture.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.models import BrandAssets, ExtractedColor, LogoCandidate


# ---------------------------------------------------------------------------
# Config Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config() -> BrandExtractorConfig:
    """기본 BrandExtractorConfig."""
    return BrandExtractorConfig(
        brandfetch_api_key="",
        timeout=10,
        min_logo_size=64,
        preferred_logo_size=512,
        max_colors=5,
        fallback_enabled=True,
    )


@pytest.fixture
def brandfetch_config() -> BrandExtractorConfig:
    """Brandfetch API 키가 설정된 BrandExtractorConfig."""
    return BrandExtractorConfig(
        brandfetch_api_key="test-api-key-12345",
        timeout=10,
        min_logo_size=64,
        preferred_logo_size=512,
        max_colors=5,
        fallback_enabled=True,
    )


# ---------------------------------------------------------------------------
# Model Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_brand_assets() -> BrandAssets:
    """샘플 BrandAssets."""
    return BrandAssets(
        company_name="테스트 기업",
        primary_color="#FF5733",
        secondary_color="#33FF57",
        logo_url="https://example.com/logo.png",
        confidence=0.8,
        source="website",
    )


@pytest.fixture
def fallback_brand_assets() -> BrandAssets:
    """AMIC 폴백 BrandAssets."""
    return BrandAssets(
        company_name="",
        primary_color="#0F3A32",
        secondary_color="#26C260",
        logo_dark_path="amic_logo_dark.png",
        logo_white_path="amic_logo_white.png",
        cover_bg_path="amic_cover_bg.jpeg",
        confidence=0.0,
        source="fallback",
    )


@pytest.fixture
def sample_logo_candidates() -> list[LogoCandidate]:
    """샘플 로고 후보 리스트."""
    return [
        LogoCandidate(
            url="https://example.com/logo.png",
            source="apple-touch-icon",
            width=180,
            height=180,
            has_transparency=True,
            format="png",
        ),
        LogoCandidate(
            url="https://example.com/og-image.jpg",
            source="og:image",
            width=1200,
            height=630,
            has_transparency=False,
            format="jpeg",
        ),
        LogoCandidate(
            url="https://example.com/favicon.ico",
            source="favicon",
            width=32,
            height=32,
            has_transparency=False,
            format="ico",
        ),
    ]


@pytest.fixture
def sample_extracted_colors() -> list[ExtractedColor]:
    """샘플 추출 색상 리스트."""
    return [
        ExtractedColor(hex="#FF0000", rgb=(255, 0, 0), hsv=(0.0, 1.0, 1.0), ratio=0.4),
        ExtractedColor(
            hex="#00FF00", rgb=(0, 255, 0), hsv=(120.0, 1.0, 1.0), ratio=0.3
        ),
        ExtractedColor(
            hex="#808080", rgb=(128, 128, 128), hsv=(0.0, 0.0, 0.502), ratio=0.2
        ),
        ExtractedColor(
            hex="#0000FF", rgb=(0, 0, 255), hsv=(240.0, 1.0, 1.0), ratio=0.1
        ),
    ]


# ---------------------------------------------------------------------------
# Image Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def red_image() -> Image.Image:
    """단색 빨간 이미지 (100x100)."""
    return Image.new("RGB", (100, 100), (255, 0, 0))


@pytest.fixture
def multicolor_image() -> Image.Image:
    """다색 이미지 (200x200) — 4분면 각각 다른 색."""
    img = Image.new("RGB", (200, 200))
    for x in range(200):
        for y in range(200):
            if x < 100 and y < 100:
                img.putpixel((x, y), (255, 0, 0))  # 빨강
            elif x >= 100 and y < 100:
                img.putpixel((x, y), (0, 128, 0))  # 녹색
            elif x < 100 and y >= 100:
                img.putpixel((x, y), (0, 0, 255))  # 파랑
            else:
                img.putpixel((x, y), (255, 165, 0))  # 주황
    return img


@pytest.fixture
def rgba_image() -> Image.Image:
    """RGBA 이미지 (100x100) — 절반 투명."""
    img = Image.new("RGBA", (100, 100))
    for x in range(100):
        for y in range(100):
            if x < 50:
                img.putpixel((x, y), (0, 100, 200, 255))  # 불투명
            else:
                img.putpixel((x, y), (0, 100, 200, 0))  # 완전 투명
    return img


@pytest.fixture
def red_image_bytes(red_image: Image.Image) -> bytes:
    """단색 빨간 이미지 바이트."""
    buf = BytesIO()
    red_image.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# HTML Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_html_with_logo() -> str:
    """로고가 포함된 샘플 HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:image" content="https://example.com/og-logo.png" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="icon" type="image/png" href="/favicon-32x32.png" sizes="32x32" />
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    </head>
    <body>
        <header>
            <a href="/" class="logo-link">
                <img src="/images/logo.png" class="header-logo" alt="Company Logo" />
            </a>
        </header>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_no_logo() -> str:
    """로고 없는 샘플 HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>No logo here.</p></body>
    </html>
    """


@pytest.fixture
def brandfetch_success_response() -> dict:
    """Brandfetch API 성공 응답 mock."""
    return {
        "name": "Samsung Electronics",
        "domain": "samsung.com",
        "logos": [
            {
                "type": "logo",
                "theme": "dark",
                "formats": [
                    {
                        "src": "https://cdn.brandfetch.io/samsung/logo.svg",
                        "format": "image/svg+xml",
                    },
                    {
                        "src": "https://cdn.brandfetch.io/samsung/logo.png",
                        "format": "image/png",
                    },
                ],
            },
        ],
        "colors": [
            {"hex": "#1428A0", "type": "dark"},
            {"hex": "#00A1E0", "type": "accent"},
            {"hex": "#FFFFFF", "type": "light"},
        ],
    }
