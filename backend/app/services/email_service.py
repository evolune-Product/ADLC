"""
Transactional email over SMTP.

No third-party dependency: any provider (SES, Postmark, Resend, Mailgun,
corporate relay) speaks SMTP, which matters for the self-hosted tier where
outbound calls to a SaaS mail API may not be permitted. When SMTP is not
configured, sends are logged and skipped so local development never breaks.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger(__name__)

_ACCENT = "#E8632A"
_SEVERITY_COLOR = {"info": "#0F0F0F", "warning": _ACCENT, "critical": "#C0392B"}


def is_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def send(*, to: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
    if not is_configured():
        log.info("[email skipped — SMTP not configured] to=%s subject=%s", to, subject)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        if settings.smtp_use_ssl:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            if settings.smtp_use_tls:
                server.starttls()
        with server:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        log.exception("Failed to send email to %s", to)
        return False


def render(title: str, body: str, url: str, severity: str = "info") -> str:
    """Plain, warm-cream HTML matching the product's design system."""
    color = _SEVERITY_COLOR.get(severity, "#0F0F0F")
    return f"""\
<div style="background:#F5EFE6;padding:32px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <div style="max-width:520px;margin:0 auto;background:#fff;border:1px solid #E5DDD0;border-radius:6px;padding:28px">
    <p style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#8a8378;margin:0 0 10px;font-weight:600">
      Agentic SDLC
    </p>
    <h1 style="font-size:19px;color:#0C0C0C;margin:0 0 12px;font-weight:600">{title}</h1>
    <p style="font-size:14px;line-height:1.6;color:#4a4a4a;margin:0 0 22px;white-space:pre-wrap">{body}</p>
    <a href="{url}" style="display:inline-block;background:{color};color:#fff;text-decoration:none;
       padding:10px 20px;border-radius:6px;font-size:14px;font-weight:500">Open in Agentic SDLC</a>
    <p style="font-size:12px;color:#8a8378;margin:24px 0 0;border-top:1px solid #E5DDD0;padding-top:14px">
      You are receiving this because you are a member of this workspace.
      Manage notifications in Settings.
    </p>
  </div>
</div>"""
