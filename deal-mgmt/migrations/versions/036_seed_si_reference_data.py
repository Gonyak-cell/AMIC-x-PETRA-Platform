"""SI 매핑 참조 데이터 시딩 — CSV 파일에서 DB로 자동 삽입.

io_sectors, ksic_io_mappings, io_transactions, ksic_classifications, si_companies(더미)를
CSV 파일에서 읽어 DB에 삽입한다. 이미 데이터가 있으면 스킵(idempotent).

Revision ID: 036
Revises: 035
"""

from __future__ import annotations

import csv
import itertools
import json
import logging
import random
import uuid
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)

# CSV 디렉토리: migrations/versions/ → migrations/ → deal-mgmt/ → app/marketing/si_mapping/db/
_CSV_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "marketing" / "si_mapping" / "db"
_CHUNK = 5000

# ── SA table 참조 (ORM 없이 사용) ──────────────────────────
_io_sectors = sa.table(
    "io_sectors",
    sa.column("code", sa.String),
    sa.column("name", sa.String),
)

_ksic_io_mappings = sa.table(
    "ksic_io_mappings",
    sa.column("io_code", sa.String),
    sa.column("io_name", sa.String),
    sa.column("ksic_code", sa.String),
    sa.column("ksic_name", sa.String),
)

_io_transactions = sa.table(
    "io_transactions",
    sa.column("source_io_code", sa.String),
    sa.column("source_io_name", sa.String),
    sa.column("target_io_code", sa.String),
    sa.column("target_io_name", sa.String),
    sa.column("transaction_value", sa.Numeric),
)

_ksic_classifications = sa.table(
    "ksic_classifications",
    sa.column("basic_code", sa.String),
    sa.column("basic_name", sa.String),
    sa.column("sub_code", sa.String),
    sa.column("sub_name", sa.String),
    sa.column("mid_code", sa.String),
    sa.column("mid_name", sa.String),
    sa.column("large_code", sa.String),
    sa.column("large_name", sa.String),
)

_si_companies = sa.table(
    "si_companies",
    sa.column("id", sa.Uuid),
    sa.column("company_name", sa.String),
    sa.column("ksic_codes", sa.JSON),
    sa.column("revenue", sa.Numeric),
    sa.column("has_investment_history", sa.Boolean),
    sa.column("description", sa.Text),
)

