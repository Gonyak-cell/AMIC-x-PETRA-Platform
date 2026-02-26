"""
법률 문서 docxtpl 템플릿 생성 스크립트.

한국 M&A 실무 체결본(SPA/SHA/BTA/SSA/MOU) 서식 분석을 기반으로
python-docx를 사용하여 docxtpl 호환 템플릿을 생성한다.

서식 기준 (2026-02-23 샘플 분석):
  - 폰트: 바탕체 (한글), Times New Roman (영문)
  - 페이지: A4 (21.0 × 29.7 cm)
  - 여백: 좌 2.54 / 우 2.54 / 상 3.00 / 하 2.54 cm (SPA/SHA/SSA/MOU)
          좌 2.50 / 우 2.50 / 상 3.00 / 하 3.00 cm (BTA)
  - 제목: 16pt Bold 중앙정렬 (SPA/SHA/SSA), 14pt (MOU), 20pt (BTA)
  - 본문: 12pt, 들여쓰기 1.30~1.50 cm
  - 색상: 흑백 (브랜드 컬러 사용 안 함)

사용법:
    cd deal-mgmt
    uv run python scripts/create_legal_templates.py

생성 위치: deal-mgmt/templates/legal/
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "legal"
TEMPLATE_VERSION = "2.0"

# 한글 폰트 (체결본 분석 결과)
FONT_KO = "바탕체"
FONT_EN = "Times New Roman"


# ─── 공통 유틸 ────────────────────────────────────────────────────────────────


def _apply_font(run, size_pt: float | None = None, bold: bool | None = None) -> None:
    """Run에 바탕체 폰트 및 Times New Roman 영문 폰트 적용."""
    run.font.name = FONT_EN
    run.font.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_KO)
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.bold = bold


def _set_margins(
    doc: Document, left: float = 2.54, right: float = 2.54, top: float = 3.00, bottom: float = 2.54
) -> None:
    """A4 페이지 여백 설정 (cm 단위)."""
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(left)
        section.right_margin = Cm(right)
        section.top_margin = Cm(top)
        section.bottom_margin = Cm(bottom)


def _add_title(doc: Document, text: str, size_pt: float = 16.0, space_before_pt: float = 60.0) -> None:
    """문서 제목 단락 추가 — 중앙정렬, 바탕체 Bold."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(space_before_pt)
    para.paragraph_format.space_after = Pt(12)
    run = para.add_run(text)
    _apply_font(run, size_pt=size_pt, bold=True)


def _add_subtitle(doc: Document, text: str) -> None:
    """영문 부제 (ex: Stock Purchase Agreement) — 중앙정렬 10pt."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_after = Pt(6)
    run = para.add_run(text)
    _apply_font(run, size_pt=10.0, bold=False)


def _add_section_label(doc: Document, text: str, bold: bool = True) -> None:
    """'전  문', '아  래' 등 중앙 소제목 — 12pt Bold."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(10)
    para.paragraph_format.space_after = Pt(6)
    run = para.add_run(text)
    _apply_font(run, size_pt=12.0, bold=bold)


def _add_preamble_body(doc: Document, text: str, indent_cm: float = 1.30) -> None:
    """전문 본문 단락 — 바탕체 12pt, 들여쓰기."""
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(indent_cm)
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run(text)
    _apply_font(run, size_pt=12.0)


def _add_preamble_text(doc: Document, text: str) -> None:
    """전문 설명 본문 — 들여쓰기 없음, 12pt."""
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run(text)
    _apply_font(run, size_pt=12.0)


def _add_article_heading(doc: Document, num: int, title: str) -> None:
    """제N조 (제목) — Heading 1 스타일 기반, Bold 12pt."""
    para = doc.add_paragraph(style="Heading 1")
    para.paragraph_format.space_before = Pt(12)
    para.paragraph_format.space_after = Pt(6)
    run = para.add_run(f"제{num}조 ({title})")
    _apply_font(run, size_pt=12.0, bold=True)


def _add_subheading(doc: Document, text: str) -> None:
    """소항 제목 — Heading 2 스타일 기반, 12pt."""
    para = doc.add_paragraph(style="Heading 2")
    para.paragraph_format.space_before = Pt(8)
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run(text)
    _apply_font(run, size_pt=12.0, bold=True)


def _add_body(doc: Document, text: str, indent_cm: float = 0.0) -> None:
    """조항 본문 단락 — 12pt."""
    para = doc.add_paragraph()
    if indent_cm:
        para.paragraph_format.left_indent = Cm(indent_cm)
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run(text)
    _apply_font(run, size_pt=12.0)


def _add_jinja_block(doc: Document, tag: str) -> None:
    """Jinja2 블록 태그 전용 단락 ({%p for %} 등).

    docxtpl은 단락 수준 태그에 {%p ... %} 문법을 요구한다.
    이 함수는 태그만 포함된 빈 단락을 생성한다.
    """
    para = doc.add_paragraph()
    run = para.add_run(tag)
    _apply_font(run, size_pt=12.0)


def _add_jinja_line(doc: Document, text: str, indent_cm: float = 1.30) -> None:
    """반복 루프 내 항목 단락 ({{ variable }} 포함)."""
    para = doc.add_paragraph()
    if indent_cm:
        para.paragraph_format.left_indent = Cm(indent_cm)
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run(text)
    _apply_font(run, size_pt=12.0)


