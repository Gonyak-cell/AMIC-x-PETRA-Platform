"""종류주식투자(Preferred Stock Investment) LDD 템플릿 — 9개 섹션.

샘플 보고서 4건 분석 결과:
- 지분/지배구조 → 인허가 → 계약 → 부동산 → 인사노무
  → 개인정보 → 소송 → IP/IT → 보험
- 투자자보호 조항 중심 분석
"""

from __future__ import annotations

from app.ralph.generators.ldd.templates.base import AppendixDef, ItemDef, LDDTemplate, SectionDef


class PreferredStockTemplate(LDDTemplate):
    deal_type = "PREFERRED_STOCK"
    display_name = "종류주식투자"

    sections = [
        SectionDef(
            section_type="GOVERNANCE",
            title="1. 지분 및 지배구조",
            items=[
                ItemDef("CORP-01", "설립/등기/정관 검토"),
                ItemDef("CORP-02", "이사회 구성 및 의사결정 구조"),
                ItemDef("CORP-03", "주주명부 및 지분 현황"),
                ItemDef("CORP-04", "기존 투자계약 (기존 투자자 권리)"),
                ItemDef("CORP-05", "신주발행 절차 적법성"),
                ItemDef("CORP-06", "종류주식 내용 (전환/상환/의결권)"),
                ItemDef("CORP-07", "투자자 보호 조항 (Tag-along/Drag-along)"),
            ],
        ),
        SectionDef(
            section_type="PERMITS",
            title="2. 인허가 및 규제",
            items=[
                ItemDef("PERMIT-01", "영업허가/면허 유효성"),
                ItemDef("PERMIT-02", "외국인투자 관련 규제"),
                ItemDef("PERMIT-03", "정부보조금 조건 (지분변동 시 회수)"),
                ItemDef("PERMIT-04", "공정거래 이슈"),
            ],
        ),
        SectionDef(
            section_type="CONTRACTS",
            title="3. 주요 계약",
            items=[
                ItemDef("CONTRACT-01", "주요 고객계약 (매출집중도)"),
                ItemDef("CONTRACT-02", "주요 공급계약"),
                ItemDef("CONTRACT-03", "금융계약 (기한이익상실 조항)"),
                ItemDef("CONTRACT-04", "Change of Control 조항 영향"),
                ItemDef("CONTRACT-05", "라이선스 계약"),
            ],
        ),
        SectionDef(
            section_type="REAL_ESTATE",
            title="4. 부동산",
            items=[
                ItemDef("RE-01", "부동산 소유권 및 권원"),
                ItemDef("RE-02", "저당권/담보 현황"),
                ItemDef("RE-03", "임차계약 현황"),
                ItemDef("RE-04", "환경오염 이력"),
            ],
        ),
        SectionDef(
            section_type="LABOR",
            title="5. 인사 및 노무",
            items=[
                ItemDef("LABOR-01", "근로계약 및 취업규칙"),
                ItemDef("LABOR-02", "핵심인력 계약 (비경쟁/비밀유지)"),
                ItemDef("LABOR-03", "스톡옵션/RSU 현황"),
                ItemDef("LABOR-04", "노무 분쟁 이력"),
                ItemDef("LABOR-05", "퇴직급여 적립 현황"),
            ],
        ),
        SectionDef(
            section_type="DATA_IT",
            title="6. 개인정보 및 IT",
            items=[
                ItemDef("IT-01", "개인정보 처리 현황 (PIPA 준수)"),
                ItemDef("IT-02", "정보보호 인증 (ISMS/ISO)"),
                ItemDef("IT-03", "핵심 IT 시스템 현황"),
                ItemDef("IT-04", "데이터 유출/보안사고 이력"),
            ],
        ),
        SectionDef(
            section_type="LITIGATION",
            title="7. 소송 및 분쟁",
            items=[
                ItemDef("LIT-01", "진행 중 민사 소송"),
                ItemDef("LIT-02", "진행 중 형사/행정 절차"),
                ItemDef("LIT-03", "행정제재 이력"),
                ItemDef("LIT-04", "잠재적 분쟁 리스크"),
            ],
        ),
        SectionDef(
            section_type="IP",
            title="8. 지식재산권",
            items=[
                ItemDef("IP-01", "특허/실용신안 포트폴리오"),
                ItemDef("IP-02", "상표/디자인권 현황"),
                ItemDef("IP-03", "제3자 IP 침해 가능성"),
                ItemDef("IP-04", "오픈소스 라이선스 준수"),
                ItemDef("IP-05", "직무발명 보상 규정"),
            ],
        ),
        SectionDef(
            section_type="INSURANCE",
            title="9. 보험",
            items=[
                ItemDef("INS-01", "D&O 보험 (임원배상책임)"),
                ItemDef("INS-02", "화재/영업배상 보험"),
                ItemDef("INS-03", "보험 부보 적정성 검토"),
            ],
        ),
    ]

    appendices = [
        AppendixDef("APP-01", "별지 1: 지분/자본 변동 이력", ["일자", "변동유형", "주식수", "가액", "투자자"]),
        AppendixDef("APP-02", "별지 2: 기존 투자계약 주요 조건", ["투자자", "투자일", "종류", "전환비율", "보호조항"]),
        AppendixDef("APP-03", "별지 3: 소송/분쟁 목록", ["사건번호", "법원", "상대방", "청구액", "진행상황"]),
        AppendixDef("APP-04", "별지 4: IP 포트폴리오", ["유형", "명칭", "등록번호", "출원일", "만료일"]),
    ]
