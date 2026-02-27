"""기업개황 CSV → si_companies 테이블 고속 적재(Seeding) 스크립트.

industry_master_dict.csv (1,574건 업종명→KSIC 매핑 사전)를 메모리에 로드한 뒤,
20개 기업개황 CSV 파일을 순회하며 PostgreSQL si_companies 테이블에 UPSERT 적재한다.

사용법:
    cd deal-mgmt
    python -m scripts.seed_company_data [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import logging
import re
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
SI_CSV_DIR = BASE_DIR / "app" / "marketing" / "si_list" / "csv"
MASTER_DICT_CSV = BASE_DIR / "app" / "marketing" / "si_mapping" / "db" / "industry_master_dict.csv"
IO_KSIC_MAPPING_CSV = BASE_DIR / "app" / "marketing" / "si_mapping" / "db" / "io_ksic_mapping.csv"

CHUNK_SIZE = 5000


# ---------------------------------------------------------------------------
# 0단계: IO-KSIC 매핑 테이블의 KSIC 코드 풀 로드
# ---------------------------------------------------------------------------
def _load_io_ksic_pool() -> set[str]:
    """io_ksic_mapping.csv에서 고유 KSIC 코드 집합을 로드한다."""
    if not IO_KSIC_MAPPING_CSV.exists():
        logger.warning("io_ksic_mapping.csv 없음: %s", IO_KSIC_MAPPING_CSV)
        return set()
    io_df = pd.read_csv(IO_KSIC_MAPPING_CSV, dtype=str, encoding="utf-8-sig")
    pool = set(io_df["ksic_code"].dropna().str.strip())
    logger.info("IO-KSIC 코드 풀 로드: %d개 고유 코드", len(pool))
    if not pool:
        logger.error("IO-KSIC 코드 풀이 비어 있음 — 접두사 역매핑 불가, 원본 코드로 저장됩니다")
    return pool


# ---------------------------------------------------------------------------
# 1단계: 마스터 사전 메모리 로드
# ---------------------------------------------------------------------------
def load_master_dict() -> dict[str, list[str]]:
    """industry_master_dict.csv를 읽어 {원본_업종명: [KSIC코드,...]} dict를 생성한다.

    5자리 코드 우선. 4자리 이하 코드는 io_ksic_mapping에서 접두사 역매핑하여
    실제 매핑 테이블에 존재하는 코드로 확장한다.

    NOTE: 접두사 확장은 적재 시점(여기)과 조회 시점(si_mapping_service._lookup_by_ksic)
    양쪽에서 수행된다. 적재 시점에서 가능한 한 정확한 5자리 코드로 정규화하고,
    조회 시점에서 나머지 자릿수 불일치를 접두사 매칭으로 보완하는 2중 안전망 설계.
    """
    io_ksic_pool = _load_io_ksic_pool()

    df = pd.read_csv(MASTER_DICT_CSV, dtype=str, encoding="utf-8-sig")
    logger.info("마스터 사전 로드: %d건", len(df))

    mapping: dict[str, list[str]] = {}
    for _, row in df.iterrows():
        name = str(row["원본_업종명"]).strip()
        if not name:
            continue
        code_5 = str(row.get("KSIC_코드_5자리", "")).strip()
        code_4 = str(row.get("KSIC_코드_4자리", "")).strip()

        # 5자리 코드 우선
        if code_5 and code_5 != "nan" and len(code_5) >= 5:
            if code_5 in io_ksic_pool:
                mapping[name] = [code_5]
                continue
            # 접두사 역매핑 (5자리로 시작하는 더 긴 코드 찾기)
            expanded = [c for c in io_ksic_pool if c.startswith(code_5)]
            if expanded:
                mapping[name] = expanded
                continue
            # io_mapping에 없어도 원본 코드 유지 (서비스 레이어 접두사 매칭이 처리)
            mapping[name] = [code_5]
            continue

        # 4자리 이하 fallback → 접두사 역매핑
        code = code_4 if code_4 and code_4 != "nan" else None
        if code:
            expanded = [c for c in io_ksic_pool if c.startswith(code)]
            if expanded:
                mapping[name] = expanded
            else:
                mapping[name] = [code]

    logger.info("마스터 사전 매핑 엔트리: %d건", len(mapping))
    return mapping


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------
def strip_to_digits(value: str, max_len: int) -> str | None:
    """문자열에서 숫자만 추출하여 max_len 자리까지 반환한다."""
    if not value or pd.isna(value):
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits[:max_len] if digits else None


# ---------------------------------------------------------------------------
# 2~3단계: CSV 순회 + 전처리
# ---------------------------------------------------------------------------
def process_csv_files(
    master_dict: dict[str, list[str]],
) -> tuple[list[dict], int, int, int, list[str]]:
    """기업개황 CSV를 순회하며 DB 삽입용 레코드 리스트를 생성한다.

    반환: (records, total_rows, mapped_count, total_csv_files, failed_files)
    """
    csv_files = sorted(glob.glob(str(SI_CSV_DIR / "*.csv")))
    logger.info("[Step 2] CSV 파일 %d개 발견: %s", len(csv_files), SI_CSV_DIR)

    all_records: list[dict] = []
    seen_jurir: set[str] = set()  # 메모리 내 중복 제거
    total_rows = 0
    mapped_count = 0
    failed_files: list[str] = []

    for csv_path in csv_files:
        fname = Path(csv_path).name
        try:
            df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
        except Exception as exc:
            logger.warning("  파일 읽기 실패: %s — %s", fname, exc)
            failed_files.append(fname)
            continue

        # 법인등록번호 결측 행 Drop
        df = df.dropna(subset=["법인등록번호"])
        total_rows += len(df)
        file_new = 0

        for _, row in df.iterrows():
            jurir_no = strip_to_digits(row["법인등록번호"], 13)
            if not jurir_no or len(jurir_no) < 6:
                continue  # 유효하지 않은 법인등록번호

            # 메모리 내 중복 제거 (파일 간 동일 기업)
            if jurir_no in seen_jurir:
                continue
            seen_jurir.add(jurir_no)

            # 업종명 → KSIC 코드 매핑 (접두사 역매핑 적용)
            industry_name = str(row.get("업종명", "")).strip()
            ksic_codes = master_dict.get(industry_name, [])
            if ksic_codes:
                mapped_count += 1

            record = {
                "id": uuid.uuid4(),
                "company_name": str(row.get("회사이름", "")).strip() or "Unknown",
                "jurir_no": jurir_no,
                "corp_code": strip_to_digits(row.get("사업자등록번호", ""), 10),
                "ksic_codes": ksic_codes,
                "revenue": None,
                "has_investment_history": False,
                "description": None,
            }
            all_records.append(record)
            file_new += 1

        logger.info("  %s: %d행 → 신규 %d건", fname, len(df), file_new)

    logger.info(
        "[Step 3] 전처리 완료: 총 CSV 행 %d → 고유 기업 %d건 (KSIC 매핑 %d건)",
        total_rows,
        len(all_records),
        mapped_count,
    )
    return all_records, total_rows, mapped_count, len(csv_files), failed_files


# ---------------------------------------------------------------------------
# 4단계: UPSERT 벌크 삽입
# ---------------------------------------------------------------------------
async def upsert_companies(
    session: AsyncSession,
    records: list[dict],
    force: bool = False,
) -> int:
    """si_companies 테이블에 UPSERT(on_conflict_do_nothing) 방식으로 벌크 삽입한다."""
    from app.models.si_company import SICompany

    if force:
        # 실제 기업(jurir_no 있는 것)만 삭제, 더미 기업은 유지
        result = await session.execute(delete(SICompany).where(SICompany.jurir_no.isnot(None)))
        await session.commit()
        logger.info("기존 실제 기업 데이터 삭제: %d건", result.rowcount)

    if not records:
        logger.warning("삽입할 레코드가 없습니다.")
        return 0

    inserted = 0
    for i in range(0, len(records), CHUNK_SIZE):
        chunk = records[i : i + CHUNK_SIZE]
        stmt = pg_insert(SICompany).values(chunk)
        stmt = stmt.on_conflict_do_nothing(index_elements=["jurir_no"])
        result = await session.execute(stmt)
        inserted += result.rowcount
        logger.info(
            "[Step 4] 청크 %d~%d: %d건 삽입 (누적 %d)",
            i,
            min(i + CHUNK_SIZE, len(records)),
            result.rowcount,
            inserted,
        )

    await session.commit()
    return inserted


# ---------------------------------------------------------------------------
# 5단계: 메인 실행
# ---------------------------------------------------------------------------
async def main(force: bool = False) -> None:
    """적재 파이프라인 메인."""
    print("=" * 60)
    print("  기업개황 → si_companies DB 고속 적재 (UPSERT)")
    print("=" * 60)

    # 1단계: 마스터 사전 로드
    master_dict = load_master_dict()

    # 2~3단계: CSV 순회 + 전처리
    records, total_rows, mapped_count, total_csv_files, failed_files = process_csv_files(master_dict)

    if not records:
        logger.error("적재할 레코드가 없습니다. 종료.")
        return

    # 4단계: DB 연결 + UPSERT
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        inserted = await upsert_companies(session, records, force)

        # 최종 카운트 확인
        db_count = (
            await session.execute(text("SELECT COUNT(*) FROM si_companies WHERE jurir_no IS NOT NULL"))
        ).scalar()

    await engine.dispose()

    # 5단계: 결과 리포트
    print("\n" + "=" * 60)
    print("  적재 완료 리포트")
    print("=" * 60)
    print(f"  처리 CSV 파일: {total_csv_files - len(failed_files)}/{total_csv_files}개")
    print(f"  총 CSV 행: {total_rows:,}")
    print(f"  고유 기업 (중복 제거): {len(records):,}")
    print(f"  KSIC 매핑 성공: {mapped_count:,} ({mapped_count / len(records) * 100:.1f}%)")
    print(f"  DB 삽입: {inserted:,}건")
    print(f"  DB 실제 기업 총계: {db_count:,}건")
    if failed_files:
        print(f"  실패 파일: {failed_files}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="기업개황 CSV → si_companies DB 적재")
    parser.add_argument("--force", action="store_true", help="기존 실제 기업 삭제 후 재삽입")
    args = parser.parse_args()

    asyncio.run(main(force=args.force))
