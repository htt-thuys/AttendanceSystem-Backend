import asyncio
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from core.config import settings

logger = logging.getLogger(__name__)


def is_email_enabled() -> bool:
    return bool(settings.EMAIL_ENABLED and settings.SMTP_HOST)


async def send_email(
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    """Send one plain-text email using configured SMTP settings."""
    if not to_email or not is_email_enabled():
        return False

    try:
        await asyncio.to_thread(_send_email_sync, to_email, subject, body)
        return True
    except Exception:
        logger.warning("Email sending failed for %s", to_email, exc_info=True)
        return False


async def send_bulk_email(
    recipients: list[str],
    subject: str,
    body: str,
) -> int:
    sent_count = 0
    for recipient in recipients:
        if await send_email(recipient, subject, body):
            sent_count += 1
    return sent_count


def _send_email_sync(to_email: str, subject: str, body: str) -> None:
    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    if not from_email:
        raise RuntimeError("SMTP_FROM_EMAIL or SMTP_USERNAME must be configured")

    message = EmailMessage()
    message["From"] = formataddr((settings.SMTP_FROM_NAME, from_email))
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    ) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)
