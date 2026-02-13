from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .config import AppConfig


def is_email_enabled(cfg: AppConfig) -> bool:
    return bool(cfg.smtp_host and cfg.smtp_user and cfg.smtp_password and cfg.smtp_from and cfg.smtp_to)


def send_report_email(cfg: AppConfig, subject: str, markdown_body: str) -> None:
    msg = EmailMessage()
    msg["From"] = cfg.smtp_from
    msg["To"] = cfg.smtp_to
    msg["Subject"] = subject
    msg.set_content(markdown_body)

    if cfg.smtp_use_ssl:
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=30) as smtp:
            smtp.login(cfg.smtp_user, cfg.smtp_password)
            smtp.send_message(msg)
        return

    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(cfg.smtp_user, cfg.smtp_password)
        smtp.send_message(msg)
