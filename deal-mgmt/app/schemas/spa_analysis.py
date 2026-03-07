"""SPA 계약서 LLM 역분석 — Pydantic 스키마.

3단계 Human-in-the-Loop 프로토콜:
  Step 1: 원문 → 변수 추출
  Step 2: 변수 확정 → 조항 분해
  Step 3: 최종 확정 → DB 템플릿 생성
"""

from __future__ import annotations

import ast
import re
import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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

# BTA 전용 ENUM
BTA_SCOPES = [
    "COMPREHENSIVE_TRANSFER",
    "PARTIAL_TRANSFER",
    "OTHER_SCOPE",
]

SEVERANCE_PAY_HANDLING = [
    "ASSUMED_BY_BUYER",
    "PAID_BY_SELLER",
    "OTHER_METHOD",
]

# SSA 전용 ENUM
SSA_SECURITY_TYPES = [
    "COMMON_SHARE",
    "RCPS",
    "CB",
    "BW",
    "OTHER_SECURITY",
]

SSA_TRANSACTION_CONTEXTS = [
    "STANDALONE_INVESTMENT",
    "PARALLEL_WITH_SPA",
    "PARALLEL_WITH_BTA",
    "OTHER_CONTEXT",
]

# MOU 전용 ENUM
MOU_TRANSACTION_TYPES = [
    "SHARE_PURCHASE",
    "BUSINESS_TRANSFER",
    "NEW_SHARE_ISSUE",
    "COMBINED",
    "OTHER_MOU_TYPE",
]

MOU_DEPOSIT_HANDLING = [
    "REFUNDABLE",
    "NON_REFUNDABLE",
    "NO_DEPOSIT",
]

# SPA + SHA + BTA + SSA + MOU 통합 유효값 (validator용)
ALL_STRUCTURE_TYPES = [
    *DEAL_STRUCTURES,
    *SHA_TYPES,
    *BTA_SCOPES,
    *SSA_SECURITY_TYPES,
    *MOU_TRANSACTION_TYPES,
]

# Literal 타입 — IDE 자동완성 + 타입 안전성
AllStructureType = Literal[
    # SPA
    "PURE_SHARE_TRANSFER",
    "CARVE_OUT",
    "WITH_NEW_SHARES",
    "OTHER_STRUCTURE",
    # SHA
    "POST_BUYOUT",
    "JOINT_VENTURE",
    "MINORITY_INVESTMENT",
    "OTHER_TYPE",
    # BTA
    "COMPREHENSIVE_TRANSFER",
    "PARTIAL_TRANSFER",
    "OTHER_SCOPE",
    # SSA
    "COMMON_SHARE",
    "RCPS",
    "CB",
    "BW",
    "OTHER_SECURITY",
    # MOU
    "SHARE_PURCHASE",
    "BUSINESS_TRANSFER",
    "NEW_SHARE_ISSUE",
    "COMBINED",
    "OTHER_MOU_TYPE",
]

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

    variable_key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]{0,98}$",
    )
    input_type: str = Field(..., description="TEXT/TEXTAREA/NUMBER/DATE/SELECT/BOOLEAN/CURRENCY/PERCENTAGE")
    question_label: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=1000)
    extracted_value: str | None = Field(default=None, max_length=10000, description="원문에서 추출된 실제 값")
    default_value: str | None = Field(default=None, max_length=10000)
    is_required: bool = True
    select_options: dict[str, str] | None = None
    display_order: int = 0
    group_name: str | None = Field(default=None, max_length=100)
    visible_condition: str | None = Field(default=None, max_length=500)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("input_type")
    @classmethod
    def validate_input_type(cls, v: str) -> str:
        if v not in VALID_INPUT_TYPES:
            msg = f"input_type은 {VALID_INPUT_TYPES} 중 하나여야 합니다: {v}"
            raise ValueError(msg)
        return v

    @field_validator("visible_condition")
    @classmethod
    def validate_visible_condition(cls, v: str | None) -> str | None:
        """visible_condition도 condition_expression과 동일한 보안 검증 적용."""
        if v is None:
            return v

        forbidden = re.compile(
            r"(__\w+__|import|exec|eval|compile|globals|locals|getattr|setattr|delattr|open|os\.|sys\.|subprocess)"
        )
        if forbidden.search(v):
            return None  # 위험한 표현식 → 무시
        try:
            ast.parse(v, mode="eval")
        except SyntaxError:
            return None  # 파싱 불가능 → 무시
        return v


