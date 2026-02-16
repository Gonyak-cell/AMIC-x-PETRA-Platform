"""심사역 이동 추적 태스크

ManagerService.detect_movements()를 호출하여 새 이동 이벤트를 감지하고
관련 워치리스트 구독자에게 알림을 생성한다.
"""

import json
import logging

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.watchlist import Watchlist
from app.services.alert_service import AlertService
from app.services.manager_service import ManagerService

logger = logging.getLogger(__name__)


async def run_manager_tracking() -> dict:
    """심사역 이동을 추적한다.

    Returns:
        {"movements_detected": int, "alerts_created": int}
    """
    logger.info("심사역 이동 추적 시작")
    movements_detected = 0
    alerts_created = 0

    try:
        svc = ManagerService()
        alert_svc = AlertService()

        async with async_session_factory() as db:
            movements = await svc.detect_movements(db)
            movements_detected = len(movements)

            for movement in movements:
                company_ids = set()
                if movement.from_company_id:
                    company_ids.add(movement.from_company_id)
                if movement.to_company_id:
                    company_ids.add(movement.to_company_id)

                for company_id in company_ids:
                    result = await db.execute(
                        select(Watchlist).where(
                            Watchlist.company_id == company_id,
                            Watchlist.is_active == True,  # noqa: E712
                        )
                    )
                    watchlist_entries = result.scalars().all()

                    for entry in watchlist_entries:
                        alert_types = json.loads(entry.alert_types) if entry.alert_types else []
                        if "manager_movement" in alert_types:
                            await alert_svc.create_and_notify(
                                db=db,
                                user_id=entry.user_id,
                                company_id=company_id,
                                alert_type="manager_movement",
                                title=f"심사역 이동: {movement.manager_name}",
                                message=movement.description,
                            )
                            alerts_created += 1

            await db.commit()
    except Exception:
        logger.exception("심사역 이동 추적 중 예외 발생")

    logger.info("심사역 이동 추적 완료: movements=%d, alerts=%d", movements_detected, alerts_created)
    return {"movements_detected": movements_detected, "alerts_created": alerts_created}
