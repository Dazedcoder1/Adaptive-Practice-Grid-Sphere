"""Outbound email. "console" backend logs the message (and keeps it in memory for tests);
"smtp" sends it. Set EMAIL_BACKEND=smtp and SMTP_* in .env for real delivery."""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.config.settings import settings

log = logging.getLogger("app.email")


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str


# Console backend keeps the most recent messages so tests (and dev tools) can read links.
outbox: list[SentEmail] = []


def send_email(to: str, subject: str, body: str) -> None:
    if settings.email_backend == "smtp":
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
        return

    outbox.append(SentEmail(to, subject, body))
    del outbox[:-50]
    log.warning(
        "\n──── EMAIL (console backend) ────\nTo: %s\nSubject: %s\n\n%s\n────", to, subject, body
    )
