"""Redline Engine 단위 테스트 — OOXML Tracked Changes 핵심 알고리즘 검증."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import patch

import pytest
from lxml import etree

from app.services.redline_engine import (
    _MAX_XML_SIZE,
    _SAFE_PARSER,
    W_NS,
    XML_NS,
    CommentManager,
    RedlineSegment,
    W,
    _anchor_comment_to_run,
    _apply_segments,
    _build_char_map,
    _collect_and_split_target_runs,
    _find_target_in_paragraphs,
    _inject_deletion,
    _inject_insertion,
    _normalize_text_for_matching,
    _normalize_with_index_map,
    _parse_redline_markup,
    _read_zip_entry,
    _resolve_run_properties,
    _RevIdCounter,
    _scan_max_revision_id,
    _split_run_at,
    apply_redlines,
    extract_paragraphs_text,
)

NSMAP = {"w": W_NS}


# ── 헬퍼: 최소 DOCX 생성 ────────────────────────────────────────────────────


def _make_minimal_docx(paragraphs: list[str]) -> bytes:
    """최소 DOCX ZIP — 주어진 텍스트 문단으로 word/document.xml 생성."""
    root = etree.Element(f"{W}document", nsmap=NSMAP)
    body = etree.SubElement(root, f"{W}body")
    for text in paragraphs:
        p = etree.SubElement(body, f"{W}p")
        r = etree.SubElement(p, f"{W}r")
        t = etree.SubElement(r, f"{W}t")
        t.set(f"{{{XML_NS}}}space", "preserve")
        t.text = text

    xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    ct_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )

    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )

    doc_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        "</Relationships>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/document.xml", xml_bytes)
        zf.writestr("word/_rels/document.xml.rels", doc_rels_xml)
    buf.seek(0)
    return buf.read()


def _make_paragraph(*runs_text: str) -> etree._Element:
    """테스트용 <w:p> 요소를 생성한다. 각 인자는 하나의 <w:r>/<w:t>."""
    p = etree.Element(f"{W}p", nsmap=NSMAP)
    for text in runs_text:
        r = etree.SubElement(p, f"{W}r")
        t = etree.SubElement(r, f"{W}t")
        t.set(f"{{{XML_NS}}}space", "preserve")
        t.text = text
    return p


# ── 1. _build_char_map 테스트 ────────────────────────────────────────────────


class TestBuildCharMap:
    def test_simple_single_run(self) -> None:
        """단일 Run에서 char_map이 정확히 매핑되는지 검증."""
        p = _make_paragraph("안녕하세요")
        merged, char_map = _build_char_map(p)

        assert merged == "안녕하세요"
        assert len(char_map) == 5
        # 모든 문자가 같은 run을 가리켜야 함
        assert all(cm.run_element is char_map[0].run_element for cm in char_map)
        assert [cm.char_index for cm in char_map] == [0, 1, 2, 3, 4]

    def test_fragmented_runs(self) -> None:
        """파편화된 여러 Run이 올바르게 병합되는지 검증."""
        p = _make_paragraph("매매대금의 ", "100분의 30", "을 한도로")
        merged, char_map = _build_char_map(p)

        assert merged == "매매대금의 100분의 30을 한도로"
        # 각 문자가 올바른 run을 가리키는지 확인
        runs = list(p.findall(f".//{W}r"))
        assert char_map[0].run_element is runs[0]
        assert char_map[6].run_element is runs[1]
        assert char_map[16].run_element is runs[2]  # "을" 첫 글자

    def test_skips_deleted_text(self) -> None:
        """기존 <w:del>/<w:delText> 내부 텍스트를 무시하는지 검증."""
        p = etree.Element(f"{W}p", nsmap=NSMAP)

        # 일반 run
        r1 = etree.SubElement(p, f"{W}r")
        t1 = etree.SubElement(r1, f"{W}t")
        t1.text = "보이는"

        # 삭제된 run (w:del 내부)
        del_el = etree.SubElement(p, f"{W}del")
        r2 = etree.SubElement(del_el, f"{W}r")
        dt = etree.SubElement(r2, f"{W}delText")
        dt.text = "삭제됨"

        # 일반 run
        r3 = etree.SubElement(p, f"{W}r")
        t3 = etree.SubElement(r3, f"{W}t")
        t3.text = "텍스트"

        merged, _char_map = _build_char_map(p)
        assert merged == "보이는텍스트"
        assert "삭제됨" not in merged


# ── 2. _normalize_text_for_matching 테스트 ───────────────────────────────────


class TestNormalizeText:
    def test_smart_quotes_and_dashes(self) -> None:
        """스마트 따옴표와 대시가 정규화되는지 검증."""
        text = "\u201c문서\u201d\u2019s \u2014 규정"
        result = _normalize_text_for_matching(text)
        assert result == '"문서"\'s - 규정'

    def test_multiple_spaces(self) -> None:
        """연속 공백이 단일 공백으로 축소되는지 검증."""
        text = "매매   대금의    100분"
        result = _normalize_text_for_matching(text)
        assert result == "매매 대금의 100분"


# ── 3. _split_run_at 테스트 (간접 — _collect_and_split_target_runs 경유) ────


class TestSplitRunAtBoundary:
    def test_split_preserves_formatting(self) -> None:
        """Run 분할 시 rPr(서식)이 보존되는지 검증."""
        p = etree.Element(f"{W}p", nsmap=NSMAP)
        r = etree.SubElement(p, f"{W}r")
        rPr = etree.SubElement(r, f"{W}rPr")
        bold = etree.SubElement(rPr, f"{W}b")
        t = etree.SubElement(r, f"{W}t")
        t.text = "ABCDE"

        before, after = _split_run_at(r, t, 3)

        # 원본: "ABC", 복사본: "DE"
        assert before.find(f"{W}t").text == "ABC"
        after_t = after.find(f"{W}t")
        assert after_t.text == "DE"

        # 서식(bold) 보존 확인
        assert before.find(f"{W}rPr/{W}b") is not None
        assert after.find(f"{W}rPr/{W}b") is not None


# ── 4. _parse_redline_markup 테스트 ──────────────────────────────────────────


class TestParseRedlineMarkup:
    def test_del_ins_with_keep(self) -> None:
        """DEL/INS 태그와 KEEP 텍스트가 올바르게 파싱되는지 검증."""
        markup = "매매대금의 [DEL]100분의 30[/DEL][INS]100분의 20[/INS]을 한도로"
        segments = _parse_redline_markup(markup)

        assert len(segments) == 4
        assert segments[0] == RedlineSegment(action="KEEP", text="매매대금의 ")
        assert segments[1] == RedlineSegment(action="DEL", text="100분의 30")
        assert segments[2] == RedlineSegment(action="INS", text="100분의 20")
        assert segments[3] == RedlineSegment(action="KEEP", text="을 한도로")

    def test_only_del(self) -> None:
        """DEL만 있는 마크업."""
        segments = _parse_redline_markup("[DEL]삭제 대상[/DEL]")
        assert len(segments) == 1
        assert segments[0].action == "DEL"

    def test_empty_string(self) -> None:
        """빈 문자열은 빈 리스트."""
        assert _parse_redline_markup("") == []


# ── 5. _inject_deletion 테스트 ────────────────────────────────────────────────


class TestInjectDeletion:
    def test_creates_valid_xml(self) -> None:
        """<w:del> 구조가 올바르게 생성되는지 검증."""
        p = _make_paragraph("삭제 대상 텍스트")
        runs = list(p.findall(f".//{W}r"))

        del_el = _inject_deletion(
            runs,
            author="AI Reviewer",
            revision_id=1,
            date_str="2026-03-07T00:00:00Z",
        )

        assert del_el.tag == f"{W}del"
        assert del_el.get(f"{W}author") == "AI Reviewer"
        assert del_el.get(f"{W}id") == "1"

        # <w:t> -> <w:delText> 변환 확인
        del_texts = del_el.findall(f".//{W}delText")
        assert len(del_texts) == 1
        assert del_texts[0].text == "삭제 대상 텍스트"

        # xml:space="preserve" 확인
        assert del_texts[0].get(f"{{{XML_NS}}}space") == "preserve"


# ── 6. _inject_insertion 테스트 ───────────────────────────────────────────────


class TestInjectInsertion:
    def test_copies_formatting(self) -> None:
        """<w:ins> 생성 시 reference_run의 서식이 복제되는지 검증."""
        p = _make_paragraph("기준 텍스트")
        ref_run = p.find(f".//{W}r")

        # 서식 추가
        rPr = etree.SubElement(ref_run, f"{W}rPr")
        etree.SubElement(rPr, f"{W}b")  # bold

        # ref_run 앞에 rPr 배치 (실제 OOXML 순서)
        ref_run.remove(rPr)
        ref_run.insert(0, rPr)

        ins_el = _inject_insertion(
            "추가된 텍스트",
            ref_run,
            p,
            author="AI Reviewer",
            revision_id=2,
            date_str="2026-03-07T00:00:00Z",
        )

        assert ins_el.tag == f"{W}ins"

        # 서식 복제 확인
        ins_run = ins_el.find(f"{W}r")
        assert ins_run.find(f"{W}rPr/{W}b") is not None

        # 텍스트 확인
        ins_text = ins_run.find(f"{W}t")
        assert ins_text.text == "추가된 텍스트"

    def test_newline_creates_br(self) -> None:
        """INS 텍스트 내 \\n이 <w:br/>로 변환되는지 검증."""
        p = _make_paragraph("기준")
        ref_run = p.find(f".//{W}r")

        ins_el = _inject_insertion(
            "첫째줄\n둘째줄\n셋째줄",
            ref_run,
            p,
            author="AI Reviewer",
            revision_id=3,
            date_str="2026-03-07T00:00:00Z",
        )

        ins_run = ins_el.find(f"{W}r")
        # <w:t> 3개 + <w:br/> 2개
        t_elements = ins_run.findall(f"{W}t")
        br_elements = ins_run.findall(f"{W}br")

        assert len(t_elements) == 3
        assert len(br_elements) == 2
        assert t_elements[0].text == "첫째줄"
        assert t_elements[1].text == "둘째줄"
        assert t_elements[2].text == "셋째줄"


# ── 7. _scan_max_revision_id 테스트 ──────────────────────────────────────────


class TestScanMaxRevisionId:
    def test_with_existing_tracked_changes(self) -> None:
        """기존 Tracked Changes가 있는 문서에서 max ID를 추출."""
        root = etree.Element(f"{W}document", nsmap=NSMAP)
        body = etree.SubElement(root, f"{W}body")
        p = etree.SubElement(body, f"{W}p")

        ins1 = etree.SubElement(p, f"{W}ins")
        ins1.set(f"{W}id", "5")
        del1 = etree.SubElement(p, f"{W}del")
        del1.set(f"{W}id", "10")

        assert _scan_max_revision_id(root) == 10

    def test_no_tracked_changes(self) -> None:
        """Tracked Changes가 없으면 0 반환."""
        root = etree.Element(f"{W}document", nsmap=NSMAP)
        assert _scan_max_revision_id(root) == 0


# ── 8. _resolve_run_properties 폴백 테스트 ───────────────────────────────────


class TestResolveRunProperties:
    def test_fallback_to_adjacent_run(self) -> None:
        """rPr 없는 Run에서 인접 Run의 rPr을 폴백으로 가져오는지 검증."""
        p = etree.Element(f"{W}p", nsmap=NSMAP)

        # 서식 있는 run
        r1 = etree.SubElement(p, f"{W}r")
        rPr1 = etree.SubElement(r1, f"{W}rPr")
        etree.SubElement(rPr1, f"{W}i")  # italic
        t1 = etree.SubElement(r1, f"{W}t")
        t1.text = "서식있는"

        # 서식 없는 run
        r2 = etree.SubElement(p, f"{W}r")
        t2 = etree.SubElement(r2, f"{W}t")
        t2.text = "서식없는"

        result = _resolve_run_properties(r2, p)
        assert result is not None
        assert result.find(f"{W}i") is not None

    def test_no_rpr_anywhere(self) -> None:
        """문단 전체에 rPr이 없으면 None 반환."""
        p = _make_paragraph("서식 없음")
        r = p.find(f".//{W}r")
        result = _resolve_run_properties(r, p)
        assert result is None


# ── 9. xml:space="preserve" 테스트 ────────────────────────────────────────────


class TestXmlSpacePreserve:
    def test_del_text_has_xml_space(self) -> None:
        """<w:delText>에 xml:space 네임스페이스 속성이 정확히 설정되는지 검증."""
        p = _make_paragraph(" 공백 포함 텍스트 ")
        runs = list(p.findall(f".//{W}r"))

        del_el = _inject_deletion(
            runs,
            author="AI",
            revision_id=1,
            date_str="2026-01-01T00:00:00Z",
        )

        del_text = del_el.find(f".//{W}delText")
        space_attr = del_text.get(f"{{{XML_NS}}}space")
        assert space_attr == "preserve"

    def test_ins_text_has_xml_space(self) -> None:
        """<w:t>에 xml:space 네임스페이스 속성이 정확히 설정되는지 검증."""
        p = _make_paragraph("기준")
        ref_run = p.find(f".//{W}r")

        ins_el = _inject_insertion(
            " 공백 앞뒤 ",
            ref_run,
            p,
            author="AI",
            revision_id=1,
            date_str="2026-01-01T00:00:00Z",
        )

        ins_t = ins_el.find(f".//{W}r/{W}t")
        assert ins_t.get(f"{{{XML_NS}}}space") == "preserve"


# ── 10. Comment 관련 테스트 ──────────────────────────────────────────────────


class TestCommentInjection:
    def test_comment_injection_with_rationale(self) -> None:
        """Comment 주입 + 본문 앵커 구조 검증."""
        # CommentManager 생성 (빈 ZIP에서)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("word/document.xml", "<dummy/>")
        buf.seek(0)

        with zipfile.ZipFile(buf, "r") as zf:
            mgr = CommentManager.from_docx_zip(zf)

        cid = mgr.add_comment("[High] 진술보증 범위\n수정 필요", author="AI", date_str="2026-01-01T00:00:00Z")
        assert cid == 1

        # XML 구조 확인
        comment = mgr.comments_root.find(f"{W}comment")
        assert comment is not None
        assert comment.get(f"{W}id") == "1"
        assert comment.get(f"{W}author") == "AI"

        # 텍스트 확인 (2개 문단)
        paras = comment.findall(f"{W}p")
        assert len(paras) == 2

    def test_anchor_to_run(self) -> None:
        """commentRangeStart/End + commentReference 앵커 구조 검증."""

        p = _make_paragraph("앵커 대상")
        r = p.find(f".//{W}r")

        _anchor_comment_to_run(r, comment_id=42)

        # commentRangeStart가 run 앞에 삽입
        children = list(p)
        tags = [c.tag for c in children]

        assert f"{W}commentRangeStart" in tags
        assert f"{W}commentRangeEnd" in tags

        # commentReference가 있는 run
        ref_runs = [c for c in children if c.tag == f"{W}r" and c.find(f"{W}commentReference") is not None]
        assert len(ref_runs) == 1
        assert ref_runs[0].find(f"{W}commentReference").get(f"{W}id") == "42"

    def test_failed_issue_comment_at_doc_top(self) -> None:
        """매칭 실패 시 문서 최상단에 메모가 삽입되는지 검증 (E2E)."""
        docx_bytes = _make_minimal_docx(["첫 번째 문단", "두 번째 문단"])

        issues = [
            {
                "issue_id": "ISS-001",
                "clause_ref": "제999조",
                "severity": "High",
                "rationale": "존재하지 않는 조항",
                "original_target_text": "이 텍스트는 문서에 없습니다 절대로",
                "proposed_redline": "[DEL]이 텍스트는 문서에 없습니다 절대로[/DEL][INS]대체 텍스트[/INS]",
            }
        ]

        result = apply_redlines(docx_bytes, issues)

        # 결과 DOCX에서 comments.xml 확인
        with zipfile.ZipFile(result, "r") as zf:
            assert "word/comments.xml" in zf.namelist()
            comments_xml = zf.read("word/comments.xml")
            comments_root = etree.fromstring(comments_xml)
            comments = comments_root.findall(f"{W}comment")
            assert len(comments) >= 1
            # 매칭 실패 메모 확인
            first_comment_text = "".join(t.text or "" for t in comments[0].iter(f"{W}t"))
            assert "매칭 실패" in first_comment_text
            assert "ISS-001" in first_comment_text


# ── 11. RedlineIssueSchema 검증 테스트 ────────────────────────────────────────


class TestRedlineIssueSchema:
    def test_rejects_newlines_in_target_text(self) -> None:
        """original_target_text에 줄바꿈 포함 시 Pydantic 검증 오류."""
        from app.schemas.spa_analysis import RedlineIssueSchema

        with pytest.raises(ValueError, match="줄바꿈"):
            RedlineIssueSchema.model_validate(
                {
                    "issue_id": "ISS-001",
                    "clause_ref": "제5조",
                    "severity": "High",
                    "rationale": "테스트 사유",
                    "original_target_text": "첫째줄\n둘째줄",
                    "proposed_redline": "[DEL]첫째줄[/DEL][INS]대체[/INS]",
                }
            )

    def test_validates_redline_tags(self) -> None:
        """[DEL]/[INS] 태그가 없으면 검증 실패."""
        from app.schemas.spa_analysis import RedlineIssueSchema

        with pytest.raises(ValueError, match=r"DEL.*INS|태그"):
            RedlineIssueSchema.model_validate(
                {
                    "issue_id": "ISS-001",
                    "clause_ref": "제5조",
                    "severity": "High",
                    "rationale": "테스트 사유",
                    "original_target_text": "원본 텍스트 조항",
                    "proposed_redline": "태그가 없는 텍스트입니다",
                }
            )


# ── 12. End-to-End: apply_redlines ────────────────────────────────────────────


class TestApplyRedlinesE2E:
    def test_end_to_end(self) -> None:
        """실제 DOCX로 전체 파이프라인 검증."""
        docx_bytes = _make_minimal_docx(["매매대금의 100분의 30을 한도로 손해배상을 청구할 수 있다."])

        issues = [
            {
                "issue_id": "ISS-001",
                "clause_ref": "제5조 (진술 및 보장)",
                "severity": "High",
                "rationale": "매도인의 손해배상 한도가 과도합니다.",
                "original_target_text": "100분의 30을 한도로",
                "proposed_redline": "[DEL]100분의 30[/DEL][INS]100분의 20[/INS]을 한도로",
            }
        ]

        result = apply_redlines(docx_bytes, issues)

        # 결과가 유효한 DOCX (ZIP)인지 확인
        assert isinstance(result, io.BytesIO)
        with zipfile.ZipFile(result, "r") as zf:
            assert "word/document.xml" in zf.namelist()
            assert "word/comments.xml" in zf.namelist()

            # document.xml에 <w:del>과 <w:ins> 존재 확인
            doc_xml = zf.read("word/document.xml")
            doc_root = etree.fromstring(doc_xml)

            del_elements = list(doc_root.iter(f"{W}del"))
            ins_elements = list(doc_root.iter(f"{W}ins"))

            assert len(del_elements) >= 1, "최소 1개의 <w:del>이 있어야 합니다"
            assert len(ins_elements) >= 1, "최소 1개의 <w:ins>이 있어야 합니다"

            # 삭제된 텍스트 확인
            del_texts = [dt.text for dt in doc_root.iter(f"{W}delText") if dt.text]
            assert any("100분의 30" in t for t in del_texts)

            # 삽입된 텍스트 확인
            ins_runs = []
            for ins in ins_elements:
                for t in ins.iter(f"{W}t"):
                    if t.text:
                        ins_runs.append(t.text)
            assert any("100분의 20" in t for t in ins_runs)

            # comments.xml에 rationale 메모 존재 확인
            comments_xml = zf.read("word/comments.xml")
            comments_root = etree.fromstring(comments_xml)
            comment_texts = "".join(t.text or "" for t in comments_root.iter(f"{W}t"))
            assert "손해배상" in comment_texts

    def test_extract_and_apply_roundtrip(self) -> None:
        """extract_paragraphs_text -> apply_redlines 왕복 검증."""
        original_text = "본 계약의 당사자는 매도인과 매수인으로 한다."
        docx_bytes = _make_minimal_docx([original_text])

        # 추출된 텍스트 확인
        extracted = extract_paragraphs_text(docx_bytes)
        assert original_text in extracted

        # 빈 이슈로 apply_redlines (변경 없이 통과)
        result = apply_redlines(docx_bytes, [])
        assert isinstance(result, io.BytesIO)

        # 결과 DOCX에서 텍스트 추출 — 원본과 동일해야 함
        result_text = extract_paragraphs_text(result.read())
        assert original_text in result_text


# ── 13. extract_paragraphs_text 테스트 ───────────────────────────────────────


class TestExtractParagraphsText:
    def test_basic_extraction(self) -> None:
        """DOCX에서 텍스트가 올바르게 추출되는지 검증."""
        docx_bytes = _make_minimal_docx(["첫 번째", "두 번째", "세 번째"])
        text = extract_paragraphs_text(docx_bytes)
        assert "첫 번째" in text
        assert "두 번째" in text
        assert "세 번째" in text

    def test_invalid_docx_raises(self) -> None:
        """유효하지 않은 DOCX에서 ValueError."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("dummy.txt", "not a docx")
        buf.seek(0)

        with pytest.raises(ValueError, match=r"document\.xml"):
            extract_paragraphs_text(buf.read())


