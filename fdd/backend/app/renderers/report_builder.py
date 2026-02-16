"""Report Builder - Report IR 구성.

engines → report_builder → JSON IR → renderers (PPT/Word) 패턴의 중간 표현(IR)을 정의합니다.
모든 FDD 분석 결과를 표준화된 보고서 블록으로 변환합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any


class BlockType(str, Enum):
    """보고서 블록 타입."""

    COVER = "cover"
    KPI = "kpi"
    TABLE = "table"
    CHART = "chart"
    TEXT = "text"
    CLAIM = "claim"  # 서술문 + EvidenceLink
    ISSUE = "issue"  # 이슈 로그
    METHODOLOGY = "methodology"  # 분석 방법론
    SCOPE = "scope"  # 분석 범위/정의
    APPENDIX = "appendix"  # 부록


class ChartType(str, Enum):
    """차트 타입."""

    WATERFALL = "waterfall"
    BAR = "bar"
    LINE = "line"
    PIE = "pie"


class AlignType(str, Enum):
    """텍스트 정렬."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class RiskLevel(str, Enum):
    """리스크 등급."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Position & Size
# =============================================================================


@dataclass
class Position:
    """블록 위치 (인치 단위)."""

    x: float = 0.5
    y: float = 1.5


@dataclass
class Size:
    """블록 크기 (인치 단위)."""

    w: float = 9.0
    h: float = 4.0


# =============================================================================
# Block Dataclasses
# =============================================================================


@dataclass
class CoverBlock:
    """표지 블록.

    보고서 첫 슬라이드/페이지에 표시될 정보.
    """

    type: BlockType = field(default=BlockType.COVER, init=False)
    deal_name: str = ""
    deal_type: str = ""  # "Acquisition", "Carve-out", etc.
    target_name: str = ""
    date: date | None = None
    prepared_by: str = ""
    confidentiality: str = "CONFIDENTIAL"
    logo_base64: str | None = None
    position: Position | None = None


@dataclass
class KPIBlock:
    """KPI 콜아웃 블록.

    대형 숫자와 레이블로 핵심 지표 강조.
    """

    type: BlockType = field(default=BlockType.KPI, init=False)
    title: str = ""
    kpis: list[dict[str, Any]] = field(default_factory=list)
    # kpis: [{"label": "Adjusted EBITDA", "value": "12,500", "unit": "백만원", "trend": "up"}]
    columns: int = 3  # KPI 배치 컬럼 수
    position: Position | None = None
    size: Size | None = None


@dataclass
class TableColumn:
    """테이블 컬럼 정의."""

    key: str  # 데이터 필드명
    header: str  # 표시 헤더
    width: float = 1.5  # 인치
    align: AlignType = AlignType.RIGHT
    format: str | None = None  # number_formats 키 (currency, percentage 등)


@dataclass
class TableBlock:
    """테이블 블록.

    FDD 분석 결과 테이블 (QoE Bridge, NWC, Net Debt 등).
    """

    type: BlockType = field(default=BlockType.TABLE, init=False)
    title: str = ""
    columns: list[TableColumn] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    # rows: [{"category": "Revenue", "reported": "10000", "adjusted": "10500", ...}]
    footer_rows: list[dict[str, Any]] = field(default_factory=list)  # 합계/소계 행
    show_header: bool = True
    zebra_stripe: bool = True
    position: Position | None = None
    size: Size | None = None


@dataclass
class ChartData:
    """차트 데이터."""

    categories: list[str] = field(default_factory=list)  # X축 레이블
    values: list[Decimal | None] = field(default_factory=list)  # Y축 값
    series_name: str | None = None  # 시리즈 이름 (다중 시리즈용)


@dataclass
class ChartBlock:
    """차트 블록.

    PNG 이미지로 렌더링될 차트.
    Backend에서 Plotly로 생성 후 base64 인코딩하여 전달.
    """

    type: BlockType = field(default=BlockType.CHART, init=False)
    chart_type: ChartType = ChartType.WATERFALL
    title: str = ""
    data: ChartData | None = None
    image_base64: str | None = None  # 렌더링된 PNG (Backend에서 생성)
    position: Position | None = None
    size: Size | None = None


@dataclass
class TextBlock:
    """텍스트 블록.

    분석 코멘트, 주석, 리스크 설명 등.
    """

    type: BlockType = field(default=BlockType.TEXT, init=False)
    title: str | None = None
    content: str = ""
    bullet_points: list[str] = field(default_factory=list)
    risk_level: RiskLevel | None = None  # 리스크 표시 시
    highlight: bool = False
    position: Position | None = None
    size: Size | None = None


@dataclass
class EvidenceRef:
    """근거 참조 정보."""

    evidence_id: str  # EvidenceLink UUID
    source_type: str  # FILE, TB, GL, PDF
    source_id: str  # 원본 ID
    description: str = ""  # 설명


@dataclass
class ClaimBlock:
    """서술문 블록.

    FDD 분석 결과에 대한 서술문 + 근거 참조.
    모든 Claim은 EvidenceLink가 1개 이상 없으면 Unverified로 표시.
    """

    type: BlockType = field(default=BlockType.CLAIM, init=False)
    claim_text: str = ""  # 주장/발견 내용
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    verified: bool = False  # 근거 검증 여부 (자동 계산)
    risk_level: RiskLevel | None = None
    category: str | None = None  # QoE, NWC, Debt 등
    position: Position | None = None
    size: Size | None = None


@dataclass
class IssueItem:
    """이슈 항목."""

    issue_id: str
    category: str  # QoE_ADJUSTMENT, TIMING, DATA_QUALITY 등
    severity: str  # critical, high, medium, low
    title: str
    description: str = ""
    status: str = "open"  # open, resolved, dismissed
    recommendation: str = ""


@dataclass
class IssueBlock:
    """이슈 로그 블록.

    탐지된 이슈들의 목록.
    """

    type: BlockType = field(default=BlockType.ISSUE, init=False)
    title: str = "Issue Log"
    issues: list[IssueItem] = field(default_factory=list)
    show_resolved: bool = False
    position: Position | None = None
    size: Size | None = None


@dataclass
class MethodologyItem:
    """방법론 항목."""

    step: int
    title: str
    description: str = ""


@dataclass
class MethodologyBlock:
    """방법론 블록.

    FDD 분석 방법론 설명.
    """

    type: BlockType = field(default=BlockType.METHODOLOGY, init=False)
    title: str = "Methodology"
    introduction: str = ""
    steps: list[MethodologyItem] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    position: Position | None = None
    size: Size | None = None


@dataclass
class ScopeItem:
    """범위 항목."""

    category: str  # period, entity, currency, data_sources 등
    label: str
    value: str


@dataclass
class ScopeBlock:
    """범위/정의 블록.

    분석 범위 및 주요 정의.
    """

    type: BlockType = field(default=BlockType.SCOPE, init=False)
    title: str = "Scope & Definitions"
    scope_items: list[ScopeItem] = field(default_factory=list)
    definitions: dict[str, str] = field(default_factory=dict)  # 용어: 정의
    position: Position | None = None
    size: Size | None = None


@dataclass
class AppendixItem:
    """부록 항목."""

    title: str
    content: str = ""
    table_data: list[dict[str, Any]] | None = None
    reference_page: int | None = None


@dataclass
class AppendixBlock:
    """부록 블록.

    상세 데이터, 참고 자료 등.
    """

    type: BlockType = field(default=BlockType.APPENDIX, init=False)
    title: str = "Appendix"
    items: list[AppendixItem] = field(default_factory=list)
    position: Position | None = None
    size: Size | None = None


# =============================================================================
# Report IR
# =============================================================================


@dataclass
class ReportMetadata:
    """보고서 메타데이터."""

    deal_id: str = ""
    deal_name: str = ""
    generated_at: str = ""  # ISO 8601
    version: str = "1.0"
    engine_versions: dict[str, str] = field(default_factory=dict)
    # {"qoe": "0.1.0", "nwc": "0.1.0", "debt": "0.1.0"}


# Union type for all blocks
ReportBlock = (
    CoverBlock
    | KPIBlock
    | TableBlock
    | ChartBlock
    | TextBlock
    | ClaimBlock
    | IssueBlock
    | MethodologyBlock
    | ScopeBlock
    | AppendixBlock
)


@dataclass
class ReportIR:
    """Report Intermediate Representation.

    모든 FDD 분석 결과를 담는 중간 표현.
    PPT/Word 렌더러가 이 IR을 받아 최종 문서를 생성.

    Example:
        >>> ir = ReportIR(
        ...     metadata=ReportMetadata(deal_id="123", deal_name="Target Corp"),
        ...     sections=[
        ...         CoverBlock(deal_name="Target Corp", target_name="Target Co., Ltd."),
        ...         KPIBlock(title="Summary", kpis=[...]),
        ...         TableBlock(title="QoE Bridge", columns=[...], rows=[...]),
        ...         ChartBlock(chart_type=ChartType.WATERFALL, title="EBITDA Bridge", ...),
        ...     ]
        ... )
    """

    metadata: ReportMetadata = field(default_factory=ReportMetadata)
    sections: list[ReportBlock] = field(default_factory=list)


# =============================================================================
# Builder Functions
# =============================================================================


def build_qoe_table_block(
    title: str,
    bridge_data: list[dict[str, Any]],
    fiscal_years: list[str],
) -> TableBlock:
    """QoE Bridge 테이블 블록 생성.

    Args:
        title: 테이블 제목
        bridge_data: QoE Bridge 데이터 리스트
        fiscal_years: 표시할 회계연도 리스트

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(key="category", header="Category", width=2.5, align=AlignType.LEFT),
    ]
    for fy in fiscal_years:
        columns.append(
            TableColumn(
                key=fy, header=fy, width=1.2, align=AlignType.RIGHT, format="currency"
            )
        )

    return TableBlock(
        title=title,
        columns=columns,
        rows=bridge_data,
        zebra_stripe=True,
    )


