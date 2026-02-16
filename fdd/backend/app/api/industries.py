"""산업 분류 API — /api/v1/industries/*.

FDD 산업별 템플릿 시스템에서 사용 가능한 산업 목록을 반환한다.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.industry import list_industries

router = APIRouter(prefix="/industries", tags=["industries"])


@router.get("")
def get_industries() -> list[dict[str, str]]:
    """지원 산업 목록을 반환한다.

    Returns:
        [{"id": "general", "name_kr": "일반", "name_en": "General"}, ...]
    """
    return list_industries()
