"""알림 및 워치리스트 서비스 테스트"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.user import User
from app.models.watchlist import AlertHistory
from app.services.alert_service import AlertService


@pytest.fixture
def alert_service() -> AlertService:
    """알림 서비스 인스턴스"""
    return AlertService()


@pytest.fixture
async def sample_user(async_session: AsyncSession) -> User:
    """테스트용 사용자"""
    from app.core.security import get_password_hash

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("pass1234"),
        role="viewer",
    )
    async_session.add(user)
    await async_session.flush()
    return user


@pytest.fixture
async def sample_company(async_session: AsyncSession) -> Company:
    """테스트용 기업"""
    company = Company(
        corp_code="00100001",
        corp_name="테스트기업",
        corp_cls="E",
    )
    async_session.add(company)
    await async_session.flush()
    return company


@pytest.fixture
async def second_company(async_session: AsyncSession) -> Company:
    """테스트용 두 번째 기업"""
    company = Company(
        corp_code="00100002",
        corp_name="두번째기업",
        corp_cls="Y",
    )
    async_session.add(company)
    await async_session.flush()
    return company


class TestWatchlist:
    """워치리스트 테스트"""

    async def test_add_to_watchlist(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """워치리스트에 기업 추가"""
        watchlist = await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_types=["new_disclosure", "reputation_change"],
        )

        assert watchlist is not None
        assert watchlist.user_id == sample_user.id
        assert watchlist.company_id == sample_company.id
        assert watchlist.is_active is True

    async def test_add_duplicate_updates(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """동일 기업 중복 추가 시 알림 유형 업데이트"""
        # 첫 번째 추가
        first = await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_types=["new_disclosure"],
        )

        # 동일 기업 다시 추가 (유형 변경)
        second = await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_types=["new_disclosure", "new_deal", "sanction"],
        )

        assert first.id == second.id  # 동일 레코드 업데이트
        assert second.is_active is True

    async def test_remove_from_watchlist(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """워치리스트에서 기업 제거 (비활성화)"""
        await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_types=["new_disclosure"],
        )

        removed = await alert_service.remove_from_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
        )
        assert removed is True

    async def test_remove_nonexistent(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
    ):
        """등록되지 않은 기업 제거 시 False 반환"""
        removed = await alert_service.remove_from_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=99999,
        )
        assert removed is False

    async def test_get_watchlist(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
        second_company: Company,
    ):
        """활성 워치리스트 목록 조회"""
        # 2개 기업 추가
        await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_types=["new_disclosure"],
        )
        await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=second_company.id,
            alert_types=["reputation_change"],
        )

        items = await alert_service.get_watchlist(
            db=async_session,
            user_id=sample_user.id,
        )

        assert len(items) == 2
        company_names = [item["company_name"] for item in items]
        assert "테스트기업" in company_names
        assert "두번째기업" in company_names

    async def test_get_watchlist_excludes_inactive(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """비활성화된 항목은 조회 결과에서 제외"""
        await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_types=["new_disclosure"],
        )
        await alert_service.remove_from_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
        )

        items = await alert_service.get_watchlist(
            db=async_session,
            user_id=sample_user.id,
        )
        assert len(items) == 0

    async def test_reactivate_watchlist(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """비활성화 후 다시 추가하면 활성화"""
        await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_types=["new_disclosure"],
        )
        await alert_service.remove_from_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
        )

        # 다시 추가
        reactivated = await alert_service.add_to_watchlist(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_types=["new_deal"],
        )
        assert reactivated.is_active is True

        items = await alert_service.get_watchlist(
            db=async_session,
            user_id=sample_user.id,
        )
        assert len(items) == 1


class TestAlerts:
    """알림 이력 테스트"""

    async def test_create_alert(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """알림 생성"""
        alert = await alert_service.create_alert(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_type="new_disclosure",
            title="테스트기업 신규 공시 등록",
            message="사업보고서가 등록되었습니다.",
            reference_id=100,
            reference_type="disclosure",
        )

        assert alert.id is not None
        assert alert.user_id == sample_user.id
        assert alert.company_id == sample_company.id
        assert alert.alert_type == "new_disclosure"
        assert alert.title == "테스트기업 신규 공시 등록"
        assert alert.is_read is False

    async def test_get_alerts(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """알림 목록 조회"""
        # 알림 3개 생성
        for i in range(3):
            await alert_service.create_alert(
                db=async_session,
                user_id=sample_user.id,
                company_id=sample_company.id,
                alert_type="new_disclosure",
                title=f"알림 {i + 1}",
            )

        items, total = await alert_service.get_alerts(
            db=async_session,
            user_id=sample_user.id,
            page=1,
            size=20,
        )

        assert total == 3
        assert len(items) == 3
        assert items[0]["company_name"] == "테스트기업"

    async def test_get_alerts_pagination(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """알림 목록 페이지네이션"""
        for i in range(5):
            await alert_service.create_alert(
                db=async_session,
                user_id=sample_user.id,
                company_id=sample_company.id,
                alert_type="new_disclosure",
                title=f"알림 {i + 1}",
            )

        items, total = await alert_service.get_alerts(
            db=async_session,
            user_id=sample_user.id,
            page=1,
            size=2,
        )

        assert total == 5
        assert len(items) == 2

    async def test_mark_as_read(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """알림 읽음 처리"""
        alert = await alert_service.create_alert(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_type="new_disclosure",
            title="읽을 알림",
        )
        assert alert.is_read is False

        success = await alert_service.mark_as_read(
            db=async_session,
            alert_id=alert.id,
            user_id=sample_user.id,
        )
        assert success is True

        # 재조회하여 확인
        from sqlalchemy import select

        stmt = select(AlertHistory).where(AlertHistory.id == alert.id)
        result = await async_session.execute(stmt)
        updated = result.scalar_one()
        assert updated.is_read is True

    async def test_mark_as_read_wrong_user(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """다른 사용자의 알림은 읽음 처리 불가"""
        alert = await alert_service.create_alert(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_type="new_disclosure",
            title="다른 사용자 알림",
        )

        success = await alert_service.mark_as_read(
            db=async_session,
            alert_id=alert.id,
            user_id=99999,  # 다른 사용자
        )
        assert success is False

    async def test_mark_as_read_nonexistent(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
    ):
        """존재하지 않는 알림 읽음 처리 시 False 반환"""
        success = await alert_service.mark_as_read(
            db=async_session,
            alert_id=99999,
            user_id=sample_user.id,
        )
        assert success is False

    async def test_get_unread_count(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """미읽음 알림 수 조회"""
        # 알림 3개 생성
        alerts = []
        for i in range(3):
            alert = await alert_service.create_alert(
                db=async_session,
                user_id=sample_user.id,
                company_id=sample_company.id,
                alert_type="new_disclosure",
                title=f"알림 {i + 1}",
            )
            alerts.append(alert)

        # 전체 미읽음
        count = await alert_service.get_unread_count(
            db=async_session,
            user_id=sample_user.id,
        )
        assert count == 3

        # 1개 읽음 처리
        await alert_service.mark_as_read(
            db=async_session,
            alert_id=alerts[0].id,
            user_id=sample_user.id,
        )

        count = await alert_service.get_unread_count(
            db=async_session,
            user_id=sample_user.id,
        )
        assert count == 2

    async def test_get_unread_count_no_alerts(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
    ):
        """알림이 없으면 미읽음 수 0"""
        count = await alert_service.get_unread_count(
            db=async_session,
            user_id=sample_user.id,
        )
        assert count == 0

    async def test_create_alert_with_reference(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """참조 정보가 포함된 알림 생성"""
        alert = await alert_service.create_alert(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_type="reputation_change",
            title="평판 등급 변경: Stable -> Risk",
            message="테스트기업의 평판 등급이 하락했습니다.",
            reference_id=42,
            reference_type="reputation",
        )

        assert alert.reference_id == 42
        assert alert.reference_type == "reputation"

    async def test_create_alert_without_optional_fields(
        self,
        async_session: AsyncSession,
        alert_service: AlertService,
        sample_user: User,
        sample_company: Company,
    ):
        """선택 필드 없이 알림 생성"""
        alert = await alert_service.create_alert(
            db=async_session,
            user_id=sample_user.id,
            company_id=sample_company.id,
            alert_type="new_deal",
            title="신규 딜 감지",
        )

        assert alert.message is None
        assert alert.reference_id is None
        assert alert.reference_type is None