def build_waterfall_chart_block(
    title: str,
    categories: list[str],
    values: list[Decimal | None],
    image_base64: str | None = None,
) -> ChartBlock:
    """워터폴 차트 블록 생성.

    Args:
        title: 차트 제목
        categories: X축 카테고리
        values: Y축 값
        image_base64: 렌더링된 PNG base64 (없으면 pptx-service에서 생성)

    Returns:
        ChartBlock 인스턴스
    """
    return ChartBlock(
        chart_type=ChartType.WATERFALL,
        title=title,
        data=ChartData(categories=categories, values=values),
        image_base64=image_base64,
        size=Size(w=9.0, h=4.5),
    )


def build_kpi_block(
    title: str,
    kpis: list[tuple[str, str, str | None]],
    columns: int = 3,
) -> KPIBlock:
    """KPI 콜아웃 블록 생성.

    Args:
        title: 블록 제목
        kpis: [(label, value, unit), ...] 튜플 리스트
        columns: 배치 컬럼 수

    Returns:
        KPIBlock 인스턴스
    """
    kpi_list = [
        {"label": label, "value": value, "unit": unit} for label, value, unit in kpis
    ]
    return KPIBlock(title=title, kpis=kpi_list, columns=columns)


def build_text_block(
    content: str,
    title: str | None = None,
    bullet_points: list[str] | None = None,
    risk_level: RiskLevel | None = None,
) -> TextBlock:
    """텍스트 블록 생성.

    Args:
        content: 본문 텍스트
        title: 블록 제목 (선택)
        bullet_points: 불릿 포인트 리스트 (선택)
        risk_level: 리스크 레벨 (선택)

    Returns:
        TextBlock 인스턴스
    """
    return TextBlock(
        title=title,
        content=content,
        bullet_points=bullet_points or [],
        risk_level=risk_level,
    )


