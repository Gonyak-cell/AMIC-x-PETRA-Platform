"""Beta Pilot 샘플 데이터 생성 — Sprint 13 A5.

파트너 온보딩용 샘플 TB/GL Excel 파일 생성.

사용법:
    python scripts/generate-sample-data.py
    python scripts/generate-sample-data.py --output-dir data/samples
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


def generate_sample_tb(output_dir: Path) -> str:
    """샘플 시산표 (TB) 생성 — 20개 계정."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"

    # Header styling
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(
        start_color="4472C4", end_color="4472C4", fill_type="solid"
    )
    header_font_white = Font(bold=True, size=11, color="FFFFFF")

    headers = ["계정코드", "계정명", "차변", "대변"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # 계정 데이터 (현실적인 FDD 시산표)
    accounts = [
        ("1010", "현금및현금성자산", Decimal("500000000"), Decimal("0")),
        ("1020", "단기금융상품", Decimal("200000000"), Decimal("0")),
        ("1110", "매출채권", Decimal("350000000"), Decimal("0")),
        ("1120", "대손충당금", Decimal("0"), Decimal("15000000")),
        ("1200", "재고자산", Decimal("280000000"), Decimal("0")),
        ("1210", "원재료", Decimal("120000000"), Decimal("0")),
        ("1300", "선급금", Decimal("45000000"), Decimal("0")),
        ("1310", "선급비용", Decimal("30000000"), Decimal("0")),
        ("2010", "유형자산", Decimal("800000000"), Decimal("0")),
        ("2020", "감가상각누계액", Decimal("0"), Decimal("320000000")),
        ("3010", "매입채무", Decimal("0"), Decimal("250000000")),
        ("3020", "미지급금", Decimal("0"), Decimal("85000000")),
        ("3030", "예수금", Decimal("0"), Decimal("35000000")),
        ("3100", "단기차입금", Decimal("0"), Decimal("300000000")),
        ("3200", "장기차입금", Decimal("0"), Decimal("500000000")),
        ("4010", "자본금", Decimal("0"), Decimal("100000000")),
        ("4020", "이익잉여금", Decimal("0"), Decimal("720000000")),
        ("5010", "매출액", Decimal("0"), Decimal("2500000000")),
        ("6010", "매출원가", Decimal("1800000000"), Decimal("0")),
        ("7010", "판매비와관리비", Decimal("500000000"), Decimal("0")),
    ]

    for row_idx, (code, name, debit, credit) in enumerate(accounts, 2):
        ws.cell(row=row_idx, column=1, value=code)
        ws.cell(row=row_idx, column=2, value=name)
        ws.cell(row=row_idx, column=3, value=int(debit))
        ws.cell(row=row_idx, column=4, value=int(credit))

    # Column widths
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18

    file_path = output_dir / "sample-tb.xlsx"
    wb.save(str(file_path))
    return str(file_path)


def generate_sample_gl(output_dir: Path) -> str:
    """샘플 총계정원장 (GL) 생성 — 50건 전표."""
    wb = Workbook()
    ws = wb.active
    ws.title = "총계정원장"

    # Header styling
    header_fill = PatternFill(
        start_color="4472C4", end_color="4472C4", fill_type="solid"
    )
    header_font_white = Font(bold=True, size=11, color="FFFFFF")

    headers = [
        "전표번호",
        "전표일자",
        "계정코드",
        "계정명",
        "차변",
        "대변",
        "적요",
        "거래처",
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # 전표 데이터 (현실적인 FDD GL)
    entries = [
        (
            "J-2025-001",
            "2025-01-05",
            "1010",
            "현금및현금성자산",
            50000000,
            0,
            "전월이월",
            "",
        ),
        (
            "J-2025-002",
            "2025-01-10",
            "5010",
            "매출액",
            0,
            150000000,
            "1월 매출",
            "ABC전자",
        ),
        (
            "J-2025-002",
            "2025-01-10",
            "1110",
            "매출채권",
            150000000,
            0,
            "1월 매출",
            "ABC전자",
        ),
        (
            "J-2025-003",
            "2025-01-15",
            "6010",
            "매출원가",
            100000000,
            0,
            "1월 원가",
            "원재료공급사",
        ),
        (
            "J-2025-003",
            "2025-01-15",
            "3010",
            "매입채무",
            0,
            100000000,
            "1월 원가",
            "원재료공급사",
        ),
        (
            "J-2025-004",
            "2025-01-20",
            "7010",
            "판매비와관리비",
            25000000,
            0,
            "급여",
            "임직원",
        ),
        (
            "J-2025-004",
            "2025-01-20",
            "1010",
            "현금및현금성자산",
            0,
            25000000,
            "급여 지급",
            "임직원",
        ),
        (
            "J-2025-005",
            "2025-01-25",
            "1010",
            "현금및현금성자산",
            120000000,
            0,
            "매출채권 회수",
            "ABC전자",
        ),
        (
            "J-2025-005",
            "2025-01-25",
            "1110",
            "매출채권",
            0,
            120000000,
            "매출채권 회수",
            "ABC전자",
        ),
        (
            "J-2025-006",
            "2025-01-31",
            "7010",
            "판매비와관리비",
            5000000,
            0,
            "접대비",
            "",
        ),
        (
            "J-2025-006",
            "2025-01-31",
            "1010",
            "현금및현금성자산",
            0,
            5000000,
            "접대비 지급",
            "",
        ),
        (
            "J-2025-007",
            "2025-02-05",
            "5010",
            "매출액",
            0,
            180000000,
            "2월 매출",
            "XYZ무역",
        ),
        (
            "J-2025-007",
            "2025-02-05",
            "1110",
            "매출채권",
            180000000,
            0,
            "2월 매출",
            "XYZ무역",
        ),
        (
            "J-2025-008",
            "2025-02-10",
            "6010",
            "매출원가",
            130000000,
            0,
            "2월 원가",
            "원재료공급사",
        ),
        (
            "J-2025-008",
            "2025-02-10",
            "3010",
            "매입채무",
            0,
            130000000,
            "2월 원가",
            "원재료공급사",
        ),
        (
            "J-2025-009",
            "2025-02-15",
            "3010",
            "매입채무",
            80000000,
            0,
            "1월분 지급",
            "원재료공급사",
        ),
        (
            "J-2025-009",
            "2025-02-15",
            "1010",
            "현금및현금성자산",
            0,
            80000000,
            "매입채무 지급",
            "원재료공급사",
        ),
        (
            "J-2025-010",
            "2025-02-20",
            "7010",
            "판매비와관리비",
            25000000,
            0,
            "2월 급여",
            "임직원",
        ),
        (
            "J-2025-010",
            "2025-02-20",
            "1010",
            "현금및현금성자산",
            0,
            25000000,
            "2월 급여 지급",
            "임직원",
        ),
        (
            "J-2025-011",
            "2025-02-28",
            "2020",
            "감가상각누계액",
            0,
            10000000,
            "2월 감가상각",
            "",
        ),
        (
            "J-2025-011",
            "2025-02-28",
            "7010",
            "판매비와관리비",
            10000000,
            0,
            "감가상각비",
            "",
        ),
        (
            "J-2025-012",
            "2025-03-05",
            "5010",
            "매출액",
            0,
            200000000,
            "3월 매출",
            "DEF산업",
        ),
        (
            "J-2025-012",
            "2025-03-05",
            "1110",
            "매출채권",
            200000000,
            0,
            "3월 매출",
            "DEF산업",
        ),
        (
            "J-2025-013",
            "2025-03-10",
            "6010",
            "매출원가",
            140000000,
            0,
            "3월 원가",
            "원재료공급사",
        ),
        (
            "J-2025-013",
            "2025-03-10",
            "3010",
            "매입채무",
            0,
            140000000,
            "3월 원가",
            "원재료공급사",
        ),
        (
            "J-2025-014",
            "2025-03-15",
            "1020",
            "단기금융상품",
            100000000,
            0,
            "정기예금 가입",
            "한국은행",
        ),
        (
            "J-2025-014",
            "2025-03-15",
            "1010",
            "현금및현금성자산",
            0,
            100000000,
            "정기예금 가입",
            "한국은행",
        ),
        (
            "J-2025-015",
            "2025-03-20",
            "7010",
            "판매비와관리비",
            25000000,
            0,
            "3월 급여",
            "임직원",
        ),
        (
            "J-2025-015",
            "2025-03-20",
            "1010",
            "현금및현금성자산",
            0,
            25000000,
            "3월 급여 지급",
            "임직원",
        ),
        (
            "J-2025-016",
            "2025-03-25",
            "3100",
            "단기차입금",
            50000000,
            0,
            "차입금 상환",
            "기업은행",
        ),
        (
            "J-2025-016",
            "2025-03-25",
            "1010",
            "현금및현금성자산",
            0,
            50000000,
            "차입금 상환",
            "기업은행",
        ),
        (
            "J-2025-017",
            "2025-03-28",
            "7010",
            "판매비와관리비",
            15000000,
            0,
            "법률자문료",
            "법률법인",
        ),
        (
            "J-2025-017",
            "2025-03-28",
            "3020",
            "미지급금",
            0,
            15000000,
            "법률자문료",
            "법률법인",
        ),
        (
            "J-2025-018",
            "2025-03-30",
            "1110",
            "매출채권",
            0,
            160000000,
            "2월분 회수",
            "XYZ무역",
        ),
        (
            "J-2025-018",
            "2025-03-30",
            "1010",
            "현금및현금성자산",
            160000000,
            0,
            "매출채권 회수",
            "XYZ무역",
        ),
        (
            "J-2025-019",
            "2025-03-31",
            "1120",
            "대손충당금",
            0,
            5000000,
            "대손충당금 설정",
            "",
        ),
        (
            "J-2025-019",
            "2025-03-31",
            "7010",
            "판매비와관리비",
            5000000,
            0,
            "대손상각비",
            "",
        ),
        (
            "J-2025-020",
            "2025-03-31",
            "7010",
            "판매비와관리비",
            8000000,
            0,
            "임차료",
            "강남빌딩",
        ),
        (
            "J-2025-020",
            "2025-03-31",
            "1010",
            "현금및현금성자산",
            0,
            8000000,
            "임차료 지급",
            "강남빌딩",
        ),
        (
            "J-2025-021",
            "2025-03-31",
            "7010",
            "판매비와관리비",
            3000000,
            0,
            "보험료",
            "삼성화재",
        ),
        (
            "J-2025-021",
            "2025-03-31",
            "1310",
            "선급비용",
            0,
            3000000,
            "보험료 대체",
            "삼성화재",
        ),
        (
            "J-2025-022",
            "2025-03-31",
            "5010",
            "매출액",
            0,
            50000000,
            "특별 매출 (일회성)",
            "GHI테크",
        ),
        (
            "J-2025-022",
            "2025-03-31",
            "1110",
            "매출채권",
            50000000,
            0,
            "특별 매출 (일회성)",
            "GHI테크",
        ),
        (
            "J-2025-023",
            "2025-03-31",
            "7010",
            "판매비와관리비",
            20000000,
            0,
            "소송합의금 (일회성)",
            "",
        ),
        (
            "J-2025-023",
            "2025-03-31",
            "1010",
            "현금및현금성자산",
            0,
            20000000,
            "소송합의금 지급",
            "",
        ),
        (
            "J-2025-024",
            "2025-03-31",
            "7010",
            "판매비와관리비",
            12000000,
            0,
            "이사 보너스 (비경상)",
            "임직원",
        ),
        (
            "J-2025-024",
            "2025-03-31",
            "3020",
            "미지급금",
            0,
            12000000,
            "이사 보너스",
            "임직원",
        ),
        (
            "J-2025-025",
            "2025-03-31",
            "7010",
            "판매비와관리비",
            2000000,
            0,
            "잡손실",
            "",
        ),
        (
            "J-2025-025",
            "2025-03-31",
            "1010",
            "현금및현금성자산",
            0,
            2000000,
            "잡손실",
            "",
        ),
    ]

    for row_idx, entry in enumerate(entries, 2):
        for col_idx, val in enumerate(entry, 1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    # Column widths
    widths = [14, 12, 10, 20, 15, 15, 25, 15]
    for col_idx, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + col_idx)].width = w

    file_path = output_dir / "sample-gl.xlsx"
    wb.save(str(file_path))
    return str(file_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate FDD sample data for beta pilot"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/samples",
        help="Output directory (default: data/samples)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating sample data for Beta Pilot...")
    print()

    tb_path = generate_sample_tb(output_dir)
    print(f"  TB created: {tb_path}")

    gl_path = generate_sample_gl(output_dir)
    print(f"  GL created: {gl_path}")

    print()
    print(f"Sample files saved to: {output_dir}/")
    print("  sample-tb.xlsx  — 시산표 (20 계정)")
    print("  sample-gl.xlsx  — 총계정원장 (50 전표)")
    print()
    print("Note: GL에 일회성/비경상 항목 포함 (QoE 조정 테스트용):")
    print("  - J-2025-022: 특별 매출 (일회성)")
    print("  - J-2025-023: 소송합의금 (일회성)")
    print("  - J-2025-024: 이사 보너스 (비경상)")


if __name__ == "__main__":
    main()
