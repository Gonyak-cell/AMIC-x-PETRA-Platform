"""산업별 변형 기반 클래스 (T-N12).

> 마지막 수정: 2026-02-10 11:52:29

산업별 추가 컨텍스트, 용어 오버라이드, 강조 영역을 정의한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class IndustryConfig:
    """산업별 설정.

    Attributes:
        industry_id: 산업 식별자.
        industry_name_kr: 한국어 산업명.
        industry_name_en: 영문 산업명.
    """

    industry_id: str
    industry_name_kr: str
    industry_name_en: str


class IndustryVariant(ABC):
    """산업별 프롬프트 변형 추상 기반 클래스.

    BasePrompt의 시스템 프롬프트에 산업별 컨텍스트를 보강한다.
    """

    config: IndustryConfig

    @abstractmethod
    def get_industry_context(self) -> str:
        """산업별 추가 컨텍스트를 반환한다.

        시스템 프롬프트에 산업 특화 분석 지침으로 포함된다.
        """

    @abstractmethod
    def get_terminology_overrides(self) -> dict[str, str]:
        """산업별 용어 오버라이드를 반환한다.

        일반 금융 용어 대신 산업 특화 용어가 필요한 경우.
        {일반용어: 산업특화용어} 형태.
        """

    @abstractmethod
    def get_emphasis_areas(self) -> list[str]:
        """분석에서 강조할 영역을 반환한다."""

    def format_context(self) -> str:
        """산업 컨텍스트를 포맷팅된 문자열로 반환한다."""
        parts = [
            f"### {self.config.industry_name_kr} ({self.config.industry_name_en}) 산업 분석 가이드\n",
            self.get_industry_context(),
            "\n#### 핵심 분석 영역",
        ]
        for area in self.get_emphasis_areas():
            parts.append(f"- {area}")

        overrides = self.get_terminology_overrides()
        if overrides:
            parts.append("\n#### 산업 특화 용어")
            for general, specific in overrides.items():
                parts.append(f"- {general} → {specific}")

        return "\n".join(parts)
