"""SPA 계약서 LLM 역분석 — Pydantic 스키마.

3단계 Human-in-the-Loop 프로토콜:
  Step 1: 원문 → 변수 추출
  Step 2: 변수 확정 → 조항 분해
  Step 3: 최종 확정 → DB 템플릿 생성
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ── 확장 ENUM 상수 ──────────────────────────────────────────────────────────

VALID_DOC_TYPES = ["SPA", "SHA", "BTA", "SSA", "MOU"]

DEAL_STRUCTURES = [
    "PURE_SHARE_TRANSFER",
    "CARVE_OUT",
    "WITH_NEW_SHARES",
    "OTHER_STRUCTURE",
]

# SHA 전용 ENUM
SHA_TYPES = [
    "POST_BUYOUT",
    "JOINT_VENTURE",
    "MINORITY_INVESTMENT",
    "OTHER_TYPE",
]

EXIT_STRATEGIES = [
    "IPO_FOCUSED",
    "MNA_FOCUSED",
    "OTHER_STRATEGY",
]

# SPA DEAL_STRUCTURES + SHA SHA_TYPES 통합 유효값 (validator용)
ALL_STRUCTURE_TYPES = [*DEAL_STRUCTURES, *SHA_TYPES]

INDUSTRY_TYPES = [
    "MANUFACTURING",
    "SOFTWARE",
    "FRANCHISE",
    "GENERAL",
    "OTHER_INDUSTRY",
]

VALID_INPUT_TYPES = [
    "TEXT",
    "TEXTAREA",
    "NUMBER",
    "DATE",
    "SELECT",
    "BOOLEAN",
    "CURRENCY",
    "PERCENTAGE",
]

# ── Step 1: 변수 추출 ──────────────────────────────────────────────────────


class SpaStep1Request(BaseModel):
    """Step 1 요청 — 계약서 원문 텍스트 입력."""

    spa_text: str = Field(..., min_length=100, max_length=500_000)
    language_hint: Literal["ko", "en"] | None = Field(
        default=None,
        description="언어 힌트. 미지정 시 LLM이 자동 감지.",
    )
    doc_type_hint: Literal["SPA", "SHA", "BTA", "SSA", "MOU"] | None = Field(
        default=None,
        description="문서 유형 힌트. 미지정 시 LLM이 자동 감지.",
    )


class ExtractedVariable(BaseModel):
    """LLM이 추출한 변수 하나."""

    variable_key: str = Field(..., min_length=1, max_length=100)
    input_type: str = Field(..., description="TEXT/TEXTAREA/NUMBER/DATE/SELECT/BOOLEAN/CURRENCY/PERCENTAGE")
    question_label: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    extracted_value: str | None = Field(default=None, description="원문에서 추출된 실제 값")
    default_value: str | None = None
    is_required: bool = True
    select_options: dict[str, str] | None = None
    display_order: int = 0
    group_name: str | None = None
    visible_condition: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("input_type")
    @classmethod
    def validate_input_type(cls, v: str) -> str:
        if v not in VALID_INPUT_TYPES:
            msg = f"input_type은 {VALID_INPUT_TYPES} 중 하나여야 합니다: {v}"
            raise ValueError(msg)
        return v


class DiscoveredBoolean(BaseModel):
    """LLM이 자율 발견한 특수 조항 BOOLEAN 변수."""

    variable_key: str = Field(..., pattern=r"^has_[a-z_]+$")
    question_label: str
    detected_in_clause: str | None = Field(
        default=None,
        description="해당 BOOLEAN이 발견된 원문 조항 제목",
    )


class SpaStep1Response(BaseModel):
    """Step 1 응답 — 추출된 변수 목록."""

    session_id: str
    variables: list[ExtractedVariable]
    deal_structure: str  # SPA: DEAL_STRUCTURES / SHA: SHA_TYPES
    industry_type: str
    detected_doc_type: str = Field(
        default="SPA",
        description="LLM이 감지한 계약서 유형 (SPA/SHA/BTA/SSA/MOU)",
    )
    # SHA 전용 필드 (SPA에서는 None)
    sha_type: str | None = Field(
        default=None,
        description="SHA 유형 (POST_BUYOUT/JOINT_VENTURE/MINORITY_INVESTMENT/OTHER_TYPE)",
    )
    exit_strategy: str | None = Field(
        default=None,
        description="SHA 주요 Exit 전략 (IPO_FOCUSED/MNA_FOCUSED/OTHER_STRATEGY)",
    )
    discovered_booleans: list[DiscoveredBoolean] = Field(default_factory=list)
    llm_cost_usd: float | None = None
    model_used: str | None = None

    @field_validator("deal_structure")
    @classmethod
    def validate_deal_structure(cls, v: str) -> str:
        if v not in ALL_STRUCTURE_TYPES:
            msg = f"deal_structure는 {ALL_STRUCTURE_TYPES} 중 하나여야 합니다: {v}"
            raise ValueError(msg)
        return v

    @field_validator("industry_type")
    @classmethod
    def validate_industry_type(cls, v: str) -> str:
        if v not in INDUSTRY_TYPES:
            msg = f"industry_type은 {INDUSTRY_TYPES} 중 하나여야 합니다: {v}"
            raise ValueError(msg)
        return v

    @field_validator("detected_doc_type")
    @classmethod
    def validate_detected_doc_type(cls, v: str) -> str:
        if v not in VALID_DOC_TYPES:
            return "SPA"  # 알 수 없는 유형 → SPA 기본값
        return v


# ── Step 2: 조항 분해 ──────────────────────────────────────────────────────


class SpaStep2Request(BaseModel):
    """Step 2 요청 — 확정된 변수 + deal/industry 분류."""

    session_id: str = Field(..., min_length=1)
    spa_text: str | None = Field(
        default=None,
        max_length=500_000,
        description="멀티워커 폴백용 원문 텍스트 (세션 유실 시 사용)",
    )
    variables: list[ExtractedVariable]
    deal_structure: str
    industry_type: str

    @field_validator("deal_structure")
    @classmethod
    def validate_deal_structure(cls, v: str) -> str:
        if v not in ALL_STRUCTURE_TYPES:
            msg = f"deal_structure는 {ALL_STRUCTURE_TYPES} 중 하나여야 합니다: {v}"
            raise ValueError(msg)
        return v

    @field_validator("industry_type")
    @classmethod
    def validate_industry_type(cls, v: str) -> str:
        if v not in INDUSTRY_TYPES:
            msg = f"industry_type은 {INDUSTRY_TYPES} 중 하나여야 합니다: {v}"
            raise ValueError(msg)
        return v


class AnalyzedClause(BaseModel):
    """LLM이 분해한 조항 하나."""

    clause_order: int = Field(..., ge=0)
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1, description="Jinja2 템플릿 변환된 HTML")
    original_content: str = Field(..., min_length=1, description="원문 HTML")
    is_boilerplate: bool = False
    condition_expression: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class SpaStep2Response(BaseModel):
    """Step 2 응답 — 분해된 조항 목록."""

    session_id: str
    clauses: list[AnalyzedClause]
    llm_cost_usd: float | None = None
    model_used: str | None = None


# ── Step 3: 템플릿 생성 ────────────────────────────────────────────────────


class SpaStep3Request(BaseModel):
    """Step 3 요청 — 최종 확정 후 DB 저장."""

    session_id: str = Field(..., min_length=1)
    template_name: str = Field(..., min_length=1, max_length=200)
    template_description: str | None = Field(default=None, max_length=2000)
    doc_type: str = Field(default="SPA", description="계약서 유형 (SPA/SHA/BTA/SSA/MOU)")
    variables: list[ExtractedVariable]
    clauses: list[AnalyzedClause]

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        if v not in VALID_DOC_TYPES:
            return "SPA"
        return v


class SpaStep3Response(BaseModel):
    """Step 3 응답 — 생성된 템플릿 정보."""

    template_id: uuid.UUID
    template_name: str
    variables_count: int
    clauses_count: int
    message: str
