"""
샘플 체결본 .docx 파일 서식 분석 스크립트

각 타입별 체결본의 단락 구조, 폰트, 스타일, 번호 매기기 패턴을 추출하여
convert_sample_to_template.py 작성의 기초 자료로 활용한다.

사용법:
    python scripts/analyze_sample_templates.py
    python scripts/analyze_sample_templates.py --type spa --verbose
"""

import argparse
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.oxml.ns import qn
except ImportError:
    print("python-docx 설치 필요: pip install python-docx")
    sys.exit(1)

# OneDrive 샘플 파일 경로
ONEDRIVE = Path(
    "C:/Users/서지원/OneDrive - 주식회사 페트라브릿지파트너스"
    "/AMIC의 파일 - 1. AMIC/5. 기업 인수&합병/98_References/Contracts"
)

SAMPLE_FILES = {
    "spa": ONEDRIVE / "spa" / "Project_Tempus_주식매매계약_체결본.docx",
    "sha": ONEDRIVE / "sha" / "M&A" / "Project_Tempus_주주간계약_체결본.docx",
    "ssa": ONEDRIVE / "ssa" / "M&A" / "Project_Tempus_신주인수계약_체결본.docx",
    "mou": ONEDRIVE / "mou" / "Pjt Jade_MOU_20250820_최종본.docx",
    # BTA: PDF밖에 없음 → 분석 불가
}

# 보조 SPA 파일들 (구조 비교용)
EXTRA_SPA = [
    ONEDRIVE / "spa" / "Project Ignite_SPA_SK_241108_체결본 (3) (1).docx",
    ONEDRIVE / "spa" / "Wolf 주식매매계약서 (250318) - Execution (별지포함).DOCX",
]


def get_font_name(run):
    """Run의 폰트명 추출 (한글 폰트 우선)"""
    if run.font.name:
        return run.font.name
    # XML에서 직접 추출
    rFonts = run._element.find(qn("w:rPr") + "/" + qn("w:rFonts"))
    if rFonts is not None:
        eastAsia = rFonts.get(qn("w:eastAsia"))
        ascii_font = rFonts.get(qn("w:ascii"))
        return eastAsia or ascii_font or "Unknown"
    return "Unknown"


def get_numbering_info(paragraph):
    """단락의 번호 매기기 정보 추출"""
    pPr = paragraph._element.find(qn("w:pPr"))
    if pPr is None:
        return None
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        return None
    ilvl = numPr.find(qn("w:ilvl"))
    numId = numPr.find(qn("w:numId"))
    level = int(ilvl.get(qn("w:val"))) if ilvl is not None else 0
    num_id = int(numId.get(qn("w:val"))) if numId is not None else 0
    return {"level": level, "numId": num_id}


def analyze_paragraph(para, idx, verbose=False):
    """단락 분석 후 딕셔너리 반환"""
    text = para.text.strip()
    style_name = para.style.name if para.style else "Normal"

    # 폰트 정보 (첫 번째 Run 기준)
    font_name = "N/A"
    font_size = "N/A"
    bold = False
    if para.runs:
        r = para.runs[0]
        font_name = get_font_name(r)
        font_size = str(r.font.size.pt) if r.font.size else "N/A"
        bold = r.bold or False

    # 들여쓰기
    pf = para.paragraph_format
    indent_left = pf.left_indent.cm if pf.left_indent else 0.0
    indent_first = pf.first_line_indent.cm if pf.first_line_indent else 0.0

    # 번호 매기기
    numbering = get_numbering_info(para)

    info = {
        "idx": idx,
        "style": style_name,
        "text_preview": text[:80] + ("..." if len(text) > 80 else ""),
        "font": font_name,
        "size_pt": font_size,
        "bold": bold,
        "indent_left_cm": round(indent_left, 2),
        "indent_first_cm": round(indent_first, 2),
        "numbering": numbering,
        "alignment": str(pf.alignment) if pf.alignment else "None",
    }
    return info


