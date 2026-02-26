"""PEF 등록부 데이터 검색 서비스 (DB 기반).

funds 테이블에서 data_source='pef_registry' 조건으로 검색하며,
fund_gps 테이블과 JOIN하여 Co-GP 정보를 제공한다.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fund import Fund, FundGP
from app.schemas.fund import (
    FundDetailResponse,
    FundItem,
    FundListItem,
    GPInfo,
    GPListItem,
)

logger = logging.getLogger(__name__)


class PEFRegistryService:
    """PEF 등록부 데이터 검색 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_funds(
        self,
        *,
        company_name: str | None = None,
        fund_name: str | None = None,
        fund_types: list[str] | None = None,
        legal_types: list[str] | None = None,
        asset_classes: list[str] | None = None,
        fund_statuses: list[str] | None = None,
        vintage_from: int | None = None,
        vintage_to: int | None = None,
        amount_min: int | None = None,
        amount_max: int | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[FundListItem], int, str | None]:
        """PEF 등록부 펀드를 검색한다.

        Returns:
            (items, total_count, reference_date)
        """
        stmt = (
            select(Fund)
            .options(selectinload(Fund.gp_list))
            .where(Fund.data_source == "pef_registry")
        )

        # 텍스트 검색
        if company_name:
            # GP 이름으로도 검색 (fund_gps 테이블 JOIN)
            gp_fund_ids = (
                select(FundGP.fund_id)
                .where(FundGP.gp_name.ilike(f"%{company_name}%"))
                .scalar_subquery()
            )
            stmt = stmt.where(
                Fund.company_name.ilike(f"%{company_name}%")
                | Fund.id.in_(gp_fund_ids)
            )
        if fund_name:
            stmt = stmt.where(Fund.fund_name.ilike(f"%{fund_name}%"))

        # 다중 선택 필터
        if fund_types:
            stmt = stmt.where(Fund.fund_type.in_(fund_types))
        if legal_types:
            stmt = stmt.where(Fund.legal_type.in_(legal_types))
        if asset_classes:
            stmt = stmt.where(Fund.asset_class.in_(asset_classes))

        # 빈티지 범위
        if vintage_from:
            stmt = stmt.where(Fund.vintage_year >= vintage_from)
        if vintage_to:
            stmt = stmt.where(Fund.vintage_year <= vintage_to)

        # 금액 범위 (억원 → 원)
        if amount_min is not None:
            stmt = stmt.where(Fund.total_amount >= Decimal(amount_min) * Decimal("100000000"))
        if amount_max is not None:
            stmt = stmt.where(Fund.total_amount <= Decimal(amount_max) * Decimal("100000000"))

        # 전체 개수
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # 정렬
        allowed_sorts = {"total_amount", "vintage_year", "fund_name", "company_name"}
        if sort_by and sort_by in allowed_sorts:
            col = getattr(Fund, sort_by)
            stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
        else:
            stmt = stmt.order_by(Fund.total_amount.desc().nullslast())

        # 페이지네이션
        stmt = stmt.offset((page - 1) * size).limit(size)

        result = await self.session.execute(stmt)
        funds = result.scalars().unique().all()

        # reference_date 추출 (첫 번째 레코드에서)
        ref_date = funds[0].reference_date if funds else None

        items = [self._to_fund_list_item(f) for f in funds]
        return items, total, ref_date

    async def get_gp_list(
        self,
        *,
        company_name: str | None = None,
        asset_class: str | None = None,
        sort_by: str = "total_aum",
        sort_order: str = "desc",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[GPListItem], int, str | None]:
        """PEF 등록부 GP별 집계를 반환한다.

        fund_gps 테이블 기준으로 GP별 펀드 수, AUM 등을 집계한다.
        """
        # GP별 집계 쿼리
        stmt = (
            select(
                FundGP.gp_name,
                func.count(Fund.id).label("fund_count"),
                func.sum(Fund.total_amount).label("total_aum"),
                func.min(Fund.vintage_year).label("min_vintage"),
                func.max(Fund.vintage_year).label("max_vintage"),
                func.sum(func.cast(Fund.is_co_gp, type_=func.cast.type)).label("co_gp_count"),
            )
            .join(Fund, FundGP.fund_id == Fund.id)
            .where(Fund.data_source == "pef_registry")
        )

        if company_name:
            stmt = stmt.where(FundGP.gp_name.ilike(f"%{company_name}%"))

        stmt = stmt.group_by(FundGP.gp_name)

        # 실행
        result = await self.session.execute(stmt)
        rows = result.all()

        # Co-GP 카운트를 위해 별도 쿼리 (위의 cast가 DB에 따라 문제될 수 있으므로)
        co_gp_stmt = (
            select(
                FundGP.gp_name,
                func.count(Fund.id).label("co_gp_count"),
            )
            .join(Fund, FundGP.fund_id == Fund.id)
            .where(Fund.data_source == "pef_registry")
            .where(Fund.is_co_gp.is_(True))
        )
        if company_name:
            co_gp_stmt = co_gp_stmt.where(FundGP.gp_name.ilike(f"%{company_name}%"))
        co_gp_stmt = co_gp_stmt.group_by(FundGP.gp_name)

        co_gp_result = await self.session.execute(co_gp_stmt)
        co_gp_map: dict[str, int] = {row.gp_name: row.co_gp_count for row in co_gp_result}

        # reference_date
        ref_stmt = (
            select(Fund.reference_date)
            .where(Fund.data_source == "pef_registry")
            .where(Fund.reference_date.isnot(None))
            .limit(1)
        )
        ref_date = (await self.session.execute(ref_stmt)).scalar_one_or_none()

        gp_items: list[GPListItem] = []
        for row in rows:
            mn_v = row.min_vintage
            mx_v = row.max_vintage
            vintage_range = None
            if mn_v is not None:
                vintage_range = str(mn_v) if mn_v == mx_v else f"{mn_v}~{mx_v}"

            gp_items.append(GPListItem(
                company_name=row.gp_name,
                company_code="",
                fund_count=row.fund_count,
                active_fund_count=row.fund_count,  # PEF 등록부는 모두 active
                total_aum=row.total_aum,
                asset_classes=["pef"],
                vintage_range=vintage_range,
                has_maturity_alert=False,
                data_sources=["pef_registry"],
                is_co_gp_count=co_gp_map.get(row.gp_name, 0),
                pef_fund_count=row.fund_count,
                reference_date=ref_date,
            ))

        # 정렬
        allowed_gp_sorts = {"total_aum", "fund_count", "company_name"}
        if sort_by in allowed_gp_sorts:
            reverse = sort_order != "asc"
            if sort_by == "company_name":
                gp_items.sort(key=lambda g: g.company_name, reverse=reverse)
            else:
                with_val = [g for g in gp_items if getattr(g, sort_by) is not None]
                without_val = [g for g in gp_items if getattr(g, sort_by) is None]
                with_val.sort(key=lambda g: getattr(g, sort_by), reverse=reverse)
                gp_items = with_val + without_val

        total = len(gp_items)

        # 페이지네이션
        start = (page - 1) * size
        gp_items = gp_items[start: start + size]

        return gp_items, total, ref_date

    async def get_fund_detail(self, fund_code: str) -> FundDetailResponse | None:
        """PEF 펀드 상세 정보를 반환한다."""
        stmt = (
            select(Fund)
            .options(selectinload(Fund.gp_list), selectinload(Fund.managers))
            .where(Fund.fund_code == fund_code)
            .where(Fund.data_source == "pef_registry")
        )
        result = await self.session.execute(stmt)
        fund = result.scalar_one_or_none()
        if fund is None:
            return None

        gp_list = [
            GPInfo(gp_name=gp.gp_name, gp_role=gp.gp_role)
            for gp in sorted(fund.gp_list, key=lambda g: g.gp_role)
        ]

        from app.schemas.fund import FundManagerItem

        managers = [
            FundManagerItem(
                manager_name=m.manager_name,
                position=m.position or "",
                role=m.role or "",
                career_years=m.career_years,
                education=m.education or "",
                certifications=m.certifications or "",
                appointed_date=m.appointed_date,
                resigned_date=m.resigned_date,
                is_active=m.is_active,
            )
            for m in fund.managers
        ]

        fund_item = FundItem(
            fund_code=fund.fund_code,
            fund_name=fund.fund_name,
            fund_type=fund.fund_type,
            fund_category=fund.fund_category or "",
            company_name=fund.company_name,
            company_code=fund.company_code or "",
            total_amount=fund.total_amount,
            established_date=fund.established_date,
            maturity_date=fund.maturity_date,
            vintage_year=fund.vintage_year,
            is_active=fund.is_active,
            is_maturity_alert=fund.is_maturity_alert,
            description=fund.description or "",
            source_url=fund.source_url or "",
            data_source=fund.data_source,
            legal_basis=fund.legal_basis,
            is_co_gp=fund.is_co_gp,
            gp_list=gp_list,
            reference_date=fund.reference_date,
        )

        return FundDetailResponse(
            fund=fund_item,
            managers=managers,
            reference_date=fund.reference_date,
        )

    def _to_fund_list_item(self, fund: Fund) -> FundListItem:
        """Fund ORM → FundListItem schema 변환"""
        gp_list = None
        if fund.gp_list:
            gp_list = [
                GPInfo(gp_name=gp.gp_name, gp_role=gp.gp_role)
                for gp in sorted(fund.gp_list, key=lambda g: g.gp_role)
            ]

        return FundListItem(
            fund_code=fund.fund_code,
            fund_name=fund.fund_name,
            fund_type=fund.fund_type,
            legal_type=fund.legal_type or "",
            asset_class=fund.asset_class or "",
            fund_status="active" if fund.is_active else "liquidated",
            company_name=fund.company_name,
            total_amount=fund.total_amount,
            vintage_year=fund.vintage_year,
            is_maturity_alert=fund.is_maturity_alert,
            data_source=fund.data_source,
            legal_basis=fund.legal_basis,
            is_co_gp=fund.is_co_gp,
            gp_list=gp_list,
            reference_date=fund.reference_date,
        )
