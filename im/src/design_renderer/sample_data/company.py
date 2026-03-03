"""회사/시장/경영진/주주 데이터 — 가상 IT 서비스 기업 '넥스트테크'.

실제 M&A 실사 수준의 정성적 데이터를 구성한다.
"""

from __future__ import annotations

from src.design_renderer.im_document import (
    CompanyOverview,
    ContactInfo,
    DealStructure,
    GrowthStrategy,
    ManagementMember,
    MarketData,
    ShareholderInfo,
    TransactionType,
)


def build_company_overview() -> CompanyOverview:
    """회사 개요 — 연혁, 사업모델, 조직 등."""
    return CompanyOverview(
        history=[
            {"year": "2005", "event": "넥스트테크 주식회사 설립 (서울 강남구)"},
            {"year": "2008", "event": "클라우드 인프라 사업부 신설"},
            {"year": "2011", "event": "매출 100억원 돌파, ISO 27001 인증 취득"},
            {
                "year": "2014",
                "event": "데이터 분석 사업부 출범, 빅데이터 플랫폼 자체 개발",
            },
            {"year": "2016", "event": "ISMS-P 인증 취득, 공공부문 진출"},
            {"year": "2018", "event": "넥스트캐피탈 PE 전략적 투자 유치 (300억원)"},
            {"year": "2020", "event": "매출 500억원 돌파, 보안 솔루션 사업부 신설"},
            {"year": "2022", "event": "일본 법인 설립, 해외 매출 개시"},
            {"year": "2024", "event": "매출 1,550억원 달성, 직원 850명"},
        ],
        business_model="B2B IT 서비스 (클라우드 인프라 구축·운영, 데이터 분석 플랫폼, SI/컨설팅, 보안 솔루션)",
        business_description=(
            "넥스트테크는 2005년 설립 이후 국내 주요 대기업 및 금융기관을 대상으로 "
            "클라우드 인프라, 데이터 분석, SI/컨설팅, 보안 솔루션 등 4개 사업부를 운영하고 있다. "
            "특히 클라우드 인프라 사업부는 전체 매출의 47%를 차지하며, 최근 3년간 연평균 30% 이상의 "
            "고성장을 기록하고 있다. AWS, Azure, GCP 등 멀티 클라우드 환경에서의 설계·구축·운영 역량이 "
            "핵심 경쟁력으로, 금융권 클라우드 전환 수요를 선점하고 있다."
        ),
        value_chain=[
            "사전 컨설팅",
            "아키텍처 설계",
            "구축·마이그레이션",
            "운영·모니터링",
            "최적화·보안",
        ],
        key_products=[
            "NextCloud Platform (클라우드 통합 관리 플랫폼)",
            "DataInsight Pro (실시간 데이터 분석 솔루션)",
            "SecureShield (통합 보안 관제 솔루션)",
            "NextConsulting (IT 전략 컨설팅 서비스)",
        ],
        certifications=[
            "ISO 27001 (정보보안 경영시스템)",
            "ISMS-P (정보보호 및 개인정보보호 관리체계)",
            "ISO 9001 (품질경영시스템)",
            "CMMI Level 3 (소프트웨어 개발 성숙도)",
            "클라우드 서비스 보안인증 (CSAP)",
        ],
        employee_count=850,
        headquarters="서울특별시 강남구 테헤란로 152, 넥스트타워 15~18층",
        established_date="2005-03-15",
        locations=["판교 R&D 센터", "부산 지사", "도쿄 법인 (NextTech Japan)"],
        organization=[
            "클라우드 인프라 사업본부",
            "데이터 분석 사업본부",
            "SI/컨설팅 사업본부",
            "보안 솔루션 사업본부",
            "경영지원본부",
            "R&D센터",
        ],
        departments=[
            {
                "name": "클라우드 인프라 사업본부",
                "head": "박영호",
                "headcount": "280명",
            },
            {"name": "데이터 분석 사업본부", "head": "이수진", "headcount": "200명"},
            {"name": "SI/컨설팅 사업본부", "head": "최성민", "headcount": "150명"},
            {"name": "보안 솔루션 사업본부", "head": "정하늘", "headcount": "100명"},
            {"name": "경영지원본부", "head": "한미영", "headcount": "60명"},
            {"name": "R&D센터", "head": "강도현", "headcount": "60명"},
        ],
    )


