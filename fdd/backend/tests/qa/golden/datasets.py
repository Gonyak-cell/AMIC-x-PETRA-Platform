"""Golden 데이터셋 정의 — Sprint 8 Phase 4.

12-15개의 표준 테스트 케이스:
- QoE 관련: 3개 (정상, 불일치, 구조 오류)
- NWC 관련: 2개 (정상, 불일치)
- Net Debt 관련: 2개 (정상, 불일치)
- Evidence 관련: 2개 (100% 커버리지, 누락)
- Layout 관련: 2개 (정상, placeholder 누락)
- 복합: 3개 (전체 정상, 전체 오류, 빈 데이터)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class GoldenCaseType(str, Enum):
    """골든 케이스 유형."""

    QOE = "qoe"
    NWC = "nwc"
    DEBT = "debt"
    EVIDENCE = "evidence"
    LAYOUT = "layout"
    COMPOSITE = "composite"
    PERFORMANCE = "performance"


@dataclass
class GoldenCase:
    """골든 테스트 케이스.

    Attributes:
        case_id: 케이스 ID (예: "G-QOE-001")
        name: 케이스 이름
        case_type: 케이스 유형
        description: 설명
        input_ir: 입력 Report IR (실제 생성된 IR)
        expected_ir: 예상 Report IR (골든 기준)
        evidence_index: Evidence ID → 상세 정보 맵
        expected_passed: 예상 QA 통과 여부
        expected_warnings: 예상 경고 수
        expected_errors: 예상 오류 수
        expected_criticals: 예상 치명적 오류 수
        tags: 추가 태그 (필터링용)
    """

    case_id: str
    name: str
    case_type: GoldenCaseType
    description: str
    input_ir: dict[str, Any]
    expected_ir: dict[str, Any]
    evidence_index: dict[str, Any] = field(default_factory=dict)
    expected_passed: bool = True
    expected_warnings: int = 0
    expected_errors: int = 0
    expected_criticals: int = 0
    tags: list[str] = field(default_factory=list)


# =============================================================================
# QoE 관련 케이스
# =============================================================================

G_QOE_001 = GoldenCase(
    case_id="G-QOE-001",
    name="QoE Bridge 정상",
    case_type=GoldenCaseType.QOE,
    description="QoE Bridge 테이블 수치가 정확히 일치하는 정상 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-001", "deal_name": "Test Corp"},
        "sections": [
            {
                "type": "table",
                "title": "QoE Bridge",
                "rows": [
                    {"category": "Revenue", "fy2023": "10000000.0000", "fy2024": "12000000.0000"},
                    {"category": "COGS", "fy2023": "-6000000.0000", "fy2024": "-7200000.0000"},
                    {"category": "Gross Profit", "fy2023": "4000000.0000", "fy2024": "4800000.0000"},
                    {"category": "SG&A", "fy2023": "-2000000.0000", "fy2024": "-2400000.0000"},
                    {"category": "EBITDA", "fy2023": "2000000.0000", "fy2024": "2400000.0000"},
                ],
                "footer_rows": [
                    {"category": "Adjusted EBITDA", "fy2023": "2150000.0000", "fy2024": "2600000.0000"},
                ],
            }
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-001", "deal_name": "Test Corp"},
        "sections": [
            {
                "type": "table",
                "title": "QoE Bridge",
                "rows": [
                    {"category": "Revenue", "fy2023": "10000000.0000", "fy2024": "12000000.0000"},
                    {"category": "COGS", "fy2023": "-6000000.0000", "fy2024": "-7200000.0000"},
                    {"category": "Gross Profit", "fy2023": "4000000.0000", "fy2024": "4800000.0000"},
                    {"category": "SG&A", "fy2023": "-2000000.0000", "fy2024": "-2400000.0000"},
                    {"category": "EBITDA", "fy2023": "2000000.0000", "fy2024": "2400000.0000"},
                ],
                "footer_rows": [
                    {"category": "Adjusted EBITDA", "fy2023": "2150000.0000", "fy2024": "2600000.0000"},
                ],
            }
        ],
    },
    expected_passed=True,
    expected_errors=0,
    tags=["qoe", "exact_match"],
)

G_QOE_002 = GoldenCase(
    case_id="G-QOE-002",
    name="QoE Bridge 수치 불일치",
    case_type=GoldenCaseType.QOE,
    description="EBITDA 수치가 불일치하는 오류 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-002"},
        "sections": [
            {
                "type": "table",
                "title": "QoE Bridge",
                "rows": [
                    {"category": "Revenue", "fy2024": "10000000.0000"},
                    {"category": "EBITDA", "fy2024": "2000000.0000"},  # 실제
                ],
            }
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-002"},
        "sections": [
            {
                "type": "table",
                "title": "QoE Bridge",
                "rows": [
                    {"category": "Revenue", "fy2024": "10000000.0000"},
                    {"category": "EBITDA", "fy2024": "2500000.0000"},  # 예상 (500K 차이)
                ],
            }
        ],
    },
    expected_passed=False,
    expected_errors=1,
    tags=["qoe", "numeric_diff"],
)

G_QOE_003 = GoldenCase(
    case_id="G-QOE-003",
    name="QoE 행 개수 불일치",
    case_type=GoldenCaseType.QOE,
    description="예상보다 행이 적은 구조 오류 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-003"},
        "sections": [
            {
                "type": "table",
                "title": "QoE Adjustments",
                "rows": [
                    {"description": "Legal settlement", "amount": "150000.0000"},
                    # 누락: Restructuring
                ],
            }
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-003"},
        "sections": [
            {
                "type": "table",
                "title": "QoE Adjustments",
                "rows": [
                    {"description": "Legal settlement", "amount": "150000.0000"},
                    {"description": "Restructuring", "amount": "200000.0000"},
                ],
            }
        ],
    },
    expected_passed=False,
    expected_errors=1,  # 구조 불일치
    tags=["qoe", "structure_mismatch"],
)


# =============================================================================
# NWC 관련 케이스
# =============================================================================

G_NWC_001 = GoldenCase(
    case_id="G-NWC-001",
    name="NWC Definition 정상",
    case_type=GoldenCaseType.NWC,
    description="NWC 정의 테이블이 정확히 일치하는 정상 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-nwc-001"},
        "sections": [
            {
                "type": "table",
                "title": "NWC Definition",
                "rows": [
                    {"account": "Accounts Receivable", "balance": "5000000.0000"},
                    {"account": "Inventory", "balance": "3000000.0000"},
                    {"account": "Accounts Payable", "balance": "-2500000.0000"},
                    {"account": "Accrued Expenses", "balance": "-1000000.0000"},
                ],
                "footer_rows": [
                    {"account": "Net Working Capital", "balance": "4500000.0000"},
                ],
            }
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-nwc-001"},
        "sections": [
            {
                "type": "table",
                "title": "NWC Definition",
                "rows": [
                    {"account": "Accounts Receivable", "balance": "5000000.0000"},
                    {"account": "Inventory", "balance": "3000000.0000"},
                    {"account": "Accounts Payable", "balance": "-2500000.0000"},
                    {"account": "Accrued Expenses", "balance": "-1000000.0000"},
                ],
                "footer_rows": [
                    {"account": "Net Working Capital", "balance": "4500000.0000"},
                ],
            }
        ],
    },
    expected_passed=True,
    expected_errors=0,
    tags=["nwc", "exact_match"],
)

G_NWC_002 = GoldenCase(
    case_id="G-NWC-002",
    name="NWC Peg 불일치",
    case_type=GoldenCaseType.NWC,
    description="NWC Peg Target 수치가 불일치하는 오류 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-nwc-002"},
        "sections": [
            {
                "type": "table",
                "title": "NWC Peg Analysis",
                "rows": [
                    {"method": "Average", "target_nwc": "4200000.0000"},  # 실제
                    {"method": "Closing", "target_nwc": "4500000.0000"},
                ],
            }
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-nwc-002"},
        "sections": [
            {
                "type": "table",
                "title": "NWC Peg Analysis",
                "rows": [
                    {"method": "Average", "target_nwc": "4000000.0000"},  # 예상 (200K 차이)
                    {"method": "Closing", "target_nwc": "4500000.0000"},
                ],
            }
        ],
    },
    expected_passed=False,
    expected_errors=1,
    tags=["nwc", "numeric_diff"],
)


# =============================================================================
# Net Debt 관련 케이스
# =============================================================================

G_DEBT_001 = GoldenCase(
    case_id="G-DEBT-001",
    name="Net Debt Schedule 정상",
    case_type=GoldenCaseType.DEBT,
    description="Net Debt 스케줄이 정확히 일치하는 정상 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-debt-001"},
        "sections": [
            {
                "type": "table",
                "title": "Net Debt Schedule",
                "rows": [
                    {"item": "Bank Loan A", "balance": "5000000.0000"},
                    {"item": "Bank Loan B", "balance": "3000000.0000"},
                    {"item": "Cash", "balance": "-1500000.0000"},
                ],
                "footer_rows": [
                    {"item": "Net Debt", "balance": "6500000.0000"},
                ],
            }
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-debt-001"},
        "sections": [
            {
                "type": "table",
                "title": "Net Debt Schedule",
                "rows": [
                    {"item": "Bank Loan A", "balance": "5000000.0000"},
                    {"item": "Bank Loan B", "balance": "3000000.0000"},
                    {"item": "Cash", "balance": "-1500000.0000"},
                ],
                "footer_rows": [
                    {"item": "Net Debt", "balance": "6500000.0000"},
                ],
            }
        ],
    },
    expected_passed=True,
    expected_errors=0,
    tags=["debt", "exact_match"],
)

G_DEBT_002 = GoldenCase(
    case_id="G-DEBT-002",
    name="Net Debt 불일치",
    case_type=GoldenCaseType.DEBT,
    description="Net Debt 합계가 불일치하는 오류 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-debt-002"},
        "sections": [
            {
                "type": "table",
                "title": "Net Debt Schedule",
                "rows": [],
                "footer_rows": [
                    {"item": "Net Debt", "balance": "7000000.0000"},  # 실제
                ],
            }
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-debt-002"},
        "sections": [
            {
                "type": "table",
                "title": "Net Debt Schedule",
                "rows": [],
                "footer_rows": [
                    {"item": "Net Debt", "balance": "6500000.0000"},  # 예상 (500K 차이)
                ],
            }
        ],
    },
    expected_passed=False,
    expected_errors=1,
    tags=["debt", "numeric_diff"],
)


# =============================================================================
# Evidence 관련 케이스
# =============================================================================

G_EVIDENCE_001 = GoldenCase(
    case_id="G-EVIDENCE-001",
    name="Evidence 100% 커버리지",
    case_type=GoldenCaseType.EVIDENCE,
    description="모든 ClaimBlock에 Evidence가 있는 정상 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-ev-001"},
        "sections": [
            {
                "type": "claim",
                "claim_text": "FY2024 매출은 120억원으로 전년 대비 20% 증가",
                "evidence_refs": [
                    {"evidence_id": "ev-001", "source_type": "TB", "source_id": "TB-2024-001"},
                ],
                "verified": True,
            },
            {
                "type": "claim",
                "claim_text": "비경상 법적 합의금 1.5억원 조정",
                "evidence_refs": [
                    {"evidence_id": "ev-002", "source_type": "GL", "source_id": "GL-2024-1523"},
                ],
                "verified": True,
            },
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-ev-001"},
        "sections": [
            {
                "type": "claim",
                "claim_text": "FY2024 매출은 120억원으로 전년 대비 20% 증가",
                "evidence_refs": [
                    {"evidence_id": "ev-001", "source_type": "TB", "source_id": "TB-2024-001"},
                ],
                "verified": True,
            },
            {
                "type": "claim",
                "claim_text": "비경상 법적 합의금 1.5억원 조정",
                "evidence_refs": [
                    {"evidence_id": "ev-002", "source_type": "GL", "source_id": "GL-2024-1523"},
                ],
                "verified": True,
            },
        ],
    },
    evidence_index={
        "ev-001": {"source_type": "TB", "source_id": "TB-2024-001", "valid": True},
        "ev-002": {"source_type": "GL", "source_id": "GL-2024-1523", "valid": True},
    },
    expected_passed=True,
    expected_errors=0,
    tags=["evidence", "100_coverage"],
)

G_EVIDENCE_002 = GoldenCase(
    case_id="G-EVIDENCE-002",
    name="Evidence 누락 (verified=True)",
    case_type=GoldenCaseType.EVIDENCE,
    description="verified=True인 ClaimBlock에 Evidence가 없는 오류 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-ev-002"},
        "sections": [
            {
                "type": "claim",
                "claim_text": "FY2024 EBITDA 마진은 업계 평균 대비 높음",
                "evidence_refs": [],  # Evidence 누락!
                "verified": True,  # verified=True인데 evidence 없음 → ERROR
            },
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-ev-002"},
        "sections": [
            {
                "type": "claim",
                "claim_text": "FY2024 EBITDA 마진은 업계 평균 대비 높음",
                "evidence_refs": [
                    {"evidence_id": "ev-003", "source_type": "REPORT", "source_id": "INDUSTRY-2024"},
                ],
                "verified": True,
            },
        ],
    },
    evidence_index={},
    expected_passed=False,
    expected_errors=1,  # Evidence QA에서 verified=True + empty refs → ERROR
    tags=["evidence", "missing"],
)


# =============================================================================
# Layout 관련 케이스
# =============================================================================

G_LAYOUT_001 = GoldenCase(
    case_id="G-LAYOUT-001",
    name="Layout 정상",
    case_type=GoldenCaseType.LAYOUT,
    description="모든 placeholder가 치환되고 overflow 없는 정상 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-layout-001", "deal_name": "ABC Corp"},
        "sections": [
            {
                "type": "cover",
                "deal_name": "ABC Corp",
                "target_name": "ABC Co., Ltd.",
                "date": "2024-12-31",
                "prepared_by": "FDD Team",
            },
            {
                "type": "text",
                "title": "Executive Summary",
                "content": "ABC Corp의 FY2024 실적은 양호합니다.",
            },
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-layout-001", "deal_name": "ABC Corp"},
        "sections": [
            {
                "type": "cover",
                "deal_name": "ABC Corp",
                "target_name": "ABC Co., Ltd.",
                "date": "2024-12-31",
                "prepared_by": "FDD Team",
            },
            {
                "type": "text",
                "title": "Executive Summary",
                "content": "ABC Corp의 FY2024 실적은 양호합니다.",
            },
        ],
    },
    expected_passed=True,
    expected_errors=0,
    tags=["layout", "no_issues"],
)

G_LAYOUT_002 = GoldenCase(
    case_id="G-LAYOUT-002",
    name="Placeholder 미치환",
    case_type=GoldenCaseType.LAYOUT,
    description="{{placeholder}}가 치환되지 않은 경고 케이스 (WARNING)",
    input_ir={
        "metadata": {"deal_id": "deal-layout-002", "deal_name": "{{deal_name}}"},  # 미치환!
        "sections": [
            {
                "type": "cover",
                "deal_name": "{{deal_name}}",  # 미치환!
                "target_name": "XYZ Corp",
                "date": "{{report_date}}",  # 미치환!
            },
            {
                "type": "text",
                "content": "분석 기간: {{period_start}} ~ {{period_end}}",  # 미치환!
            },
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-layout-002", "deal_name": "XYZ Corp"},
        "sections": [
            {
                "type": "cover",
                "deal_name": "XYZ Corp",
                "target_name": "XYZ Corp",
                "date": "2024-12-31",
            },
            {
                "type": "text",
                "content": "분석 기간: 2024-01-01 ~ 2024-12-31",
            },
        ],
    },
    expected_passed=False,  # Layout QA에서 WARNING 발생, 테스트에서 별도 확인
    expected_warnings=5,  # 5개의 placeholder 미치환 (metadata 1 + cover 2 + text 2)
    expected_errors=0,  # placeholder는 WARNING, ERROR 아님
    tags=["layout", "placeholder_missing"],
)


# =============================================================================
# 복합 케이스
# =============================================================================

G_COMPOSITE_001 = GoldenCase(
    case_id="G-COMPOSITE-001",
    name="전체 Report IR 정상",
    case_type=GoldenCaseType.COMPOSITE,
    description="QoE + NWC + Debt + Claims 모두 포함된 완전한 정상 케이스",
    input_ir={
        "metadata": {
            "deal_id": "deal-full-001",
            "deal_name": "Full Test Corp",
            "generated_at": "2024-12-31T12:00:00Z",
        },
        "sections": [
            {
                "type": "cover",
                "deal_name": "Full Test Corp",
                "target_name": "Full Test Co., Ltd.",
            },
            {
                "type": "kpi",
                "title": "Key Metrics",
                "kpis": [
                    {"label": "Revenue", "value": "120억", "unit": "원"},
                    {"label": "Adj. EBITDA", "value": "26억", "unit": "원"},
                    {"label": "Net Debt", "value": "65억", "unit": "원"},
                ],
            },
            {
                "type": "table",
                "title": "QoE Bridge",
                "rows": [
                    {"category": "Reported EBITDA", "fy2024": "2400000.0000"},
                    {"category": "Adjustments", "fy2024": "200000.0000"},
                    {"category": "Adjusted EBITDA", "fy2024": "2600000.0000"},
                ],
            },
            {
                "type": "table",
                "title": "NWC Summary",
                "rows": [
                    {"item": "Current Assets", "balance": "8000000.0000"},
                    {"item": "Current Liabilities", "balance": "-3500000.0000"},
                    {"item": "NWC", "balance": "4500000.0000"},
                ],
            },
            {
                "type": "table",
                "title": "Net Debt",
                "rows": [
                    {"item": "Total Debt", "balance": "8000000.0000"},
                    {"item": "Cash", "balance": "-1500000.0000"},
                    {"item": "Net Debt", "balance": "6500000.0000"},
                ],
            },
            {
                "type": "claim",
                "claim_text": "조정 EBITDA는 26억원으로 확인됨",
                "evidence_refs": [
                    {"evidence_id": "ev-full-001", "source_type": "TB", "source_id": "TB-2024"},
                ],
                "verified": True,
            },
        ],
    },
    expected_ir={
        "metadata": {
            "deal_id": "deal-full-001",
            "deal_name": "Full Test Corp",
            "generated_at": "2024-12-31T12:00:00Z",
        },
        "sections": [
            {
                "type": "cover",
                "deal_name": "Full Test Corp",
                "target_name": "Full Test Co., Ltd.",
            },
            {
                "type": "kpi",
                "title": "Key Metrics",
                "kpis": [
                    {"label": "Revenue", "value": "120억", "unit": "원"},
                    {"label": "Adj. EBITDA", "value": "26억", "unit": "원"},
                    {"label": "Net Debt", "value": "65억", "unit": "원"},
                ],
            },
            {
                "type": "table",
                "title": "QoE Bridge",
                "rows": [
                    {"category": "Reported EBITDA", "fy2024": "2400000.0000"},
                    {"category": "Adjustments", "fy2024": "200000.0000"},
                    {"category": "Adjusted EBITDA", "fy2024": "2600000.0000"},
                ],
            },
            {
                "type": "table",
                "title": "NWC Summary",
                "rows": [
                    {"item": "Current Assets", "balance": "8000000.0000"},
                    {"item": "Current Liabilities", "balance": "-3500000.0000"},
                    {"item": "NWC", "balance": "4500000.0000"},
                ],
            },
            {
                "type": "table",
                "title": "Net Debt",
                "rows": [
                    {"item": "Total Debt", "balance": "8000000.0000"},
                    {"item": "Cash", "balance": "-1500000.0000"},
                    {"item": "Net Debt", "balance": "6500000.0000"},
                ],
            },
            {
                "type": "claim",
                "claim_text": "조정 EBITDA는 26억원으로 확인됨",
                "evidence_refs": [
                    {"evidence_id": "ev-full-001", "source_type": "TB", "source_id": "TB-2024"},
                ],
                "verified": True,
            },
        ],
    },
    evidence_index={
        "ev-full-001": {"source_type": "TB", "source_id": "TB-2024", "valid": True},
    },
    expected_passed=True,
    expected_errors=0,
    tags=["composite", "full_report"],
)

G_COMPOSITE_002 = GoldenCase(
    case_id="G-COMPOSITE-002",
    name="복합 오류 케이스",
    case_type=GoldenCaseType.COMPOSITE,
    description="수치 불일치 + Evidence 누락 + Placeholder 미치환 복합 오류",
    input_ir={
        "metadata": {"deal_id": "deal-err-001", "deal_name": "{{company_name}}"},  # placeholder
        "sections": [
            {
                "type": "table",
                "title": "QoE Bridge",
                "rows": [
                    {"category": "EBITDA", "fy2024": "2000000.0000"},  # 불일치
                ],
            },
            {
                "type": "claim",
                "claim_text": "검토 결과 이상 없음",
                "evidence_refs": [],  # Evidence 누락
                "verified": False,
            },
        ],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-err-001", "deal_name": "Error Corp"},
        "sections": [
            {
                "type": "table",
                "title": "QoE Bridge",
                "rows": [
                    {"category": "EBITDA", "fy2024": "2500000.0000"},  # 예상
                ],
            },
            {
                "type": "claim",
                "claim_text": "검토 결과 이상 없음",
                "evidence_refs": [
                    {"evidence_id": "ev-err-001", "source_type": "REVIEW", "source_id": "REV-001"},
                ],
                "verified": True,
            },
        ],
    },
    expected_passed=False,
    expected_errors=2,  # 수치 불일치 + Evidence 누락 (placeholder는 layout QA에서 별도 검출)
    tags=["composite", "multiple_errors"],
)

G_COMPOSITE_003 = GoldenCase(
    case_id="G-COMPOSITE-003",
    name="빈 데이터 케이스",
    case_type=GoldenCaseType.COMPOSITE,
    description="섹션이 비어있는 경계 케이스",
    input_ir={
        "metadata": {"deal_id": "deal-empty-001"},
        "sections": [],
    },
    expected_ir={
        "metadata": {"deal_id": "deal-empty-001"},
        "sections": [],
    },
    expected_passed=True,
    expected_errors=0,
    tags=["composite", "empty"],
)


# =============================================================================
# 전체 데이터셋
# =============================================================================

GOLDEN_DATASETS: list[GoldenCase] = [
    # QoE (3개)
    G_QOE_001,
    G_QOE_002,
    G_QOE_003,
    # NWC (2개)
    G_NWC_001,
    G_NWC_002,
    # Debt (2개)
    G_DEBT_001,
    G_DEBT_002,
    # Evidence (2개)
    G_EVIDENCE_001,
    G_EVIDENCE_002,
    # Layout (2개)
    G_LAYOUT_001,
    G_LAYOUT_002,
    # Composite (3개)
    G_COMPOSITE_001,
    G_COMPOSITE_002,
    G_COMPOSITE_003,
]


def get_cases_by_type(case_type: GoldenCaseType) -> list[GoldenCase]:
    """유형별 케이스 필터링.

    Args:
        case_type: 케이스 유형

    Returns:
        해당 유형의 케이스 목록
    """
    return [c for c in GOLDEN_DATASETS if c.case_type == case_type]


def get_cases_by_tag(tag: str) -> list[GoldenCase]:
    """태그별 케이스 필터링.

    Args:
        tag: 태그

    Returns:
        해당 태그의 케이스 목록
    """
    return [c for c in GOLDEN_DATASETS if tag in c.tags]


def get_passing_cases() -> list[GoldenCase]:
    """통과 예상 케이스만 필터링."""
    return [c for c in GOLDEN_DATASETS if c.expected_passed]


def get_failing_cases() -> list[GoldenCase]:
    """실패 예상 케이스만 필터링."""
    return [c for c in GOLDEN_DATASETS if not c.expected_passed]
