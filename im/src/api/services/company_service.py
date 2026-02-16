"""Company 서비스 레이어 (T-I18).

> 마지막 수정: 2026-02-10 23:30:00

기업 데이터 fetch/캐시 조회 비즈니스 로직.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.company import Company
from src.api.exceptions import NotFoundError


class CompanyService:
    """Company 관련 비즈니스 로직."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def fetch_company(self, corp_code: str) -> Company:
        """기업 데이터 수집을 시작한다 (upsert + Celery dispatch).

        Args:
            corp_code: 법인 코드.

        Returns:
            Company 인스턴스 (PENDING 상태).
        """
        from src.api.tasks.fetch_company import fetch_company_task

        result = await self.db.execute(
            select(Company).where(Company.corp_code == corp_code)
        )
        company = result.scalar_one_or_none()

        if company is None:
            company = Company(
                corp_code=corp_code,
                corp_name="",
                fetch_status="PENDING",
            )
            self.db.add(company)
        else:
            company.fetch_status = "PENDING"

        await self.db.commit()
        await self.db.refresh(company)

        task = fetch_company_task.delay(corp_code)
        company.fetch_task_id = task.id
        await self.db.commit()
        await self.db.refresh(company)

        return company

    async def get_company(self, corp_code: str) -> Company:
        """기업 데이터를 조회한다 (캐시 만료 시 자동 재수집).

        Args:
            corp_code: 법인 코드.

        Returns:
            Company 인스턴스.

        Raises:
            NotFoundError: 기업 데이터가 없을 때.
        """
        from src.api.tasks.fetch_company import fetch_company_task

        result = await self.db.execute(
            select(Company).where(Company.corp_code == corp_code)
        )
        company = result.scalar_one_or_none()

        if company is None:
            raise NotFoundError("Company", corp_code)

        # 캐시 만료 체크 → 백그라운드 재수집
        now = datetime.now(timezone.utc)
        if (
            company.cache_expires_at is not None
            and company.cache_expires_at < now
            and company.fetch_status != "PENDING"
        ):
            task = fetch_company_task.delay(corp_code)
            company.fetch_status = "REFRESHING"
            company.fetch_task_id = task.id
            await self.db.commit()
            await self.db.refresh(company)

        return company
