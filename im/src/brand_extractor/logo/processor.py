"""로고 이미지 프로세서 (T-B04 보조).

> 마지막 수정: 2026-02-10 22:00:00

로고 이미지를 다운로드하고, 리사이즈/포맷 변환 후 로컬에 저장한다.
"""

from __future__ import annotations

import logging
import tempfile
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.exceptions import LogoDetectionError

logger = logging.getLogger(__name__)

# 최종 저장 크기
_TARGET_SIZE = 512


class LogoProcessor:
    """로고 이미지를 다운로드/리사이즈/저장한다.

    Examples:
        >>> processor = LogoProcessor(config)
        >>> path = await processor.download_and_save("https://example.com/logo.png", "company")
        >>> Path(path).exists()
        True
    """

    def __init__(self, config: BrandExtractorConfig) -> None:
        """초기화.

        Args:
            config: Brand Extractor 설정.
        """
        self._timeout = config.timeout
        if config.logo_output_dir:
            self._output_dir = Path(config.logo_output_dir)
            self._output_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._output_dir = Path(tempfile.mkdtemp(prefix="brand_logos_"))

    @property
    def output_dir(self) -> Path:
        """로고 저장 디렉토리."""
        return self._output_dir

    async def download_and_save(
        self,
        url: str,
        prefix: str = "logo",
        *,
        variant: str = "dark",
    ) -> str:
        """로고를 다운로드하여 리사이즈 후 PNG로 저장한다.

        Args:
            url: 로고 이미지 URL.
            prefix: 파일명 접두사.
            variant: 변형 ("dark" | "white").

        Returns:
            저장된 파일의 절대 경로 문자열.

        Raises:
            LogoDetectionError: 다운로드 또는 처리 실패 시.
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                image_data = resp.content
        except Exception as e:
            raise LogoDetectionError(
                url=url,
                reason=f"다운로드 실패: {e}",
            ) from e

        return self.save_from_bytes(image_data, prefix=prefix, variant=variant)

    def save_from_bytes(
        self,
        data: bytes,
        prefix: str = "logo",
        *,
        variant: str = "dark",
    ) -> str:
        """바이트 데이터를 리사이즈 후 PNG로 저장한다.

        Args:
            data: 이미지 바이트 데이터.
            prefix: 파일명 접두사.
            variant: 변형 ("dark" | "white").

        Returns:
            저장된 파일의 절대 경로 문자열.

        Raises:
            LogoDetectionError: 이미지 처리 실패 시.
        """
        try:
            img = Image.open(BytesIO(data))
        except Exception as e:
            raise LogoDetectionError(reason=f"이미지 디코딩 실패: {e}") from e

        # 리사이즈 (비율 유지)
        img.thumbnail((_TARGET_SIZE, _TARGET_SIZE), Image.Resampling.LANCZOS)

        # RGBA 유지 (투명 배경), 그 외 RGB 변환
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA") if "A" in (img.mode or "") else img.convert("RGB")

        filename = f"{prefix}_{variant}.png"
        path = self._output_dir / filename
        img.save(str(path), format="PNG", optimize=True)

        logger.info("로고 저장: %s (%dx%d)", path, img.width, img.height)
        return str(path)
