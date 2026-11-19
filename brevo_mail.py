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
    "last_send_http_status": None,
}
_BREVO_AUTH_TTL_OK = 600
_BREVO_AUTH_TTL_FAIL = 120

_RENDER_SMTP_HINT = (
    "На Render исходящий SMTP (порты 587/465) заблокирован — письма только через HTTP API Brevo. "
    "Создайте новый BREVO_API_KEY (xkeysib-…) с правом Send emails; xsmtpsib на Render не сработает."
)

_BREVO_IP_BLOCK_HINT = (
    "Brevo заблокировал запрос с IP сервера Render (защита аккаунта), а не из‑за «плохого» ключа. "
    "В app.brevo.com → Security → Authorized IPs отключите список IP или подтвердите письмо Brevo "
    "о неизвестном IP (Render: 74.220.49.x). Затем снова send_email_code."
)


def _brevo_ip_restriction_error(body: str) -> bool:
    low = (body or "").lower()
    return "unrecognised ip" in low or "unrecognized ip" in low or "unrecognised ip address" in low


def _hosted_on_render() -> bool:
    return bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))


def _smtp_outbound_allowed() -> bool:
    if _clean_env("BREVO_USE_SMTP") == "1" and not _hosted_on_render():
        return True
    if _hosted_on_render():
        return False
    return bool(_brevo_smtp_password())


def _clean_env(var_name: str) -> str:
    raw = os.getenv(var_name) or ""
    return raw.strip().strip("'\"").replace("\n", "").replace("\r", "")


def _brevo_api_key() -> str:
    return _clean_env("BREVO_API_KEY")


def _brevo_smtp_password() -> str:
    """SMTP-ключ xsmtpsib-… (отдельно или ошибочно в BREVO_API_KEY)."""
    smtp = _clean_env("BREVO_SMTP_KEY")
    if smtp:
        return smtp
    api = _brevo_api_key()
    if api.startswith("xsmtpsib-"):
        return api
    return ""


def delivery_configured() -> bool:
    sender = _clean_env("BREVO_SENDER_EMAIL")
    brevo = sender and (_brevo_api_key().startswith("xkeysib-") or _brevo_smtp_password())
    smtp = _clean_env("SMTP_EMAIL") and _clean_env("SMTP_PASSWORD")
    return bool(brevo or smtp)


def brevo_configured() -> bool:
    return bool(_clean_env("BREVO_SENDER_EMAIL") and (_brevo_api_key() or _brevo_smtp_password()))


def brevo_public_diagnostics() -> dict:
    """Без секретов: помогает понять, почему brevo_auth_ok=false на Render."""
    key = _brevo_api_key()
    sender = _clean_env("BREVO_SENDER_EMAIL")
    looks_api = key.startswith("xkeysib-")
    looks_smtp_key = key.startswith("xsmtpsib-") or bool(_clean_env("BREVO_SMTP_KEY"))
    last_send = _brevo_auth_cache.get("last_send_http_status")
    diag = {
        "sender_email_set": bool(sender),
        "sender_email_domain": sender.split("@")[-1] if "@" in sender else "",
        "api_key_length": len(key),
        "api_key_starts_with_xkeysib": looks_api,
        "api_key_is_smtp_key_xsmtpsib": looks_smtp_key,
        "brevo_smtp_key_set": bool(_clean_env("BREVO_SMTP_KEY")),
        "render_smtp_blocked": _hosted_on_render(),
        "last_brevo_http_status": _brevo_auth_cache.get("http_status"),
        "last_brevo_send_status": last_send,
        "last_brevo_error": (_brevo_auth_cache.get("body_snippet") or "")[:120],
        "hint": "",
    }
    snippet = diag.get("last_brevo_error") or ""
    if _brevo_ip_restriction_error(snippet):
        diag["hint"] = _BREVO_IP_BLOCK_HINT
        diag["brevo_ip_authorization_required"] = True
    elif _hosted_on_render() and not diag["hint"]:
        diag["hint"] = _RENDER_SMTP_HINT
    if looks_smtp_key and not looks_api:
        diag["hint"] = (
            "В BREVO_API_KEY лежит xsmtpsib (SMTP). На Render SMTP не работает — "
            "создайте xkeysib API key (Transactional → API Keys) и положите в BREVO_API_KEY."
        )
    elif last_send == 401 and not _brevo_ip_restriction_error(snippet):
        diag["hint"] = (
            "Brevo отклоняет API-ключ (401). Создайте НОВЫЙ xkeysib с правом Send emails "
            "и обновите BREVO_API_KEY на Render."
        )
    elif not key and not _brevo_smtp_password():
        diag["hint"] = "Добавьте BREVO_API_KEY (xkeysib) или BREVO_SMTP_KEY (xsmtpsib) и передеплойте."
    elif diag["last_brevo_http_status"] == 403:
        diag["hint"] = "Brevo 403: включите Send transactional emails у API key."
    elif diag["last_brevo_http_status"] == 402:
        diag["hint"] = "Brevo 402: лимит/оплата — app.brevo.com."
    else:
        diag["hint"] = "См. last_brevo_send_status и подтвердите отправителя в Brevo → Senders."
    free_mail = {"icloud.com", "gmail.com", "mail.ru", "yandex.ru", "bk.ru", "inbox.ru"}
    if sender and sender.split("@")[-1].lower() in free_mail:
        diag["sender_free_mail_hint"] = (
            "Адрес BREVO_SENDER_EMAIL должен быть Verified в Brevo → Senders."
        )
    return diag


