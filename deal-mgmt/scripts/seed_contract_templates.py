"""5종 계약서 템플릿 시드 데이터 — SPA/SHA/BTA/SSA/MOU.

사용법:
    cd deal-mgmt
    python scripts/seed_contract_templates.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.contract_clause import ContractClause
from app.models.contract_template import ContractTemplate
from app.models.enums import (
    ContractTemplateStatus,
    LegalDocType,
    TemplateVariableInputType,
)
from app.models.template_variable import TemplateVariable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── 공통 변수 (당사자 정보) ─────────────────────────────────────────────────

_PARTY_VARIABLES: list[dict] = [
    {
        "variable_key": "seller_name",
        "input_type": TemplateVariableInputType.TEXT,
        "question_label": "매도인 명칭",
        "description": "매도인(매각자)의 법인명 또는 성명",
        "is_required": True,
        "display_order": 1,
        "group_name": "당사자 정보",
    },
    {
        "variable_key": "seller_address",
        "input_type": TemplateVariableInputType.TEXT,
        "question_label": "매도인 주소",
        "description": "매도인의 등기부 소재지",
        "is_required": True,
        "display_order": 2,
        "group_name": "당사자 정보",
    },
    {
        "variable_key": "seller_representative",
        "input_type": TemplateVariableInputType.TEXT,
        "question_label": "매도인 대표자",
        "is_required": True,
        "display_order": 3,
        "group_name": "당사자 정보",
    },
    {
        "variable_key": "buyer_name",
        "input_type": TemplateVariableInputType.TEXT,
        "question_label": "매수인 명칭",
        "description": "매수인(인수자)의 법인명 또는 성명",
        "is_required": True,
        "display_order": 4,
        "group_name": "당사자 정보",
    },
    {
        "variable_key": "buyer_address",
        "input_type": TemplateVariableInputType.TEXT,
        "question_label": "매수인 주소",
        "is_required": True,
        "display_order": 5,
        "group_name": "당사자 정보",
    },
    {
        "variable_key": "buyer_representative",
        "input_type": TemplateVariableInputType.TEXT,
        "question_label": "매수인 대표자",
        "is_required": True,
        "display_order": 6,
        "group_name": "당사자 정보",
    },
]


# ── SPA (주식매매계약서) ─────────────────────────────────────────────────────

SPA_VARIABLES: list[dict] = [
    *_PARTY_VARIABLES,
    {
        "variable_key": "target_company",
        "input_type": TemplateVariableInputType.TEXT,
        "question_label": "대상회사 명칭",
        "is_required": True,
        "display_order": 10,
        "group_name": "거래 대상",
    },
    {
        "variable_key": "share_count",
        "input_type": TemplateVariableInputType.NUMBER,
        "question_label": "양도 주식 수 (주)",
        "is_required": True,
        "display_order": 11,
        "group_name": "거래 대상",
    },
    {
        "variable_key": "share_ratio",
        "input_type": TemplateVariableInputType.PERCENTAGE,
        "question_label": "지분율 (%)",
        "is_required": True,
        "display_order": 12,
        "group_name": "거래 대상",
    },
    {
        "variable_key": "total_purchase_price",
        "input_type": TemplateVariableInputType.CURRENCY,
        "question_label": "총 매매대금 (원)",
        "is_required": True,
        "display_order": 20,
        "group_name": "거래 조건",
    },
    {
        "variable_key": "price_per_share",
        "input_type": TemplateVariableInputType.CURRENCY,
        "question_label": "주당 매매가격 (원)",
        "is_required": True,
        "display_order": 21,
        "group_name": "거래 조건",
    },
    {
        "variable_key": "signing_date",
        "input_type": TemplateVariableInputType.DATE,
        "question_label": "계약 체결일",
        "is_required": True,
        "display_order": 30,
        "group_name": "일정",
    },
    {
        "variable_key": "closing_date",
        "input_type": TemplateVariableInputType.DATE,
        "question_label": "거래 종결일",
        "is_required": True,
        "display_order": 31,
        "group_name": "일정",
    },
    {
        "variable_key": "escrow_included",
        "input_type": TemplateVariableInputType.BOOLEAN,
        "question_label": "에스크로 포함 여부",
        "default_value": "false",
        "is_required": True,
        "display_order": 40,
        "group_name": "특약 사항",
    },
    {
        "variable_key": "escrow_amount",
        "input_type": TemplateVariableInputType.CURRENCY,
        "question_label": "에스크로 금액 (원)",
        "is_required": True,
        "display_order": 41,
        "group_name": "특약 사항",
        "visible_condition": "escrow_included == True",
    },
    {
        "variable_key": "escrow_period_months",
        "input_type": TemplateVariableInputType.NUMBER,
        "question_label": "에스크로 기간 (개월)",
        "default_value": "12",
        "is_required": True,
        "display_order": 42,
        "group_name": "특약 사항",
        "visible_condition": "escrow_included == True",
    },
    {
        "variable_key": "earnout_included",
        "input_type": TemplateVariableInputType.BOOLEAN,
        "question_label": "어닝아웃 포함 여부",
        "default_value": "false",
        "is_required": True,
        "display_order": 50,
        "group_name": "특약 사항",
    },
    {
        "variable_key": "non_compete_years",
        "input_type": TemplateVariableInputType.NUMBER,
        "question_label": "경업금지 기간 (년)",
        "default_value": "2",
        "is_required": False,
        "display_order": 60,
        "group_name": "특약 사항",
    },
    {
        "variable_key": "governing_law",
        "input_type": TemplateVariableInputType.SELECT,
        "question_label": "준거법",
        "default_value": "대한민국법",
        "is_required": True,
        "display_order": 70,
        "group_name": "기타",
        "select_options": {"대한민국법": "대한민국법", "영국법": "영국법", "뉴욕주법": "뉴욕주법"},
    },
    {
        "variable_key": "dispute_resolution",
        "input_type": TemplateVariableInputType.SELECT,
        "question_label": "분쟁해결 방법",
        "default_value": "대한상사중재원",
        "is_required": True,
        "display_order": 71,
        "group_name": "기타",
        "select_options": {
            "대한상사중재원": "대한상사중재원 중재",
            "서울중앙지방법원": "서울중앙지방법원 소송",
            "ICC": "ICC 국제중재",
            "SIAC": "SIAC 싱가포르 중재",
        },
    },
]

SPA_CLAUSES: list[dict] = [
    {
        "clause_order": 1,
        "title": "정의",
        "is_boilerplate": True,
        "content": (
            "<p>본 계약에서 사용하는 용어의 정의는 다음과 같다.</p>"
            "<ol>"
            '<li>"매도인"이란 {{ seller_name }}을(를) 의미한다.</li>'
            '<li>"매수인"이란 {{ buyer_name }}을(를) 의미한다.</li>'
            '<li>"대상회사"란 {{ target_company }}을(를) 의미한다.</li>'
            '<li>"대상주식"이란 대상회사가 발행한 보통주식 {{ share_count | number_format }}주'
            " (발행주식총수의 {{ share_ratio }}%)를 의미한다.</li>"
            '<li>"매매대금"이란 금 {{ total_purchase_price | number_format }}원을 의미한다.</li>'
            '<li>"거래종결일"이란 {{ closing_date | date_format }}을(를) 의미한다.</li>'
            "</ol>"
        ),
    },
    {
        "clause_order": 2,
        "title": "매매의 목적",
        "content": (
            "<p>매도인은 자신이 보유하고 있는 대상주식을 매수인에게 양도하고, 매수인은 이를 양수하기로 한다.</p>"
        ),
    },
    {
        "clause_order": 3,
        "title": "매매대금 및 지급방법",
        "content": (
            "<p>대상주식의 매매대금은 금 {{ total_purchase_price | number_format }}원"
            " (주당 {{ price_per_share | number_format }}원)으로 한다.</p>"
            "<p>매수인은 거래종결일에 매도인이 지정하는 은행 계좌로 매매대금 전액을 "
            "현금으로 지급하여야 한다.</p>"
        ),
    },
    {
        "clause_order": 4,
        "title": "에스크로",
        "condition_expression": "escrow_included == True",
        "content": (
            "<p>매매대금 중 금 {{ escrow_amount | number_format }}원은 거래종결일로부터 "
            "{{ escrow_period_months }}개월간 에스크로 계좌에 예치한다.</p>"
            "<p>에스크로 해제 조건은 다음과 같다:</p>"
            "<ol>"
            "<li>매도인의 진술 및 보증 위반이 없는 경우</li>"
            "<li>에스크로 기간 만료 시</li>"
            "</ol>"
        ),
    },
    {
        "clause_order": 5,
        "title": "어닝아웃",
        "condition_expression": "earnout_included == True",
        "content": (
            "<p>매매대금의 일부는 대상회사의 거래종결 이후 실적에 따라 "
            '별도 합의된 산정 방식에 의해 추가 지급될 수 있다 (이하 "어닝아웃").</p>'
            "<p>어닝아웃의 세부 조건은 별도 부속서에서 정한다.</p>"
        ),
    },
    {
        "clause_order": 6,
        "title": "거래 선행조건",
        "content": (
            "<p>거래의 종결은 다음 각 호의 선행조건이 모두 충족되는 것을 조건으로 한다.</p>"
            "<ol>"
            "<li>이사회 및 주주총회 승인 완료</li>"
            "<li>관련 행정기관의 인허가 취득 (해당 시)</li>"
            "<li>매도인의 진술 및 보증이 중요한 측면에서 정확할 것</li>"
            "<li>거래종결일까지 중대한 불리한 변경(MAC)이 발생하지 않을 것</li>"
            "</ol>"
        ),
    },
    {
        "clause_order": 7,
        "title": "매도인의 진술 및 보증",
        "content": (
            "<p>매도인은 본 계약 체결일 현재 다음 각 호의 사항이 진실하고 정확함을 "
            "진술하고 보증한다.</p>"
            "<ol>"
            "<li>매도인은 대상주식의 적법한 소유자이며, 대상주식에 어떠한 담보권이나 "
            "제3자의 권리도 설정되어 있지 아니하다.</li>"
            "<li>대상회사는 적법하게 설립되어 유효하게 존속하고 있다.</li>"
            "<li>대상회사의 재무제표는 일반적으로 인정된 회계원칙에 따라 적정하게 "
            "작성되었다.</li>"
            "<li>대상회사에 대하여 계류 중이거나 위협받고 있는 소송 등이 없다.</li>"
            "</ol>"
        ),
    },
    {
        "clause_order": 8,
        "title": "매수인의 진술 및 보증",
        "content": (
            "<p>매수인은 본 계약 체결일 현재 다음 각 호의 사항이 진실하고 정확함을 "
            "진술하고 보증한다.</p>"
            "<ol>"
            "<li>매수인은 본 계약을 체결하고 이행할 충분한 권한을 가지고 있다.</li>"
            "<li>매수인은 매매대금을 지급할 충분한 자금을 보유하고 있다.</li>"
            "</ol>"
        ),
    },
    {
        "clause_order": 9,
        "title": "경업금지",
        "condition_expression": "non_compete_years > 0",
        "content": (
            "<p>매도인은 거래종결일로부터 {{ non_compete_years }}년간 대상회사와 "
            "동일 또는 유사한 사업을 영위하여서는 아니 된다.</p>"
        ),
    },
    {
        "clause_order": 10,
        "title": "비밀유지",
        "is_boilerplate": True,
        "content": (
            "<p>각 당사자는 본 계약의 존재 및 내용, 본 계약과 관련하여 취득한 "
            "상대방의 비밀정보를 제3자에게 공개하여서는 아니 된다.</p>"
        ),
    },
    {
        "clause_order": 11,
        "title": "손해배상",
        "content": (
            "<p>일방 당사자가 본 계약상의 진술, 보증, 확약 또는 의무를 위반한 경우, "
            "상대방은 그로 인하여 발생한 모든 손해의 배상을 청구할 수 있다.</p>"
        ),
    },
    {
        "clause_order": 12,
        "title": "준거법 및 분쟁해결",
        "is_boilerplate": True,
        "content": (
            "<p>본 계약은 {{ governing_law }}에 의하여 해석되고 규율된다.</p>"
            "<p>본 계약과 관련하여 발생하는 모든 분쟁은 "
            "{{ dispute_resolution }}에서 해결한다.</p>"
        ),
    },
    {
        "clause_order": 13,
        "title": "일반 조항",
        "is_boilerplate": True,
        "content": (
            "<p>본 계약은 당사자 간의 완전한 합의를 구성하며, 본 계약 체결 전에 "
            "이루어진 모든 구두 또는 서면 합의를 대체한다.</p>"
            "<p>본 계약의 수정은 양 당사자의 서면 합의에 의해서만 가능하다.</p>"
        ),
    },
]


# ── SHA (주주간계약서) 핵심 조항 ──────────────────────────────────────────────

SHA_VARIABLES: list[dict] = [
    *_PARTY_VARIABLES,
    {
        "variable_key": "target_company",
        "input_type": TemplateVariableInputType.TEXT,
        "question_label": "대상회사 명칭",
        "is_required": True,
        "display_order": 10,
        "group_name": "거래 대상",
    },
    {
        "variable_key": "board_seats_total",
        "input_type": TemplateVariableInputType.NUMBER,
        "question_label": "이사회 총 석수",
        "default_value": "5",
        "is_required": True,
        "display_order": 20,
        "group_name": "지배구조",
    },
    {
        "variable_key": "signing_date",
        "input_type": TemplateVariableInputType.DATE,
        "question_label": "계약 체결일",
        "is_required": True,
        "display_order": 30,
        "group_name": "일정",
    },
    {
        "variable_key": "tag_along_included",
        "input_type": TemplateVariableInputType.BOOLEAN,
        "question_label": "동반매도청구권(Tag-along) 포함",
        "default_value": "true",
        "is_required": True,
        "display_order": 40,
        "group_name": "특약 사항",
    },
    {
        "variable_key": "drag_along_included",
        "input_type": TemplateVariableInputType.BOOLEAN,
        "question_label": "동반매도요구권(Drag-along) 포함",
        "default_value": "false",
        "is_required": True,
        "display_order": 41,
        "group_name": "특약 사항",
    },
    {
        "variable_key": "governing_law",
        "input_type": TemplateVariableInputType.SELECT,
        "question_label": "준거법",
        "default_value": "대한민국법",
        "is_required": True,
        "display_order": 70,
        "group_name": "기타",
        "select_options": {"대한민국법": "대한민국법", "영국법": "영국법"},
    },
    {
        "variable_key": "dispute_resolution",
        "input_type": TemplateVariableInputType.SELECT,
        "question_label": "분쟁해결 방법",
        "default_value": "대한상사중재원",
        "is_required": True,
        "display_order": 71,
        "group_name": "기타",
        "select_options": {"대한상사중재원": "대한상사중재원 중재", "서울중앙지방법원": "서울중앙지방법원 소송"},
    },
]

SHA_CLAUSES: list[dict] = [
    {
        "clause_order": 1,
        "title": "정의",
        "is_boilerplate": True,
        "content": (
            "<p>본 계약에서 사용하는 용어의 정의는 다음과 같다.</p>"
            "<ol>"
            '<li>"주주 갑"이란 {{ seller_name }}을(를) 의미한다.</li>'
            '<li>"주주 을"이란 {{ buyer_name }}을(를) 의미한다.</li>'
            '<li>"대상회사"란 {{ target_company }}을(를) 의미한다.</li>'
            "</ol>"
        ),
    },
    {
        "clause_order": 2,
        "title": "이사회 구성",
        "content": ("<p>대상회사의 이사회는 {{ board_seats_total }}인으로 구성한다.</p>"),
    },
    {
        "clause_order": 3,
        "title": "동반매도청구권 (Tag-along)",
        "condition_expression": "tag_along_included == True",
        "content": (
            "<p>일방 주주가 보유주식의 전부 또는 일부를 제3자에게 양도하고자 하는 경우, "
            "타방 주주는 동일한 조건으로 자신의 지분을 함께 매도할 것을 청구할 수 있다.</p>"
        ),
    },
    {
        "clause_order": 4,
        "title": "동반매도요구권 (Drag-along)",
        "condition_expression": "drag_along_included == True",
        "content": (
            "<p>과반수 주주가 보유주식 전부를 제3자에게 양도하고자 하는 경우, "
            "소수주주에게 동일한 조건으로 함께 매도할 것을 요구할 수 있다.</p>"
        ),
    },
    {
        "clause_order": 5,
        "title": "비밀유지",
        "is_boilerplate": True,
        "content": "<p>각 주주는 대상회사 및 본 계약에 관한 비밀정보를 제3자에게 공개하여서는 아니 된다.</p>",
    },
    {
        "clause_order": 6,
        "title": "준거법 및 분쟁해결",
        "is_boilerplate": True,
        "content": (
            "<p>본 계약은 {{ governing_law }}에 의하여 해석되고 규율된다.</p>"
            "<p>본 계약 관련 분쟁은 {{ dispute_resolution }}에서 해결한다.</p>"
        ),
    },
]


# ── BTA/SSA/MOU — 간소 템플릿 ─────────────────────────────────────────────


def _make_simple_template(
    doc_type_label: str,
    subject_label: str,
    *,
    party_a_label: str = "매도인",
    party_b_label: str = "매수인",
) -> tuple[list[dict], list[dict]]:
    """BTA/SSA/MOU용 간소 변수 + 조항 세트를 생성한다.

    Args:
        doc_type_label: 계약 유형 한글명 (예: "영업양수도", "신주인수")
        subject_label: 거래 대상 한글명 (예: "영업", "신주", "사업")
        party_a_label: 갑측 당사자 호칭 (기본: "매도인")
        party_b_label: 을측 당사자 호칭 (기본: "매수인")
    """
    party_vars = []
    for v in _PARTY_VARIABLES:
        updated = dict(v)
        updated["question_label"] = (
            updated["question_label"].replace("매도인", party_a_label).replace("매수인", party_b_label)
        )
        if updated.get("description"):
            updated["description"] = (
                updated["description"]
                .replace("매도인", party_a_label)
                .replace("매수인", party_b_label)
                .replace("매각자", party_a_label)
                .replace("인수자", party_b_label)
            )
        party_vars.append(updated)
    variables: list[dict] = [
        *party_vars,
        {
            "variable_key": "target_company",
            "input_type": TemplateVariableInputType.TEXT,
            "question_label": f"{subject_label} 명칭",
            "is_required": True,
            "display_order": 10,
            "group_name": "거래 대상",
        },
        {
            "variable_key": "total_purchase_price",
            "input_type": TemplateVariableInputType.CURRENCY,
            "question_label": "대금 (원)",
            "is_required": True,
            "display_order": 20,
            "group_name": "거래 조건",
        },
        {
            "variable_key": "signing_date",
            "input_type": TemplateVariableInputType.DATE,
            "question_label": "계약 체결일",
            "is_required": True,
            "display_order": 30,
            "group_name": "일정",
        },
        {
            "variable_key": "closing_date",
            "input_type": TemplateVariableInputType.DATE,
            "question_label": "거래 종결일",
            "is_required": True,
            "display_order": 31,
            "group_name": "일정",
        },
        {
            "variable_key": "governing_law",
            "input_type": TemplateVariableInputType.SELECT,
            "question_label": "준거법",
            "default_value": "대한민국법",
            "is_required": True,
            "display_order": 70,
            "group_name": "기타",
            "select_options": {"대한민국법": "대한민국법", "영국법": "영국법"},
        },
        {
            "variable_key": "dispute_resolution",
            "input_type": TemplateVariableInputType.SELECT,
            "question_label": "분쟁해결 방법",
            "default_value": "대한상사중재원",
            "is_required": True,
            "display_order": 71,
            "group_name": "기타",
            "select_options": {"대한상사중재원": "대한상사중재원 중재", "서울중앙지방법원": "서울중앙지방법원 소송"},
        },
    ]

    clauses: list[dict] = [
        {
            "clause_order": 1,
            "title": "정의",
            "is_boilerplate": True,
            "content": (
                "<p>본 계약에서 사용하는 용어의 정의는 다음과 같다.</p>"
                "<ol>"
                f'<li>"{party_a_label}"이란 {{{{ seller_name }}}}을(를) 의미한다.</li>'
                f'<li>"{party_b_label}"이란 {{{{ buyer_name }}}}을(를) 의미한다.</li>'
                f'<li>"대상{subject_label}"이란 {{{{ target_company }}}}을(를) 의미한다.</li>'
                "</ol>"
            ),
        },
        {
            "clause_order": 2,
            "title": f"{doc_type_label}의 목적",
            "content": (
                f"<p>{party_a_label}은(는) 대상{subject_label}을(를) {party_b_label}에게 양도하고, "
                f"{party_b_label}은(는) 이를 양수하기로 한다.</p>"
            ),
        },
        {
            "clause_order": 3,
            "title": "대금 및 지급",
            "content": (
                "<p>대금은 금 {{ total_purchase_price | number_format }}원으로 한다.</p>"
                f"<p>{party_b_label}은(는) 거래종결일({{{{ closing_date | date_format }}}})에 "
                f"{party_a_label} 지정 계좌로 전액 지급한다.</p>"
            ),
        },
        {
            "clause_order": 4,
            "title": "진술 및 보증",
            "content": (
                f"<p>{party_a_label}은(는) 다음을 진술하고 보증한다.</p>"
                "<ol>"
                f"<li>대상{subject_label}의 적법한 소유자이다.</li>"
                f"<li>대상{subject_label}에 담보권 등 제3자 권리가 없다.</li>"
                "</ol>"
            ),
        },
        {
            "clause_order": 5,
            "title": "비밀유지",
            "is_boilerplate": True,
            "content": "<p>각 당사자는 본 계약의 존재 및 내용을 비밀로 유지한다.</p>",
        },
        {
            "clause_order": 6,
            "title": "준거법 및 분쟁해결",
            "is_boilerplate": True,
            "content": (
                "<p>본 계약은 {{ governing_law }}에 의하여 해석되고 규율된다.</p>"
                "<p>분쟁은 {{ dispute_resolution }}에서 해결한다.</p>"
            ),
        },
    ]
    return variables, clauses


# ── 템플릿 정의 레지스트리 ─────────────────────────────────────────────────

BTA_VARS, BTA_CLAUSES = _make_simple_template("영업양수도", "영업")
SSA_VARS, SSA_CLAUSES = _make_simple_template("신주인수", "신주", party_a_label="발행회사", party_b_label="인수인")
MOU_VARS, MOU_CLAUSES = _make_simple_template("양해각서", "사업", party_a_label="갑", party_b_label="을")

TEMPLATES: list[dict] = [
    {
        "doc_type": LegalDocType.SPA,
        "name": "주식매매계약서 (SPA) 표준 템플릿",
        "description": "M&A 주식매매계약 표준 양식. 에스크로, 어닝아웃 조건부 조항 포함.",
        "variables": SPA_VARIABLES,
        "clauses": SPA_CLAUSES,
    },
    {
        "doc_type": LegalDocType.SHA,
        "name": "주주간계약서 (SHA) 표준 템플릿",
        "description": "주주간 권리의무 합의서. Tag-along/Drag-along 조건부 조항 포함.",
        "variables": SHA_VARIABLES,
        "clauses": SHA_CLAUSES,
    },
    {
        "doc_type": LegalDocType.BTA,
        "name": "영업양수도계약서 (BTA) 표준 템플릿",
        "description": "영업/사업부문 양수도 계약 표준 양식.",
        "variables": BTA_VARS,
        "clauses": BTA_CLAUSES,
    },
    {
        "doc_type": LegalDocType.SSA,
        "name": "신주인수계약서 (SSA) 표준 템플릿",
        "description": "신주 발행 및 인수 계약 표준 양식.",
        "variables": SSA_VARS,
        "clauses": SSA_CLAUSES,
    },
    {
        "doc_type": LegalDocType.MOU,
        "name": "양해각서 (MOU) 표준 템플릿",
        "description": "M&A 거래 의향 양해각서 표준 양식.",
        "variables": MOU_VARS,
        "clauses": MOU_CLAUSES,
    },
]


# ── 시드 실행 ──────────────────────────────────────────────────────────────


async def _seed(db: AsyncSession) -> None:
    """5종 계약서 템플릿 시드를 삽입한다."""
    # 기존 템플릿을 doc_type별로 확인 (부분 시드 가능)
    existing_types_result = await db.execute(select(ContractTemplate.doc_type).distinct())
    existing_types = {row[0] for row in existing_types_result.fetchall()}
    if len(existing_types) >= len(TEMPLATES):
        logger.info("이미 %d종 템플릿 존재 — 스킵합니다.", len(existing_types))
        return

    for tmpl_def in TEMPLATES:
        if tmpl_def["doc_type"] in existing_types:
            logger.info("⏭ %s 템플릿 이미 존재 — 스킵", tmpl_def["name"])
            continue
        template = ContractTemplate(
            id=uuid.uuid4(),
            doc_type=tmpl_def["doc_type"],
            name=tmpl_def["name"],
            description=tmpl_def["description"],
            version="1.0",
            status=ContractTemplateStatus.ACTIVE,
            created_by_email="system@amic.kr",
        )
        db.add(template)

        for var_def in tmpl_def["variables"]:
            variable = TemplateVariable(
                id=uuid.uuid4(),
                template_id=template.id,
                **var_def,
            )
            db.add(variable)

        for clause_def in tmpl_def["clauses"]:
            clause = ContractClause(
                id=uuid.uuid4(),
                template_id=template.id,
                is_boilerplate=clause_def.get("is_boilerplate", False),
                condition_expression=clause_def.get("condition_expression"),
                clause_order=clause_def["clause_order"],
                title=clause_def["title"],
                content=clause_def["content"],
            )
            db.add(clause)

        logger.info(
            "✓ %s 템플릿 생성 (조항 %d, 변수 %d)",
            tmpl_def["name"],
            len(tmpl_def["clauses"]),
            len(tmpl_def["variables"]),
        )

    await db.commit()
    logger.info("시드 완료 — 5종 계약서 템플릿 생성됨")


async def main() -> None:
    """메인 진입점."""
    async with async_session_factory() as session:
        await _seed(session)


if __name__ == "__main__":
    asyncio.run(main())