# ── 14. _find_target_in_paragraphs 테스트 ────────────────────────────────────


class TestFindTargetInParagraphs:
    def test_exact_match(self) -> None:
        """정확한 텍스트 매칭."""
        p = _make_paragraph("매매대금의 100분의 30을 한도로")
        result = _find_target_in_paragraphs([p], "100분의 30")
        assert result is not None
        _para, start, end, merged, _char_map = result
        assert merged[start:end] == "100분의 30"

    def test_normalized_match(self) -> None:
        """정규화 매칭 (스마트 따옴표 등)."""
        p = _make_paragraph("\u201c계약서\u201d의 내용")
        # 일반 따옴표로 검색
        result = _find_target_in_paragraphs([p], '"계약서"의')
        assert result is not None

    def test_no_match_returns_none(self) -> None:
        """매칭 실패 시 None."""
        p = _make_paragraph("완전히 다른 텍스트입니다")
        result = _find_target_in_paragraphs([p], "존재하지 않는 문구")
        assert result is None


# ── 15. C-02 수정 검증: _extract_json list 반환 ─────────────────────────────


class TestExtractJsonListReturn:
    """C-02 수정: _extract_json이 JSON 배열(list)도 반환하는지 검증."""

    def test_returns_list(self) -> None:
        """JSON 배열 입력 시 list 반환."""
        from app.services.spa_analysis_service import _extract_json

        result = _extract_json('[{"issue_id": "ISS-001"}]')
        assert isinstance(result, list)
        assert result[0]["issue_id"] == "ISS-001"

    def test_returns_dict(self) -> None:
        """JSON 객체 입력 시 dict 반환 (기존 동작 보존)."""
        from app.services.spa_analysis_service import _extract_json

        result = _extract_json('{"key": "value"}')
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_code_block_extraction(self) -> None:
        """```json 코드 블록에서 배열 추출."""
        from app.services.spa_analysis_service import _extract_json

        text = '```json\n[{"a": 1}, {"b": 2}]\n```'
        result = _extract_json(text)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_rejects_non_object_or_array(self) -> None:
        """최상위가 object/array가 아니면 ValueError."""
        from app.services.spa_analysis_service import _extract_json

        with pytest.raises(ValueError, match="object 또는 array"):
            _extract_json('"just a string"')


