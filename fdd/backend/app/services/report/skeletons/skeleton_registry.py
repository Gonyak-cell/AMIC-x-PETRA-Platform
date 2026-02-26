"""YAML 스켈레톤 로더 + LineItemDef 변환.

YAML 파일에서 재무제표 행 구조를 로드하고,
multiperiod_engine이 사용하는 LineItemDef 리스트로 변환한다.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

from app.engines.multiperiod_engine import LineItemDef

_SKELETON_DIR = Path(__file__).parent

# 지원되는 스켈레톤 파일
_SKELETON_FILES: dict[str, str] = {
    "IS": "is_skeleton.yaml",
    "BS": "bs_skeleton.yaml",
    "CF": "cf_skeleton.yaml",
}


@functools.lru_cache(maxsize=8)
def load_skeleton(statement_type: str) -> dict[str, Any]:
    """YAML 스켈레톤 파일을 로드한다.

    Args:
        statement_type: "IS" | "BS" | "CF"

    Returns:
        파싱된 YAML 딕셔너리

    Raises:
        FileNotFoundError: 스켈레톤 파일이 없을 때
        ValueError: 잘못된 statement_type
    """
    filename = _SKELETON_FILES.get(statement_type)
    if not filename:
        raise ValueError(
            f"Unknown statement_type: {statement_type}. "
            f"Supported: {list(_SKELETON_FILES.keys())}"
        )

    filepath = _SKELETON_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Skeleton file not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        return yaml.safe_load(f)


def skeleton_to_line_item_defs(
    statement_type: str,
    *,
    industry: str | None = None,
) -> list[LineItemDef]:
    """스켈레톤에서 LineItemDef 리스트를 생성한다.

    Args:
        statement_type: "IS" | "BS" | "CF"
        industry: 산업 식별자 (예: "manufacturing", "tech")
            None이면 기본 행 구조만 사용.

    Returns:
        display_order 순서의 LineItemDef 리스트
    """
    skeleton = load_skeleton(statement_type)
    defs: list[LineItemDef] = []
    order = 0

    for section in skeleton.get("sections", []):
        for row in section.get("rows", []):
            order += 10  # 10 단위로 간격 (삽입 여유)
            parent_code = _infer_parent_code(row, section)

            defs.append(
                LineItemDef(
                    code=row["code"],
                    name_ko=row["label_ko"],
                    name_en=row["label_en"],
                    category=row.get("category", ""),
                    statement_type=statement_type,
                    display_order=order,
                    parent_code=parent_code,
                    is_subtotal=row.get("is_subtotal", False),
                )
            )

    # 산업별 확장 행 삽입
    if industry:
        defs = _apply_industry_extensions(defs, skeleton, industry, statement_type)

    return defs


def get_validation_rules(statement_type: str) -> list[dict[str, str]]:
    """스켈레톤의 교차검증 규칙을 반환한다."""
    skeleton = load_skeleton(statement_type)
    return skeleton.get("validation", [])


def get_skeleton_title(statement_type: str) -> tuple[str, str]:
    """스켈레톤 제목 (ko, en)을 반환한다."""
    skeleton = load_skeleton(statement_type)
    return skeleton.get("title_ko", ""), skeleton.get("title_en", "")


def _infer_parent_code(
    row: dict[str, Any],
    section: dict[str, Any],
) -> str | None:
    """소계 행의 parent_code를 추론한다.

    is_subtotal=true이고 formula가 있으면,
    해당 섹션의 비-소계 행들이 하위 항목.
    """
    if row.get("is_subtotal"):
        return None  # 소계 행 자체는 parent가 없음

    # 같은 section 내 소계 행을 찾아 parent로 설정
    for other_row in section.get("rows", []):
        if other_row.get("is_subtotal") and other_row["code"] != row["code"]:
            return other_row["code"]

    return None


def _apply_industry_extensions(
    defs: list[LineItemDef],
    skeleton: dict[str, Any],
    industry: str,
    statement_type: str,
) -> list[LineItemDef]:
    """산업별 확장 행을 적절한 위치에 삽입한다."""
    extensions = skeleton.get("industry_extensions", {})
    ext_config = extensions.get(industry)

    if not ext_config:
        return defs

    insert_after = ext_config.get("insert_after")
    ext_rows = ext_config.get("rows", [])

    if not insert_after or not ext_rows:
        return defs

    # 삽입 위치 찾기
    insert_idx = None
    insert_order = 0
    for i, d in enumerate(defs):
        if d.code == insert_after:
            insert_idx = i + 1
            insert_order = d.display_order
            break

    if insert_idx is None:
        return defs

    # 확장 행 생성 + 삽입
    new_defs = list(defs)
    for j, row in enumerate(ext_rows):
        ext_def = LineItemDef(
            code=row["code"],
            name_ko=row["label_ko"],
            name_en=row["label_en"],
            category=row.get("category", ""),
            statement_type=statement_type,
            display_order=insert_order + j + 1,
            parent_code=insert_after,
            is_subtotal=row.get("is_subtotal", False),
        )
        new_defs.insert(insert_idx + j, ext_def)

    return new_defs
