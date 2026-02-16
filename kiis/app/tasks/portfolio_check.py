"""포트폴리오 생존 점검 태스크

전체 PortfolioCompany를 순회하며 생존 상태를 확인하고
유니콘 전환 감지 시 알림을 생성한다.
"""

import json
import logging

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.company import Company
from app.models.portfolio import PortfolioCompany
from app.models.watchlist import Watchlist
from app.services.alert_service import AlertService
from app.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)


async def run_portfolio_check() -> dict:
    """포트폴리오 생존 상태를 점검한다.

    Returns:
        {"total": int, "checked": int, "unicorns_detected": int, "errors": int}
    """
    logger.info("포트폴리오 생존 점검 시작")
    checked = 0
    unicorns_detected = 0
    errors = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(PortfolioCompany.id, PortfolioCompany.investor_company_id)
        )
        portfolio_entries = result.all()

    total = len(portfolio_entries)
    svc = PortfolioService()
    alert_svc = AlertService()

    for portfolio_id, investor_company_id in portfolio_entries:
        try:
            async with async_session_factory() as db:
                prev_result = await db.execute(
                    select(PortfolioCompany.is_unicorn).where(PortfolioCompany.id == portfolio_id)
                )
                was_unicorn = prev_result.scalar_one_or_none() or False

                portfolio = await svc.check_survival(db, portfolio_id)
                await db.commit()

                if portfolio and portfolio.is_unicorn and not was_unicorn:
                    unicorns_detected += 1
                    await _notify_unicorn(db, alert_svc, investor_company_id, portfolio)
                    await db.commit()

                checked += 1
        except Exception:
            errors += 1
            logger.exception("포트폴리오 점검 실패: portfolio_id=%d", portfolio_id)

    logger.info(
        "포트폴리오 생존 점검 완료: total=%d, checked=%d, unicorns=%d, errors=%d",
        total,
        checked,
        unicorns_detected,
        errors,
    )
    return {"total": total, "checked": checked, "unicorns_detected": unicorns_detected, "errors": errors}


async def _notify_unicorn(
    db,
    alert_svc: AlertService,
    investor_company_id: int,
    portfolio: PortfolioCompany,
) -> None:
    """유니콘 전환을 워치리스트 구독자에게 알린다."""
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.company_id == investor_company_id,
            Watchlist.is_active == True,  # noqa: E712
        )
    )
    watchlist_entries = result.scalars().all()

    company_result = await db.execute(
        select(Company.corp_name).where(Company.id == investor_company_id)
    )
    corp_name = company_result.scalar_one_or_none() or "알 수 없음"

    for entry in watchlist_entries:
        alert_types = json.loads(entry.alert_types) if entry.alert_types else []
        if "new_deal" in alert_types:
            await alert_svc.create_and_notify(
                db=db,
                user_id=entry.user_id,
                company_id=investor_company_id,
                alert_type="new_deal",
                title=f"유니콘 등극: {portfolio.target_company_name}",
                message=f"{corp_name}의 피투자사 {portfolio.target_company_name}이(가) 유니콘 기업가치를 달성했습니다.",
                company_name=corp_name,
            )