def build_market_data() -> MarketData:
    """시장 데이터 — TAM/SAM/SOM, 경쟁사 5사, 산업 트렌드."""
    return MarketData(
        tam=1_200_000,  # 120조원 (국내 IT 서비스 전체)
        sam=350_000,  # 35조원 (클라우드+데이터 관련)
        som=55_000,  # 5.5조원 (넥스트테크 타겟 시장)
        market_growth_rate=0.12,
        market_cagr=0.14,
        competitors=[
            {
                "name": "삼성SDS",
                "revenue": 420_000,
                "market_share": 0.22,
                "strengths": "대기업 계열 IT 인프라, 글로벌 네트워크",
                "weaknesses": "높은 내부거래 의존도",
            },
            {
                "name": "LG CNS",
                "revenue": 340_000,
                "market_share": 0.18,
                "strengths": "스마트팩토리, 금융 IT",
                "weaknesses": "클라우드 전환 속도",
            },
            {
                "name": "SK C&C",
                "revenue": 130_000,
                "market_share": 0.07,
                "strengths": "AI 기반 솔루션, 데이터센터",
                "weaknesses": "중소기업 시장 침투력",
            },
            {
                "name": "포스코DX",
                "revenue": 95_000,
                "market_share": 0.05,
                "strengths": "제조업 DX 전문성",
                "weaknesses": "금융/공공 부문 레퍼런스 부족",
            },
            {
                "name": "메가존클라우드",
                "revenue": 80_000,
                "market_share": 0.04,
                "strengths": "AWS 파트너십, 스타트업 고객",
                "weaknesses": "기업 규모, 재무 안정성",
            },
        ],
        industry_trends=[
            "금융권 클라우드 전환 가속화 (2차 전환 도래)",
            "AI/ML 기반 데이터 분석 수요 폭증",
            "제로 트러스트 보안 아키텍처 도입 확산",
            "하이브리드·멀티 클라우드 환경 표준화",
            "공공부문 클라우드 네이티브 전환 정책 강화",
        ],
        market_position="국내 IT 서비스 시장 점유율 8% (3위권), 클라우드 인프라 부문 독립계 1위",
        competitive_advantages=[
            "멀티 클라우드 통합 관리 플랫폼 (NextCloud) 자체 보유",
            "금융권 클라우드 구축 레퍼런스 국내 최다 (15개 금융기관)",
            "ISMS-P + CSAP 동시 인증 (독립 IT 서비스 기업 중 유일)",
            "데이터 분석 플랫폼 경쟁 우위 (처리 속도 업계 평균 대비 2.5배)",
        ],
        regulatory_notes=(
            "2025년 시행된 '클라우드 컴퓨팅 발전법' 개정안에 따라 금융기관의 핵심 업무 "
            "클라우드 전환이 의무화되었으며, 이는 넥스트테크의 핵심 사업영역에 직접적인 수혜를 제공한다. "
            "또한 데이터 3법 개정으로 산업 간 데이터 결합이 확대되어 데이터 분석 사업부의 성장이 가속되고 있다."
        ),
    )