# 더미 기업명 풀
_PREFIXES = [
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
]
_SUFFIXES = [
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


def _chunked_insert(conn, table, rows: list[dict]) -> int:
    """rows를 _CHUNK 크기로 나눠 삽입."""
    total = 0
    for i in range(0, len(rows), _CHUNK):
        chunk = rows[i : i + _CHUNK]
        conn.execute(table.insert(), chunk)
        total += len(chunk)
    return total


def _has_data(conn, table_name: str) -> bool:
    return conn.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar() > 0


# ── 1. io_sectors ──────────────────────────────────────────
def _seed_io_sectors(conn, tx_csv: Path) -> int:
    io_codes: dict[str, str] = {}
    with open(tx_csv, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = row["source_io_code"].strip()
            src_name = row.get("source_io_name", "").strip()
            tgt = row["target_io_code"].strip()
            tgt_name = row.get("target_io_name", "").strip()
            if src and src not in io_codes:
                io_codes[src] = src_name
            if tgt and tgt not in io_codes:
                io_codes[tgt] = tgt_name
    rows = [{"code": c, "name": n or c} for c, n in sorted(io_codes.items())]
    return _chunked_insert(conn, _io_sectors, rows)


# ── 2. ksic_io_mappings ───────────────────────────────────
def _seed_ksic_io_mappings(conn, csv_path: Path) -> int:
    rows = []
    seen: set[tuple[str, str]] = set()
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            io_code = row["io_code"].strip()
            ksic_code = row["ksic_code"].strip()
            # 범위 표기(예: "13101sc1-15220sc1(제외)")는 VARCHAR(20) 초과 → 스킵
            if len(ksic_code) > 20 or len(io_code) > 20:
                continue
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
    return _chunked_insert(conn, _ksic_io_mappings, rows)


# ── 3. io_transactions ────────────────────────────────────
def _seed_io_transactions(conn, csv_path: Path) -> int:
    rows = []
    seen: set[tuple[str, str]] = set()
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val_str = row["value"].strip()
            if not val_str:
                continue
            try:
                fval = float(val_str)
            except ValueError:
                continue
            if fval == 0:
                continue
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
    return _chunked_insert(conn, _io_transactions, rows)


# ── 4. ksic_classifications ───────────────────────────────
def _seed_ksic_classifications(conn, csv_path: Path) -> int:
    rows = []
    seen: set[str] = set()
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
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
    return _chunked_insert(conn, _ksic_classifications, rows)


# ── 5. si_companies (더미) ────────────────────────────────
def _seed_dummy_companies(conn, ksic_pool: list[str], n: int = 500) -> int:
    rng = random.Random(42)  # 고정 시드 — 재현성 보장

    max_names = len(_PREFIXES) * len(_SUFFIXES)
    if n > max_names:
        n = max_names

    all_names = [f"{p}{s}" for p, s in itertools.product(_PREFIXES, _SUFFIXES)]
    rng.shuffle(all_names)
    selected = all_names[:n]

    rows = []
    for name in selected:
        k = rng.randint(1, 3)
        codes = rng.sample(ksic_pool, min(k, len(ksic_pool)))
        rows.append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "company_name": name,
                "ksic_codes": json.dumps(codes),
                "revenue": float(rng.randint(100, 10000)) * 1_0000_0000,
                "has_investment_history": rng.choice([True, False]),
                "description": None,
            }
        )
    return _chunked_insert(conn, _si_companies, rows)


# ── upgrade / downgrade ───────────────────────────────────
def upgrade() -> None:
    conn = op.get_bind()

    # 이미 시딩된 경우 스킵 (idempotent)
    if _has_data(conn, "ksic_io_mappings"):
        logger.info("ksic_io_mappings에 데이터 존재 — 시딩 스킵")
        return

    if not _CSV_DIR.exists():
        logger.warning("CSV 디렉토리 없음: %s — 시딩 스킵", _CSV_DIR)
        return

    tx_csv = _CSV_DIR / "transaction_table.csv"
    mapping_csv = _CSV_DIR / "io_ksic_mapping.csv"
    cls_csv = _CSV_DIR / "industry_classification.csv"

    # 필수 CSV 존재 확인
    for p in [tx_csv, mapping_csv]:
        if not p.exists():
            logger.warning("필수 CSV 없음: %s — 시딩 스킵", p)
            return

    # FK 순서: io_sectors → ksic_io_mappings, io_transactions → classifications → companies
    n1 = _seed_io_sectors(conn, tx_csv)
    logger.info("io_sectors: %d건 삽입", n1)

    n2 = _seed_ksic_io_mappings(conn, mapping_csv)
    logger.info("ksic_io_mappings: %d건 삽입", n2)

    n3 = _seed_io_transactions(conn, tx_csv)
    logger.info("io_transactions: %d건 삽입", n3)

    if cls_csv.exists():
        n4 = _seed_ksic_classifications(conn, cls_csv)
        logger.info("ksic_classifications: %d건 삽입", n4)

    # KSIC 코드 풀 추출 → 더미 기업 생성
    result = conn.execute(sa.text("SELECT DISTINCT ksic_code FROM ksic_io_mappings"))
    ksic_pool = [row[0] for row in result]
    if ksic_pool:
        n5 = _seed_dummy_companies(conn, ksic_pool)
        logger.info("si_companies (더미): %d건 삽입", n5)


def downgrade() -> None:
    conn = op.get_bind()
    # FK 역순으로 삭제
    for table in [
        "si_companies",
        "io_transactions",
        "ksic_io_mappings",
        "io_sectors",
        "ksic_classifications",
    ]:
        conn.execute(sa.text(f"DELETE FROM {table}"))
