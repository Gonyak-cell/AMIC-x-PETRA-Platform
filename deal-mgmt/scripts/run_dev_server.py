from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

default_db_path = PROJECT_ROOT / "generated" / "deal_mgmt_dev.db"
default_db_path.parent.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("ENV", "local")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("SECRET_KEY", "deal-mgmt-local-dev-secret")
os.environ.setdefault("JWT_SECRET", "deal-mgmt-local-dev-jwt-secret")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{default_db_path.as_posix()}")
os.environ.setdefault("LOG_DIR", str(REPO_ROOT / "logs"))

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "CHAR(36)"


async def _bootstrap_database() -> None:
    import app.main  # noqa: F401
    from app.core.database import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def main() -> None:
    asyncio.run(_bootstrap_database())

    import uvicorn

    host = os.environ.get("DEAL_MGMT_HOST", "127.0.0.1")
    port = int(os.environ.get("DEAL_MGMT_PORT", "8000"))
    reload_enabled = os.environ.get("DEAL_MGMT_RELOAD", "true").lower() == "true"
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
