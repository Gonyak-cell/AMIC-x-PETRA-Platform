"""K-IFRS 조정사항.

> 마지막 수정: 2026-02-12 10:39:21

K-IFRS 1115(수익인식), 1116(리스), 1037(충당부채), 1019(종업원급여),
1103(사업결합), 1036(자산손상), 1038(무형자산) 등 M&A DD 시 확인 필요 기준서.
"""

from __future__ import annotations

from src.industry.korea.models import KIFRSNote

ALL_INDUSTRIES = ["tech", "manufacturing", "healthcare", "logistics", "financial_services"]

KIFRS_NOTES: list[KIFRSNote] = [
    # ── 공통 (5개) ──
    KIFRSNote(
        note_id="kifrs_1115",
        standard_number="1115",
        topic_kr="고객과의 계약에서 생기는 수익",
        topic_en="Revenue from Contracts with Customers",
        description="수행의무 식별, 거래가격 배분, 수익인식 시점 판단",
        deal_consideration=(
            "매출 인식 시점/방법 차이로 EBITDA 조정 필요 가능. "
            "SaaS 구독 매출 vs 라이선스 일시 매출 구분 확인"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    KIFRSNote(
        note_id="kifrs_1116",
        standard_number="1116",
        topic_kr="리스",
        topic_en="Leases",
        description="사용권자산과 리스부채 인식, 운용리스→금융리스 전환 영향",
        deal_consideration=(
            "리스 자본화로 EBITDA 과대 계상 가능. "
            "순차입금 산정 시 리스부채 포함 여부 합의 필요"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    KIFRSNote(
        note_id="kifrs_1037",
        standard_number="1037",
        topic_kr="충당부채, 우발부채, 우발자산",
        topic_en="Provisions, Contingent Liabilities and Contingent Assets",
        description="법적 소송, 환경복원, 구조조정 등 충당부채 인식 기준",
        deal_consideration=(
            "미인식 우발부채가 DD에서 발견될 리스크. "
            "SPA 진술보증(R&W) 항목으로 반영 필요"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    KIFRSNote(
        note_id="kifrs_1103",
        standard_number="1103",
        topic_kr="사업결합",
        topic_en="Business Combinations",
        description="취득법 적용, 영업권(Goodwill) 산정, PPA(매수가격배분)",
        deal_consideration=(
            "PPA 결과에 따라 무형자산 상각비 발생. "
            "영업권 손상검사 주기적 수행 필요"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    KIFRSNote(
        note_id="kifrs_1019",
        standard_number="1019",
        topic_kr="종업원급여",
        topic_en="Employee Benefits",
        description="퇴직급여(DB/DC), 기타장기종업원급여 인식",
        deal_consideration=(
            "DB형 퇴직연금 적립 부족분이 숨은 부채. "
            "인수 후 DC 전환 비용 추정 필요"
        ),
        applicable_industries=ALL_INDUSTRIES,
    ),
    # ── 자산 집약 산업: 제조, 물류 (1개) ──
    KIFRSNote(
        note_id="kifrs_1036",
        standard_number="1036",
        topic_kr="자산손상",
        topic_en="Impairment of Assets",
        description="사용가치 또는 순공정가치로 자산손상 검사",
        deal_consideration=(
            "유형자산 감액 리스크. 가동률 하락 시 손상차손 인식 가능"
        ),
        applicable_industries=["manufacturing", "logistics"],
    ),
    # ── Tech: 무형자산 (1개) ──
    KIFRSNote(
        note_id="kifrs_1038_tech",
        standard_number="1038",
        topic_kr="무형자산",
        topic_en="Intangible Assets",
        description="내부 개발 소프트웨어 자산화 기준, 내용연수 결정",
        deal_consideration=(
            "R&D 자산화 정책 차이로 이익 왜곡 가능. "
            "자산화 비율 및 상각 기간 비교 필수"
        ),
        applicable_industries=["tech"],
    ),
    # ── Financial Services: 금융상품 (2개) ──
    KIFRSNote(
        note_id="kifrs_1109",
        standard_number="1109",
        topic_kr="금융상품",
        topic_en="Financial Instruments",
        description="금융자산 분류(AC/FVOCI/FVPL), 기대신용손실(ECL) 모형 적용",
        deal_consideration=(
            "ECL 모형 변경으로 대손충당금 대폭 변동 가능. "
            "FVOCI 채권의 미실현손익이 자본에 누적되어 순자산 왜곡 가능"
        ),
        applicable_industries=["financial_services"],
    ),
    KIFRSNote(
        note_id="kifrs_1117",
        standard_number="1117",
        topic_kr="보험계약",
        topic_en="Insurance Contracts",
        description="보험계약 측정 모형(BBA/PAA), CSM 상각, 할인율 결정",
        deal_consideration=(
            "IFRS 17 적용으로 보험부채 재측정. "
            "CSM(계약서비스마진) 규모가 미래 이익 지표로 활용"
        ),
        applicable_industries=["financial_services"],
    ),
    # ── Healthcare: 개발비 (1개) ──
    KIFRSNote(
        note_id="kifrs_1038_hc",
        standard_number="1038",
        topic_kr="무형자산 (개발비)",
        topic_en="Intangible Assets (Development Costs)",
        description="임상시험 단계별 개발비 자산화 판단",
        deal_consideration=(
            "Phase별 자산화 시점이 회사마다 다름. "
            "실패 시 즉시 비용화로 대규모 손실 가능"
        ),
        applicable_industries=["healthcare"],
    ),
]
