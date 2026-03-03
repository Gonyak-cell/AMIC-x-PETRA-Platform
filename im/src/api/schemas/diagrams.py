"""Diagram 관련 스키마.

Excalidraw 다이어그램 생성/수정/응답 Pydantic v2 스키마를 정의한다.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


_VALID_DIAGRAM_TYPES = {
    "shareholding",
    "org_chart",
    "deal_structure",
    "value_chain",
    "custom",
}

# Excalidraw JSON 최대 크기 (5 MB)
_MAX_EXCALIDRAW_DATA_BYTES = 5 * 1024 * 1024


def _validate_excalidraw_data_size(v: dict[str, Any]) -> dict[str, Any]:
    """excalidraw_data의 직렬화 크기가 5MB를 초과하지 않는지 검증한다."""
    size = len(json.dumps(v, ensure_ascii=False).encode("utf-8"))
    if size > _MAX_EXCALIDRAW_DATA_BYTES:
        limit_mb = _MAX_EXCALIDRAW_DATA_BYTES // (1024 * 1024)
        raise ValueError(
            f"excalidraw_data 크기가 {limit_mb}MB를 초과합니다 "
            f"({size / (1024 * 1024):.1f}MB)"
        )
    return v


class DiagramCreate(BaseModel):
    """다이어그램 생성 요청."""

    diagram_type: str = Field(
        description="다이어그램 유형",
    )
    title: str = Field(
        min_length=1,
        max_length=200,
        description="다이어그램 제목",
    )
    excalidraw_data: dict[str, Any] = Field(
        description="Excalidraw JSON 데이터",
    )

    @field_validator("diagram_type")
    @classmethod
    def validate_diagram_type(cls, v: str) -> str:
        """diagram_type이 유효한 값인지 검증한다."""
        if v not in _VALID_DIAGRAM_TYPES:
            raise ValueError(
                f"diagram_type은 {_VALID_DIAGRAM_TYPES} 중 하나여야 합니다"
            )
        return v

    @field_validator("excalidraw_data")
    @classmethod
    def validate_excalidraw_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """excalidraw_data 크기를 검증한다."""
        return _validate_excalidraw_data_size(v)


class DiagramUpdate(BaseModel):
    """다이어그램 수정 요청."""

    excalidraw_data: dict[str, Any] = Field(
        description="수정된 Excalidraw JSON 데이터",
    )

    @field_validator("excalidraw_data")
    @classmethod
    def validate_excalidraw_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """excalidraw_data 크기를 검증한다."""
        return _validate_excalidraw_data_size(v)


class DiagramResponse(BaseModel):
    """다이어그램 응답 (상세 조회 — excalidraw_data 포함)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    diagram_type: str
    title: str
    excalidraw_data: dict[str, Any] | None
    png_path: str | None
    created_at: datetime
    updated_at: datetime


class DiagramListResponse(BaseModel):
    """다이어그램 목록 응답 (excalidraw_data 생략)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    diagram_type: str
    title: str
    png_path: str | None
    created_at: datetime
    updated_at: datetime


class PngExportResponse(BaseModel):
    """PNG 내보내기 응답."""

    png_path: str
