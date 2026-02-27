"""기업개황 Excel → CSV 일괄 변환 스크립트.

deal-mgmt/app/marketing/si_list/ 폴더의 모든 .xlsx 파일을
dtype=str로 읽어 앞자리 0을 보존한 채 CSV로 변환한다.

Usage:
    cd deal-mgmt

    # 기본 실행 (소스: app/marketing/si_list/, 출력: csv/ 하위 폴더)
    python scripts/convert_si_excel_to_csv.py

    # 출력 디렉토리 지정
    python scripts/convert_si_excel_to_csv.py --output-dir ./output

    # 소스 디렉토리 지정
    python scripts/convert_si_excel_to_csv.py --source-dir ./data
"""

from __future__ import annotations

import argparse
import gc
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = SCRIPT_DIR.parent / "app" / "marketing" / "si_list"


def convert_all(source_dir: Path, output_dir: Path) -> None:
    """source_dir 내 모든 .xlsx를 output_dir에 .csv로 변환한다."""

    output_dir.mkdir(parents=True, exist_ok=True)

    xlsx_files = sorted(source_dir.glob("*.xlsx"))

    if not xlsx_files:
        logger.error("xlsx 파일을 찾을 수 없습니다: %s", source_dir)
        return

    logger.info("발견된 xlsx 파일: %d개", len(xlsx_files))
    logger.info("출력 폴더: %s", output_dir)

    success_count = 0
    fail_count = 0
    failed_files: list[str] = []
    total_rows = 0

    for filepath in xlsx_files:
        csv_filename = filepath.stem + ".csv"
        csv_path = output_dir / csv_filename

        try:
            df = pd.read_excel(filepath, engine="openpyxl", dtype=str)
            row_count = len(df)
            total_rows += row_count

            df.to_csv(csv_path, encoding="utf-8-sig", index=False)

            logger.info("[OK] %s → %s (%s행)", filepath.name, csv_filename, f"{row_count:,}")

            del df
            gc.collect()

            success_count += 1

        except Exception:
            logger.exception("[FAIL] %s", filepath.name)
            fail_count += 1
            failed_files.append(filepath.name)
            continue

    logger.info("성공: %d개 / 실패: %d개 / 총 행수: %s", success_count, fail_count, f"{total_rows:,}")
    if failed_files:
        logger.info("실패 파일: %s", ", ".join(failed_files))


def main() -> None:
    parser = argparse.ArgumentParser(description="기업개황 Excel → CSV 일괄 변환")
    parser.add_argument(
        "--source-dir",
        type=str,
        default=None,
        help="소스 xlsx 디렉토리 (기본: app/marketing/si_list/)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="출력 csv 디렉토리 (기본: 소스 디렉토리/csv/)",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir) if args.source_dir else DEFAULT_SOURCE_DIR
    output_dir = Path(args.output_dir) if args.output_dir else source_dir / "csv"

    convert_all(source_dir, output_dir)


if __name__ == "__main__":
    main()
