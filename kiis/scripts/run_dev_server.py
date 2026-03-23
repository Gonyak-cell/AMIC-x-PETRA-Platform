from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

default_db_path = PROJECT_ROOT / "generated" / "kiis_dev.db"
default_db_path.parent.mkdir(parents=True, exist_ok=True)

os.environ["ENV"] = os.environ.get("KIIS_ENV", "local")
os.environ["DEBUG"] = os.environ.get("KIIS_DEBUG", "true")
os.environ["AUTH_ENABLED"] = os.environ.get("KIIS_AUTH_ENABLED", "false")
os.environ["SCHEDULER_ENABLED"] = os.environ.get("KIIS_SCHEDULER_ENABLED", "false")
os.environ["SECRET_KEY"] = os.environ.get("KIIS_SECRET_KEY", "kiis-local-dev-secret")
os.environ["JWT_SECRET"] = os.environ.get("KIIS_JWT_SECRET", "kiis-local-dev-jwt-secret")
os.environ["DATABASE_URL"] = os.environ.get(
    "KIIS_DATABASE_URL",
    f"sqlite+aiosqlite:///{default_db_path.as_posix()}",
)
os.environ["ELASTICSEARCH_URL"] = os.environ.get("KIIS_ELASTICSEARCH_URL", "")
os.environ["LOG_DIR"] = os.environ.get("KIIS_LOG_DIR", str(REPO_ROOT / "logs"))

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "CHAR(36)"
SQLiteTypeCompiler.visit_Uuid = lambda self, type_, **kw: "CHAR(36)"


async def _bootstrap_database() -> None:
    from app.core.database import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def main() -> None:
    asyncio.run(_bootstrap_database())

    import uvicorn

    host = os.environ.get("KIIS_HOST", "127.0.0.1")
    port = int(os.environ.get("KIIS_PORT", "8001"))
    reload_enabled = os.environ.get("KIIS_RELOAD", "true").lower() == "true"
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
