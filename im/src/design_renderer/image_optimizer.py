"""차트/이미지 PNG 최적화 모듈.

> 마지막 수정: 2026-02-11 22:00:00

PPTX에 삽입되는 PNG 이미지의 파일 크기를 줄여
최종 문서 크기를 최적화한다. Pillow 기반 PNG 양자화 + 메타데이터 제거.
"""

from __future__ import annotations

import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

DEFAULT_PNG_COLORS: int = 256
"""양자화 색상 수 (최대 256)."""

DEFAULT_COMPRESS_LEVEL: int = 9
"""zlib 압축 레벨 (0-9, 9 = 최대 압축)."""

DEFAULT_MAX_WIDTH: int = 2700
"""PPTX 후처리 시 이미지 최대 너비(px). 900px × scale 3."""

MIN_SIZE_FOR_OPTIMIZATION: int = 10_000
"""10KB 미만이면 최적화 생략."""


# ---------------------------------------------------------------------------
# 예외
# ---------------------------------------------------------------------------


class ImageOptimizationError(Exception):
    """이미지 최적화 실패 예외."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# PNG 압축
# ---------------------------------------------------------------------------


def compress_png(
    png_bytes: bytes,
    *,
    max_colors: int = DEFAULT_PNG_COLORS,
    compress_level: int = DEFAULT_COMPRESS_LEVEL,
    max_width: int | None = None,
    strip_metadata: bool = True,
) -> bytes:
    """PNG 바이트를 최적화하여 파일 크기를 줄인다.

    최적화 단계:
    1. max_width 초과 시 비율 유지 리사이즈 (LANCZOS)
    2. RGBA/RGB → P (팔레트) 양자화로 색상 수 감소
    3. compress_level=9로 최대 zlib 압축
    4. 불필요한 메타데이터(tEXt, iTXt 등) 제거

    Args:
        png_bytes: 원본 PNG 바이트.
        max_colors: 양자화 색상 수 (2-256). 0이면 양자화 생략.
        compress_level: PNG 압축 레벨 (0-9).
        max_width: 최대 너비(px). None이면 리사이즈 안 함.
        strip_metadata: True면 메타데이터 제거.

    Returns:
        최적화된 PNG 바이트. 실패 시 원본 반환.
    """
    if len(png_bytes) < MIN_SIZE_FOR_OPTIMIZATION:
        return png_bytes

    try:
        from PIL import Image, PngImagePlugin
    except ImportError:
        logger.debug("Pillow 미설치 — 원본 PNG 반환")
        return png_bytes

    try:
        img = Image.open(BytesIO(png_bytes))

        # 1. 리사이즈 (선택)
        if max_width and img.width > max_width:
            ratio = max_width / img.width
            new_h = int(img.height * ratio)
            img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

        # 2. 양자화 (선택)
        if max_colors > 0 and img.mode in ("RGBA", "RGB"):
            if img.mode == "RGBA":
                img = img.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
            else:
                img = img.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)

        # 3. PNG으로 재저장 (최대 압축)
        buf = BytesIO()
        save_kwargs: dict[str, Any] = {
            "format": "PNG",
            "optimize": True,
            "compress_level": compress_level,
        }
        if strip_metadata:
            save_kwargs["pnginfo"] = PngImagePlugin.PngInfo()

        img.save(buf, **save_kwargs)
        optimized = buf.getvalue()

        # 최적화가 오히려 크기를 키운 경우 원본 반환
        if len(optimized) >= len(png_bytes):
            logger.debug(
                "최적화 후 크기 증가 (%d -> %d) — 원본 유지",
                len(png_bytes),
                len(optimized),
            )
            return png_bytes

        reduction_pct = (1 - len(optimized) / len(png_bytes)) * 100
        logger.info(
            "PNG 최적화: %d -> %d bytes (%.1f%% 감소)",
            len(png_bytes),
            len(optimized),
            reduction_pct,
        )
        return optimized

    except Exception as e:
        logger.warning("PNG 최적화 실패 — 원본 반환: %s", e)
        return png_bytes


# ---------------------------------------------------------------------------
# PPTX 이미지 후처리
# ---------------------------------------------------------------------------


def optimize_pptx_images(
    pptx_path: str | Path,
    *,
    max_colors: int = DEFAULT_PNG_COLORS,
    compress_level: int = DEFAULT_COMPRESS_LEVEL,
    max_width: int | None = DEFAULT_MAX_WIDTH,
    in_place: bool = True,
) -> Path:
    """저장된 PPTX 파일 내 모든 PNG 이미지를 후처리 최적화한다.

    PPTX(ZIP) 내부의 ppt/media/*.png 파트를 개별 재압축한다.

    Args:
        pptx_path: PPTX 파일 경로.
        max_colors: PNG 양자화 색상 수.
        compress_level: PNG 압축 레벨.
        max_width: 이미지 최대 너비(px). None이면 리사이즈 안 함.
        in_place: True면 원본 파일 덮어쓰기. False면 *_optimized.pptx 생성.

    Returns:
        최적화된 PPTX 파일 경로.

    Raises:
        ImageOptimizationError: 파일 없음 또는 최적화 실패 시.
    """
    src = Path(pptx_path)
    if not src.exists():
        raise ImageOptimizationError(
            f"PPTX 파일 없음: {src}",
            details={"path": str(src)},
        )

    if in_place:
        dst = src.with_suffix(".tmp.pptx")
    else:
        dst = src.with_name(src.stem + "_optimized.pptx")

    total_saved = 0
    image_count = 0

    try:
        with zipfile.ZipFile(src, "r") as zin:
            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)

                    # ppt/media/ 경로의 PNG 이미지만 최적화
                    if (
                        item.filename.startswith("ppt/media/")
                        and item.filename.lower().endswith(".png")
                    ):
                        original_size = len(data)
                        data = compress_png(
                            data,
                            max_colors=max_colors,
                            compress_level=compress_level,
                            max_width=max_width,
                        )
                        total_saved += original_size - len(data)
                        image_count += 1

                    zout.writestr(item, data)

        if in_place:
            dst.replace(src)
            result_path = src
        else:
            result_path = dst

        logger.info(
            "PPTX 이미지 최적화: %d개 이미지, %.1fKB 절감",
            image_count,
            total_saved / 1024,
        )
        return result_path

    except ImageOptimizationError:
        raise
    except Exception as e:
        # 실패 시 tmp 파일 정리
        if dst.exists() and in_place:
            dst.unlink(missing_ok=True)
        raise ImageOptimizationError(
            f"PPTX 이미지 최적화 실패: {e}",
            details={"path": str(src)},
        ) from e
