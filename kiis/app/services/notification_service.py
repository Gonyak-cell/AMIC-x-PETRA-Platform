"""알림 발송 서비스 (Slack 웹훅 + SMTP 이메일)

외부 채널로 알림을 실제 발송하는 역할을 담당한다.
설정이 비어 있으면 graceful skip, 예외 발생 시 로깅 후 False 반환 (fire-and-forget).
"""

import logging
from email.mime.text import MIMEText

import aiosmtplib
from slack_sdk.webhook.async_client import AsyncWebhookClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Slack 웹훅 및 SMTP 이메일 발송 서비스"""

    async def send_slack(
        self,
        title: str,
        message: str,
        alert_type: str,
        company_name: str | None = None,
    ) -> bool:
        """Slack 웹훅으로 메시지를 발송한다.

        Args:
            title: 알림 제목
            message: 알림 본문
            alert_type: 알림 유형 (new_disclosure, reputation_change 등)
            company_name: 관련 기업명 (선택)

        Returns:
            발송 성공 여부. 미설정 시 False 반환 (에러 아님).
        """
        if not settings.SLACK_WEBHOOK_URL:
            logger.debug("Slack webhook URL이 설정되지 않아 발송을 건너뜁니다.")
            return False

        try:
            header = f"[{alert_type.upper()}]"
            if company_name:
                header += f" {company_name}"

            text = f"*{header}*\n*{title}*\n{message}"

            client = AsyncWebhookClient(url=settings.SLACK_WEBHOOK_URL)
            response = await client.send(text=text)

            if response.status_code == 200:
                logger.info("Slack 알림 발송 성공: %s", title)
                return True

            logger.warning("Slack 알림 발송 실패 (status=%d): %s", response.status_code, response.body)
            return False
        except Exception:
            logger.exception("Slack 알림 발송 중 예외 발생")
            return False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> bool:
        """SMTP를 통해 이메일을 발송한다.

        Args:
            to_email: 수신자 이메일 주소
            subject: 메일 제목
            body: 메일 본문

        Returns:
            발송 성공 여부. SMTP 미설정 시 False 반환 (에러 아님).
        """
        if not settings.SMTP_HOST:
            logger.debug("SMTP 호스트가 설정되지 않아 이메일 발송을 건너뜁니다.")
            return False

        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
            msg["To"] = to_email

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME or None,
                password=settings.SMTP_PASSWORD or None,
                use_tls=settings.SMTP_USE_TLS,
            )
            logger.info("이메일 발송 성공: %s → %s", subject, to_email)
            return True
        except Exception:
            logger.exception("이메일 발송 중 예외 발생")
            return False

    async def dispatch(
        self,
        user_email: str | None,
        title: str,
        message: str,
        alert_type: str,
        company_name: str | None = None,
    ) -> dict[str, bool]:
        """Slack과 이메일 양쪽 채널로 알림을 동시 발송한다.

        Args:
            user_email: 수신자 이메일 (None이면 이메일 발송 건너뜀)
            title: 알림 제목
            message: 알림 본문
            alert_type: 알림 유형
            company_name: 관련 기업명 (선택)

        Returns:
            {"slack": bool, "email": bool} 채널별 발송 결과
        """
        slack_ok = await self.send_slack(
            title=title,
            message=message,
            alert_type=alert_type,
            company_name=company_name,
        )

        email_ok = False
        if user_email:
            subject = f"[KIIS] {title}"
            email_ok = await self.send_email(
                to_email=user_email,
                subject=subject,
                body=message,
            )

        return {"slack": slack_ok, "email": email_ok}