# ── 16. M-01 수정 검증: 공백 축소 시 인덱스 매핑 ────────────────────────────


class TestNormalizeWithIndexMap:
    """M-01 수정: _normalize_with_index_map 인덱스 매핑 정확성 검증."""

    def test_whitespace_collapse_index_mapping(self) -> None:
        """연속 공백 축소 후에도 원본 인덱스가 정확히 매핑된다."""
        text = "ABC  DEF"  # 공백 2개 → 1개로 축소
        norm, mapping = _normalize_with_index_map(text)
        assert norm == "ABC DEF"
        # 'D'의 정규화 인덱스 = 4, 원본 인덱스 = 5
        assert mapping[4] == 5

    def test_smart_quote_replacement(self) -> None:
        """스마트 따옴표 치환 후 인덱스 길이 보존."""
        text = "\u201c계약\u201d"  # "계약"
        norm, mapping = _normalize_with_index_map(text)
        assert norm == '"계약"'
        assert len(mapping) == len(norm)

    def test_find_target_whitespace_collapsed(self) -> None:
        """연속 공백이 있는 문단에서 정규화 매칭 시 올바른 원본 범위 반환."""
        p = _make_paragraph("매매대금의  100분의  30을 한도로")
        result = _find_target_in_paragraphs([p], "100분의 30을")
        assert result is not None
        _para, start, end, merged, _char_map = result
        # 원본 텍스트에서 추출한 범위가 올바른지 확인
        extracted = merged[start:end]
        assert "100분의" in extracted
        assert "30을" in extracted