class DiscoveredBoolean(BaseModel):
    """LLM이 자율 발견한 특수 조항 BOOLEAN 변수."""

    variable_key: str = Field(..., pattern=r"^has_[a-z_]+$", max_length=100)
    question_label: str = Field(..., min_length=1, max_length=300)
    detected_in_clause: str | None = Field(
        default=None,
        max_length=200,
        description="해당 BOOLEAN이 발견된 원문 조항 제목",
    )


class SpaStep1Response(BaseModel):
    """Step 1 응답 — 추출된 변수 목록."""

    session_id: str
    variables: list[ExtractedVariable]
    deal_structure: AllStructureType
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
    # BTA 전용 필드 (SPA/SHA에서는 None)
    bta_scope: str | None = Field(
        default=None,
        description="BTA 양도 범위 (COMPREHENSIVE_TRANSFER/PARTIAL_TRANSFER/OTHER_SCOPE)",
    )
    severance_pay_handling: str | None = Field(
        default=None,
        description="BTA 퇴직금 처리 (ASSUMED_BY_BUYER/PAID_BY_SELLER/OTHER_METHOD)",
    )
    # SSA 전용 필드 (SPA/SHA/BTA에서는 None)
    security_type: str | None = Field(
        default=None,
        description="SSA 증권 종류 (COMMON_SHARE/RCPS/CB/BW/OTHER_SECURITY)",
    )
    transaction_context: str | None = Field(
        default=None,
        description="SSA 거래 맥락 (STANDALONE_INVESTMENT/PARALLEL_WITH_SPA/PARALLEL_WITH_BTA/OTHER_CONTEXT)",
    )
    # MOU 전용 필드 (SPA/SHA/BTA/SSA에서는 None)
    mou_transaction_type: str | None = Field(
        default=None,
        description="MOU 거래 유형 (SHARE_PURCHASE/BUSINESS_TRANSFER/NEW_SHARE_ISSUE/COMBINED/OTHER_MOU_TYPE)",
    )
    deposit_handling: str | None = Field(
        default=None,
        description="MOU 보증금 처리 (REFUNDABLE/NON_REFUNDABLE/NO_DEPOSIT)",
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

    @field_validator("sha_type")
    @classmethod
    def validate_sha_type(cls, v: str | None) -> str | None:
        if v is not None and v not in SHA_TYPES:
            return "OTHER_TYPE"  # LLM 잘못된 값 → 안전한 기본값
        return v

    @field_validator("exit_strategy")
    @classmethod
    def validate_exit_strategy(cls, v: str | None) -> str | None:
        if v is not None and v not in EXIT_STRATEGIES:
            return "OTHER_STRATEGY"  # LLM 잘못된 값 → 안전한 기본값
        return v

    @field_validator("bta_scope")
    @classmethod
    def validate_bta_scope(cls, v: str | None) -> str | None:
        if v is not None and v not in BTA_SCOPES:
            return "OTHER_SCOPE"  # LLM 잘못된 값 → 안전한 기본값
        return v

    @field_validator("severance_pay_handling")
    @classmethod
    def validate_severance_pay_handling(cls, v: str | None) -> str | None:
        if v is not None and v not in SEVERANCE_PAY_HANDLING:
            return "OTHER_METHOD"  # LLM 잘못된 값 → 안전한 기본값
        return v

    @field_validator("security_type")
    @classmethod
    def validate_security_type(cls, v: str | None) -> str | None:
        if v is not None and v not in SSA_SECURITY_TYPES:
            return "OTHER_SECURITY"  # LLM 잘못된 값 → 안전한 기본값
        return v

    @field_validator("transaction_context")
    @classmethod
    def validate_transaction_context(cls, v: str | None) -> str | None:
        if v is not None and v not in SSA_TRANSACTION_CONTEXTS:
            return "OTHER_CONTEXT"  # LLM 잘못된 값 → 안전한 기본값
        return v

    @field_validator("mou_transaction_type")
    @classmethod
    def validate_mou_transaction_type(cls, v: str | None) -> str | None:
        if v is not None and v not in MOU_TRANSACTION_TYPES:
            return "OTHER_MOU_TYPE"  # LLM 잘못된 값 → 안전한 기본값
        return v

    @field_validator("deposit_handling")
    @classmethod
    def validate_deposit_handling(cls, v: str | None) -> str | None:
        if v is not None and v not in MOU_DEPOSIT_HANDLING:
            return "NO_DEPOSIT"  # LLM 잘못된 값 → 안전한 기본값
        return v

    @field_validator("detected_doc_type")
    @classmethod
    def validate_detected_doc_type(cls, v: str) -> str:
        if v not in VALID_DOC_TYPES:
            return "SPA"  # 알 수 없는 유형 → SPA 기본값
        return v

    @model_validator(mode="after")
    def validate_structure_for_doc_type(self) -> SpaStep1Response:
        """SHA→SHA_TYPES, BTA→BTA_SCOPES, SSA→SSA_SECURITY_TYPES, MOU→MOU_TRANSACTION_TYPES, 그 외→DEAL_STRUCTURES 허용."""
        ds = self.deal_structure
        if self.detected_doc_type == "SHA" and ds not in SHA_TYPES:
            self.deal_structure = "OTHER_TYPE"
        elif self.detected_doc_type == "BTA" and ds not in BTA_SCOPES:
            self.deal_structure = "OTHER_SCOPE"
        elif self.detected_doc_type == "SSA" and ds not in SSA_SECURITY_TYPES:
            self.deal_structure = "OTHER_SECURITY"
        elif self.detected_doc_type == "MOU" and ds not in MOU_TRANSACTION_TYPES:
            self.deal_structure = "OTHER_MOU_TYPE"
        elif self.detected_doc_type == "SPA" and ds not in DEAL_STRUCTURES:
            self.deal_structure = "OTHER_STRUCTURE"
        return self


# ── Step 2: 조항 분해 ──────────────────────────────────────────────────────


class SpaStep2Request(BaseModel):
    """Step 2 요청 — 확정된 변수 + deal/industry 분류."""

    session_id: str = Field(..., min_length=1)
    spa_text: str | None = Field(
        default=None,
        max_length=500_000,
        description="멀티워커 폴백용 원문 텍스트 (세션 유실 시 사용)",
    )
    doc_type_hint: Literal["SPA", "SHA", "BTA", "SSA", "MOU"] | None = Field(
        default=None,
        description="멀티워커 폴백용 문서 유형 (세션 유실 시 detected_doc_type 복원)",
    )
    variables: list[ExtractedVariable]
    deal_structure: AllStructureType
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
    condition_expression: str | None = Field(default=None, max_length=500)
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


# ── Step 4: 교차 검증 Redline ────────────────────────────────────────────────


class RedlineIssueSchema(BaseModel):
    """LLM 반환 교차 검증 이슈 (파싱 + 검증용)."""

    issue_id: str = Field(..., pattern=r"^ISS-\d{3,}$")
    clause_ref: str = Field(..., max_length=200)
    severity: Literal["High", "Medium", "Low"]
    rationale: str = Field(..., max_length=5000)
    original_target_text: str = Field(..., min_length=5, max_length=5000)
    proposed_redline: str = Field(..., min_length=5, max_length=10000)

    @field_validator("original_target_text")
    @classmethod
    def validate_no_newlines(cls, v: str) -> str:
        """문단 간 교차 타겟팅 차단 — 줄바꿈 포함 시 검증 오류."""
        if "\n" in v or "\r" in v:
            raise ValueError(
                "original_target_text에 줄바꿈이 포함되어 있습니다. 반드시 단일 문단 내의 문구로 한정하세요."
            )
        return v

    @field_validator("proposed_redline")
    @classmethod
    def validate_redline_tags(cls, v: str) -> str:
        """[DEL]/[INS] 태그 쌍 검증 + 개별 태그 내용 길이 제한."""
        import re as _re

        del_opens = v.count("[DEL]")
        del_closes = v.count("[/DEL]")
        ins_opens = v.count("[INS]")
        ins_closes = v.count("[/INS]")

        if del_opens != del_closes:
            raise ValueError(f"[DEL] 태그 불일치: 열림={del_opens}, 닫힘={del_closes}")
        if ins_opens != ins_closes:
            raise ValueError(f"[INS] 태그 불일치: 열림={ins_opens}, 닫힘={ins_closes}")
        if del_opens == 0 and ins_opens == 0:
            raise ValueError("proposed_redline에 [DEL] 또는 [INS] 태그가 하나도 없습니다.")

        max_tag_len = 2000
        for tag in ("DEL", "INS"):
            for m in _re.finditer(rf"\[{tag}\](.*?)\[/{tag}\]", v, _re.DOTALL):
                if len(m.group(1)) > max_tag_len:
                    raise ValueError(f"[{tag}] 태그 내용이 {max_tag_len}자를 초과합니다 ({len(m.group(1))}자).")
        return v
