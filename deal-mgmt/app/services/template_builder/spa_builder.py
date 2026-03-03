"""SPA(주식매매계약) 표준 템플릿 빌더.

한국 M&A 실무에서 사용되는 주식매매계약서의 표준 조항 15~20개와
변수 42개를 정의한다. 각 조항은 Jinja2 변수를 포함하며,
조건부 조항(에스크로, 어닝아웃, 가격조정)을 지원한다.
"""

from __future__ import annotations

from .base import ClauseData, TemplateData, VariableData


def build_spa_template() -> TemplateData:
    """SPA 표준 템플릿을 생성한다."""
    return TemplateData(
        doc_type="SPA",
        name="주식매매계약서 (SPA) 표준 템플릿",
        description="한국 M&A 실무 기반 주식매매계약서. 에스크로, 어닝아웃, 가격조정 등 조건부 조항 포함.",
        clauses=_build_clauses(),
        variables=_build_variables(),
    )


def _build_clauses() -> list[ClauseData]:
    """SPA 표준 조항 18개를 반환한다."""
    return [
        ClauseData(
            clause_order=1,
            title="정의",
            content=(
                "<p>본 계약에서 사용되는 용어는 본 조에서 달리 정의되지 아니하는 한, "
                "아래와 같은 의미를 가진다.</p>\n"
                '<p>"대상회사"라 함은 {{ target_company_name }}(사업자등록번호: '
                "{{ target_business_number }})을 의미한다.</p>\n"
                '<p>"매도인"이라 함은 {{ seller_name }}을 의미한다.</p>\n'
                '<p>"매수인"이라 함은 {{ buyer_name }}을 의미한다.</p>\n'
                '<p>"대상주식"이라 함은 대상회사의 보통주식 {{ total_shares }}주 중 '
                "매도인이 보유한 {{ transfer_shares }}주(지분율 약 "
                "{{ stake_percentage }}%)를 의미한다.</p>\n"
                '<p>"매매대금"이라 함은 제4조에서 정한 대상주식의 매매대금 '
                "{{ purchase_price|currency_format }}을 의미한다.</p>\n"
                '<p>"거래종결일"이라 함은 제5조에 따라 거래가 종결되는 날인 '
                "{{ closing_date|date_format }}을 의미한다.</p>\n"
                '<p>"진술보증일"이라 함은 본 계약 체결일인 {{ signing_date|date_format }}을 '
                "의미한다.</p>\n"
                '<p>"보상한도"라 함은 {{ indemnity_cap|currency_format }}을 의미한다.</p>\n'
                '<p>"보상기간"이라 함은 거래종결일로부터 {{ warranty_period_months }}개월간의 '
                "기간을 의미한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=2,
            title="거래의 목적",
            content=(
                "<p>본 계약은 매도인이 보유한 대상주식을 매수인에게 양도하고, 매수인이 이를 "
                "양수하는 것을 목적으로 한다.</p>\n"
                "<p>당사자들은 본 계약에서 정하는 조건에 따라 성실하게 거래를 이행하며, "
                "거래종결일까지 대상회사의 가치를 보전하기 위하여 최선의 노력을 다한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=3,
            title="거래 대상",
            content=(
                "<p>본 계약에 따른 거래의 대상은 매도인이 보유한 대상회사의 보통주식 "
                '{{ transfer_shares }}주(이하 "대상주식")로서, 이는 대상회사의 발행주식 '
                "총수 {{ total_shares }}주의 약 {{ stake_percentage }}%에 해당한다.</p>\n"
                "<p>매도인은 대상주식의 적법한 소유자로서, 대상주식에 대하여 질권, 저당권, "
                "양도담보, 가압류, 가처분 등 어떠한 제한도 존재하지 아니함을 확인한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=4,
            title="매매대금",
            content=(
                '<p>대상주식의 매매대금(이하 "매매대금")은 {{ purchase_price|currency_format }}으로 '
                "한다. 주당 가격은 {{ share_price_per|currency_format }}으로 산정한다.</p>\n"
                "<p>매매대금은 대한민국 원화(KRW)로 표시하며, 거래종결일의 환율 변동에 따른 "
                "조정은 적용하지 아니한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=5,
            title="대금 지급",
            content=(
                "<p>매수인은 매도인에게 매매대금을 다음과 같이 지급한다.</p>\n"
                "<ol>\n"
                "<li>계약금: 매매대금의 {{ deposit_percentage }}%에 해당하는 "
                "{{ deposit_amount|currency_format }}을 본 계약 체결일에 매도인이 지정하는 "
                "계좌로 지급한다.</li>\n"
                "<li>잔금: 매매대금에서 계약금을 공제한 잔액을 거래종결일에 매도인이 지정하는 "
                "계좌로 지급한다.</li>\n"
                "</ol>\n"
                "<p>지급이 지연되는 경우, 매수인은 미지급 금액에 대하여 연 {{ late_interest_rate }}%의 "
                "지연이자를 부담한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=6,
            title="에스크로",
            content=(
                "<p>매수인은 매매대금 중 {{ escrow_percentage }}%에 해당하는 금액(이하 "
                '"에스크로 금액")을 {{ escrow_agent }}가 관리하는 에스크로 계좌에 예치한다.</p>\n'
                "<p>에스크로 금액은 거래종결일로부터 {{ escrow_period_months }}개월이 경과한 "
                '날(이하 "에스크로 해제일")에 다음 조건에 따라 처리한다.</p>\n'
                "<ol>\n"
                "<li>보상청구가 없는 경우: 에스크로 금액 전액을 매도인에게 지급한다.</li>\n"
                "<li>보상청구가 있는 경우: 보상청구 금액을 공제한 잔액을 매도인에게 지급하되, "
                "미해결 보상청구에 대하여는 해결 시까지 해당 금액을 유보한다.</li>\n"
                "</ol>"
            ),
            condition_expression="has_escrow == True",
        ),
        ClauseData(
            clause_order=7,
            title="선행조건",
            content=(
                "<p>거래의 종결은 다음 각 호의 선행조건이 모두 충족되거나 면제되는 것을 "
                "조건으로 한다.</p>\n"
                "<ol>\n"
                "<li>대상회사 이사회 및 주주총회(필요한 경우)의 승인</li>\n"
                "<li>공정거래위원회 기업결합 신고 완료 및 이의 없음 통보 수령 "
                "(기업결합 신고 대상인 경우)</li>\n"
                "<li>매도인의 진술 및 보증이 진술보증일 및 거래종결일 현재 중요한 점에서 "
                "진실하고 정확할 것</li>\n"
                "<li>당사자들의 확약사항 이행 완료</li>\n"
                "<li>거래의 이행을 금지하는 법원의 명령, 판결 또는 가처분이 존재하지 아니할 것</li>\n"
                "<li>{{ additional_conditions }}</li>\n"
                "</ol>"
            ),
        ),
        ClauseData(
            clause_order=8,
            title="진술 및 보증 — 매도인",
            content=(
                "<p>매도인은 진술보증일 현재 및 거래종결일 현재 다음 각 호의 사항이 "
                "진실하고 정확함을 매수인에게 진술하고 보증한다.</p>\n"
                "<ol>\n"
                "<li>매도인은 대상주식의 적법한 소유자이며, 대상주식에 대하여 어떠한 "
                "담보권, 질권, 가압류 등의 부담도 존재하지 아니한다.</li>\n"
                "<li>대상회사는 대한민국 법률에 따라 적법하게 설립되어 유효하게 존속하는 "
                "회사이다.</li>\n"
                "<li>대상회사는 사업 수행에 필요한 모든 인허가를 적법하게 보유하고 있다.</li>\n"
                "<li>대상회사의 최근 감사보고서 및 재무제표는 한국채택국제회계기준(K-IFRS) "
                "또는 일반기업회계기준(K-GAAP)에 따라 작성되었으며, 대상회사의 재무상태 및 "
                "경영성과를 중요한 점에서 공정하게 표시하고 있다.</li>\n"
                "<li>매도인이 알고 있는 한, 대상회사에 중대한 영향을 미칠 수 있는 소송, "
                "중재 또는 행정절차가 계류 중이지 아니하다.</li>\n"
                "<li>매도인이 알고 있는 한, 대상회사의 주요 계약에 대한 채무불이행 사유가 "
                "발생하지 아니하였다.</li>\n"
                "<li>대상회사의 세무 신고 및 납부는 관련 법령에 따라 적법하게 이루어졌다.</li>\n"
                "</ol>"
            ),
        ),
        ClauseData(
            clause_order=9,
            title="진술 및 보증 — 매수인",
            content=(
                "<p>매수인은 진술보증일 현재 및 거래종결일 현재 다음 각 호의 사항이 "
                "진실하고 정확함을 매도인에게 진술하고 보증한다.</p>\n"
                "<ol>\n"
                "<li>매수인은 대한민국 법률에 따라 적법하게 설립되어 유효하게 존속하는 "
                "법인이다.</li>\n"
                "<li>매수인은 본 계약의 체결 및 이행을 위하여 필요한 모든 내부 승인을 "
                "취득하였거나 거래종결일까지 취득할 것이다.</li>\n"
                "<li>매수인은 매매대금의 지급에 필요한 충분한 자금을 확보하고 있거나, "
                "거래종결일까지 확보할 것이다.</li>\n"
                "</ol>"
            ),
        ),
        ClauseData(
            clause_order=10,
            title="확약사항",
            content=(
                "<p>당사자들은 본 계약 체결일부터 거래종결일까지 다음 각 호의 사항을 "
                "확약한다.</p>\n"
                "<ol>\n"
                "<li>매도인은 대상회사로 하여금 통상적인 사업 과정에서 사업을 영위하도록 "
                "하며, 매수인의 사전 서면 동의 없이 대상회사의 자산, 부채 또는 사업에 "
                "중대한 변경을 초래하는 행위를 하지 아니한다.</li>\n"
                "<li>매도인은 거래종결일로부터 {{ non_compete_years }}년간 대상회사와 "
                "동일 또는 유사한 사업을 직접 또는 간접적으로 영위하지 아니한다 "
                "(경업금지의무).</li>\n"
                "<li>당사자들은 거래의 종결을 위하여 필요한 정부 인허가, 승인 등의 취득에 "
                "상호 협력한다.</li>\n"
                "</ol>"
            ),
        ),
        ClauseData(
            clause_order=11,
            title="거래종결",
            content=(
                '<p>거래의 종결은 {{ closing_date|date_format }}(이하 "거래종결일")에 '
                "{{ closing_location }}에서 이루어진다.</p>\n"
                "<p>거래종결일에 다음 각 호의 행위가 동시에 이행된다.</p>\n"
                "<ol>\n"
                "<li>매도인: 대상주식의 주권 교부 및 주주명부 명의개서에 필요한 서류 교부</li>\n"
                "<li>매수인: 잔금 지급 (제5조에 따름)</li>\n"
                "<li>당사자들: 기타 거래종결에 필요한 서류의 교환</li>\n"
                "</ol>"
            ),
        ),
        ClauseData(
            clause_order=12,
            title="보상",
            content=(
                "<p>매도인이 본 계약에 따른 진술 및 보증을 위반하거나 확약사항을 불이행한 "
                "경우, 매도인은 매수인이 입은 손해를 배상한다.</p>\n"
                "<p>보상 한도는 {{ indemnity_cap|currency_format }}으로 한다. 다만, "
                "사기, 고의적 위반 또는 근본적 진술보증 위반의 경우에는 보상 한도 제한이 "
                "적용되지 아니한다.</p>\n"
                "<p>보상 청구는 거래종결일로부터 {{ warranty_period_months }}개월 이내에 "
                "서면으로 통지하여야 하며, 위 기간 내에 통지되지 아니한 보상 청구는 "
                "소멸한다.</p>\n"
                "<p>개별 보상 청구 금액이 {{ de_minimis_amount|currency_format }}("
                '소액기준금액") 미만인 경우에는 보상 대상에서 제외된다.</p>'
            ),
        ),
        ClauseData(
            clause_order=13,
            title="계약의 해제 및 해지",
            content=(
                "<p>다음 각 호의 사유가 발생한 경우, 당사자는 상대방에게 서면 통지를 "
                "함으로써 본 계약을 해제할 수 있다.</p>\n"
                "<ol>\n"
                '<li>제7조의 선행조건이 {{ long_stop_date|date_format }}(이하 "최종기한")까지 '
                "충족되지 아니한 경우 (단, 조건 미충족의 원인을 제공한 당사자는 해제권을 "
                "행사할 수 없다)</li>\n"
                "<li>상대방이 본 계약상의 중요한 의무를 위반하고, 서면 통지 후 "
                "{{ cure_period_days }}일 이내에 시정하지 아니한 경우</li>\n"
                "<li>거래의 이행을 영구적으로 금지하는 확정된 법원의 판결 또는 행정처분이 "
                "존재하는 경우</li>\n"
                "</ol>\n"
                "<p>본 계약이 해제된 경우, 매수인이 기지급한 계약금은 해제 사유에 따라 "
                "반환 또는 위약벌로 처리한다.</p>"
            ),
        ),
        ClauseData(
            clause_order=14,
            title="비밀유지",
            content=(
                "<p>당사자들은 본 계약의 존재 및 내용, 거래와 관련하여 상대방으로부터 "
                '제공받은 모든 정보(이하 "비밀정보")를 비밀로 유지하여야 하며, '
                "상대방의 사전 서면 동의 없이 제3자에게 공개하지 아니한다.</p>\n"
                "<p>비밀유지 의무는 본 계약의 종료 또는 해제 후에도 {{ confidentiality_years }}년간 "
                "존속한다.</p>\n"
                "<p>다만, 다음 각 호에 해당하는 경우에는 비밀유지 의무가 적용되지 아니한다.</p>\n"
                "<ol>\n"
                "<li>공개 당시 이미 공지의 사실이었거나 수령자의 귀책 사유 없이 "
                "공지의 사실이 된 정보</li>\n"
                "<li>법률, 규정 또는 관할 법원이나 정부기관의 명령에 의하여 공개가 "
                "요구되는 경우 (단, 사전에 상대방에게 통지하여야 한다)</li>\n"
                "<li>비밀유지 의무에 구속되는 전문가 자문인(변호사, 회계사 등)에게의 공개</li>\n"
                "</ol>"
            ),
            is_boilerplate=True,
        ),
        ClauseData(
            clause_order=15,
            title="어닝아웃",
            content=(
                "<p>당사자들은 매매대금의 일부를 거래종결 후 대상회사의 실적에 연동하여 "
                '지급하는 것에 합의한다(이하 "어닝아웃").</p>\n'
                "<p>어닝아웃 기준 지표: {{ earnout_metric }}</p>\n"
                "<p>어닝아웃 측정 기간: 거래종결일로부터 {{ earnout_period_years }}년</p>\n"
                "<p>어닝아웃 최대 금액: {{ earnout_max_amount|currency_format }}</p>\n"
                "<p>어닝아웃 지급 조건:</p>\n"
                "<ol>\n"
                "<li>기준 지표가 {{ earnout_target }}에 도달하는 경우 어닝아웃 금액의 "
                "100%를 지급한다.</li>\n"
                "<li>기준 지표가 {{ earnout_threshold }}에 미달하는 경우 어닝아웃 금액을 "
                "지급하지 아니한다.</li>\n"
                "<li>기준 지표가 {{ earnout_threshold }}과 {{ earnout_target }} 사이인 경우 "
                "비례 계산하여 지급한다.</li>\n"
                "</ol>\n"
                "<p>어닝아웃 금액의 산정은 대상회사의 감사받은 재무제표를 기준으로 하며, "
                "산정에 대한 이의가 있는 경우 독립적인 회계법인의 판정에 따른다.</p>"
            ),
            condition_expression="has_earnout == True",
        ),
        ClauseData(
            clause_order=16,
            title="가격조정",
            content=(
                '<p>매매대금은 거래종결일 현재의 대상회사 순운전자본(이하 "실제 '
                '순운전자본")에 따라 다음과 같이 조정된다.</p>\n'
                "<p>기준 순운전자본: {{ target_working_capital|currency_format }}</p>\n"
                "<p>조정 방식:</p>\n"
                "<ol>\n"
                "<li>실제 순운전자본이 기준 순운전자본을 초과하는 경우: 초과분만큼 매매대금을 "
                "증액한다.</li>\n"
                "<li>실제 순운전자본이 기준 순운전자본에 미달하는 경우: 미달분만큼 매매대금을 "
                "감액한다.</li>\n"
                "</ol>\n"
                "<p>가격조정의 산정은 거래종결일 후 {{ price_adjustment_days }}일 이내에 매수인이 "
                "작성한 조정계산서를 기준으로 하며, 매도인은 수령 후 {{ price_adjustment_review_days }}일 "
                "이내에 이의를 제기할 수 있다.</p>"
            ),
            condition_expression="has_price_adjustment == True",
        ),
        ClauseData(
            clause_order=17,
            title="준거법 및 분쟁해결",
            content=(
                "<p>본 계약은 {{ governing_law }} 법률에 따라 해석되고 이행된다.</p>\n"
                "<p>본 계약으로부터 또는 본 계약과 관련하여 발생하는 분쟁은 "
                "{{ dispute_resolution }}에 의하여 최종적으로 해결한다.</p>"
            ),
            is_boilerplate=True,
        ),
        ClauseData(
            clause_order=18,
            title="일반조항",
            content=(
                "<p>본 계약에 대한 통지는 서면(등기우편, 팩스 또는 이메일)으로 하며, "
                "다음 주소로 송달한다.</p>\n"
                "<p>매도인 주소: {{ seller_address }}</p>\n"
                "<p>매수인 주소: {{ buyer_address }}</p>\n"
                "<p>본 계약은 상대방의 사전 서면 동의 없이 양도할 수 없다.</p>\n"
                "<p>본 계약은 당사자 간의 거래에 관한 완전한 합의를 구성하며, 본 계약 "
                "체결 이전의 모든 구두 또는 서면 합의를 대체한다.</p>\n"
                "<p>본 계약의 어느 조항이 무효 또는 집행불능인 경우에도 나머지 조항의 "
                "유효성에는 영향을 미치지 아니한다.</p>\n"
                "<p>본 계약은 {{ contract_copies }}부를 작성하여 당사자들이 각 1부씩 "
                "보관한다.</p>"
            ),
            is_boilerplate=True,
        ),
    ]


def _build_variables() -> list[VariableData]:
    """SPA 표준 변수 42개를 반환한다."""
    order = 0

    def _next() -> int:
        nonlocal order
        order += 1
        return order

    return [
        # ── 당사자 정보 ──
        VariableData(
            variable_key="seller_name",
            input_type="TEXT",
            question_label="매도인 법인명(또는 성명)",
            group_name="당사자 정보",
            display_order=_next(),
        ),
        VariableData(
            variable_key="buyer_name",
            input_type="TEXT",
            question_label="매수인 법인명(또는 성명)",
            group_name="당사자 정보",
            display_order=_next(),
        ),
        VariableData(
            variable_key="target_company_name",
            input_type="TEXT",
            question_label="대상회사 법인명",
            group_name="당사자 정보",
            display_order=_next(),
        ),
        VariableData(
            variable_key="target_business_number",
            input_type="TEXT",
            question_label="대상회사 사업자등록번호",
            group_name="당사자 정보",
            display_order=_next(),
            is_required=False,
        ),
        # ── 거래 조건 ──
        VariableData(
            variable_key="total_shares",
            input_type="NUMBER",
            question_label="대상회사 발행주식 총수",
            group_name="거래 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="transfer_shares",
            input_type="NUMBER",
            question_label="양도 대상 주식 수",
            group_name="거래 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="stake_percentage",
            input_type="PERCENTAGE",
            question_label="양도 지분율 (%)",
            group_name="거래 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="purchase_price",
            input_type="CURRENCY",
            question_label="매매대금 (원)",
            group_name="거래 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="share_price_per",
            input_type="CURRENCY",
            question_label="주당 매매가격 (원)",
            group_name="거래 조건",
            display_order=_next(),
        ),
        # ── 일정 ──
        VariableData(
            variable_key="signing_date",
            input_type="DATE",
            question_label="계약 체결일",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="closing_date",
            input_type="DATE",
            question_label="거래종결일 (예정)",
            group_name="일정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="long_stop_date",
            input_type="DATE",
            question_label="최종기한 (Long-Stop Date)",
            group_name="일정",
            display_order=_next(),
        ),
        # ── 대금 지급 ──
        VariableData(
            variable_key="deposit_percentage",
            input_type="PERCENTAGE",
            question_label="계약금 비율 (%)",
            default_value="10",
            group_name="대금 지급",
            display_order=_next(),
        ),
        VariableData(
            variable_key="deposit_amount",
            input_type="CURRENCY",
            question_label="계약금 (원)",
            group_name="대금 지급",
            display_order=_next(),
        ),
        VariableData(
            variable_key="late_interest_rate",
            input_type="NUMBER",
            question_label="지연이자율 (연 %)",
            default_value="15",
            group_name="대금 지급",
            display_order=_next(),
        ),
        # ── 에스크로 (조건부) ──
        VariableData(
            variable_key="has_escrow",
            input_type="BOOLEAN",
            question_label="에스크로 적용 여부",
            default_value="false",
            group_name="에스크로",
            display_order=_next(),
        ),
        VariableData(
            variable_key="escrow_percentage",
            input_type="PERCENTAGE",
            question_label="에스크로 비율 (%)",
            default_value="10",
            group_name="에스크로",
            visible_condition="has_escrow == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="escrow_agent",
            input_type="TEXT",
            question_label="에스크로 에이전트 (은행/법무법인)",
            group_name="에스크로",
            visible_condition="has_escrow == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="escrow_period_months",
            input_type="NUMBER",
            question_label="에스크로 기간 (개월)",
            default_value="12",
            group_name="에스크로",
            visible_condition="has_escrow == True",
            is_required=False,
            display_order=_next(),
        ),
        # ── 보상 ──
        VariableData(
            variable_key="indemnity_cap",
            input_type="CURRENCY",
            question_label="보상 한도 (원)",
            group_name="보상",
            display_order=_next(),
        ),
        VariableData(
            variable_key="warranty_period_months",
            input_type="NUMBER",
            question_label="진술보증 보상 기간 (개월)",
            default_value="18",
            group_name="보상",
            display_order=_next(),
        ),
        VariableData(
            variable_key="de_minimis_amount",
            input_type="CURRENCY",
            question_label="소액기준금액 (De Minimis, 원)",
            group_name="보상",
            display_order=_next(),
            is_required=False,
        ),
        # ── 어닝아웃 (조건부) ──
        VariableData(
            variable_key="has_earnout",
            input_type="BOOLEAN",
            question_label="어닝아웃 적용 여부",
            default_value="false",
            group_name="어닝아웃",
            display_order=_next(),
        ),
        VariableData(
            variable_key="earnout_metric",
            input_type="SELECT",
            question_label="어닝아웃 기준 지표",
            select_options={"choices": ["REVENUE", "EBITDA", "NET_INCOME", "CUSTOMER_COUNT"]},
            group_name="어닝아웃",
            visible_condition="has_earnout == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="earnout_period_years",
            input_type="NUMBER",
            question_label="어닝아웃 측정 기간 (년)",
            default_value="3",
            group_name="어닝아웃",
            visible_condition="has_earnout == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="earnout_max_amount",
            input_type="CURRENCY",
            question_label="어닝아웃 최대 금액 (원)",
            group_name="어닝아웃",
            visible_condition="has_earnout == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="earnout_target",
            input_type="TEXT",
            question_label="어닝아웃 목표 수준",
            group_name="어닝아웃",
            visible_condition="has_earnout == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="earnout_threshold",
            input_type="TEXT",
            question_label="어닝아웃 최소 기준",
            group_name="어닝아웃",
            visible_condition="has_earnout == True",
            is_required=False,
            display_order=_next(),
        ),
        # ── 가격조정 (조건부) ──
        VariableData(
            variable_key="has_price_adjustment",
            input_type="BOOLEAN",
            question_label="가격조정 적용 여부",
            default_value="false",
            group_name="가격조정",
            display_order=_next(),
        ),
        VariableData(
            variable_key="target_working_capital",
            input_type="CURRENCY",
            question_label="기준 순운전자본 (원)",
            group_name="가격조정",
            visible_condition="has_price_adjustment == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="price_adjustment_days",
            input_type="NUMBER",
            question_label="조정계산서 제출 기한 (일)",
            default_value="60",
            group_name="가격조정",
            visible_condition="has_price_adjustment == True",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="price_adjustment_review_days",
            input_type="NUMBER",
            question_label="이의제기 기한 (일)",
            default_value="30",
            group_name="가격조정",
            visible_condition="has_price_adjustment == True",
            is_required=False,
            display_order=_next(),
        ),
        # ── 기타 ──
        VariableData(
            variable_key="non_compete_years",
            input_type="NUMBER",
            question_label="경업금지 기간 (년)",
            default_value="3",
            group_name="기타 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="confidentiality_years",
            input_type="NUMBER",
            question_label="비밀유지 기간 (년)",
            default_value="5",
            group_name="기타 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="closing_location",
            input_type="TEXT",
            question_label="거래종결 장소",
            default_value="서울특별시",
            group_name="기타 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="dispute_resolution",
            input_type="SELECT",
            question_label="분쟁 해결 방법",
            select_options={
                "choices": [
                    "서울중앙지방법원 관할 소송",
                    "대한상사중재원 중재",
                    "대한법률구조공단 중재",
                ]
            },
            default_value="서울중앙지방법원 관할 소송",
            group_name="기타 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="additional_conditions",
            input_type="TEXTAREA",
            question_label="추가 선행조건 (있는 경우)",
            default_value="해당 없음",
            group_name="기타 조건",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="cure_period_days",
            input_type="NUMBER",
            question_label="의무 위반 시정 기간 (일)",
            default_value="30",
            group_name="기타 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="seller_address",
            input_type="TEXTAREA",
            question_label="매도인 주소 (통지용)",
            group_name="통지",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="buyer_address",
            input_type="TEXTAREA",
            question_label="매수인 주소 (통지용)",
            group_name="통지",
            is_required=False,
            display_order=_next(),
        ),
        VariableData(
            variable_key="contract_copies",
            input_type="NUMBER",
            question_label="계약서 작성 부수",
            default_value="2",
            group_name="기타 조건",
            display_order=_next(),
        ),
        VariableData(
            variable_key="governing_law",
            input_type="TEXT",
            question_label="준거법",
            default_value="대한민국",
            group_name="기타 조건",
            is_required=False,
            display_order=_next(),
        ),
    ]
