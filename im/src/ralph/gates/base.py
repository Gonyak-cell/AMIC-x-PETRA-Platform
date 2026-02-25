"""품질 게이트 추상 클래스 및 공통 데이터 모델."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class GateVerdict(StrEnum):
    PASS = "PASS"                 # 4.0/5.0 이상
    CONDITIONAL_PASS = "COND"     # 3.0-3.9 — 경미한 수정 후 재평가
    FAIL = "FAIL"                 # 3.0 미만 — 대폭 재작업


@dataclass(frozen=True)
class DimensionScore:
    """평가 차원별 점수."""

    name: str                     # 차원명 (예: "completeness")
    label: str                    # 한글 레이블 (예: "완전성")
    score: float                  # 0.0 ~ 5.0
    weight: float                 # 가중치 (합계 1.0)
    feedback: str = ""            # 구체적 개선 지시


@dataclass
class GateResult:
    """품질 게이트 평가 결과."""

    gate_name: str
    verdict: GateVerdict
    weighted_score: float         # 가중 합산 점수 (0.0 ~ 5.0)
    dimensions: list[DimensionScore] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)        # 발견된 구체적 문제
    suggestions: list[str] = field(default_factory=list)   # 개선 지시 (위치 특정)
    critical_flags: list[str] = field(default_factory=list) # CRITICAL Red Flag
    cost_usd: float = 0.0
    duration_ms: int = 0
    raw_data: dict[str, Any] = field(default_factory=dict) # 디버깅용 원시 데이터

    @property
    def passed(self) -> bool:
        return self.verdict == GateVerdict.PASS and not self.critical_flags


class QualityGate(ABC):
    """품질 게이트 인터페이스.

    모든 게이트는 이 인터페이스를 구현한다.
    Gate 1(프로그래밍)은 LLM 호출 없이 밀리초 단위로 동작하고,
    Gate 2(Vision)는 GPT-4o Vision API로 시각 품질을 평가하며,
    Gate 3(LLM Judge)는 다차원 디자인 평가를 수행한다.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """게이트 고유 이름."""
        ...

    @abstractmethod
    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        """문서 산출물을 평가한다.

        Args:
            artifact_path: 생성된 PPTX 파일 경로.
            prd_section: PRD의 해당 섹션 수용 기준.
            source_data: 원본 데이터 (교차 검증용).

        Returns:
            GateResult: 평가 결과 (점수, 피드백, Red Flag).
        """
        ...

    def _compute_weighted_score(self, dimensions: list[DimensionScore]) -> float:
        """차원별 가중 합산 점수를 계산한다."""
        if not dimensions:
            return 0.0
        return sum(d.score * d.weight for d in dimensions)

    def _determine_verdict(
        self,
        score: float,
        critical_flags: list[str],
        pass_threshold: float = 4.0,
    ) -> GateVerdict:
        """점수와 Red Flag에 따라 판정을 결정한다."""
        if critical_flags:
            return GateVerdict.FAIL
        if score >= pass_threshold:
            return GateVerdict.PASS
        if score >= 3.0:
            return GateVerdict.CONDITIONAL_PASS
        return GateVerdict.FAIL

    def _timed_result(
        self,
        start_ns: int,
        dimensions: list[DimensionScore],
        issues: list[str],
        suggestions: list[str],
        critical_flags: list[str],
        cost_usd: float = 0.0,
        raw_data: dict | None = None,
    ) -> GateResult:
        """공통 결과 빌더 — 시간 측정 포함."""
        score = self._compute_weighted_score(dimensions)
        verdict = self._determine_verdict(score, critical_flags)
        elapsed_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

        return GateResult(
            gate_name=self.name,
            verdict=verdict,
            weighted_score=round(score, 3),
            dimensions=dimensions,
            issues=issues,
            suggestions=suggestions,
            critical_flags=critical_flags,
            cost_usd=cost_usd,
            duration_ms=elapsed_ms,
            raw_data=raw_data or {},
        )
