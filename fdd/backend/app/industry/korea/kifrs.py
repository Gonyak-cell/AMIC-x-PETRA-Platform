"""FDD 관점 K-IFRS 조정사항.

EBITDA 조정, NWC 분류, Net Debt 산정 시 고려해야 할
K-IFRS 기준서별 FDD 영향 사항을 정의한다.
"""

from __future__ import annotations

from app.industry.korea.models import FDDKIFRSNote

ALL_INDUSTRIES = ["tech", "manufacturing", "healthcare", "logistics", "financial_services"]

KIFRS_NOTES: list[FDDKIFRSNote] = [
    # ── 공통 (5개) ──
    FDDKIFRSNote(
        standard_number="1115",
        topic_kr="고객과의 계약에서 생기는 수익",
        ebitda_impact=(
            "수익인식 시점/방법 차이로 EBITDA 조정 필요. "
            "한시점 인식 vs 기간 인식 판단이 Reported EBITDA에 직접 영향"
        ),
        nwc_impact=(
            "계약자산/계약부채 분류가 NWC 산정에 영향. "
            "선수수익(계약부채)은 NWC 포함 여부 합의 필요"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    FDDKIFRSNote(
        standard_number="1116",
        topic_kr="리스",
        ebitda_impact=(
            "리스 자본화로 감가상각비+이자비용 대체 → EBITDA 과대 계상. "
            "운용리스 환원 시 EBITDA 하향 조정 검토"
        ),
        nwc_impact="리스부채 유동/비유동 분류가 NWC에 영향 (일반적으로 NWC 제외)",
        net_debt_impact=(
            "사용권자산 리스부채는 Net Debt 포함 여부 합의 필요. "
            "리스부채를 Net Debt에 포함 시 매수가격 조정 영향"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    FDDKIFRSNote(
        standard_number="1037",
        topic_kr="충당부채, 우발부채, 우발자산",
        ebitda_impact="충당부채 전입·환입은 비경상 항목으로 EBITDA 조정 대상",
        nwc_impact="유동 충당부채는 NWC 포함 여부 검토 (보증충당부채 등)",
        net_debt_impact=(
            "소송·환경복원 충당부채는 Debt-like 항목으로 Net Debt 반영. "
            "미인식 우발부채는 SPA R&W 항목으로 별도 관리"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    FDDKIFRSNote(
        standard_number="1019",
        topic_kr="종업원급여 (퇴직급여)",
        ebitda_impact=(
            "DB형 퇴직급여 서비스원가/이자원가 구분 필요. "
            "퇴직급여 보험수리적 가정 변경 영향은 비경상 조정"
        ),
        nwc_impact="단기 종업원급여(미지급 상여 등)는 NWC 포함",
        net_debt_impact=(
            "DB형 퇴직연금 적립 부족분(순확정급여부채)은 Debt-like 항목. "
            "DC 전환 비용은 매수가격 조정 협상 대상"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    FDDKIFRSNote(
        standard_number="1103",
        topic_kr="사업결합 (PPA)",
        ebitda_impact=(
            "PPA 결과 무형자산 상각비 발생 → 인수 후 EBITDA에 영향. "
            "영업권 손상차손은 비경상 항목으로 EBITDA 조정"
        ),
        nwc_impact="PPA 공정가치 조정이 재고자산·매출채권 평가에 영향",
        net_debt_impact="조건부 대가(Earn-out)는 Debt-like 항목으로 분류",
        applicable_industries=ALL_INDUSTRIES,
    ),
    # ── Tech: SaaS 수익·R&D (2개) ──
    FDDKIFRSNote(
        standard_number="1115",
        topic_kr="SaaS 수익인식 특수성",
        ebitda_impact=(
            "SaaS 구독 매출의 기간 인식 vs 라이선스 일시 인식 구분. "
            "ARR/MRR 기반 수익 지속성 평가가 EBITDA 정상화 핵심"
        ),
        nwc_impact=(
            "선수수익(Deferred Revenue)이 대규모 → 음의 NWC 구조. "
            "선수수익은 NWC에 포함하되 매수가격 조정에서 별도 논의"
        ),
        applicable_industries=["tech"],
    ),
    FDDKIFRSNote(
        standard_number="1038",
        topic_kr="무형자산 (R&D 자산화)",
        ebitda_impact=(
            "R&D 자산화 비율에 따라 비용화 EBITDA 차이 발생. "
            "SBC(주식보상비용) 조정과 함께 EBITDA 정상화 핵심"
        ),
        nwc_impact="자산화된 개발비는 NWC에서 제외 (비유동자산)",
        applicable_industries=["tech"],
    ),
    # ── Healthcare: 개발비·파이프라인 (1개) ──
    FDDKIFRSNote(
        standard_number="1038",
        topic_kr="무형자산 (임상 개발비)",
        ebitda_impact=(
            "임상시험 Phase별 자산화 시점이 회사마다 다름. "
            "자산화 정책 차이로 EBITDA 과대/과소 계상 가능. "
            "실패 시 즉시 비용화 → 대규모 EBITDA 하락"
        ),
        nwc_impact="임상 관련 미수금/미지급금은 NWC 포함 (장기 계약 분류 주의)",
        applicable_industries=["healthcare"],
    ),
    # ── Manufacturing: 자산손상·재고 (2개) ──
    FDDKIFRSNote(
        standard_number="1036",
        topic_kr="자산손상",
        ebitda_impact=(
            "유형자산 손상차손은 비경상 항목으로 EBITDA Add-back. "
            "가동률 하락 시 CGU(현금창출단위) 손상 리스크"
        ),
        nwc_impact="손상된 재고자산은 NWC에서 조정 필요",
        net_debt_impact="유형자산 손상 시 담보가치 하락 → 차입 조건 변경 리스크",
        applicable_industries=["manufacturing"],
    ),
    FDDKIFRSNote(
        standard_number="1002",
        topic_kr="재고자산",
        ebitda_impact=(
            "재고자산 평가손실(NRV 하회)은 EBITDA 조정 검토. "
            "FIFO/가중평균 변경 시 매출원가 영향"
        ),
        nwc_impact=(
            "재고자산은 NWC의 핵심 항목. "
            "재고회전일수 변동이 NWC Peg 산정에 직접 영향. "
            "진부화 재고(Obsolete Inventory) 조정 필수"
        ),
        applicable_industries=["manufacturing"],
    ),
    # ── Financial Services: 금융상품 (2개) ──
    FDDKIFRSNote(
        standard_number="1109",
        topic_kr="금융상품 (ECL 모형)",
        ebitda_impact=(
            "기대신용손실(ECL) 모형 변경으로 대손충당금 대폭 변동. "
            "대손충당금 전입·환입은 EBITDA 조정 핵심 항목"
        ),
        nwc_impact="유동 금융자산/부채 분류가 NWC 산정에 영향",
        net_debt_impact=(
            "FVOCI 채권 미실현손익이 자본에 누적 → 순자산 왜곡. "
            "차입금의 공정가치 vs 장부가치 차이 검토"
        ),
        applicable_industries=["financial_services"],
    ),
    FDDKIFRSNote(
        standard_number="1117",
        topic_kr="보험계약",
        ebitda_impact=(
            "IFRS 17 적용으로 보험부채 재측정. "
            "CSM(계약서비스마진) 상각이 이익의 핵심 동인. "
            "보험금융손익의 OCI/PL 선택이 EBITDA에 영향"
        ),
        nwc_impact="보험계약자산/부채는 NWC와 별도 관리",
        net_debt_impact="보험부채(BEL+RA+CSM)는 일반 Net Debt 프레임워크와 다른 분석 필요",
        applicable_industries=["financial_services"],
    ),
    # ── Logistics: 리스·유류비 (1개) ──
    FDDKIFRSNote(
        standard_number="1116",
        topic_kr="리스 (차량·물류센터)",
        ebitda_impact=(
            "물류업 리스 비중이 매우 높음 → EBITDA 과대 계상 효과 극대화. "
            "리스 환원 EBITDA 산정이 밸류에이션 핵심"
        ),
        nwc_impact="리스 선급금은 NWC 포함 여부 검토",
        net_debt_impact=(
            "차량·물류센터 리스부채가 Net Debt의 상당 부분. "
            "리스부채 포함/제외 시나리오 분석 필수"
        ),
        applicable_industries=["logistics"],
    ),
]