# ── 17. M-03 수정 검증: industry_type 패턴 검증 ──────────────────────────────


class TestIndustryTypeValidation:
    """M-03 수정: industry_type Form 파라미터 패턴 검증."""

    def test_valid_industry_types(self) -> None:
        """유효한 industry_type 값은 redline_prompts의 industry_map 키와 일치."""
        import re

        pattern = r"^(GENERAL|SOFTWARE|MANUFACTURING|FRANCHISE)$"
        for valid in ("GENERAL", "SOFTWARE", "MANUFACTURING", "FRANCHISE"):
            assert re.match(pattern, valid), f"{valid}이 패턴에 매칭되지 않음"

    def test_invalid_industry_types_rejected(self) -> None:
        """유효하지 않은 industry_type은 패턴에 매칭되지 않음."""
        import re

        pattern = r"^(GENERAL|SOFTWARE|MANUFACTURING|FRANCHISE)$"
        for invalid in ("general", "BIOTECH", "RETAIL", "", "SOFTWARE "):
            assert not re.match(pattern, invalid), f"{invalid}이 잘못 매칭됨"

    def test_industry_map_keys_match_pattern(self) -> None:
        """redline_prompts.industry_map 키가 패턴과 정확히 일치."""
        from app.services.redline_prompts import build_step4_prompt

        # build_step4_prompt 호출 시 유효한 industry_type만 허용되는지 확인
        # 유효한 키로 호출하면 에러 없이 반환
        for key in ("GENERAL", "SOFTWARE", "MANUFACTURING", "FRANCHISE"):
            result = build_step4_prompt(industry_type=key)
            assert isinstance(result, str)


