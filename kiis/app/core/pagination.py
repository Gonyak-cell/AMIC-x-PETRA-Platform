"""페이지네이션 공통 유틸리티.

KIIS 전체 라우터에서 반복되는 page/size → offset 계산, 총 건수 쿼리,
결과 조립 로직을 통합한다.
"""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginationParams:
    """FastAPI Depends()로 주입 가능한 페이지네이션 파라미터.

    Usage::

        @router.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends(),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="페이지 번호"),
        size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    ):
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


async def paginate(
    db: AsyncSession,
    query: Select,
    params: PaginationParams,
) -> tuple[list[Any], int]:
    """쿼리에 페이지네이션을 적용하고 (rows, total) 튜플을 반환한다.

    Args:
        db: 비동기 DB 세션
        query: 필터가 적용된 SELECT 문 (ORDER BY 포함 권장)
        params: 페이지네이션 파라미터

    Returns:
        (rows, total) — rows는 query 결과, total은 전체 건수
    """
    # 총 건수
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 페이지네이션 적용
    paginated = query.offset(params.offset).limit(params.size)
    result = await db.execute(paginated)
    rows = result.all()

    return rows, total
