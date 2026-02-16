"""물류/운송 산업 변형 (A2).

> 마지막 수정: 2026-02-11 14:00:00
"""

from __future__ import annotations

from src.narrative_generator.prompts.industry_variants.base_variant import (
    IndustryConfig,
    IndustryVariant,
)


class LogisticsVariant(IndustryVariant):
    """물류/운송 산업 프롬프트 변형."""

    config = IndustryConfig(
        industry_id="logistics",
        industry_name_kr="물류/운송",
        industry_name_en="Logistics",
    )

    def get_industry_context(self) -> str:
        return (
            "물류/운송 산업의 IM 작성 시 다음 사항에 유의하십시오:\n"
            "- 물동량(톤km)과 운송 모드별(육상/해상/항공) 비중이 사업 구조를 결정합니다.\n"
            "- 3PL/4PL 비중과 콜드체인·특수화물 등 고부가 세그먼트가 마진에 직결됩니다.\n"
            "- 네트워크 밀도, 허브앤스포크 구조, 라스트마일 효율을 분석합니다.\n"
            "- 플릿 규모·연식·가동률과 CAPEX 사이클이 수익성 핵심 레버입니다.\n"
            "- 유가·환율 민감도와 계절성에 따른 매출 변동성을 평가합니다.\n"
        )

    def get_terminology_overrides(self) -> dict[str, str]:
        return {
            "매출액": "운송 매출 또는 물류 매출",
            "고객 수": "화주 수 또는 계약 거래처",
            "재고": "물동량(톤km) 또는 처리량",
            "시장점유율": "노선별 점유율 또는 물동량 M/S",
        }

    def get_emphasis_areas(self) -> list[str]:
        return [
            "정시 배송률(OTD) 및 클레임 비율",
            "톤km당 매출 및 공차율",
            "플릿 가동률 및 연비 효율",
            "창고 가동률 및 UPH(시간당 처리량)",
            "3PL/4PL 전환율 및 디지털화 수준",
            "네트워크 커버리지 및 허브 효율",
        ]