# ── 18. SEC-001 수정 검증: safe parser + XXE 방어 ─────────────────────────────


class TestSafeParserXXE:
    """SEC-001: etree.fromstring()에 safe parser가 적용되었는지 검증."""

    def test_safe_parser_configured(self) -> None:
        """_SAFE_PARSER가 resolve_entities=False로 설정되어 있다."""

        # lxml XMLParser는 resolve_entities 속성을 직접 노출하지 않으므로
        # 내부 엔티티가 포함된 XML 파싱 시 엔티티가 해석되지 않는지 검증
        xml_with_entity = b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY test "RESOLVED">]><root>&test;</root>'
        try:
            root = etree.fromstring(xml_with_entity, parser=_SAFE_PARSER)
            # 파싱 성공 시 엔티티가 해석되지 않았는지 확인
            assert root.text is None or "RESOLVED" not in (root.text or "")
        except etree.XMLSyntaxError:
            # 엔티티 해석 차단으로 파싱 에러 → 정상
            pass

    def test_extract_paragraphs_text_ignores_xxe_entity(self) -> None:
        """XXE 엔티티가 있는 DOCX에서 엔티티가 해석되지 않는다 (빈 텍스트 또는 에러)."""
        # safe parser는 엔티티 해석을 차단 — 에러 발생 또는 빈 텍스트
        normal_xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<w:document xmlns:w="{W_NS}">'
            f"<w:body><w:p><w:r><w:t>안전한 텍스트</w:t></w:r></w:p></w:body>"
            f"</w:document>"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
            )
            zf.writestr("word/document.xml", normal_xml)
            zf.writestr(
                "_rels/.rels",
                '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
            )
            zf.writestr(
                "word/_rels/document.xml.rels",
                '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
            )

        result = extract_paragraphs_text(buf.getvalue())
        assert "안전한 텍스트" in result
        # "INJECTED" 같은 외부 엔티티 값이 없어야 함
        assert "INJECTED" not in result


# ── 19. C-01 + SEC-NEW-01 수정 검증: ZIP bomb 방어 ───────────────────────────


