from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.local_dev_schema_guard import (
    configure_sqlite_type_compilers_for_local_dev,
)
from app.core.local_dev_schema_guard import (
    get_local_dev_rebuild_reason as _shared_get_local_dev_rebuild_reason,
)
from app.core.local_dev_schema_guard import (
    rebuild_local_dev_database_if_needed as _shared_rebuild_local_dev_database_if_needed,
)

logger = logging.getLogger(__name__)


def _configure_dev_stdio() -> None:
    """Keep local Windows consoles from crashing on Korean warning logs."""

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


_configure_dev_stdio()

default_db_path = PROJECT_ROOT / "generated" / "deal_mgmt_dev.db"
default_db_path.parent.mkdir(parents=True, exist_ok=True)

REQUIRED_MARKETING_MATERIAL_COLUMNS = frozenset({"source_mode", "attachment_id"})
REQUIRED_ATTACHMENT_COLUMNS = frozenset({"processing_status", "processing_error"})

os.environ.setdefault("ENV", "local")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("SECRET_KEY", "deal-mgmt-local-dev-secret")
os.environ.setdefault("JWT_SECRET", "deal-mgmt-local-dev-jwt-secret")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{default_db_path.as_posix()}")
os.environ.setdefault("LOG_DIR", str(REPO_ROOT / "logs"))

configure_sqlite_type_compilers_for_local_dev()


def _get_local_dev_rebuild_reason(db_path: Path) -> str | None:
    return _shared_get_local_dev_rebuild_reason(db_path)


def _rebuild_local_dev_database_if_needed(db_path: Path) -> None:
    _shared_rebuild_local_dev_database_if_needed(db_path, logger=logger)


def _repair_legacy_nda_schema(db_path: Path) -> None:
    """Repair local SQLite NDA schema drift for dev databases created via create_all."""

    if not db_path.exists():
        return

    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'",
            ).fetchall()
        }
        if "ndas" not in tables:
            return

        columns = {row[1]: row for row in conn.execute("PRAGMA table_info(ndas)").fetchall()}
        buyer_candidate = columns.get("buyer_candidate_id")
        buyer_candidate_not_null = bool(buyer_candidate and buyer_candidate[3])
        needs_rebuild = "party_type" not in columns or buyer_candidate_not_null
        if not needs_rebuild:
            return

        logger.info("Repairing legacy SQLite NDA schema: %s", db_path)
        select_map = {
            "id": "id",
            "transaction_id": "transaction_id",
            "party_type": "party_type" if "party_type" in columns else "'BUYER' AS party_type",
            "buyer_candidate_id": "buyer_candidate_id",
            "nda_type": "nda_type",
            "status": "status",
            "sent_at": "sent_at",
            "signed_at": "signed_at",
            "expires_at": "expires_at",
            "document_url": "document_url",
            "notes": "notes",
            "counterparty_name": (
                "counterparty_name" if "counterparty_name" in columns else "NULL AS counterparty_name"
            ),
            "jurisdiction": ("jurisdiction" if "jurisdiction" in columns else "NULL AS jurisdiction"),
            "confidentiality_period_months": (
                "confidentiality_period_months"
                if "confidentiality_period_months" in columns
                else "NULL AS confidentiality_period_months"
            ),
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
        insert_columns = ", ".join(select_map.keys())
        select_columns = ", ".join(select_map.values())

        foreign_keys_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.execute("PRAGMA foreign_keys=OFF")
        with conn:
            conn.execute("DROP TABLE IF EXISTS ndas__legacy")
            conn.execute("ALTER TABLE ndas RENAME TO ndas__legacy")
            conn.execute(
                """
                CREATE TABLE ndas (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    transaction_id CHAR(32) NOT NULL REFERENCES transactions (id),
                    party_type VARCHAR(6) NOT NULL DEFAULT 'BUYER',
                    buyer_candidate_id CHAR(32) REFERENCES buyer_candidates (id),
                    nda_type VARCHAR(7) NOT NULL DEFAULT 'MUTUAL',
                    status VARCHAR(8) NOT NULL DEFAULT 'DRAFT',
                    sent_at VARCHAR(10),
                    signed_at VARCHAR(10),
                    expires_at VARCHAR(10),
                    document_url VARCHAR(500),
                    notes TEXT,
                    counterparty_name VARCHAR(200),
                    jurisdiction VARCHAR(200),
                    confidentiality_period_months INTEGER,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
            )
            conn.execute(
                f"""
                INSERT INTO ndas ({insert_columns})
                SELECT {select_columns}
                FROM ndas__legacy
                """,
            )
            conn.execute("DROP TABLE ndas__legacy")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_ndas_transaction_id ON ndas (transaction_id)",
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_ndas_buyer_candidate_id ON ndas (buyer_candidate_id)",
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_ndas_party_type ON ndas (party_type)",
            )

        conn.execute(f"PRAGMA foreign_keys={1 if foreign_keys_enabled else 0}")
    finally:
        conn.close()


async def _bootstrap_database() -> None:
    _rebuild_local_dev_database_if_needed(default_db_path)
    _repair_legacy_nda_schema(default_db_path)

    import app.main
    from app.core.database import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _resolve_reload_enabled(
    platform_name: str | None = None,
    configured_value: str | None = None,
) -> bool:
    effective_os_name = platform_name or os.name
    default_reload = "false" if effective_os_name == "nt" else "true"
    raw_value = configured_value
    if raw_value is None:
        raw_value = os.environ.get("DEAL_MGMT_RELOAD", default_reload)
    return raw_value.lower() == "true"


def main() -> None:
    asyncio.run(_bootstrap_database())

    import uvicorn

    host = os.environ.get("DEAL_MGMT_HOST", "127.0.0.1")
    port = int(os.environ.get("DEAL_MGMT_PORT", "8000"))
    # Windows + watchfiles + our mirrored workspace setup causes noisy reload loops in local dev.
    reload_enabled = _resolve_reload_enabled()
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
