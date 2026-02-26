"""Template Engine 스키마 — Ralph Loop이 생성하는 콘텐츠의 구조화된 형식.

TemplateContent는 LLM이 생성한 콘텐츠를 마스터 PPTX 템플릿에
삽입하기 위한 중간 표현(intermediate representation)이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SeriesData:
    """차트 데이터 시리즈."""

    name: str
    values: list[float | int]


@dataclass
class ChartContent:
    """네이티브 PPTX 차트에 삽입할 데이터.

    chart.replace_data()로 기존 차트의 데이터만 교체하며,
    색상/축/레이블 서식은 템플릿에서 자동 보존된다.
    """

    categories: list[str]
    series: list[SeriesData]


@dataclass
class TableContent:
    """테이블에 삽입할 데이터.

    headers가 None이면 기존 헤더를 유지하고 데이터 행만 교체한다.
    """

    rows: list[list[str]]
    headers: list[str] | None = None


@dataclass
class SlideContent:
    """단일 슬라이드에 삽입할 콘텐츠.

    각 dict의 키는 shape_name(PPTX 내부 이름)이다.
    """

    slide_idx: int
    title: str | None = None
    texts: dict[str, str] = field(default_factory=dict)
    charts: dict[str, ChartContent] = field(default_factory=dict)
    tables: dict[str, TableContent] = field(default_factory=dict)


@dataclass
class TemplateContent:
    """마스터 템플릿에 삽입할 전체 콘텐츠.

    Ralph Loop Pass 1이 LLM을 통해 생성하는 최종 출력물이다.
    TemplatePopulator가 이 데이터를 마스터 PPTX에 삽입한다.
    """

    project_name: str
    date: str
    memo_type: str  # "TM" | "DM"
    slides: list[SlideContent] = field(default_factory=list)
    excluded_slides: list[int] = field(default_factory=list)
