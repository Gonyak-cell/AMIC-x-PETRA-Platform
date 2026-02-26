"""회사분할(Corporate Split) LDD 템플릿 — 8개 섹션.

샘플 보고서 1건 분석 결과:
- 분할 개요 → 분할절차 → 자산/부채 배분 → 인허가 승계 → 계약 승계
  → 인사/노무 → 소송/분쟁 → 세무
- 분할비율/배분 기준 분석이 핵심
"""

from __future__ import annotations

from app.ralph.generators.ldd.templates.base import AppendixDef, ItemDef, LDDTemplate, SectionDef


class CorporateSplitTemplate(LDDTemplate):
    deal_type = "CORPORATE_SPLIT"
    display_name = "회사분할"

    sections = [
        SectionDef(
            section_type="SPLIT_OVERVIEW",
            title="1. 분할 개요",
            items=[
                ItemDef("SPLIT-01", "분할 유형 (물적분할/인적분할/분할합병)"),
                ItemDef("SPLIT-02", "분할 목적 및 사업적 합리성"),
                ItemDef("SPLIT-03", "분할비율 산정 근거"),
                ItemDef("SPLIT-04", "분할기일 및 일정"),
                ItemDef("SPLIT-05", "신설회사/존속회사 구조"),
            ],
        ),
        SectionDef(
            section_type="SPLIT_PROCEDURE",
            title="2. 분할 절차",
            items=[
                ItemDef("PROC-01", "주주총회 특별결의 요건"),
                ItemDef("PROC-02", "채권자 보호절차 (이의제출 기간)"),
                ItemDef("PROC-03", "분할계획서/분할합병계약서 적법성"),
                ItemDef("PROC-04", "주식매수청구권 행사"),
                ItemDef("PROC-05", "분할등기 요건"),
            ],
        ),
        SectionDef(
            section_type="ASSET_ALLOCATION",
            title="3. 자산/부채 배분",
            items=[
                ItemDef("ASSET-01", "유형자산 배분 기준 및 적정성"),
                ItemDef("ASSET-02", "무형자산/영업권 배분"),
                ItemDef("ASSET-03", "부채 배분 기준 (연대책임 범위)"),
                ItemDef("ASSET-04", "우발채무/충당부채 배분"),
                ItemDef("ASSET-05", "공동 사용 자산/계약 처리"),
            ],
        ),
        SectionDef(
            section_type="PERMIT_SUCCESSION",
            title="4. 인허가 승계",
            items=[
                ItemDef("PSUC-01", "영업허가/면허 승계 가능성"),
                ItemDef("PSUC-02", "신규 취득 필요 인허가"),
                ItemDef("PSUC-03", "인허가 공백기간 리스크"),
                ItemDef("PSUC-04", "정부보조금/그랜트 승계 조건"),
            ],
        ),
        SectionDef(
            section_type="CONTRACT_SUCCESSION",
            title="5. 계약 승계",
            items=[
                ItemDef("CSUC-01", "주요 계약 승계 방법 (포괄승계/개별이전)"),
                ItemDef("CSUC-02", "상대방 동의 필요 계약"),
                ItemDef("CSUC-03", "금융계약 승계 (대주단 동의)"),
                ItemDef("CSUC-04", "Change of Control 조항 영향"),
            ],
        ),
        SectionDef(
            section_type="LABOR",
            title="6. 인사 및 노무",
            items=[
                ItemDef("LABOR-01", "근로관계 승계 (포괄승계 원칙)"),
                ItemDef("LABOR-02", "노동조합 대응 및 의견청취"),
                ItemDef("LABOR-03", "퇴직급여 충당 및 이전"),
                ItemDef("LABOR-04", "고용유지 약정"),
            ],
        ),
        SectionDef(
            section_type="LITIGATION",
            title="7. 소송 및 분쟁",
            items=[
                ItemDef("LIT-01", "진행 중 소송 배분"),
                ItemDef("LIT-02", "연대책임 범위 (분할 전 채무)"),
                ItemDef("LIT-03", "잠재적 분쟁 리스크"),
            ],
        ),
        SectionDef(
            section_type="TAX",
            title="8. 세무",
            items=[
                ItemDef("TAX-01", "적격분할 요건 충족 여부"),
                ItemDef("TAX-02", "양도소득세/법인세 과세 이슈"),
                ItemDef("TAX-03", "사후관리 의무 (적격분할 유지)"),
                ItemDef("TAX-04", "부가가치세 영향"),
                ItemDef("TAX-05", "지방세(취득세/등록세) 감면 적용"),
            ],
        ),
    ]

    appendices = [
        AppendixDef("APP-01", "별지 1: 자산/부채 배분표", ["항목", "존속회사", "신설회사", "배분기준", "비고"]),
        AppendixDef("APP-02", "별지 2: 인허가 승계 현황", ["인허가명", "근거법령", "승계가능", "조치사항", "일정"]),
        AppendixDef("APP-03", "별지 3: 주요 계약 승계 현황", ["계약명", "상대방", "승계방법", "동의필요", "현황"]),
    ]
