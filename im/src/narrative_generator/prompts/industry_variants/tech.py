"""테크 산업 변형 (T-N12).

> 마지막 수정: 2026-02-10 11:52:29
"""

from __future__ import annotations

from src.narrative_generator.prompts.industry_variants.base_variant import (
    IndustryConfig,
    IndustryVariant,
)


class TechVariant(IndustryVariant):
    """테크/IT/SaaS 산업 프롬프트 변형."""

    config = IndustryConfig(
        industry_id="tech",
        industry_name_kr="테크/IT",
        industry_name_en="Technology",
    )

    def get_industry_context(self) -> str:
        return (
            "테크/IT 산업의 IM 작성 시 다음 사항에 유의하십시오:\n"
            "- SaaS/구독 모델의 경우 ARR, MRR, NRR 등 반복 매출 지표가 핵심입니다.\n"
            "- 고객 경제학(CAC, LTV, LTV/CAC 비율)으로 비즈니스 지속 가능성을 평가합니다.\n"
            "- 플랫폼 비즈니스의 경우 GMV, Take Rate, 네트워크 효과를 강조합니다.\n"
            "- R&D 투자 비중과 기술 경쟁력을 수익성 분석에 반영합니다.\n"
            "- 높은 매출 성장률과 규모의 경제에 따른 마진 개선 가능성에 주목합니다.\n"
        )

    def get_terminology_overrides(self) -> dict[str, str]:
        return {
            "매출액": "연간 반복 매출(ARR) 또는 매출액",
            "고객 수": "활성 사용자(MAU/DAU) 또는 유료 구독자",
            "시장점유율": "시장점유율 또는 플랫폼 침투율",
            "재고": "해당 없음 (소프트웨어/서비스)",
        }

    def get_emphasis_areas(self) -> list[str]:
        return [
            "ARR/MRR 성장률 및 NRR (순매출유지율)",
            "CAC (고객획득비용) 및 LTV (고객생애가치) 분석",
            "이탈률(Churn Rate) 트렌드",
            "Rule of 40 (성장률 + 영업이익률)",
            "R&D 투자 비중 및 기술 경쟁력",
            "플랫폼 네트워크 효과 및 진입장벽",
        ]
