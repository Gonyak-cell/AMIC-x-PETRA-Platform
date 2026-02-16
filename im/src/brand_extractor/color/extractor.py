"""K-Means 색상 추출기 (T-B05).

> 마지막 수정: 2026-02-10 22:00:00

이미지에서 K-Means 클러스터링을 사용하여 주요 색상을 추출한다.
scikit-learn의 KMeans와 Pillow를 활용한다.
"""

from __future__ import annotations

import colorsys
import logging
from io import BytesIO
from typing import TYPE_CHECKING

import httpx
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from src.brand_extractor.exceptions import ColorExtractionError
from src.brand_extractor.models import ExtractedColor

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# 흰색/검정 필터링 임계값
_WHITE_THRESHOLD = 240
_BLACK_THRESHOLD = 15
# K-Means 성능을 위한 최대 리사이즈 크기
_MAX_RESIZE = 200
# 유효 픽셀 최소 수
_MIN_PIXELS = 10


class ColorExtractor:
    """K-Means 클러스터링으로 이미지에서 주요 색상을 추출한다.

    Examples:
        >>> extractor = ColorExtractor(n_colors=5)
        >>> img = Image.new("RGB", (100, 100), (255, 0, 0))
        >>> colors = extractor.extract_from_image(img)
        >>> colors[0].hex
        '#FF0000'
    """

    def __init__(self, n_colors: int = 5) -> None:
        """초기화.

        Args:
            n_colors: 추출할 색상 수 (K-Means 클러스터 수).
        """
        self._n_colors = n_colors

    def extract_from_image(self, image: Image.Image) -> list[ExtractedColor]:
        """PIL Image에서 주요 색상을 추출한다.

        Args:
            image: PIL Image 객체.

        Returns:
            ExtractedColor 리스트 (ratio 내림차순 정렬).

        Raises:
            ColorExtractionError: 유효 픽셀 부족 등 추출 실패 시.
        """
        pixels = self._prepare_pixels(image)

        if len(pixels) < _MIN_PIXELS:
            raise ColorExtractionError(
                reason=f"유효 픽셀 부족: {len(pixels)}개 (최소 {_MIN_PIXELS}개 필요)"
            )

        # 클러스터 수 조정 (유효 픽셀 < n_colors일 수 있음)
        n_clusters = min(self._n_colors, len(pixels))

        try:
            kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
            labels = kmeans.fit_predict(pixels)
        except Exception as e:
            raise ColorExtractionError(reason=f"K-Means 클러스터링 실패: {e}") from e

        # 클러스터별 색상 및 비율 계산
        total = len(labels)
        colors: list[ExtractedColor] = []

        for i in range(n_clusters):
            center = kmeans.cluster_centers_[i]
            r, g, b = int(round(center[0])), int(round(center[1])), int(round(center[2]))
            count = int(np.sum(labels == i))
            ratio = count / total

            hex_color = f"#{r:02X}{g:02X}{b:02X}"
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            hsv = (round(h * 360, 1), round(s, 4), round(v, 4))

            colors.append(
                ExtractedColor(
                    hex=hex_color,
                    rgb=(r, g, b),
                    hsv=hsv,
                    ratio=round(ratio, 4),
                )
            )

        # ratio 내림차순 정렬
        colors.sort(key=lambda c: c.ratio, reverse=True)

        logger.info("K-Means 색상 %d개 추출 완료", len(colors))
        return colors

    def extract_from_bytes(self, data: bytes) -> list[ExtractedColor]:
        """바이트 데이터에서 색상을 추출한다.

        Args:
            data: 이미지 바이트 데이터.

        Returns:
            ExtractedColor 리스트.

        Raises:
            ColorExtractionError: 이미지 디코딩 실패 시.
        """
        try:
            image = Image.open(BytesIO(data))
        except Exception as e:
            raise ColorExtractionError(reason=f"이미지 디코딩 실패: {e}") from e
        return self.extract_from_image(image)

    async def extract_from_url(
        self,
        url: str,
        *,
        timeout: int = 30,
    ) -> list[ExtractedColor]:
        """URL에서 이미지를 다운로드하여 색상을 추출한다.

        Args:
            url: 이미지 URL.
            timeout: HTTP 요청 타임아웃 (초).

        Returns:
            ExtractedColor 리스트.

        Raises:
            ColorExtractionError: 다운로드 또는 추출 실패 시.
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except Exception as e:
            raise ColorExtractionError(
                reason=f"이미지 다운로드 실패: url='{url}' — {e}"
            ) from e
        return self.extract_from_bytes(resp.content)

    def _prepare_pixels(self, image: Image.Image) -> NDArray[np.uint8]:
        """이미지를 K-Means 입력용 픽셀 배열로 변환한다.

        처리 단계:
        1. 애니메이션 → 첫 프레임
        2. RGBA → alpha < 128 픽셀 제거 후 RGB
        3. 리사이즈 (max 200x200)
        4. 흰색/검정 필터링

        Args:
            image: PIL Image 객체.

        Returns:
            (N, 3) 형태의 uint8 numpy 배열.
        """
        # 애니메이션 첫 프레임
        if hasattr(image, "n_frames") and image.n_frames > 1:
            image.seek(0)

        # RGBA 처리 — alpha가 낮은 픽셀 제거
        if image.mode == "RGBA":
            arr = np.array(image)
            mask = arr[:, :, 3] >= 128
            rgb_arr = arr[:, :, :3]
            pixels = rgb_arr[mask]
        else:
            img_rgb = image.convert("RGB")
            # 리사이즈 (성능)
            if max(img_rgb.size) > _MAX_RESIZE:
                img_rgb.thumbnail((_MAX_RESIZE, _MAX_RESIZE), Image.Resampling.LANCZOS)
            pixels = np.array(img_rgb).reshape(-1, 3)

        # RGBA 모드에서 리사이즈를 아직 안 했으면 샘플링
        if len(pixels) > _MAX_RESIZE * _MAX_RESIZE:
            rng = np.random.default_rng(42)
            indices = rng.choice(len(pixels), size=_MAX_RESIZE * _MAX_RESIZE, replace=False)
            pixels = pixels[indices]

        # 흰색/검정 필터링
        is_white = np.all(pixels > _WHITE_THRESHOLD, axis=1)
        is_black = np.all(pixels < _BLACK_THRESHOLD, axis=1)
        mask = ~(is_white | is_black)
        pixels = pixels[mask]

        return pixels
