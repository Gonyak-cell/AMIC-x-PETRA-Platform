"""PEF 레지스트리 시드 스크립트.

기관전용 사모집합투자기구 현황 xlsx → pef_fund_registry 테이블 bulk insert.
금융감독원 공시 기준 약 1,137건.

Usage:
    python scripts/seed_pef_registry.py [--xlsx PATH] [--database-url URL]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_XLSX = Path(__file__).resolve().parent.parent / "data" / "fss_pef_registry.xlsx"


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
            "registration_date": str(row[4]).strip()[:10] if row[4] else None,
            "gp1": str(row[5]).strip() if len(row) > 5 and row[5] else None,
            "gp2": str(row[6]).strip() if len(row) > 6 and row[6] else None,
            "gp3": str(row[7]).strip() if len(row) > 7 and row[7] else None,
            "total_committed_capital": capital,
        }
        records.append(record)

    wb.close()
    return records


async def seed_database(database_url: str, records: list[dict], *, force: bool = False) -> int:
    """레코드들을 DB에 bulk insert한다.

    기본 동작: 100건 이상이면 스킵 (idempotent). --force로 재삽입 가능.
    """
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # idempotent: 이미 100건 이상이면 스킵
        existing = (await session.execute(text("SELECT COUNT(*) FROM pef_fund_registry"))).scalar() or 0
        if existing >= 100 and not force:
            logger.info("pef_fund_registry already has %d rows — skipping (use --force to re-seed)", existing)
            await engine.dispose()
            return 0

        # 기존 데이터 삭제
        await session.execute(text("DELETE FROM pef_fund_registry"))

        # bulk insert (100건씩 배치)
        batch_size = 100
        inserted = 0
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            stmt = text(
                "INSERT INTO pef_fund_registry "
                "(id, pef_name, legal_basis, registration_date, gp1, gp2, gp3, total_committed_capital) "
                "VALUES (:id, :pef_name, :legal_basis, :registration_date, :gp1, :gp2, :gp3, :capital)"
            )
            params = [
                {
                    "id": str(r["id"]),
                    "pef_name": r["pef_name"],
                    "legal_basis": r["legal_basis"],
                    "registration_date": r["registration_date"],
                    "gp1": r["gp1"],
                    "gp2": r["gp2"],
                    "gp3": r["gp3"],
                    "capital": float(r["total_committed_capital"])
                    if r["total_committed_capital"] is not None
                    else None,
                }
                for r in batch
            ]
            await session.execute(stmt, params)
            inserted += len(batch)

        await session.commit()

    await engine.dispose()
    return inserted


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
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 데이터가 있어도 강제 재삽입",
    )
    args = parser.parse_args()

    if args.database_url is None:
        import os

        args.database_url = os.environ.get(
            "DATABASE_URL",
            "sqlite+aiosqlite:///./deal_mgmt.db",
        )

    logger.info("Parsing %s ...", args.xlsx)
    records = parse_xlsx(args.xlsx)
    logger.info("Parsed %d PEF records", len(records))

    logger.info("Seeding to %s ...", args.database_url)
    inserted = await seed_database(args.database_url, records, force=args.force)
    logger.info("Done — %d records inserted", inserted)


if __name__ == "__main__":
    asyncio.run(main())
