"""한국은행 2020 산업연관표 ETL 파이프라인.

3개 Excel 원본 파일을 파싱하여 5개 flat CSV 파일을 생성한다.
DB/서버 없이 로컬에서 독립 실행 가능.

Usage:
    cd deal-mgmt

    # 탐색 모드: 파일 구조 검사만 수행 (CSV 미생성)
    python scripts/parse_io_tables.py --explore

    # Phase 1만: 차원 테이블 2개 (KSIC 매핑 + 산업분류)
    python scripts/parse_io_tables.py --phase 1

    # Phase 2만: 팩트 테이블 3개 (총거래표 + 생산유발계수 + 부가가치유발계수)
    python scripts/parse_io_tables.py --phase 2

    # 전체: Phase 1 + Phase 2 (5개 CSV 모두 생성)
    python scripts/parse_io_tables.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import openpyxl

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DEAL_MGMT_DIR = SCRIPT_DIR.parent
DB_DIR = DEAL_MGMT_DIR / "app" / "marketing" / "si_mapping" / "db"

FILE_KSIC = DB_DIR / "IO코드와 KSIC 및 HS코드 대조표.xlsx"
FILE_INDUSTRY = DB_DIR / "2020_산업분류표.xlsx"
FILE_IO_TABLE = DB_DIR / "(표)(2020실측)투입산출표_생산자가격_기본부문.xlsx"

# Phase 2 대상 시트 → 출력 CSV 매핑
IO_SHEETS = {
    "A표_총거래표(생산자)": "transaction_table.csv",
    "생산유발계수": "production_inducement.csv",
    "부가가치유발계수": "value_added_inducement.csv",
}


def _is_empty(val) -> bool:
    """None 이거나 빈 문자열이면 True."""
    return val is None or str(val).strip() == ""


def _normalize_io_code(raw) -> str:
    """IO코드를 4자리 문자열로 정규화 (int/float/str 혼재 대응)."""
    if isinstance(raw, float):
        raw = int(raw)
    return str(raw).strip().zfill(4)


# ===================================================================
# 탐색 모드
# ===================================================================


def explore_all(output_dir: Path) -> None:
    """3개 Excel 파일의 구조를 검사하고 요약을 출력한다."""

    print("=" * 70)
    print(" 사전 탐색: 파일 구조 검사")
    print("=" * 70)

    # --- File 1: IO-KSIC 대조표 ---
    print("\n[1] IO코드와 KSIC 및 HS코드 대조표")
    print(f"    경로: {FILE_KSIC}")
    wb = openpyxl.load_workbook(FILE_KSIC, read_only=True, data_only=True)
    try:
        print(f"    시트: {wb.sheetnames}")
        ws = wb["IO코드와 KSIC 비교표"]
        print(f"    행수: {ws.max_row}, 열수: {ws.max_column}")
        print("    처음 5행:")
        for i, row in enumerate(ws.iter_rows(max_row=5, values_only=True), 1):
            print(f"      Row {i}: {list(row[:6])}")
    finally:
        wb.close()

    # --- File 2: 산업분류표 ---
    print("\n[2] 2020 산업분류표")
    print(f"    경로: {FILE_INDUSTRY}")
    wb = openpyxl.load_workbook(FILE_INDUSTRY, read_only=True, data_only=True)
    try:
        print(f"    시트: {wb.sheetnames}")
        ws = wb[wb.sheetnames[0]]
        print(f"    행수: {ws.max_row}, 열수: {ws.max_column}")
        print("    처음 5행:")
        for i, row in enumerate(ws.iter_rows(max_row=5, values_only=True), 1):
            print(f"      Row {i}: {list(row[:8])}")
    finally:
        wb.close()

    # --- File 3: 투입산출표 ---
    print("\n[3] 투입산출표 (생산자가격, 기본부문)")
    print(f"    경로: {FILE_IO_TABLE}")
    wb = openpyxl.load_workbook(FILE_IO_TABLE, read_only=True, data_only=True)
    try:
        print(f"    시트 목록 ({len(wb.sheetnames)}개):")
        for s in wb.sheetnames:
            ws = wb[s]
            print(f"      - {s}  ({ws.max_row}행 × {ws.max_column}열)")
        print("    파싱 대상 시트 헤더 (Row 5-7):")
        for sname in IO_SHEETS:
            ws = wb[sname]
            print(f"\n    [{sname}]")
            for i, row in enumerate(ws.iter_rows(min_row=5, max_row=7, values_only=True), 5):
                vals = list(row[:8])
                print(f"      Row {i}: {vals}")
    finally:
        wb.close()

    print("\n" + "=" * 70)
    print(" 탐색 완료. CSV 파일은 생성하지 않았습니다.")
    print("=" * 70)


# ===================================================================
# Phase 1-1: KSIC 매핑 테이블
# ===================================================================


def parse_ksic_mapping(output_dir: Path) -> int:
    """IO코드-KSIC 1:1 매핑을 파싱하여 CSV로 저장한다."""

    print("\n--- Phase 1-1: IO-KSIC 매핑 ---")
    wb = openpyxl.load_workbook(FILE_KSIC, read_only=True, data_only=True)
    try:
        ws = wb["IO코드와 KSIC 비교표"]

        current_io: str | None = None
        current_name: str = ""
        all_io_codes: set[str] = set()
        records: list[tuple[str, str, str]] = []

        for row in ws.iter_rows(min_row=3, values_only=True):
            io_val = row[0]
            name_val = row[1]
            ksic_val = row[2]

            # ffill: IO코드가 비어있지 않으면 갱신
            if not _is_empty(io_val):
                current_io = str(io_val).strip()
                current_name = str(name_val).strip() if name_val else ""
                all_io_codes.add(current_io)

            # KSIC가 비어있으면 skip
            if _is_empty(ksic_val):
                continue

            if current_io is None:
                continue

            records.append((current_io, current_name, str(ksic_val).strip()))
    finally:
        wb.close()

    # CSV 저장
    out_path = output_dir / "io_ksic_mapping.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["io_code", "io_name", "ksic_code"])
        writer.writerows(records)

    mapped_ios = set(r[0] for r in records)
    unmapped_ios = sorted(all_io_codes - mapped_ios)
    print(f"  고유 IO코드: {len(mapped_ios)}")
    print(f"  총 레코드: {len(records)}")
    if unmapped_ios:
        print(f"  KSIC 미매핑 IO코드: {unmapped_ios}")
    print(f"  저장: {out_path}")
    return len(records)


# ===================================================================
# Phase 1-2: 산업분류 계층 테이블
# ===================================================================


def parse_industry_classification(output_dir: Path) -> int:
    """산업분류 4단계 계층을 파싱하여 flat CSV로 저장한다."""

    print("\n--- Phase 1-2: 산업분류 계층 ---")
    wb = openpyxl.load_workbook(FILE_INDUSTRY, read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]

        # ffill 상태 변수
        cur_sub = ("", "")  # (소분류코드, 소분류명)
        cur_mid = ("", "")  # (중분류코드, 중분류명)
        cur_large = ("", "")  # (대분류코드, 대분류명)

        records: list[tuple[str, ...]] = []

        for row in ws.iter_rows(min_row=4, values_only=True):
            basic_code = row[0]

            # 빈 행 skip
            if _is_empty(basic_code):
                continue

            basic_code_str = str(basic_code).strip()

            # 각주 행 skip
            if basic_code_str.startswith("1)"):
                continue

            basic_name = str(row[1]).strip() if row[1] else ""

            # 상위 계층 ffill (빈 문자열/None이 아닐 때만 갱신)
            if not _is_empty(row[2]):
                cur_sub = (str(row[2]).strip(), str(row[3]).strip() if row[3] else "")
            if not _is_empty(row[4]):
                cur_mid = (str(row[4]).strip(), str(row[5]).strip() if row[5] else "")
            if not _is_empty(row[6]):
                cur_large = (
                    str(row[6]).strip(),
                    str(row[7]).strip() if row[7] else "",
                )

            records.append(
                (
                    basic_code_str,
                    basic_name,
                    cur_sub[0],
                    cur_sub[1],
                    cur_mid[0],
                    cur_mid[1],
                    cur_large[0],
                    cur_large[1],
                )
            )
    finally:
        wb.close()

    # CSV 저장
    out_path = output_dir / "industry_classification.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "basic_code",
                "basic_name",
                "sub_code",
                "sub_name",
                "mid_code",
                "mid_name",
                "large_code",
                "large_name",
            ]
        )
        writer.writerows(records)

    pure_count = sum(1 for r in records if not r[0].startswith("9"))
    nine_count = sum(1 for r in records if r[0].startswith("9"))
    print(f"  총 레코드: {len(records)} (0xxx~8xxx: {pure_count} + 9xxx계열: {nine_count})")
    print(f"  저장: {out_path}")
    return len(records)


# ===================================================================
# Phase 2: 투입산출 매트릭스 평탄화
# ===================================================================


def _parse_io_sheet(ws, sheet_name: str, output_path: Path) -> int:
    """IO 행렬 1개 시트를 unpivot하여 flat CSV로 저장한다.

    380x380 순수 부문 행렬만 추출 (9xxx 합계/요약 행/열 제거).
    """

    print(f"\n  [{sheet_name}]")

    # Step 1: Row 5-6에서 열 IO코드/명 추출 (단일 iter_rows 호출)
    col_map: dict[int, tuple[str, str]] = {}
    header_rows = list(ws.iter_rows(min_row=5, max_row=6, values_only=True))
    row5 = header_rows[0]
    row6 = header_rows[1]

    for c_idx in range(2, len(row5)):
        raw_code = row5[c_idx]
        if raw_code is None:
            continue
        code_str = _normalize_io_code(raw_code)
        if code_str.startswith("9"):
            continue
        name = row6[c_idx] if c_idx < len(row6) else ""
        name_str = str(name).strip().replace("\n", " ") if name else ""
        col_map[c_idx] = (code_str, name_str)

    # Step 2: Row 7부터 데이터 순회, unpivot → CSV 직접 쓰기
    n_cols = len(col_map)
    n_rows = 0
    count = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "source_io_code",
                "source_io_name",
                "target_io_code",
                "target_io_name",
                "value",
            ]
        )

        for row in ws.iter_rows(min_row=7, values_only=True):
            row_code_raw = row[0]
            if row_code_raw is None:
                continue

            row_code = _normalize_io_code(row_code_raw)
            if row_code.startswith("9"):
                continue

            row_name_raw = row[1]
            row_name = str(row_name_raw).strip() if row_name_raw else ""
            n_rows += 1

            for c_idx, (col_code, col_name) in col_map.items():
                val = row[c_idx] if c_idx < len(row) else None

                # None, 하이픈, 문자열 → 0.0
                if val is None:
                    val = 0.0
                elif isinstance(val, str):
                    val_stripped = val.strip()
                    if val_stripped in ("-", "…", "...", ""):
                        val = 0.0
                    else:
                        try:
                            val = float(val_stripped.replace(",", ""))
                        except ValueError:
                            val = 0.0
                else:
                    val = float(val)

                writer.writerow([row_code, row_name, col_code, col_name, val])
                count += 1

    print(f"    행렬: {n_rows}행 × {n_cols}열 = {count:,} 레코드")
    print(f"    저장: {output_path}")
    return count


def run_phase2(output_dir: Path) -> None:
    """Phase 2: 3개 시트 순회 처리 (워크북 1회만 open)."""
    print("\n--- Phase 2: 투입산출 매트릭스 평탄화 ---")
    wb = openpyxl.load_workbook(FILE_IO_TABLE, read_only=True, data_only=True)
    try:
        for sheet_name, csv_name in IO_SHEETS.items():
            _parse_io_sheet(wb[sheet_name], sheet_name, output_dir / csv_name)
    finally:
        wb.close()


# ===================================================================
# 메인
# ===================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="한국은행 2020 산업연관표 ETL 파이프라인")
    parser.add_argument(
        "--explore",
        action="store_true",
        help="탐색 모드: 파일 구조 검사만 수행 (CSV 미생성)",
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2],
        default=None,
        help="특정 Phase만 실행 (1=차원, 2=팩트). 생략 시 전체 실행.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="출력 디렉토리 (기본: 소스 파일과 동일 경로)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else DB_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # 파일 존재 확인
    for fpath in (FILE_KSIC, FILE_INDUSTRY, FILE_IO_TABLE):
        if not fpath.exists():
            print(f"ERROR: 파일 없음 — {fpath}", file=sys.stderr)
            sys.exit(1)

    if args.explore:
        explore_all(output_dir)
        return

    print("=" * 70)
    print(" 한국은행 2020 산업연관표 ETL 파이프라인")
    print("=" * 70)

    if args.phase is None or args.phase == 1:
        parse_ksic_mapping(output_dir)
        parse_industry_classification(output_dir)

    if args.phase is None or args.phase == 2:
        run_phase2(output_dir)

    # 결과 요약
    print("\n" + "=" * 70)
    print(" ETL 결과 요약")
    print("=" * 70)

    for csv_name in (
        "io_ksic_mapping.csv",
        "industry_classification.csv",
        "transaction_table.csv",
        "production_inducement.csv",
        "value_added_inducement.csv",
    ):
        fpath = output_dir / csv_name
        if fpath.exists():
            size_kb = fpath.stat().st_size / 1024
            unit = "KB" if size_kb < 1024 else "MB"
            size_val = size_kb if size_kb < 1024 else size_kb / 1024
            print(f"  {csv_name:40s} {size_val:8.1f} {unit}")
        else:
            print(f"  {csv_name:40s} (미생성)")

    print("\n완료.")


if __name__ == "__main__":
    main()