def build_qoe_adjustments_table_block(
    title: str,
    adjustments: list[dict[str, Any]],
) -> TableBlock:
    """QoE 조정 상세 테이블 블록 생성.

    Args:
        title: 테이블 제목
        adjustments: 조정 항목 리스트
            [{"category": "Non-recurring", "description": "법적 합의금",
              "amount": "150", "status": "approved", "evidence": "GL-001"}]

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(key="category", header="Category", width=1.5, align=AlignType.LEFT),
        TableColumn(
            key="description", header="Description", width=3.0, align=AlignType.LEFT
        ),
        TableColumn(
            key="amount",
            header="Amount",
            width=1.2,
            align=AlignType.RIGHT,
            format="currency",
        ),
        TableColumn(key="status", header="Status", width=1.0, align=AlignType.CENTER),
        TableColumn(
            key="evidence", header="Evidence", width=1.0, align=AlignType.CENTER
        ),
    ]

    return TableBlock(
        title=title,
        columns=columns,
        rows=adjustments,
        zebra_stripe=True,
    )


def build_nwc_definition_table_block(
    title: str,
    line_items: list[dict[str, Any]],
) -> TableBlock:
    """NWC 정의 테이블 블록 생성.

    Args:
        title: 테이블 제목
        line_items: NWC 라인 아이템 리스트
            [{"account": "매출채권", "classification": "above_the_line",
              "balance": "5,000", "included": True}]

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(key="account", header="Account", width=2.5, align=AlignType.LEFT),
        TableColumn(
            key="classification",
            header="Classification",
            width=1.5,
            align=AlignType.CENTER,
        ),
        TableColumn(
            key="balance",
            header="Balance",
            width=1.5,
            align=AlignType.RIGHT,
            format="currency",
        ),
        TableColumn(
            key="included", header="Included", width=1.0, align=AlignType.CENTER
        ),
    ]

    return TableBlock(
        title=title,
        columns=columns,
        rows=line_items,
        zebra_stripe=True,
    )