def build_management_team() -> list[ManagementMember]:
    """경영진 8명 — 각각 name/title/role/career 보유."""
    return [
        ManagementMember(
            name="김진수",
            title="대표이사",
            role="CEO",
            career=[
                "前 삼성SDS 클라우드사업부 상무 (2010~2018)",
                "前 AWS Korea 파트너 솔루션즈 아키텍트 (2006~2010)",
                "서울대학교 컴퓨터공학과 학사, MIT Sloan MBA",
                "한국클라우드산업협회 부회장",
            ],
        ),
        ManagementMember(
            name="이정은",
            title="부사장",
            role="CFO",
            career=[
                "前 JP Morgan 투자은행부 Vice President (2008~2016)",
                "前 PWC 삼일회계법인 Senior Manager (2003~2008)",
                "고려대학교 경제학과 학사, CPA·CFA",
            ],
        ),
        ManagementMember(
            name="박영호",
            title="전무",
            role="CTO",
            career=[
                "前 Google Cloud Korea 엔지니어링 리드 (2015~2020)",
                "前 네이버 클라우드 플랫폼 아키텍트 (2010~2015)",
                "KAIST 전산학과 석사",
            ],
        ),
        ManagementMember(
            name="최성민",
            title="상무",
            role="COO",
            career=[
                "前 LG CNS 컨설팅사업부 수석컨설턴트 (2012~2019)",
                "前 Accenture Korea 매니저 (2007~2012)",
                "연세대학교 산업공학과 학사",
            ],
        ),
        ManagementMember(
            name="이수진",
            title="상무",
            role="CDO (Chief Data Officer)",
            career=[
                "前 카카오 데이터 플랫폼팀 팀장 (2016~2021)",
                "前 IBM Watson 한국팀 수석연구원 (2012~2016)",
                "서울대학교 통계학과 박사",
            ],
        ),
        ManagementMember(
            name="정하늘",
            title="이사",
            role="CISO (Chief Information Security Officer)",
            career=[
                "前 금융보안원 수석연구원 (2014~2020)",
                "前 안랩 보안컨설팅팀 책임연구원 (2009~2014)",
                "고려대학교 정보보호학과 석사, CISSP·CISA",
            ],
        ),
        ManagementMember(
            name="한미영",
            title="이사",
            role="CHRO (Chief HR Officer)",
            career=[
                "前 삼성전자 인사팀 수석 (2010~2018)",
                "前 맥킨지 서울오피스 Associate (2006~2010)",
                "이화여자대학교 경영학과 학사",
            ],
        ),
        ManagementMember(
            name="강도현",
            title="이사",
            role="R&D 센터장",
            career=[
                "前 Microsoft Research Asia 연구원 (2013~2019)",
                "前 삼성리서치 AI Lab 선임연구원 (2009~2013)",
                "KAIST 전산학과 박사, 국제학술논문 30편+",
            ],
        ),
    ]


def build_shareholders() -> list[ShareholderInfo]:
    """주주 구성 — 5명, stake_pct 합계 = 1.0."""
    return [
        ShareholderInfo(
            name="넥스트캐피탈 PE",
            stake_pct=0.45,
            share_count=4_500_000,
            category="최대주주",
        ),
        ShareholderInfo(
            name="김진수 (대표이사)",
            stake_pct=0.20,
            share_count=2_000_000,
            category="특수관계인",
        ),
        ShareholderInfo(
            name="기관투자자 (복수)",
            stake_pct=0.15,
            share_count=1_500_000,
            category="기관투자자",
        ),
        ShareholderInfo(
            name="임직원 ESOP",
            stake_pct=0.08,
            share_count=800_000,
            category="특수관계인",
        ),
        ShareholderInfo(
            name="기타 소액주주",
            stake_pct=0.12,
            share_count=1_200_000,
            category="소액주주",
        ),
    ]


def build_deal_structure() -> DealStructure:
    """딜 구조 — 매각 배경, 밸류에이션, 타임라인."""
    return DealStructure(
        seller="넥스트캐피탈 PE",
        stake_pct=0.60,
        deal_background=(
            "넥스트캐피탈 PE는 2018년 전략적 투자 이후 7년간 넥스트테크의 성장을 지원하였으며, "
            "펀드 만기(2026년 12월)를 앞두고 전략적 매각을 추진한다. "
            "대상 지분은 PE 보유분(45%) + 김진수 대표 보유분 중 일부(15%)로 총 60%이며, "
            "경영권 이전을 포함한 전량 매각 구조이다."
        ),
        timeline={
            "IM 배포": "2026-03",
            "예비입찰": "2026-04",
            "실사 (DD)": "2026-05~06",
            "본입찰": "2026-07",
            "SPA 체결": "2026-08",
            "클로징": "2026-09",
        },
        old_shares=6_000_000,
        new_shares=None,
        valuation_low=350_000,
        valuation_high=460_000,
        valuation_method="EV/EBITDA",
        transaction_type=TransactionType.MA,
    )


