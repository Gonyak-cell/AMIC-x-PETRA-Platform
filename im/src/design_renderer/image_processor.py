"""이미지 다운로드 및 처리 모듈.

원격/로컬 이미지를 다운로드·리사이즈하여 base64 data URI로 변환한다.
Radar 프로젝트 image_processor.py 기반 이식 + 파라미터화 확장.
"""

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# 기본 이미지 처리 설정
DEFAULT_MAX_WIDTH = 480  # 픽셀
DEFAULT_MAX_HEIGHT = 270  # 픽셀
JPEG_QUALITY = 85
DOWNLOAD_TIMEOUT = 10  # 초


def download_and_process_image(
    url: str,
    *,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> Optional[str]:
    """이미지를 다운로드, 리사이즈, base64 data URI로 변환.

    실패 시 None을 반환하며 경고 로그만 남긴다 (렌더링에 영향 없음).

    Args:
        url: 이미지 URL.
        max_width: 최대 너비(px).
        max_height: 최대 높이(px).

    Returns:
        base64 data URI 문자열 또는 None.
    """
    if not url:
        return None

    try:
        image_bytes = _download_image(url)
        if not image_bytes:
            return None

        resized_bytes = _resize_image(image_bytes, max_width, max_height)
        if not resized_bytes:
            return None

        b64 = base64.b64encode(resized_bytes).decode("ascii")
        data_uri = f"data:image/jpeg;base64,{b64}"

        logger.info("이미지 처리 성공: %s... (%d bytes)", url[:60], len(resized_bytes))
        return data_uri

    except Exception as e:
        logger.warning("이미지 처리 실패: %s... - %s", url[:60], e)
        return None


def download_and_process_image_with_size(
    url: str,
    *,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> Optional[Tuple[str, int, int]]:
    """이미지를 다운로드, 리사이즈, base64 data URI + 크기 반환.

    Args:
        url: 이미지 URL.
        max_width: 최대 너비(px).
        max_height: 최대 높이(px).

    Returns:
        (data_uri, width, height) 튜플 또는 None.
    """
    if not url:
        return None

    try:
        image_bytes = _download_image(url)
        if not image_bytes:
            return None

        result = _resize_image_with_size(image_bytes, max_width, max_height)
        if not result:
            return None

        resized_bytes, width, height = result
        b64 = base64.b64encode(resized_bytes).decode("ascii")
        data_uri = f"data:image/jpeg;base64,{b64}"

        logger.info(
            "이미지 처리 성공: %s... (%dx%d, %d bytes)",
            url[:60],
            width,
            height,
            len(resized_bytes),
        )
        return data_uri, width, height

    except Exception as e:
        logger.warning("이미지 처리 실패: %s... - %s", url[:60], e)
        return None


def embed_local_image(
    file_path: str | Path,
    *,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
    mime_type: str | None = None,
) -> Optional[str]:
    """로컬 이미지 파일을 base64 data URI로 변환.

    Args:
        file_path: 로컬 이미지 파일 경로.
        max_width: 최대 너비(px). 0이면 리사이즈 안 함.
        max_height: 최대 높이(px). 0이면 리사이즈 안 함.
        mime_type: MIME 타입 오버라이드. None이면 확장자에서 추론.

    Returns:
        base64 data URI 문자열 또는 None.
    """
    path = Path(file_path)
    if not path.is_file():
        logger.warning("파일 없음: %s", path)
        return None

    try:
        image_bytes = path.read_bytes()

        if max_width > 0 and max_height > 0:
            resized = _resize_image(image_bytes, max_width, max_height)
            if resized is not None:
                image_bytes = resized
                if mime_type is None:
                    mime_type = "image/jpeg"

        if mime_type is None:
            mime_type = _guess_mime_type(path.suffix)

        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_uri = f"data:{mime_type};base64,{b64}"

        logger.info("로컬 이미지 임베딩: %s (%d bytes)", path.name, len(image_bytes))
        return data_uri

    except Exception as e:
        logger.warning("로컬 이미지 임베딩 실패: %s - %s", path, e)
        return None


def embed_local_image_with_size(
    file_path: str | Path,
    *,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> Optional[Tuple[str, int, int]]:
    """로컬 이미지 파일을 base64 data URI + 크기로 반환.

    Args:
        file_path: 로컬 이미지 파일 경로.
        max_width: 최대 너비(px).
        max_height: 최대 높이(px).

    Returns:
        (data_uri, width, height) 튜플 또는 None.
    """
    path = Path(file_path)
    if not path.is_file():
        logger.warning("파일 없음: %s", path)
        return None

    try:
        image_bytes = path.read_bytes()
        result = _resize_image_with_size(image_bytes, max_width, max_height)
        if not result:
            return None

        resized_bytes, width, height = result
        b64 = base64.b64encode(resized_bytes).decode("ascii")
        data_uri = f"data:image/jpeg;base64,{b64}"

        logger.info(
            "로컬 이미지 임베딩: %s (%dx%d, %d bytes)",
            path.name,
            width,
            height,
            len(resized_bytes),
        )
        return data_uri, width, height

    except Exception as e:
        logger.warning("로컬 이미지 임베딩 실패: %s - %s", path, e)
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _download_image(url: str) -> Optional[bytes]:
    """이미지 다운로드."""
    try:
        with httpx.Client(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if content_type and "image" not in content_type.lower():
                logger.warning("이미지 아닌 콘텐츠: %s", content_type)
                return None

            result: bytes = response.content
            return result

    except httpx.HTTPError as e:
        logger.warning("다운로드 실패: %s... - %s", url[:60], e)
        return None


def _convert_to_rgb(img):  # noqa: ANN001
    """RGBA/P/LA 등 → RGB 변환 (JPEG 호환)."""
    from PIL import Image

    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode in ("RGBA", "LA"):
            background.paste(img, mask=img.split()[-1])
        return background
    elif img.mode != "RGB":
        return img.convert("RGB")
    return img


def _resize_image(
    image_bytes: bytes,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> Optional[bytes]:
    """이미지 리사이즈 (비율 유지, JPEG 변환)."""
    result = _resize_image_with_size(image_bytes, max_width, max_height)
    if result is None:
        return None
    return result[0]


def _resize_image_with_size(
    image_bytes: bytes,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> Optional[Tuple[bytes, int, int]]:
    """이미지 리사이즈 + 크기 반환 (비율 유지, JPEG 변환).

    Returns:
        (jpeg_bytes, width, height) 튜플 또는 None.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.debug("Pillow 미설치 — 크기 정보 없이 원본 사용")
        return None

    try:
        img: Image.Image = Image.open(BytesIO(image_bytes))
        img = _convert_to_rgb(img)

        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        width, height = img.size

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buffer.getvalue(), width, height

    except Exception as e:
        logger.warning("이미지 리사이즈 실패: %s", e)
        return None


def _guess_mime_type(suffix: str) -> str:
    """파일 확장자로 MIME 타입 추론."""
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".ico": "image/x-icon",
    }
    return mapping.get(suffix.lower(), "application/octet-stream")