def build_nwc_trend_table_block(
    title: str,
    trend_data: list[dict[str, Any]],
    months: list[str],
) -> TableBlock:
    """NWC 월별 트렌드 테이블 블록 생성.

    Args:
        title: 테이블 제목
        trend_data: 트렌드 데이터 리스트
            [{"item": "Current Assets", "2024-01": "1000", "2024-02": "1100", ...}]
        months: 표시할 월 리스트 ["2024-01", "2024-02", ...]

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(key="item", header="Item", width=2.0, align=AlignType.LEFT),
    ]
    for month in months:
        columns.append(
            TableColumn(
                key=month,
                header=month,
                width=1.0,
                align=AlignType.RIGHT,
                format="currency",
            )
        )

    return TableBlock(
        title=title,
        columns=columns,
        rows=trend_data,
        zebra_stripe=True,
    )


def build_nwc_peg_table_block(
    title: str,
    peg_scenarios: list[dict[str, Any]],
) -> TableBlock:
    """NWC Peg 시나리오 테이블 블록 생성.

    Args:
        title: 테이블 제목
        peg_scenarios: Peg 시나리오 리스트
            [{"method": "Average", "target_nwc": "3,500", "adjustment": "-500"}]

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(key="method", header="Peg Method", width=2.5, align=AlignType.LEFT),
        TableColumn(
            key="target_nwc",
            header="Target NWC",
            width=1.5,
            align=AlignType.RIGHT,
            format="currency",
        ),
        TableColumn(
            key="adjustment",
            header="Adjustment",
            width=1.5,
            align=AlignType.RIGHT,
            format="currency",
        ),
        TableColumn(key="notes", header="Notes", width=2.5, align=AlignType.LEFT),
    ]

    return TableBlock(
        title=title,
        columns=columns,
        rows=peg_scenarios,
        zebra_stripe=True,
    )


def build_net_debt_schedule_block(
    title: str,
    debt_items: list[dict[str, Any]],
    include_cash: bool = True,
) -> TableBlock:
    """Net Debt 스케줄 테이블 블록 생성.

    Args:
        title: 테이블 제목
        debt_items: Debt/Cash 항목 리스트
            [{"item": "Bank Loan", "type": "debt", "balance": "10,000",
              "debt_like": False, "include": True}]
        include_cash: Cash-like 항목 포함 여부

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(key="item", header="Item", width=2.5, align=AlignType.LEFT),
        TableColumn(key="type", header="Type", width=1.0, align=AlignType.CENTER),
        TableColumn(
            key="balance",
            header="Balance",
            width=1.5,
            align=AlignType.RIGHT,
            format="currency",
        ),
        TableColumn(
            key="adjustment",
            header="Adj.",
            width=1.0,
            align=AlignType.RIGHT,
            format="currency",
        ),
        TableColumn(
            key="adjusted",
            header="Adjusted",
            width=1.5,
            align=AlignType.RIGHT,
            format="currency",
        ),
    ]

    return TableBlock(
        title=title,
        columns=columns,
        rows=debt_items,
        zebra_stripe=True,
    )


def build_issue_summary_table_block(
    title: str,
    issues: list[dict[str, Any]],
) -> TableBlock:
    """이슈 요약 테이블 블록 생성.

    Args:
        title: 테이블 제목
        issues: 이슈 리스트
            [{"id": "ISS-001", "category": "QoE", "severity": "high",
              "title": "비경상 항목 미분류", "status": "open"}]

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(key="id", header="ID", width=0.8, align=AlignType.LEFT),
        TableColumn(
            key="category", header="Category", width=1.0, align=AlignType.CENTER
        ),
        TableColumn(
            key="severity", header="Severity", width=0.8, align=AlignType.CENTER
        ),
        TableColumn(key="title", header="Issue", width=4.0, align=AlignType.LEFT),
        TableColumn(key="status", header="Status", width=0.8, align=AlignType.CENTER),
    ]

    return TableBlock(
        title=title,
        columns=columns,
        rows=issues,
        zebra_stripe=True,
    )