def build_growth_strategy() -> GrowthStrategy:
    """성장 전략 — 유기적 성장 + 신사업 + M&A + 로드맵."""
    return GrowthStrategy(
        organic_growth=[
            "금융권 2차 클라우드 전환 수주 확대 (기존 15개 → 25개 금융기관)",
            "기존 고객사 Cross-selling (클라우드 → 데이터 분석 → 보안 패키지 번들)",
            "공공부문 클라우드 네이티브 전환 사업 수주 (정부 의무화 정책 대응)",
            "글로벌 확장: 일본 법인 매출 500억원 돌파 목표 (2028년)",
        ],
        new_business=[
            "AI Ops 플랫폼: 클라우드 운영 자동화 AI 솔루션 (2026년 하반기 출시)",
            "SaaS 기반 데이터 분석 플랫폼: DataInsight Cloud (월 구독 모델)",
            "제로 트러스트 보안 솔루션: SecureShield Zero (SASE 아키텍처)",
        ],
        ma_targets=[
            "국내 AI/ML 전문 스타트업 인수 (30~50억원 규모)",
            "일본 소재 클라우드 MSP 기업 인수 검토 (해외 진출 가속)",
        ],
        roadmap={
            "2026": [
                "금융권 2차 클라우드 전환 5개사 수주",
                "AI Ops 플랫폼 베타 출시",
                "DataInsight Cloud SaaS 전환 착수",
            ],
            "2027": [
                "AI 스타트업 인수 완료",
                "공공부문 대형 프로젝트 3건+ 수주",
                "일본 법인 매출 300억원 달성",
            ],
            "2028": [
                "SaaS 매출 비중 20% 돌파",
                "해외 매출 비중 15% 달성",
                "매출 3,000억원 돌파",
            ],
        },
    )


def build_org_structure() -> dict[str, str]:
    """조직도 데이터 — Graphviz DOT 구조."""
    return {
        "type": "org_chart",
        "dot": (
            "digraph OrgChart {\n"
            "  rankdir=TB;\n"
            '  node [shape=box, style=filled, fillcolor="#E6FDD6"];\n'
            '  CEO [label="김진수\\n대표이사 (CEO)", fillcolor="#0F3A32", fontcolor="white"];\n'
            '  CFO [label="이정은\\n부사장 (CFO)"];\n'
            '  CTO [label="박영호\\n전무 (CTO)"];\n'
            '  COO [label="최성민\\n상무 (COO)"];\n'
            '  CDO [label="이수진\\n상무 (CDO)"];\n'
            '  CISO [label="정하늘\\n이사 (CISO)"];\n'
            '  CHRO [label="한미영\\n이사 (CHRO)"];\n'
            '  RND [label="강도현\\n이사 (R&D 센터장)"];\n'
            "  CEO -> {CFO CTO COO};\n"
            "  CEO -> {CDO CISO CHRO RND};\n"
            "}"
        ),
    }


def build_contacts() -> list[ContactInfo]:
    """연락처 정보 (가상 데이터)."""
    return [
        ContactInfo(
            name="홍길동",
            title="Managing Director",
            email="gdhong@sample-advisory.co.kr",
            phone="02-0000-1234",
            company="Sample Advisory Partners",
        ),
        ContactInfo(
            name="김철수",
            title="Vice President",
            email="cskim@sample-advisory.co.kr",
            phone="02-0000-1235",
            company="Sample Advisory Partners",
        ),
    ]