def _add_date_line(doc: Document) -> None:
    """서명 날짜 줄 — 중앙정렬."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(20)
    para.paragraph_format.space_after = Pt(10)
    run = para.add_run("{{ signing_date }}")
    _apply_font(run, size_pt=12.0)


def _add_signature_table(doc: Document, parties: list[tuple[str, str, str]]) -> None:
    """서명란 테이블.

    parties: [(역할, 회사변수, 대표이사변수), ...]
    예: [('매도인 (甲)', '{{ seller_name }}', '{{ seller_representative }}')]
    """
    doc.add_paragraph()
    note = doc.add_paragraph("본 계약의 성립을 증명하기 위하여 아래에 서명 또는 기명날인한다.")
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in note.runs:
        _apply_font(run, size_pt=11.0)
    doc.add_paragraph()

    # 2열 테이블: 역할 | 서명
    table = doc.add_table(rows=len(parties), cols=2)
    table.style = "Table Grid"

    for i, (role, company_var, rep_var) in enumerate(parties):
        row = table.rows[i]
        # 왼쪽: 역할
        cell_l = row.cells[0]
        cell_l.text = role
        for run in cell_l.paragraphs[0].runs:
            _apply_font(run, size_pt=11.0, bold=True)
        # 오른쪽: 회사 + 대표이사
        cell_r = row.cells[1]
        p = cell_r.paragraphs[0]
        p.add_run(company_var + "\n")
        p.add_run("대표이사: " + rep_var)
        for run in p.runs:
            _apply_font(run, size_pt=11.0)

        # 최소 높이 설정 (3cm)
        for cell in (cell_l, cell_r):
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcH = OxmlElement("w:tcH")
            tcH.set(qn("w:val"), "1701")
            tcH.set(qn("w:type"), "atLeast")
            tcPr.append(tcH)


# ─── SPA 템플릿 ───────────────────────────────────────────────────────────────


def create_spa_template(out_dir: Path) -> None:
    """주식매매계약서 (Stock Purchase Agreement) 템플릿 생성."""
    doc = Document()
    _set_margins(doc, left=2.54, right=2.54, top=3.00, bottom=2.54)

    # 표지
    _add_title(doc, "주 식 매 매 계 약 서", size_pt=16.0, space_before_pt=80.0)
    _add_subtitle(doc, "(Stock Purchase Agreement)")
    doc.add_page_break()

    # 전문 서두 — 당사자 목록
    _add_preamble_text(
        doc,
        '본 주식매매계약(이하 "본 계약")은 {{ signing_date }}(이하 "본 계약 체결일") '
        "아래 당사자들 사이에서 체결되었다.",
    )
    _add_preamble_body(doc, '{{ seller_name }}(이하 "매도인")', indent_cm=1.30)
    _add_preamble_body(doc, '{{ buyer_name }}(이하 "매수인", 매도인과 매수인을 총칭하여 "당사자들")', indent_cm=1.30)

    _add_section_label(doc, "전     문")
    _add_preamble_text(
        doc, '{{ target_company_name }}(이하 "대상회사")는 대한민국 법령에 따라 설립되어 존속하는 주식회사이다.'
    )
    _add_preamble_text(
        doc,
        "매도인은 본 계약 체결일 현재 대상회사 발행의 보통주식 {{ transfer_shares }}주(발행주식총수 {{ total_shares }}주 중 해당 비율에 해당)를 보유하고 있다.",
    )
    _add_preamble_text(doc, "이에 당사자들은 아래와 같이 합의한다.")
    _add_section_label(doc, "아     래")

    # 제1조 용어 정의
    _add_article_heading(doc, 1, "정의")
    _add_body(
        doc, "본 계약에서 사용되는 다음의 용어는 본 계약에서 달리 정의되지 아니하는 한, 아래 규정된 의미를 가진다."
    )
    _add_body(doc, '"대상주식"이라 함은 대상회사 발행의 보통주식 {{ transfer_shares }}주를 말한다.', indent_cm=1.30)
    _add_body(
        doc,
        '"매매대금"이라 함은 1주당 금 {{ share_price_per }}원으로 산정한 총 금 {{ total_purchase_price }}원을 말한다.',
        indent_cm=1.30,
    )
    _add_body(doc, '"거래종결일"이라 함은 {{ closing_date }}을 말한다.', indent_cm=1.30)
    _add_body(doc, '"에스크로 금원"이라 함은 금 {{ escrow_amount }}원을 말한다.', indent_cm=1.30)
    _add_body(
        doc, '"진술보장 기간"이라 함은 거래종결일로부터 {{ warranty_period_months }}개월을 말한다.', indent_cm=1.30
    )
    _add_body(doc, '"준거법"이라 함은 {{ governing_law }} 법을 말한다.', indent_cm=1.30)

    # 제2조 매매대금
    _add_article_heading(doc, 2, "대상주식의 매수 및 매매대금")
    _add_subheading(doc, "대상주식의 매수.")
    _add_body(
        doc,
        "본 계약에서 정하는 조건에 따라, 매도인은 거래종결일에 매수인에게 대상주식을 양도하고, 매수인은 이를 인수한다.",
    )
    _add_subheading(doc, "매매대금.")
    _add_body(doc, "대상주식의 매매대금은 금 {{ total_purchase_price }}원(1주당 금 {{ share_price_per }}원)으로 한다.")
    _add_body(doc, "매수인은 거래종결일에 매도인이 서면으로 지정하는 계좌로 매매대금을 송금하는 방법으로 지급한다.")

    # 제3조 거래종결
    _add_article_heading(doc, 3, "거래종결")
    _add_subheading(doc, "거래종결.")
    _add_body(doc, '본 계약에 따른 거래의 종결(이하 "거래종결")은 {{ closing_date }}(이하 "거래종결일")에 이루어진다.')
    _add_subheading(doc, "거래종결 방법.")
    _add_body(doc, "거래종결일에 매수인은 다음 각 호를 동시에 이행한다.")
    _add_body(doc, "① 매매대금 전액의 지급", indent_cm=1.30)
    _add_body(doc, "② 거래종결에 관한 이사회 결의서 교부", indent_cm=1.30)
    _add_body(doc, "거래종결일에 매도인은 다음 각 호를 동시에 이행한다.")
    _add_body(doc, "① 대상주식에 대한 주식양도증서 교부", indent_cm=1.30)
    _add_body(doc, "② 주주명부 명의개서 이행", indent_cm=1.30)

    # 제4조 선행조건
    _add_article_heading(doc, 4, "선행조건")
    _add_body(
        doc, "본 계약에 따른 거래종결은 아래 각 호의 선행조건이 모두 충족(또는 권리자의 서면 포기)됨을 전제로 한다."
    )
    _add_body(doc, "① 각 당사자의 진술 및 보장이 거래종결일을 기준으로 중요한 면에서 사실과 부합할 것", indent_cm=1.30)
    _add_body(doc, "② 각 당사자가 본 계약상 이행해야 할 의무를 중요한 면에서 이행하였을 것", indent_cm=1.30)
    _add_body(doc, "③ 본 계약의 체결 및 이행에 필요한 정부승인 및 제3자 동의를 취득하였을 것", indent_cm=1.30)

    # 제5조 진술 및 보장
    _add_article_heading(doc, 5, "진술 및 보장")
    _add_subheading(doc, "매도인의 진술 및 보장.")
    _add_body(doc, "매도인은 본 계약 체결일 및 거래종결일을 기준으로 다음 각 사항을 진술하고 보장한다.")
    _add_body(doc, "① 매도인은 본 계약을 체결하고 이행할 완전한 권한을 보유한다.", indent_cm=1.30)
    _add_body(doc, "② 대상주식에는 제한부담(유치권, 질권, 저당권 등)이 설정되어 있지 아니하다.", indent_cm=1.30)
    _add_body(doc, "③ 대상회사는 대한민국 법령에 따라 적법하게 설립·존속 중인 주식회사이다.", indent_cm=1.30)
    _add_subheading(doc, "매수인의 진술 및 보장.")
    _add_body(doc, "매수인은 본 계약 체결일 및 거래종결일을 기준으로 다음 각 사항을 진술하고 보장한다.")
    _add_body(doc, "① 매수인은 본 계약을 체결하고 이행할 완전한 권한을 보유한다.", indent_cm=1.30)
    _add_body(doc, "② 본 계약의 체결 및 이행에 어떠한 법적 장애사유도 존재하지 아니한다.", indent_cm=1.30)

    # 제6조 에스크로
    _add_article_heading(doc, 6, "에스크로")
    _add_body(
        doc,
        "매수인은 거래종결 시 매매대금 중 금 {{ escrow_amount }}원을 "
        "당사자들이 별도로 합의하는 에스크로 계좌에 예치하며, "
        "동 금원은 매도인의 진술보장 위반에 따른 손해배상 등 책임 이행을 위한 담보로서 "
        "{{ escrow_period_months }}개월간 유지된다.",
    )

    # 제7조 손해배상 및 면책
    _add_article_heading(doc, 7, "손해배상 및 면책")
    _add_body(
        doc,
        "일방 당사자가 본 계약상 진술·보장을 위반하거나 의무를 불이행하는 경우, "
        "상대방 당사자에게 발생한 손해를 배상한다. "
        "매도인의 진술·보장에 기한 배상 청구 기간은 거래종결일로부터 {{ warranty_period_months }}개월로 한다.",
    )

    # 제8조 비밀유지
    _add_article_heading(doc, 8, "비밀유지")
    _add_body(
        doc,
        "각 당사자는 본 계약의 내용 및 거래 협의 과정에서 취득한 상대방의 비밀정보를 "
        "상대방의 사전 서면 동의 없이 제3자에게 공개하거나 본 계약 이외의 목적으로 사용하여서는 아니 된다.",
    )

    # 제9조 준거법
    _add_article_heading(doc, 9, "준거법 및 관할")
    _add_body(
        doc,
        "본 계약은 {{ governing_law }} 법에 따라 해석되며, "
        "본 계약으로부터 발생하는 분쟁은 서울중앙지방법원을 제1심 전속 관할법원으로 한다.",
    )

    # 제10조 일반 조항
    _add_article_heading(doc, 10, "일반 조항")
    _add_body(
        doc,
        "본 계약은 대상주식의 매수도에 관하여 당사자간의 완전한 합의를 구성하며, "
        "본 계약 체결 이전의 구두 또는 서면에 의한 모든 합의에 우선한다. "
        "본 계약의 변경은 양 당사자가 서명한 서면에 의하여야 한다.",
    )

    _add_date_line(doc)
    _add_signature_table(
        doc,
        [
            ("매도인 (甲)", "{{ seller_name }}", "{{ seller_representative }}"),
            ("매수인 (乙)", "{{ buyer_name }}", "{{ buyer_representative }}"),
        ],
    )

    out_path = out_dir / "spa_template.docx"
    doc.save(str(out_path))
    print(f"[OK] SPA 템플릿 생성: {out_path}")


# ─── SHA 템플릿 ───────────────────────────────────────────────────────────────


def create_sha_template(out_dir: Path) -> None:
    """주주간계약서 (Shareholders Agreement) 템플릿 생성."""
    doc = Document()
    _set_margins(doc, left=2.54, right=2.54, top=3.00, bottom=2.54)

    _add_title(doc, "주 주 간 계 약 서", size_pt=16.0, space_before_pt=80.0)
    _add_subtitle(doc, "(Shareholders Agreement)")
    doc.add_page_break()

    _add_preamble_text(
        doc,
        '본 주주간계약(이하 "본 계약")은 {{ signing_date }}(이하 "본 계약 체결일") 아래 당사자들 사이에서 체결되었다.',
    )

    # 주주 목록 반복
    _add_jinja_block(doc, "{%p for s in shareholders %}")
    _add_preamble_body(doc, '{{ s.name }}(이하 "{{ s.name }}")', indent_cm=1.30)
    _add_jinja_block(doc, "{%p endfor %}")

    _add_section_label(doc, "전     문")
    _add_preamble_text(doc, '본 계약 체결일 현재 {{ company_name }}(이하 "대상회사")의 주주 구성은 다음과 같다.')
    _add_preamble_text(
        doc, "당사자들은 대상회사의 공동 운영과 당사자들의 권리·의무를 규율하기 위하여 본 계약을 체결한다."
    )
    _add_section_label(doc, "아     래")

    # 제1조 정의
    _add_article_heading(doc, 1, "정의 및 목적")
    _add_body(
        doc,
        "본 계약에서 사용되는 용어는 본건 주식매매계약 및 신주인수계약에서 정한 바에 따르며, "
        "본 계약은 대상회사의 경영과 주주간 관계를 규율하는 것을 목적으로 한다.",
    )

    # 제2조 이사회
    _add_article_heading(doc, 2, "이사회 구성 및 임원")
    _add_subheading(doc, "이사회 구성.")
    _add_body(doc, "대상회사의 이사회는 총 {{ board_seats_total }}인 이상으로 한다.")
    _add_subheading(doc, "이사 지명권.")
    _add_jinja_block(doc, "{%p for b in board_seats_by_shareholder %}")
    _add_body(doc, "{{ b.shareholder }}은(는) 이사 {{ b.seats }}인을 지명할 권리를 가진다.", indent_cm=1.30)
    _add_jinja_block(doc, "{%p endfor %}")

    # 제3조 우선매수권
    _add_article_heading(doc, 3, "우선매수권 (Right of First Refusal)")
    _add_jinja_block(doc, "{%p if rofr_included %}")
    _add_body(
        doc,
        "주주가 그 보유주식의 전부 또는 일부를 제3자에게 양도(담보 설정 포함)하고자 하는 경우, "
        "다른 주주는 당해 양도 예정 주식에 대하여 우선적으로 매수할 권리를 가진다.",
    )
    _add_jinja_block(doc, "{%p else %}")
    _add_body(doc, "본 계약에서 우선매수권은 적용하지 아니한다.")
    _add_jinja_block(doc, "{%p endif %}")

    # 제4조 동반매각권
    _add_article_heading(doc, 4, "동반매각권 (Drag-Along Right)")
    _add_jinja_block(doc, "{%p if drag_along_included %}")
    _add_body(
        doc,
        "지배주주가 제3자에게 대상회사 발행주식의 과반수 이상을 매각하고자 하는 경우, "
        "지배주주는 다른 주주들로 하여금 동일한 조건으로 그 보유주식을 함께 매각하도록 요구할 수 있다.",
    )
    _add_jinja_block(doc, "{%p else %}")
    _add_body(doc, "본 계약에서 동반매각권은 적용하지 아니한다.")
    _add_jinja_block(doc, "{%p endif %}")

    # 제5조 동반참여권
    _add_article_heading(doc, 5, "동반참여권 (Tag-Along Right)")
    _add_jinja_block(doc, "{%p if tag_along_included %}")
    _add_body(
        doc,
        "지배주주가 제3자에게 그 보유주식의 전부 또는 일부를 매각하고자 하는 경우, "
        "다른 주주는 동일한 조건으로 자신의 보유주식을 함께 매각할 권리를 가진다.",
    )
    _add_jinja_block(doc, "{%p else %}")
    _add_body(doc, "본 계약에서 동반참여권은 적용하지 아니한다.")
    _add_jinja_block(doc, "{%p endif %}")

    # 제6조 락업
    _add_article_heading(doc, 6, "주식 처분 제한 (Lock-up)")
    _add_body(
        doc,
        "각 주주는 본 계약 체결일로부터 {{ lock_up_months }}개월이 경과하는 날까지 "
        "다른 당사자의 사전 서면 동의 없이 그 보유주식 또는 그 일부를 "
        "제3자에게 양도하거나 담보권을 설정하여서는 아니 된다.",
    )

    # 제7조 경업금지
    _add_article_heading(doc, 7, "경업금지 및 비밀유지")
    _add_body(
        doc,
        "각 주주는 본 계약 종료 후 {{ non_compete_months }}개월 동안 대상회사와 동일하거나 "
        "유사한 사업을 직접 또는 제3자를 통해 영위하여서는 아니 된다.",
    )

    # 제8조 준거법
    _add_article_heading(doc, 8, "준거법 및 관할")
    _add_body(
        doc,
        "본 계약은 {{ governing_law }} 법에 따라 해석되며, "
        "본 계약으로부터 발생하는 분쟁은 서울중앙지방법원을 제1심 전속 관할법원으로 한다.",
    )

    _add_date_line(doc)

    # 주주 서명란
    doc.add_paragraph()
    sig_label = doc.add_paragraph("【 주주 서명란 】")
    for run in sig_label.runs:
        _apply_font(run, size_pt=12.0, bold=True)

    _add_jinja_block(doc, "{%p for s in shareholders %}")
    _add_body(
        doc,
        "주주: {{ s.name }}   보유주식: {{ s.shares }}주   지분율: {{ s.pct }}%",
        indent_cm=1.30,
    )
    _add_jinja_block(doc, "{%p endfor %}")

    out_path = out_dir / "sha_template.docx"
    doc.save(str(out_path))
    print(f"[OK] SHA 템플릿 생성: {out_path}")


# ─── BTA 템플릿 ───────────────────────────────────────────────────────────────


def create_bta_template(out_dir: Path) -> None:
    """영업양수도계약서 (Business Transfer Agreement) 템플릿 생성.

    BTA 샘플 참조: 'Clean Pjt Jade_영업양수도계약서_Seller markup_251028.docx'
    서식: LK_본문(바탕 12pt), LK_Level1(조 제목), LK_Level2(항), LK_Level3(호)
    여백: 좌2.50 우2.50 상3.00 하3.00 cm, 제목 20pt
    """
    doc = Document()
    _set_margins(doc, left=2.50, right=2.50, top=3.00, bottom=3.00)

    _add_title(doc, "영 업 양 수 도 계 약 서", size_pt=20.0, space_before_pt=80.0)
    _add_subtitle(doc, "(Business Transfer Agreement)")
    doc.add_page_break()

    # 전문
    _add_preamble_text(
        doc,
        '본 영업양수도계약(이하 "본 계약")은 {{ signing_date }}(이하 "본 계약 체결일") '
        "아래 당사자들 사이에서 체결되었다.",
    )
    _add_preamble_body(doc, '{{ transferor_name }}(이하 "양도인")', indent_cm=1.50)
    _add_preamble_body(
        doc, '{{ transferee_name }}(이하 "양수인", 양도인과 양수인을 총칭하여 "당사자들")', indent_cm=1.50
    )

    _add_section_label(doc, "전     문")
    _add_preamble_text(
        doc,
        "양도인은 {{ business_description }}을(를) 영위하고 있으며, "
        "양도인과 양수인은 본 계약에서 정하는 바에 따라 양도인이 양수인에게 "
        "양도대상 영업을 포괄적으로 양도하고, 양수인은 이를 양수하는 거래를 진행하기로 합의하였다.",
    )
    _add_preamble_text(doc, "이에 당사자들은 아래와 같이 합의한다.")
    _add_section_label(doc, "아     래")

    # 제1조 정의
    _add_article_heading(doc, 1, "정의")
    _add_subheading(doc, "정의.")
    _add_body(doc, "본 계약에서 사용되는 다음의 용어는 아래 규정된 의미를 가진다.")
    _add_body(doc, '"양도대상 영업"이란 {{ business_description }}을 말한다.', indent_cm=1.40)
    _add_body(doc, '"거래종결일"이란 {{ closing_date }}을 말한다.', indent_cm=1.40)
    _add_body(doc, '"양도대금"이란 금 {{ total_consideration }}원을 말한다.', indent_cm=1.40)

    # 제2조 양도대상 영업
    _add_article_heading(doc, 2, "양도대상 영업의 범위")
    _add_subheading(doc, "이전 자산.")
    _add_body(doc, '양도영업에 포함되는 자산(이하 "이전 자산")은 다음과 같다.')
    _add_jinja_block(doc, "{%p for asset in transferred_assets %}")
    _add_body(doc, "· {{ asset }}", indent_cm=1.40)
    _add_jinja_block(doc, "{%p endfor %}")
    _add_subheading(doc, "제외 자산.")
    _add_body(doc, "다음 자산은 양도 대상에서 제외한다.")
    _add_jinja_block(doc, "{%p for asset in excluded_assets %}")
    _add_body(doc, "· {{ asset }}", indent_cm=1.40)
    _add_jinja_block(doc, "{%p endfor %}")

    # 제3조 부채 인수
    _add_article_heading(doc, 3, "부채 및 의무의 인수")
    _add_body(doc, "양수인은 거래종결일에 다음의 부채 및 의무를 인수한다.")
    _add_jinja_block(doc, "{%p for liab in transferred_liabilities %}")
    _add_body(doc, "· {{ liab }}", indent_cm=1.40)
    _add_jinja_block(doc, "{%p endfor %}")

    # 제4조 양도대금
    _add_article_heading(doc, 4, "양도대금")
    _add_subheading(doc, "양도대금.")
    _add_body(doc, "양도대상 영업의 대금은 금 {{ total_consideration }}원으로 한다.")
    _add_subheading(doc, "지급 방법.")
    _add_body(doc, "양수인은 거래종결일에 양도인이 서면으로 지정하는 계좌로 양도대금 전액을 지급한다.")

    # 제5조 직원 이전
    _add_article_heading(doc, 5, "직원 이전")
    _add_jinja_block(doc, "{%p if employee_transfer %}")
    _add_body(
        doc,
        "양도인 소속 직원 {{ employee_count }}명은 거래종결일 기준으로 양수인에게 이전하며, "
        "이전 직원의 근속기간 및 퇴직금 승계에 관하여는 별도 합의로 정한다.",
    )
    _add_jinja_block(doc, "{%p else %}")
    _add_body(doc, "직원 이전 여부 및 조건은 별도 협의에 따른다.")
    _add_jinja_block(doc, "{%p endif %}")

    # 제6조 선행조건
    _add_article_heading(doc, 6, "선행조건")
    _add_body(doc, "거래종결은 아래 각 호의 선행조건이 모두 충족(또는 포기)됨을 전제로 한다.")
    _add_body(doc, "① 각 당사자의 진술 및 보장이 거래종결일을 기준으로 중요한 면에서 사실과 부합할 것", indent_cm=1.40)
    _add_body(doc, "② 각 당사자가 본 계약상 의무를 중요한 면에서 이행하였을 것", indent_cm=1.40)
    _add_body(doc, "③ 관련 인허가 및 제3자 동의 취득 완료", indent_cm=1.40)

    # 제7조 진술 및 보장
    _add_article_heading(doc, 7, "진술 및 보장")
    _add_subheading(doc, "양도인의 진술 및 보장.")
    _add_body(doc, "양도인은 본 계약 체결일 및 거래종결일을 기준으로 다음 각 사항을 진술하고 보장한다.")
    _add_body(doc, "① 양도인은 본 계약을 체결하고 이행할 완전한 권한을 보유한다.", indent_cm=1.40)
    _add_body(doc, "② 양도대상 영업에는 별도 공시된 사항 외에 중요한 하자가 없다.", indent_cm=1.40)

    # 제8조 준거법
    _add_article_heading(doc, 8, "준거법 및 관할")
    _add_body(
        doc, "본 계약은 {{ governing_law }} 법에 따라 해석되며, 분쟁은 서울중앙지방법원을 제1심 전속 관할법원으로 한다."
    )

    _add_date_line(doc)
    _add_signature_table(
        doc,
        [
            ("양도인 (甲)", "{{ transferor_name }}", "{{ transferor_representative }}"),
            ("양수인 (乙)", "{{ transferee_name }}", "{{ transferee_representative }}"),
        ],
    )

    out_path = out_dir / "bta_template.docx"
    doc.save(str(out_path))
    print(f"[OK] BTA 템플릿 생성: {out_path}")


# ─── SSA 템플릿 ───────────────────────────────────────────────────────────────


def create_ssa_template(out_dir: Path) -> None:
    """신주인수계약서 (Share Subscription Agreement) 템플릿 생성."""
    doc = Document()
    _set_margins(doc, left=2.54, right=2.54, top=3.00, bottom=2.54)

    _add_title(doc, "신 주 인 수 계 약 서", size_pt=16.0, space_before_pt=80.0)
    _add_subtitle(doc, "(Share Subscription Agreement)")
    doc.add_page_break()

    # 전문
    _add_preamble_text(
        doc,
        '본 신주인수계약(이하 "본 계약")은 {{ signing_date }}(이하 "본 계약 체결일") '
        "아래 당사자들 사이에서 체결되었다.",
    )
    _add_preamble_body(doc, '{{ company_name }}(이하 "발행회사")', indent_cm=1.30)
    _add_preamble_body(doc, '{{ investor_name }}(이하 "인수인")', indent_cm=1.30)
    _add_preamble_body(doc, '(발행회사와 인수인을 총칭하여 "당사자들", 개별적으로 "당사자")', indent_cm=1.30)

    _add_section_label(doc, "전     문")
    _add_preamble_text(
        doc,
        "발행회사는 본 계약 체결일 현재 {{ share_class }} 주식을 발행하고 있으며, "
        "발행회사와 인수인은 발행회사가 인수인에게 대상신주({{ new_shares_count }}주)를 "
        "제3자 배정 유상증자 방식으로 발행하여 배정하는 거래를 진행하기로 합의하였다.",
    )
    _add_preamble_text(doc, "이에 당사자들은 아래와 같이 합의한다.")
    _add_section_label(doc, "아     래")

    # 제1조 정의
    _add_article_heading(doc, 1, "정의")
    _add_body(doc, "본 계약에서 사용되는 주요 용어는 다음과 같이 정의한다.")
    _add_body(
        doc,
        '"대상신주"라 함은 발행회사가 제3자 배정 유상증자 방식으로 인수인에게 발행하는 {{ share_class }} {{ new_shares_count }}주를 말한다.',
        indent_cm=1.30,
    )
    _add_body(
        doc,
        '"신주인수대금"이라 함은 대상신주의 1주당 발행금액 금 {{ subscription_price_per }}원에 대상신주의 수를 곱한 총 금 {{ total_investment }}원을 말한다.',
        indent_cm=1.30,
    )
    _add_body(doc, '"발행일"이라 함은 거래종결일 다음 날을 말한다.', indent_cm=1.30)
    _add_body(doc, '"거래종결일"이라 함은 {{ investment_date }}을 말한다.', indent_cm=1.30)

    # 제2조 대상신주 인수
    _add_article_heading(doc, 2, "대상신주 인수")
    _add_subheading(doc, "대상신주 인수.")
    _add_body(
        doc,
        "본 계약에서 정하는 조건에 따라, 발행회사는 인수인에게 제3자 배정 유상증자 방식으로 "
        "대상신주({{ share_class }} {{ new_shares_count }}주)를 발행하여 배정하고, 인수인은 이를 인수한다.",
    )
    _add_subheading(doc, "신주인수대금.")
    _add_body(
        doc,
        "대상신주의 1주당 발행금액은 금 {{ subscription_price_per }}원(총 발행금액 금 {{ total_investment }}원)이다.",
    )

    # 제3조 거래종결
    _add_article_heading(doc, 3, "거래종결")
    _add_subheading(doc, "거래종결.")
    _add_body(
        doc,
        '신주인수대금의 납입을 위한 거래의 종결(이하 "거래종결")은 {{ investment_date }}(이하 "거래종결일")에 이루어진다.',
    )
    _add_subheading(doc, "거래종결 방법.")
    _add_body(doc, "거래종결일에 인수인은 다음 각 호를 이행한다.")
    _add_body(doc, "① 신주인수대금 전액을 발행회사 지정 계좌에 납입", indent_cm=1.30)
    _add_body(doc, "거래종결일에 발행회사는 다음 각 호를 이행한다.")
    _add_body(doc, "① 신주인수대금 전액에 대한 영수증 교부", indent_cm=1.30)
    _add_body(doc, "② 주금납입증명서 교부", indent_cm=1.30)
    _add_body(doc, "③ 이사회 의사록 사본 교부", indent_cm=1.30)

    # 제4조 기업가치
    _add_article_heading(doc, 4, "기업가치 및 지분율")
    _add_body(
        doc,
        "본 거래 기준 발행회사의 Pre-money 기업가치는 금 {{ pre_money_valuation }}원이며, "
        "Post-money 기업가치는 금 {{ post_money_valuation }}원이다.",
    )

    # 제5조 희석방지
    _add_article_heading(doc, 5, "희석방지 조항")
    _add_body(
        doc,
        "발행회사가 본 거래 이후 더 낮은 발행가격으로 신주를 발행하는 경우, "
        "{{ anti_dilution }} 방식으로 인수인의 실질적인 인수가액을 조정한다.",
    )

    # 제6조 청산우선권
    _add_article_heading(doc, 6, "청산우선권")
    _add_body(
        doc,
        "발행회사가 해산·청산하는 경우, 인수인은 다른 주주에 우선하여 "
        "신주인수대금의 {{ liquidation_preference_x }}배에 해당하는 금액을 분배받을 권리를 가진다.",
    )

    # 제7조 이사 지명권
    _add_article_heading(doc, 7, "이사 지명권")
    _add_body(doc, "인수인은 대상회사의 이사회에 {{ board_seats }}인의 이사를 지명할 권리를 가진다.")

    # 제8조 자금 사용 목적
    _add_article_heading(doc, 8, "자금 사용 목적")
    _add_body(
        doc,
        "발행회사는 신주인수대금을 아래 목적에만 사용하며, "
        "그 외의 목적으로 사용하고자 하는 경우 인수인의 사전 서면 동의를 받아야 한다.",
    )
    _add_body(doc, "{{ use_of_proceeds }}", indent_cm=1.30)

    # 제9조 준거법
    _add_article_heading(doc, 9, "준거법 및 관할")
    _add_body(
        doc, "본 계약은 {{ governing_law }} 법에 따라 해석되며, 분쟁은 서울중앙지방법원을 제1심 전속 관할법원으로 한다."
    )

    _add_date_line(doc)
    _add_signature_table(
        doc,
        [
            ("발행회사 (甲)", "{{ company_name }}", "{{ company_representative }}"),
            ("인수인 (乙)", "{{ investor_name }}", "{{ investor_representative }}"),
        ],
    )

    out_path = out_dir / "ssa_template.docx"
    doc.save(str(out_path))
    print(f"[OK] SSA 템플릿 생성: {out_path}")


# ─── MOU 템플릿 ───────────────────────────────────────────────────────────────


def create_mou_template(out_dir: Path) -> None:
    """양해각서 (Memorandum of Understanding) 템플릿 생성."""
    doc = Document()
    _set_margins(doc, left=2.50, right=2.50, top=3.00, bottom=2.50)

    _add_title(doc, "양  해  각  서", size_pt=14.0, space_before_pt=80.0)
    _add_subtitle(doc, "(Memorandum of Understanding)")
    doc.add_page_break()

    # 전문
    _add_preamble_text(
        doc,
        '본 양해각서(이하 "본 양해각서")는 {{ signing_date }}(이하 "본 양해각서 체결일")에 '
        "다음의 당사자들 사이에서 체결되었다.",
    )
    _add_preamble_body(doc, '{{ party_a_name }} 및 그 관계인들(이하 총칭하여 "매도인대표")', indent_cm=1.30)
    _add_preamble_body(
        doc, '{{ party_b_name }}(이하 "매수인", 매도인대표와 매수인을 총칭하여 "당사자들")', indent_cm=1.30
    )

    _add_section_label(doc, "전     문")
    _add_preamble_text(doc, "당사자들은 {{ purpose }}에 관한 기본적인 사항을 정하고자 본 양해각서를 체결한다.")

    # 각 조항
    _add_article_heading(doc, 1, "이행보증금 납입 및 독점적 협상권 부여")
    _add_body(
        doc,
        "본 양해각서 체결 즉시 매수인은 매도인대표가 지정하는 계좌에 이행보증금을 납입하며, "
        "매도인대표는 본 양해각서 체결일로부터 {{ exclusivity_start_date }}까지 "
        '{{ exclusivity_period_days }}일간(이하 "독점적 협상기간") 매수인에게 독점적 협상권을 부여한다.',
    )

    _add_article_heading(doc, 2, "실사")
    _add_body(
        doc,
        "매수인은 독점적 협상기간 동안 본건 거래와 관련하여 대상회사에 대한 재무, 조세, 법률, "
        "환경 등 제반 실사를 진행할 예정이고, 매도인대표는 이에 필요한 자료와 협조를 제공한다.",
    )

    _add_article_heading(doc, 3, "구속력 있는 조항")
    _add_body(doc, "본 양해각서 중 다음 각 호의 조항은 당사자들을 법적으로 구속한다.")
    _add_jinja_block(doc, "{%p for p in binding_provisions %}")
    _add_body(doc, "· {{ p }}", indent_cm=1.30)
    _add_jinja_block(doc, "{%p endfor %}")

    _add_article_heading(doc, 4, "비구속적 조항")
    _add_body(
        doc,
        "다음 각 호의 사항은 법적 구속력을 갖지 아니하며, "
        "향후 당사자들 사이에 별도로 체결될 본계약에서 최종적으로 합의될 예정이다.",
    )
    _add_jinja_block(doc, "{%p for p in non_binding_provisions %}")
    _add_body(doc, "· {{ p }}", indent_cm=1.30)
    _add_jinja_block(doc, "{%p endfor %}")

    _add_article_heading(doc, 5, "비밀유지")
    _add_body(
        doc,
        "당사자들은 본 양해각서 및 본건 거래의 협의 과정에서 알게 된 상대방의 비밀정보를 "
        "상대방의 사전 서면 동의 없이 제3자에게 공개하거나 본건 거래 이외의 목적으로 사용하여서는 아니 된다. "
        "비밀유지 의무는 본 양해각서 종료 후 {{ confidentiality_period_months }}개월간 존속한다.",
    )

    _add_article_heading(doc, 6, "준거법 및 관할")
    _add_body(
        doc,
        "본 양해각서는 {{ governing_law }} 법에 따라 해석되며, 분쟁은 서울중앙지방법원을 제1심 전속 관할법원으로 한다.",
    )

    _add_date_line(doc)
    _add_signature_table(
        doc,
        [
            ("매도인대표 (甲)", "{{ party_a_name }}", "{{ party_a_representative }}"),
            ("매수인 (乙)", "{{ party_b_name }}", "{{ party_b_representative }}"),
        ],
    )

    out_path = out_dir / "mou_template.docx"
    doc.save(str(out_path))
    print(f"[OK] MOU 템플릿 생성: {out_path}")


# ─── 메인 ─────────────────────────────────────────────────────────────────────


def main() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 템플릿 저장 위치: {TEMPLATE_DIR.resolve()}")
    print(f"[INFO] 템플릿 버전: {TEMPLATE_VERSION}")
    print("[INFO] 서식 기준: 체결본 분석 결과 (바탕체, A4, 표준 여백)\n")

    create_spa_template(TEMPLATE_DIR)
    create_sha_template(TEMPLATE_DIR)
    create_bta_template(TEMPLATE_DIR)
    create_ssa_template(TEMPLATE_DIR)
    create_mou_template(TEMPLATE_DIR)

    print(f"\n[DONE] 법률 문서 템플릿 5종 생성 완료 (v{TEMPLATE_VERSION})")


if __name__ == "__main__":
    main()
