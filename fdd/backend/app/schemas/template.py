"""Template Contract Schemas - 템플릿 주입 스키마.

EPIC-10: PPT/Word 템플릿 주입 기능을 위한 스키마 정의.
고객 템플릿에 FDD 콘텐츠를 주입하기 위한 슬롯 정의 및 계약.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SlotType(StrEnum):
    """템플릿 슬롯 타입."""

    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    IMAGE = "image"


class SlotStatus(StrEnum):
    """슬롯 상태."""

    EMPTY = "empty"
    MAPPED = "mapped"
    FILLED = "filled"
    ERROR = "error"


class TemplateStatus(StrEnum):
    """템플릿 상태."""

    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    ARCHIVED = "archived"


# ── Slot Definitions ──────────────────────────────────────


class SlotConstraints(BaseModel):
    """슬롯 제약 조건."""

    max_rows: int | None = Field(default=None, ge=1, description="테이블 최대 행 수")
    max_chars: int | None = Field(default=None, ge=1, description="텍스트 최대 문자 수")
    max_width: float | None = Field(default=None, gt=0, description="최대 너비(인치)")
    max_height: float | None = Field(default=None, gt=0, description="최대 높이(인치)")
    allowed_formats: list[str] | None = Field(
        default=None, description="허용되는 포맷 (png, jpg 등)"
    )


class TemplateSlot(BaseModel):
    """템플릿 슬롯 정의.

    템플릿 내 콘텐츠가 주입될 위치를 정의합니다.

    슬롯 ID 패턴:
    - {{SLOT:NAME}} : 기본 슬롯
    - {{TABLE:NAME}} : 테이블 슬롯
    - {{CHART:NAME}} : 차트 슬롯
    - {{TEXT:NAME}} : 텍스트 슬롯
    """

    slot_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="슬롯 ID (예: {{SLOT:QOE_BRIDGE}})",
        pattern=r"^\{\{(SLOT|TABLE|CHART|TEXT|IMAGE):[\w_]+\}\}$",
    )
    slot_type: SlotType = Field(..., description="슬롯 타입")
    required: bool = Field(default=True, description="필수 슬롯 여부")
    description: str | None = Field(default=None, max_length=500, description="슬롯 설명")
    constraints: SlotConstraints | None = Field(default=None, description="슬롯 제약 조건")
    default_block_id: str | None = Field(
        default=None, description="기본 매핑될 Report IR 블록 ID"
    )


# ── Style Token Mappings ──────────────────────────────────


class ColorMapping(BaseModel):
    """색상 매핑."""

    primary: str = Field(default="#003366", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary: str = Field(default="#0066CC", pattern=r"^#[0-9A-Fa-f]{6}$")
    accent: str = Field(default="#FF6600", pattern=r"^#[0-9A-Fa-f]{6}$")
    text_dark: str = Field(default="#333333", pattern=r"^#[0-9A-Fa-f]{6}$")
    text_light: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    background: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    warning: str = Field(default="#FF9900", pattern=r"^#[0-9A-Fa-f]{6}$")
    error: str = Field(default="#CC0000", pattern=r"^#[0-9A-Fa-f]{6}$")
    success: str = Field(default="#009933", pattern=r"^#[0-9A-Fa-f]{6}$")


class FontMapping(BaseModel):
    """폰트 매핑."""

    heading: str = Field(default="Arial Bold", max_length=100)
    body: str = Field(default="Arial", max_length=100)
    caption: str = Field(default="Arial", max_length=100)
    table_header: str = Field(default="Arial Bold", max_length=100)
    table_body: str = Field(default="Arial", max_length=100)


class SizeMapping(BaseModel):
    """폰트 크기 매핑 (포인트)."""

    title: int = Field(default=24, ge=8, le=72)
    heading1: int = Field(default=18, ge=8, le=48)
    heading2: int = Field(default=14, ge=8, le=36)
    body: int = Field(default=10, ge=6, le=24)
    caption: int = Field(default=8, ge=6, le=18)
    table_header: int = Field(default=9, ge=6, le=18)
    table_body: int = Field(default=8, ge=6, le=16)


class StyleTokens(BaseModel):
    """스타일 토큰 매핑.

    고객 템플릿의 스타일을 FDD Design System 토큰에 매핑합니다.
    """

    colors: ColorMapping = Field(default_factory=ColorMapping)
    fonts: FontMapping = Field(default_factory=FontMapping)
    sizes: SizeMapping = Field(default_factory=SizeMapping)


# ── Template Contract ─────────────────────────────────────


class TemplateContract(BaseModel):
    """템플릿 계약 정의.

    고객 PPT/Word 템플릿과 FDD 콘텐츠 간의 계약을 정의합니다.
    어떤 슬롯에 어떤 콘텐츠가 주입될지, 스타일 토큰 매핑 등을 포함합니다.
    """

    contract_version: str = Field(default="1.0", description="계약 버전")
    template_id: str = Field(
        ..., min_length=1, max_length=100, description="템플릿 고유 ID"
    )
    template_name: str = Field(
        ..., min_length=1, max_length=255, description="템플릿 표시명"
    )
    template_type: str = Field(
        default="pptx", pattern=r"^(pptx|docx)$", description="템플릿 타입"
    )
    slots: list[TemplateSlot] = Field(
        default_factory=list, description="템플릿 슬롯 목록"
    )
    style_tokens: StyleTokens = Field(
        default_factory=StyleTokens, description="스타일 토큰 매핑"
    )
    validation_rules: list[str] = Field(
        default_factory=list, description="검증 규칙 목록"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="추가 메타데이터"
    )


# ── Detected Slot ─────────────────────────────────────────


class DetectedSlot(BaseModel):
    """템플릿에서 탐지된 슬롯."""

    slot_id: str = Field(..., description="슬롯 ID")
    slot_type: SlotType = Field(..., description="추론된 슬롯 타입")
    location: str = Field(..., description="슬롯 위치 (슬라이드 번호, 페이지 등)")
    raw_text: str | None = Field(default=None, description="원본 텍스트")
    shape_id: str | None = Field(default=None, description="도형 ID (PPTX용)")


# ── Validation Results ────────────────────────────────────


class ValidationIssue(BaseModel):
    """검증 이슈."""

    severity: str = Field(..., pattern=r"^(error|warning|info)$")
    code: str = Field(..., description="이슈 코드")
    message: str = Field(..., description="이슈 메시지")
    slot_id: str | None = Field(default=None, description="관련 슬롯 ID")
    location: str | None = Field(default=None, description="이슈 위치")


class TemplateValidationResult(BaseModel):
    """템플릿 검증 결과."""

    is_valid: bool = Field(..., description="검증 통과 여부")
    detected_slots: list[DetectedSlot] = Field(
        default_factory=list, description="탐지된 슬롯 목록"
    )
    issues: list[ValidationIssue] = Field(
        default_factory=list, description="검증 이슈 목록"
    )
    contract: TemplateContract | None = Field(
        default=None, description="생성된 템플릿 계약 (검증 성공 시)"
    )


# ── Slot Mapping ──────────────────────────────────────────


class SlotBlockMapping(BaseModel):
    """슬롯-블록 매핑."""

    slot_id: str = Field(..., description="슬롯 ID")
    block_id: str = Field(..., description="Report IR 블록 ID")
    status: SlotStatus = Field(default=SlotStatus.MAPPED, description="매핑 상태")


class SlotMappingRequest(BaseModel):
    """슬롯 매핑 요청."""

    mappings: list[SlotBlockMapping] = Field(..., description="슬롯-블록 매핑 목록")


# ── Template CRUD Schemas ─────────────────────────────────


class TemplateUpload(BaseModel):
    """템플릿 업로드 요청 (메타데이터)."""

    template_name: str = Field(
        ..., min_length=1, max_length=255, description="템플릿 이름"
    )
    description: str | None = Field(default=None, max_length=1000)
    style_tokens: StyleTokens | None = Field(default=None)


class TemplateCreate(BaseModel):
    """템플릿 생성 요청."""

    template_name: str = Field(
        ..., min_length=1, max_length=255, description="템플릿 이름"
    )
    template_type: str = Field(default="pptx", pattern=r"^(pptx|docx)$")
    contract: TemplateContract
    description: str | None = Field(default=None, max_length=1000)


class TemplateUpdate(BaseModel):
    """템플릿 업데이트 요청."""

    template_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    style_tokens: StyleTokens | None = Field(default=None)
    status: TemplateStatus | None = Field(default=None)


class TemplateRead(BaseModel):
    """템플릿 조회 응답."""

    id: uuid.UUID
    template_id: str
    template_name: str
    template_type: str
    file_path: str | None
    contract: TemplateContract
    status: TemplateStatus
    description: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateListItem(BaseModel):
    """템플릿 목록 아이템."""

    id: uuid.UUID
    template_id: str
    template_name: str
    template_type: str
    status: TemplateStatus
    slot_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Injection Schemas ─────────────────────────────────────


class InjectionRequest(BaseModel):
    """템플릿 주입 요청."""

    template_id: uuid.UUID = Field(..., description="템플릿 ID")
    deal_id: uuid.UUID = Field(..., description="Deal ID")
    report_ir_id: str | None = Field(default=None, description="Report IR ID (캐시용)")
    slot_mappings: list[SlotBlockMapping] | None = Field(
        default=None, description="커스텀 슬롯 매핑 (없으면 기본 매핑 사용)"
    )
    output_format: str = Field(
        default="pptx", pattern=r"^(pptx|docx|pdf)$", description="출력 포맷"
    )


class InjectionResult(BaseModel):
    """템플릿 주입 결과."""

    success: bool
    output_path: str | None = Field(default=None, description="생성된 파일 경로")
    output_url: str | None = Field(default=None, description="다운로드 URL")
    filled_slots: list[str] = Field(default_factory=list, description="채워진 슬롯 목록")
    empty_slots: list[str] = Field(default_factory=list, description="빈 슬롯 목록")
    errors: list[str] = Field(default_factory=list, description="오류 목록")
    warnings: list[str] = Field(default_factory=list, description="경고 목록")
