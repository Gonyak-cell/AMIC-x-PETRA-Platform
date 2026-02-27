"""Dispute Detection Tests - 분쟁 민감 항목 탐지 테스트.

EPIC-15 FDD-1503: Dispute Detection 테스트.
"""

from decimal import Decimal

import pytest

from app.engines.delta_engine import ChangeType, DefinitionDelta, ImpactLevel
from app.renderers.report_builder import (
    AlignType,
    ClaimBlock,
    EvidenceRef,
    ReportIR,
    ReportMetadata,
    TableBlock,
    TableColumn,
    TextBlock,
)
from app.services.dispute import (
    DisputeCategory,
    HighlightStyle,
    detect_large_adjustments,
    detect_related_party_transactions,
    detect_subjective_judgments,
    detect_unverified_evidence,
    detect_version_change_items,
    identify_dispute_sensitive_items,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_report_ir_with_adjustments() -> ReportIR:
    """조정 항목이 있는 Report IR."""
    return ReportIR(
        metadata=ReportMetadata(deal_id="test-001"),
        sections=[
            TableBlock(
                title="qoe_bridge",
                columns=[
                    TableColumn(key="category", header="Category", align=AlignType.LEFT),
                    TableColumn(key="amount", header="Amount", align=AlignType.RIGHT),
                ],
                rows=[
                    {"category": "Reported EBITDA", "amount": "10,000"},
                    {"category": "Non-recurring adjustment", "amount": "1,500"},  # 15% - large
                    {"category": "Normalization", "amount": "200"},  # 2% - small
                    {"category": "Adjusted EBITDA", "amount": "11,700"},
                ],
            ),
        ],
    )


@pytest.fixture
def sample_report_ir_with_related_party() -> ReportIR:
    """관계사 거래가 있는 Report IR."""
    return ReportIR(
        metadata=ReportMetadata(deal_id="test-002"),
        sections=[
            TableBlock(
                title="transactions",
                columns=[
                    TableColumn(key="description", header="Description", align=AlignType.LEFT),
                    TableColumn(key="amount", header="Amount", align=AlignType.RIGHT),
                ],
                rows=[
                    {"description": "Regular vendor payment", "amount": "500"},
                    {"description": "관계사 대여금", "amount": "3,000"},  # Related party
                    {"description": "Intercompany transfer", "amount": "2,000"},  # Related party
                ],
            ),
            ClaimBlock(
                claim_text="The company has significant affiliate transactions.",
                verified=True,
                evidence_refs=[
                    EvidenceRef(evidence_id="ev1", source_type="FILE", source_id="doc1"),
                ],
            ),
        ],
    )


@pytest.fixture
def sample_report_ir_with_claims() -> ReportIR:
    """Claim이 있는 Report IR."""
    return ReportIR(
        metadata=ReportMetadata(deal_id="test-003"),
        sections=[
            ClaimBlock(
                claim_text="Management estimates future growth at 10%.",
                verified=True,
                evidence_refs=[
                    EvidenceRef(evidence_id="ev1", source_type="FILE", source_id="doc1"),
                ],
            ),
            ClaimBlock(
                claim_text="This is an unverified claim.",
                verified=False,
                evidence_refs=[],
            ),
            ClaimBlock(
                claim_text="Revenue is expected to increase.",
                verified=True,
                evidence_refs=[
                    EvidenceRef(evidence_id="ev2", source_type="TB", source_id="tb1"),
                ],
            ),
        ],
    )


@pytest.fixture
def sample_deltas() -> list[DefinitionDelta]:
    """샘플 정의 변경 내역."""
    return [
        DefinitionDelta(
            field="cash",
            change_type=ChangeType.MODIFIED,
            old_value={"include": ["1110"]},
            new_value={"include": ["1110", "1120"]},
            impact_level=ImpactLevel.MEDIUM,
            description="Cash definition updated",
        ),
        DefinitionDelta(
            field="debt_like",
            change_type=ChangeType.ADDED,
            old_value=None,
            new_value=[{"item": "Pension", "category": "pension"}],
            impact_level=ImpactLevel.HIGH,
            description="Debt-like items added",
        ),
        DefinitionDelta(
            field="target_nwc",
            change_type=ChangeType.MODIFIED,
            old_value={"method": "6M_AVG"},
            new_value={"method": "12M_AVG", "value": "5000"},
            impact_level=ImpactLevel.CRITICAL,
            description="Target NWC method changed",
        ),
    ]


# =============================================================================
# Large Adjustment Tests
# =============================================================================


class TestDetectLargeAdjustments:
    """detect_large_adjustments tests."""

    def test_detect_large_adjustment(self, sample_report_ir_with_adjustments):
        """대규모 조정 탐지."""
        items = detect_large_adjustments(
            sample_report_ir_with_adjustments,
            threshold_percent=Decimal("10"),
        )

        # 1,500 / 10,000 = 15% > 10% threshold
        assert len(items) == 1
        assert items[0].category == DisputeCategory.LARGE_ADJUSTMENT
        assert items[0].severity == "high"
        assert items[0].highlight_style == HighlightStyle.RED_BORDER

    def test_no_large_adjustments(self, sample_report_ir_with_adjustments):
        """임계값 이상 조정 없음."""
        items = detect_large_adjustments(
            sample_report_ir_with_adjustments,
            threshold_percent=Decimal("20"),  # Higher threshold
        )

        assert len(items) == 0

    def test_empty_report(self):
        """빈 리포트."""
        report = ReportIR()
        items = detect_large_adjustments(report)
        assert len(items) == 0


# =============================================================================
# Related Party Tests
# =============================================================================


class TestDetectRelatedPartyTransactions:
    """detect_related_party_transactions tests."""

    def test_detect_related_party_in_table(self, sample_report_ir_with_related_party):
        """테이블에서 관계사 거래 탐지."""
        items = detect_related_party_transactions(sample_report_ir_with_related_party)

        # Should find "관계사" and "intercompany" and "affiliate"
        assert len(items) >= 2
        categories = [i.category for i in items]
        assert all(c == DisputeCategory.RELATED_PARTY for c in categories)

    def test_detect_related_party_in_claim(self, sample_report_ir_with_related_party):
        """Claim에서 관계사 거래 탐지."""
        items = detect_related_party_transactions(sample_report_ir_with_related_party)

        # "affiliate" in claim
        affilite_items = [i for i in items if "affiliate" in str(i.metadata)]
        assert len(affilite_items) >= 1

    def test_custom_keywords(self):
        """커스텀 키워드 사용."""
        report = ReportIR(
            sections=[
                TableBlock(
                    title="test",
                    columns=[TableColumn(key="desc", header="Desc", align=AlignType.LEFT)],
                    rows=[{"desc": "CUSTOM_KEYWORD transaction"}],
                )
            ]
        )
        items = detect_related_party_transactions(report, keywords=["CUSTOM_KEYWORD"])

        assert len(items) == 1
        assert items[0].metadata["keyword"] == "CUSTOM_KEYWORD"


# =============================================================================
# Subjective Judgment Tests
# =============================================================================


class TestDetectSubjectiveJudgments:
    """detect_subjective_judgments tests."""

    def test_detect_unverified_claim(self, sample_report_ir_with_claims):
        """미검증 주장 탐지."""
        items = detect_subjective_judgments(sample_report_ir_with_claims)

        # Find unverified claim
        unverified = [i for i in items if "unverified" in i.item_id.lower()]
        assert len(unverified) >= 1

    def test_detect_subjective_keywords(self, sample_report_ir_with_claims):
        """주관적 키워드 탐지."""
        items = detect_subjective_judgments(sample_report_ir_with_claims)

        # "estimates" and "expected" should trigger
        keyword_items = [i for i in items if "kw" in i.item_id]
        assert len(keyword_items) >= 1


# =============================================================================
# Version Change Tests
# =============================================================================


class TestDetectVersionChangeItems:
    """detect_version_change_items tests."""

    def test_detect_high_impact_changes(self, sample_deltas):
        """HIGH/CRITICAL 영향 변경 탐지."""
        items = detect_version_change_items(sample_deltas)

        # Should find HIGH and CRITICAL changes (not MEDIUM)
        assert len(items) == 2  # debt_like (HIGH) and target_nwc (CRITICAL)

        severities = {i.severity for i in items}
        assert "high" in severities
        assert "medium" in severities  # CRITICAL → high, HIGH → medium in detector

    def test_no_deltas(self):
        """변경 없음."""
        items = detect_version_change_items(None)
        assert len(items) == 0

        items = detect_version_change_items([])
        assert len(items) == 0


# =============================================================================
# Unverified Evidence Tests
# =============================================================================


class TestDetectUnverifiedEvidence:
    """detect_unverified_evidence tests."""

    def test_detect_claims_without_evidence(self, sample_report_ir_with_claims):
        """근거 없는 주장 탐지."""
        items = detect_unverified_evidence(sample_report_ir_with_claims)

        # One claim has no evidence
        assert len(items) == 1
        assert items[0].category == DisputeCategory.UNVERIFIED_EVIDENCE
        assert items[0].highlight_style == HighlightStyle.GRAY_ITALIC


# =============================================================================
# Integration Tests
# =============================================================================


class TestIdentifyDisputeSensitiveItems:
    """identify_dispute_sensitive_items integration tests."""

    def test_full_detection(
        self,
        sample_report_ir_with_adjustments,
        sample_deltas,
    ):
        """전체 탐지 파이프라인."""
        result = identify_dispute_sensitive_items(
            report_ir=sample_report_ir_with_adjustments,
            deltas=sample_deltas,
            ebitda_threshold_percent=Decimal("10"),
        )

        # Should find large adjustments and version changes
        assert len(result.items) >= 3
        assert result.high_risk_count >= 1
        assert DisputeCategory.LARGE_ADJUSTMENT in result.summary

    def test_detection_with_related_party(
        self,
        sample_report_ir_with_related_party,
    ):
        """관계사 거래 포함 탐지."""
        result = identify_dispute_sensitive_items(
            report_ir=sample_report_ir_with_related_party,
        )

        assert DisputeCategory.RELATED_PARTY in result.summary
        assert result.summary[DisputeCategory.RELATED_PARTY] >= 2

    def test_detection_with_claims(
        self,
        sample_report_ir_with_claims,
    ):
        """Claim 포함 탐지."""
        result = identify_dispute_sensitive_items(
            report_ir=sample_report_ir_with_claims,
        )

        # Should find unverified evidence and subjective judgments
        categories = set(result.summary.keys())
        assert DisputeCategory.UNVERIFIED_EVIDENCE in categories or DisputeCategory.SUBJECTIVE_JUDGMENT in categories

    def test_empty_report(self):
        """빈 리포트 처리."""
        result = identify_dispute_sensitive_items(ReportIR())

        assert len(result.items) == 0
        assert result.high_risk_count == 0

    def test_summary_aggregation(
        self,
        sample_report_ir_with_related_party,
        sample_deltas,
    ):
        """요약 집계 확인."""
        result = identify_dispute_sensitive_items(
            report_ir=sample_report_ir_with_related_party,
            deltas=sample_deltas,
        )

        # Summary should contain counts
        total_from_summary = sum(result.summary.values())
        assert total_from_summary == len(result.items)
