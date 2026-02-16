"""평판 재계산 태스크

전체 Company를 순회하며 ReputationService.calculate_reputation()을 호출한다.
상태 변경(예: Stable→Risk) 감지 시 워치리스트 구독자에게 알림을 생성한다.
"""

import json
import logging

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.company import Company
from app.models.reputation import ReputationScore
from app.models.watchlist import Watchlist
from app.services.alert_service import AlertService
from app.services.reputation_service import ReputationService

logger = logging.getLogger(__name__)


async def run_reputation_recalc() -> dict:
    """전체 기업의 평판을 재계산한다.

    Returns:
        {"total": int, "recalculated": int, "status_changes": int, "errors": int}
    """
    logger.info("평판 재계산 시작")
    recalculated = 0
    status_changes = 0
    errors = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(Company.id, Company.corp_code, Company.corp_name).where(Company.corp_code.isnot(None))
        )
        companies = result.all()

    total = len(companies)
    rep_svc = ReputationService()
    alert_svc = AlertService()

    for company_id, corp_code, corp_name in companies:
        try:
            async with async_session_factory() as db:
                # 이전 상태 조회
                prev_result = await db.execute(
                    select(ReputationScore.status_tag).where(ReputationScore.company_id == company_id)
                )
                prev_status = prev_result.scalar_one_or_none()

                # 재계산
                score = await rep_svc.calculate_reputation(db, corp_code)
                await db.commit()

                # 상태 변경 감지
                if score and prev_status and score.status_tag != prev_status:
                    status_changes += 1
                    await _notify_watchlist_subscribers(
                        db, alert_svc, company_id, corp_name, prev_status, score.status_tag
                    )
                    await db.commit()

                recalculated += 1
        except Exception:
            errors += 1
            logger.exception("평판 재계산 실패: corp_code=%s", corp_code)

    logger.info(
        "평판 재계산 완료: total=%d, recalculated=%d, status_changes=%d, errors=%d",
        total,
        recalculated,
        status_changes,
        errors,
    )
    return {"total": total, "recalculated": recalculated, "status_changes": status_changes, "errors": errors}


async def _notify_watchlist_subscribers(
    db,
    alert_svc: AlertService,
    company_id: int,
    corp_name: str,
    prev_status: str,
    new_status: str,
) -> None:
    """워치리스트 구독자에게 평판 상태 변경 알림을 생성한다."""
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.company_id == company_id,
            Watchlist.is_active == True,  # noqa: E712
        )
    )
    watchlist_entries = result.scalars().all()

    for entry in watchlist_entries:
        alert_types = json.loads(entry.alert_types) if entry.alert_types else []
        if "reputation_change" in alert_types:
            await alert_svc.create_and_notify(
                db=db,
                user_id=entry.user_id,
                company_id=company_id,
                alert_type="reputation_change",
                title=f"{corp_name} 평판 상태 변경: {prev_status} → {new_status}",
                message=f"{corp_name}의 평판 등급이 {prev_status}에서 {new_status}(으)로 변경되었습니다.",
                company_name=corp_name,
            )