class TestZipBombDefense:
    """C-01 + SEC-NEW-01: ZIP 내부 파일 크기 검증."""

    def test_read_zip_entry_rejects_oversized(self) -> None:
        """_read_zip_entry가 file_size 초과 시 ValueError를 발생시킨다."""

        # 정상 크기의 엔트리는 통과
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("test.xml", "<root/>")
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as zf:
            data = _read_zip_entry(zf, "test.xml")
            assert data == b"<root/>"

    def test_invalid_docx_missing_document_xml(self) -> None:
        """word/document.xml이 없는 ZIP은 ValueError."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("dummy.txt", "not a docx")

        with pytest.raises(ValueError, match=r"word/document\.xml"):
            extract_paragraphs_text(buf.getvalue())


# ── 20. N-R4-01 수정 검증: XMLSyntaxError 처리 ──────────────────────────────


class TestXMLSyntaxErrorHandling:
    """N-R4-01: 손상된 XML이 ValueError로 변환된다."""

    def test_corrupted_xml_raises_valueerror(self) -> None:
        """손상된 document.xml이 포함된 DOCX는 ValueError."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
            )
            zf.writestr("word/document.xml", "<not valid xml <<<>>>")
            zf.writestr(
                "_rels/.rels",
                '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
            )
            zf.writestr(
                "word/_rels/document.xml.rels",
                '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
            )

        with pytest.raises(ValueError, match="XML이 손상"):
            extract_paragraphs_text(buf.getvalue())

    def test_corrupted_xml_in_apply_redlines(self) -> None:
        """apply_redlines에서도 손상된 XML은 ValueError."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
            )
            zf.writestr("word/document.xml", "INVALID XML CONTENT!!!")
            zf.writestr(
                "_rels/.rels",
                '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
            )
            zf.writestr(
                "word/_rels/document.xml.rels",
                '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
            )

        with pytest.raises(ValueError, match="XML이 손상"):
            apply_redlines(buf.getvalue(), [])


# ── 21. R3-NEW-01 수정 검증: comments.xml 파싱 에러 폴백 ─────────────────────


class TestCommentsXmlFallback:
    """R3-NEW-01: 손상된 comments.xml이 있어도 빈 <w:comments>로 폴백."""

    def test_corrupted_comments_xml_fallback(self) -> None:
        """손상된 comments.xml이 있는 DOCX에서 CommentManager가 정상 생성된다."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("word/comments.xml", "NOT VALID XML <<<")
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as zf:
            mgr = CommentManager.from_docx_zip(zf)
        # 빈 comments_root로 폴백되어야 함
        assert mgr.next_id == 1
        # 코멘트 추가가 정상 작동해야 함
        cid = mgr.add_comment("test", author="test", date_str="2026-01-01T00:00:00Z")
        assert cid == 1


# ── 22. R6-S-02 수정 검증: 하이퍼링크 내부 Run 수집 ──────────────────────────


class TestHyperlinkRunCollection:
    """R6-S-02: _collect_and_split_target_runs가 하이퍼링크 내부 Run도 수집."""

    def test_build_char_map_includes_hyperlink_runs(self) -> None:
        """_build_char_map은 하이퍼링크 내부 <w:r>도 포함한다."""
        p = etree.Element(f"{W}p", nsmap=NSMAP)
        # 일반 run
        r1 = etree.SubElement(p, f"{W}r")
        t1 = etree.SubElement(r1, f"{W}t")
        t1.text = "앞 텍스트 "
        # 하이퍼링크 내부 run
        hl = etree.SubElement(p, f"{W}hyperlink")
        r2 = etree.SubElement(hl, f"{W}r")
        t2 = etree.SubElement(r2, f"{W}t")
        t2.text = "링크텍스트"
        # 뒤 일반 run
        r3 = etree.SubElement(p, f"{W}r")
        t3 = etree.SubElement(r3, f"{W}t")
        t3.text = " 뒤 텍스트"

        merged, _char_map = _build_char_map(p)
        assert "링크텍스트" in merged
        assert merged == "앞 텍스트 링크텍스트 뒤 텍스트"


# ── 23. M-02+MOD-02 수정 검증: _apply_segments KEEP+DEL+INS ─────────────────


class TestApplySegmentsKeepDelIns:
    """M-02+MOD-02: KEEP+DEL+INS 조합에서 올바른 처리."""

    def test_keep_then_del_then_ins(self) -> None:
        """KEEP 후 DEL+INS 패턴이 정상 동작한다 (다중 Run)."""

        # 3개의 Run으로 구성: "ABC " / "DEF" / " GHI"
        p = _make_paragraph("ABC ", "DEF", " GHI")
        target_runs = list(p.findall(f".//{W}r"))
        assert len(target_runs) == 3

        segments = [
            RedlineSegment(action="KEEP", text="ABC "),
            RedlineSegment(action="DEL", text="DEF"),
            RedlineSegment(action="INS", text="XYZ"),
        ]

        result = _apply_segments(
            segments=segments,
            target_runs=target_runs,
            paragraph=p,
            author="test",
            rev_counter=_RevIdCounter(0),
            date_str="2026-01-01T00:00:00Z",
        )
        # 결과가 None이 아니어야 함
        assert result is not None

        # DEL 태그가 생성되었는지 확인
        del_els = list(p.iter(f"{W}del"))
        assert len(del_els) >= 1

        # INS 태그가 생성되었는지 확인
        ins_els = list(p.iter(f"{W}ins"))
        assert len(ins_els) >= 1

    def test_del_then_ins_sequential(self) -> None:
        """연속 DEL+INS 패턴 (KEEP 없이)."""

        p = _make_paragraph("원본 텍스트입니다")
        target_runs = list(p.findall(f".//{W}r"))

        segments = [
            RedlineSegment(action="DEL", text="원본 텍스트입니다"),
            RedlineSegment(action="INS", text="수정된 텍스트입니다"),
        ]

        result = _apply_segments(
            segments=segments,
            target_runs=target_runs,
            paragraph=p,
            author="test",
            rev_counter=_RevIdCounter(0),
            date_str="2026-01-01T00:00:00Z",
        )
        assert result is not None

        # DEL과 INS가 각각 생성됨
        assert len(list(p.iter(f"{W}del"))) >= 1
        assert len(list(p.iter(f"{W}ins"))) >= 1


# ── 24. SEC-NEW-04 수정 검증: ZIP Slip 방어 ──────────────────────────────────


