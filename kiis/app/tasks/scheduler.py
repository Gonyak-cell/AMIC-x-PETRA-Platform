"""백그라운드 스케줄러 초기화 및 관리

APScheduler 3.x AsyncIOScheduler를 사용하여
데이터 수집/분석 작업을 주기적으로 실행한다.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


async def init_scheduler() -> None:
    """스케줄러를 초기화하고 작업을 등록한다.

    SCHEDULER_ENABLED=False이면 스킵한다 (테스트/개발 환경용).
    """
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("스케줄러가 비활성화 상태입니다 (SCHEDULER_ENABLED=False)")
        return

    _scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    # 지연 임포트로 순환 참조 방지
    from app.tasks.company_sync import sync_companies_from_dart
    from app.tasks.dart_sync import run_dart_sync
    from app.tasks.elestock_sync import run_elestock_sync
    from app.tasks.gp_profile_sync import run_gp_profile_sync
    from app.tasks.holding_sync import run_holding_sync
    from app.tasks.ib_collect import run_ib_collect
    from app.tasks.manager_tracking import run_manager_tracking
    from app.tasks.news_collect import run_news_collect
    from app.tasks.portfolio_check import run_portfolio_check
    from app.tasks.reputation_recalc import run_reputation_recalc
    from app.tasks.watchlist_alerts import run_watchlist_alerts

    _scheduler.add_job(
        sync_companies_from_dart,
        "cron",
        day_of_week="mon",
        hour=6,
        id="company_sync",
        name="DART 기업목록 동기화",
    )

    _scheduler.add_job(
        run_dart_sync,
        "interval",
        hours=settings.DART_SYNC_INTERVAL_HOURS,
        id="dart_sync",
        name="DART 공시 동기화",
    )

    _scheduler.add_job(
        run_news_collect,
        "interval",
        hours=settings.NEWS_COLLECT_INTERVAL_HOURS,
        id="news_collect",
        name="뉴스 자동 수집",
    )

    _scheduler.add_job(
        run_reputation_recalc,
        "cron",
        hour=settings.REPUTATION_RECALC_HOUR,
        id="reputation_recalc",
        name="평판 재계산",
    )

    _scheduler.add_job(
        run_manager_tracking,
        "cron",
        day_of_week=settings.MANAGER_TRACKING_DAY_OF_WEEK,
        hour=9,
        id="manager_tracking",
        name="심사역 이동 추적",
    )

    _scheduler.add_job(
        run_portfolio_check,
        "cron",
        hour=settings.PORTFOLIO_CHECK_HOUR,
        id="portfolio_check",
        name="포트폴리오 생존 점검",
    )

    _scheduler.add_job(
        run_watchlist_alerts,
        "interval",
        hours=settings.WATCHLIST_ALERT_INTERVAL_HOURS,
        id="watchlist_alerts",
        name="워치리스트 알림 확인",
    )

    _scheduler.add_job(
        run_ib_collect,
        "interval",
        hours=settings.IB_COLLECT_INTERVAL_HOURS,
        id="ib_collect",
        name="IB 매체 자동 수집",
    )

    _scheduler.add_job(
        run_gp_profile_sync,
        "cron",
        day_of_week=settings.GP_PROFILE_SYNC_DAY_OF_WEEK,
        hour=settings.GP_PROFILE_SYNC_HOUR,
        id="gp_profile_sync",
        name="GP 프로파일 동기화 (공공데이터)",
    )

    _scheduler.add_job(
        run_holding_sync,
        "cron",
        hour=settings.HOLDING_SYNC_HOUR,
        id="holding_sync",
        name="DART 대량보유 동기화 + 딜 신호",
    )

    _scheduler.add_job(
        run_elestock_sync,
        "cron",
        hour=settings.ELESTOCK_SYNC_HOUR,
        id="elestock_sync",
        name="DART 임원소유보고 동기화 + 딜 신호",
    )

    _scheduler.start()
    logger.info("스케줄러 시작 완료 (%d개 작업 등록)", len(_scheduler.get_jobs()))


async def close_scheduler() -> None:
    """스케줄러를 종료한다."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료 완료")
        _scheduler = None
