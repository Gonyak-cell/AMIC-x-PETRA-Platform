"""IPO LDD 템플릿 — 4개 섹션.

샘플 보고서 2건 분석 결과:
- 일반사항 → 경영안정성 → 경영투명성 → 기업계속성
- 상장적격성 중심 분석 (한국거래소 상장심사 기준)
"""

from __future__ import annotations

from app.ralph.generators.ldd.templates.base import AppendixDef, ItemDef, LDDTemplate, SectionDef


class IPOTemplate(LDDTemplate):
    deal_type = "IPO"
    display_name = "IPO (기업공개)"

    sections = [
        SectionDef(
            section_type="GENERAL",
            title="1. 일반사항",
            items=[
                ItemDef("GEN-01", "회사 설립 및 연혁"),
                ItemDef("GEN-02", "정관 주요 내용 (적격성)"),
                ItemDef("GEN-03", "주식/자본금 변동 이력"),
                ItemDef("GEN-04", "주주 구성 및 특수관계인"),
                ItemDef("GEN-05", "자회사/관계사 현황"),
                ItemDef("GEN-06", "CB/BW/전환사채/스톡옵션 현황"),
                ItemDef("GEN-07", "최대주주 변경 이력 (3년)"),
            ],
        ),
        SectionDef(
            section_type="MGMT_STABILITY",
            title="2. 경영안정성",
            items=[
                ItemDef("STAB-01", "이사회 구성 적정성 (사외이사 비율)"),
                ItemDef("STAB-02", "감사/감사위원회 설치 및 운영"),
                ItemDef("STAB-03", "내부회계관리제도 운영 현황"),
                ItemDef("STAB-04", "핵심인력 유출 위험"),
                ItemDef("STAB-05", "경영권 분쟁 가능성"),
                ItemDef("STAB-06", "최대주주 지분율 변동 위험"),
            ],
        ),
        SectionDef(
            section_type="MGMT_TRANSPARENCY",
            title="3. 경영투명성",
            items=[
                ItemDef("TRANS-01", "특수관계인 거래 현황"),
                ItemDef("TRANS-02", "이해충돌 거래 검토"),
                ItemDef("TRANS-03", "자기거래/자기주식 처분 적법성"),
                ItemDef("TRANS-04", "공시 의무 위반 이력"),
                ItemDef("TRANS-05", "회계처리 적정성 (외부감사의견)"),
                ItemDef("TRANS-06", "횡령/배임 이력 및 위험"),
            ],
        ),
        SectionDef(
            section_type="GOING_CONCERN",
            title="4. 기업계속성",
            items=[
                ItemDef("GC-01", "주요 영업 인허가 유효성"),
                ItemDef("GC-02", "주요 계약 지속 가능성"),
                ItemDef("GC-03", "진행 중 소송 (상장 영향)"),
                ItemDef("GC-04", "노사관계 안정성"),
                ItemDef("GC-05", "환경/안전 규제 준수"),
                ItemDef("GC-06", "지식재산권 보호 현황"),
                ItemDef("GC-07", "개인정보보호/IT 보안 준수"),
            ],
        ),
    ]

    appendices = [
        AppendixDef("APP-01", "별지 1: 주식/자본금 변동 이력", ["일자", "변동사유", "변동주식수", "변동후주식수", "비고"]),
        AppendixDef("APP-02", "별지 2: 특수관계인 거래 현황", ["거래상대방", "관계", "거래유형", "거래금액", "조건"]),
        AppendixDef("APP-03", "별지 3: 소송/분쟁 현황", ["사건번호", "법원", "상대방", "청구액", "진행상황"]),
        AppendixDef("APP-04", "별지 4: 인허가 현황", ["인허가명", "근거법령", "발급기관", "유효기간", "상장영향"]),
    ]
