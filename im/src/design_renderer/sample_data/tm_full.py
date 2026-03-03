"""TM(Teaser Memorandum) 100% 완성 데이터 — get_full_tm_data().

25 슬라이드 이상의 TM PPTX 생성이 가능한 수준의 완전한 IMDocumentData를 반환한다.
IM FULL과 동일한 회사(넥스트테크) 데이터를 기반으로 하되,
im_style=TEASER, TM 전용 내러티브(마케팅 톤), Pro-Forma 전망 데이터를 포함한다.
"""

from __future__ import annotations

from src.design_renderer.im_document import IMDocumentData, IMStyle

from .company import (
    build_company_overview,
    build_contacts,
    build_deal_structure,
    build_growth_strategy,
    build_management_team,
    build_market_data,
    build_shareholders,
)
from .financials import (
    build_charts,
    build_financial_statements,
    build_segment_revenue,
    build_source_citations,
    build_valuation_data,
)
from .narratives_tm import build_tm_narratives
from .proforma import build_proforma_charts


def get_full_tm_data() -> IMDocumentData:
    """100% 완성된 TM(TEASER) IMDocumentData를 반환한다.

    IM FULL 데이터와 동일한 회사 데이터를 재사용하되:
    - im_style = TEASER (4그룹 고정 구조)
    - narratives = TM 전용 마케팅 톤 8개 섹션
    - charts = 기존 차트 + Pro-Forma 전망 차트 병합
    - 파생 지표(derived_metrics)가 이미 계산된 상태
    """
    # ── 차트 병합 (기존 IM 차트 + Pro-Forma 전망 차트) ──
    base_charts = build_charts()
    proforma_charts = build_proforma_charts()
    merged_charts = {**base_charts, **proforma_charts}

    data = IMDocumentData(
        # ── 기본 정보 ──
        project_name="Project NEXUS",
        company_name_kr="넥스트테크",
        company_name_en="NextTech Co., Ltd.",
        corp_code="00987654",
        website_url="https://www.nexttech.co.kr",
        date="2026-03-01",
        # ── 섹션 구성 (TEASER 프리셋 자동 적용) ──
        im_style=IMStyle.TEASER,
        # ── 재무 데이터 (기존 5년 실적) ──
        financial_statements=build_financial_statements(),
        segment_revenue=build_segment_revenue(),
        key_customers=[
            "삼성전자",
            "현대자동차",
            "KB금융지주",
            "신한금융지주",
            "SK하이닉스",
        ],
        # ── 딜 구조 ──
        deal_structure=build_deal_structure(),
        # ── 밸류에이션 ──
        valuation_data=build_valuation_data(),
        # ── 정성 데이터 ──
        company_overview=build_company_overview(),
        market_data=build_market_data(),
        investment_highlights=[
            "클라우드 인프라 매출 CAGR 30%+ — 금융권 2차 전환 최대 수혜자",
            "영업이익률 12% → 18% 지속 개선, 반복 매출 비중 48%",
            "ISMS-P + CSAP 동시 인증 — 독립계 유일, 규제적 해자 확보",
            "자체 플랫폼 Cross-selling → 고객 ARPU 연 15% 성장",
            "AI Ops·SaaS·해외 확장 등 다각적 성장 옵션 보유",
        ],
        growth_strategy=build_growth_strategy(),
        # ── 인적 자원 ──
        management_team=build_management_team(),
        shareholders=build_shareholders(),
        # ── TM 전용 내러티브 (마케팅 톤) ──
        narratives=build_tm_narratives(),
        # ── 차트 데이터 (IM + Pro-Forma 병합) ──
        charts=merged_charts,
        # ── 출처 메타데이터 ──
        source_citations=build_source_citations(),
        # ── 연락처 ──
        contacts=build_contacts(),
    )
    # 파생 지표 계산
    data.compute_derived_metrics()
    return data