def _brevo_probe_send_api(api_key: str) -> tuple[bool, int, str]:
    """Пустой POST: 401 = ключ мёртвый; 400 = ключ принят Brevo."""
    if not api_key.startswith("xkeysib-"):
        return False, 0, "not_xkeysib"
    headers = {"api-key": api_key, "Content-Type": "application/json", "accept": "application/json"}
    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers=headers,
            json={},
            timeout=10,
        )
        body = (resp.text or "")[:200]
        if resp.status_code == 401:
            return False, 401, body
        if resp.status_code in (200, 201, 400, 402):
            return True, resp.status_code, "send_api_reachable"
        if resp.status_code == 403:
            return False, 403, body
        return False, resp.status_code, body
    except Exception as e:
        return False, 0, str(e)[:200]


def brevo_auth_ok(force: bool = False) -> bool:
    """Ключ реально пригоден для отправки (probe POST /smtp/email)."""
    if not brevo_configured():
        return False
    now = time.time()
    if not force and _brevo_auth_cache["ok"] is not None:
        ttl = _BREVO_AUTH_TTL_OK if _brevo_auth_cache["ok"] else _BREVO_AUTH_TTL_FAIL
        if now - _brevo_auth_cache["checked_at"] < ttl:
            return bool(_brevo_auth_cache["ok"])

    api_key = _brevo_api_key()
    ok = False
    status = 0
    snippet = ""

    if api_key.startswith("xkeysib-"):
        ok, status, snippet = _brevo_probe_send_api(api_key)
    elif _brevo_smtp_password() and _smtp_outbound_allowed():
        ok, status, snippet = True, 200, "smtp_key_only"
    elif _brevo_smtp_password() and _hosted_on_render():
        ok, status, snippet = False, 0, "smtp_blocked_on_render"

    _brevo_auth_cache["http_status"] = status
    _brevo_auth_cache["body_snippet"] = snippet
    _brevo_auth_cache["ok"] = ok
    _brevo_auth_cache["checked_at"] = now
    if not ok:
        print(f"[BREVO AUTH] probe failed {status}: {snippet}")
    return ok


def _brevo_error_message(status_code: int, body: str) -> str:
    lowered = (body or "").lower()
    if status_code == 401 and _brevo_ip_restriction_error(body):
        return _BREVO_IP_BLOCK_HINT
    if status_code == 401:
        base = (
            "Brevo отклонил API-ключ (401). Создайте новый xkeysib (Send emails) "
            "в Brevo → API Keys и вставьте в BREVO_API_KEY на Render одной строкой."
        )
        if _hosted_on_render():
            return f"{base} SMTP (xsmtpsib) на Render недоступен."
        return base
    if status_code == 403:
        return (
            "Brevo 403: у ключа нет права отправки. "
            "Включите Send transactional emails для API key."
        )
    if status_code == 400 and ("sender" in lowered or "not valid" in lowered or "inactive" in lowered):
        return (
            "Отправитель не подтверждён в Brevo. "
            "BREVO_SENDER_EMAIL должен быть Verified в Brevo → Senders."
        )
    return f"Brevo отклонил отправку ({status_code}). Проверьте ключ и отправителя."


