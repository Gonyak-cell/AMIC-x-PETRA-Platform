"""Korea Overlay Module — 한국 PE 특수성 자동 분석.

> 마지막 수정: 2026-02-11 15:00:00

산업별 한국 규제, K-IFRS 조정, 노동법, ESG 요구사항을 집계한다.
"""

from __future__ import annotations

from src.industry.korea.kifrs import KIFRS_NOTES
from src.industry.korea.labor_esg import ESG_REQUIREMENTS, LABOR_ITEMS
from src.industry.korea.models import KoreaOverlayData
from src.industry.korea.regulatory import REGULATORY_ITEMS

__version__ = "0.1.0"


def get_korea_overlay_data(industry_id: str) -> KoreaOverlayData | None:
    """산업별 한국 오버레이 데이터를 집계하여 반환한다.

    Args:
        industry_id: 산업 식별자 ("tech", "manufacturing", "healthcare", "logistics").

    Returns:
        KoreaOverlayData 인스턴스. 해당 산업 데이터가 없으면 None.
    """
    reg = [r for r in REGULATORY_ITEMS if industry_id in r.applicable_industries]
    kifrs = [k for k in KIFRS_NOTES if industry_id in k.applicable_industries]
    labor = [item for item in LABOR_ITEMS if industry_id in item.applicable_industries]
    esg = [e for e in ESG_REQUIREMENTS if industry_id in e.applicable_industries]

    if not any([reg, kifrs, labor, esg]):
        return None

    return KoreaOverlayData(
        industry_id=industry_id,
        regulatory_items=reg,
        kifrs_notes=kifrs,
        labor_items=labor,
        esg_requirements=esg,
    )


__all__ = [
    "get_korea_overlay_data",
    "KoreaOverlayData",
    "REGULATORY_ITEMS",
    "KIFRS_NOTES",
    "LABOR_ITEMS",
    "ESG_REQUIREMENTS",
]
