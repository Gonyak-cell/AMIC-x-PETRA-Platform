"""SSA(신주인수계약) 표준 템플릿 빌더.

벤처투자/성장투자에서 사용되는 신주인수계약서의 표준 조항 15개와
변수 26개를 정의한다. 투자금액, 주식 종류(보통주/우선주),
투자자 보호 조항(전환권, 상환권, 희석방지, ROFR 등)을 포함한다.
"""

from __future__ import annotations

from .base import ClauseData, TemplateData, VariableData


def build_ssa_template() -> TemplateData:
    """SSA 표준 템플릿을 생성한다."""
    return TemplateData(
        doc_type="SSA",
        name="신주인수계약서 (SSA) 표준 템플릿",
        description="한국 VC/PE 투자 실무 기반 신주인수계약서. 우선주 조건, 전환/상환권, 희석방지 등 포함.",
        clauses=_build_clauses(),
        variables=_build_variables(),
    )


def _build_clauses() -> list[ClauseData]:
    return [
        ClauseData(
            clause_order=1,
            title="정의",
            content=(
                "<p>본 계약에서 사용되는 용어는 아래와 같은 의미를 가진다.</p>\n"
                '<p>"회사"라 함은 {{ ssa_company_name }}을 의미한다.</p>\n'
                '<p>"투자자"라 함은 {{ investor_name }}을 의미한다.</p>\n'
                '<p>"인수주식"이라 함은 회사가 투자자에게 발행하는 '
                "{{ share_type }} {{ subscription_shares }}주를 의미한다.</p>\n"
                '<p>"투자금"이라 함은 {{ investment_amount|currency_format }}을 의미한다.</p>\n'
                '<p>"1주당 인수가액"이라 함은 {{ price_per_share|currency_format }}을 의미한다.</p>\n'
                '<p>"Pre-Money 기업가치"라 함은 {{ pre_money_valuation|currency_format }}을 의미한다.</p>'
            ),
        ),
        ClauseData(
            clause_order=2,
            title="신주의 발행 및 인수",
            content=(
                "<p>회사는 투자자에게 {{ share_type }} {{ subscription_shares }}주를 발행하고, "
                "투자자는 1주당 {{ price_per_share|currency_format }}에 이를 인수한다.</p>\n"
                "<p>총 투자금은 {{ investment_amount|currency_format }}으로 한다.</p>\n"
                "<p>투자 후 투자자의 지분율은 약 {{ post_investment_stake }}%이다.</p>"
            ),
        ),
        ClauseData(
            clause_order=3,
            title="투자금 납입",
            content=(
                "<p>투자자는 {{ payment_date|date_format }}까지 투자금 전액을 "
                "회사가 지정하는 주금납입 계좌에 납입한다.</p>\n"
                "<p>투자금 납입 후 {{ registration_days }}일 이내에 회사는 "
                "신주 발행 등기를 완료한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=4,
            title="선행조건",
            content=(
                "<p>투자의 실행은 다음 각 호의 선행조건이 모두 충족되는 것을 전제로 한다.</p>\n"
                "<ol>\n<li>회사 이사회 및 주주총회의 신주 발행 승인</li>\n"
                "<li>회사의 진술 및 보증이 투자 실행일 현재 진실하고 정확할 것</li>\n"
                "<li>관련 법령상 필요한 인허가 및 승인의 취득</li>\n"
                "<li>투자자 만족 실사(Due Diligence) 완료</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=5,
            title="진술 및 보증",
            content=(
                "<p>회사 및 대표이사는 투자자에게 다음 각 호의 사항을 진술하고 보증한다.</p>\n"
                "<ol>\n<li>회사는 대한민국 법률에 따라 적법하게 설립되어 유효하게 존속하고 있다.</li>\n"
                "<li>회사의 자본 구조, 주주 명부 및 발행 주식 현황이 정확하다.</li>\n"
                "<li>회사에 계류 중인 중요 소송이나 분쟁이 존재하지 아니한다.</li>\n"
                "<li>회사의 재무제표가 회사의 재무상태를 공정하게 표시하고 있다.</li>\n"
                "<li>본 계약 체결 및 이행에 법적 장애가 없다.</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=6,
            title="전환권",
            content=(
                "<p>투자자는 인수주식을 회사의 보통주식으로 전환할 수 있는 권리(전환권)를 "
                "가진다.</p>\n"
                "<p>전환 비율: {{ share_type }} 1주당 보통주 {{ conversion_ratio }}주</p>\n"
                "<p>전환 청구 가능 시기: 인수주식 발행일로부터 {{ conversion_start_months }}개월 "
                "경과 후</p>\n"
                "<p>전환 비율은 제8조의 희석방지 조항에 따라 조정될 수 있다.</p>"
            ),
            condition_expression="has_conversion_right == True",
        ),
        ClauseData(
            clause_order=7,
            title="상환권",
            content=(
                "<p>투자자는 인수주식 발행일로부터 {{ redemption_start_years }}년 경과 후, "
                "투자금에 연 {{ redemption_interest_rate }}%의 이자를 가산한 금액으로 "
                "인수주식의 상환을 회사에 청구할 수 있다(상환권).</p>\n"
                "<p>회사는 상환 청구 수령일로부터 {{ redemption_payment_days }}일 이내에 "
                "상환금을 투자자에게 지급하여야 한다.</p>"
            ),
            condition_expression="has_redemption_right == True",
        ),
        ClauseData(
            clause_order=8,
            title="희석방지",
            content=(
                "<p>회사가 투자자의 인수가액보다 낮은 가격으로 신주를 발행하는 경우, "
                "투자자의 전환 비율은 {{ anti_dilution_method }}에 따라 조정된다.</p>\n"
                "<p>다만, 다음 각 호의 신주 발행은 희석방지 조항의 적용에서 제외된다.</p>\n"
                "<ol>\n<li>임직원 스톡옵션에 따른 신주 발행 "
                "(발행주식 총수의 {{ stock_option_pool_pct }}% 이내)</li>\n"
                "<li>주식분할 또는 주식병합</li>\n"
                "<li>투자자의 사전 서면 동의를 받은 신주 발행</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=9,
            title="이사회 참관권",
            content=(
                "<p>투자자는 회사의 이사회에 {{ observer_count }}명의 참관인을 참석시킬 수 "
                "있는 권리를 가진다. 참관인은 발언권은 있으나 의결권은 없다.</p>\n"
                "<p>회사는 이사회 개최 {{ board_notice_days }}일 전까지 투자자에게 "
                "이사회 소집 통지를 하여야 한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=10,
            title="투자자 사전 동의 사항",
            content=(
                "<p>회사가 다음 각 호의 행위를 하기 위해서는 투자자의 사전 서면 동의가 "
                "필요하다.</p>\n"
                "<ol>\n<li>정관의 변경</li>\n"
                "<li>신주 발행, 전환사채/신주인수권부사채 발행</li>\n"
                "<li>합병, 영업양수도, 분할, 해산</li>\n"
                "<li>{{ ssa_consent_threshold|currency_format }} 초과 차입 또는 보증</li>\n"
                "<li>배당의 결정</li>\n"
                "<li>대표이사의 선임 및 해임</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=11,
            title="우선매수권",
            content=(
                "<p>회사가 신주 또는 신주인수권을 발행하는 경우, 투자자는 자신의 지분율에 "
                "비례하여 우선적으로 인수할 권리(우선인수권)를 가진다.</p>\n"
                "<p>회사는 신주 발행 {{ preemptive_notice_days }}일 전까지 투자자에게 "
                "서면으로 통지하여야 한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=12,
            title="동반매도참여권",
            content=(
                "<p>기존 주주가 보유 주식을 제3자에게 양도하고자 하는 경우, "
                "투자자는 동일한 비율 및 조건으로 보유 주식을 함께 양도할 수 있는 "
                "권리(Tag-Along)를 가진다.</p>"
            ),
        ),
        ClauseData(
            clause_order=13,
            title="정보 제공 의무",
            content=(
                "<p>회사는 투자자에게 다음 각 호의 정보를 정기적으로 제공한다.</p>\n"
                "<ol>\n<li>분기 재무제표: 분기 종료 후 {{ ssa_financial_report_days }}일 이내</li>\n"
                "<li>연간 감사보고서: 사업연도 종료 후 90일 이내</li>\n"
                "<li>사업계획서: 매 사업연도 개시 전</li>\n"
                "<li>중요 사항 발생 시 즉시 통지</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=14,
            title="비밀유지",
            content=(
                "<p>당사자들은 본 계약 및 투자 관련 비밀정보를 비밀로 유지하며, "
                "비밀유지 의무는 계약 종료 후 {{ ssa_confidentiality_years }}년간 존속한다.</p>"
            ),
            is_boilerplate=True,
        ),
        ClauseData(
            clause_order=15,
            title="준거법 및 분쟁해결",
            content=(
                "<p>본 계약은 대한민국 법률에 따라 해석되고 이행된다.</p>\n"
                "<p>분쟁은 {{ ssa_dispute_resolution }}에 의하여 해결한다.</p>"
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
            variable_key="ssa_company_name",
            input_type="TEXT",
            question_label="회사 법인명",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="investor_name",
            input_type="TEXT",
            question_label="투자자 명칭",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="share_type",
            input_type="SELECT",
            question_label="인수 주식 종류",
            select_options={"choices": ["보통주식", "상환전환우선주식", "전환우선주식", "상환우선주식"]},
            group_name="주식",
            display_order=_next(),
        ),
        VariableData(
            variable_key="subscription_shares",
            input_type="NUMBER",
            question_label="인수 주식 수",
            group_name="주식",
            display_order=_next(),
        ),
        VariableData(
            variable_key="price_per_share",
            input_type="CURRENCY",
            question_label="1주당 인수가액 (원)",
            group_name="투자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="investment_amount",
            input_type="CURRENCY",
            question_label="총 투자금 (원)",
            group_name="투자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="pre_money_valuation",
            input_type="CURRENCY",
            question_label="Pre-Money 기업가치 (원)",
            group_name="투자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="post_investment_stake",
            input_type="PERCENTAGE",
            question_label="투자 후 지분율 (%)",
            group_name="투자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="payment_date",
            input_type="DATE",
            question_label="투자금 납입일",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="registration_days",
            input_type="NUMBER",
            question_label="신주 등기 기한 (일)",
            default_value="14",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="has_conversion_right",
            input_type="BOOLEAN",
            question_label="전환권 포함 여부",
            default_value="true",
            group_name="전환/상환",
            display_order=_next(),
        ),
        VariableData(
            variable_key="conversion_ratio",
            input_type="NUMBER",
            question_label="전환 비율 (우선주 1주당 보통주 N주)",
            default_value="1",
            group_name="전환/상환",
            visible_condition="has_conversion_right == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="conversion_start_months",
            input_type="NUMBER",
            question_label="전환 청구 가능 시기 (발행 후 개월)",
            default_value="1",
            group_name="전환/상환",
            visible_condition="has_conversion_right == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="has_redemption_right",
            input_type="BOOLEAN",
            question_label="상환권 포함 여부",
            default_value="true",
            group_name="전환/상환",
            display_order=_next(),
        ),
        VariableData(
            variable_key="redemption_start_years",
            input_type="NUMBER",
            question_label="상환 청구 가능 시기 (발행 후 년)",
            default_value="3",
            group_name="전환/상환",
            visible_condition="has_redemption_right == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="redemption_interest_rate",
            input_type="NUMBER",
            question_label="상환 이자율 (연 %)",
            default_value="1",
            group_name="전환/상환",
            visible_condition="has_redemption_right == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="redemption_payment_days",
            input_type="NUMBER",
            question_label="상환금 지급 기한 (일)",
            default_value="30",
            group_name="전환/상환",
            visible_condition="has_redemption_right == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="anti_dilution_method",
            input_type="SELECT",
            question_label="희석방지 방식",
            select_options={"choices": ["가중평균 방식 (Weighted Average)", "완전희석 방식 (Full Ratchet)"]},
            group_name="투자자 보호",
            display_order=_next(),
        ),
        VariableData(
            variable_key="stock_option_pool_pct",
            input_type="PERCENTAGE",
            question_label="스톡옵션 풀 비율 (%)",
            default_value="10",
            group_name="투자자 보호",
            display_order=_next(),
        ),
        VariableData(
            variable_key="observer_count",
            input_type="NUMBER",
            question_label="이사회 참관인 수",
            default_value="1",
            group_name="거버넌스",
            display_order=_next(),
        ),
        VariableData(
            variable_key="board_notice_days",
            input_type="NUMBER",
            question_label="이사회 소집 통지 기간 (일)",
            default_value="7",
            group_name="거버넌스",
            display_order=_next(),
        ),
        VariableData(
            variable_key="ssa_consent_threshold",
            input_type="CURRENCY",
            question_label="사전 동의 기준 차입 한도 (원)",
            group_name="투자자 보호",
            display_order=_next(),
        ),
        VariableData(
            variable_key="preemptive_notice_days",
            input_type="NUMBER",
            question_label="우선인수권 통지 기간 (일)",
            default_value="30",
            group_name="투자자 보호",
            display_order=_next(),
        ),
        VariableData(
            variable_key="ssa_financial_report_days",
            input_type="NUMBER",
            question_label="분기 재무제표 제출 기한 (일)",
            default_value="45",
            group_name="정보 제공",
            display_order=_next(),
        ),
        VariableData(
            variable_key="ssa_confidentiality_years",
            input_type="NUMBER",
            question_label="비밀유지 기간 (년)",
            default_value="5",
            group_name="기타",
            display_order=_next(),
        ),
        VariableData(
            variable_key="ssa_dispute_resolution",
            input_type="SELECT",
            question_label="분쟁 해결 방법",
            select_options={"choices": ["서울중앙지방법원", "대한상사중재원"]},
            group_name="기타",
            display_order=_next(),
        ),
    ]
