# -*- coding: utf-8 -*-
"""Brevo (Sendinblue) transactional email for iOS auth."""
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

_brevo_auth_cache = {"ok": None, "checked_at": 0.0}
_BREVO_AUTH_TTL = 600


def _clean_env(var_name: str) -> str:
    raw = os.getenv(var_name) or ""
    return raw.strip().strip("'\"").replace("\n", "").replace("\r", "")


def delivery_configured() -> bool:
    brevo = _clean_env("BREVO_API_KEY") and _clean_env("BREVO_SENDER_EMAIL")
    smtp = _clean_env("SMTP_EMAIL") and _clean_env("SMTP_PASSWORD")
    return bool(brevo or smtp)


def brevo_configured() -> bool:
    return bool(_clean_env("BREVO_API_KEY") and _clean_env("BREVO_SENDER_EMAIL"))


def brevo_auth_ok(force: bool = False) -> bool:
    """Проверка API-ключа через GET /v3/account (кэш 10 мин)."""
    if not brevo_configured():
        return False
    now = time.time()
    if not force and _brevo_auth_cache["ok"] is not None and now - _brevo_auth_cache["checked_at"] < _BREVO_AUTH_TTL:
        return bool(_brevo_auth_cache["ok"])

    api_key = _clean_env("BREVO_API_KEY")
    ok = False
    try:
        resp = requests.get(
            "https://api.brevo.com/v3/account",
            headers={"api-key": api_key, "accept": "application/json"},
            timeout=8,
        )
        ok = resp.status_code == 200
        if not ok:
            print(f"[BREVO AUTH] account check {resp.status_code}: {(resp.text or '')[:200]}")
    except Exception as e:
        print(f"[BREVO AUTH ERR] {e}")

    _brevo_auth_cache["ok"] = ok
    _brevo_auth_cache["checked_at"] = now
    return ok


def _brevo_error_message(status_code: int, body: str) -> str:
    if status_code == 401:
        return (
            "Неверный BREVO_API_KEY на Render (401). "
            "В Brevo: Transactional → API Keys → создайте ключ xkeysib-…, "
            "вставьте в Render без кавычек и передеплойте."
        )
    if status_code == 400 and "sender" in (body or "").lower():
        return (
            "Отправитель не подтверждён в Brevo. "
            "Проверьте BREVO_SENDER_EMAIL в Render и верификацию домена/адреса в Brevo."
        )
    return f"Brevo отклонил отправку ({status_code}). Проверьте API-ключ и sender."


def send_html_email(target_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    target_email = str(target_email or "").strip().lower()
    if not target_email or "@" not in target_email:
        return False, "Некорректный Email"

    api_key = _clean_env("BREVO_API_KEY")
    sender_email = _clean_env("BREVO_SENDER_EMAIL")
    sender_name = _clean_env("BREVO_SENDER_NAME") or "ПК МИШКА"

    if api_key and sender_email:
        if not brevo_auth_ok():
            return False, _brevo_error_message(401, "")
        try:
            resp = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": api_key, "Content-Type": "application/json", "accept": "application/json"},
                json={
                    "sender": {"name": sender_name, "email": sender_email},
                    "to": [{"email": target_email}],
                    "subject": subject,
                    "htmlContent": html_body,
                },
                timeout=15,
            )
            if resp.status_code in (200, 201):
                return True, "Код отправлен на вашу почту. Проверьте «Спам», если нет во входящих."
            detail = resp.text or ""
            print(f"[BREVO] {resp.status_code} {detail[:300]}")
            _brevo_auth_cache["ok"] = False
            _brevo_auth_cache["checked_at"] = time.time()
            return False, _brevo_error_message(resp.status_code, detail)
        except Exception as e:
            print(f"[BREVO SEND ERR] {e}")
            return False, f"Ошибка связи с Brevo: {e}"

    smtp_user = _clean_env("SMTP_EMAIL")
    smtp_pass = _clean_env("SMTP_PASSWORD")
    if smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = target_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            smtp_host = _clean_env("SMTP_HOST") or "smtp.yandex.ru"
            smtp_port = int(_clean_env("SMTP_PORT") or "465")
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, target_email, msg.as_string())
            return True, "Код отправлен на вашу почту."
        except Exception as e:
            print(f"[SMTP SEND ERR] {e}")
            return False, f"Ошибка SMTP: {e}"

    return False, "Почта на сервере не настроена (BREVO_API_KEY + BREVO_SENDER_EMAIL на Render)."