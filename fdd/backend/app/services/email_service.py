"""이메일 발송 서비스 — CLIENT 초대 이메일."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_invite_email(
    to_email: str,
    display_name: str,
    invite_url: str,
    transaction_names: list[str],
) -> None:
    """CLIENT 초대 이메일을 발송한다. SMTP 미설정 시 RuntimeError."""
    if not settings.smtp_server:
        logger.warning("SMTP not configured", extra={"ctx": {"to": to_email}})
        raise RuntimeError("SMTP server not configured")

    deals_html = "".join(f"<li>{n}</li>" for n in transaction_names)
    html_body = f"""<div style="font-family: 'Pretendard', sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #0f172a;">AMIC Platform 초대</h2>
      <p>안녕하세요 {display_name}님,</p>
      <p>아래 거래에 대한 접근 권한이 부여되었습니다:</p>
      <ul>{deals_html}</ul>
      <p>아래 버튼을 클릭하여 비밀번호를 설정하고 로그인하세요.</p>
      <a href="{invite_url}" style="display: inline-block; padding: 12px 24px; background: #0ea5e9; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">초대 수락하기</a>
      <p style="color: #64748b; font-size: 13px; margin-top: 24px;">이 링크는 {settings.invite_token_expire_hours}시간 동안 유효합니다.</p>
    </div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[AMIC Platform] {display_name}님, 초대가 도착했습니다"
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
    logger.info("Invite email sent", extra={"ctx": {"to": to_email}})
