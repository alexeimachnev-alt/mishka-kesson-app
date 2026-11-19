# -*- coding: utf-8 -*-
"""Brevo (Sendinblue) transactional email for iOS auth."""
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

_brevo_auth_cache = {
    "ok": None,
    "checked_at": 0.0,
    "http_status": None,
    "body_snippet": "",
}
_BREVO_AUTH_TTL_OK = 600
_BREVO_AUTH_TTL_FAIL = 45


def _clean_env(var_name: str) -> str:
    raw = os.getenv(var_name) or ""
    return raw.strip().strip("'\"").replace("\n", "").replace("\r", "")


def delivery_configured() -> bool:
    brevo = _clean_env("BREVO_API_KEY") and _clean_env("BREVO_SENDER_EMAIL")
    smtp = _clean_env("SMTP_EMAIL") and _clean_env("SMTP_PASSWORD")
    return bool(brevo or smtp)


def brevo_configured() -> bool:
    return bool(_clean_env("BREVO_API_KEY") and _clean_env("BREVO_SENDER_EMAIL"))


def brevo_public_diagnostics() -> dict:
    """Без секретов: помогает понять, почему brevo_auth_ok=false на Render."""
    key = _clean_env("BREVO_API_KEY")
    sender = _clean_env("BREVO_SENDER_EMAIL")
    looks_api = key.startswith("xkeysib-")
    looks_smtp_key = key.startswith("xsmtpsib-")
    diag = {
        "sender_email_set": bool(sender),
        "sender_email_domain": sender.split("@")[-1] if "@" in sender else "",
        "api_key_length": len(key),
        "api_key_starts_with_xkeysib": looks_api,
        "api_key_is_smtp_key_xsmtpsib": looks_smtp_key,
        "last_brevo_http_status": _brevo_auth_cache.get("http_status"),
        "last_brevo_error": (_brevo_auth_cache.get("body_snippet") or "")[:120],
        "hint": (
            "Замените xsmtpsib- на API key xkeysib- в Brevo → Transactional → API keys"
            if looks_smtp_key
            else (
                "Добавьте BREVO_API_KEY (xkeysib-…) и передеплойте"
                if not key
                else (
                    "Ключ не прошёл GET /v3/account — создайте новый API key в Brevo"
                    if not looks_api
                    else "Ключ есть, но Brevo отклоняет — пересоздайте ключ или проверьте аккаунт"
                )
            )
        ),
    }
    if diag["last_brevo_http_status"] == 401:
        diag["hint"] = (
            "Brevo вернул 401: ключ недействителен, отозван или скопирован не полностью. "
            "Создайте НОВЫЙ API key (xkeysib) и вставьте в Render одной строкой без кавычек."
        )
    elif diag["last_brevo_http_status"] == 403:
        if "scoped_key" in (diag.get("last_brevo_error") or ""):
            diag["hint"] = "Ключ ограниченный (только отправка) — это нормально, почта должна работать."
        else:
            diag["hint"] = "Brevo 403: включите у API key право Send transactional emails."
    elif diag["last_brevo_http_status"] == 402:
        diag["hint"] = "Brevo 402: лимит/оплата — проверьте план и квоты на app.brevo.com."
    return diag


def _brevo_validate_api_key(api_key: str) -> tuple[bool, int, str]:
    """
    Полный ключ → GET /v3/account = 200.
    Ограниченный (только transactional send) → /account 403 permission_denied — это нормально.
    """
    headers = {"api-key": api_key, "accept": "application/json"}
    try:
        resp = requests.get(
            "https://api.brevo.com/v3/account",
            headers=headers,
            timeout=8,
        )
        body = (resp.text or "")
        if resp.status_code == 200:
            return True, 200, body[:200]
        if resp.status_code == 401:
            return False, 401, body[:200]
        if resp.status_code == 403 and "account" in body.lower() and "permission" in body.lower():
            senders = requests.get(
                "https://api.brevo.com/v3/senders",
                headers=headers,
                timeout=8,
                params={"limit": 1},
            )
            if senders.status_code == 200:
                return True, 200, "scoped_key: senders_ok"
            return True, 403, "scoped_key: transactional_send_only"
        return False, resp.status_code, body[:200]
    except Exception as e:
        return False, 0, str(e)[:200]


def brevo_auth_ok(force: bool = False) -> bool:
    """Проверка API-ключа (кэш)."""
    if not brevo_configured():
        return False
    now = time.time()
    if not force and _brevo_auth_cache["ok"] is not None:
        ttl = _BREVO_AUTH_TTL_OK if _brevo_auth_cache["ok"] else _BREVO_AUTH_TTL_FAIL
        if now - _brevo_auth_cache["checked_at"] < ttl:
            return bool(_brevo_auth_cache["ok"])

    api_key = _clean_env("BREVO_API_KEY")
    ok, status, snippet = _brevo_validate_api_key(api_key)
    _brevo_auth_cache["http_status"] = status
    _brevo_auth_cache["body_snippet"] = snippet
    if not ok:
        print(f"[BREVO AUTH] validate failed {status}: {snippet}")

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