def analyze_table(table, table_idx):
    """테이블 구조 요약"""
    rows = len(table.rows)
    cols = len(table.columns) if table.rows else 0
    sample_cells = []
    for r_idx, row in enumerate(table.rows[:3]):  # 처음 3행만
        for c_idx, cell in enumerate(row.cells[:3]):  # 처음 3열만
            text = cell.text.strip()[:40]
            sample_cells.append(f"[{r_idx},{c_idx}]={text!r}")
    return {
        "table_idx": table_idx,
        "rows": rows,
        "cols": cols,
        "sample": ", ".join(sample_cells),
    }


def print_analysis(doc_path: Path, doc_type: str, verbose: bool = False, max_paras: int = 60):
    """문서 전체 분석 출력"""
    print(f"\n{'=' * 70}")
    print(f"  [{doc_type.upper()}] {doc_path.name}")
    print(f"{'=' * 70}")

    if not doc_path.exists():
        print(f"  ⚠️  파일 없음: {doc_path}")
        return

    doc = Document(str(doc_path))

    # ── 단락 분석 ──────────────────────────────────────────────
    print(f"\n[단락 분석] 총 {len(doc.paragraphs)}개 단락 (상위 {max_paras}개 출력)")
    print(f"{'idx':>4}  {'Style':<25} {'Font':<15} {'Sz':>5} {'B':>2} {'Li':>5} {'Fi':>5}  Text")
    print("-" * 100)

    font_counter: dict[str, int] = {}
    style_counter: dict[str, int] = {}

    for i, para in enumerate(doc.paragraphs[:max_paras]):
        info = analyze_paragraph(para, i, verbose)
        numbering_str = f"L{info['numbering']['level']}" if info["numbering"] else "   "
        print(
            f"{info['idx']:>4}  {info['style']:<25} {info['font']:<15} "
            f"{info['size_pt']:>5} {'B' if info['bold'] else ' ':>2} "
            f"{info['indent_left_cm']:>5.2f} {info['indent_first_cm']:>5.2f}  "
            f"{numbering_str}  {info['text_preview']}"
        )
        font_counter[info["font"]] = font_counter.get(info["font"], 0) + 1
        style_counter[info["style"]] = style_counter.get(info["style"], 0) + 1

    # ── 테이블 분석 ──────────────────────────────────────────────
    if doc.tables:
        print(f"\n[테이블 분석] 총 {len(doc.tables)}개 테이블")
        for t_idx, table in enumerate(doc.tables):
            info = analyze_table(table, t_idx)
            print(f"  Table {info['table_idx']}: {info['rows']}행 × {info['cols']}열 | {info['sample']}")

    # ── 서식 요약 ──────────────────────────────────────────────
    print("\n[서식 요약]")
    top_fonts = sorted(font_counter.items(), key=lambda x: -x[1])[:5]
    print(f"  주요 폰트: {top_fonts}")
    top_styles = sorted(style_counter.items(), key=lambda x: -x[1])[:5]
    print(f"  주요 스타일: {top_styles}")

    # ── 섹션/페이지 설정 ──────────────────────────────────────────────
    if doc.sections:
        section = doc.sections[0]
        print("\n[페이지 설정]")
        try:
            print(f"  크기: {section.page_width.cm:.1f}cm × {section.page_height.cm:.1f}cm")
            print(
                f"  여백: 좌{section.left_margin.cm:.2f} 우{section.right_margin.cm:.2f} "
                f"상{section.top_margin.cm:.2f} 하{section.bottom_margin.cm:.2f} cm"
            )
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="샘플 체결본 서식 분석")
    parser.add_argument("--type", choices=["spa", "sha", "ssa", "mou", "all"], default="all")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--max-paras", type=int, default=60, help="출력할 최대 단락 수")
    args = parser.parse_args()

    targets = SAMPLE_FILES if args.type == "all" else {args.type: SAMPLE_FILES[args.type]}

    for doc_type, path in targets.items():
        print_analysis(path, doc_type, verbose=args.verbose, max_paras=args.max_paras)

    # SPA 추가 파일
    if args.type in ("spa", "all"):
        for extra in EXTRA_SPA:
            if extra.exists():
                print_analysis(extra, "spa_extra", verbose=args.verbose, max_paras=args.max_paras)

    print("\n✅ 분석 완료")


if __name__ == "__main__":
    main()
