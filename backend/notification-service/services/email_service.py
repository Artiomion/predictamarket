"""Email notification service — SendGrid API or SMTP fallback.

Sends transactional emails for:
- Price alerts triggered
- Earnings reminders
- Forecast ready notifications

All sending runs in asyncio.to_thread to avoid blocking the event loop.
"""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
import structlog

from shared.config import settings

logger = structlog.get_logger()

# HTML email template
ALERT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: 'DM Sans', Arial, sans-serif; background: #0A0A0F; color: #E8E8ED; padding: 20px; }}
  .card {{ background: #12121A; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 24px; max-width: 500px; margin: 0 auto; }}
  .ticker {{ font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 600; }}
  .signal {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .buy {{ background: rgba(0,255,136,0.15); color: #00FF88; }}
  .sell {{ background: rgba(255,51,102,0.15); color: #FF3366; }}
  .price {{ font-size: 24px; font-weight: 700; }}
  .muted {{ color: #6B6B80; font-size: 13px; }}
  .cta {{ display: inline-block; background: linear-gradient(135deg, #00D4AA, #00A3FF); color: #0A0A0F; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 16px; }}
</style></head>
<body>
<div class="card">
  <p class="muted">PredictaMarket Alert</p>
  <h2 style="margin:8px 0">{title}</h2>
  <p>{body}</p>
  <a href="https://predictamarket.com/stocks/{ticker}" class="cta">View {ticker} →</a>
  <p class="muted" style="margin-top:24px">You received this because you set a price alert on PredictaMarket.</p>
</div>
</body>
</html>
"""


async def send_email(
    to_email: str,
    subject: str,
    title: str,
    body: str,
    ticker: str = "",
) -> bool:
    """Send email notification. Returns True on success."""
    if not settings.EMAIL_ENABLED:
        await logger.ainfo("email_disabled", to=to_email, subject=subject)
        return False

    html = ALERT_TEMPLATE.format(title=title, body=body, ticker=ticker)

    if settings.SENDGRID_API_KEY:
        return await _send_via_sendgrid(to_email, subject, html)
    elif settings.SMTP_HOST:
        return await asyncio.to_thread(_send_via_smtp_sync, to_email, subject, html)
    else:
        await logger.awarning("no_email_provider", to=to_email)
        return False


async def _send_via_sendgrid(to_email: str, subject: str, html: str) -> bool:
    """Send via SendGrid v3 API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": settings.EMAIL_FROM, "name": settings.EMAIL_FROM_NAME},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html}],
                },
                timeout=10.0,
            )
        if response.status_code in (200, 202):
            await logger.ainfo("email_sent_sendgrid", to=to_email, subject=subject)
            return True
        else:
            await logger.aerror("sendgrid_error", status=response.status_code, body=response.text[:200])
            return False
    except Exception as exc:
        await logger.aerror("sendgrid_exception", to=to_email, error=str(exc))
        return False


def _send_via_smtp_sync(to_email: str, subject: str, html: str) -> bool:
    """Send via SMTP (runs in thread pool)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())

        structlog.get_logger().info("email_sent_smtp", to=to_email, subject=subject)
        return True
    except Exception as exc:
        structlog.get_logger().error("smtp_error", to=to_email, error=str(exc))
        return False
