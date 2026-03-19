"""PPTX 템플릿 계약 — 슬롯 레벨 핏 보장.

> 마지막 수정: 2026-03-13 21:16:29

템플릿과 렌더러 사이의 형식적 계약을 정의한다.
렌더러는 TemplateSpec만 보고 배치하며, 암묵적 shape name,
수동 좌표 계산, 암묵적 폰트 축소를 금지한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SlotContentType(StrEnum):
    """슬롯 콘텐츠 유형."""

    TEXT = "TEXT"
    TABLE = "TABLE"
    CHART = "CHART"
    IMAGE = "IMAGE"


class OverflowPolicy(StrEnum):
    """콘텐츠 오버플로우 정책."""

    FAIL = "FAIL"  # 품질 게이트 FAIL 처리
    TRUNCATE = "TRUNCATE"  # 초과분 잘라냄 (비권장)


class ShrinkPolicy(StrEnum):
    """폰트 축소 정책."""

    FAIL = "FAIL"  # 축소 불가 — 품질 게이트 FAIL
    TRUNCATE = "TRUNCATE"  # 텍스트 잘라냄


@dataclass(frozen=True)
class SlotSpec:
    """개별 슬롯(shape) 계약."""

    name: str
    content_type: SlotContentType
    bbox: tuple[float, float, float, float]  # left, top, width, height (inches)
    max_lines: int | None = None
    max_chars: int | None = None
    min_font_pt: float | None = None
    shrink_policy: ShrinkPolicy = ShrinkPolicy.FAIL
    overflow_policy: OverflowPolicy = OverflowPolicy.FAIL
    alignment: str = "LEFT"
    aspect_ratio_policy: str | None = None  # IMAGE 슬롯 전용


@dataclass(frozen=True)
class SlideSpec:
    """슬라이드 단위 계약."""

    purpose: str  # "cover", "disclaimer", "financial_analysis" 등
    layout_name: str  # 마스터 레이아웃 이름
    required_shapes: tuple[str, ...] = ()
    optional_shapes: tuple[str, ...] = ()
    slots: tuple[SlotSpec, ...] = ()


@dataclass(frozen=True)
class TemplateSpec:
    """템플릿 전체 계약."""

    template_id: str
    doc_type: str  # "TM", "DM", "IM"
    variant: str  # "default", "andersen", etc.
    template_path: str  # 모듈 루트 기준 상대 경로
    brand_tokens: dict[str, str] = field(default_factory=dict)
    slides: tuple[SlideSpec, ...] = ()

    @property
    def slide_purposes(self) -> list[str]:
        """슬라이드 목적 목록."""
        return [s.purpose for s in self.slides]


def get_spec(doc_type: str, variant: str = "default") -> TemplateSpec | None:
    """등록된 TemplateSpec을 반환한다. 없으면 None."""
    return _SPEC_REGISTRY.get((doc_type.upper(), variant))


def register_spec(spec: TemplateSpec) -> None:
    """TemplateSpec을 레지스트리에 등록한다."""
    _SPEC_REGISTRY[(spec.doc_type.upper(), spec.variant)] = spec


_SPEC_REGISTRY: dict[tuple[str, str], TemplateSpec] = {}
