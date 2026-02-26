"""주식인수(Stock Acquisition) LDD 템플릿 — 11개 섹션.

샘플 보고서 15건 분석 결과:
- 기업일반 → 인허가 → 영업계약 → 금융계약 → 공정거래 → 소송 → IP → 부동산 → 환경 → 보험 → 인사노무
- 별지 4-6개, 그룹사별 분석 포함
"""

from __future__ import annotations

from app.ralph.generators.ldd.templates.base import AppendixDef, ItemDef, LDDTemplate, SectionDef


class StockAcquisitionTemplate(LDDTemplate):
    deal_type = "STOCK_ACQUISITION"
    display_name = "주식인수"

    sections = [
        SectionDef(
            section_type="GOVERNANCE",
            title="1. 기업 일반 및 지배구조",
            items=[
                ItemDef("CORP-01", "설립/등기/정관 검토"),
                ItemDef("CORP-02", "이사회 의사록 검토"),
                ItemDef("CORP-03", "주주명부 적정성"),
                ItemDef("CORP-04", "임원 선임 및 등기"),
                ItemDef("CORP-05", "자기거래/이해충돌"),
                ItemDef("CORP-06", "자회사/관계사 현황"),
                ItemDef("CORP-07", "지점/영업소 현황"),
            ],
        ),
        SectionDef(
            section_type="CAPITAL",
            title="2. 자본구조 및 주주협약",
            items=[
                ItemDef("CAP-01", "발행주식 및 자본금 변동"),
                ItemDef("CAP-02", "CB/BW/전환사채 조건"),
                ItemDef("CAP-03", "스톡옵션/ESOP 현황"),
                ItemDef("CAP-04", "우선주 내용 (환수권/의결권/배당)"),
                ItemDef("CAP-05", "주주협약(SHA) 검토"),
                ItemDef("CAP-06", "주식 양도제한 조항"),
            ],
        ),
        SectionDef(
            section_type="PERMITS",
            title="3. 인허가 및 규제",
            items=[
                ItemDef("PERMIT-01", "영업허가/면허 유효성"),
                ItemDef("PERMIT-02", "Change of Control 시 인허가 영향"),
                ItemDef("PERMIT-03", "정부보조금/그랜트 조건 (회수 위험)"),
                ItemDef("PERMIT-04", "공정거래 이슈 (기업결합신고)"),
                ItemDef("PERMIT-05", "해외 인허가 (기업결합신고 해당 시)"),
                ItemDef("PERMIT-06", "외국인투자 관련 규제"),
            ],
        ),
        SectionDef(
            section_type="CONTRACTS",
            title="4. 영업 계약",
            items=[
                ItemDef("CONTRACT-01", "주요 고객계약 (종료조건/매출집중도)"),
                ItemDef("CONTRACT-02", "주요 공급계약 (대체가능성)"),
                ItemDef("CONTRACT-03", "Change of Control 조항 일제 확인"),
                ItemDef("CONTRACT-04", "계약 위반/분쟁 가능성"),
                ItemDef("CONTRACT-05", "라이선스 계약 (이전가능성)"),
                ItemDef("CONTRACT-06", "장기 계약 및 독점 공급 조건"),
            ],
        ),
        SectionDef(
            section_type="FINANCE_CONTRACTS",
            title="5. 금융 계약",
            items=[
                ItemDef("FIN-01", "차입금 현황 (기한이익상실 조항)"),
                ItemDef("FIN-02", "담보/보증 제공 현황"),
                ItemDef("FIN-03", "금융 약정(Covenant) 준수"),
                ItemDef("FIN-04", "리스/할부 계약"),
                ItemDef("FIN-05", "파생상품/헤지 계약"),
            ],
        ),
        SectionDef(
            section_type="ANTITRUST",
            title="6. 공정거래",
            items=[
                ItemDef("AT-01", "시장지배적 지위 해당 여부"),
                ItemDef("AT-02", "부당 공동행위(담합) 이력"),
                ItemDef("AT-03", "불공정거래행위 이력"),
                ItemDef("AT-04", "기업집단 지정/공시 의무"),
                ItemDef("AT-05", "하도급 관련 이슈"),
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
                ItemDef("LIT-05", "규제기관 조사 이력"),
            ],
        ),
        SectionDef(
            section_type="IP",
            title="8. 지식재산권",
            items=[
                ItemDef("IP-01", "특허/실용신안 유효성"),
                ItemDef("IP-02", "상표/디자인권 현황"),
                ItemDef("IP-03", "소프트웨어 라이선스 준수"),
                ItemDef("IP-04", "제3자 IP 침해 가능성"),
                ItemDef("IP-05", "직무발명 규정 및 보상 청구 위험"),
            ],
        ),
        SectionDef(
            section_type="REAL_ESTATE",
            title="9. 부동산 및 환경",
            items=[
                ItemDef("RE-01", "부동산 소유권 등기 및 하자"),
                ItemDef("RE-02", "저당권/전세권 현황"),
                ItemDef("RE-03", "임차계약 (종료 위험)"),
                ItemDef("RE-04", "환경오염 이력 및 오염토양"),
                ItemDef("RE-05", "지역지구 제한 (용도변경)"),
                ItemDef("RE-06", "보험 현황 (부보 적정성)"),
            ],
        ),
        SectionDef(
            section_type="LABOR",
            title="10. 인사 및 노무",
            items=[
                ItemDef("LABOR-01", "근로계약 및 취업규칙"),
                ItemDef("LABOR-02", "노동조합 및 단체협약"),
                ItemDef("LABOR-03", "퇴직급여 및 연금 적립"),
                ItemDef("LABOR-04", "임원 보상 및 스톡옵션"),
                ItemDef("LABOR-05", "노무 분쟁 이력"),
                ItemDef("LABOR-06", "미지급 임금 및 보너스"),
            ],
        ),
        SectionDef(
            section_type="TAX",
            title="11. 조세",
            items=[
                ItemDef("TAX-01", "최근 3년 세무신고 적정성"),
                ItemDef("TAX-02", "법인세 과세표준 및 납부 이력"),
                ItemDef("TAX-03", "부가가치세 신고/납부"),
                ItemDef("TAX-04", "이전가격 (특수관계인 거래)"),
                ItemDef("TAX-05", "미지급 세금/가산세/세무조사 진행"),
            ],
        ),
    ]

    appendices = [
        AppendixDef("APP-01", "별지 1: 소송/분쟁 목록", ["사건번호", "법원", "상대방", "청구액", "진행상황", "예상결과"]),
        AppendixDef("APP-02", "별지 2: 지식재산권 목록", ["유형", "명칭", "등록번호", "출원일", "만료일", "상태"]),
        AppendixDef("APP-03", "별지 3: 부동산 현황", ["소재지", "면적", "용도", "소유형태", "담보설정", "감정가"]),
        AppendixDef("APP-04", "별지 4: 주요 계약 목록", ["계약명", "상대방", "기간", "금액", "CoC조항", "비고"]),
        AppendixDef("APP-05", "별지 5: 보험 현황", ["보험종류", "보험사", "보험금액", "보험기간", "부보대상"]),
        AppendixDef("APP-06", "별지 6: 인허가 목록", ["인허가명", "근거법령", "발급기관", "유효기간", "CoC영향"]),
    ]
