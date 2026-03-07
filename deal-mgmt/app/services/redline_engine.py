"""OOXML Redline Engine — Word Tracked Changes 주입 엔진.

SPA 교차 검증 결과를 원본 .docx에 <w:del>/<w:ins> + <w:comment>로
Tracked Changes 형태로 삽입한다.

핵심 난제: Run Fragmentation — 하나의 문장이 여러 <w:r> 노드로 파편화되어 있어
글자 단위 매핑(Character-to-Node Mapping) 알고리즘이 필요하다.
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime

from lxml import etree

logger = logging.getLogger(__name__)

# lxml safe parser — XXE 방어
_SAFE_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)

# ── OOXML 네임스페이스 상수 ───────────────────────────────────────────────────

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
XML_NS = "http://www.w3.org/XML/1998/namespace"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
COMMENTS_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"

NSMAP = {"w": W_NS}


# ── 핵심 데이터 구조 ─────────────────────────────────────────────────────────


@dataclass(slots=True)
class CharMapping:
    """병합 문자열의 한 글자 -> 원본 XML 노드 위치 매핑."""

    run_element: etree._Element
    text_element: etree._Element
    char_index: int  # <w:t> 텍스트 내 오프셋


@dataclass
class RedlineSegment:
    """[DEL]/[INS]/KEEP 파싱 결과."""

    action: str  # "DEL" | "INS" | "KEEP"
    text: str


@dataclass
class _RevIdCounter:
    """Revision ID 순차 발급 카운터 (뮤터블 래핑 대체)."""

    value: int

    def next(self) -> int:
        """다음 revision ID를 발급하고 카운터를 증가시킨다."""
        self.value += 1
        return self.value


@dataclass
class CommentManager:
    """word/comments.xml 관리 — 메모 생성 + 본문 앵커 삽입 총괄."""

    comments_root: etree._Element
    next_id: int = 1

    @classmethod
    def from_docx_zip(cls, zf: zipfile.ZipFile) -> CommentManager:
        """DOCX ZIP에서 word/comments.xml 로드. 없으면 빈 <w:comments> 생성."""
        try:
            comments_xml = zf.read("word/comments.xml")
            root = etree.fromstring(comments_xml, parser=_SAFE_PARSER)
        except (KeyError, etree.XMLSyntaxError):
            root = etree.Element(f"{W}comments", nsmap=NSMAP)

        # 기존 comment ID 최대값 스캔
        max_id = 0
        for comment in root.iter(f"{W}comment"):
            cid = comment.get(f"{W}id")
            if cid and cid.isdigit():
                max_id = max(max_id, int(cid))

        return cls(comments_root=root, next_id=max_id + 1)

    def add_comment(
        self,
        text: str,
        *,
        author: str,
        date_str: str,
    ) -> int:
        """<w:comment> 노드를 comments_root에 추가. 할당된 comment_id를 반환."""
        comment_id = self.next_id
        self.next_id += 1

        comment_el = etree.SubElement(self.comments_root, f"{W}comment")
        comment_el.set(f"{W}id", str(comment_id))
        comment_el.set(f"{W}author", author)
        comment_el.set(f"{W}date", date_str)

        # 텍스트를 줄바꿈 기준으로 여러 <w:p>로 분할
        lines = text.split("\n")
        for line in lines:
            p_el = etree.SubElement(comment_el, f"{W}p")
            r_el = etree.SubElement(p_el, f"{W}r")
            t_el = etree.SubElement(r_el, f"{W}t")
            t_el.set(f"{{{XML_NS}}}space", "preserve")
            t_el.text = line

        return comment_id

    def serialize(self) -> bytes:
        """comments_root -> XML bytes."""
        return etree.tostring(
            self.comments_root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        )


_MAX_XML_SIZE = 50 * 1024 * 1024  # 50MB — ZIP 내부 XML 압축 해제 상한


def _read_zip_entry(zf: zipfile.ZipFile, entry_name: str) -> bytes:
    """ZIP 엔트리를 읽되, 압축 해제 크기가 상한을 초과하면 ValueError를 발생시킨다."""
    info = zf.getinfo(entry_name)  # KeyError if not found
    # 1차: 선언된 크기 사전 체크 (Data Descriptor 방식에서 0일 수 있음)
    if info.file_size > _MAX_XML_SIZE:
        raise ValueError(
            f"ZIP 내부 파일 '{entry_name}' 크기({info.file_size:,} bytes)가 상한({_MAX_XML_SIZE:,} bytes)을 초과합니다."
        )
    # 2차: 실제 스트리밍 읽기로 크기 검증
    chunks: list[bytes] = []
    total = 0
    with zf.open(info) as fobj:
        while True:
            chunk = fobj.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_XML_SIZE:
                raise ValueError(
                    f"ZIP 내부 파일 '{entry_name}' 실제 크기가 상한({_MAX_XML_SIZE:,} bytes)을 초과합니다."
                )
            chunks.append(chunk)
    return b"".join(chunks)


# ── 공개 함수 ────────────────────────────────────────────────────────────────


def extract_paragraphs_text(docx_bytes: bytes) -> str:
    """DOCX bytes -> 전체 plain text (LLM 입력용)."""
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        try:
            xml_bytes = _read_zip_entry(zf, "word/document.xml")
        except KeyError as exc:
            raise ValueError("유효하지 않은 DOCX 파일입니다: word/document.xml이 없습니다.") from exc

    try:
        root = etree.fromstring(xml_bytes, parser=_SAFE_PARSER)
    except etree.XMLSyntaxError as exc:
        raise ValueError("DOCX 내부 XML이 손상되었습니다.") from exc

    paragraphs: list[str] = []

    for p in root.iter(f"{W}p"):
        texts: list[str] = []
        for t in p.iter(f"{W}t"):
            if t.text:
                # <w:del> 내부의 <w:delText>는 iter(f"{W}t")에 포함되지 않으므로 안전
                texts.append(t.text)
        if texts:
            paragraphs.append("".join(texts))

    return "\n".join(paragraphs)


def apply_redlines(
    docx_bytes: bytes,
    issues: list[dict],
    *,
    author: str = "AI Reviewer",
) -> io.BytesIO:
    """원본 DOCX에 Tracked Changes + Comment 적용 -> 새 DOCX BytesIO 반환."""
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        try:
            xml_bytes = _read_zip_entry(zf, "word/document.xml")
        except KeyError as exc:
            raise ValueError("유효하지 않은 DOCX 파일입니다: word/document.xml이 없습니다.") from exc

        # 1.5: Comment 매니저 초기화
        comment_mgr = CommentManager.from_docx_zip(zf)

    # 2: 문서 파싱
    try:
        root = etree.fromstring(xml_bytes, parser=_SAFE_PARSER)
    except etree.XMLSyntaxError as exc:
        raise ValueError("DOCX 내부 XML이 손상되었습니다.") from exc
    body = root.find(f"{W}body")
    if body is None:
        raise ValueError("유효하지 않은 DOCX 파일입니다: <w:body>가 없습니다.")

    # 3: 모든 <w:p> 수집 (본문 + 표 내부)
    all_paragraphs = list(body.iter(f"{W}p"))

    # 3.5: 기존 revision ID 최대값 스캔
    rev_counter = _RevIdCounter(_scan_max_revision_id(root))
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 4: 각 issue 처리 (개별 이슈 예외 시 skip — R4-C4)
    first_paragraph = all_paragraphs[0] if all_paragraphs else None
    for issue in issues:
        try:
            _apply_single_issue(
                issue=issue,
                all_paragraphs=all_paragraphs,
                first_paragraph=first_paragraph,
                comment_mgr=comment_mgr,
                rev_counter=rev_counter,
                author=author,
                date_str=date_str,
            )
        except Exception:
            issue_id = issue.get("issue_id", "ISS-000")
            clause_ref_log = issue.get("clause_ref", "N/A")
            severity_log = issue.get("severity", "N/A")
            logger.exception(
                "이슈 처리 중 예외 발생, skip: issue=%s, clause=%s, severity=%s",
                issue_id,
                clause_ref_log,
                severity_log,
            )
            # 매칭 실패 메모 삽입
            if first_paragraph is not None:
                clause_ref = issue.get("clause_ref", "")
                rationale = issue.get("rationale", "")
                fail_text = f"[처리 실패] {issue_id} — {clause_ref}\n수동 검토 요망.\n{rationale}"
                cid = comment_mgr.add_comment(fail_text, author=author, date_str=date_str)
                first_run = first_paragraph.find(f".//{W}r")
                if first_run is not None:
                    _anchor_comment_to_run(first_run, cid)

    # 5: 직렬화
    modified_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    # 5.5: Comments XML 직렬화
    comments_xml = comment_mgr.serialize()

    # 6: ZIP 재패키징
    return _repack_docx(docx_bytes, modified_xml, comments_xml=comments_xml)


def _apply_single_issue(
    *,
    issue: dict,
    all_paragraphs: list[etree._Element],
    first_paragraph: etree._Element | None,
    comment_mgr: CommentManager,
    rev_counter: _RevIdCounter,
    author: str,
    date_str: str,
) -> None:
    """단일 이슈를 문서에 적용한다. 실패 시 예외를 raise한다."""
    original_target = issue.get("original_target_text", "")
    proposed_redline = issue.get("proposed_redline", "")
    rationale = issue.get("rationale", "")
    severity = issue.get("severity", "Medium")
    clause_ref = issue.get("clause_ref", "")
    issue_id = issue.get("issue_id", "ISS-000")

    # 4a: 레드라인 마크업 파싱
    segments = _parse_redline_markup(proposed_redline)
    if not segments:
        logger.warning("빈 세그먼트: issue=%s, skip", issue_id)
        return

    # 4b: 타겟 텍스트 검색
    match = _find_target_in_paragraphs(all_paragraphs, original_target)
    if match is None:
        # 4c: 매칭 실패 -> 문서 최상단에 실패 메모 삽입
        logger.warning("매칭 실패: issue=%s, target='%s...'", issue_id, original_target[:50])
        if first_paragraph is not None:
            fail_text = f"[매칭 실패] {issue_id} — {clause_ref}\n수동 검토 요망.\n{rationale}"
            cid = comment_mgr.add_comment(fail_text, author=author, date_str=date_str)
            first_run = first_paragraph.find(f".//{W}r")
            if first_run is not None:
                _anchor_comment_to_run(first_run, cid)
        return

    paragraph, start_idx, end_idx, _merged_text, char_map = match

    # 4d~4e: Run 경계 분할 및 대상 Run 수집
    target_runs = _collect_and_split_target_runs(char_map, start_idx, end_idx)
    if not target_runs:
        logger.warning("Run 수집 실패: issue=%s, skip", issue_id)
        return

    # 4f: segments 순서대로 처리
    last_processed_run = _apply_segments(
        segments=segments,
        target_runs=target_runs,
        paragraph=paragraph,
        author=author,
        rev_counter=rev_counter,
        date_str=date_str,
    )

    # 4g: Rationale 메모 삽입
    anchor_run = last_processed_run if last_processed_run is not None else (target_runs[-1] if target_runs else None)
    if anchor_run is not None:
        comment_text = f"[{severity}] {clause_ref}\n{rationale}"
        cid = comment_mgr.add_comment(comment_text, author=author, date_str=date_str)
        _anchor_comment_to_run(anchor_run, cid)


# ── 1단계: Character-to-Node Mapping ─────────────────────────────────────────


def _build_char_map(paragraph: etree._Element) -> tuple[str, list[CharMapping]]:
    """문단의 모든 <w:r>/<w:t> 순회 -> 병합 문자열 + 글자별 매핑 리스트.

    기존 Tracked Changes 처리 정책:
    - <w:del> 내부의 <w:r>/<w:delText> -> 무시 (이미 삭제된 텍스트)
    - <w:ins> 내부의 <w:r>/<w:t> -> 포함 (수락 시 보이는 텍스트)
    """
    merged_chars: list[str] = []
    char_maps: list[CharMapping] = []

    # <w:del> 태그 내부의 run 노드 집합을 사전 수집
    del_runs: set[int] = set()
    for del_el in paragraph.iter(f"{W}del"):
        for r in del_el.iter(f"{W}r"):
            del_runs.add(id(r))

    # 모든 <w:r> 순회 (하이퍼링크 내부 포함)
    for run in paragraph.iter(f"{W}r"):
        if id(run) in del_runs:
            continue  # 삭제된 텍스트 무시

        for t_elem in run.findall(f"{W}t"):
            text = t_elem.text or ""
            for i, ch in enumerate(text):
                merged_chars.append(ch)
                char_maps.append(CharMapping(run_element=run, text_element=t_elem, char_index=i))

    return "".join(merged_chars), char_maps


# ── 2단계: Boundary Splitting ────────────────────────────────────────────────


def _normalize_text_for_matching(text: str) -> str:
    """텍스트 매칭 전 정규화 전처리."""
    normalized, _ = _normalize_with_index_map(text)
    return normalized


def _normalize_with_index_map(text: str) -> tuple[str, list[int]]:
    """텍스트를 정규화하면서 정규화→원본 인덱스 매핑을 생성한다.

    반환: (정규화된 문자열, [정규화 문자열의 각 위치에 대응하는 원본 인덱스])
    """
    # 1. 유니코드 정규화 + 문자 치환 (길이 불변 치환)
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "-",
        "\u2013": "-",
    }
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch in replacements:
            chars[i] = replacements[ch]
    text = "".join(chars)

    # 2. 연속 공백 축소 + 인덱스 매핑
    norm_chars: list[str] = []
    norm_to_orig: list[int] = []
    prev_was_space = False
    for i, ch in enumerate(text):
        if ch in (" ", "\t", "\n", "\r"):
            if not prev_was_space:
                norm_chars.append(" ")
                norm_to_orig.append(i)
                prev_was_space = True
            # 연속 공백은 건너뜀 (매핑 없음)
        else:
            norm_chars.append(ch)
            norm_to_orig.append(i)
            prev_was_space = False

    return "".join(norm_chars), norm_to_orig


def _find_target_in_paragraphs(
    paragraphs: list[etree._Element],
    target_text: str,
) -> tuple[etree._Element, int, int, str, list[CharMapping]] | None:
    """모든 문단에서 target_text를 검색."""
    norm_target = _normalize_text_for_matching(target_text)

    for para in paragraphs:
        merged, char_map = _build_char_map(para)
        if not merged:
            continue

        # 정확 매칭
        idx = merged.find(target_text)
        if idx >= 0:
            return para, idx, idx + len(target_text), merged, char_map

        # 정규화 매칭 (인덱스 매핑 테이블 사용)
        norm_merged, norm_to_orig = _normalize_with_index_map(merged)
        idx = norm_merged.find(norm_target)
        if idx >= 0:
            orig_start = norm_to_orig[idx]
            end_norm = idx + len(norm_target) - 1
            orig_end = norm_to_orig[end_norm] + 1 if end_norm < len(norm_to_orig) else len(merged)
            return para, orig_start, orig_end, merged, char_map

    return None


def _split_run_at(
    run: etree._Element,
    text_elem: etree._Element,
    split_offset: int,
) -> tuple[etree._Element, etree._Element]:
    """<w:r> 노드를 split_offset 위치에서 두 개로 분할."""
    parent = run.getparent()
    if parent is None:
        raise ValueError("Run에 부모 노드가 없습니다.")

    run_after = deepcopy(run)

    # 원본 run의 텍스트를 [:split_offset]로 자름
    original_text = text_elem.text or ""
    text_elem.text = original_text[:split_offset]
    text_elem.set(f"{{{XML_NS}}}space", "preserve")

    # 복사본의 텍스트를 [split_offset:]로 자름 — 인덱스 기반 접근
    t_elems_orig = run.findall(f"{W}t")
    t_index = -1
    for idx, t in enumerate(t_elems_orig):
        if t is text_elem:
            t_index = idx
            break
    after_t_elems = run_after.findall(f"{W}t")
    if t_index >= 0 and t_index < len(after_t_elems):
        after_t_elems[t_index].text = original_text[split_offset:]
        after_t_elems[t_index].set(f"{{{XML_NS}}}space", "preserve")

    # run 바로 뒤에 삽입
    run.addnext(run_after)

    return run, run_after


def _collect_and_split_target_runs(
    char_map: list[CharMapping],
    start_idx: int,
    end_idx: int,
) -> list[etree._Element]:
    """char_map에서 start_idx~end_idx 범위의 run을 수집하고, 필요 시 경계 분할."""
    if not char_map or start_idx >= end_idx:
        return []

    # 안전 범위 클리핑
    start_idx = max(0, min(start_idx, len(char_map) - 1))
    end_idx = max(1, min(end_idx, len(char_map)))

    start_mapping = char_map[start_idx]
    end_mapping = char_map[end_idx - 1]

    # 같은 run 내 부분 타겟팅: stale 참조 방지를 위해 끝 → 시작 순서로 분할
    if start_mapping.run_element is end_mapping.run_element:
        run = start_mapping.run_element
        t_elem = start_mapping.text_element
        full_text = t_elem.text or ""
        s_off = start_mapping.char_index
        e_off = end_mapping.char_index + 1

        # 끝 경계 먼저 분할 (start offset 유효성 보존)
        if e_off < len(full_text):
            before, _ = _split_run_at(run, t_elem, e_off)
            run = before
        # 시작 경계 분할
        if s_off > 0:
            _, after = _split_run_at(run, t_elem, s_off)
            return [after]
        return [run]

    # 시작 경계가 Run 중간이면 분할
    if start_mapping.char_index > 0:
        _, after = _split_run_at(start_mapping.run_element, start_mapping.text_element, start_mapping.char_index)
        start_run = after
    else:
        start_run = start_mapping.run_element

    # 끝 경계가 Run 중간이면 분할
    end_text = end_mapping.text_element.text or ""
    if end_mapping.char_index < len(end_text) - 1:
        before, _ = _split_run_at(end_mapping.run_element, end_mapping.text_element, end_mapping.char_index + 1)
        end_run = before
    else:
        end_run = end_mapping.run_element

    # start_run ~ end_run 사이의 모든 <w:r> 수집 (하이퍼링크 내부 포함)
    # 하이퍼링크 등 컨테이너 내부인 경우 문단(<w:p>)까지 올라감
    parent = start_run.getparent()
    while parent is not None and parent.tag != f"{W}p":
        parent = parent.getparent()
    if parent is None:
        return [start_run]

    runs: list[etree._Element] = []
    collecting = False
    found_end = False
    for child in parent:
        # 하이퍼링크 등 컨테이너 내부의 <w:r>도 탐색
        child_runs = [child] if child.tag == f"{W}r" else list(child.iter(f"{W}r"))
        for r in child_runs:
            if r is start_run:
                collecting = True
            if collecting and r.tag == f"{W}r":
                runs.append(r)
            if r is end_run:
                found_end = True
                break
        if found_end:
            break

    return runs if runs else [start_run]


# ── 3단계: Tag Injection ─────────────────────────────────────────────────────


def _inject_deletion(
    runs: list[etree._Element],
    *,
    author: str,
    revision_id: int,
    date_str: str,
) -> etree._Element:
    """대상 <w:r> 노드들을 <w:del> 태그로 감싼다."""
    if not runs:
        raise ValueError("삭제 대상 Run이 없습니다.")

    # <w:ins> 내부 run 필터링: 기존 삽입 태그 내 run을 DEL로 감싸면 문서 손상
    safe_runs: list[etree._Element] = []
    for run in runs:
        run_parent = run.getparent()
        if run_parent is not None and run_parent.tag == f"{W}ins":
            logger.warning("기존 <w:ins> 내부 run에 DEL 적용 시도 — skip (문서 손상 방지)")
            continue
        safe_runs.append(run)

    if not safe_runs:
        raise ValueError("삭제 대상 Run이 없습니다 (모두 <w:ins> 내부).")

    parent = safe_runs[0].getparent()
    if parent is None:
        raise ValueError("Run에 부모 노드가 없습니다.")

    # <w:del> 생성
    del_el = etree.Element(f"{W}del")
    del_el.set(f"{W}id", str(revision_id))
    del_el.set(f"{W}author", author)
    del_el.set(f"{W}date", date_str)

    # 첫 번째 run 위치에 <w:del> 삽입
    safe_runs[0].addprevious(del_el)

    for run in safe_runs:
        parent.remove(run)
        # <w:t> -> <w:delText> 변경
        for t in run.findall(f"{W}t"):
            t.tag = f"{W}delText"
            t.set(f"{{{XML_NS}}}space", "preserve")
        del_el.append(run)

    return del_el


def _inject_insertion(
    text: str,
    reference_run: etree._Element,
    paragraph: etree._Element,
    *,
    author: str,
    revision_id: int,
    date_str: str,
) -> etree._Element:
    """[INS] 텍스트를 <w:ins> 태그로 생성."""
    parent = reference_run.getparent()
    if parent is None:
        raise ValueError("Run에 부모 노드가 없습니다.")

    # <w:ins> 생성
    ins_el = etree.Element(f"{W}ins")
    ins_el.set(f"{W}id", str(revision_id))
    ins_el.set(f"{W}author", author)
    ins_el.set(f"{W}date", date_str)

    # 새 <w:r> 생성
    new_run = etree.SubElement(ins_el, f"{W}r")

    # rPr 복제 (폴백 포함)
    rPr = _resolve_run_properties(reference_run, paragraph)
    if rPr is not None:
        new_run.insert(0, rPr)

    # 텍스트 내 줄바꿈 처리: \n -> <w:br/>
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            etree.SubElement(new_run, f"{W}br")
        t_el = etree.SubElement(new_run, f"{W}t")
        t_el.set(f"{{{XML_NS}}}space", "preserve")
        t_el.text = line

    # reference_run 직후에 삽입
    reference_run.addnext(ins_el)

    return ins_el


def _parse_redline_markup(proposed_redline: str) -> list[RedlineSegment]:
    """정규식으로 [DEL]...[/DEL], [INS]...[/INS] 파싱."""
    segments: list[RedlineSegment] = []
    pattern = re.compile(r"\[DEL\](.*?)\[/DEL\]|\[INS\](.*?)\[/INS\]", re.DOTALL)

    last_end = 0
    for m in pattern.finditer(proposed_redline):
        # KEEP: 태그 사이의 텍스트
        if m.start() > last_end:
            keep_text = proposed_redline[last_end : m.start()]
            if keep_text:
                segments.append(RedlineSegment(action="KEEP", text=keep_text))

        if m.group(1) is not None:
            segments.append(RedlineSegment(action="DEL", text=m.group(1)))
        elif m.group(2) is not None:
            segments.append(RedlineSegment(action="INS", text=m.group(2)))

        last_end = m.end()

    # 마지막 KEEP
    if last_end < len(proposed_redline):
        tail = proposed_redline[last_end:]
        if tail:
            segments.append(RedlineSegment(action="KEEP", text=tail))

    return segments


# ── 3.5단계: Comment 앵커 ────────────────────────────────────────────────────


def _anchor_comment_to_run(
    run_element: etree._Element,
    comment_id: int,
) -> None:
    """본문의 <w:r> 노드에 메모 앵커를 삽입."""
    parent = run_element.getparent()
    if parent is None:
        return

    # <w:commentRangeStart> (run 앞)
    range_start = etree.Element(f"{W}commentRangeStart")
    range_start.set(f"{W}id", str(comment_id))
    run_element.addprevious(range_start)

    # <w:commentRangeEnd> (run 뒤)
    range_end = etree.Element(f"{W}commentRangeEnd")
    range_end.set(f"{W}id", str(comment_id))
    run_element.addnext(range_end)

    # <w:r><w:commentReference> (range_end 뒤)
    ref_run = etree.Element(f"{W}r")
    ref_el = etree.SubElement(ref_run, f"{W}commentReference")
    ref_el.set(f"{W}id", str(comment_id))
    range_end.addnext(ref_run)


# ── 4단계: Edge Case Handling + 보조 함수 ────────────────────────────────────


def _resolve_run_properties(
    run: etree._Element,
    paragraph: etree._Element,
) -> etree._Element | None:
    """<w:rPr> 복제 대상을 결정하는 폴백 로직."""
    # 1차: run 자체
    rPr = run.find(f"{W}rPr")
    if rPr is not None:
        return deepcopy(rPr)

    # 2차: 같은 문단 내 인접 run
    for sibling in paragraph.iter(f"{W}r"):
        sibling_rPr = sibling.find(f"{W}rPr")
        if sibling_rPr is not None:
            return deepcopy(sibling_rPr)

    # 3차: 문단 pPr 내 rPr
    pPr = paragraph.find(f"{W}pPr")
    if pPr is not None:
        pPr_rPr = pPr.find(f"{W}rPr")
        if pPr_rPr is not None:
            return deepcopy(pPr_rPr)

    # 4차: 없음
    return None


def _scan_max_revision_id(root: etree._Element) -> int:
    """문서 전체에서 기존 Tracked Changes의 최대 w:id를 추출 (단일 패스)."""
    max_id = 0
    revision_tags = {f"{W}ins", f"{W}del", f"{W}pPrChange", f"{W}rPrChange", f"{W}sectPrChange"}

    for el in root.iter():
        if el.tag in revision_tags:
            rid = el.get(f"{W}id")
            if rid and rid.isdigit():
                max_id = max(max_id, int(rid))

    return max_id


def _consume_runs_for_keep(
    remaining_runs: list[etree._Element],
    keep_len: int,
) -> tuple[etree._Element | None, list[etree._Element]]:
    """KEEP 텍스트 길이만큼 run을 소비한다. 경계가 run 중간이면 분할한다.

    반환: (마지막 KEEP run, 남은 runs)
    """
    consumed = 0
    last_keep_run: etree._Element | None = None

    for i, run in enumerate(remaining_runs):
        run_text = "".join(t.text or "" for t in run.findall(f"{W}t"))
        run_len = len(run_text)

        if consumed + run_len <= keep_len:
            # run 전체가 KEEP 범위 내
            consumed += run_len
            last_keep_run = run
            if consumed == keep_len:
                return last_keep_run, remaining_runs[i + 1 :]
        else:
            # run 중간에서 KEEP 경계 → 분할 (R4-C1)
            split_offset = keep_len - consumed
            t_elems = run.findall(f"{W}t")
            if t_elems and split_offset > 0:
                before, after = _split_run_at(run, t_elems[0], split_offset)
                last_keep_run = before
                return last_keep_run, [after, *remaining_runs[i + 1 :]]
            # split_offset == 0이면 이 run은 KEEP에 포함되지 않음
            return last_keep_run, remaining_runs[i:]

    return last_keep_run, []


def _inject_phantom_deletion(
    text: str,
    reference: etree._Element,
    paragraph: etree._Element,
    *,
    author: str,
    revision_id: int,
    date_str: str,
) -> etree._Element:
    """다중 DEL 세그먼트에서 remaining_runs 소진 후, 텍스트 기반 <w:del>을 삽입한다."""
    parent = reference.getparent()
    if parent is None:
        parent = paragraph

    del_el = etree.Element(f"{W}del")
    del_el.set(f"{W}id", str(revision_id))
    del_el.set(f"{W}author", author)
    del_el.set(f"{W}date", date_str)

    new_run = etree.SubElement(del_el, f"{W}r")
    # reference_run의 rPr 복제
    rPr = _resolve_run_properties(reference, paragraph)
    if rPr is not None:
        new_run.insert(0, rPr)

    del_text = etree.SubElement(new_run, f"{W}delText")
    del_text.set(f"{{{XML_NS}}}space", "preserve")
    del_text.text = text

    reference.addnext(del_el)
    return del_el


def _apply_segments(
    *,
    segments: list[RedlineSegment],
    target_runs: list[etree._Element],
    paragraph: etree._Element,
    author: str,
    rev_counter: _RevIdCounter,
    date_str: str,
) -> etree._Element | None:
    """세그먼트들을 적용하여 DEL/INS/KEEP 처리. 마지막 처리된 run을 반환."""
    last_run: etree._Element | None = None
    remaining_runs = list(target_runs)  # 복사본으로 작업

    for seg in segments:
        if seg.action == "DEL":
            if remaining_runs:
                del_el = _inject_deletion(
                    remaining_runs,
                    author=author,
                    revision_id=rev_counter.next(),
                    date_str=date_str,
                )
                last_run = del_el
                remaining_runs = []  # 삭제된 runs는 더 이상 사용 불가
            elif last_run is not None:
                # 다중 DEL: remaining_runs 소진 후 텍스트 기반 삭제 삽입 (R4-W2)
                del_el = _inject_phantom_deletion(
                    seg.text,
                    last_run,
                    paragraph,
                    author=author,
                    revision_id=rev_counter.next(),
                    date_str=date_str,
                )
                last_run = del_el
            else:
                logger.warning(
                    "DEL 세그먼트에 대응할 run 없음: text='%s...'",
                    seg.text[:30],
                )

        elif seg.action == "INS":
            ref = last_run if last_run is not None else (remaining_runs[-1] if remaining_runs else None)
            if ref is None:
                logger.warning("INS 삽입 기준 run이 없습니다. skip")
                continue
            ins_el = _inject_insertion(
                seg.text,
                ref,
                paragraph,
                author=author,
                revision_id=rev_counter.next(),
                date_str=date_str,
            )
            last_run = ins_el

        elif seg.action == "KEEP" and remaining_runs:
            # KEEP 텍스트 길이만큼 run 소비 + 경계 분할 (R4-C1)
            keep_run, remaining_runs = _consume_runs_for_keep(remaining_runs, len(seg.text))
            if keep_run is not None:
                last_run = keep_run

    return last_run


# ── ZIP 재패키징 ─────────────────────────────────────────────────────────────


def _repack_docx(
    original_bytes: bytes,
    modified_xml: bytes,
    *,
    comments_xml: bytes | None = None,
) -> io.BytesIO:
    """원본 DOCX ZIP에서 word/document.xml 교체 + word/comments.xml 추가/교체."""
    output = io.BytesIO()

    with (
        zipfile.ZipFile(io.BytesIO(original_bytes), "r") as zf_in,
        zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf_out,
    ):
        skip_files = {"word/document.xml"}
        if comments_xml is not None:
            skip_files.add("word/comments.xml")

        for item in zf_in.infolist():
            # ZIP Slip 방어: 경로 순회 차단
            if ".." in item.filename or item.filename.startswith("/"):
                logger.warning("ZIP Slip 의심 엔트리 무시: %s", item.filename)
                continue
            if item.filename in skip_files:
                continue

            if item.filename == "word/_rels/document.xml.rels" and comments_xml is not None:
                # 관계 파일에 comments 관계 추가 (없는 경우)
                rels_data = _read_zip_entry(zf_in, item.filename)
                rels_data = _ensure_comments_relationship(rels_data)
                zf_out.writestr(item, rels_data)
            elif item.filename == "[Content_Types].xml" and comments_xml is not None:
                ct_data = _read_zip_entry(zf_in, item.filename)
                ct_data = _ensure_comments_content_type(ct_data)
                zf_out.writestr(item, ct_data)
            else:
                # ZIP Bomb 방어: 개별 엔트리 크기 제한
                if item.file_size > _MAX_XML_SIZE:
                    logger.warning(
                        "ZIP 엔트리 크기 초과 무시: %s (%s bytes)",
                        item.filename,
                        item.file_size,
                    )
                    continue
                zf_out.writestr(item, _read_zip_entry(zf_in, item.filename))

        # .rels 파일이 ZIP에 없었으나 comments_xml이 필요한 경우 → 폴백 생성
        if comments_xml is not None:
            rels_exists = any(item.filename == "word/_rels/document.xml.rels" for item in zf_in.infolist())
            if not rels_exists:
                rels_fallback = _create_default_rels_with_comments()
                zf_out.writestr("word/_rels/document.xml.rels", rels_fallback)

        # 수정된 document.xml 쓰기
        zf_out.writestr("word/document.xml", modified_xml)

        # comments.xml 쓰기
        if comments_xml is not None:
            zf_out.writestr("word/comments.xml", comments_xml)

    output.seek(0)
    return output


def _create_default_rels_with_comments() -> bytes:
    """word/_rels/document.xml.rels가 ZIP에 없을 때 기본 관계 + comments 관계 생성."""
    ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    root = etree.Element(f"{{{ns}}}Relationships")
    # document.xml → styles.xml 기본 관계
    r1 = etree.SubElement(root, f"{{{ns}}}Relationship")
    r1.set("Id", "rId1")
    r1.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles")
    r1.set("Target", "styles.xml")
    # comments.xml 관계
    r2 = etree.SubElement(root, f"{{{ns}}}Relationship")
    r2.set("Id", "rId2")
    r2.set("Type", COMMENTS_REL_TYPE)
    r2.set("Target", "comments.xml")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _ensure_comments_relationship(rels_data: bytes) -> bytes:
    """document.xml.rels에 comments 관계가 없으면 추가."""
    root = etree.fromstring(rels_data, parser=_SAFE_PARSER)
    ns = "http://schemas.openxmlformats.org/package/2006/relationships"

    # 이미 있는지 확인
    for rel in root:
        rel_type = rel.get("Type", "")
        if rel_type == COMMENTS_REL_TYPE:
            return rels_data  # 이미 존재

    # 새 관계 추가
    # 고유 rId 생성
    existing_ids = {rel.get("Id", "") for rel in root}
    rid = 1
    while f"rId{rid}" in existing_ids:
        rid += 1

    new_rel = etree.SubElement(root, f"{{{ns}}}Relationship")
    new_rel.set("Id", f"rId{rid}")
    new_rel.set("Type", COMMENTS_REL_TYPE)
    new_rel.set("Target", "comments.xml")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _ensure_comments_content_type(ct_data: bytes) -> bytes:
    """[Content_Types].xml에 comments.xml ContentType이 없으면 추가."""
    root = etree.fromstring(ct_data, parser=_SAFE_PARSER)
    ns = CT_NS

    # 이미 있는지 확인
    for override in root:
        part_name = override.get("PartName", "")
        if part_name == "/word/comments.xml":
            return ct_data  # 이미 존재

    # 추가
    new_override = etree.SubElement(root, f"{{{ns}}}Override")
    new_override.set("PartName", "/word/comments.xml")
    new_override.set("ContentType", COMMENTS_CT)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
