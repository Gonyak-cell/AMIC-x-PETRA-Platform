"""알림 및 워치리스트 서비스

워치리스트 관리, 알림 생성/조회/읽음 처리 등의 비즈니스 로직을 담당한다.
"""

import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.watchlist import AlertHistory, Watchlist
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class AlertService:
    """알림 서비스

    워치리스트 CRUD 및 알림 이력 관리를 제공한다.
    """

    async def add_to_watchlist(
        self,
        db: AsyncSession,
        user_id: int,
        company_id: int,
        alert_types: list[str],
    ) -> Watchlist:
        """워치리스트에 기업을 추가한다.

        이미 등록된 기업이면 alert_types를 업데이트하고 활성화한다.

        Args:
            db: DB 세션
            user_id: 사용자 ID
            company_id: 기업 ID
            alert_types: 수신할 알림 유형 목록

        Returns:
            생성 또는 업데이트된 Watchlist 인스턴스
        """
        stmt = select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.company_id == company_id,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.alert_types = json.dumps(alert_types)
            existing.is_active = True
            await db.flush()
            await db.commit()
            return existing

        watchlist = Watchlist(
            user_id=user_id,
            company_id=company_id,
            alert_types=json.dumps(alert_types),
            is_active=True,
        )
        db.add(watchlist)
        await db.flush()
        await db.commit()
        return watchlist

    async def remove_from_watchlist(
        self,
        db: AsyncSession,
        user_id: int,
        company_id: int,
    ) -> bool:
        """워치리스트에서 기업을 비활성화한다.

        Args:
            db: DB 세션
            user_id: 사용자 ID
            company_id: 기업 ID

        Returns:
            성공 여부 (등록되지 않은 기업이면 False)
        """
        stmt = select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.company_id == company_id,
        )
        result = await db.execute(stmt)
        watchlist = result.scalar_one_or_none()

        if not watchlist:
            return False

        watchlist.is_active = False
        await db.flush()
        await db.commit()
        return True

    async def get_watchlist(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> list[dict]:
        """사용자의 활성 워치리스트를 조회한다.

        Args:
            db: DB 세션
            user_id: 사용자 ID

        Returns:
            워치리스트 항목 딕셔너리 리스트
        """
        stmt = (
            select(Watchlist, Company.corp_name)
            .join(Company, Watchlist.company_id == Company.id, isouter=True)
            .where(
                Watchlist.user_id == user_id,
                Watchlist.is_active == True,  # noqa: E712
            )
        )
        result = await db.execute(stmt)

        items: list[dict] = []
        for watchlist, company_name in result.all():
            alert_types = json.loads(watchlist.alert_types) if watchlist.alert_types else []
            items.append(
                {
                    "id": watchlist.id,
                    "user_id": watchlist.user_id,
                    "company_id": watchlist.company_id,
                    "company_name": company_name,
                    "alert_types": alert_types,
                    "is_active": watchlist.is_active,
                    "created_at": watchlist.created_at,
                }
            )
        return items

    async def get_alerts(
        self,
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict], int]:
        """사용자의 알림 이력을 페이지네이션으로 조회한다.

        Args:
            db: DB 세션
            user_id: 사용자 ID
            page: 페이지 번호 (1부터)
            size: 페이지당 건수

        Returns:
            (알림 항목 리스트, 총 건수)
        """
        base = select(AlertHistory).where(AlertHistory.user_id == user_id)

        count_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar() or 0

        stmt = base.order_by(AlertHistory.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(stmt)
        alerts = result.scalars().all()

        items: list[dict] = []
        for alert in alerts:
            company = await db.get(Company, alert.company_id)
            items.append(
                {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "title": alert.title,
                    "message": alert.message,
                    "is_read": alert.is_read,
                    "company_id": alert.company_id,
                    "company_name": company.corp_name if company else None,
                    "reference_id": alert.reference_id,
                    "reference_type": alert.reference_type,
                    "created_at": alert.created_at,
                }
            )
        return items, total

    async def mark_as_read(
        self,
        db: AsyncSession,
        alert_id: int,
        user_id: int,
    ) -> bool:
        """알림을 읽음 처리한다.

        Args:
            db: DB 세션
            alert_id: 알림 ID
            user_id: 사용자 ID (본인 확인용)

        Returns:
            성공 여부 (존재하지 않거나 본인 것이 아니면 False)
        """
        stmt = select(AlertHistory).where(
            AlertHistory.id == alert_id,
            AlertHistory.user_id == user_id,
        )
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            return False

        alert.is_read = True
        await db.flush()
        await db.commit()
        return True

    async def get_unread_count(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> int:
        """미읽음 알림 수를 반환한다.

        Args:
            db: DB 세션
            user_id: 사용자 ID

        Returns:
            미읽음 알림 개수
        """
        result = await db.execute(
            select(func.count(AlertHistory.id)).where(
                AlertHistory.user_id == user_id,
                AlertHistory.is_read == False,  # noqa: E712
            )
        )
        return result.scalar() or 0

    async def create_alert(
        self,
        db: AsyncSession,
        user_id: int,
        company_id: int,
        alert_type: str,
        title: str,
        message: str | None = None,
        reference_id: int | None = None,
        reference_type: str | None = None,
    ) -> AlertHistory:
        """새 알림을 생성한다.

        Args:
            db: DB 세션
            user_id: 사용자 ID
            company_id: 기업 ID
            alert_type: 알림 유형
            title: 알림 제목
            message: 알림 내용
            reference_id: 참조 레코드 ID
            reference_type: 참조 유형

        Returns:
            생성된 AlertHistory 인스턴스
        """
        alert = AlertHistory(
            user_id=user_id,
            company_id=company_id,
            alert_type=alert_type,
            title=title,
            message=message,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        db.add(alert)
        await db.flush()
        await db.commit()
        return alert

    async def create_and_notify(
        self,
        db: AsyncSession,
        user_id: int,
        company_id: int,
        alert_type: str,
        title: str,
        message: str | None = None,
        reference_id: int | None = None,
        reference_type: str | None = None,
        user_email: str | None = None,
        company_name: str | None = None,
    ) -> tuple[AlertHistory, dict[str, bool]]:
        """알림을 생성한 뒤 Slack/이메일로 발송한다.

        기존 create_alert()을 래핑하고 NotificationService.dispatch()를 호출한다.

        Args:
            db: DB 세션
            user_id: 사용자 ID
            company_id: 기업 ID
            alert_type: 알림 유형
            title: 알림 제목
            message: 알림 내용
            reference_id: 참조 레코드 ID
            reference_type: 참조 유형
            user_email: 사용자 이메일 (이메일 발송용, None이면 이메일 건너뜀)
            company_name: 기업명 (Slack 메시지용)

        Returns:
            (AlertHistory, {"slack": bool, "email": bool})
        """
        alert = await self.create_alert(
            db=db,
            user_id=user_id,
            company_id=company_id,
            alert_type=alert_type,
            title=title,
            message=message,
            reference_id=reference_id,
            reference_type=reference_type,
        )

        notifier = NotificationService()
        dispatch_result = await notifier.dispatch(
            user_email=user_email,
            title=title,
            message=message or "",
            alert_type=alert_type,
            company_name=company_name,
        )

        return alert, dispatch_result
