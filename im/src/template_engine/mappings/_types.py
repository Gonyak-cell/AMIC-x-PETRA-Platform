"""매핑 데이터 타입 정의.

SlideMapping과 SlotMapping은 모든 매핑 파일에서 공유하는 기본 타입이다.
개별 매핑 파일(nx3_dm.py, ytn_dm.py 등)에서 import하여 사용한다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlotMapping:
    """shape→data_key 매핑."""

    shape_name: str
    data_key: str
    slot_type: str  # "text", "chart", "table"


@dataclass(frozen=True)
class SlideMapping:
    """슬라이드별 매핑."""

    slide_idx: int
    description: str
    slots: list[SlotMapping]
