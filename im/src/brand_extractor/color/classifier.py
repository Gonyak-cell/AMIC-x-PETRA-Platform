"""색상 분류기 (T-B06).

> 마지막 수정: 2026-02-10 22:00:00

K-Means로 추출된 색상을 Primary / Secondary / Accent으로 분류한다.
HSV 색 공간의 채도(S)와 명도(V)를 기반으로 판별한다.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from src.brand_extractor.models import ExtractedColor

logger = logging.getLogger(__name__)

# 무채색 판별 임계값 (채도)
_ACHROMATIC_SATURATION = 0.08
# 색상환 최소 거리 (°) — primary-secondary 구별
_MIN_HUE_DISTANCE = 30.0


class ColorClassifier:
    """추출된 색상을 Primary/Secondary/Accent으로 분류한다.

    분류 알고리즘:
    1. 무채색(S < 0.08) 제거
    2. 유채색을 "채도 x 비율" 내림차순 정렬
    3. 1순위 → primary
    4. 2순위 → secondary (primary와 색상환 거리 > 30° 일 때)
    5. 3순위 → accent
    6. 유채색 없으면 비율 최대 무채색을 primary로 사용

    Examples:
        >>> classifier = ColorClassifier()
        >>> classified = classifier.classify(colors)
        >>> primary = [c for c in classified if c.role == "primary"]
        >>> len(primary) == 1
        True
    """

    ACHROMATIC_THRESHOLD: ClassVar[float] = _ACHROMATIC_SATURATION
    MIN_HUE_DISTANCE: ClassVar[float] = _MIN_HUE_DISTANCE

    def classify(self, colors: list[ExtractedColor]) -> list[ExtractedColor]:
        """색상 리스트에 role을 부여한다.

        Args:
            colors: ExtractedColor 리스트 (role 미설정 상태).

        Returns:
            role이 설정된 ExtractedColor 리스트 (원본 순서 유지).
        """
        if not colors:
            return []

        # 무채색/유채색 분리
        chromatic: list[ExtractedColor] = []
        achromatic: list[ExtractedColor] = []
        for c in colors:
            if self._is_achromatic(c):
                achromatic.append(c)
            else:
                chromatic.append(c)

        # 유채색을 "채도 × 비율" 내림차순 정렬
        chromatic.sort(key=lambda c: c.hsv[1] * c.ratio, reverse=True)

        roles: dict[str, str] = {}  # hex → role

        if chromatic:
            # Primary: 가장 눈에 띄는 유채색
            primary = chromatic[0]
            roles[primary.hex] = "primary"

            # Secondary & Accent: primary와 색상환 거리 기반
            for c in chromatic[1:]:
                if "secondary" not in roles.values():
                    dist = self._hue_distance(primary.hsv[0], c.hsv[0])
                    if dist >= self.MIN_HUE_DISTANCE:
                        roles[c.hex] = "secondary"
                        continue
                    # 거리 부족 → secondary 후보 아님, 다음으로
                if "accent" not in roles.values():
                    roles[c.hex] = "accent"
                # 둘 다 할당되면 종료
                if "secondary" in roles.values() and "accent" in roles.values():
                    break
        else:
            # 모든 색상이 무채색 → 비율 최대를 primary로
            if achromatic:
                best = max(achromatic, key=lambda c: c.ratio)
                roles[best.hex] = "primary"

        # role 할당한 새 리스트 반환
        result: list[ExtractedColor] = []
        for c in colors:
            role = roles.get(c.hex, "")
            result.append(
                ExtractedColor(
                    hex=c.hex,
                    rgb=c.rgb,
                    hsv=c.hsv,
                    ratio=c.ratio,
                    role=role,
                )
            )

        assigned = [r for r in roles.values() if r]
        logger.info("색상 분류 완료: %s", ", ".join(assigned) or "없음")
        return result

    @staticmethod
    def _hue_distance(h1: float, h2: float) -> float:
        """색상환에서 두 색상 간 거리를 계산한다 (0-180°).

        Args:
            h1: 첫 번째 색상의 Hue (0-360).
            h2: 두 번째 색상의 Hue (0-360).

        Returns:
            0-180 범위의 각도 거리.
        """
        diff = abs(h1 - h2)
        return min(diff, 360.0 - diff)

    @staticmethod
    def _is_achromatic(color: ExtractedColor) -> bool:
        """무채색 여부를 판별한다.

        Args:
            color: 판별할 색상.

        Returns:
            채도(S)가 임계값 미만이면 True.
        """
        return color.hsv[1] < _ACHROMATIC_SATURATION
