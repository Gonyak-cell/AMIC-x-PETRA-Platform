"""FDD 관점 한국 세무 검토 사항.

이전가격, 접대비/기부금 한도, R&D 세액공제, 지방세 등
FDD 분석 시 EBITDA 정상화·우발채무·Net Debt에 영향을 주는 세무 항목을 정의한다.
"""

from __future__ import annotations

from app.industry.korea.models import FDDTaxItem, Severity

ALL_INDUSTRIES = ["tech", "manufacturing", "healthcare", "logistics", "financial_services"]

TAX_ITEMS: list[FDDTaxItem] = [
    # ── 공통 세무 (5개) ──
    FDDTaxItem(
        item_id="transfer_pricing",
        description_kr="이전가격 세제 (Transfer Pricing)",
        fdd_consideration=(
            "특수관계자 거래의 정상가격(Arm's Length Price) 적정성 검토. "
            "이전가격 조정 시 추징세액은 우발채무로 Net Debt 반영. "
            "BEPS Action Plan 준수 여부 확인 (국가별 보고서 제출 의무)"
        ),
        applicable_industries=ALL_INDUSTRIES,
        severity=Severity.HIGH,
    ),
    FDDTaxItem(
        item_id="entertainment_donation",
        description_kr="접대비·기부금 한도 초과",
        fdd_consideration=(
            "세무상 손금불산입 접대비·기부금은 EBITDA 조정 시 검토. "
            "한도 초과분의 법인세 효과 → 실효세율 상승. "
            "반복 패턴 시 정상 운영비 vs 비경상 구분 필요"
        ),
        applicable_industries=ALL_INDUSTRIES,
        severity=Severity.LOW,
    ),
    FDDTaxItem(
        item_id="deferred_tax",
        description_kr="이연법인세 자산·부채",
        fdd_consideration=(
            "이연법인세 자산의 실현 가능성 평가 (미래 과세소득 충분성). "
            "Net Debt 산정 시 이연법인세 부채 포함 여부 합의 필요. "
            "M&A 후 이연법인세 재측정 영향 분석"
        ),
        applicable_industries=ALL_INDUSTRIES,
        severity=Severity.MEDIUM,
    ),
    FDDTaxItem(
        item_id="local_tax",
        description_kr="지방세 (취득세·재산세)",
        fdd_consideration=(
            "부동산·기계장치 취득세(4.6%)는 CAPEX 관련 일시적 비용. "
            "재산세·종합부동산세는 정상 운영비로 EBITDA 포함. "
            "M&A 시 주식양수도 vs 영업양수도의 취득세 차이 검토"
        ),
        applicable_industries=ALL_INDUSTRIES,
        severity=Severity.LOW,
    ),
    FDDTaxItem(
        item_id="vat_refund",
        description_kr="부가가치세 환급 지연",
        fdd_consideration=(
            "VAT 매입세액 환급 지연은 NWC에 영향 (미수금 증가). "
            "수출 비중이 높은 기업의 영세율 적용 적정성 확인. "
            "VAT 부정환급 리스크는 우발채무 검토"
        ),
        applicable_industries=ALL_INDUSTRIES,
        severity=Severity.LOW,
    ),
    # ── Tech 세무 (2개) ──
    FDDTaxItem(
        item_id="rd_tax_credit",
        description_kr="R&D 세액공제",
        fdd_consideration=(
            "R&D 세액공제(최대 40%)의 영속성 평가 → 실효세율 변동. "
            "M&A 후 연구인력·시설 유지 조건 충족 여부 확인. "
            "세액공제 감소 시 세후 이익 하락 → 밸류에이션 영향"
        ),
        applicable_industries=["tech"],
        severity=Severity.MEDIUM,
    ),
    FDDTaxItem(
        item_id="sbc_tax",
        description_kr="주식보상비용(SBC) 세무 처리",
        fdd_consideration=(
            "SBC의 손금산입 시점(행사 시) vs 회계상 인식 시점(부여 시) 차이. "
            "이연법인세 자산으로 인식된 SBC 관련 세효과 검토. "
            "EBITDA 정상화 시 SBC Add-back과 세효과 동시 고려"
        ),
        applicable_industries=["tech"],
        severity=Severity.MEDIUM,
    ),
    # ── Healthcare 세무 (1개) ──
    FDDTaxItem(
        item_id="clinical_rd_credit",
        description_kr="임상시험 R&D 세액공제",
        fdd_consideration=(
            "임상시험 비용의 R&D 세액공제 적격 여부 확인. "
            "해외 위탁 임상비용(CRO)의 국내 세액공제 적용 제한. "
            "Phase 실패 시 자산화 개발비 즉시 비용화 + 세액공제 환수 리스크"
        ),
        applicable_industries=["healthcare"],
        severity=Severity.MEDIUM,
    ),
    # ── Manufacturing 세무 (1개) ──
    FDDTaxItem(
        item_id="investment_tax_credit",
        description_kr="시설투자 세액공제",
        fdd_consideration=(
            "국가전략기술·신성장동력 투자 세액공제(최대 25%) 영속성 평가. "
            "M&A 후 시설 용도 변경 시 세액공제 환수 리스크. "
            "CAPEX 계획과 세액공제 스케줄의 정합성 확인"
        ),
        applicable_industries=["manufacturing"],
        severity=Severity.MEDIUM,
    ),
    # ── Financial Services 세무 (1개) ──
    FDDTaxItem(
        item_id="financial_tax",
        description_kr="금융업 특수 세무",
        fdd_consideration=(
            "대손충당금 세무상 한도(채권 잔액 1%) vs 회계상 ECL 차이. "
            "유가증권 평가손익의 세무 인식 시점 차이. "
            "금융보증계약의 보증료 수익 세무 인식 시점 검토"
        ),
        applicable_industries=["financial_services"],
        severity=Severity.MEDIUM,
    ),
    # ── Logistics 세무 (1개) ──
    FDDTaxItem(
        item_id="logistics_tax",
        description_kr="물류업 세무 특수성",
        fdd_consideration=(
            "유가보조금의 법인세 과세 여부 확인 (정부보조금 과세 원칙). "
            "차량 감가상각 내용연수 적정성 (세무 vs 회계 차이). "
            "차량 리스료의 세무상 한도(연 800만원) 초과분 손금불산입"
        ),
        applicable_industries=["logistics"],
        severity=Severity.LOW,
    ),
]