def build_claim_block(
    claim_text: str,
    evidence_refs: list[tuple[str, str, str, str]] | None = None,
    risk_level: RiskLevel | None = None,
    category: str | None = None,
) -> ClaimBlock:
    """Claim(서술문) 블록 생성.

    Args:
        claim_text: 주장/발견 내용
        evidence_refs: 근거 참조 리스트 [(evidence_id, source_type, source_id, description), ...]
        risk_level: 리스크 레벨 (선택)
        category: 카테고리 (QoE, NWC, Debt 등)

    Returns:
        ClaimBlock 인스턴스
    """
    refs = []
    if evidence_refs:
        refs = [
            EvidenceRef(
                evidence_id=e[0],
                source_type=e[1],
                source_id=e[2],
                description=e[3] if len(e) > 3 else "",
            )
            for e in evidence_refs
        ]

    return ClaimBlock(
        claim_text=claim_text,
        evidence_refs=refs,
        verified=len(refs) > 0,
        risk_level=risk_level,
        category=category,
    )


def build_scope_block(
    scope_items: list[tuple[str, str, str]],
    definitions: dict[str, str] | None = None,
    title: str = "Scope & Definitions",
) -> ScopeBlock:
    """범위/정의 블록 생성.

    Args:
        scope_items: 범위 항목 [(category, label, value), ...]
        definitions: 용어 정의 딕셔너리
        title: 블록 제목

    Returns:
        ScopeBlock 인스턴스
    """
    items = [ScopeItem(category=s[0], label=s[1], value=s[2]) for s in scope_items]

    return ScopeBlock(
        title=title,
        scope_items=items,
        definitions=definitions or {},
    )


def build_methodology_block(
    steps: list[tuple[int, str, str]],
    introduction: str = "",
    limitations: list[str] | None = None,
    title: str = "Methodology",
) -> MethodologyBlock:
    """방법론 블록 생성.

    Args:
        steps: 방법론 단계 [(step_num, title, description), ...]
        introduction: 도입부 설명
        limitations: 제한 사항 리스트
        title: 블록 제목

    Returns:
        MethodologyBlock 인스턴스
    """
    method_steps = [
        MethodologyItem(step=s[0], title=s[1], description=s[2]) for s in steps
    ]

    return MethodologyBlock(
        title=title,
        introduction=introduction,
        steps=method_steps,
        limitations=limitations or [],
    )


