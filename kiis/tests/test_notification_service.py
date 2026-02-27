"""NotificationService 테스트

Slack 웹훅, SMTP 이메일 발송, dispatch 통합 테스트.
모든 외부 I/O는 AsyncMock으로 모킹한다.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.notification_service import NotificationService

# ─── Slack Tests ───


class TestSendSlack:
    """Slack 웹훅 발송 테스트"""

    @pytest.fixture
    def service(self):
        return NotificationService()

    async def test_send_slack_success(self, service: NotificationService):
        """Slack 웹훅 URL이 설정되어 있고 발송 성공 시 True를 반환한다."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.body = "ok"

        with (
            patch("app.services.notification_service.settings") as mock_settings,
            patch("app.services.notification_service.AsyncWebhookClient") as mock_client_cls,
        ):
            mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/test"
            mock_client = AsyncMock()
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await service.send_slack(
                title="테스트 알림",
                message="테스트 메시지입니다.",
                alert_type="new_disclosure",
                company_name="한국투자파트너스",
            )

        assert result is True
        mock_client.send.assert_called_once()

    async def test_send_slack_not_configured(self, service: NotificationService):
        """Slack 웹훅 URL이 비어 있으면 False를 반환한다 (에러 아님)."""
        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.SLACK_WEBHOOK_URL = ""

            result = await service.send_slack(
                title="테스트",
                message="msg",
                alert_type="new_disclosure",
            )

        assert result is False

    async def test_send_slack_failure_status(self, service: NotificationService):
        """Slack API가 200이 아닌 상태 코드를 반환하면 False를 반환한다."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.body = "server_error"

        with (
            patch("app.services.notification_service.settings") as mock_settings,
            patch("app.services.notification_service.AsyncWebhookClient") as mock_client_cls,
        ):
            mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/test"
            mock_client = AsyncMock()
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await service.send_slack(
                title="테스트",
                message="msg",
                alert_type="new_disclosure",
            )

        assert result is False

    async def test_send_slack_exception(self, service: NotificationService):
        """Slack 발송 중 예외 발생 시 False를 반환한다."""
        with (
            patch("app.services.notification_service.settings") as mock_settings,
            patch("app.services.notification_service.AsyncWebhookClient") as mock_client_cls,
        ):
            mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/test"
            mock_client = AsyncMock()
            mock_client.send = AsyncMock(side_effect=ConnectionError("network error"))
            mock_client_cls.return_value = mock_client

            result = await service.send_slack(
                title="테스트",
                message="msg",
                alert_type="new_disclosure",
            )

        assert result is False


# ─── Email Tests ───


class TestSendEmail:
    """SMTP 이메일 발송 테스트"""

    @pytest.fixture
    def service(self):
        return NotificationService()

    async def test_send_email_success(self, service: NotificationService):
        """SMTP가 설정되어 있고 발송 성공 시 True를 반환한다."""
        with (
            patch("app.services.notification_service.settings") as mock_settings,
            patch("app.services.notification_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send,
        ):
            mock_settings.SMTP_HOST = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "user@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.SMTP_FROM_EMAIL = "noreply@kiis.io"
            mock_settings.SMTP_USE_TLS = True

            result = await service.send_email(
                to_email="recipient@example.com",
                subject="[KIIS] 테스트 알림",
                body="테스트 메시지입니다.",
            )

        assert result is True
        mock_send.assert_called_once()

    async def test_send_email_not_configured(self, service: NotificationService):
        """SMTP 호스트가 비어 있으면 False를 반환한다 (에러 아님)."""
        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.SMTP_HOST = ""

            result = await service.send_email(
                to_email="recipient@example.com",
                subject="테스트",
                body="msg",
            )

        assert result is False

    async def test_send_email_exception(self, service: NotificationService):
        """이메일 발송 중 예외 발생 시 False를 반환한다."""
        with (
            patch("app.services.notification_service.settings") as mock_settings,
            patch(
                "app.services.notification_service.aiosmtplib.send",
                new_callable=AsyncMock,
                side_effect=ConnectionError("smtp error"),
            ),
        ):
            mock_settings.SMTP_HOST = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "user@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.SMTP_FROM_EMAIL = "noreply@kiis.io"
            mock_settings.SMTP_USE_TLS = True

            result = await service.send_email(
                to_email="recipient@example.com",
                subject="테스트",
                body="msg",
            )

        assert result is False


# ─── Dispatch Tests ───


class TestDispatch:
    """dispatch 통합 테스트"""

    @pytest.fixture
    def service(self):
        return NotificationService()

    async def test_dispatch_both_channels(self, service: NotificationService):
        """Slack과 이메일 모두 발송 성공 시 양쪽 True를 반환한다."""
        with (
            patch.object(service, "send_slack", new_callable=AsyncMock, return_value=True),
            patch.object(service, "send_email", new_callable=AsyncMock, return_value=True),
        ):
            result = await service.dispatch(
                user_email="user@example.com",
                title="테스트 알림",
                message="본문",
                alert_type="new_disclosure",
                company_name="한투파",
            )

        assert result == {"slack": True, "email": True}

    async def test_dispatch_no_email(self, service: NotificationService):
        """user_email이 None이면 이메일 발송을 건너뛴다."""
        with (
            patch.object(service, "send_slack", new_callable=AsyncMock, return_value=True),
            patch.object(service, "send_email", new_callable=AsyncMock) as mock_email,
        ):
            result = await service.dispatch(
                user_email=None,
                title="테스트",
                message="본문",
                alert_type="new_disclosure",
            )

        assert result == {"slack": True, "email": False}
        mock_email.assert_not_called()

    async def test_dispatch_partial_failure(self, service: NotificationService):
        """Slack 실패, 이메일 성공 시 각각의 결과를 반환한다."""
        with (
            patch.object(service, "send_slack", new_callable=AsyncMock, return_value=False),
            patch.object(service, "send_email", new_callable=AsyncMock, return_value=True),
        ):
            result = await service.dispatch(
                user_email="user@example.com",
                title="테스트",
                message="본문",
                alert_type="reputation_change",
            )

        assert result == {"slack": False, "email": True}


# ─── AlertService.create_and_notify Tests ───


class TestCreateAndNotify:
    """AlertService.create_and_notify 통합 테스트"""

    async def test_create_and_notify(self, async_session):
        """알림 생성 후 dispatch가 호출되는지 검증한다."""
        from app.models.company import Company
        from app.models.user import User
        from app.services.alert_service import AlertService

        company = Company(
            corp_code="00100001",
            corp_name="테스트기업",
            corp_cls="Y",
        )
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        async_session.add_all([company, user])
        await async_session.flush()

        svc = AlertService()

        with patch(
            "app.services.alert_service.NotificationService.dispatch",
            new_callable=AsyncMock,
            return_value={"slack": True, "email": True},
        ) as mock_dispatch:
            alert, result = await svc.create_and_notify(
                db=async_session,
                user_id=user.id,
                company_id=company.id,
                alert_type="new_disclosure",
                title="새 공시 알림",
                message="테스트 기업의 새 공시가 등록되었습니다.",
                user_email="test@example.com",
                company_name="테스트기업",
            )

        assert alert.id is not None
        assert alert.alert_type == "new_disclosure"
        assert result == {"slack": True, "email": True}
        mock_dispatch.assert_called_once_with(
            user_email="test@example.com",
            title="새 공시 알림",
            message="테스트 기업의 새 공시가 등록되었습니다.",
            alert_type="new_disclosure",
            company_name="테스트기업",
        )
