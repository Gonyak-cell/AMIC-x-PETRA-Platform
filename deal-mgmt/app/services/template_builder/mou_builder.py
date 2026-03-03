"""MOU(양해각서) 표준 템플릿 빌더.

M&A 거래 초기 단계에서 사용되는 양해각서의 표준 조항 15개와
변수 23개를 정의한다. 거래 의향, 독점교섭, 실사 범위, 비밀유지 등
구속력 있는/없는 조항을 구분하여 포함한다.
"""

from __future__ import annotations

from .base import ClauseData, TemplateData, VariableData


def build_mou_template() -> TemplateData:
    """MOU 표준 템플릿을 생성한다."""
    return TemplateData(
        doc_type="MOU",
        name="양해각서 (MOU) 표준 템플릿",
        description="한국 M&A 실무 기반 양해각서. 거래 의향, 독점교섭, 실사 범위, 구속력 구분 등 포함.",
        clauses=_build_clauses(),
        variables=_build_variables(),
    )


def _build_clauses() -> list[ClauseData]:
    return [
        ClauseData(
            clause_order=1,
            title="정의",
            content=(
                "<p>본 양해각서에서 사용되는 용어는 아래와 같은 의미를 가진다.</p>\n"
                '<p>"매도 예정자"라 함은 {{ mou_seller_name }}을 의미한다.</p>\n'
                '<p>"매수 예정자"라 함은 {{ mou_buyer_name }}을 의미한다.</p>\n'
                '<p>"대상회사"라 함은 {{ mou_target_name }}을 의미한다.</p>\n'
                '<p>"거래"라 함은 대상회사의 {{ mou_deal_scope }}에 관한 '
                "거래를 의미한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=2,
            title="거래 개요",
            content=(
                "<p>매도 예정자와 매수 예정자는 대상회사에 관한 거래를 진행하기 위한 "
                "상호 양해사항을 본 양해각서에 기재한다.</p>\n"
                "<p>거래 유형: {{ mou_deal_type }}</p>\n"
                "<p>대상 지분율: 약 {{ mou_target_stake }}%</p>\n"
                "<p>예상 거래 규모: {{ mou_estimated_value|currency_format }} "
                "(최종 거래가는 실사 및 밸류에이션 결과에 따라 조정될 수 있다)</p>"
            ),
        ),
        ClauseData(
            clause_order=3,
            title="거래 일정",
            content=(
                "<p>당사자들은 다음 일정에 따라 거래를 진행하기 위하여 성실히 노력한다.</p>\n"
                "<ol>\n<li>양해각서 체결: {{ mou_signing_date|date_format }}</li>\n"
                "<li>실사 착수: 양해각서 체결일로부터 {{ dd_start_days }}일 이내</li>\n"
                "<li>실사 완료: 실사 착수일로부터 {{ dd_duration_weeks }}주 이내</li>\n"
                "<li>본계약(SPA) 체결 목표: {{ spa_target_date|date_format }}</li>\n"
                "<li>거래 종결 목표: {{ closing_target_date|date_format }}</li>\n</ol>\n"
                "<p>위 일정은 예상 일정이며, 당사자 합의에 따라 변경될 수 있다.</p>"
            ),
        ),
        ClauseData(
            clause_order=4,
            title="실사",
            content=(
                "<p>매도 예정자는 매수 예정자가 지정하는 자문사에게 대상회사에 대한 "
                "실사(Due Diligence)를 수행할 수 있도록 합리적인 범위에서 협조한다.</p>\n"
                "<p>실사 범위: {{ dd_scope }}</p>\n"
                "<p>매도 예정자는 실사에 필요한 자료를 성실하게 제공하며, "
                "가상 데이터룸(VDR) 또는 현장 방문을 통한 자료 열람을 허용한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=5,
            title="독점교섭",
            content=(
                "<p>매도 예정자는 본 양해각서 체결일로부터 {{ exclusivity_period_days }}일간 "
                "(독점교섭기간) 매수 예정자 이외의 제3자와 대상회사의 매각에 관한 협의, "
                "정보 제공 또는 계약 체결을 하지 아니한다.</p>\n"
                "<p>독점교섭기간 내에 본계약이 체결되지 아니한 경우, 당사자들의 합의에 "
                "따라 독점교섭기간을 연장할 수 있다.</p>"
            ),
        ),
        ClauseData(
            clause_order=6,
            title="가격 산정 방법",
            content=(
                "<p>거래 가격은 다음 방법론을 참고하여 산정한다.</p>\n"
                "<p>주요 밸류에이션 방법: {{ mou_valuation_method }}</p>\n"
                "<p>참고 지표: {{ mou_valuation_reference }}</p>\n"
                "<p>최종 거래가는 실사 결과 및 당사자 간 협상에 의하여 결정된다.</p>"
            ),
        ),
        ClauseData(
            clause_order=7,
            title="보증금",
            content=(
                "<p>매수 예정자는 거래 의향의 성실성을 담보하기 위하여 "
                "{{ mou_deposit_amount|currency_format }}을 매도 예정자에게 "
                "예치한다(보증금).</p>\n"
                "<p>본계약이 체결되는 경우, 보증금은 매매대금의 일부에 충당한다.</p>\n"
                "<p>매수 예정자의 귀책 사유로 거래가 불성립되는 경우, 보증금은 "
                "매도 예정자에게 귀속된다.</p>\n"
                "<p>매도 예정자의 귀책 사유 또는 불가항력으로 거래가 불성립되는 경우, "
                "보증금은 매수 예정자에게 반환된다.</p>"
            ),
            condition_expression="has_mou_deposit == True",
        ),
        ClauseData(
            clause_order=8,
            title="비밀유지",
            content=(
                "<p>당사자들은 본 양해각서의 존재 및 내용, 거래와 관련하여 제공받은 "
                "모든 정보를 비밀로 유지하여야 한다.</p>\n"
                "<p>비밀유지 의무는 본 양해각서의 종료 또는 만료 후에도 "
                "{{ mou_confidentiality_years }}년간 존속한다.</p>\n"
                "<p>비밀유지 의무의 위반 시, 위반 당사자는 상대방이 입은 실제 손해를 "
                "배상할 책임을 부담한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=9,
            title="구속력의 범위",
            content=(
                "<p>본 양해각서 중 다음 조항은 법적 구속력을 가진다.</p>\n"
                "<ol>\n<li>제5조 (독점교섭)</li>\n"
                "<li>제8조 (비밀유지)</li>\n"
                "<li>제9조 (구속력의 범위)</li>\n"
                "<li>제14조 (준거법 및 분쟁해결)</li>\n</ol>\n"
                "<p>위 조항을 제외한 나머지 조항은 당사자들의 거래 의향을 표시하는 것으로, "
                "법적 구속력이 없다. 법적 구속력 있는 권리·의무 관계는 향후 체결될 "
                "본계약에 의하여 발생한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=10,
            title="비용 부담",
            content=(
                "<p>본 양해각서 및 거래와 관련하여 각 당사자가 부담하는 자문 비용 "
                "(법률, 회계, 세무 자문 등)은 각 당사자가 개별적으로 부담한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=11,
            title="양해각서의 유효기간",
            content=(
                "<p>본 양해각서는 체결일로부터 {{ mou_validity_months }}개월간 유효하다.</p>\n"
                "<p>유효기간 만료 시까지 본계약이 체결되지 아니한 경우, 본 양해각서는 "
                "자동으로 효력을 상실한다. 다만, 당사자들의 서면 합의에 따라 유효기간을 "
                "연장할 수 있다.</p>"
            ),
        ),
        ClauseData(
            clause_order=12,
            title="양해각서의 해지",
            content=(
                "<p>다음 각 호의 사유가 발생한 경우, 당사자는 상대방에게 서면 통지를 "
                "함으로써 본 양해각서를 해지할 수 있다.</p>\n"
                "<ol>\n<li>상대방이 본 양해각서의 구속력 있는 조항을 중대하게 위반한 경우</li>\n"
                "<li>실사 결과 거래 진행이 불합리한 것으로 판단되는 경우</li>\n"
                "<li>관련 법령 변경 또는 정부 규제로 거래가 불가능하게 된 경우</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=13,
            title="통지",
            content=(
                "<p>본 양해각서에 따른 모든 통지는 서면(등기우편, 이메일)으로 하며, "
                "다음 주소로 송달한다.</p>\n"
                "<p>매도 예정자: {{ mou_seller_address }}</p>\n"
                "<p>매수 예정자: {{ mou_buyer_address }}</p>"
            ),
            is_boilerplate=True,
        ),
        ClauseData(
            clause_order=14,
            title="준거법 및 분쟁해결",
            content=(
                "<p>본 양해각서는 대한민국 법률에 따라 해석되고 이행된다.</p>\n"
                "<p>본 양해각서와 관련하여 발생하는 분쟁은 "
                "{{ mou_dispute_resolution }}에 의하여 해결한다.</p>"
            ),
            is_boilerplate=True,
        ),
        ClauseData(
            clause_order=15,
            title="일반조항",
            content=(
                "<p>본 양해각서는 당사자 간의 합의 내용 전부를 구성하며, "
                "본 양해각서 이전의 구두 또는 서면 합의를 대체한다.</p>\n"
                "<p>본 양해각서의 수정 또는 변경은 양 당사자의 서면 합의에 의하여만 "
                "효력을 가진다.</p>\n"
                "<p>본 양해각서는 2부를 작성하여 당사자들이 각 1부씩 보관한다.</p>"
            ),
            is_boilerplate=True,
        ),
    ]


def _build_variables() -> list[VariableData]:
    order = 0

    def _next() -> int:
        nonlocal order
        order += 1
        return order

    return [
        VariableData(
            variable_key="mou_seller_name",
            input_type="TEXT",
            question_label="매도 예정자 명칭",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_buyer_name",
            input_type="TEXT",
            question_label="매수 예정자 명칭",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_target_name",
            input_type="TEXT",
            question_label="대상회사 법인명",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_deal_scope",
            input_type="SELECT",
            question_label="거래 범위",
            select_options={"choices": ["주식 양수도", "신주 인수", "영업 양수도", "합병"]},
            group_name="거래",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_deal_type",
            input_type="TEXT",
            question_label="거래 유형 (상세)",
            group_name="거래",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_target_stake",
            input_type="PERCENTAGE",
            question_label="대상 지분율 (%)",
            group_name="거래",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_estimated_value",
            input_type="CURRENCY",
            question_label="예상 거래 규모 (원)",
            group_name="거래",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_signing_date",
            input_type="DATE",
            question_label="양해각서 체결일",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="dd_start_days",
            input_type="NUMBER",
            question_label="실사 착수 기한 (체결일 후 일수)",
            default_value="7",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="dd_duration_weeks",
            input_type="NUMBER",
            question_label="실사 기간 (주)",
            default_value="4",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="spa_target_date",
            input_type="DATE",
            question_label="본계약(SPA) 체결 목표일",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="closing_target_date",
            input_type="DATE",
            question_label="거래 종결 목표일",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="dd_scope",
            input_type="SELECT",
            question_label="실사 범위",
            select_options={
                "choices": [
                    "재무, 법률, 세무 실사 (Full Scope)",
                    "재무 실사만 (FDD Only)",
                    "법률 실사만 (LDD Only)",
                    "Red-Flag 실사",
                ]
            },
            group_name="실사",
            display_order=_next(),
        ),
        VariableData(
            variable_key="exclusivity_period_days",
            input_type="NUMBER",
            question_label="독점교섭 기간 (일)",
            default_value="60",
            group_name="독점교섭",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_valuation_method",
            input_type="SELECT",
            question_label="밸류에이션 방법",
            select_options={"choices": ["EV/EBITDA 배수법", "DCF (현금흐름할인법)", "유사거래비교법", "순자산가치법"]},
            group_name="가격",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_valuation_reference",
            input_type="TEXT",
            question_label="밸류에이션 참고 지표",
            default_value="최근 3개년 평균 EBITDA",
            group_name="가격",
            display_order=_next(),
        ),
        VariableData(
            variable_key="has_mou_deposit",
            input_type="BOOLEAN",
            question_label="보증금 조항 포함",
            default_value="false",
            group_name="보증금",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_deposit_amount",
            input_type="CURRENCY",
            question_label="보증금 (원)",
            group_name="보증금",
            visible_condition="has_mou_deposit == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_confidentiality_years",
            input_type="NUMBER",
            question_label="비밀유지 기간 (년)",
            default_value="3",
            group_name="비밀유지",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_validity_months",
            input_type="NUMBER",
            question_label="양해각서 유효기간 (개월)",
            default_value="6",
            group_name="유효기간",
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_seller_address",
            input_type="TEXTAREA",
            question_label="매도 예정자 주소 (통지용)",
            group_name="통지",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_buyer_address",
            input_type="TEXTAREA",
            question_label="매수 예정자 주소 (통지용)",
            group_name="통지",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="mou_dispute_resolution",
            input_type="SELECT",
            question_label="분쟁 해결 방법",
            select_options={"choices": ["서울중앙지방법원", "대한상사중재원"]},
            group_name="기타",
            display_order=_next(),
        ),
    ]
