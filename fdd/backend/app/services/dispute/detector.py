"""Dispute Sensitive Item Detector - 분쟁 민감 항목 탐지.

EPIC-15 FDD-1503: 분쟁 가능성 높은 항목 자동 식별.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.engines.delta_engine import DefinitionDelta, ImpactLevel
from app.renderers.report_builder import (
    BlockType,
    ClaimBlock,
    ReportBlock,
    ReportIR,
    TableBlock,
)

logger = logging.getLogger(__name__)


class DisputeCategory(StrEnum):
    """분쟁 카테고리."""

    LARGE_ADJUSTMENT = "large_adjustment"  # 대규모 조정
    RELATED_PARTY = "related_party"  # 관계사 거래
    SUBJECTIVE_JUDGMENT = "subjective_judgment"  # 주관적 판단
    VERSION_CHANGE = "version_change"  # 버전 변경
    UNVERIFIED_EVIDENCE = "unverified_evidence"  # 미검증 근거
    TIMING_SENSITIVE = "timing_sensitive"  # 기말/기초 민감
    RECURRING_DISPUTE = "recurring_dispute"  # 반복 분쟁 항목


class HighlightStyle(StrEnum):
    """강조 스타일."""

    RED_BORDER = "red_border"  # 빨간 테두리
    YELLOW_BACKGROUND = "yellow_background"  # 노란 배경
    QUESTION_ICON = "question_icon"  # 물음표 아이콘
    STAR_ICON = "star_icon"  # 별표 표시
    GRAY_ITALIC = "gray_italic"  # 회색 이탤릭


@dataclass
class DisputeSensitiveItem:
    """분쟁 민감 항목."""

    item_id: str
    category: DisputeCategory
    severity: str  # high, medium, low
    title: str
    description: str
    location: str  # Report IR 내 위치
    highlight_style: HighlightStyle
    related_evidence: list[str] = field(default_factory=list)
    recommendation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DisputeDetectionResult:
    """분쟁 탐지 결과."""

    items: list[DisputeSensitiveItem] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    high_risk_count: int = 0


# =============================================================================
# Detection Rules
# =============================================================================


def detect_large_adjustments(
    report_ir: ReportIR,
    threshold_percent: Decimal = Decimal("10"),
) -> list[DisputeSensitiveItem]:
    """대규모 조정 항목 탐지.

    조정금액이 EBITDA의 일정 비율 이상인 항목을 탐지합니다.

    Args:
        report_ir: Report IR
        threshold_percent: 임계값 (EBITDA 대비 %)

    Returns:
        분쟁 민감 항목 리스트
    """
    items: list[DisputeSensitiveItem] = []

    # EBITDA 기준값 추출 (KPI 블록에서)
    ebitda_base = Decimal("0")
    for block in report_ir.sections:
        if isinstance(block, TableBlock) and "qoe" in block.title.lower():
            for row in block.rows:
                if "reported" in str(row.get("category", "")).lower():
                    try:
                        ebitda_base = Decimal(
                            str(row.get("amount", "0")).replace(",", "")
                        )
                        break
                    except (ValueError, TypeError):
                        pass

    if ebitda_base == 0:
        return items

    threshold = abs(ebitda_base * threshold_percent / 100)

    # QoE 테이블에서 대규모 조정 탐지
    for block in report_ir.sections:
        if isinstance(block, TableBlock) and "qoe" in block.title.lower():
            for idx, row in enumerate(block.rows):
                try:
                    amount = Decimal(str(row.get("amount", "0")).replace(",", ""))
                    if abs(amount) > threshold:
                        category = row.get("category", "Unknown")
                        category_lower = category.lower()
                        # 조정 항목 필터 (합계/소계 행 제외)
                        is_adjustment = (
                            ("adjust" in category_lower or "non" in category_lower)
                            and "adjusted ebitda" not in category_lower
                            and "total" not in category_lower
                            and "subtotal" not in category_lower
                            and "reported" not in category_lower
                        )
                        if is_adjustment:
                            items.append(
                                DisputeSensitiveItem(
                                    item_id=f"large_adj_{idx}",
                                    category=DisputeCategory.LARGE_ADJUSTMENT,
                                    severity="high",
                                    title=f"Large adjustment: {category}",
                                    description=f"Adjustment amount {amount} exceeds {threshold_percent}% of EBITDA",
                                    location=f"{block.title}:row_{idx}",
                                    highlight_style=HighlightStyle.RED_BORDER,
                                    metadata={"amount": str(amount), "threshold": str(threshold)},
                                )
                            )
                except (ValueError, TypeError):
                    pass

    return items


def detect_related_party_transactions(
    report_ir: ReportIR,
    keywords: list[str] | None = None,
) -> list[DisputeSensitiveItem]:
    """관계사 거래 탐지.

    관계사 거래 관련 키워드가 포함된 항목을 탐지합니다.

    Args:
        report_ir: Report IR
        keywords: 관계사 키워드 리스트

    Returns:
        분쟁 민감 항목 리스트
    """
    if keywords is None:
        keywords = [
            "관계사",
            "특수관계",
            "related party",
            "affiliate",
            "intercompany",
            "대주주",
            "계열사",
            "모회사",
            "자회사",
        ]

    items: list[DisputeSensitiveItem] = []

    for block in report_ir.sections:
        if isinstance(block, TableBlock):
            for idx, row in enumerate(block.rows):
                row_text = " ".join(str(v) for v in row.values()).lower()
                for keyword in keywords:
                    if keyword.lower() in row_text:
                        items.append(
                            DisputeSensitiveItem(
                                item_id=f"rpt_{block.title}_{idx}",
                                category=DisputeCategory.RELATED_PARTY,
                                severity="medium",
                                title=f"Related party transaction detected",
                                description=f"Keyword '{keyword}' found in {block.title}",
                                location=f"{block.title}:row_{idx}",
                                highlight_style=HighlightStyle.YELLOW_BACKGROUND,
                                metadata={"keyword": keyword},
                            )
                        )
                        break  # 중복 방지

        elif isinstance(block, ClaimBlock):
            claim_text = block.claim_text.lower()
            for keyword in keywords:
                if keyword.lower() in claim_text:
                    items.append(
                        DisputeSensitiveItem(
                            item_id=f"rpt_claim_{id(block)}",
                            category=DisputeCategory.RELATED_PARTY,
                            severity="medium",
                            title="Related party mentioned in claim",
                            description=f"Keyword '{keyword}' found in claim",
                            location="claim_block",
                            highlight_style=HighlightStyle.YELLOW_BACKGROUND,
                            metadata={"keyword": keyword},
                        )
                    )
                    break

    return items


def detect_subjective_judgments(
    report_ir: ReportIR,
    confidence_threshold: float = 0.5,
) -> list[DisputeSensitiveItem]:
    """주관적 판단 항목 탐지.

    신뢰도가 낮거나 주관적 판단이 필요한 항목을 탐지합니다.

    Args:
        report_ir: Report IR
        confidence_threshold: 신뢰도 임계값

    Returns:
        분쟁 민감 항목 리스트
    """
    items: list[DisputeSensitiveItem] = []

    subjective_keywords = [
        "추정",
        "estimate",
        "예상",
        "expected",
        "가정",
        "assumption",
        "판단",
        "judgment",
        "불확실",
        "uncertain",
        "미확정",
        "tentative",
    ]

    for block in report_ir.sections:
        if isinstance(block, ClaimBlock):
            # 신뢰도 기반 (evidence가 없거나 적음)
            if not block.verified or len(block.evidence_refs) == 0:
                items.append(
                    DisputeSensitiveItem(
                        item_id=f"subj_unverified_{id(block)}",
                        category=DisputeCategory.SUBJECTIVE_JUDGMENT,
                        severity="medium",
                        title="Unverified claim",
                        description="Claim has no supporting evidence",
                        location="claim_block",
                        highlight_style=HighlightStyle.QUESTION_ICON,
                    )
                )

            # 키워드 기반
            claim_lower = block.claim_text.lower()
            for keyword in subjective_keywords:
                if keyword.lower() in claim_lower:
                    items.append(
                        DisputeSensitiveItem(
                            item_id=f"subj_kw_{id(block)}_{keyword}",
                            category=DisputeCategory.SUBJECTIVE_JUDGMENT,
                            severity="low",
                            title=f"Subjective language: '{keyword}'",
                            description=f"Claim contains subjective language",
                            location="claim_block",
                            highlight_style=HighlightStyle.QUESTION_ICON,
                            metadata={"keyword": keyword},
                        )
                    )
                    break

    return items


def detect_version_change_items(
    deltas: list[DefinitionDelta] | None = None,
) -> list[DisputeSensitiveItem]:
    """버전 변경 민감 항목 탐지.

    정의 변경 중 HIGH/CRITICAL 영향도 항목을 탐지합니다.

    Args:
        deltas: 정의 변경 내역

    Returns:
        분쟁 민감 항목 리스트
    """
    items: list[DisputeSensitiveItem] = []

    if not deltas:
        return items

    for delta in deltas:
        if delta.impact_level in (ImpactLevel.HIGH, ImpactLevel.CRITICAL):
            severity = "high" if delta.impact_level == ImpactLevel.CRITICAL else "medium"
            items.append(
                DisputeSensitiveItem(
                    item_id=f"ver_{delta.field}",
                    category=DisputeCategory.VERSION_CHANGE,
                    severity=severity,
                    title=f"Definition change: {delta.field}",
                    description=delta.description,
                    location="definition",
                    highlight_style=HighlightStyle.STAR_ICON,
                    metadata={
                        "change_type": delta.change_type.value,
                        "impact_level": delta.impact_level.value,
                    },
                )
            )

    return items


def detect_unverified_evidence(
    report_ir: ReportIR,
) -> list[DisputeSensitiveItem]:
    """미검증 근거 탐지.

    Evidence가 없거나 검증되지 않은 주장을 탐지합니다.

    Args:
        report_ir: Report IR

    Returns:
        분쟁 민감 항목 리스트
    """
    items: list[DisputeSensitiveItem] = []

    for block in report_ir.sections:
        if isinstance(block, ClaimBlock):
            if not block.evidence_refs:
                items.append(
                    DisputeSensitiveItem(
                        item_id=f"unverified_{id(block)}",
                        category=DisputeCategory.UNVERIFIED_EVIDENCE,
                        severity="medium",
                        title="Claim without evidence",
                        description="This claim has no linked evidence",
                        location="claim_block",
                        highlight_style=HighlightStyle.GRAY_ITALIC,
                        recommendation="Link supporting documents or data sources",
                    )
                )

    return items


# =============================================================================
# Main Detection Function
# =============================================================================


def identify_dispute_sensitive_items(
    report_ir: ReportIR,
    definition: dict[str, Any] | None = None,
    deltas: list[DefinitionDelta] | None = None,
    ebitda_threshold_percent: Decimal = Decimal("10"),
) -> DisputeDetectionResult:
    """분쟁 민감 항목 종합 탐지.

    모든 탐지 규칙을 실행하여 분쟁 민감 항목을 식별합니다.

    Args:
        report_ir: Report IR
        definition: 현재 정의 데이터 (선택)
        deltas: 정의 변경 내역 (선택)
        ebitda_threshold_percent: 대규모 조정 임계값

    Returns:
        분쟁 탐지 결과
    """
    all_items: list[DisputeSensitiveItem] = []

    # 1. 대규모 조정 탐지
    all_items.extend(detect_large_adjustments(report_ir, ebitda_threshold_percent))

    # 2. 관계사 거래 탐지
    all_items.extend(detect_related_party_transactions(report_ir))

    # 3. 주관적 판단 탐지
    all_items.extend(detect_subjective_judgments(report_ir))

    # 4. 버전 변경 민감 항목
    if deltas:
        all_items.extend(detect_version_change_items(deltas))

    # 5. 미검증 근거 탐지
    all_items.extend(detect_unverified_evidence(report_ir))

    # 카테고리별 집계
    summary: dict[str, int] = {}
    high_risk_count = 0

    for item in all_items:
        summary[item.category] = summary.get(item.category, 0) + 1
        if item.severity == "high":
            high_risk_count += 1

    return DisputeDetectionResult(
        items=all_items,
        summary=summary,
        high_risk_count=high_risk_count,
    )
