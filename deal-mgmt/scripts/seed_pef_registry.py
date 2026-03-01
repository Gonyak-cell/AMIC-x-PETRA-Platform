"""PEF 레지스트리 시드 스크립트.

기관전용 사모집합투자기구 현황 xlsx → pef_fund_registry 테이블 bulk insert.
금융감독원 공시 기준 약 1,137건.

Usage:
    python scripts/seed_pef_registry.py [--xlsx PATH] [--database-url URL]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_XLSX = (
    Path(__file__).resolve().parent.parent.parent / "기관전용 사모집합투자기구 현황(2024.12월말 기준)_게시용.xlsx"
)

# xlsx 헤더 → DB 컬럼 매핑 (row 4 기준, 0-indexed col)
COL_MAP = {
    2: "legal_basis",  # 설립근거법률
    3: "pef_name",  # PEF 명칭(약식)
    4: "registration_date",  # 등록일(설립일)*
    5: "gp1",  # GP1
    6: "gp2",  # GP2
    7: "gp3",  # GP3
    8: "total_committed_capital",  # 총약정액(합계)
}


def parse_xlsx(xlsx_path: Path) -> list[dict]:
    """xlsx 파일을 파싱하여 PEF 레코드 목록을 반환한다."""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        msg = f"No active sheet in {xlsx_path}"
        raise ValueError(msg)

    records: list[dict] = []
    for _row_idx, row in enumerate(ws.iter_rows(min_row=5, values_only=True), start=5):
        # 순번 컬럼(col 1)이 숫자가 아니면 합계/빈행 → 건너뜀
        seq = row[1] if len(row) > 1 else None
        if seq is None or not isinstance(seq, (int, float)):
            continue

        pef_name = row[3] if len(row) > 3 else None
        if not pef_name or not str(pef_name).strip():
            continue

        capital_raw = row[8] if len(row) > 8 else None
        capital: Decimal | None = None
        if capital_raw is not None:
            try:
                capital = Decimal(str(capital_raw))
            except (InvalidOperation, ValueError):
                capital = None

        record = {
            "id": uuid.uuid4(),
            "pef_name": str(row[3]).strip(),
            "legal_basis": str(row[2]).strip() if row[2] else None,
            "registration_date": str(row[4]).strip() if row[4] else None,
            "gp1": str(row[5]).strip() if len(row) > 5 and row[5] else None,
            "gp2": str(row[6]).strip() if len(row) > 6 and row[6] else None,
            "gp3": str(row[7]).strip() if len(row) > 7 and row[7] else None,
            "total_committed_capital": capital,
        }
        records.append(record)

    wb.close()
    return records


async def seed_database(database_url: str, records: list[dict]) -> int:
    """레코드들을 DB에 bulk insert한다."""
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 기존 데이터 삭제
        await session.execute(text("DELETE FROM pef_fund_registry"))

        # bulk insert (100건씩 배치)
        batch_size = 100
        inserted = 0
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            values_list = []
            for r in batch:
                values_list.append(
                    f"('{r['id']}', '{r['pef_name']}', "
                    f"{_sql_str(r['legal_basis'])}, "
                    f"{_sql_str(r['registration_date'])}, "
                    f"{_sql_str(r['gp1'])}, "
                    f"{_sql_str(r['gp2'])}, "
                    f"{_sql_str(r['gp3'])}, "
                    f"{r['total_committed_capital'] if r['total_committed_capital'] is not None else 'NULL'})"
                )
            sql = (
                "INSERT INTO pef_fund_registry "
                "(id, pef_name, legal_basis, registration_date, gp1, gp2, gp3, total_committed_capital) "
                "VALUES " + ", ".join(values_list)
            )
            await session.execute(text(sql))
            inserted += len(batch)

        await session.commit()

    await engine.dispose()
    return inserted


def _sql_str(value: str | None) -> str:
    """SQL 문자열 리터럴로 변환한다. None이면 NULL."""
    if value is None:
        return "NULL"
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


async def main() -> None:
    parser = argparse.ArgumentParser(description="PEF 레지스트리 시드")
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=DEFAULT_XLSX,
        help="PEF 현황 xlsx 파일 경로",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="AsyncDB URL (기본: 환경변수 DATABASE_URL)",
    )
    args = parser.parse_args()

    if args.database_url is None:
        import os

        args.database_url = os.environ.get(
            "DATABASE_URL",
            "sqlite+aiosqlite:///./deal_mgmt.db",
        )

    print(f"Parsing {args.xlsx} ...")
    records = parse_xlsx(args.xlsx)
    print(f"Parsed {len(records)} PEF records")

    print(f"Seeding to {args.database_url} ...")
    inserted = await seed_database(args.database_url, records)
    print(f"Done — {inserted} records inserted")


if __name__ == "__main__":
    asyncio.run(main())
