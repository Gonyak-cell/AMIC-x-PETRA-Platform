"""Checklist to IMData Converter — 확정된 체크리스트 → IMDocumentData 변환.

> 마지막 수정: 2026-02-25 21:00:00

사용자가 확정한 체크리스트 아이템을 IMDocumentData 객체로 변환하여
IM 문서 생성 파이프라인에 공급한다.

카테고리별 변환 로직:
  - FINANCIAL → FinancialStatements (연도별 데이터)
  - COMPANY → CompanyOverview
  - MARKET → MarketData
  - DEAL → DealStructure
  - MANAGEMENT → ManagementTeam
  - SHAREHOLDERS → ShareholderStructure
"""

from __future__ import annotations

import logging
from typing import Any

from src.design_renderer.im_document import (
    CompanyOverview,
    DealStructure,
    FinancialStatements,
    GrowthStrategy,
    IMDocumentData,
    ManagementMember,
    MarketData,
    ShareholderInfo,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 재무 field_key → FinancialStatements 필드 매핑
# ---------------------------------------------------------------------------

_FS_FIELD_MAP: dict[str, str] = {
    "revenue": "revenue",
    "operating_income": "operating_income",
    "ebitda": "ebitda",
    "net_income": "net_income",
    "total_assets": "total_assets",
    "total_equity": "total_equity",
    "total_debt": "total_debt",
    "cash": "cash_and_equivalents",
    "cogs": "cost_of_goods_sold",
    "gross_profit": "gross_profit",
}


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


class ChecklistToIMDataConverter:
    """확정된 체크리스트 아이템을 IMDocumentData로 변환하는 변환기.

    Usage::

        converter = ChecklistToIMDataConverter()
        im_data = converter.convert(checklist_items, config={"im_style": "FULL"})
    """

    def convert(
        self,
        checklist_items: list[dict[str, Any]],
        config: dict[str, Any] | None = None,
    ) -> IMDocumentData:
        """체크리스트 아이템 목록을 IMDocumentData로 변환한다.

        Args:
            checklist_items: 체크리스트 아이템 dict 리스트.
                각 dict는 최소 category, field_key, effective_value를 포함해야 한다.
                선택적으로 fiscal_year, unit을 포함한다.
            config: 문서 설정 dict (im_style, project_name, company_name 등).

        Returns:
            IMDocumentData 인스턴스.
        """
        cfg = config or {}

        # 카테고리별 분류
        by_category: dict[str, list[dict[str, Any]]] = {}
        for item in checklist_items:
            category = item.get("category", "UNKNOWN")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(item)

        # 카테고리별 변환
        financial_statements = self._convert_financial(
            by_category.get("FINANCIAL", []),
        )
        company_overview = self._convert_company(
            by_category.get("COMPANY", []),
        )
        market_data = self._convert_market(
            by_category.get("MARKET", []),
        )
        deal_structure = self._convert_deal(
            by_category.get("DEAL", []),
        )
        management_team = self._convert_management(
            by_category.get("MANAGEMENT", []),
        )
        shareholders = self._convert_shareholders(
            by_category.get("SHAREHOLDERS", []),
        )

        # IMDocumentData 조립
        im_data = IMDocumentData(
            project_name=cfg.get("project_name", ""),
            company_name_kr=cfg.get("company_name", ""),
            company_name_en=cfg.get("company_name_en", ""),
            corp_code=cfg.get("corp_code", ""),
            financial_statements=financial_statements,
            company_overview=company_overview,
            market_data=market_data,
            deal_structure=deal_structure,
            management_team=management_team,
            shareholders=shareholders,
        )

        # im_style 설정
        im_style_str = cfg.get("im_style")
        if im_style_str:
            from src.design_renderer.im_document import IMStyle
            try:
                im_data.im_style = IMStyle(im_style_str)
            except ValueError:
                logger.warning("알 수 없는 im_style: %s", im_style_str)

        # industry 설정
        industry = cfg.get("industry", "")
        if industry:
            im_data.industry = industry

        logger.info(
            "체크리스트 → IMDocumentData 변환 완료: "
            "%d 아이템 → 재무 %d년, 회사정보 %d, 시장 %d, 딜 %d, "
            "경영진 %d, 주주 %d",
            len(checklist_items),
            len(financial_statements.years),
            1 if company_overview else 0,
            1 if market_data else 0,
            1 if deal_structure else 0,
            len(management_team),
            len(shareholders),
        )

        return im_data

    # ------------------------------------------------------------------
    # 카테고리별 변환 로직
    # ------------------------------------------------------------------

    def _convert_financial(
        self,
        items: list[dict[str, Any]],
    ) -> FinancialStatements:
        """FINANCIAL 카테고리 → FinancialStatements.

        field_key + fiscal_year 조합으로 연도별 dict를 구성한다.

        Args:
            items: FINANCIAL 카테고리 아이템 리스트.

        Returns:
            FinancialStatements 인스턴스.
        """
        fs = FinancialStatements()

        for item in items:
            field_key = item.get("field_key", "")
            value_str = item.get("effective_value") or item.get("confirmed_value") or item.get("extracted_value")
            fiscal_year = item.get("fiscal_year")

            if not value_str or not fiscal_year:
                continue

            fs_field = _FS_FIELD_MAP.get(field_key)
            if fs_field is None:
                # extra 필드에 저장
                year_str = str(fiscal_year)
                value = self._parse_number(value_str)
                if value is not None:
                    if field_key not in fs.extra:
                        fs.extra[field_key] = {}
                    fs.extra[field_key][year_str] = value
                continue

            # 표준 필드에 매핑
            year_str = str(fiscal_year)
            value = self._parse_number(value_str)
            if value is not None:
                target_dict: dict[str, float] = getattr(fs, fs_field)
                target_dict[year_str] = value

        return fs

    def _convert_company(
        self,
        items: list[dict[str, Any]],
    ) -> CompanyOverview | None:
        """COMPANY 카테고리 → CompanyOverview.

        Args:
            items: COMPANY 카테고리 아이템 리스트.

        Returns:
            CompanyOverview 인스턴스 또는 None (데이터 없을 때).
        """
        if not items:
            return None

        overview = CompanyOverview()
        field_map: dict[str, Any] = {}

        for item in items:
            field_key = item.get("field_key", "")
            value = item.get("effective_value") or item.get("confirmed_value") or item.get("extracted_value")
            if not value:
                continue
            field_map[field_key] = value

        # 매핑
        if "company_name" in field_map:
            overview.business_description = field_map.get("business_description", "")
        if "employee_count" in field_map:
            try:
                overview.employee_count = int(
                    self._parse_number(field_map["employee_count"]) or 0,
                )
            except (ValueError, TypeError):
                pass
        if "founded_date" in field_map:
            overview.established_date = field_map["founded_date"]
        if "headquarters" in field_map:
            overview.headquarters = field_map["headquarters"]
        if "business_model" in field_map:
            overview.business_model = field_map["business_model"]
        if "business_description" in field_map:
            overview.business_description = field_map["business_description"]
        if "company_description" in field_map and not overview.business_description:
            overview.business_description = field_map["company_description"]
        if "certifications" in field_map:
            overview.certifications = [
                c.strip() for c in field_map["certifications"].split(",")
                if c.strip()
            ]
        products_str = field_map.get("key_products") or field_map.get("main_products")
        if products_str:
            overview.key_products = [
                p.strip() for p in products_str.split(",")
                if p.strip()
            ]

        return overview

    def _convert_market(
        self,
        items: list[dict[str, Any]],
    ) -> MarketData | None:
        """MARKET 카테고리 → MarketData.

        Args:
            items: MARKET 카테고리 아이템 리스트.

        Returns:
            MarketData 인스턴스 또는 None.
        """
        if not items:
            return None

        market = MarketData()

        for item in items:
            field_key = item.get("field_key", "")
            value = item.get("effective_value") or item.get("confirmed_value") or item.get("extracted_value")
            if not value:
                continue

            if field_key == "tam":
                market.tam = self._parse_number(value)
            elif field_key == "sam":
                market.sam = self._parse_number(value)
            elif field_key == "som":
                market.som = self._parse_number(value)
            elif field_key == "market_growth_rate":
                market.market_growth_rate = self._parse_number(value)
            elif field_key == "market_cagr":
                market.market_cagr = self._parse_number(value)
            elif field_key == "market_position":
                market.market_position = value
            elif field_key in ("competitive_advantage", "competitive_advantages"):
                market.competitive_advantages = [
                    a.strip() for a in value.split(",") if a.strip()
                ]
            elif field_key == "key_competitors":
                market.competitors = [
                    {"name": c.strip()} for c in value.split(",") if c.strip()
                ]
            elif field_key == "industry_trends":
                market.industry_trends = [
                    t.strip() for t in value.split(",") if t.strip()
                ]
            elif field_key == "regulatory_notes":
                market.regulatory_notes = value

        return market

    def _convert_deal(
        self,
        items: list[dict[str, Any]],
    ) -> DealStructure | None:
        """DEAL 카테고리 → DealStructure.

        Args:
            items: DEAL 카테고리 아이템 리스트.

        Returns:
            DealStructure 인스턴스 또는 None.
        """
        if not items:
            return None

        deal = DealStructure()

        for item in items:
            field_key = item.get("field_key", "")
            value = item.get("effective_value") or item.get("confirmed_value") or item.get("extracted_value")
            if not value:
                continue

            if field_key == "seller":
                deal.seller = value
            elif field_key == "stake_pct":
                deal.stake_pct = self._parse_number(value)
            elif field_key == "deal_background":
                deal.deal_background = value
            elif field_key == "old_shares":
                deal.old_shares = self._parse_number(value)
            elif field_key == "new_shares":
                deal.new_shares = self._parse_number(value)
            elif field_key == "valuation_low":
                deal.valuation_low = self._parse_number(value)
            elif field_key == "valuation_high":
                deal.valuation_high = self._parse_number(value)
            elif field_key == "valuation_method":
                deal.valuation_method = value

        return deal

    def _convert_management(
        self,
        items: list[dict[str, Any]],
    ) -> list[ManagementMember]:
        """MANAGEMENT 카테고리 → ManagementTeam (ManagementMember 리스트).

        field_key 패턴: "management_{index}_{field}"
        예: "management_0_name", "management_0_title", "management_1_name"

        또는 단순 필드: "ceo_name" → ManagementMember(role="CEO")

        Args:
            items: MANAGEMENT 카테고리 아이템 리스트.

        Returns:
            ManagementMember 리스트.
        """
        members: list[ManagementMember] = []
        indexed: dict[int, dict[str, str]] = {}

        for item in items:
            field_key = item.get("field_key", "")
            value = item.get("effective_value") or item.get("confirmed_value") or item.get("extracted_value")
            if not value:
                continue

            # 인덱스 패턴 매칭: mgmt_{idx}_{field}
            parts = field_key.split("_")
            if len(parts) >= 3 and parts[0] == "mgmt":
                try:
                    idx = int(parts[1])
                    sub_field = "_".join(parts[2:])
                    if idx not in indexed:
                        indexed[idx] = {}
                    indexed[idx][sub_field] = value
                except ValueError:
                    pass

            # CEO 이름 단순 필드
            if field_key == "ceo_name":
                members.append(ManagementMember(
                    name=value,
                    role="CEO",
                    title="대표이사",
                ))

        # 인덱스 기반 멤버 변환
        for idx in sorted(indexed.keys()):
            data = indexed[idx]
            member = ManagementMember(
                name=data.get("name", ""),
                title=data.get("title", ""),
                role=data.get("role", ""),
                career=[
                    c.strip()
                    for c in data.get("career", "").split(",")
                    if c.strip()
                ],
            )
            if member.name:
                members.append(member)

        return members

    def _convert_shareholders(
        self,
        items: list[dict[str, Any]],
    ) -> list[ShareholderInfo]:
        """SHAREHOLDERS 카테고리 → ShareholderInfo 리스트.

        field_key 패턴: "shareholder_{index}_{field}"
        예: "shareholder_0_name", "shareholder_0_stake_pct"

        Args:
            items: SHAREHOLDERS 카테고리 아이템 리스트.

        Returns:
            ShareholderInfo 리스트.
        """
        indexed: dict[int, dict[str, str]] = {}

        for item in items:
            field_key = item.get("field_key", "")
            value = item.get("effective_value") or item.get("confirmed_value") or item.get("extracted_value")
            if not value:
                continue

            # 인덱스 패턴 매칭: sh_{idx}_{field}
            parts = field_key.split("_")
            if len(parts) >= 3 and parts[0] == "sh":
                try:
                    idx = int(parts[1])
                    sub_field = "_".join(parts[2:])
                    if idx not in indexed:
                        indexed[idx] = {}
                    indexed[idx][sub_field] = value
                except ValueError:
                    pass

        shareholders: list[ShareholderInfo] = []
        for idx in sorted(indexed.keys()):
            data = indexed[idx]
            info = ShareholderInfo(
                name=data.get("name", ""),
                stake_pct=self._parse_number(data.get("pct") or data.get("stake_pct") or "0") or 0.0,
                category=data.get("category", ""),
            )
            if data.get("share_count"):
                try:
                    info.share_count = int(
                        self._parse_number(data["share_count"]) or 0,
                    )
                except (ValueError, TypeError):
                    pass
            if info.name:
                shareholders.append(info)

        return shareholders

    # ------------------------------------------------------------------
    # 유틸리티
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_number(value: str | None) -> float | None:
        """문자열을 float로 파싱한다. 실패 시 None 반환.

        콤마, 공백, 단위("원", "백만원", "억원") 등을 제거하고 파싱한다.

        Args:
            value: 숫자 문자열.

        Returns:
            float 값 또는 None.
        """
        if value is None:
            return None

        # 정리
        cleaned = value.strip()
        cleaned = cleaned.replace(",", "").replace(" ", "")

        # 한국 단위 승수 (긴 접미사부터 매칭)
        _UNIT_MULTIPLIER: dict[str, float] = {
            "조원": 1_000_000_000_000,
            "억원": 100_000_000,
            "백만원": 1_000_000,
            "만원": 10_000,
            "천원": 1_000,
            "원": 1,
        }
        multiplier = 1.0
        for suffix, mult in _UNIT_MULTIPLIER.items():
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)]
                multiplier = mult
                break

        # 괄호 표기법: (100) → -100
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]

        try:
            return float(cleaned) * multiplier
        except ValueError:
            return None