def build_entity_breakdown_block(
    title: str,
    entity_rows: list[dict[str, Any]],
    entity_names: list[str],
) -> TableBlock:
    """엔티티별 금액 분석 테이블 블록 생성.

    Args:
        title: 테이블 제목
        entity_rows: 항목별 엔티티 금액 리스트
            [{"category": "Revenue", "entity_A": "1000", "entity_B": "500", "consolidated": "1500"}]
        entity_names: 엔티티명 리스트 (컬럼 순서와 일치)

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(key="category", header="Category", width=2.0, align=AlignType.LEFT),
    ]
    for name in entity_names:
        columns.append(
            TableColumn(
                key=name,
                header=name,
                width=1.2,
                align=AlignType.RIGHT,
                format="currency",
            )
        )
    columns.append(
        TableColumn(
            key="consolidated",
            header="Consolidated",
            width=1.5,
            align=AlignType.RIGHT,
            format="currency",
        )
    )

    return TableBlock(
        title=title,
        columns=columns,
        rows=entity_rows,
        zebra_stripe=True,
    )


def build_fx_summary_block(
    title: str,
    fx_rows: list[dict[str, Any]],
) -> TableBlock:
    """FX 환율 요약 테이블 블록 생성.

    Args:
        title: 테이블 제목
        fx_rows: 환율 항목 리스트
            [{"pair": "USD/KRW", "rate_type": "CLOSING", "rate": "1,320.00",
              "effective_date": "2025-12-31", "source": "MANUAL"}]

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(
            key="pair", header="Currency Pair", width=1.5, align=AlignType.LEFT
        ),
        TableColumn(key="rate_type", header="Type", width=1.2, align=AlignType.CENTER),
        TableColumn(key="rate", header="Rate", width=1.5, align=AlignType.RIGHT),
        TableColumn(
            key="effective_date", header="Date", width=1.2, align=AlignType.CENTER
        ),
        TableColumn(key="source", header="Source", width=1.0, align=AlignType.CENTER),
    ]

    return TableBlock(
        title=title,
        columns=columns,
        rows=fx_rows,
        zebra_stripe=True,
    )


def build_consolidation_block(
    title: str,
    elimination_rows: list[dict[str, Any]],
    minority_rows: list[dict[str, Any]] | None = None,
) -> TableBlock:
    """연결 조정(IC 제거 + 소수지분) 테이블 블록 생성.

    Args:
        title: 테이블 제목
        elimination_rows: IC 제거 항목 리스트
            [{"debit_entity": "A", "credit_entity": "B", "category": "Revenue",
              "amount": "500", "description": "Intercompany sales"}]
        minority_rows: 소수지분 항목 (선택)

    Returns:
        TableBlock 인스턴스
    """
    columns = [
        TableColumn(
            key="debit_entity", header="Debit Entity", width=1.5, align=AlignType.LEFT
        ),
        TableColumn(
            key="credit_entity", header="Credit Entity", width=1.5, align=AlignType.LEFT
        ),
        TableColumn(
            key="category", header="Category", width=1.5, align=AlignType.CENTER
        ),
        TableColumn(
            key="amount",
            header="Amount",
            width=1.5,
            align=AlignType.RIGHT,
            format="currency",
        ),
        TableColumn(
            key="description", header="Description", width=2.0, align=AlignType.LEFT
        ),
    ]

    rows = elimination_rows[:]
    if minority_rows:
        rows.extend(minority_rows)

    return TableBlock(
        title=title,
        columns=columns,
        rows=rows,
        zebra_stripe=True,
    )


def build_issue_block(
    issues: list[dict[str, Any]],
    title: str = "Issue Log",
    show_resolved: bool = False,
) -> IssueBlock:
    """이슈 로그 블록 생성.

    Args:
        issues: 이슈 리스트 [{"issue_id": "...", "category": "...", ...}]
        title: 블록 제목
        show_resolved: 해결된 이슈 표시 여부

    Returns:
        IssueBlock 인스턴스
    """
    issue_items = [
        IssueItem(
            issue_id=i.get("issue_id", ""),
            category=i.get("category", ""),
            severity=i.get("severity", "medium"),
            title=i.get("title", ""),
            description=i.get("description", ""),
            status=i.get("status", "open"),
            recommendation=i.get("recommendation", ""),
        )
        for i in issues
    ]

    return IssueBlock(
        title=title,
        issues=issue_items,
        show_resolved=show_resolved,
    )


# =============================================================================
# Serialization
# =============================================================================


def _serialize_decimal(obj: Any) -> Any:
    """Decimal을 문자열로 변환."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    return obj


def _dataclass_to_dict(obj: Any) -> dict[str, Any] | Any:
    """Dataclass를 딕셔너리로 재귀 변환."""
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            result[field_name] = _dataclass_to_dict(value)
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return _serialize_decimal(obj)


def report_ir_to_dict(ir: ReportIR) -> dict[str, Any]:
    """ReportIR을 JSON 직렬화 가능한 딕셔너리로 변환.

    Args:
        ir: ReportIR 인스턴스

    Returns:
        JSON 직렬화 가능한 딕셔너리
    """
    return _dataclass_to_dict(ir)