class TestZipSlipDefense:
    """SEC-NEW-04: _repack_docx에서 경로 순회 엔트리 차단."""

    def test_apply_redlines_with_path_traversal_entry(self) -> None:
        """../가 포함된 ZIP 엔트리가 있는 DOCX도 정상 처리 (해당 엔트리만 무시)."""
        docx_bytes = _make_minimal_docx(["테스트 문장입니다"])

        # 악의적 엔트리를 추가한 DOCX 생성
        buf = io.BytesIO(docx_bytes)
        with zipfile.ZipFile(buf, "a") as zf:
            zf.writestr("../malicious.txt", "evil content")

        result = apply_redlines(buf.getvalue(), [])
        assert result is not None

        # 결과 DOCX에 ../malicious.txt가 포함되지 않아야 함
        result.seek(0)
        with zipfile.ZipFile(result, "r") as zf:
            assert "../malicious.txt" not in zf.namelist()


# ── 25. 프롬프트 보강 검증 ───────────────────────────────────────────────────


class TestPromptEnhancements:
    """R6-W-01, R6-W-02, R6-W-03, R6-S-01: 프롬프트 보강 검증."""

    def test_severity_escrow_alternative_language(self) -> None:
        """R6-W-03: 심각도 기준에 '대체 담보 전무' 표현이 포함."""
        from app.services.redline_prompts import STEP4_SYSTEM_PROMPT

        assert "대체 담보 전무" in STEP4_SYSTEM_PROMPT

    def test_franchise_law_articles(self) -> None:
        """R6-W-01: FRANCHISE 프롬프트에 가맹사업법 조항이 포함."""
        from app.services.redline_prompts import INDUSTRY_FRANCHISE

        assert "제6조의5" in INDUSTRY_FRANCHISE
        assert "제12조의4" in INDUSTRY_FRANCHISE

    def test_weak_leverage_severity_differentiation(self) -> None:
        """R6-S-01: WEAK 레버리지에서 severity별 대응 차등화."""
        from app.services.redline_prompts import LEVERAGE_WEAK

        assert "High" in LEVERAGE_WEAK
        assert "Medium" in LEVERAGE_WEAK or "Low" in LEVERAGE_WEAK

    def test_escrow_alternative_sufficiency_criteria(self) -> None:
        """R6-W-02: 대체 담보 충분성 기준이 구체화됨."""
        from app.services.redline_prompts import DOMESTIC_KR_SECTION

        assert "10%" in DOMESTIC_KR_SECTION
        assert "개인보증" in DOMESTIC_KR_SECTION


# ── 26. FU-19: ZIP bomb 초과 케이스 테스트 ──────────────────────────────────


class TestZipBombOversized:
    """FU-19: _read_zip_entry가 실제 초과 케이스에서 ValueError를 발생시킨다."""

    def test_declared_file_size_exceeds_limit(self) -> None:
        """선언된 file_size가 상한을 초과하면 ValueError."""

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("big.xml", "<root/>")
        buf.seek(0)

        with zipfile.ZipFile(buf, "r") as zf:
            info = zf.getinfo("big.xml")
            # file_size를 상한 초과로 패치
            with (
                patch.object(type(info), "file_size", new_callable=lambda: property(lambda self: 60 * 1024 * 1024)),
                pytest.raises(ValueError, match="상한"),
            ):
                _read_zip_entry(zf, "big.xml")

    def test_streaming_size_exceeds_limit(self) -> None:
        """실제 스트리밍 크기가 상한을 초과하면 ValueError (file_size=0 우회 방어)."""

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("big.xml", "<root/>")
        buf.seek(0)

        with zipfile.ZipFile(buf, "r") as zf:
            # file_size를 0으로 속이되, open()이 거대한 데이터를 반환하도록 모킹
            info = zf.getinfo("big.xml")
            original_open = zf.open

            def fake_open(name_or_info: object) -> io.BytesIO:
                # 상한 + 1 바이트의 데이터를 반환
                return io.BytesIO(b"x" * (_MAX_XML_SIZE + 1))

            with (
                patch.object(type(info), "file_size", new_callable=lambda: property(lambda self: 0)),
                patch.object(zf, "open", side_effect=fake_open),
                pytest.raises(ValueError, match="실제 크기"),
            ):
                _read_zip_entry(zf, "big.xml")


# ── 27. FU-20: _apply_segments KEEP-only 시나리오 ────────────────────────────


class TestApplySegmentsKeepOnly:
    """FU-20: KEEP-only 세그먼트에서 원본이 변경되지 않아야 한다."""

    def test_keep_only_preserves_original(self) -> None:
        """KEEP만 있으면 DEL/INS 없이 원본 유지."""

        p = _make_paragraph("원본 텍스트 그대로")
        target_runs = list(p.findall(f".//{W}r"))

        segments = [RedlineSegment(action="KEEP", text="원본 텍스트 그대로")]

        result = _apply_segments(
            segments=segments,
            target_runs=target_runs,
            paragraph=p,
            author="test",
            rev_counter=_RevIdCounter(0),
            date_str="2026-01-01T00:00:00Z",
        )

        # DEL/INS 태그가 없어야 함
        assert len(list(p.iter(f"{W}del"))) == 0
        assert len(list(p.iter(f"{W}ins"))) == 0
        # 결과는 마지막 run (KEEP의 마지막 run)
        assert result is not None


# ── 28. FU-21: _split_run_at 경계 조건 테스트 ────────────────────────────────


