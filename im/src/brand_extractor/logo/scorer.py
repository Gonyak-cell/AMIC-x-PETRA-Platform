"""로고 품질 스코어링 (T-B04).

> 마지막 수정: 2026-02-10 22:00:00

로고 후보의 해상도, 비율, 투명도, 포맷, 소스 신뢰도를 종합하여
0-1 범위의 품질 점수를 부여한다.
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import ClassVar

import httpx
from PIL import Image

from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.models import LogoCandidate

logger = logging.getLogger(__name__)


class LogoScorer:
    """로고 후보의 품질 점수를 계산한다 (0-1).

    스코어링 가중치:
        - 해상도: 0.40 (min(w,h) 기준)
        - 비율: 0.20 (정사각형에 가까울수록 높음)
        - 투명도: 0.15 (PNG alpha → 1.0)
        - 포맷: 0.10 (SVG > PNG > JPEG)
        - 소스 신뢰도: 0.15 (apple-touch-icon > og:image > css-selector > favicon)

    Examples:
        >>> scorer = LogoScorer(config)
        >>> scored = await scorer.score_candidates(candidates)
        >>> scored[0].score >= scored[1].score
        True
    """

    W_RESOLUTION: ClassVar[float] = 0.40
    W_RATIO: ClassVar[float] = 0.20
    W_TRANSPARENCY: ClassVar[float] = 0.15
    W_FORMAT: ClassVar[float] = 0.10
    W_SOURCE: ClassVar[float] = 0.15

    FORMAT_SCORES: ClassVar[dict[str, float]] = {
        "svg": 1.0,
        "png": 0.8,
        "jpeg": 0.5,
        "ico": 0.3,
    }

    SOURCE_SCORES: ClassVar[dict[str, float]] = {
        "apple-touch-icon": 1.0,
        "brandfetch": 0.95,
        "og:image": 0.7,
        "css-selector": 0.5,
        "favicon": 0.4,
    }

    def __init__(self, config: BrandExtractorConfig) -> None:
        """초기화.

        Args:
            config: Brand Extractor 설정.
        """
        self._min_size = config.min_logo_size
        self._preferred_size = config.preferred_logo_size
        self._timeout = config.timeout

    async def score_candidates(
        self,
        candidates: list[LogoCandidate],
    ) -> list[LogoCandidate]:
        """후보 리스트에 점수를 부여하고 내림차순 정렬한다.

        이미지 메타데이터가 없는 후보는 HTTP HEAD/GET으로 확인한다.

        Args:
            candidates: 스코어링할 LogoCandidate 리스트.

        Returns:
            점수가 부여된 LogoCandidate 리스트 (내림차순).
        """
        scored: list[LogoCandidate] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for candidate in candidates:
                enriched = await self._enrich_metadata(client, candidate)
                enriched.score = self._calculate_score(
                    width=enriched.width,
                    height=enriched.height,
                    has_transparency=enriched.has_transparency,
                    fmt=enriched.format,
                    source=enriched.source,
                )
                scored.append(enriched)

        scored.sort(key=lambda c: c.score, reverse=True)
        logger.info(
            "로고 스코어링 완료: %d개 후보, 최고 점수=%.2f",
            len(scored),
            scored[0].score if scored else 0.0,
        )
        return scored

    def _calculate_score(
        self,
        width: int,
        height: int,
        has_transparency: bool,
        fmt: str,
        source: str,
    ) -> float:
        """단일 후보의 품질 점수를 계산한다.

        Args:
            width: 이미지 너비 (px).
            height: 이미지 높이 (px).
            has_transparency: 투명 배경 여부.
            fmt: 이미지 포맷.
            source: 탐지 소스.

        Returns:
            0-1 범위의 품질 점수.
        """
        # 해상도 점수
        min_dim = min(width, height) if width > 0 and height > 0 else 0
        if min_dim < self._min_size:
            s_resolution = 0.0
        else:
            s_resolution = min(1.0, min_dim / self._preferred_size)

        # 비율 점수 (정사각형에 가까울수록 높음)
        if width > 0 and height > 0:
            ratio = width / height
            s_ratio = max(0.0, 1.0 - abs(1.0 - ratio) / 3.0)
        else:
            s_ratio = 0.3  # 크기 미확인

        # 투명도 점수
        s_transparency = 1.0 if has_transparency else 0.3

        # 포맷 점수
        s_format = self.FORMAT_SCORES.get(fmt, 0.4)

        # 소스 신뢰도 점수
        s_source = self.SOURCE_SCORES.get(source, 0.3)

        score = (
            self.W_RESOLUTION * s_resolution
            + self.W_RATIO * s_ratio
            + self.W_TRANSPARENCY * s_transparency
            + self.W_FORMAT * s_format
            + self.W_SOURCE * s_source
        )
        return round(min(1.0, max(0.0, score)), 4)

    async def _enrich_metadata(
        self,
        client: httpx.AsyncClient,
        candidate: LogoCandidate,
    ) -> LogoCandidate:
        """이미지 메타데이터(크기, 포맷, 투명도)를 보강한다.

        Args:
            client: httpx 클라이언트.
            candidate: 보강할 LogoCandidate.

        Returns:
            메타데이터가 보강된 LogoCandidate.
        """
        if candidate.width > 0 and candidate.height > 0:
            return candidate

        # SVG는 다운로드 불필요
        if candidate.format == "svg":
            return LogoCandidate(
                url=candidate.url,
                source=candidate.source,
                width=512,
                height=512,
                has_transparency=True,
                format="svg",
                score=candidate.score,
            )

        try:
            resp = await client.get(candidate.url)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content))
            w, h = img.size
            has_alpha = img.mode in ("RGBA", "LA", "PA")
            fmt = candidate.format or _pil_format_to_str(img.format)

            return LogoCandidate(
                url=candidate.url,
                source=candidate.source,
                width=w,
                height=h,
                has_transparency=has_alpha,
                format=fmt,
                score=candidate.score,
            )
        except Exception:
            logger.debug("로고 메타데이터 조회 실패: %s", candidate.url)
            return candidate


def _pil_format_to_str(pil_format: str | None) -> str:
    """PIL 포맷 문자열을 정규화한다.

    Args:
        pil_format: PIL Image.format (예: "PNG", "JPEG").

    Returns:
        정규화된 포맷 문자열 ("png" | "jpeg" | "svg" | "ico" | "").
    """
    if not pil_format:
        return ""
    mapping = {"PNG": "png", "JPEG": "jpeg", "SVG": "svg", "ICO": "ico", "GIF": "png"}
    return mapping.get(pil_format.upper(), pil_format.lower())
