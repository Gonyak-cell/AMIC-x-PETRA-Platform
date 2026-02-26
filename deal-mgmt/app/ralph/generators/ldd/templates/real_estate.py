"""부동산(Real Estate) LDD 템플릿 — 6개 섹션.

샘플 보고서 3건 분석 결과:
- 펀드구조 → 매도인/거래 → 부동산현황 → 임대차 → 사용관리 → 세금/보험
- Zoning/용적률 상세, 임대차 심층 분석 포함
"""

from __future__ import annotations

from app.ralph.generators.ldd.templates.base import AppendixDef, ItemDef, LDDTemplate, SectionDef


class RealEstateTemplate(LDDTemplate):
    deal_type = "REAL_ESTATE"
    display_name = "부동산"

    sections = [
        SectionDef(
            section_type="FUND_STRUCTURE",
            title="1. 펀드 및 거래 구조",
            items=[
                ItemDef("FUND-01", "펀드 설립/등록 적법성"),
                ItemDef("FUND-02", "집합투자업자/자산관리회사 자격"),
                ItemDef("FUND-03", "수익자(투자자) 현황 및 의결구조"),
                ItemDef("FUND-04", "신탁계약/투자약관 주요 조건"),
                ItemDef("FUND-05", "차입구조 및 LTV 비율"),
            ],
        ),
        SectionDef(
            section_type="SELLER_DEAL",
            title="2. 매도인 및 거래 조건",
            items=[
                ItemDef("SELLER-01", "매도인 법적 지위 및 처분권한"),
                ItemDef("SELLER-02", "매매대금 및 정산 조건"),
                ItemDef("SELLER-03", "진술보장 및 면책 조항"),
                ItemDef("SELLER-04", "거래 선행조건(CP) 검토"),
            ],
        ),
        SectionDef(
            section_type="PROPERTY_STATUS",
            title="3. 부동산 현황",
            items=[
                ItemDef("PROP-01", "소유권 등기 및 권원하자"),
                ItemDef("PROP-02", "저당권/근저당/전세권 현황"),
                ItemDef("PROP-03", "용도지역/지구/구역 (Zoning)"),
                ItemDef("PROP-04", "건축허가/준공검사/위반건축물"),
                ItemDef("PROP-05", "용적률/건폐율 적합성"),
                ItemDef("PROP-06", "토지이용계획 확인 (개발행위제한)"),
                ItemDef("PROP-07", "환경영향평가/오염 이력"),
            ],
        ),
        SectionDef(
            section_type="LEASE",
            title="4. 임대차 분석",
            items=[
                ItemDef("LEASE-01", "임대차 현황 (공실률/임대율)"),
                ItemDef("LEASE-02", "주요 임차인 신용도 및 잔여기간"),
                ItemDef("LEASE-03", "임대료 수준 (시장대비 적정성)"),
                ItemDef("LEASE-04", "임대차보호법/상가임대차법 적용"),
                ItemDef("LEASE-05", "임대차 승계/동의 조항"),
                ItemDef("LEASE-06", "관리비/공용면적 정산 구조"),
            ],
        ),
        SectionDef(
            section_type="MANAGEMENT",
            title="5. 사용 및 관리",
            items=[
                ItemDef("MGT-01", "위탁관리(PM/FM) 계약"),
                ItemDef("MGT-02", "시설물 유지보수 이력"),
                ItemDef("MGT-03", "에너지/안전 인증 현황"),
                ItemDef("MGT-04", "주차장/부대시설 운영"),
            ],
        ),
        SectionDef(
            section_type="TAX_INSURANCE",
            title="6. 세금 및 보험",
            items=[
                ItemDef("RETAX-01", "취득세/등록세 추계"),
                ItemDef("RETAX-02", "재산세/종합부동산세 현황"),
                ItemDef("RETAX-03", "부가가치세 과세 여부"),
                ItemDef("RETAX-04", "양도소득세/법인세 영향"),
                ItemDef("RETAX-05", "화재/배상 보험 부보 적정성"),
            ],
        ),
    ]

    appendices = [
        AppendixDef("APP-01", "별지 1: 부동산 현황 요약", ["소재지", "면적(㎡)", "용도", "소유형태", "등기현황", "감정가"]),
        AppendixDef("APP-02", "별지 2: 임대차 현황", ["임차인", "면적(㎡)", "임대료(월)", "기간", "보증금", "갱신옵션"]),
        AppendixDef("APP-03", "별지 3: 담보/제한물권 현황", ["유형", "채권자", "채권최고액", "설정일", "해제조건"]),
    ]
