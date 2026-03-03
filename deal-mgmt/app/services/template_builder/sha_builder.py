"""SHA(주주간계약) 표준 템플릿 빌더.

한국 M&A/투자 실무에서 사용되는 주주간계약서의 표준 조항 16개와
변수 33개를 정의한다. 이사회/주주총회 거버넌스, 동반매도/우선매수,
교착상태 해결 등 주주간 권리·의무 조항을 포함한다.
"""

from __future__ import annotations

from .base import ClauseData, TemplateData, VariableData


def build_sha_template() -> TemplateData:
    """SHA 표준 템플릿을 생성한다."""
    return TemplateData(
        doc_type="SHA",
        name="주주간계약서 (SHA) 표준 템플릿",
        description="한국 M&A/투자 실무 기반 주주간계약서. 거버넌스, 주식 양도 제한, 교착상태 해결 등 포함.",
        clauses=_build_clauses(),
        variables=_build_variables(),
    )


def _build_clauses() -> list[ClauseData]:
    return [
        ClauseData(
            clause_order=1,
            title="정의",
            content=(
                "<p>본 계약에서 사용되는 용어는 달리 정의되지 아니하는 한 아래와 같은 의미를 가진다.</p>\n"
                '<p>"회사"라 함은 {{ company_name }}을 의미한다.</p>\n'
                '<p>"주주 A"라 함은 {{ shareholder_a_name }}을 의미한다.</p>\n'
                '<p>"주주 B"라 함은 {{ shareholder_b_name }}을 의미한다.</p>\n'
                '<p>"지분비율"이라 함은 주주 A {{ shareholder_a_stake }}%, '
                "주주 B {{ shareholder_b_stake }}%의 비율을 의미한다.</p>\n"
                '<p>"최초 투자금"이라 함은 각 주주가 회사에 투자한 금액으로서, '
                "주주 A {{ investment_amount_a|currency_format }}, "
                "주주 B {{ investment_amount_b|currency_format }}을 의미한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=2,
            title="목적",
            content=(
                "<p>본 계약은 회사의 경영 및 운영에 관한 주주들의 권리·의무를 규정하고, "
                "주주 간의 관계를 규율하는 것을 목적으로 한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=3,
            title="이사회 구성 및 운영",
            content=(
                "<p>회사의 이사회는 {{ total_directors }}명의 이사로 구성한다.</p>\n"
                "<p>주주 A는 {{ directors_nominated_a }}명의 이사를 지명하고, "
                "주주 B는 {{ directors_nominated_b }}명의 이사를 지명한다.</p>\n"
                "<p>이사회의 의장은 {{ board_chair_nominator }}가 지명한 이사 중에서 선임한다.</p>\n"
                "<p>이사회는 {{ board_quorum }}의 출석으로 성립하며, "
                "출석 이사 과반수의 찬성으로 의결한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=4,
            title="주주총회 운영",
            content=(
                "<p>주주총회의 소집 통지는 회의일 {{ notice_period_days }}일 전까지 "
                "서면으로 발송하여야 한다.</p>\n"
                "<p>다음 각 호의 사항은 발행주식 총수의 {{ special_resolution_threshold }}% "
                "이상의 동의가 있어야 승인된다(특별결의사항).</p>\n"
                "<ol>\n<li>정관의 변경</li>\n<li>신주의 발행</li>\n"
                "<li>합병, 분할, 해산</li>\n<li>자본금의 감소</li>\n"
                "<li>{{ additional_special_matters }}</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=5,
            title="사전 동의 사항",
            content=(
                "<p>회사가 다음 각 호의 행위를 하고자 하는 경우, 모든 주주의 사전 서면 동의를 "
                "얻어야 한다.</p>\n"
                "<ol>\n<li>{{ consent_threshold|currency_format }}을 초과하는 차입 또는 보증</li>\n"
                "<li>주요 자산의 처분 또는 취득 (장부가 기준 {{ asset_threshold|currency_format }} 초과)</li>\n"
                "<li>제3자와의 합작투자, 파트너십 또는 전략적 제휴</li>\n"
                "<li>배당의 결정 및 배당률의 변경</li>\n"
                "<li>임원의 선임 및 해임, 임원 보수 변경</li>\n"
                "<li>사업 영역의 변경 또는 신규 사업 진출</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=6,
            title="주식 양도 제한",
            content=(
                "<p>주주는 본 계약에서 허용하는 경우를 제외하고, 상대방 주주의 사전 "
                "서면 동의 없이 회사의 주식을 제3자에게 양도할 수 없다.</p>\n"
                "<p>양도 제한 기간(Lock-up): 본 계약 체결일로부터 {{ lockup_period_years }}년</p>"
            ),
        ),
        ClauseData(
            clause_order=7,
            title="우선매수권",
            content=(
                "<p>주주가 보유 주식의 전부 또는 일부를 제3자에게 양도하고자 하는 경우, "
                "해당 주주(양도주주)는 양도 의사를 상대방 주주에게 서면으로 통지하여야 한다.</p>\n"
                "<p>상대방 주주는 통지 수령일로부터 {{ rofr_exercise_days }}일 이내에 동일한 "
                "조건으로 해당 주식을 우선 매수할 권리를 가진다(우선매수권, Right of First Refusal).</p>\n"
                "<p>우선매수권이 행사되지 아니한 경우, 양도주주는 통지된 조건과 동일하거나 "
                "그보다 유리한 조건으로 제3자에게 주식을 양도할 수 있다.</p>"
            ),
        ),
        ClauseData(
            clause_order=8,
            title="동반매도청구권",
            content=(
                "<p>주주 A가 보유 주식의 전부를 제3자에게 양도하고자 하는 경우, "
                "주주 A는 주주 B에게 동일한 조건으로 주주 B의 보유 주식 전부를 "
                "함께 양도할 것을 청구할 수 있다(Drag-Along Right).</p>\n"
                "<p>주주 B는 해당 청구를 수령한 날로부터 {{ drag_along_response_days }}일 "
                "이내에 양도에 동의하여야 한다.</p>"
            ),
            condition_expression="has_drag_along == True",
        ),
        ClauseData(
            clause_order=9,
            title="동반매도참여권",
            content=(
                "<p>주주 A가 보유 주식의 전부 또는 일부를 제3자에게 양도하고자 하는 경우, "
                "주주 B는 동일한 비율 및 조건으로 본인의 보유 주식을 함께 양도할 것을 "
                "요청할 수 있다(Tag-Along Right).</p>\n"
                "<p>주주 B의 동반매도참여권은 양도 통지 수령일로부터 "
                "{{ tag_along_exercise_days }}일 이내에 행사하여야 한다.</p>"
            ),
            condition_expression="has_tag_along == True",
        ),
        ClauseData(
            clause_order=10,
            title="교착상태 해결",
            content=(
                "<p>이사회 또는 주주총회에서 중요 안건에 대하여 의결이 이루어지지 아니하는 "
                "경우(교착상태), 당사자들은 다음 절차에 따라 해결을 도모한다.</p>\n"
                "<ol>\n<li>교착상태 발생 후 {{ deadlock_negotiation_days }}일간 성실한 협의</li>\n"
                "<li>협의 실패 시, 독립적인 제3자 중재인의 중재</li>\n"
                "<li>중재에도 불구하고 해결되지 아니하는 경우, "
                "{{ deadlock_resolution_method }}</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=11,
            title="배당 정책",
            content=(
                "<p>회사는 매 사업연도 종료 후 {{ dividend_payout_period_months }}개월 이내에 "
                "배당 가능 이익의 {{ dividend_payout_ratio }}% 이상을 주주에게 배당한다.</p>\n"
                "<p>배당의 구체적인 금액 및 시기는 이사회 결의에 따르되, 회사의 재무건전성 및 "
                "사업 계획에 필요한 재투자 소요를 고려하여 결정한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=12,
            title="풋옵션",
            content=(
                "<p>다음 각 호의 사유가 발생한 경우, 주주 B는 주주 A에 대하여 주주 B 보유 "
                "주식의 전부를 {{ put_option_price_method }}로 산정된 가격에 매수할 것을 "
                "청구할 수 있다(풋옵션).</p>\n"
                "<ol>\n<li>주주 A의 본 계약 중대한 위반</li>\n"
                "<li>회사의 연속 {{ put_trigger_loss_years }}년 영업손실 발생</li>\n"
                "<li>기타 당사자 합의 사유</li>\n</ol>"
            ),
            condition_expression="has_put_option == True",
        ),
        ClauseData(
            clause_order=13,
            title="정보 접근권",
            content=(
                "<p>각 주주는 회사의 재무제표, 사업보고서, 이사회 의사록 등 경영 정보에 "
                "대한 열람 및 등사 청구권을 가진다.</p>\n"
                "<p>회사는 매 분기 종료 후 {{ financial_report_days }}일 이내에 "
                "분기 재무제표를 주주에게 제공하여야 한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=14,
            title="비밀유지",
            content=(
                "<p>당사자들은 본 계약 및 회사의 경영에 관한 모든 비밀정보를 비밀로 "
                "유지하며, 비밀유지 의무는 본 계약 종료 후 {{ sha_confidentiality_years }}년간 "
                "존속한다.</p>"
            ),
            is_boilerplate=True,
        ),
        ClauseData(
            clause_order=15,
            title="계약의 종료",
            content=(
                "<p>본 계약은 다음 각 호의 사유 중 하나가 발생한 경우 종료된다.</p>\n"
                "<ol>\n<li>모든 주주의 서면 합의</li>\n"
                "<li>일방 주주가 회사의 주식 전부를 타방 주주에게 양도한 경우</li>\n"
                "<li>회사의 해산 또는 청산</li>\n"
                "<li>회사의 기업공개(IPO) 완료</li>\n</ol>"
            ),
            is_boilerplate=True,
        ),
        ClauseData(
            clause_order=16,
            title="준거법 및 분쟁해결",
            content=(
                "<p>본 계약은 대한민국 법률에 따라 해석되고 이행된다.</p>\n"
                "<p>본 계약과 관련하여 발생하는 분쟁은 {{ sha_dispute_resolution }}에 "
                "의하여 해결한다.</p>"
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
            variable_key="company_name",
            input_type="TEXT",
            question_label="회사 법인명",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="shareholder_a_name",
            input_type="TEXT",
            question_label="주주 A 명칭",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="shareholder_b_name",
            input_type="TEXT",
            question_label="주주 B 명칭",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="shareholder_a_stake",
            input_type="PERCENTAGE",
            question_label="주주 A 지분율 (%)",
            group_name="지분",
            display_order=_next(),
        ),
        VariableData(
            variable_key="shareholder_b_stake",
            input_type="PERCENTAGE",
            question_label="주주 B 지분율 (%)",
            group_name="지분",
            display_order=_next(),
        ),
        VariableData(
            variable_key="investment_amount_a",
            input_type="CURRENCY",
            question_label="주주 A 투자금 (원)",
            group_name="지분",
            display_order=_next(),
        ),
        VariableData(
            variable_key="investment_amount_b",
            input_type="CURRENCY",
            question_label="주주 B 투자금 (원)",
            group_name="지분",
            display_order=_next(),
        ),
        VariableData(
            variable_key="total_directors",
            input_type="NUMBER",
            question_label="이사회 이사 수",
            default_value="5",
            group_name="거버넌스",
            display_order=_next(),
        ),
        VariableData(
            variable_key="directors_nominated_a",
            input_type="NUMBER",
            question_label="주주 A 지명 이사 수",
            default_value="3",
            group_name="거버넌스",
            display_order=_next(),
        ),
        VariableData(
            variable_key="directors_nominated_b",
            input_type="NUMBER",
            question_label="주주 B 지명 이사 수",
            default_value="2",
            group_name="거버넌스",
            display_order=_next(),
        ),
        VariableData(
            variable_key="board_chair_nominator",
            input_type="SELECT",
            question_label="이사회 의장 지명권자",
            select_options={"choices": ["주주 A", "주주 B", "교대"]},
            group_name="거버넌스",
            display_order=_next(),
        ),
        VariableData(
            variable_key="board_quorum",
            input_type="TEXT",
            question_label="이사회 의사정족수",
            default_value="재적이사 과반수",
            group_name="거버넌스",
            display_order=_next(),
        ),
        VariableData(
            variable_key="notice_period_days",
            input_type="NUMBER",
            question_label="주주총회 소집 통지 기간 (일)",
            default_value="14",
            group_name="주주총회",
            display_order=_next(),
        ),
        VariableData(
            variable_key="special_resolution_threshold",
            input_type="NUMBER",
            question_label="특별결의 동의 비율 (%)",
            default_value="67",
            group_name="주주총회",
            display_order=_next(),
        ),
        VariableData(
            variable_key="additional_special_matters",
            input_type="TEXTAREA",
            question_label="추가 특별결의 사항",
            default_value="해당 없음",
            group_name="주주총회",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="consent_threshold",
            input_type="CURRENCY",
            question_label="사전 동의 기준 차입 한도 (원)",
            group_name="사전 동의",
            display_order=_next(),
        ),
        VariableData(
            variable_key="asset_threshold",
            input_type="CURRENCY",
            question_label="사전 동의 기준 자산 한도 (원)",
            group_name="사전 동의",
            display_order=_next(),
        ),
        VariableData(
            variable_key="lockup_period_years",
            input_type="NUMBER",
            question_label="양도 제한 기간 (년)",
            default_value="3",
            group_name="양도 제한",
            display_order=_next(),
        ),
        VariableData(
            variable_key="rofr_exercise_days",
            input_type="NUMBER",
            question_label="우선매수권 행사 기간 (일)",
            default_value="30",
            group_name="양도 제한",
            display_order=_next(),
        ),
        VariableData(
            variable_key="has_drag_along",
            input_type="BOOLEAN",
            question_label="동반매도청구권 포함 여부",
            default_value="true",
            group_name="양도",
            display_order=_next(),
        ),
        VariableData(
            variable_key="drag_along_response_days",
            input_type="NUMBER",
            question_label="동반매도 응답 기간 (일)",
            default_value="30",
            group_name="양도",
            visible_condition="has_drag_along == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="has_tag_along",
            input_type="BOOLEAN",
            question_label="동반매도참여권 포함 여부",
            default_value="true",
            group_name="양도",
            display_order=_next(),
        ),
        VariableData(
            variable_key="tag_along_exercise_days",
            input_type="NUMBER",
            question_label="동반매도참여 행사 기간 (일)",
            default_value="30",
            group_name="양도",
            visible_condition="has_tag_along == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="deadlock_negotiation_days",
            input_type="NUMBER",
            question_label="교착상태 협의 기간 (일)",
            default_value="30",
            group_name="교착상태",
            display_order=_next(),
        ),
        VariableData(
            variable_key="deadlock_resolution_method",
            input_type="SELECT",
            question_label="교착상태 최종 해결 방법",
            select_options={"choices": ["Russian Roulette 조항", "Texas Shootout 조항", "강제 매각"]},
            group_name="교착상태",
            display_order=_next(),
        ),
        VariableData(
            variable_key="dividend_payout_period_months",
            input_type="NUMBER",
            question_label="배당 지급 기한 (월)",
            default_value="3",
            group_name="배당",
            display_order=_next(),
        ),
        VariableData(
            variable_key="dividend_payout_ratio",
            input_type="NUMBER",
            question_label="최소 배당 비율 (%)",
            default_value="30",
            group_name="배당",
            display_order=_next(),
        ),
        VariableData(
            variable_key="has_put_option",
            input_type="BOOLEAN",
            question_label="풋옵션 포함 여부",
            default_value="false",
            group_name="풋옵션",
            display_order=_next(),
        ),
        VariableData(
            variable_key="put_option_price_method",
            input_type="SELECT",
            question_label="풋옵션 가격 산정 방법",
            select_options={"choices": ["공정가치 (독립 감정)", "EV/EBITDA 배수", "장부가"]},
            group_name="풋옵션",
            visible_condition="has_put_option == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="put_trigger_loss_years",
            input_type="NUMBER",
            question_label="풋옵션 발동 연속 손실 기간 (년)",
            default_value="3",
            group_name="풋옵션",
            visible_condition="has_put_option == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="financial_report_days",
            input_type="NUMBER",
            question_label="분기 재무제표 제출 기한 (일)",
            default_value="45",
            group_name="정보 접근",
            display_order=_next(),
        ),
        VariableData(
            variable_key="sha_confidentiality_years",
            input_type="NUMBER",
            question_label="비밀유지 기간 (년)",
            default_value="5",
            group_name="기타",
            display_order=_next(),
        ),
        VariableData(
            variable_key="sha_dispute_resolution",
            input_type="SELECT",
            question_label="분쟁 해결 방법",
            select_options={"choices": ["서울중앙지방법원", "대한상사중재원", "ICC 국제중재"]},
            group_name="기타",
            display_order=_next(),
        ),
    ]