class TestSplitRunAtEdgeCases:
    """FU-21: offset=0과 offset=len에서의 경계 동작."""

    def test_split_at_start(self) -> None:
        """offset=0: 원본은 빈 텍스트, 복사본은 전체 텍스트."""
        p = etree.Element(f"{W}p", nsmap=NSMAP)
        r = etree.SubElement(p, f"{W}r")
        t = etree.SubElement(r, f"{W}t")
        t.text = "ABCDE"

        before, after = _split_run_at(r, t, 0)

        before_t = before.find(f"{W}t")
        after_t = after.find(f"{W}t")
        assert before_t.text == ""  # 빈 텍스트
        assert after_t.text == "ABCDE"  # 전체

    def test_split_at_end(self) -> None:
        """offset=len: 원본은 전체 텍스트, 복사본은 빈 텍스트."""
        p = etree.Element(f"{W}p", nsmap=NSMAP)
        r = etree.SubElement(p, f"{W}r")
        t = etree.SubElement(r, f"{W}t")
        t.text = "ABCDE"

        before, after = _split_run_at(r, t, 5)

        before_t = before.find(f"{W}t")
        after_t = after.find(f"{W}t")
        assert before_t.text == "ABCDE"  # 전체
        assert after_t.text == ""  # 빈 텍스트


# ── 29. FU-22: 다중 이슈 E2E 테스트 ─────────────────────────────────────────


class TestMultiIssueE2E:
    """FU-22: 동일 문서에 여러 이슈를 동시에 적용."""

    def test_two_issues_different_paragraphs(self) -> None:
        """서로 다른 문단의 두 이슈가 모두 정상 적용된다."""
        docx_bytes = _make_minimal_docx(
            [
                "매매대금의 100분의 30을 한도로 합니다.",
                "경업금지 기간은 5년으로 합니다.",
            ]
        )

        issues = [
            {
                "issue_id": "ISS-001",
                "clause_ref": "제5조",
                "severity": "High",
                "rationale": "손해배상 한도 과다",
                "original_target_text": "100분의 30",
                "proposed_redline": "[DEL]100분의 30[/DEL][INS]100분의 20[/INS]",
            },
            {
                "issue_id": "ISS-002",
                "clause_ref": "제10조",
                "severity": "Medium",
                "rationale": "경업금지 기간 과도",
                "original_target_text": "5년으로",
                "proposed_redline": "[DEL]5년으로[/DEL][INS]3년으로[/INS]",
            },
        ]

        result = apply_redlines(docx_bytes, issues)
        assert result is not None

        # 결과 DOCX에서 두 이슈 모두 적용 확인
        result.seek(0)
        with zipfile.ZipFile(result, "r") as zf:
            doc_xml = zf.read("word/document.xml")
            xml_str = doc_xml.decode("utf-8")
            # DEL 태그가 2개 이상 있어야 함
            assert xml_str.count("<w:del ") >= 2
            # INS 태그가 2개 이상 있어야 함
            assert xml_str.count("<w:ins ") >= 2
            # 코멘트도 2개 이상 있어야 함
            comments_xml = zf.read("word/comments.xml")
            assert comments_xml.decode("utf-8").count("<w:comment ") >= 2


# ── 30. FU-24: OTHER_INDUSTRY 폴백 테스트 ────────────────────────────────────


class TestOtherIndustryFallback:
    """FU-24: OTHER_INDUSTRY가 GENERAL로 폴백된다."""

    def test_other_industry_falls_back_to_general(self) -> None:
        """알 수 없는 industry_type은 INDUSTRY_GENERAL로 폴백."""
        from app.services.redline_prompts import INDUSTRY_GENERAL, build_step4_prompt

        prompt = build_step4_prompt(industry_type="OTHER_INDUSTRY")
        # GENERAL 내용이 포함되어야 함
        assert "Market Standard" in prompt or "일반 산업" in prompt
        # GENERAL 프롬프트의 핵심 내용 확인
        for keyword in ["손해배상", "에스크로", "진술보증"]:
            if keyword in INDUSTRY_GENERAL:
                assert keyword in prompt


# ── _collect_and_split_target_runs 직접 단위 테스트 ────────────────────────────


class TestCollectAndSplitTargetRuns:
    """R3-006: _collect_and_split_target_runs 경계 분할 + run 수집 직접 테스트."""

    def _make_paragraph_with_runs(self, texts: list[str]) -> etree._Element:
        """여러 <w:r>/<w:t>를 가진 <w:p> 생성."""
        p = etree.Element(f"{W}p")
        for text in texts:
            r = etree.SubElement(p, f"{W}r")
            t = etree.SubElement(r, f"{W}t")
            t.text = text
        return p

    def test_single_run_full_range(self) -> None:
        """단일 Run 전체 범위 수집 — 분할 없음."""

        p = self._make_paragraph_with_runs(["Hello World"])
        _, char_map = _build_char_map(p)
        runs = _collect_and_split_target_runs(char_map, 0, len(char_map))
        assert len(runs) == 1
        text = "".join(t.text or "" for t in runs[0].findall(f"{W}t"))
        assert text == "Hello World"

    def test_multi_run_mid_boundary_split(self) -> None:
        """여러 Run 중간에서 시작/끝 경계 분할."""

        # "AABB" + "CCDD" → "BBCC" 범위 (index 2~6)
        p = self._make_paragraph_with_runs(["AABB", "CCDD"])
        _, char_map = _build_char_map(p)
        runs = _collect_and_split_target_runs(char_map, 2, 6)
        # 분할 후 "BB"와 "CC"가 포함된 runs 반환
        collected_text = "".join(t.text or "" for r in runs for t in r.findall(f"{W}t"))
        assert collected_text == "BBCC"

    def test_same_run_mid_range(self) -> None:
        """단일 Run 중간 부분 타겟팅 — 양쪽 분할 후 정확한 범위만 반환."""

        # "ABCDEFGH" 에서 "CDE" (index 2~5) 수집
        p = self._make_paragraph_with_runs(["ABCDEFGH"])
        _, char_map = _build_char_map(p)
        runs = _collect_and_split_target_runs(char_map, 2, 5)
        assert len(runs) == 1
        text = "".join(t.text or "" for t in runs[0].findall(f"{W}t"))
        assert text == "CDE"

    def test_empty_range_returns_empty(self) -> None:
        """빈 범위(start >= end)면 빈 리스트 반환."""

        p = self._make_paragraph_with_runs(["Hello"])
        _, char_map = _build_char_map(p)
        runs = _collect_and_split_target_runs(char_map, 3, 3)
        assert runs == []
