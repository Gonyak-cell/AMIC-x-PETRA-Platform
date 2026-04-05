from __future__ import annotations

import argparse
import asyncio
import json
import logging

from app.core.attachment_upload_runtime_diagnostics import build_attachment_upload_runtime_diagnostics
from app.core.config import settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose TM attachment upload migration/schema state.")
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit with status 1 when attachment upload migration/schema drift is detected.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of pretty JSON.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    diagnostics = await build_attachment_upload_runtime_diagnostics(
        database_url=settings.DATABASE_URL,
        logger=logging.getLogger(__name__),
    )
    print(
        json.dumps(
            diagnostics,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    if args.fail_on_drift and not diagnostics["overall_ok"]:
        return 1
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
