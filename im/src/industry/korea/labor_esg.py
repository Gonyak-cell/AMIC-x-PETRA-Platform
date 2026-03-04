"""노동법 준수 및 ESG 공시 요구사항.

> 마지막 수정: 2026-02-12 10:39:21

근로기준법, 노동조합법, 산업안전보건법 등 노동법 항목과
KCGS, TCFD, K-Taxonomy 등 ESG 요구사항을 정의한다.
"""

from __future__ import annotations

from src.industry.korea.models import ESGFramework, ESGRequirement, LaborItem

ALL_INDUSTRIES = [
    "tech",
    "manufacturing",
    "healthcare",
    "logistics",
    "financial_services",
]

# ---------------------------------------------------------------------------
# 노동법 항목 (6개)
# ---------------------------------------------------------------------------

LABOR_ITEMS: list[LaborItem] = [
    LaborItem(
        labor_id="labor_standard_act",
        law_name_kr="근로기준법",
        law_name_en="Labor Standards Act",
        description="근로조건 최저기준 (임금, 근로시간, 휴가, 해고 제한)",
        deal_impact=(
            "정리해고 요건 엄격 (긴박한 경영상 필요, 해고회피 노력, "
            "합리적 선정 기준). 카브아웃 시 전적 처리 비용 반영 필수"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    LaborItem(
        labor_id="trade_union_act",
        law_name_kr="노동조합 및 노동관계조정법",
        law_name_en="Trade Union and Labor Relations Adjustment Act",
        description="노동조합 설립, 단체교섭, 쟁의행위 규정",
        deal_impact=(
            "노조 유무 및 단체협약 내용이 인수 조건에 영향. "
            "경영권 변동 시 단체교섭 재개 가능성"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    LaborItem(
        labor_id="osha_labor",
        law_name_kr="산업안전보건법",
        law_name_en="Occupational Safety and Health Act",
        description="안전보건관리체제, 위험성평가, 안전보건교육 의무",
        deal_impact=(
            "중대재해처벌법(2022) 시행으로 경영책임자 형사처벌 가능. "
            "안전관리 비용 및 보험 충당 확인"
        ),
        applicable_industries=["manufacturing", "logistics"],
    ),
    LaborItem(
        labor_id="dispatched_workers",
        law_name_kr="파견근로자 보호 등에 관한 법률",
        law_name_en="Dispatched Workers Protection Act",
        description="파견 허용 업종, 기간 제한(2년), 직접고용 의무",
        deal_impact=(
            "불법파견 시 직접고용 간주 리스크. IT 외주인력 파견 여부 실사 필수"
        ),
        applicable_industries=["tech", "manufacturing"],
    ),
    LaborItem(
        labor_id="severance_pay",
        law_name_kr="근로자퇴직급여 보장법",
        law_name_en="Employee Retirement Benefit Security Act",
        description="퇴직급여(퇴직금/퇴직연금) 지급 의무",
        deal_impact=(
            "퇴직급여 충당부채 적정성 확인. DB→DC 전환 시 추가 부담금 발생 가능"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    LaborItem(
        labor_id="working_hours",
        law_name_kr="근로기준법 (근로시간 특례)",
        law_name_en="Labor Standards Act (Working Hours Exception)",
        description="주 52시간 상한제, 특례업종 제한",
        deal_impact=("물류/운송 특례 업종 해제 추세. 인력 추가 채용 비용 반영 필요"),
        applicable_industries=["logistics", "manufacturing"],
    ),
]

# ---------------------------------------------------------------------------
# ESG 요구사항 (8개)
# ---------------------------------------------------------------------------

ESG_REQUIREMENTS: list[ESGRequirement] = [
    # ── KCGS (3개) ──
    ESGRequirement(
        esg_id="kcgs_governance",
        framework=ESGFramework.KCGS,
        category="지배구조",
        description=(
            "한국기업지배구조원(KCGS) 지배구조 등급 평가. "
            "이사회 독립성, 감사위원회, 주주권리 보호"
        ),
        mandatory=False,
        applicable_industries=ALL_INDUSTRIES,
    ),
    ESGRequirement(
        esg_id="kcgs_environment",
        framework=ESGFramework.KCGS,
        category="환경",
        description="온실가스 배출, 에너지 사용, 폐기물 관리 평가",
        mandatory=False,
        applicable_industries=["manufacturing", "logistics"],
    ),
    ESGRequirement(
        esg_id="kcgs_social",
        framework=ESGFramework.KCGS,
        category="사회",
        description="산업안전, 인권, 공급망 관리, 지역사회 기여 평가",
        mandatory=False,
        applicable_industries=ALL_INDUSTRIES,
    ),
    # ── TCFD (2개) ──
    ESGRequirement(
        esg_id="tcfd_climate",
        framework=ESGFramework.TCFD,
        category="기후 리스크",
        description=(
            "기후 관련 재무정보 공개. 지배구조, 전략, "
            "리스크관리, 지표·목표 4대 영역 공시"
        ),
        mandatory=True,
        applicable_industries=ALL_INDUSTRIES,
        effective_year=2025,
    ),
    ESGRequirement(
        esg_id="tcfd_transition",
        framework=ESGFramework.TCFD,
        category="전환 리스크",
        description=("탄소중립 전환에 따른 좌초자산, 규제비용, 시장변화 리스크 분석"),
        mandatory=False,
        applicable_industries=["manufacturing", "logistics"],
    ),
    # ── K-Taxonomy (2개) ──
    ESGRequirement(
        esg_id="k_taxonomy_green",
        framework=ESGFramework.K_TAXONOMY,
        category="녹색경제",
        description=("한국형 녹색분류체계 적합 활동 분류. 녹색금융 적격 여부 판단"),
        mandatory=False,
        applicable_industries=["manufacturing", "logistics"],
        effective_year=2023,
    ),
    ESGRequirement(
        esg_id="k_taxonomy_transition",
        framework=ESGFramework.K_TAXONOMY,
        category="전환경제",
        description="전환 활동(천연가스 등) 분류. 과도기 투자 적격 여부",
        mandatory=False,
        applicable_industries=["manufacturing"],
        effective_year=2023,
    ),
    # ── CSRD (1개) ──
    ESGRequirement(
        esg_id="csrd_supply_chain",
        framework=ESGFramework.CSRD,
        category="공급망 실사",
        description=("EU 공급망 실사 지침 영향. EU 수출 기업의 공급망 ESG 실사 의무"),
        mandatory=True,
        applicable_industries=["manufacturing", "healthcare"],
        effective_year=2026,
    ),
]
