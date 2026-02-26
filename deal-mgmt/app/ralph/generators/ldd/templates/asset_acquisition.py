"""사업양수도(Asset/Business Acquisition) LDD 템플릿 — 10개 섹션.

M&A 실무에서 주식인수 다음으로 빈도 높은 거래유형.
자산/부채 선택적 인수 구조 → 개별 이전 절차 중심 분석.
"""

from __future__ import annotations

from app.ralph.generators.ldd.templates.base import AppendixDef, ItemDef, LDDTemplate, SectionDef


class AssetAcquisitionTemplate(LDDTemplate):
    deal_type = "ASSET_ACQUISITION"
    display_name = "사업양수도"

    sections = [
        SectionDef(
            section_type="SELLER_OVERVIEW",
            title="1. 매도인 일반",
            items=[
                ItemDef("SELL-01", "매도인 법적 지위 및 권한"),
                ItemDef("SELL-02", "정관상 영업양도 절차 (주총 특별결의)"),
                ItemDef("SELL-03", "이사회/주주총회 결의 요건"),
                ItemDef("SELL-04", "자회사/관계사 관련 사업 범위"),
            ],
        ),
        SectionDef(
            section_type="BUSINESS_SCOPE",
            title="2. 양수 사업 범위",
            items=[
                ItemDef("BIZ-01", "양수 대상 사업부 범위 확정"),
                ItemDef("BIZ-02", "양수 자산 목록 (유형/무형)"),
                ItemDef("BIZ-03", "양수 부채 목록 (인수 부채 범위)"),
                ItemDef("BIZ-04", "제외 자산/부채 확인"),
                ItemDef("BIZ-05", "영업권 산정 근거"),
            ],
        ),
        SectionDef(
            section_type="PERMITS",
            title="3. 인허가 승계",
            items=[
                ItemDef("PERMIT-01", "영업허가/면허 승계 가능성"),
                ItemDef("PERMIT-02", "신규 취득 필요 인허가"),
                ItemDef("PERMIT-03", "인허가 공백기간 리스크"),
                ItemDef("PERMIT-04", "기업결합신고 필요 여부"),
            ],
        ),
        SectionDef(
            section_type="CONTRACTS",
            title="4. 계약 이전",
            items=[
                ItemDef("CONTRACT-01", "주요 계약 이전 방식 (개별 동의)"),
                ItemDef("CONTRACT-02", "이전 불가/거부 위험 계약"),
                ItemDef("CONTRACT-03", "금융계약 이전/재계약"),
                ItemDef("CONTRACT-04", "라이선스 이전 가능성"),
                ItemDef("CONTRACT-05", "임대차 계약 승계"),
            ],
        ),
        SectionDef(
            section_type="LABOR",
            title="5. 근로관계 승계",
            items=[
                ItemDef("LABOR-01", "근로관계 포괄 승계 vs 개별 동의"),
                ItemDef("LABOR-02", "핵심인력 이전 합의"),
                ItemDef("LABOR-03", "노동조합 대응 (의견청취 의무)"),
                ItemDef("LABOR-04", "퇴직급여 정산/승계"),
                ItemDef("LABOR-05", "비경쟁/비밀유지 의무 승계"),
            ],
        ),
        SectionDef(
            section_type="REAL_ESTATE",
            title="6. 부동산/자산 이전",
            items=[
                ItemDef("RE-01", "부동산 소유권 이전 절차"),
                ItemDef("RE-02", "담보/제한물권 처리"),
                ItemDef("RE-03", "기계장비/동산 이전"),
                ItemDef("RE-04", "환경오염 책임 범위"),
            ],
        ),
        SectionDef(
            section_type="IP",
            title="7. 지식재산권 이전",
            items=[
                ItemDef("IP-01", "특허/상표 이전 등록"),
                ItemDef("IP-02", "소프트웨어/데이터 이전"),
                ItemDef("IP-03", "제3자 라이선스 이전 동의"),
                ItemDef("IP-04", "영업비밀 보호 조치"),
            ],
        ),
        SectionDef(
            section_type="LITIGATION",
            title="8. 소송 및 분쟁",
            items=[
                ItemDef("LIT-01", "양수 사업 관련 소송 현황"),
                ItemDef("LIT-02", "잠재적 채무 (우발부채)"),
                ItemDef("LIT-03", "상호 사용 관련 분쟁 위험"),
                ItemDef("LIT-04", "채권자 이의 절차"),
            ],
        ),
        SectionDef(
            section_type="TAX",
            title="9. 세무",
            items=[
                ItemDef("TAX-01", "사업양수도 부가가치세 과세 여부"),
                ItemDef("TAX-02", "자산 취득가액 배분 (PPA)"),
                ItemDef("TAX-03", "취득세/등록세 (부동산/차량)"),
                ItemDef("TAX-04", "이전가격 이슈 (특수관계인 간)"),
                ItemDef("TAX-05", "미지급 세금 책임 범위"),
            ],
        ),
        SectionDef(
            section_type="DATA_IT",
            title="10. 개인정보 및 IT",
            items=[
                ItemDef("IT-01", "개인정보 이전 동의 절차"),
                ItemDef("IT-02", "IT 시스템 분리/이전 계획"),
                ItemDef("IT-03", "데이터 마이그레이션 리스크"),
            ],
        ),
    ]

    appendices = [
        AppendixDef("APP-01", "별지 1: 양수 자산 목록", ["분류", "항목", "장부가", "평가가", "이전방법"]),
        AppendixDef("APP-02", "별지 2: 양수 부채 목록", ["분류", "항목", "금액", "채권자", "승계조건"]),
        AppendixDef("APP-03", "별지 3: 계약 이전 현황", ["계약명", "상대방", "이전방법", "동의필요", "상태"]),
        AppendixDef("APP-04", "별지 4: 인허가 승계 현황", ["인허가명", "근거법령", "승계가능", "조치사항", "일정"]),
    ]
