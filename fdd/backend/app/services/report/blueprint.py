"""WorkbookBlueprint — 시트 순서·조건·메타데이터 관리.

DealProfileResolver 결과를 받아 Excel WP 시트 생성 순서를 결정하고,
각 시트에 필요한 메타데이터(탭 색상, 카테고리, 스켈레톤 참조)를 제공한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.report.deal_profile import (
    DealProfile,
    DealProfileResolver,
    SheetSpec,
)


# ── 시트별 메타데이터 ──────────────────────────────────────

@dataclass(frozen=True)
class SheetBlueprint:
    """개별 시트 생성 청사진."""

    sheet_id: str
    title_ko: str
    title_en: str
    category: str
    tab_color: str = "1F4E79"       # 기본 Big 4 네이비
    skeleton_key: str | None = None  # YAML 스켈레톤 참조 키
    render_type: str = "table"       # "table" | "cover" | "index" | "commentary" | "checklist"
    order: int = 0                   # 정렬 순서


# ── 카테고리별 탭 색상 ─────────────────────────────────────

_CATEGORY_COLORS: dict[str, str] = {
    "기본": "1F4E79",
    "재무제표": "2E75B6",
    "매출 분석": "4472C4",
    "비용 분석": "ED7D31",
    "QoE 분석": "70AD47",
    "NWC 분석": "5B9BD5",
    "Net Debt": "FFC000",
    "FCF 분석": "9DC3E6",
    "수주 분석": "A9D18E",
    "연결 분석": "F4B183",
    "정성적 분석": "B4C7E7",
    "코멘터리": "D9E2F3",
    "검증": "FF0000",
    "Appendix": "BFBFBF",
}

# ── 시트별 렌더링 타입 매핑 ─────────────────────────────────

_RENDER_TYPES: dict[str, str] = {
    "index": "index",
    "cover": "cover",
    "commentary": "commentary",
    "checklist": "checklist",
    "validation": "checklist",
}

# ── 시트별 스켈레톤 매핑 ───────────────────────────────────

_SKELETON_MAP: dict[str, str] = {
    "is_multi": "is",
    "bs_multi": "bs",
    "cf_multi": "cf",
    "fcf_bridge": "fcf",
    "capex_analysis": "fcf",
    "cost_mfg": "cost",
    "cost_sga": "cost",
    "cost_personnel": "cost",
    "backlog_summary": "backlog",
    "backlog_customer": "backlog",
    "backlog_aging": "backlog",
    "negative_margin": "backlog",
    "entity_pl": "consolidation",
    "ic_elimination": "consolidation",
    "fx_summary": "consolidation",
}


class WorkbookBlueprint:
    """워크북 생성 청사진.

    DealProfileResolver 결과를 기반으로 시트 순서·메타데이터를 결정한다.
    """

    def __init__(
        self,
        profile: DealProfile,
        *,
        resolver: DealProfileResolver | None = None,
    ):
        self._profile = profile
        self._resolver = resolver or DealProfileResolver(profile)
        self._sheets: list[SheetBlueprint] | None = None

    @property
    def profile(self) -> DealProfile:
        return self._profile

    def build(self) -> list[SheetBlueprint]:
        """시트 청사진 목록을 생성한다."""
        if self._sheets is not None:
            return self._sheets

        resolved = self._resolver.resolve_sheets()
        blueprints: list[SheetBlueprint] = []

        for idx, spec in enumerate(resolved):
            bp = SheetBlueprint(
                sheet_id=spec.sheet_id,
                title_ko=spec.title_ko,
                title_en=spec.title_en,
                category=spec.category,
                tab_color=_CATEGORY_COLORS.get(spec.category, "1F4E79"),
                skeleton_key=_SKELETON_MAP.get(spec.sheet_id),
                render_type=_RENDER_TYPES.get(spec.sheet_id, "table"),
                order=idx,
            )
            blueprints.append(bp)

        self._sheets = blueprints
        return blueprints

    def get_sheet_ids(self) -> list[str]:
        """시트 ID 목록 (순서 보장)."""
        return [s.sheet_id for s in self.build()]

    def get_sheet(self, sheet_id: str) -> SheetBlueprint | None:
        """특정 시트 청사진 조회."""
        for s in self.build():
            if s.sheet_id == sheet_id:
                return s
        return None

    def get_sheets_by_category(self, category: str) -> list[SheetBlueprint]:
        """카테고리별 시트 목록."""
        return [s for s in self.build() if s.category == category]

    def get_categories(self) -> list[str]:
        """포함된 카테고리 목록 (순서 보장)."""
        seen: set[str] = set()
        result: list[str] = []
        for s in self.build():
            if s.category not in seen:
                seen.add(s.category)
                result.append(s.category)
        return result

    def total_sheets(self) -> int:
        """총 시트 수."""
        return len(self.build())

    def to_index_data(self) -> list[dict[str, Any]]:
        """Index 시트용 데이터 생성.

        Returns:
            카테고리별 시트 목록 (Index 시트 렌더링용)
        """
        categories: dict[str, list[dict[str, str]]] = {}
        for s in self.build():
            if s.sheet_id == "index":
                continue  # Index 자신은 제외
            cat_list = categories.setdefault(s.category, [])
            cat_list.append({
                "sheet_id": s.sheet_id,
                "title_ko": s.title_ko,
                "title_en": s.title_en,
            })

        return [
            {"category": cat, "sheets": sheets}
            for cat, sheets in categories.items()
        ]

    def get_summary(self) -> dict[str, Any]:
        """블루프린트 요약."""
        sheets = self.build()
        return {
            "deal_type": self._profile.deal_type,
            "structure": self._profile.structure,
            "industry": self._profile.industry,
            "total_sheets": len(sheets),
            "categories": self.get_categories(),
            "sheet_ids": self.get_sheet_ids(),
        }
