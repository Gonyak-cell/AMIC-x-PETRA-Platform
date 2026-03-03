"""DM(Discussion Memorandum) 100% 완성 데이터 — get_full_dm_data().

8 슬라이드 이상의 DM PPTX 생성이 가능한 수준의 완전한 IMDocumentData를 반환한다.
IM FULL과 동일한 회사(넥스트테크) 데이터를 기반으로 하되,
im_style=DM, DM 전용 내러티브(분석적/비판적 톤)를 포함한다.
"""

from __future__ import annotations

from src.design_renderer.im_document import IMDocumentData, IMStyle

from .company import (
    build_company_overview,
    build_contacts,
    build_deal_structure,
    build_market_data,
)
from .financials import (
    build_charts,
    build_financial_statements,
    build_source_citations,
    build_valuation_data,
)
from .narratives_dm import build_dm_narratives


def get_full_dm_data() -> IMDocumentData:
    """100% 완성된 DM(Discussion Memorandum) IMDocumentData를 반환한다.

    IM FULL 데이터와 동일한 회사 데이터를 재사용하되:
    - im_style = DM (내부 분석용 6개 섹션 + cover + contact)
    - narratives = DM 전용 분석적/비판적 톤 6개 섹션
    - 파생 지표(derived_metrics)가 이미 계산된 상태

    DM은 내부 투자위원회 의사결정 문서이므로 경영진(management_team),
    주주구조(shareholders), 성장전략(growth_strategy), 세그먼트 매출(segment_revenue),
    프로포마(proforma) 데이터를 포함하지 않는다.
    """
    data = IMDocumentData(
        # ── 기본 정보 ──
        project_name="Project NEXUS",
        company_name_kr="넥스트테크",
        company_name_en="NextTech Co., Ltd.",
        corp_code="00987654",
        website_url="https://www.nexttech.co.kr",
        date="2026-03-01",
        # ── 섹션 구성 (DM 프리셋 자동 적용) ──
        im_style=IMStyle.DM,
        # ── 재무 데이터 (기존 5년 실적) ──
        financial_statements=build_financial_statements(),
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
        ],
        # ── DM 전용 내러티브 (분석적/비판적 톤) ──
        narratives=build_dm_narratives(),
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
