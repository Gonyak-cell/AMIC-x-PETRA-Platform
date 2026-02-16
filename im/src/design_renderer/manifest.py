"""생성 매니페스트 — 슬라이드별 렌더링 결과 추적.

> 마지막 수정: 2026-02-11 10:30:00

PPTX/PDF 생성 과정의 슬라이드별 성공/실패/시간을 기록하는
매니페스트 데이터 모델. 디버깅 및 품질 추적에 활용한다.

Usage::

    manifest = GenerationManifest()
    manifest.add_entry("cover", title="Cover", success=True, render_time_ms=12.5)
    manifest.add_entry("financial_analysis", title="재무 분석", success=False,
                       error="데이터 없음", render_time_ms=0.0)
    print(manifest.summary())
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SlideManifestEntry:
    """개별 슬라이드/섹션 렌더링 결과 항목."""

    slide_index: int
    section_id: str
    title: str
    success: bool
    error: str | None = None
    render_time_ms: float = 0.0
    slide_count: int = 0


@dataclass
class GenerationManifest:
    """PPTX/PDF 생성 매니페스트.

    생성 과정의 모든 섹션별 결과를 기록한다.
    """

    entries: list[SlideManifestEntry] = field(default_factory=list)
    generation_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_elapsed_ms: float = 0.0

    def add_entry(
        self,
        section_id: str,
        *,
        title: str = "",
        success: bool = True,
        error: str | None = None,
        render_time_ms: float = 0.0,
        slide_count: int = 0,
    ) -> SlideManifestEntry:
        """렌더링 결과 항목을 추가한다.

        Args:
            section_id: 섹션 ID.
            title: 섹션 제목.
            success: 성공 여부.
            error: 실패 시 에러 메시지.
            render_time_ms: 렌더링 소요 시간 (밀리초).
            slide_count: 생성된 슬라이드 수.

        Returns:
            추가된 항목.
        """
        entry = SlideManifestEntry(
            slide_index=len(self.entries),
            section_id=section_id,
            title=title or section_id,
            success=success,
            error=error,
            render_time_ms=render_time_ms,
            slide_count=slide_count,
        )
        self.entries.append(entry)
        return entry

    @property
    def total_slides(self) -> int:
        """총 생성된 슬라이드 수."""
        return sum(e.slide_count for e in self.entries)

    @property
    def failed_sections(self) -> list[str]:
        """실패한 섹션 ID 목록."""
        return [e.section_id for e in self.entries if not e.success]

    @property
    def successful_sections(self) -> list[str]:
        """성공한 섹션 ID 목록."""
        return [e.section_id for e in self.entries if e.success]

    @property
    def success_rate(self) -> float:
        """성공률 (0.0~1.0). 항목이 없으면 1.0."""
        if not self.entries:
            return 1.0
        return len(self.successful_sections) / len(self.entries)

    def summary(self) -> str:
        """매니페스트 요약 문자열."""
        total = len(self.entries)
        ok = len(self.successful_sections)
        fail = len(self.failed_sections)
        slides = self.total_slides
        elapsed = self.total_elapsed_ms

        lines = [
            f"=== 생성 매니페스트 ===",
            f"시각: {self.generation_timestamp}",
            f"섹션: {ok}/{total} 성공 ({fail}개 실패)",
            f"슬라이드: {slides}장",
            f"소요시간: {elapsed:.0f}ms",
        ]

        if self.failed_sections:
            lines.append(f"실패 섹션: {', '.join(self.failed_sections)}")
            for entry in self.entries:
                if not entry.success:
                    lines.append(f"  - [{entry.section_id}] {entry.error}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """직렬화 가능한 dict로 변환."""
        return {
            "generation_timestamp": self.generation_timestamp,
            "total_elapsed_ms": self.total_elapsed_ms,
            "total_slides": self.total_slides,
            "success_rate": self.success_rate,
            "entries": [
                {
                    "slide_index": e.slide_index,
                    "section_id": e.section_id,
                    "title": e.title,
                    "success": e.success,
                    "error": e.error,
                    "render_time_ms": e.render_time_ms,
                    "slide_count": e.slide_count,
                }
                for e in self.entries
            ],
        }
