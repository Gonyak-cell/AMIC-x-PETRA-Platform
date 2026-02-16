"""헬스케어 산업 변형 (T-N12).

> 마지막 수정: 2026-02-10 11:52:29
"""

from __future__ import annotations

from src.narrative_generator.prompts.industry_variants.base_variant import (
    IndustryConfig,
    IndustryVariant,
)


class HealthcareVariant(IndustryVariant):
    """헬스케어/바이오/제약 산업 프롬프트 변형."""

    config = IndustryConfig(
        industry_id="healthcare",
        industry_name_kr="헬스케어/바이오",
        industry_name_en="Healthcare",
    )

    def get_industry_context(self) -> str:
        return (
            "헬스케어/바이오 산업의 IM 작성 시 다음 사항에 유의하십시오:\n"
            "- R&D 파이프라인의 임상 단계별 성공 확률과 기대 매출을 분석합니다.\n"
            "- 규제 승인 현황(FDA/MFDS)과 허가 일정이 밸류에이션에 직접 영향합니다.\n"
            "- 특허 만료(Patent Cliff) 리스크와 후속 파이프라인을 함께 평가합니다.\n"
            "- 건강보험 급여 적용 여부와 약가 정책이 수익성에 핵심적입니다.\n"
            "- R&D 비용 자본화 정책에 따른 재무제표 해석 차이에 유의합니다.\n"
        )

    def get_terminology_overrides(self) -> dict[str, str]:
        return {
            "제품": "의약품/의료기기/진단키트",
            "R&D 비용": "연구개발비 (임상시험 비용 포함)",
            "시장": "치료 영역(Therapeutic Area) 시장",
            "고객": "의료기관/환자/보험사",
        }

    def get_emphasis_areas(self) -> list[str]:
        return [
            "R&D 파이프라인 (임상 단계별 분류: Phase I/II/III)",
            "규제 승인 현황 및 타임라인 (FDA, MFDS, EMA)",
            "특허 포트폴리오 및 만료 일정",
            "건강보험 급여 적용 및 약가 정책",
            "핵심 치료 영역의 시장 규모 및 미충족 수요",
            "라이선스 아웃/기술이전 실적 및 파이프라인 가치",
        ]
