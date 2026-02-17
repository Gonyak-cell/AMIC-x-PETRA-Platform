"""FDD Korea Overlay Module — 한국 PE FDD 특수성 분석.

산업별 한국 규제, K-IFRS 조정, 세무 검토 사항을 집계한다.
IM의 korea/ 모듈 패턴을 FDD 도메인(EBITDA, NWC, Net Debt)에 맞게 재설계.
"""

from __future__ import annotations

from app.industry.korea.kifrs import KIFRS_NOTES
from app.industry.korea.models import FDDKoreaOverlayData
from app.industry.korea.regulatory import REGULATORY_ITEMS
from app.industry.korea.tax import TAX_ITEMS

__version__ = "0.1.0"


def get_fdd_korea_overlay_data(industry_id: str) -> FDDKoreaOverlayData | None:
    """산업별 FDD 한국 오버레이 데이터를 집계하여 반환한다.

    Args:
        industry_id: 산업 식별자 ("tech", "manufacturing", "healthcare",
                     "logistics", "financial_services").

    Returns:
        FDDKoreaOverlayData 인스턴스. 해당 산업 데이터가 없으면 None.
    """
    reg = [r for r in REGULATORY_ITEMS if industry_id in r.applicable_industries]
    kifrs = [k for k in KIFRS_NOTES if industry_id in k.applicable_industries]
    tax = [t for t in TAX_ITEMS if industry_id in t.applicable_industries]

    if not any([reg, kifrs, tax]):
        return None

    return FDDKoreaOverlayData(
        industry_id=industry_id,
        regulatory_items=reg,
        kifrs_notes=kifrs,
        tax_items=tax,
    )


__all__ = [
    "get_fdd_korea_overlay_data",
    "FDDKoreaOverlayData",
    "REGULATORY_ITEMS",
    "KIFRS_NOTES",
    "TAX_ITEMS",
]
