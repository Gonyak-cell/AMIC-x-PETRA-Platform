"""BTA(영업양수도계약) 표준 템플릿 빌더.

영업(사업) 양수도계약서의 표준 조항 16개와 변수 22개를 정의한다.
양수도 대상 범위, 근로관계 승계, 채권채무 정리, 인허가 이전 등
사업 이전 특유의 조항을 포함한다.
"""

from __future__ import annotations

from .base import ClauseData, TemplateData, VariableData


def build_bta_template() -> TemplateData:
    """BTA 표준 템플릿을 생성한다."""
    return TemplateData(
        doc_type="BTA",
        name="영업양수도계약서 (BTA) 표준 템플릿",
        description="한국 M&A 실무 기반 영업양수도계약서. 사업 양수도 범위, 근로관계 승계, 채권채무 처리 등 포함.",
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
                '<p>"양도인"이라 함은 {{ transferor_name }}을 의미한다.</p>\n'
                '<p>"양수인"이라 함은 {{ transferee_name }}을 의미한다.</p>\n'
                '<p>"대상사업"이라 함은 양도인이 영위하는 {{ business_description }} 사업 '
                '일체(이하 "대상사업")를 의미한다.</p>\n'
                '<p>"양수도대금"이라 함은 제3조에서 정한 {{ transfer_price|currency_format }}을 '
                "의미한다.</p>\n"
                '<p>"양수도일"이라 함은 {{ transfer_date|date_format }}을 의미한다.</p>'
            ),
        ),
        ClauseData(
            clause_order=2,
            title="양수도 대상 범위",
            content=(
                "<p>양도인은 양수도일에 대상사업에 관한 다음 각 호의 자산, 권리, 의무를 "
                "양수인에게 양도하고, 양수인은 이를 양수한다.</p>\n"
                "<ol>\n<li>유형자산: 기계장치, 설비, 비품, 차량운반구 등 "
                "(별첨 1 자산목록 참조)</li>\n"
                "<li>무형자산: 영업권, 특허권, 상표권, 소프트웨어 라이선스 등</li>\n"
                "<li>재고자산: 양수도일 현재 대상사업 관련 재고 일체</li>\n"
                "<li>계약상 지위: 대상사업 관련 주요 계약의 당사자 지위 (별첨 2 참조)</li>\n"
                "<li>인허가: 대상사업 관련 인허가 (이전 가능한 것에 한함)</li>\n"
                "<li>{{ additional_transfer_items }}</li>\n</ol>\n"
                "<p>다음 각 호의 사항은 양수도 대상에서 명시적으로 제외한다.</p>\n"
                "<ol>\n<li>{{ excluded_items }}</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=3,
            title="양수도대금",
            content=(
                "<p>대상사업의 양수도대금은 {{ transfer_price|currency_format }}으로 한다.</p>\n"
                "<p>양수도대금은 {{ price_determination_method }}에 의하여 산정되었다.</p>\n"
                "<p>양수도대금은 양수도일 현재의 대상사업의 순자산가치를 기준으로 하되, "
                "영업권 {{ goodwill_amount|currency_format }}을 포함한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=4,
            title="대금 지급",
            content=(
                "<p>양수인은 양도인에게 양수도대금을 다음과 같이 지급한다.</p>\n"
                "<ol>\n<li>계약금: {{ bta_deposit_amount|currency_format }}을 "
                "본 계약 체결일에 지급</li>\n"
                "<li>잔금: 양수도대금에서 계약금을 공제한 잔액을 양수도일에 지급</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=5,
            title="근로관계 승계",
            content=(
                "<p>양수도일 현재 대상사업에 종사하는 근로자(총 {{ employee_count }}명, "
                "별첨 3 참조)의 근로관계는 양수인에게 포괄적으로 승계된다.</p>\n"
                "<p>양수인은 승계되는 근로자의 기존 근로조건(급여, 퇴직금, 근속연수 등)을 "
                "양수도일 이후 {{ employment_guarantee_months }}개월간 동일하게 유지한다.</p>\n"
                "<p>양도인은 양수도일 전에 발생한 근로자의 미지급 임금, 퇴직금 등 "
                "일체의 채무를 정산할 책임을 부담한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=6,
            title="채권·채무의 정리",
            content=(
                "<p>양수도일 이전에 발생한 대상사업 관련 채권·채무는 원칙적으로 양도인에게 "
                "귀속된다. 다만, 별첨 4에 기재된 채권·채무는 양수인이 승계한다.</p>\n"
                "<p>양수도일 이후에 발생한 채권·채무는 양수인에게 귀속된다.</p>\n"
                "<p>양수도일을 기준으로 채권·채무의 귀속이 불명확한 경우, "
                "당사자들은 성실하게 협의하여 해결한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=7,
            title="인허가 이전",
            content=(
                "<p>양도인은 대상사업 관련 인허가 중 양수인에게 이전 가능한 인허가의 "
                "명의를 양수도일까지 양수인에게 이전하기 위하여 최선의 노력을 다한다.</p>\n"
                "<p>법령상 이전이 불가능한 인허가에 대하여는, 양수인이 새로이 인허가를 "
                "취득하는 데 필요한 모든 서류를 양도인이 제공하고 협력한다.</p>\n"
                "<p>인허가 이전 비용은 {{ permit_transfer_cost_bearer }}이 부담한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=8,
            title="진술 및 보증 — 양도인",
            content=(
                "<p>양도인은 다음 각 호의 사항이 진실하고 정확함을 진술하고 보증한다.</p>\n"
                "<ol>\n<li>양도인은 대상사업 자산의 적법한 소유자이며, 양수도를 위한 "
                "모든 권한을 보유한다.</li>\n"
                "<li>대상사업 자산에 대하여 제3자의 권리(담보, 질권, 유치권 등)가 "
                "설정되어 있지 아니하다.</li>\n"
                "<li>대상사업은 관련 법령 및 규정을 준수하여 영위되어 왔다.</li>\n"
                "<li>대상사업에 관한 모든 중요 계약은 유효하게 존속하고 있으며, "
                "채무불이행 사유가 발생하지 아니하였다.</li>\n"
                "<li>환경오염, 유해물질 등 환경 관련 법규 위반 사항이 존재하지 아니한다.</li>\n"
                "</ol>"
            ),
        ),
        ClauseData(
            clause_order=9,
            title="진술 및 보증 — 양수인",
            content=(
                "<p>양수인은 다음 각 호의 사항이 진실하고 정확함을 진술하고 보증한다.</p>\n"
                "<ol>\n<li>양수인은 본 계약 체결 및 이행에 필요한 권한과 자력을 "
                "보유한다.</li>\n"
                "<li>양수인은 대상사업 승계에 필요한 인허가를 취득할 수 있다.</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=10,
            title="확약사항",
            content=(
                "<p>양도인은 본 계약 체결일부터 양수도일까지 대상사업을 통상적인 과정에서 "
                "영위하며, 양수인의 사전 동의 없이 중요 자산의 처분, 신규 채무 부담 등 "
                "대상사업의 가치를 감소시킬 수 있는 행위를 하지 아니한다.</p>\n"
                "<p>양도인은 양수도일로부터 {{ bta_non_compete_years }}년간 대상사업과 "
                "동종의 사업을 영위하지 아니한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=11,
            title="양수도의 이행",
            content=(
                "<p>양수도일에 다음 각 호의 행위가 동시에 이행된다.</p>\n"
                "<ol>\n<li>양도인: 대상사업 자산의 인도, 관련 서류의 교부, "
                "인허가 명의변경 서류 제공</li>\n"
                "<li>양수인: 잔금의 지급</li>\n"
                "<li>당사자들: 양수도 확인서 서명 교환</li>\n</ol>"
            ),
        ),
        ClauseData(
            clause_order=12,
            title="재고자산 정산",
            content=(
                "<p>양수도일 현재 대상사업의 재고자산은 양수도일 전 "
                "{{ inventory_count_days }}일 이내에 양 당사자가 공동으로 실사하여 "
                "확정한다.</p>\n"
                "<p>실사 결과 확정된 재고 금액이 기준 재고 금액 "
                "{{ target_inventory|currency_format }}과 차이가 있는 경우, "
                "양수도대금을 조정한다.</p>"
            ),
            condition_expression="has_inventory_adjustment == True",
        ),
        ClauseData(
            clause_order=13,
            title="보상",
            content=(
                "<p>양도인의 진술보증 위반 또는 확약사항 불이행으로 양수인이 손해를 "
                "입은 경우, 양도인은 {{ bta_indemnity_cap|currency_format }}을 한도로 "
                "양수인의 손해를 배상한다.</p>\n"
                "<p>보상 청구는 양수도일로부터 {{ bta_warranty_months }}개월 이내에 "
                "서면으로 통지하여야 한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=14,
            title="해제 및 해지",
            content=(
                "<p>양수도일 이전에 당사자 일방이 본 계약의 중요한 의무를 위반한 경우, "
                "상대방은 서면 통지 후 {{ bta_cure_days }}일의 시정 기간을 부여하고, "
                "시정되지 아니한 경우 본 계약을 해제할 수 있다.</p>"
            ),
        ),
        ClauseData(
            clause_order=15,
            title="비밀유지",
            content=(
                "<p>당사자들은 본 계약 및 대상사업에 관한 비밀정보를 비밀로 유지하며, "
                "비밀유지 의무는 계약 종료 후 {{ bta_confidentiality_years }}년간 존속한다.</p>"
            ),
            is_boilerplate=True,
        ),
        ClauseData(
            clause_order=16,
            title="준거법 및 분쟁해결",
            content=(
                "<p>본 계약은 대한민국 법률에 따라 해석되고 이행된다.</p>\n"
                "<p>분쟁은 {{ bta_dispute_resolution }}에 의하여 해결한다.</p>"
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
            variable_key="transferor_name",
            input_type="TEXT",
            question_label="양도인 법인명",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="transferee_name",
            input_type="TEXT",
            question_label="양수인 법인명",
            group_name="당사자",
            display_order=_next(),
        ),
        VariableData(
            variable_key="business_description",
            input_type="TEXTAREA",
            question_label="대상사업 설명",
            group_name="대상사업",
            display_order=_next(),
        ),
        VariableData(
            variable_key="transfer_price",
            input_type="CURRENCY",
            question_label="양수도대금 (원)",
            group_name="대금",
            display_order=_next(),
        ),
        VariableData(
            variable_key="transfer_date",
            input_type="DATE",
            question_label="양수도일 (예정)",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="price_determination_method",
            input_type="SELECT",
            question_label="대금 산정 방법",
            select_options={"choices": ["순자산가치법", "수익환원법", "EV/EBITDA 배수법", "당사자 합의"]},
            group_name="대금",
            display_order=_next(),
        ),
        VariableData(
            variable_key="goodwill_amount",
            input_type="CURRENCY",
            question_label="영업권 금액 (원)",
            group_name="대금",
            display_order=_next(),
        ),
        VariableData(
            variable_key="bta_deposit_amount",
            input_type="CURRENCY",
            question_label="계약금 (원)",
            group_name="대금",
            display_order=_next(),
        ),
        VariableData(
            variable_key="employee_count",
            input_type="NUMBER",
            question_label="승계 대상 근로자 수",
            group_name="근로관계",
            display_order=_next(),
        ),
        VariableData(
            variable_key="employment_guarantee_months",
            input_type="NUMBER",
            question_label="고용 유지 보장 기간 (개월)",
            default_value="12",
            group_name="근로관계",
            display_order=_next(),
        ),
        VariableData(
            variable_key="permit_transfer_cost_bearer",
            input_type="SELECT",
            question_label="인허가 이전 비용 부담자",
            select_options={"choices": ["양도인", "양수인", "균등 분담"]},
            group_name="인허가",
            display_order=_next(),
        ),
        VariableData(
            variable_key="bta_non_compete_years",
            input_type="NUMBER",
            question_label="경업금지 기간 (년)",
            default_value="3",
            group_name="확약",
            display_order=_next(),
        ),
        VariableData(
            variable_key="has_inventory_adjustment",
            input_type="BOOLEAN",
            question_label="재고자산 정산 조항 포함",
            default_value="true",
            group_name="재고",
            display_order=_next(),
        ),
        VariableData(
            variable_key="inventory_count_days",
            input_type="NUMBER",
            question_label="재고 실사 기한 (양수도일 전 일수)",
            default_value="5",
            group_name="재고",
            visible_condition="has_inventory_adjustment == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="target_inventory",
            input_type="CURRENCY",
            question_label="기준 재고 금액 (원)",
            group_name="재고",
            visible_condition="has_inventory_adjustment == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="bta_indemnity_cap",
            input_type="CURRENCY",
            question_label="보상 한도 (원)",
            group_name="보상",
            display_order=_next(),
        ),
        VariableData(
            variable_key="bta_warranty_months",
            input_type="NUMBER",
            question_label="보상 청구 기간 (개월)",
            default_value="12",
            group_name="보상",
            display_order=_next(),
        ),
        VariableData(
            variable_key="bta_cure_days",
            input_type="NUMBER",
            question_label="의무 위반 시정 기간 (일)",
            default_value="30",
            group_name="해제",
            display_order=_next(),
        ),
        VariableData(
            variable_key="bta_confidentiality_years",
            input_type="NUMBER",
            question_label="비밀유지 기간 (년)",
            default_value="5",
            group_name="기타",
            display_order=_next(),
        ),
        VariableData(
            variable_key="bta_dispute_resolution",
            input_type="SELECT",
            question_label="분쟁 해결 방법",
            select_options={"choices": ["서울중앙지방법원", "대한상사중재원"]},
            group_name="기타",
            display_order=_next(),
        ),
        VariableData(
            variable_key="additional_transfer_items",
            input_type="TEXTAREA",
            question_label="추가 양수도 대상 항목",
            default_value="해당 없음",
            group_name="대상사업",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="excluded_items",
            input_type="TEXTAREA",
            question_label="양수도 제외 항목",
            default_value="양도인의 법인격, 현금 및 현금성 자산",
            group_name="대상사업",
            is_required=False,
            display_order=_next(),
        ),
    ]
