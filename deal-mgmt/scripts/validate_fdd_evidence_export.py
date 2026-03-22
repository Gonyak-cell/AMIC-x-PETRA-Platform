"""Validate a normalized FDD evidence export payload.

Usage examples:
  python scripts/validate_fdd_evidence_export.py --deal-id <uuid>
  python scripts/validate_fdd_evidence_export.py --input-json path/to/export.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.schemas.evidence import ArtifactEvidenceImportRequest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate an FDD evidence export payload.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--deal-id", type=UUID, help="FDD deal UUID to fetch from the configured FDD service.")
    group.add_argument("--input-json", type=Path, help="Local JSON file containing the export payload.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds when fetching from the FDD service.",
    )
    return parser


def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json:
        return json.loads(args.input_json.read_text(encoding="utf-8"))

    url = f"{settings.FDD_API_URL}{settings.FDD_EVIDENCE_EXPORT_PATH_TEMPLATE.format(deal_id=args.deal_id)}"
    with httpx.Client(timeout=args.timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        payload = _load_payload(args)
        normalized = ArtifactEvidenceImportRequest.model_validate(payload)
    except FileNotFoundError as exc:
        print(f"[ERROR] JSON file not found: {exc}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"[ERROR] Failed to fetch FDD evidence export: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON payload: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print("[ERROR] Payload failed schema validation:", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1

    summary = {
        "artifact_type": normalized.artifact_type,
        "default_workstream": normalized.default_workstream,
        "artifact_id": str(normalized.artifact_id) if normalized.artifact_id else None,
        "external_artifact_ref": normalized.external_artifact_ref,
        "record_count": len(normalized.records),
        "manual_review_count": sum(1 for record in normalized.records if record.requires_manual_review),
        "unresolved_count": sum(1 for record in normalized.records if record.is_unresolved_reference),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
