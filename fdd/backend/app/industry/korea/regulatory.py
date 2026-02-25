"""FDD 관점 한국 규제 맵.

기업결합 심사, 세무조사, 산업별 인허가 등
FDD 분석 시 EBITDA 조정·우발채무·사업 지속성에 영향을 주는 규제를 정의한다.
"""

from __future__ import annotations

from app.industry.korea.models import FDDRegulatoryItem, Severity

ALL_INDUSTRIES = ["tech", "manufacturing", "healthcare", "logistics", "financial_services"]

REGULATORY_ITEMS: list[FDDRegulatoryItem] = [
    # ── 공통 규제 (3개) ──
    FDDRegulatoryItem(
        regulation_id="merger_review",
        law_name_kr="독점규제 및 공정거래에 관한 법률 (기업결합 심사)",
        authority="공정거래위원회",
        fdd_impact=(
            "기업결합 심사 지연 시 Closing 일정 영향. "
            "시정 조건(사업부 매각 등) 부과 시 EBITDA 범위 변동. "
            "과징금 이력은 우발채무로 반영"
        ),
        applicable_industries=ALL_INDUSTRIES,
        severity=Severity.HIGH,
        key_articles=["제11조 (기업결합 신고)", "제14조 (시정조치)"],
    ),
    FDDRegulatoryItem(
        regulation_id="tax_audit_history",
        law_name_kr="국세기본법 (세무조사)",
        authority="국세청",
        fdd_impact=(
            "최근 5년 세무조사 이력 확인 필수. "
            "추징세액은 Net Debt 또는 우발채무로 분류. "
            "이전가격(TP) 조정 리스크는 EBITDA 정상화 시 반영"
        ),
        applicable_industries=ALL_INDUSTRIES,
        severity=Severity.HIGH,
        key_articles=["제81조의6 (세무조사)", "제81조의15 (과세전적부심사)"],
    ),
    FDDRegulatoryItem(
        regulation_id="labor_contingency",
        law_name_kr="근로기준법 (정리해고·퇴직금)",
        authority="고용노동부",
        fdd_impact=(
            "정리해고 비용은 구조조정 충당부채로 EBITDA 조정 대상. "
            "DB형 퇴직연금 적립 부족분은 Net Debt-like 항목. "
            "미지급 퇴직금은 NWC에서 제외하고 Net Debt으로 분류"
        ),
        applicable_industries=ALL_INDUSTRIES,
        severity=Severity.MEDIUM,
        key_articles=["제24조 (경영상 이유에 의한 해고)", "퇴직급여보장법 제8조"],
    ),
    # ── Tech 규제 (2개) ──
    FDDRegulatoryItem(
        regulation_id="isms_certification",
        law_name_kr="정보통신망법 (ISMS 인증)",
        authority="과학기술정보통신부",
        fdd_impact=(
            "ISMS 인증 유지 비용은 정상 운영비로 EBITDA에 반영. "
            "인증 미취득·갱신 실패 시 사업 지속성 리스크. "
            "과태료(최대 3천만원)는 우발채무 검토"
        ),
        applicable_industries=["tech"],
        severity=Severity.MEDIUM,
        key_articles=["제47조 (정보보호 관리체계 인증)"],
    ),
    FDDRegulatoryItem(
        regulation_id="pipa_data_transfer",
        law_name_kr="개인정보 보호법 (M&A 시 데이터 이전)",
        authority="개인정보보호위원회",
        fdd_impact=(
            "고객 DB 이전 동의 절차 비용 발생. "
            "과징금(매출 3%) 리스크는 우발채무로 반영. "
            "데이터 이전 불가 시 영업권 가치 재산정 필요"
        ),
        applicable_industries=["tech"],
        severity=Severity.HIGH,
        key_articles=["제17조 (제3자 제공)", "제75조의2 (과징금)"],
    ),
    # ── Healthcare 규제 (2개) ──
    FDDRegulatoryItem(
        regulation_id="pharma_license",
        law_name_kr="약사법 (제조·수입업 허가 승계)",
        authority="식품의약품안전처",
        fdd_impact=(
            "제조업 허가 승계 절차(3~6개월) 중 매출 공백 리스크. "
            "GMP 적합 판정 유지 비용은 CAPEX/OPEX 구분 필요. "
            "허가 조건 미충족 시 사업 지속성 리스크"
        ),
        applicable_industries=["healthcare"],
        severity=Severity.HIGH,
        key_articles=["제31조 (제조업 허가)", "제42조 (수입업 허가)"],
    ),
    FDDRegulatoryItem(
        regulation_id="drug_pricing",
        law_name_kr="국민건강보험법 (약가 결정)",
        authority="보건복지부·건강보험심사평가원",
        fdd_impact=(
            "약가 인하 리스크는 매출 예측에 직접 영향. "
            "실거래가 조사에 따른 약가 환수는 우발채무. "
            "약가 변동은 EBITDA 정상화 시 조정 항목"
        ),
        applicable_industries=["healthcare"],
        severity=Severity.HIGH,
        key_articles=["제41조 (요양급여)", "제46조 (약가 기준)"],
    ),
    # ── Manufacturing 규제 (2개) ──
    FDDRegulatoryItem(
        regulation_id="env_liability",
        law_name_kr="환경영향평가법·토양환경보전법",
        authority="환경부",
        fdd_impact=(
            "토양·수질 오염 복원 비용은 환경충당부채로 Net Debt 반영. "
            "환경영향평가 미이행 시 사업장 폐쇄 리스크. "
            "탄소배출권 매입 비용은 EBITDA 조정 검토"
        ),
        applicable_industries=["manufacturing"],
        severity=Severity.MEDIUM,
        key_articles=["환경영향평가법 제22조", "토양환경보전법 제10조의4"],
    ),
    FDDRegulatoryItem(
        regulation_id="serious_accident",
        law_name_kr="중대재해 처벌 등에 관한 법률",
        authority="고용노동부",
        fdd_impact=(
            "중대재해 발생 시 경영책임자 형사처벌 + 과징금(최대 50억원). "
            "안전관리 비용 증가분은 EBITDA 정상화 시 반영. "
            "과징금 리스크는 우발채무로 Net Debt에 반영"
        ),
        applicable_industries=["manufacturing"],
        severity=Severity.HIGH,
        key_articles=["제4조 (사업주 등의 안전보건 확보의무)", "제6조 (중대산업재해)"],
    ),
    # ── Financial Services 규제 (2개) ──
    FDDRegulatoryItem(
        regulation_id="capital_adequacy",
        law_name_kr="은행법·보험업법 (자본적정성)",
        authority="금융위원회·금융감독원",
        fdd_impact=(
            "BIS 비율(은행)/RBC 비율(보험) 미달 시 배당 제한 → 주주가치 영향. "
            "자본적정성 유지 비용은 Net Debt 산정 시 별도 반영. "
            "규제 자본 부족분은 추가 출자 필요 → 매수가격 조정"
        ),
        applicable_industries=["financial_services"],
        severity=Severity.HIGH,
        key_articles=["은행법 제34조 (경영지도기준)", "보험업법 제123조 (재무건전성)"],
    ),
    FDDRegulatoryItem(
        regulation_id="loan_loss_provision",
        law_name_kr="금융업 감독규정 (대손충당금)",
        authority="금융감독원",
        fdd_impact=(
            "대손충당금 적립률 차이로 EBITDA 왜곡 가능. "
            "감독원 기준 vs 경영진 추정치 차이 조정 필요. "
            "FLC(Forward-Looking Criteria) 변경 영향 분석"
        ),
        applicable_industries=["financial_services"],
        severity=Severity.MEDIUM,
        key_articles=["은행업 감독규정 제29조", "보험업 감독규정 제7-2조"],
    ),
    # ── Logistics 규제 (2개) ──
    FDDRegulatoryItem(
        regulation_id="transport_license",
        law_name_kr="화물자동차 운수사업법",
        authority="국토교통부",
        fdd_impact=(
            "운수사업 허가 승계 절차 필수. "
            "차량 대수 변경 신고 지연 시 과태료. "
            "허가 조건(최소 차량 대수 등) 미충족 시 사업 지속성 리스크"
        ),
        applicable_industries=["logistics"],
        severity=Severity.MEDIUM,
        key_articles=["제3조 (허가)", "제5조 (변경 신고)"],
    ),
    FDDRegulatoryItem(
        regulation_id="fuel_subsidy",
        law_name_kr="화물자동차 유가보조금 관리 규정",
        authority="국토교통부",
        fdd_impact=(
            "유가보조금 수령액은 EBITDA 정상화 시 비경상 항목 검토. "
            "보조금 부정수급 이력은 환수 리스크 → 우발채무. "
            "보조금 정책 변경 시 영업비용 증가 영향 분석"
        ),
        applicable_industries=["logistics"],
        severity=Severity.LOW,
        key_articles=["유가보조금 관리 규정 제4조"],
    ),
]
