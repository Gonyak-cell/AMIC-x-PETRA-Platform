"""SI 매핑 참조 데이터 시딩 스크립트.

사용법:
    python -m scripts.seed_si_data --csv-dir ./app/marketing/si_mapping/db

CSV 파일 요구사항 (parse_io_tables.py 출력):
    - transaction_table.csv: source_io_code, source_io_name, target_io_code, target_io_name, value
    - io_ksic_mapping.csv: io_code, io_name, ksic_code (ksic_name은 선택)
    - production_inducement.csv: source_io_code, source_io_name, target_io_code, target_io_name, value
    - value_added_inducement.csv: source_io_code, source_io_name, target_io_code, target_io_name, value
    - industry_classification.csv: basic_code, basic_name, sub_code, sub_name, mid_code, mid_name, large_code, large_name

옵션:
    --csv-dir     CSV 파일 디렉토리 (기본: ./app/marketing/si_mapping/db)
    --dummy-count 더미 기업 생성 수 (기본: 500, 0이면 생성 안 함)
    --force       기존 데이터 삭제 후 재삽입
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import itertools
import logging
import random
import uuid
from pathlib import Path

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _validate_csv_headers(reader: csv.DictReader, required: list[str], csv_path: Path) -> None:
    """CSV 헤더에서 필수 컬럼 존재 여부 확인."""
    if reader.fieldnames is None:
        raise ValueError(f"CSV 파일에 헤더가 없습니다: {csv_path}")
    missing = set(required) - set(reader.fieldnames)
    if missing:
        raise ValueError(f"CSV 필수 컬럼 누락: {missing} (파일: {csv_path})")


# 더미 기업명 프리픽스
_NAME_PREFIXES = [
    "테스트기업",
    "가상산업",
    "한국",
    "동양",
    "서울",
    "대한",
    "미래",
    "글로벌",
    "첨단",
    "신세계",
    "코리아",
    "아시아",
    "태평양",
    "중앙",
    "삼성",
    "현대",
    "에스케이",
    "엘지",
    "포스코",
    "한화",
    "두산",
    "금호",
    "대우",
    "쌍용",
    "효성",
    "코오롱",
    "동국",
    "세아",
]
_NAME_SUFFIXES = [
    "산업",
    "전자",
    "화학",
    "건설",
    "에너지",
    "물산",
    "테크",
    "솔루션",
    "글로벌",
    "홀딩스",
    "파트너스",
    "인더스트리",
    "코퍼레이션",
    "제약",
    "바이오",
    "시스템즈",
    "네트웍스",
    "캐피탈",
    "인베스트",
]


async def _get_engine_and_session(database_url: str | None = None):
    """DB 엔진/세션 생성."""
    if database_url is None:
        from app.core.config import settings

        database_url = settings.DATABASE_URL

    engine = create_async_engine(database_url)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def load_io_sectors(session: AsyncSession, csv_path: Path, force: bool = False) -> int:
    """transaction_table.csv에서 고유 IO 코드를 추출하여 io_sectors 테이블에 삽입."""
    from app.models.io_sector import IOSector

    if force:
        await session.execute(delete(IOSector))
        await session.commit()
        logger.info("io_sectors 기존 데이터 삭제 완료")

    count = (await session.execute(select(func.count()).select_from(IOSector))).scalar()
    if count and count > 0 and not force:
        logger.info("io_sectors 이미 %d건 존재, 스킵", count)
        return count

    # transaction_table.csv에서 고유 IO 코드+이름 추출
    io_codes: dict[str, str] = {}
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _validate_csv_headers(reader, ["source_io_code", "target_io_code"], csv_path)
        for row in reader:
            src_code = row["source_io_code"].strip()
            src_name = row.get("source_io_name", "").strip()
            tgt_code = row["target_io_code"].strip()
            tgt_name = row.get("target_io_name", "").strip()
            if src_code and src_code not in io_codes:
                io_codes[src_code] = src_name
            if tgt_code and tgt_code not in io_codes:
                io_codes[tgt_code] = tgt_name

    rows = [{"code": code, "name": name or code} for code, name in sorted(io_codes.items())]

    await session.execute(insert(IOSector), rows)
    await session.commit()
    logger.info("io_sectors 총 %d건 삽입 완료", len(rows))
    return len(rows)


async def load_ksic_io_mappings(session: AsyncSession, csv_path: Path, force: bool = False) -> int:
    """io_ksic_mapping.csv → ksic_io_mappings 테이블 벌크 삽입."""
    from app.models.ksic_io_mapping import KsicIoMapping

    if force:
        await session.execute(delete(KsicIoMapping))
        await session.commit()
        logger.info("ksic_io_mappings 기존 데이터 삭제 완료")

    # 기존 데이터 확인
    count = (await session.execute(select(func.count()).select_from(KsicIoMapping))).scalar()
    if count and count > 0 and not force:
        logger.info("ksic_io_mappings 이미 %d건 존재, 스킵", count)
        return count

    rows = []
    seen: set[tuple[str, str]] = set()
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _validate_csv_headers(reader, ["io_code", "ksic_code"], csv_path)
        for row in reader:
            io_code = row["io_code"].strip()
            ksic_code = row["ksic_code"].strip()
            key = (io_code, ksic_code)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "io_code": io_code,
                    "io_name": row.get("io_name", "").strip() or None,
                    "ksic_code": ksic_code,
                    "ksic_name": row.get("ksic_name", "").strip() or None,
                }
            )

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
    """transaction_table.csv → io_transactions 테이블 벌크 삽입."""
    from app.models.io_transaction import IOTransaction

    if force:
        await session.execute(delete(IOTransaction))
        await session.commit()
        logger.info("io_transactions 기존 데이터 삭제 완료")

    count = (await session.execute(select(func.count()).select_from(IOTransaction))).scalar()
    if count and count > 0 and not force:
        logger.info("io_transactions 이미 %d건 존재, 스킵", count)
        return count

    rows = []
    seen: set[tuple[str, str]] = set()
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _validate_csv_headers(reader, ["source_io_code", "target_io_code", "value"], csv_path)
        for row in reader:
            val = row["value"].strip()
            if not val:
                continue
            try:
                fval = float(val)
            except ValueError:
                logger.warning("거래액 숫자 변환 실패, 스킵: value=%r", val)
                continue
            if fval == 0:
                continue  # 거래액 0 제외
            src = row["source_io_code"].strip()
            tgt = row["target_io_code"].strip()
            key = (src, tgt)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "source_io_code": src,
                    "source_io_name": row.get("source_io_name", "").strip() or None,
                    "target_io_code": tgt,
                    "target_io_name": row.get("target_io_name", "").strip() or None,
                    "transaction_value": fval,
                }
            )

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


async def load_inducements(
    session: AsyncSession,
    csv_path: Path,
    table_name: str,
    model_cls: type,
    force: bool = False,
) -> int:
    """유발계수 CSV → DB 테이블 벌크 삽입 (생산유발/부가가치유발 공용)."""
    if force:
        await session.execute(delete(model_cls))
        await session.commit()
        logger.info("%s 기존 데이터 삭제 완료", table_name)

    count = (
        await session.execute(select(func.count()).select_from(model_cls))
    ).scalar()
    if count and count > 0 and not force:
        logger.info("%s 이미 %d건 존재, 스킵", table_name, count)
        return count

    rows = []
    seen: set[tuple[str, str]] = set()
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _validate_csv_headers(reader, ["source_io_code", "target_io_code", "value"], csv_path)
        for row in reader:
            src = row["source_io_code"].strip()
            tgt = row["target_io_code"].strip()
            key = (src, tgt)
            if key in seen:
                continue
            seen.add(key)
            raw_val = row["value"].strip()
            try:
                coeff = float(raw_val)
            except ValueError:
                logger.warning("%s 계수 변환 실패, 스킵: value=%r", table_name, raw_val)
                continue
            rows.append(
                {
                    "source_io_code": src,
                    "target_io_code": tgt,
                    "coefficient": coeff,
                }
            )

    chunk_size = 5000
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        await session.execute(insert(model_cls), chunk)
        total += len(chunk)
        if total % 50000 == 0 or total == len(rows):
            logger.info("%s: %d / %d 삽입", table_name, total, len(rows))

    await session.commit()
    logger.info("%s 총 %d건 삽입 완료", table_name, total)
    return total


async def load_ksic_classifications(session: AsyncSession, csv_path: Path, force: bool = False) -> int:
    """industry_classification.csv → ksic_classifications 테이블 벌크 삽입."""
    from app.models.ksic_classification import KsicClassification

    if force:
        await session.execute(delete(KsicClassification))
        await session.commit()
        logger.info("ksic_classifications 기존 데이터 삭제 완료")

    count = (await session.execute(select(func.count()).select_from(KsicClassification))).scalar()
    if count and count > 0 and not force:
        logger.info("ksic_classifications 이미 %d건 존재, 스킵", count)
        return count

    rows = []
    seen: set[str] = set()
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _validate_csv_headers(reader, ["basic_code"], csv_path)
        for row in reader:
            basic_code = row["basic_code"].strip()
            if not basic_code or basic_code in seen:
                continue
            seen.add(basic_code)
            rows.append(
                {
                    "basic_code": basic_code,
                    "basic_name": row.get("basic_name", "").strip() or basic_code,
                    "sub_code": row.get("sub_code", "").strip() or None,
                    "sub_name": row.get("sub_name", "").strip() or None,
                    "mid_code": row.get("mid_code", "").strip() or None,
                    "mid_name": row.get("mid_name", "").strip() or None,
                    "large_code": row.get("large_code", "").strip() or None,
                    "large_name": row.get("large_name", "").strip() or None,
                }
            )

    await session.execute(insert(KsicClassification), rows)
    await session.commit()
    logger.info("ksic_classifications 총 %d건 삽입 완료", len(rows))
    return len(rows)


async def generate_dummy_companies(session: AsyncSession, n: int = 500, force: bool = False) -> int:
    """더미 SI 기업 생성 — 매핑 테이블의 실제 KSIC 코드 사용."""
    from app.models.si_company import SICompany

    if force:
        await session.execute(delete(SICompany))
        await session.commit()
        logger.info("si_companies 기존 데이터 삭제 완료")

    count = (await session.execute(select(func.count()).select_from(SICompany))).scalar()
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

    max_names = len(_NAME_PREFIXES) * len(_NAME_SUFFIXES)
    if n > max_names:
        logger.warning(
            "dummy_count=%d > 최대 조합 수=%d, %d로 제한", n, max_names, max_names
        )
        n = max_names

    # 전체 이름 조합 생성 후 셔플 — while True 무한 루프 방지
    all_names = [f"{p}{s}" for p, s in itertools.product(_NAME_PREFIXES, _NAME_SUFFIXES)]
    random.shuffle(all_names)
    selected_names = all_names[:n]

    companies = []
    for name in selected_names:
        # 무작위 KSIC 1~3개
        k = random.randint(1, 3)
        codes = random.sample(ksic_pool, min(k, len(ksic_pool)))

        companies.append(
            {
                "id": uuid.uuid4(),
                "company_name": name,
                "ksic_codes": codes,
                "revenue": float(random.randint(100, 10000)) * 100_000_000,  # 100억 ~ 1조
                "has_investment_history": random.choice([True, False]),
                "description": None,
            }
        )

    chunk_size = 100
    total = 0
    for i in range(0, len(companies), chunk_size):
        chunk = companies[i : i + chunk_size]
        await session.execute(insert(SICompany), chunk)
        total += len(chunk)

    await session.commit()
    logger.info("si_companies 더미 %d건 생성 완료", total)
    return total


async def _force_clear_all(session: AsyncSession) -> None:
    """--force: 전체 SI 테이블을 FK 역순으로 삭제 (자식 → 부모)."""
    from app.models.io_inducement import (
        IOProductionInducement,
        IOValueAddedInducement,
    )
    from app.models.io_sector import IOSector
    from app.models.io_transaction import IOTransaction
    from app.models.ksic_classification import KsicClassification
    from app.models.ksic_io_mapping import KsicIoMapping
    from app.models.si_company import SICompany

    # FK 의존 역순: leaf → root
    for model in [
        SICompany,
        IOProductionInducement,
        IOValueAddedInducement,
        IOTransaction,
        KsicIoMapping,
        IOSector,
        KsicClassification,
    ]:
        await session.execute(delete(model))
    await session.commit()
    logger.info("--force: 전체 SI 테이블 초기화 완료 (FK 역순)")


async def main(csv_dir: str = "./data", dummy_count: int = 500, force: bool = False):
    """시딩 메인 실행."""
    csv_path = Path(csv_dir)

    engine, session_factory = await _get_engine_and_session()

    async with session_factory() as session:
        # --force: FK 역순으로 전체 삭제 (개별 함수의 DELETE보다 먼저 실행)
        if force:
            await _force_clear_all(session)

        # 0. IO 부문분류 마스터 (FK 참조 대상, 가장 먼저 시딩)
        tx_csv = csv_path / "transaction_table.csv"
        if tx_csv.exists():
            await load_io_sectors(session, tx_csv, force)
        else:
            logger.warning("파일 없음: %s — io_sectors 시딩 스킵", tx_csv)

        # 1. KSIC-IO 매핑
        mapping_csv = csv_path / "io_ksic_mapping.csv"
        if mapping_csv.exists():
            await load_ksic_io_mappings(session, mapping_csv, force)
        else:
            logger.warning("파일 없음: %s", mapping_csv)

        # 2. IO 거래 데이터
        if tx_csv.exists():
            await load_io_transactions(session, tx_csv, force)
        else:
            logger.warning("파일 없음: %s", tx_csv)

        # 3. 생산유발계수
        from app.models.io_inducement import (
            IOProductionInducement,
            IOValueAddedInducement,
        )

        prod_csv = csv_path / "production_inducement.csv"
        if prod_csv.exists():
            await load_inducements(
                session,
                prod_csv,
                "io_production_inducements",
                IOProductionInducement,
                force,
            )
        else:
            logger.warning("파일 없음: %s", prod_csv)

        # 4. 부가가치유발계수
        va_csv = csv_path / "value_added_inducement.csv"
        if va_csv.exists():
            await load_inducements(
                session,
                va_csv,
                "io_value_added_inducements",
                IOValueAddedInducement,
                force,
            )
        else:
            logger.warning("파일 없음: %s", va_csv)

        # 5. KSIC 산업분류 참조 테이블
        cls_csv = csv_path / "industry_classification.csv"
        if cls_csv.exists():
            await load_ksic_classifications(session, cls_csv, force)
        else:
            logger.warning("파일 없음: %s", cls_csv)

        # 6. 더미 기업 생성
        await generate_dummy_companies(session, dummy_count, force)

    await engine.dispose()
    logger.info("시딩 완료!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SI 매핑 참조 데이터 시딩")
    parser.add_argument(
        "--csv-dir",
        default="./app/marketing/si_mapping/db",
        help="CSV 파일 디렉토리",
    )
    parser.add_argument("--dummy-count", type=int, default=500, help="더미 기업 수")
    parser.add_argument("--force", action="store_true", help="기존 데이터 삭제 후 재삽입")
    args = parser.parse_args()

    asyncio.run(main(csv_dir=args.csv_dir, dummy_count=args.dummy_count, force=args.force))
