"""PRD(Product Requirements Document) 매니저 — 문서 유형별 수용 기준 관리."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PRD_DIR = Path(__file__).resolve().parent / "prds"


def load_prd(doc_type: str) -> dict[str, Any]:
    """문서 유형별 PRD를 로드한다.

    Args:
        doc_type: "ldd_full" | "ldd_redflag" | "tm" | "dm" | "im"

    Returns:
        PRD 딕셔너리 (sections, acceptance_criteria 등)
    """
    prd_path = _PRD_DIR / f"{doc_type.lower()}.json"
    if not prd_path.exists():
        # 빈 PRD 반환 (파일이 없어도 동작 가능)
        return {"name": doc_type, "sections": {}, "pass_threshold": 4.0}
    return json.loads(prd_path.read_text(encoding="utf-8"))


def get_section_criteria(prd: dict[str, Any], section_id: str) -> dict[str, Any]:
    """PRD에서 특정 섹션의 수용 기준을 반환한다."""
    for section in prd.get("sections", []):
        if section.get("id") == section_id:
            return section
    return {}


def check_section_passed(prd: dict[str, Any], section_id: str) -> bool:
    """PRD에서 특정 섹션이 통과 상태인지 확인한다."""
    section = get_section_criteria(prd, section_id)
    return section.get("passes", False)


def mark_section_passed(prd: dict[str, Any], section_id: str) -> dict[str, Any]:
    """PRD에서 특정 섹션을 통과 상태로 마킹한다."""
    for section in prd.get("sections", []):
        if section.get("id") == section_id:
            section["passes"] = True
            break
    return prd
