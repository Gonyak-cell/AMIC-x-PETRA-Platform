"""포트폴리오 생존분석 서비스

투자사의 피투자사(포트폴리오 기업)에 대한 생존 상태를 추적한다.
DART 감사보고서 제출 여부, 해산/폐업 공시 감지, 유니콘 등극 등을 분석한다.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.deal import Deal
from app.models.portfolio import PortfolioCompany, SurvivalStatus
from app.services.dart_service import DARTService

logger = logging.getLogger(__name__)

# 해산/폐업 관련 키워드
DISSOLUTION_KEYWORDS = ["해산", "폐업", "청산", "파산"]

# 유니콘 기준: 기업가치 1조원 이상
UNICORN_THRESHOLD = Decimal("1_000_000_000_000")


class PortfolioService:
    """포트폴리오 생존분석 서비스"""

    def __init__(self) -> None:
        self.dart_service = DARTService()

    async def _get_company_by_corp_code(self, db: AsyncSession, corp_code: str) -> Company | None:
        """기업을 corp_code로 조회한다."""
        stmt = select(Company).where(Company.corp_code == corp_code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def sync_from_deals(self, db: AsyncSession, investor_corp_code: str) -> int:
        """딜 데이터에서 포트폴리오 엔트리를 동기화한다.

        투자사의 딜에서 피투자사 정보를 추출하여,
        아직 포트폴리오에 없는 항목을 새로 생성한다.

        Args:
            db: DB 세션
            investor_corp_code: 투자사 DART 고유번호

        Returns:
            새로 생성된 포트폴리오 엔트리 수
        """
        # 투자사 조회
        company = await self._get_company_by_corp_code(db, investor_corp_code)
        if not company:
            return 0

        # 해당 투자사의 딜 목록 조회
        deals_stmt = select(Deal).where(Deal.company_id == company.id)
        deals_result = await db.execute(deals_stmt)
        deals = list(deals_result.scalars().all())

        if not deals:
            return 0

        # 기존 포트폴리오 엔트리 (target_company_name 기준 중복 방지)
        existing_stmt = select(PortfolioCompany.target_company_name).where(
            PortfolioCompany.investor_company_id == company.id
        )
        existing_result = await db.execute(existing_stmt)
        existing_names = set(existing_result.scalars().all())

        new_count = 0
        for deal in deals:
            target_name = deal.target_company
            if target_name in existing_names:
                continue

            portfolio_entry = PortfolioCompany(
                investor_company_id=company.id,
                target_company_name=target_name,
                target_company_id=deal.target_company_id,
                deal_id=deal.id,
                survival_status=SurvivalStatus.UNKNOWN,
            )
            db.add(portfolio_entry)
            existing_names.add(target_name)
            new_count += 1

        await db.flush()
        await db.commit()
        return new_count

    async def check_survival(self, db: AsyncSession, portfolio_id: int) -> PortfolioCompany | None:
        """포트폴리오 기업의 생존 상태를 확인한다.

        피투자사에 corp_code가 있으면 DART에서 감사보고서와 해산 공시를 조회한다.

        Args:
            db: DB 세션
            portfolio_id: 포트폴리오 ID

        Returns:
            업데이트된 포트폴리오 엔트리 (없으면 None)
        """
        # 포트폴리오 엔트리 조회
        stmt = select(PortfolioCompany).where(PortfolioCompany.id == portfolio_id)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            return None

        now = datetime.now(UTC)
        previous_status = portfolio.survival_status

        # 피투자사의 corp_code 확인
        target_corp_code = None
        if portfolio.target_company_id:
            target_stmt = select(Company).where(Company.id == portfolio.target_company_id)
            target_result = await db.execute(target_stmt)
            target = target_result.scalar_one_or_none()
            if target:
                target_corp_code = target.corp_code

        if not target_corp_code:
            # corp_code가 없으면 상태 확인 불가
            portfolio.checked_at = now
            portfolio.notes = "피투자사 DART 고유번호 미확인"
            await db.flush()
            await db.commit()
            return portfolio

        try:
            # 1. 해산/폐업 공시 확인
            disclosures, _, _ = await self.dart_service.search_disclosures(
                corp_code=target_corp_code,
                page_count=100,
            )

            # 해산/폐업 키워드 감지
            for disc in disclosures:
                report_name = disc.report_nm or ""
                if any(keyword in report_name for keyword in DISSOLUTION_KEYWORDS):
                    portfolio.survival_status = SurvivalStatus.DISSOLVED
                    portfolio.dissolution_date = (
                        datetime.strptime(disc.rcept_dt, "%Y%m%d").date() if disc.rcept_dt else None
                    )
                    portfolio.dissolution_rcept_no = disc.rcept_no
                    portfolio.checked_at = now
                    await db.flush()
                    await db.commit()
                    return portfolio

            # 2. 감사보고서 확인 (pblntf_ty="A": 정기공시)
            audit_disclosures, _, _ = await self.dart_service.search_disclosures(
                corp_code=target_corp_code,
                pblntf_ty="A",
                page_count=10,
            )

            if audit_disclosures:
                # 감사보고서가 있으면 active (유니콘은 유지)
                latest = audit_disclosures[0]
                if portfolio.is_unicorn:
                    portfolio.survival_status = SurvivalStatus.UNICORN
                else:
                    portfolio.survival_status = SurvivalStatus.ACTIVE
                portfolio.last_audit_date = (
                    datetime.strptime(latest.rcept_dt, "%Y%m%d").date() if latest.rcept_dt else None
                )
                portfolio.last_audit_rcept_no = latest.rcept_no
            else:
                # 감사보고서가 없으면 audit_missing
                portfolio.survival_status = SurvivalStatus.AUDIT_MISSING

        except Exception:
            logger.exception("DART 공시 조회 실패: portfolio_id=%s", portfolio_id)
            # 외부 API 실패 시 상태 변경하지 않음
            portfolio.notes = f"DART 조회 실패 (이전 상태: {previous_status})"

        portfolio.checked_at = now
        await db.flush()
        await db.commit()
        return portfolio

    async def get_portfolio_by_investor(
        self,
        db: AsyncSession,
        corp_code: str,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[PortfolioCompany], int]:
        """투자사의 포트폴리오 목록을 조회한다.

        Args:
            db: DB 세션
            corp_code: 투자사 DART 고유번호
            status: 생존 상태 필터 (선택)
            page: 페이지 번호
            size: 페이지 크기

        Returns:
            (포트폴리오 목록, 총 건수)
        """
        # 투자사 조회
        company = await self._get_company_by_corp_code(db, corp_code)
        if not company:
            return [], 0

        # 기본 쿼리
        base_query = select(PortfolioCompany).where(PortfolioCompany.investor_company_id == company.id)

        # 상태 필터
        if status:
            base_query = base_query.where(PortfolioCompany.survival_status == status)

        # 총 건수
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션
        query = base_query.order_by(PortfolioCompany.id.desc()).offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_portfolio_summary(self, db: AsyncSession, corp_code: str) -> dict:
        """투자사의 포트폴리오 요약 (생존 상태별 집계)을 조회한다.

        Args:
            db: DB 세션
            corp_code: 투자사 DART 고유번호

        Returns:
            상태별 건수 딕셔너리
        """
        # 투자사 조회
        company = await self._get_company_by_corp_code(db, corp_code)
        if not company:
            return {
                "total": 0,
                "active_count": 0,
                "audit_missing_count": 0,
                "dissolved_count": 0,
                "unicorn_count": 0,
                "unknown_count": 0,
            }

        # 상태별 GROUP BY 집계
        query = (
            select(
                PortfolioCompany.survival_status,
                func.count(PortfolioCompany.id).label("count"),
            )
            .where(PortfolioCompany.investor_company_id == company.id)
            .group_by(PortfolioCompany.survival_status)
        )

        result = await db.execute(query)
        rows = result.all()

        # 결과 매핑
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.survival_status] = row.count

        total = sum(counts.values())

        return {
            "total": total,
            "active_count": counts.get(SurvivalStatus.ACTIVE, 0),
            "audit_missing_count": counts.get(SurvivalStatus.AUDIT_MISSING, 0),
            "dissolved_count": counts.get(SurvivalStatus.DISSOLVED, 0),
            "unicorn_count": counts.get(SurvivalStatus.UNICORN, 0),
            "unknown_count": counts.get(SurvivalStatus.UNKNOWN, 0),
        }

    async def update_valuation(
        self,
        db: AsyncSession,
        portfolio_id: int,
        valuation: Decimal,
    ) -> tuple[PortfolioCompany | None, bool]:
        """포트폴리오 기업의 기업가치를 업데이트하고 유니콘 여부를 판정한다.

        Args:
            db: DB 세션
            portfolio_id: 포트폴리오 ID
            valuation: 추정 기업가치 (원)

        Returns:
            (업데이트된 포트폴리오 엔트리, 이번에 유니콘이 되었는지 여부)
        """
        stmt = select(PortfolioCompany).where(PortfolioCompany.id == portfolio_id)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            return None, False

        was_unicorn = portfolio.is_unicorn
        portfolio.estimated_valuation = valuation

        if valuation >= UNICORN_THRESHOLD:
            portfolio.is_unicorn = True
            if portfolio.survival_status != SurvivalStatus.DISSOLVED:
                portfolio.survival_status = SurvivalStatus.UNICORN
        else:
            portfolio.is_unicorn = False
            # 유니콘에서 내려온 경우 이전 상태로 복원 (UNKNOWN으로)
            if was_unicorn and portfolio.survival_status == SurvivalStatus.UNICORN:
                portfolio.survival_status = SurvivalStatus.ACTIVE

        is_newly_unicorn = not was_unicorn and portfolio.is_unicorn
        await db.flush()
        await db.commit()
        return portfolio, is_newly_unicorn

    async def close(self) -> None:
        """리소스를 정리한다."""
        await self.dart_service.close()
