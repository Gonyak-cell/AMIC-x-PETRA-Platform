"""IM FULL 100% 완성 데이터 — get_full_im_data().

30~40 슬라이드 PPTX 생성이 가능한 수준의 완전한 IMDocumentData를 반환한다.
financials, company, narratives_im 모듈에서 각 데이터를 조합한다.
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
    build_org_structure,
    build_shareholders,
)
from .financials import (
    build_charts,
    build_financial_statements,
    build_segment_revenue,
    build_source_citations,
    build_valuation_data,
)
from .narratives_im import build_im_narratives


def get_full_im_data() -> IMDocumentData:
    """100% 완성된 IM FULL IMDocumentData를 반환한다.

    반환된 데이터는 파생 지표(derived_metrics)가 이미 계산된 상태이다.
    """
    data = IMDocumentData(
        # ── 기본 정보 ──
        project_name="Project NEXUS",
        company_name_kr="넥스트테크",
        company_name_en="NextTech Co., Ltd.",
        corp_code="00987654",
        website_url="https://www.nexttech.co.kr",
        date="2026-03-01",
        # ── 섹션 구성 ──
        im_style=IMStyle.FULL,
        # ── 재무 데이터 ──
        financial_statements=build_financial_statements(),
        segment_revenue=build_segment_revenue(),
        key_customers=[
            "삼성전자",
            "현대자동차",
            "KB금융지주",
            "신한금융지주",
            "SK하이닉스",
            "LG에너지솔루션",
            "한국전력공사",
            "국민건강보험공단",
        ],
        # ── 딜 구조 ──
        deal_structure=build_deal_structure(),
        # ── 밸류에이션 ──
        valuation_data=build_valuation_data(),
        # ── 정성 데이터 ──
        company_overview=build_company_overview(),
        market_data=build_market_data(),
        investment_highlights=[
            "클라우드 인프라 사업부 매출 CAGR 30%+ (금융권 전환 수혜)",
            "영업이익률 12% → 18% 지속 개선 (반복 매출 비중 48%)",
            "ISMS-P + CSAP 동시 인증 (독립 IT 서비스 기업 중 유일)",
            "자체 플랫폼 Cross-selling (고객 ARPU 연 15% 성장)",
            "AI Ops·SaaS·해외 확장 등 다각적 성장 옵션 보유",
        ],
        growth_strategy=build_growth_strategy(),
        # ── 인적 자원 ──
        management_team=build_management_team(),
        org_structure=build_org_structure(),
        shareholders=build_shareholders(),
        # ── AI 내러티브 ──
        narratives=build_im_narratives(),
        # ── 차트 데이터 ──
        charts=build_charts(),
        # ── 출처 메타데이터 ──
        source_citations=build_source_citations(),
        # ── 연락처 ──
        contacts=build_contacts(),
    )
    # 파생 지표 계산
    data.compute_derived_metrics()
    return data
