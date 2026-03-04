"""템플릿 레지스트리 — 마스터 PPTX 템플릿 경로 관리.

(doc_type, variant) 조합으로 마스터 템플릿을 선택한다.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# im/ 디렉토리 기준 상대 경로
_IM_ROOT = Path(__file__).resolve().parent.parent.parent  # im/

# ── 마스터 템플릿 레지스트리 ──────────────────────────────────────────────────

_TEMPLATE_REGISTRY: dict[tuple[str, str], str] = {
    # TM (Teaser Memo)
    ("TM", "default"): "templates/SPICY - TM - 260219 vSHARE.pptx",
    ("TM", "andersen"): "templates/SWITCH - TM - 260119.pptx",
    # DM (Discussion Memo)
    ("DM", "market_analysis"): "templates/NX3 Games - DM - 260116.pptx",
    ("DM", "deal_structure"): "templates/YTN - Structure DM - 260116.pptx",
    ("DM", "default"): "templates/NX3 Games - DM - 260116.pptx",
}

# TEASER → TM 별칭
_STYLE_ALIASES: dict[str, str] = {
    "TEASER": "TM",
}


def get_template_path(
    doc_type: str,
    variant: str = "default",
) -> Path:
    """마스터 템플릿의 절대 경로를 반환한다.

    Args:
        doc_type: "TM", "TEASER", "DM" 등.
        variant: 템플릿 변형. "default", "andersen", "market_analysis", "deal_structure".

    Returns:
        마스터 템플릿 절대 경로.

    Raises:
        FileNotFoundError: 템플릿 파일이 존재하지 않을 때.
        KeyError: 등록되지 않은 (doc_type, variant) 조합일 때.
    """
    # 별칭 해석
    resolved_type = _STYLE_ALIASES.get(doc_type.upper(), doc_type.upper())

    key = (resolved_type, variant)
    rel_path = _TEMPLATE_REGISTRY.get(key)

    # variant가 없으면 default 폴백
    if rel_path is None and variant != "default":
        key = (resolved_type, "default")
        rel_path = _TEMPLATE_REGISTRY.get(key)
        if rel_path is not None:
            logger.info(
                "템플릿 variant %r 없음 → default 사용: %s",
                variant,
                rel_path,
            )

    if rel_path is None:
        raise KeyError(
            f"등록된 템플릿 없음: doc_type={doc_type!r}, variant={variant!r}. "
            f"등록된 키: {list(_TEMPLATE_REGISTRY.keys())}"
        )

    abs_path = _IM_ROOT / rel_path
    if not abs_path.exists():
        raise FileNotFoundError(f"마스터 템플릿 파일 없음: {abs_path}")

    return abs_path


def list_templates() -> dict[tuple[str, str], Path]:
    """등록된 모든 템플릿의 (key, 절대경로) 매핑을 반환한다."""
    result: dict[tuple[str, str], Path] = {}
    for key, rel_path in _TEMPLATE_REGISTRY.items():
        abs_path = _IM_ROOT / rel_path
        result[key] = abs_path
    return result


def get_available_variants(doc_type: str) -> list[str]:
    """특정 문서 유형에 사용 가능한 variant 목록을 반환한다."""
    resolved_type = _STYLE_ALIASES.get(doc_type.upper(), doc_type.upper())
    return [
        variant for (dtype, variant) in _TEMPLATE_REGISTRY if dtype == resolved_type
    ]
