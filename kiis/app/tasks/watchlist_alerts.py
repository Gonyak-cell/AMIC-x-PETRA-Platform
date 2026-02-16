"""워치리스트 알림 확인 태스크

최근 이벤트(새 공시, 새 딜, 제재)를 조회하고
워치리스트에 매칭되는 기업의 구독자에게 알림을 생성 + 발송한다.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.company import Company
from app.models.disclosure import Disclosure
from app.models.watchlist import AlertHistory, Watchlist
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


async def run_watchlist_alerts() -> dict:
    """워치리스트 기반으로 최근 이벤트 알림을 생성한다.

    Returns:
        {"new_disclosures": int, "alerts_created": int}
    """
    logger.info("워치리스트 알림 확인 시작")
    alerts_created = 0
    new_disclosures = 0

    try:
        alert_svc = AlertService()

        async with async_session_factory() as db:
            # 최근 6시간 이내 공시 조회
            since = datetime.now(KST) - timedelta(hours=6)
            disc_result = await db.execute(
                select(Disclosure).where(Disclosure.created_at >= since)
            )
            recent_disclosures = disc_result.scalars().all()
            new_disclosures = len(recent_disclosures)

            for disclosure in recent_disclosures:
                if not disclosure.company_id:
                    continue

                # 해당 기업의 워치리스트 구독자 조회
                wl_result = await db.execute(
                    select(Watchlist).where(
                        Watchlist.company_id == disclosure.company_id,
                        Watchlist.is_active == True,  # noqa: E712
                    )
                )
                watchlist_entries = wl_result.scalars().all()

                # 기업명 조회
                company_result = await db.execute(
                    select(Company.corp_name).where(Company.id == disclosure.company_id)
                )
                corp_name = company_result.scalar_one_or_none() or ""

                for entry in watchlist_entries:
                    alert_types = json.loads(entry.alert_types) if entry.alert_types else []
                    if "new_disclosure" not in alert_types:
                        continue

                    # 이미 같은 공시에 대해 알림을 보냈는지 확인
                    existing = await db.execute(
                        select(AlertHistory.id).where(
                            AlertHistory.user_id == entry.user_id,
                            AlertHistory.reference_id == disclosure.id,
                            AlertHistory.reference_type == "disclosure",
                        )
                    )
                    if existing.scalar_one_or_none() is not None:
                        continue

                    await alert_svc.create_and_notify(
                        db=db,
                        user_id=entry.user_id,
                        company_id=disclosure.company_id,
                        alert_type="new_disclosure",
                        title=f"새 공시: {disclosure.report_nm or '공시'}",
                        message=f"{corp_name}의 새 공시가 등록되었습니다: {disclosure.report_nm}",
                        reference_id=disclosure.id,
                        reference_type="disclosure",
                        company_name=corp_name,
                    )
                    alerts_created += 1

            await db.commit()
    except Exception:
        logger.exception("워치리스트 알림 확인 중 예외 발생")

    logger.info("워치리스트 알림 확인 완료: disclosures=%d, alerts=%d", new_disclosures, alerts_created)
    return {"new_disclosures": new_disclosures, "alerts_created": alerts_created}