def _send_via_brevo_http(
    api_key: str, sender_email: str, sender_name: str, target_email: str, subject: str, html_body: str
) -> tuple[bool, int, str]:
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
        detail = resp.text or ""
        _brevo_auth_cache["last_send_http_status"] = resp.status_code
        if resp.status_code in (200, 201):
            return True, resp.status_code, "Код отправлен на вашу почту. Проверьте «Спам», если нет во входящих."
        print(f"[BREVO HTTP] {resp.status_code} {detail[:300]}")
        if resp.status_code == 401:
            _brevo_auth_cache["ok"] = False
            _brevo_auth_cache["checked_at"] = time.time()
            _brevo_auth_cache["http_status"] = 401
            _brevo_auth_cache["body_snippet"] = detail[:200]
        return False, resp.status_code, _brevo_error_message(resp.status_code, detail)
    except Exception as e:
        print(f"[BREVO HTTP ERR] {e}")
        return False, 0, f"Ошибка связи с Brevo: {e}"


def _send_via_brevo_smtp(
    sender_email: str, sender_name: str, target_email: str, subject: str, html_body: str
) -> tuple[bool, str]:
    smtp_pass = _brevo_smtp_password()
    if not smtp_pass:
        return False, "SMTP-ключ Brevo не задан (BREVO_SMTP_KEY)."
    login = _clean_env("BREVO_SMTP_LOGIN") or sender_email
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = target_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(login, smtp_pass)
            server.sendmail(sender_email, [target_email], msg.as_string())
        _brevo_auth_cache["last_send_http_status"] = 200
        return True, "Код отправлен на вашу почту. Проверьте «Спам», если нет во входящих."
    except Exception as e:
        print(f"[BREVO SMTP ERR] {e}")
        _brevo_auth_cache["last_send_http_status"] = 0
        err = str(e).lower()
        if _hosted_on_render() and ("timed out" in err or "timeout" in err):
            return False, _RENDER_SMTP_HINT
        return False, (
            f"Ошибка Brevo SMTP: {e}. "
            "Проверьте BREVO_SMTP_LOGIN и BREVO_SMTP_KEY (только вне Render)."
        )


def send_html_email(target_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    target_email = str(target_email or "").strip().lower()
    if not target_email or "@" not in target_email:
        return False, "Некорректный Email"

    api_key = _brevo_api_key()
    sender_email = _clean_env("BREVO_SENDER_EMAIL")
    sender_name = _clean_env("BREVO_SENDER_NAME") or "ПК МИШКА"
    smtp_pass = _brevo_smtp_password()

    if (
        sender_email
        and smtp_pass
        and not api_key.startswith("xkeysib-")
        and _smtp_outbound_allowed()
    ):
        ok, msg = _send_via_brevo_smtp(sender_email, sender_name, target_email, subject, html_body)
        if ok:
            return True, msg
        if not api_key:
            return False, msg

    if sender_email and smtp_pass and _hosted_on_render() and not api_key.startswith("xkeysib-"):
        return False, _RENDER_SMTP_HINT

    if api_key.startswith("xkeysib-") and sender_email:
        ok, status, user_msg = _send_via_brevo_http(
            api_key, sender_email, sender_name, target_email, subject, html_body
        )
        if ok:
            return True, user_msg
        if status in (401, 403) and smtp_pass and _smtp_outbound_allowed():
            print("[BREVO] HTTP failed, trying SMTP relay")
            return _send_via_brevo_smtp(sender_email, sender_name, target_email, subject, html_body)
        if status in (401, 403) and smtp_pass and _hosted_on_render():
            return False, f"{user_msg} {_RENDER_SMTP_HINT}"
        return False, user_msg

    smtp_user = _clean_env("SMTP_EMAIL")
    smtp_pass_legacy = _clean_env("SMTP_PASSWORD")
    if smtp_user and smtp_pass_legacy:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = target_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            smtp_host = _clean_env("SMTP_HOST") or "smtp.yandex.ru"
            smtp_port = int(_clean_env("SMTP_PORT") or "465")
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12) as server:
                server.login(smtp_user, smtp_pass_legacy)
                server.sendmail(smtp_user, target_email, msg.as_string())
            return True, "Код отправлен на вашу почту."
        except Exception as e:
            print(f"[SMTP SEND ERR] {e}")
            return False, f"Ошибка SMTP: {e}"

    return False, "Почта на сервере не настроена (Brevo API или BREVO_SMTP_KEY на Render)."