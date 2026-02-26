"""LDD 거래유형별 템플릿 레지스트리.

거래유형(deal_type)에 따라 적합한 LDD 보고서 템플릿을 반환한다.
deal_type 미지정 시 기존 DEFAULT_LDD_SECTIONS 폴백 (하위 호환).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.ralph.generators.ldd.templates.asset_acquisition import AssetAcquisitionTemplate
from app.ralph.generators.ldd.templates.base import LDDTemplate
from app.ralph.generators.ldd.templates.corporate_split import CorporateSplitTemplate
from app.ralph.generators.ldd.templates.ipo import IPOTemplate
from app.ralph.generators.ldd.templates.preferred_stock import PreferredStockTemplate
from app.ralph.generators.ldd.templates.real_estate import RealEstateTemplate
from app.ralph.generators.ldd.templates.stock_acquisition import StockAcquisitionTemplate

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """거래유형 → LDD 템플릿 매핑 레지스트리."""

    _templates: dict[str, type[LDDTemplate]] = {
        "STOCK_ACQUISITION": StockAcquisitionTemplate,
        "REAL_ESTATE": RealEstateTemplate,
        "IPO": IPOTemplate,
        "CORPORATE_SPLIT": CorporateSplitTemplate,
        "PREFERRED_STOCK": PreferredStockTemplate,
        "ASSET_ACQUISITION": AssetAcquisitionTemplate,
    }

    @classmethod
    def get(cls, deal_type: str) -> LDDTemplate | None:
        """거래유형에 해당하는 템플릿 인스턴스를 반환한다.

        Args:
            deal_type: LDDDealType enum 값 (예: "STOCK_ACQUISITION")

        Returns:
            LDDTemplate 인스턴스 또는 None (미등록 유형)
        """
        template_cls = cls._templates.get(deal_type)
        if template_cls is None:
            return None
        return template_cls()

    @classmethod
    def get_or_default(cls, deal_type: str) -> LDDTemplate | None:
        """거래유형 템플릿을 반환하되, 빈 문자열이면 None (DEFAULT_LDD_SECTIONS 폴백).

        서비스 계층에서 None이면 기존 DEFAULT_LDD_SECTIONS를 사용한다.
        """
        if not deal_type:
            return None
        template = cls.get(deal_type)
        if template is None:
            logger.warning("미등록 거래유형 '%s' — DEFAULT_LDD_SECTIONS 폴백", deal_type)
        return template

    @classmethod
    def get_sections_dict(cls, deal_type: str) -> list[dict] | None:
        """거래유형에 해당하는 섹션 dict 리스트를 반환한다.

        None이면 기존 DEFAULT_LDD_SECTIONS를 사용한다.
        """
        template = cls.get_or_default(deal_type)
        if template is None:
            return None
        return template.get_sections_dict()

    @classmethod
    def list_deal_types(cls) -> list[dict]:
        """등록된 거래유형 목록을 반환한다."""
        result = []
        for deal_type, template_cls in cls._templates.items():
            t = template_cls()
            result.append(
                {
                    "deal_type": deal_type,
                    "display_name": t.display_name,
                    "section_count": len(t.sections),
                    "item_count": t.get_item_count(),
                }
            )
        return result

    @classmethod
    def register(cls, deal_type: str, template_cls: type[LDDTemplate]) -> None:
        """커스텀 템플릿을 런타임에 등록한다."""
        cls._templates[deal_type] = template_cls
