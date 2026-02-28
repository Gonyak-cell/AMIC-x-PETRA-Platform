"""DART 데이터 파싱 공유 유틸리티.

HoldingSignalService / ElestockSignalService에서 공통으로 사용하는
문자열 → 날짜/숫자 변환, corp_code 조회 헬퍼, 동기화 결과 dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


@dataclass
class DartSyncResult:
    """DART 동기화 + 딜 신호 생성 공통 결과."""

    total_fetched: int = 0
    new_records: int = 0
    updated_records: int = 0
    deals_created: int = 0
    errors: list[str] = field(default_factory=list)


def parse_float(value: str | None) -> float | None:
    """DART 문자열을 float로 변환한다."""
    if not value or value.strip() in ("", "-"):
        return None
    try:
        return float(value.strip().replace(",", ""))
    except ValueError:
        return None


def parse_date(yyyymmdd: str | None) -> date | None:
    """YYYYMMDD 문자열을 date로 변환한다."""
    if not yyyymmdd or len(yyyymmdd) < 8:
        return None
    try:
        return date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]))
    except (ValueError, IndexError):
        return None


def parse_year(yyyymmdd: str | None) -> int | None:
    """YYYYMMDD에서 연도를 추출한다."""
    if not yyyymmdd or len(yyyymmdd) < 4:
        return None
    try:
        return int(yyyymmdd[:4])
    except ValueError:
        return None


def is_acquisition(report_resn: str | None, keywords: tuple[str, ...]) -> bool:
    """보고사유에 취득 관련 키워드가 포함되었는지 확인한다."""
    if not report_resn:
        return False
    return any(kw in report_resn for kw in keywords)


async def resolve_company_by_corp_code(
    db: AsyncSession,
    corp_code: str,
) -> int | None:
    """corp_code로 Company ID를 조회한다."""
    stmt = select(Company.id).where(Company.corp_code == corp_code)
    db_result = await db.execute(stmt)
    return db_result.scalar_one_or_none()
