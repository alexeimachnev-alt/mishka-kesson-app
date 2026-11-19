# -*- coding: utf-8 -*-
"""Brevo (Sendinblue) transactional email for iOS auth."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests


def delivery_configured() -> bool:
    brevo = (os.getenv("BREVO_API_KEY") or "").strip() and (os.getenv("BREVO_SENDER_EMAIL") or "").strip()
    smtp = (os.getenv("SMTP_EMAIL") or "").strip() and (os.getenv("SMTP_PASSWORD") or "").strip()
    return bool(brevo or smtp)


def brevo_configured() -> bool:
    return bool((os.getenv("BREVO_API_KEY") or "").strip() and (os.getenv("BREVO_SENDER_EMAIL") or "").strip())


def send_html_email(target_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Send via Brevo HTTP API, fallback SMTP. Returns (ok, user_message)."""
    target_email = str(target_email or "").strip().lower()
    if not target_email or "@" not in target_email:
        return False, "Некорректный Email"

    api_key = (os.getenv("BREVO_API_KEY") or "").strip()
    sender_email = (os.getenv("BREVO_SENDER_EMAIL") or "").strip()
    sender_name = (os.getenv("BREVO_SENDER_NAME") or "ПК МИШКА").strip()

    if api_key and sender_email:
        try:
            resp = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json={
                    "sender": {"name": sender_name, "email": sender_email},
                    "to": [{"email": target_email}],
                    "subject": subject,
                    "htmlContent": html_body,
                },
                timeout=12,
            )
            if resp.status_code in (200, 201):
                return True, "Код отправлен на вашу почту. Проверьте «Спам», если нет во входящих."
            detail = resp.text[:240] if resp.text else str(resp.status_code)
            print(f"[BREVO] {resp.status_code} {detail}")
            return False, f"Brevo отклонил отправку ({resp.status_code}). Проверьте sender и API-ключ."
        except Exception as e:
            print(f"[BREVO SEND ERR] {e}")
            return False, f"Ошибка Brevo: {e}"

    smtp_user = (os.getenv("SMTP_EMAIL") or "").strip()
    smtp_pass = (os.getenv("SMTP_PASSWORD") or "").strip()
    if smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = target_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            smtp_host = os.getenv("SMTP_HOST", "smtp.yandex.ru").strip()
            smtp_port = int(os.getenv("SMTP_PORT", "465"))
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, target_email, msg.as_string())
            return True, "Код отправлен на вашу почту."
        except Exception as e:
            print(f"[SMTP SEND ERR] {e}")
            return False, f"Ошибка SMTP: {e}"

    return False, "Почта на сервере не настроена (нужны BREVO_API_KEY и BREVO_SENDER_EMAIL на Render)."