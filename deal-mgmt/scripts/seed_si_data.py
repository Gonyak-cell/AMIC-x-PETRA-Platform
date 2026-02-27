"""SI 매핑 참조 데이터 시딩 스크립트.

사용법:
    python -m scripts.seed_si_data --csv-dir ./app/marketing/si_mapping/db

CSV 파일 요구사항 (parse_io_tables.py 출력):
    - io_ksic_mapping.csv: io_code, io_name, ksic_code (ksic_name은 선택)
    - transaction_table.csv: source_io_code, source_io_name, target_io_code, target_io_name, transaction_value

옵션:
    --csv-dir     CSV 파일 디렉토리 (기본: ./app/marketing/si_mapping/db)
    --dummy-count 더미 기업 생성 수 (기본: 500, 0이면 생성 안 함)
    --force       기존 데이터 삭제 후 재삽입
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import random
import uuid
from pathlib import Path

from sqlalchemy import delete, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 더미 기업명 프리픽스
_NAME_PREFIXES = [
    "테스트기업", "가상산업", "한국", "동양", "서울", "대한", "미래",
    "글로벌", "첨단", "신세계", "코리아", "아시아", "태평양", "중앙",
    "삼성", "현대", "에스케이", "엘지", "포스코", "한화", "두산",
    "금호", "대우", "쌍용", "효성", "코오롱", "동국", "세아",
]
_NAME_SUFFIXES = [
    "산업", "전자", "화학", "건설", "에너지", "물산", "테크",
    "솔루션", "글로벌", "홀딩스", "파트너스", "인더스트리", "코퍼레이션",
    "제약", "바이오", "시스템즈", "네트웍스", "캐피탈", "인베스트",
]


async def _get_engine_and_session(database_url: str | None = None):
    """DB 엔진/세션 생성."""
    if database_url is None:
        from app.core.config import settings
        database_url = settings.DATABASE_URL

    engine = create_async_engine(database_url)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def load_ksic_io_mappings(session: AsyncSession, csv_path: Path, force: bool = False) -> int:
    """ksic_mapping.csv → ksic_io_mappings 테이블 벌크 삽입."""
    from app.models.ksic_io_mapping import KsicIoMapping

    if force:
        await session.execute(delete(KsicIoMapping))
        await session.commit()
        logger.info("ksic_io_mappings 기존 데이터 삭제 완료")

    # 기존 데이터 확인
    count = (await session.execute(text("SELECT COUNT(*) FROM ksic_io_mappings"))).scalar()
    if count and count > 0 and not force:
        logger.info("ksic_io_mappings 이미 %d건 존재, 스킵", count)
        return count

    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "io_code": row["io_code"].strip(),
                "io_name": row.get("io_name", "").strip() or None,
                "ksic_code": row["ksic_code"].strip(),
                "ksic_name": row.get("ksic_name", "").strip() or None,
            })

    # 청크 삽입
    chunk_size = 5000
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        await session.execute(insert(KsicIoMapping), chunk)
        total += len(chunk)
        logger.info("ksic_io_mappings: %d / %d 삽입", total, len(rows))

    await session.commit()
    logger.info("ksic_io_mappings 총 %d건 삽입 완료", total)
    return total


async def load_io_transactions(session: AsyncSession, csv_path: Path, force: bool = False) -> int:
    """fact_transaction.csv → io_transactions 테이블 벌크 삽입."""
    from app.models.io_transaction import IOTransaction

    if force:
        await session.execute(delete(IOTransaction))
        await session.commit()
        logger.info("io_transactions 기존 데이터 삭제 완료")

    count = (await session.execute(text("SELECT COUNT(*) FROM io_transactions"))).scalar()
    if count and count > 0 and not force:
        logger.info("io_transactions 이미 %d건 존재, 스킵", count)
        return count

    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row["transaction_value"].strip()
            if not val or float(val) == 0:
                continue  # 거래액 0 제외
            rows.append({
                "source_io_code": row["source_io_code"].strip(),
                "source_io_name": row.get("source_io_name", "").strip() or None,
                "target_io_code": row["target_io_code"].strip(),
                "target_io_name": row.get("target_io_name", "").strip() or None,
                "transaction_value": float(val),
            })

    chunk_size = 5000
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        await session.execute(insert(IOTransaction), chunk)
        total += len(chunk)
        if total % 50000 == 0 or total == len(rows):
            logger.info("io_transactions: %d / %d 삽입", total, len(rows))

    await session.commit()
    logger.info("io_transactions 총 %d건 삽입 완료", total)
    return total


async def generate_dummy_companies(
    session: AsyncSession, n: int = 500, force: bool = False
) -> int:
    """더미 SI 기업 생성 — 매핑 테이블의 실제 KSIC 코드 사용."""
    from app.models.si_company import SICompany

    if force:
        await session.execute(delete(SICompany))
        await session.commit()
        logger.info("si_companies 기존 데이터 삭제 완료")

    count = (await session.execute(text("SELECT COUNT(*) FROM si_companies"))).scalar()
    if count and count > 0 and not force:
        logger.info("si_companies 이미 %d건 존재, 스킵", count)
        return count

    # 매핑 테이블에서 KSIC 코드 풀 추출
    from app.models.ksic_io_mapping import KsicIoMapping

    result = await session.execute(select(KsicIoMapping.ksic_code).distinct())
    ksic_pool = [row[0] for row in result.all()]
    if not ksic_pool:
        logger.warning("ksic_io_mappings가 비어있어 더미 기업 생성 불가. 먼저 매핑 데이터를 삽입하세요.")
        return 0

    logger.info("KSIC 코드 풀: %d개", len(ksic_pool))

    companies = []
    used_names: set[str] = set()
    for _ in range(n):
        # 고유 기업명 생성
        while True:
            prefix = random.choice(_NAME_PREFIXES)
            suffix = random.choice(_NAME_SUFFIXES)
            name = f"{prefix}{suffix}"
            if name not in used_names:
                used_names.add(name)
                break

        # 무작위 KSIC 1~3개
        k = random.randint(1, 3)
        codes = random.sample(ksic_pool, min(k, len(ksic_pool)))

        companies.append({
            "id": uuid.uuid4(),
            "company_name": name,
            "ksic_codes": codes,
            "revenue": float(random.randint(100, 10000)) * 1_000_000_00,  # 100억 ~ 1조
            "has_investment_history": random.choice([True, False]),
            "description": None,
        })

    from app.models.si_company import SICompany

    chunk_size = 100
    total = 0
    for i in range(0, len(companies), chunk_size):
        chunk = companies[i : i + chunk_size]
        await session.execute(insert(SICompany), chunk)
        total += len(chunk)

    await session.commit()
    logger.info("si_companies 더미 %d건 생성 완료", total)
    return total


async def main(csv_dir: str = "./data", dummy_count: int = 500, force: bool = False):
    """시딩 메인 실행."""
    csv_path = Path(csv_dir)

    engine, session_factory = await _get_engine_and_session()

    async with session_factory() as session:
        # 1. KSIC-IO 매핑
        mapping_csv = csv_path / "io_ksic_mapping.csv"
        if mapping_csv.exists():
            await load_ksic_io_mappings(session, mapping_csv, force)
        else:
            logger.warning("파일 없음: %s", mapping_csv)

        # 2. IO 거래 데이터
        tx_csv = csv_path / "transaction_table.csv"
        if tx_csv.exists():
            await load_io_transactions(session, tx_csv, force)
        else:
            logger.warning("파일 없음: %s", tx_csv)

        # 3. 더미 기업 생성
        await generate_dummy_companies(session, dummy_count, force)

    await engine.dispose()
    logger.info("시딩 완료!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SI 매핑 참조 데이터 시딩")
    parser.add_argument("--csv-dir", default="./app/marketing/si_mapping/db", help="CSV 파일 디렉토리")
    parser.add_argument("--dummy-count", type=int, default=500, help="더미 기업 수")
    parser.add_argument("--force", action="store_true", help="기존 데이터 삭제 후 재삽입")
    args = parser.parse_args()

    asyncio.run(main(csv_dir=args.csv_dir, dummy_count=args.dummy_count, force=args.force))
