"""DealProfileResolver — 거래구조/산업별 시트 ON/OFF 결정.

Deal 속성(거래구조, 산업, 엔티티 수, 데이터 가용성)에 따라
WorkbookBlueprint에 포함할 시트 목록을 결정한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SheetSpec:
    """시트 명세."""

    sheet_id: str               # 고유 식별자
    title_ko: str               # 한글 시트명
    title_en: str               # 영문 시트명
    category: str               # Index 카테고리
    required: bool = True       # 필수 여부
    condition: str = ""         # 조건 키 (빈 문자열이면 무조건 포함)


@dataclass
class DealProfile:
    """거래 프로파일."""

    deal_type: str = "general"              # "completion_accounts", "locked_box"
    structure: str = "single"               # "single", "multi_entity", "carve_out"
    industry: str = "general"               # "manufacturing", "tech", "healthcare", ...
    entity_count: int = 1
    has_foreign_subsidiary: bool = False
    has_backlog_data: bool = False
    has_interview_data: bool = False
    has_detailed_cost: bool = False          # 제조원가 데이터 여부
    currency: str = "KRW"


# ── 시트 카탈로그 ────────────────────────────────────────

_SHEET_CATALOG: list[SheetSpec] = [
    # 기본 (항상 포함)
    SheetSpec("index", "Index", "Index", "기본", required=True),
    SheetSpec("cover", "Cover & Summary", "Cover & Summary", "기본", required=True),

    # 재무제표
    SheetSpec("is_multi", "IS (Multi-period)", "IS (Multi-period)", "재무제표"),
    SheetSpec("bs_multi", "BS (Multi-period)", "BS (Multi-period)", "재무제표"),
    SheetSpec("cf_multi", "CF (Multi-period)", "CF (Multi-period)", "재무제표"),

    # 매출 분석
    SheetSpec("rev_customer", "거래처별 매출", "Revenue by Customer", "매출 분석"),
    SheetSpec("rev_product", "제품별 매출", "Revenue by Product", "매출 분석"),
    SheetSpec("rev_monthly", "월별 매출 추이", "Revenue Monthly Trend", "매출 분석"),
    SheetSpec("rev_concentration", "매출 집중도", "Revenue Concentration", "매출 분석"),

    # 비용 분석
    SheetSpec("cost_mfg", "제조원가", "Manufacturing Cost", "비용 분석",
              condition="has_detailed_cost"),
    SheetSpec("cost_sga", "판관비", "SG&A Breakdown", "비용 분석"),
    SheetSpec("cost_personnel", "인건비", "Personnel Analysis", "비용 분석"),

    # QoE
    SheetSpec("qoe_bridge", "QoE Bridge", "QoE Bridge", "QoE 분석"),
    SheetSpec("qoe_adjustments", "QoE 조정", "QoE Adjustments", "QoE 분석"),

    # NWC
    SheetSpec("nwc_definition", "NWC 분류", "NWC Definition", "NWC 분석"),
    SheetSpec("nwc_trend", "NWC 추이", "NWC Monthly Trend", "NWC 분석"),
    SheetSpec("nwc_peg", "NWC Peg", "NWC Peg Scenarios", "NWC 분석",
              condition="completion_accounts"),

    # Net Debt
    SheetSpec("debt_schedule", "Net Debt", "Net Debt Schedule", "Net Debt"),

    # FCF
    SheetSpec("fcf_bridge", "FCF Bridge", "FCF Bridge", "FCF 분석"),
    SheetSpec("capex_analysis", "CAPEX 분석", "CAPEX Analysis", "FCF 분석"),

    # 수주 (조건부)
    SheetSpec("backlog_summary", "수주잔액 Summary", "Order Backlog Summary", "수주 분석",
              condition="has_backlog_data"),
    SheetSpec("backlog_customer", "수주 거래처별", "Backlog by Customer", "수주 분석",
              condition="has_backlog_data"),
    SheetSpec("backlog_aging", "수주 Aging", "Backlog Aging", "수주 분석",
              condition="has_backlog_data"),
    SheetSpec("negative_margin", "역마진", "Negative Margin", "수주 분석",
              condition="has_backlog_data"),

    # 연결 (조건부)
    SheetSpec("entity_pl", "법인별 P&L", "Entity P&L Comparison", "연결 분석",
              condition="multi_entity"),
    SheetSpec("ic_elimination", "IC 제거", "IC Elimination", "연결 분석",
              condition="multi_entity"),
    SheetSpec("fx_summary", "환율 요약", "FX Rate Summary", "연결 분석",
              condition="has_foreign_subsidiary"),

    # 정성적 (조건부)
    SheetSpec("interview_notes", "인터뷰 노트", "Interview Notes", "정성적 분석",
              condition="has_interview_data"),
    SheetSpec("key_themes", "핵심 테마", "Key Themes", "정성적 분석",
              condition="has_interview_data"),

    # 코멘터리
    SheetSpec("commentary", "분석 코멘터리", "Analysis Commentary", "코멘터리"),

    # 검증
    SheetSpec("issues", "이슈", "Issues", "검증"),
    SheetSpec("checklist", "체크리스트", "FDD Checklist", "검증"),
    SheetSpec("validation", "교차검증", "Validation", "검증"),

    # Appendix
    SheetSpec("appendix_is", "IS 상세", "Detailed IS Schedule", "Appendix"),
    SheetSpec("appendix_bs", "BS 상세", "Detailed BS Schedule", "Appendix"),
    SheetSpec("appendix_gl", "GL Top 50", "GL Top 50", "Appendix"),
    SheetSpec("appendix_mapping", "매핑 요약", "Mapping Summary", "Appendix"),
    SheetSpec("appendix_anomaly", "이상치 상세", "Anomaly Detail", "Appendix"),
    SheetSpec("appendix_evidence", "근거 참조", "Evidence Index", "Appendix"),

    # Locked Box 전용
    SheetSpec("leakage_check", "Leakage Check", "Leakage Check", "NWC 분석",
              condition="locked_box"),
]

# 거래구조별 조건 맵
_CONDITION_MAP: dict[str, Any] = {
    "completion_accounts": lambda p: p.deal_type == "completion_accounts",
    "locked_box": lambda p: p.deal_type == "locked_box",
    "multi_entity": lambda p: p.entity_count >= 2 or p.structure == "multi_entity",
    "has_foreign_subsidiary": lambda p: p.has_foreign_subsidiary,
    "has_backlog_data": lambda p: p.has_backlog_data,
    "has_interview_data": lambda p: p.has_interview_data,
    "has_detailed_cost": lambda p: p.has_detailed_cost,
}


class DealProfileResolver:
    """거래 프로파일 기반 시트 결정기."""

    def __init__(
        self,
        profile: DealProfile,
        *,
        catalog: list[SheetSpec] | None = None,
        condition_map: dict[str, Any] | None = None,
    ):
        self._profile = profile
        self._catalog = catalog or _SHEET_CATALOG
        self._conditions = condition_map or _CONDITION_MAP

    def resolve_sheets(self) -> list[SheetSpec]:
        """프로파일에 따라 포함할 시트 목록을 결정한다."""
        result: list[SheetSpec] = []

        for spec in self._catalog:
            # 조건부 시트: condition 평가 우선
            if spec.condition:
                evaluator = self._conditions.get(spec.condition)
                if evaluator and evaluator(self._profile):
                    result.append(spec)
                continue

            # 무조건 포함 (required=True 또는 condition 없음)
            result.append(spec)

        return result

    def resolve_sheet_ids(self) -> list[str]:
        """포함할 시트 ID 목록."""
        return [s.sheet_id for s in self.resolve_sheets()]

    def is_sheet_included(self, sheet_id: str) -> bool:
        """특정 시트가 포함되는지 확인."""
        return sheet_id in self.resolve_sheet_ids()

    def get_summary(self) -> dict[str, Any]:
        """프로파일 + 시트 결정 요약."""
        sheets = self.resolve_sheets()
        categories = {}
        for s in sheets:
            categories.setdefault(s.category, []).append(s.sheet_id)

        return {
            "profile": {
                "deal_type": self._profile.deal_type,
                "structure": self._profile.structure,
                "industry": self._profile.industry,
                "entity_count": self._profile.entity_count,
            },
            "total_sheets": len(sheets),
            "categories": categories,
        }
