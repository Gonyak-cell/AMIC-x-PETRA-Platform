"""AMIC IM 에셋 관리 모듈 — 폰트/이미지 경로 해석 및 base64 인코딩.

Radar 프로젝트 assets.py에서 이식. 폰트 로직 100% 유지,
IMAGE_FILES를 AMIC IM 브랜딩 이미지로 교체.
"""

import base64
import logging
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
IMAGES_DIR = ASSETS_DIR / "images"

# =====================================================
# 폰트 파일 매핑
# =====================================================

# 한글 폰트 (메인) — IM 프로젝트는 4개 웨이트만 사용
PRETENDARD_FONTS = {
    400: "Pretendard-Regular.otf",
    500: "Pretendard-Medium.otf",
    600: "Pretendard-SemiBold.otf",
    700: "Pretendard-Bold.otf",
}

# 영어 폰트 (Variable font)
INTER_FONTS = {
    "variable": "Inter-Variable.ttf",
}

# 숫자/코드 폰트 (고정폭)
IBM_PLEX_MONO_FONTS = {
    400: "IBMPlexMono-Regular.otf",
    500: "IBMPlexMono-Medium.otf",
    600: "IBMPlexMono-SemiBold.otf",
    700: "IBMPlexMono-Bold.otf",
}

# 특수문자 폰트 (Variable font)
NOTO_SANS_KR_FONTS = {
    "variable": "NotoSansKR-Variable.ttf",
}

# CSS에서 실제 사용되는 weight만 임베딩 (파일 크기 최적화)
USED_PRETENDARD_WEIGHTS = {400, 500, 600, 700}
USED_IBM_PLEX_MONO_WEIGHTS = {400, 500, 600, 700}

# =====================================================
# 이미지 파일 매핑 (AMIC IM 브랜딩)
# =====================================================

IMAGE_FILES = {
    "amic_cover_bg": "amic_cover_bg.jpeg",
    "amic_logo_dark": "amic_logo_dark.png",
    "amic_logo_white": "amic_logo_white.png",
}


def font_path(family: str, weight: int | str) -> Path:
    """폰트 파일 절대 경로를 반환한다."""
    filename: str | None = None
    if family == "Pretendard":
        if isinstance(weight, int):
            filename = PRETENDARD_FONTS.get(weight)
    elif family == "Inter":
        filename = INTER_FONTS.get("variable")
    elif family == "IBMPlexMono":
        if isinstance(weight, int):
            filename = IBM_PLEX_MONO_FONTS.get(weight)
    elif family == "NotoSansKR":
        filename = NOTO_SANS_KR_FONTS.get("variable")
    else:
        raise ValueError(f"Unknown font family: {family}")

    if not filename:
        raise ValueError(f"Unknown font: {family} weight={weight}")
    return FONTS_DIR / filename


def font_uri(family: str, weight: int | str) -> str:
    """weasyprint용 file:// URI를 반환한다."""
    path = font_path(family, weight)
    return path.as_uri()


def _compress_font_to_woff2(otf_path: Path) -> tuple[bytes, str, str]:
    """OTF 폰트를 WOFF2로 압축. (data, mime, format) 반환."""
    from fontTools.ttLib import TTFont

    font = TTFont(otf_path)
    font.flavor = "woff2"
    buf = BytesIO()
    font.save(buf)
    font.close()
    return buf.getvalue(), "font/woff2", "woff2"


def font_data_uri(family: str, weight: int | str) -> tuple[str, str]:
    """폰트를 base64 data URI로 반환. WOFF2 압축 우선, 실패 시 원본.

    Returns:
        (data_uri, css_format) 튜플.
        예: ("data:font/woff2;base64,...", "woff2")
    """
    path = font_path(family, weight)
    try:
        data, mime, fmt = _compress_font_to_woff2(path)
    except Exception:
        logger.warning(f"WOFF2 변환 실패, 원본 사용: {path.name}")
        data = path.read_bytes()
        ext = path.suffix.lower()
        if ext == ".ttf":
            mime = "font/ttf"
            fmt = "truetype"
        else:
            mime = "font/otf"
            fmt = "opentype"

    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}", fmt


def image_path(name: str) -> Path:
    """이미지 파일 절대 경로를 반환한다."""
    filename = IMAGE_FILES.get(name)
    if not filename:
        raise ValueError(f"Unknown image: {name}")
    return IMAGES_DIR / filename


def image_data_uri(name: str) -> str:
    """이미지를 base64 data URI로 반환한다."""
    path = image_path(name)
    data = path.read_bytes()
    ext = path.suffix.lower()
    mime = {
        ".jpeg": "image/jpeg",
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".svg": "image/svg+xml",
    }.get(ext, "application/octet-stream")
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def generate_font_face_css() -> str:
    """@font-face CSS를 생성한다.

    폰트 체계:
    - 영어: Inter (Variable font)
    - 숫자: IBM Plex Mono (고정폭)
    - 한글: Pretendard
    - 특수문자: Noto Sans KR (Variable font)

    폰트를 base64 data URI로 임베딩하여 브라우저/weasyprint 모두 동작한다.
    WOFF2 압축을 적용하여 파일 크기를 줄인다.
    """
    rules = []

    # Inter (영어) - Variable font
    inter_path = FONTS_DIR / INTER_FONTS["variable"]
    if inter_path.exists():
        uri, fmt = font_data_uri("Inter", "variable")
        rules.append(f"""    @font-face {{
        font-family: 'Inter';
        src: url('{uri}') format('{fmt}');
        font-weight: 100 900;
        font-style: normal;
    }}""")

    # IBM Plex Mono (숫자/코드)
    for weight, filename in IBM_PLEX_MONO_FONTS.items():
        if weight not in USED_IBM_PLEX_MONO_WEIGHTS:
            continue
        path = FONTS_DIR / filename
        if not path.exists():
            continue
        uri, fmt = font_data_uri("IBMPlexMono", weight)
        rules.append(f"""    @font-face {{
        font-family: 'IBM Plex Mono';
        src: url('{uri}') format('{fmt}');
        font-weight: {weight};
        font-style: normal;
    }}""")

    # Pretendard (한글)
    for weight, filename in PRETENDARD_FONTS.items():
        if weight not in USED_PRETENDARD_WEIGHTS:
            continue
        path = FONTS_DIR / filename
        if not path.exists():
            continue
        uri, fmt = font_data_uri("Pretendard", weight)
        rules.append(f"""    @font-face {{
        font-family: 'Pretendard';
        src: url('{uri}') format('{fmt}');
        font-weight: {weight};
        font-style: normal;
    }}""")

    # Noto Sans KR (특수문자) - Variable font
    noto_path = FONTS_DIR / NOTO_SANS_KR_FONTS["variable"]
    if noto_path.exists():
        uri, fmt = font_data_uri("NotoSansKR", "variable")
        rules.append(f"""    @font-face {{
        font-family: 'Noto Sans KR';
        src: url('{uri}') format('{fmt}');
        font-weight: 100 900;
        font-style: normal;
    }}""")

    return "\n".join(rules)
