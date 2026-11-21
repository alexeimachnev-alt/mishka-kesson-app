# -*- coding: utf-8 -*-
"""APNs: регистрация токенов и отправка (JWT + HTTP/2), когда заданы ключи Apple в .env."""

import json
import os
import time
from datetime import datetime, timezone

TOKENS_PATH = os.environ.get("IOS_PUSH_TOKENS_PATH", "ios_push_tokens.json")

_jwt_cache = {"token": None, "exp": 0}

STAFF_PUSH_ROLES = frozenset({"warehouse", "manager", "admin", "owner"})


def _load_tokens() -> dict:
    if not os.path.isfile(TOKENS_PATH):
        return {}
    try:
        with open(TOKENS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_tokens(data: dict) -> None:
    parent = os.path.dirname(os.path.abspath(TOKENS_PATH))
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        with open(TOKENS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[IOS_PUSH] save failed: {e}")


def apns_configured() -> bool:
    return bool(
        os.environ.get("APNS_KEY_ID")
        and os.environ.get("APNS_TEAM_ID")
        and os.environ.get("APNS_KEY_PATH")
        and os.environ.get("APNS_BUNDLE_ID")
        and os.path.isfile(os.environ.get("APNS_KEY_PATH", ""))
    )


def register_device_token(email: str, device_token: str, platform: str = "ios") -> None:
    email = str(email or "").strip().lower()
    device_token = str(device_token or "").strip().lower()
    if not email or not device_token:
        return
    data = _load_tokens()
    entry = data.get(email) or {"tokens": []}
    tokens = [t for t in entry.get("tokens", []) if t.get("token") != device_token]
    tokens.append({
        "token": device_token,
        "platform": platform,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    entry["tokens"] = tokens[-5:]
    data[email] = entry
    _save_tokens(data)


def tokens_for_email(email: str) -> list:
    email = str(email or "").strip().lower()
    data = _load_tokens()
    return [t.get("token") for t in (data.get(email) or {}).get("tokens", []) if t.get("token")]


def token_entries_for_email(email: str) -> list:
    email = str(email or "").strip().lower()
    data = _load_tokens()
    out = []
    for t in (data.get(email) or {}).get("tokens", []):
        tok = str(t.get("token") or "").strip()
        if not tok:
            continue
        out.append({
            "token": tok,
            "platform": str(t.get("platform") or "ios").strip().lower(),
        })
    return out


def fcm_configured() -> bool:
    path = os.environ.get("FCM_SERVICE_ACCOUNT_PATH", "").strip()
    project = os.environ.get("FCM_PROJECT_ID", "").strip()
    return bool(project and path and os.path.isfile(path))


def _send_fcm_device(device_token: str, title: str, body: str) -> bool:
    if not fcm_configured():
        print(f"[FCM] skip (FCM_PROJECT_ID / FCM_SERVICE_ACCOUNT_PATH) → {device_token[:12]}…")
        return False
    # android-{uuid} — заглушка до настройки Firebase в APK
    if device_token.startswith("android-") and len(device_token) < 80:
        print(f"[FCM] skip stub token → {device_token[:24]}…")
        return False
    try:
        import httpx
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError:
        print("[FCM] google-auth or httpx not installed")
        return False

    project_id = os.environ["FCM_PROJECT_ID"].strip()
    sa_path = os.environ["FCM_SERVICE_ACCOUNT_PATH"].strip()
    try:
        creds = service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        creds.refresh(Request())
        access = creds.token
    except Exception as e:
        print(f"[FCM] auth error: {e}")
        return False

    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    headers = {"Authorization": f"Bearer {access}", "Content-Type": "application/json; UTF-8"}
    payload = {
        "message": {
            "token": device_token,
            "notification": {"title": title, "body": body},
            "android": {"priority": "HIGH"},
        }
    }
    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            return True
        print(f"[FCM] {resp.status_code} {device_token[:8]}…: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[FCM] send error: {e}")
        return False


def _apns_base_url() -> str:
    if os.environ.get("APNS_USE_SANDBOX", "").strip() in ("1", "true", "yes"):
        return "https://api.sandbox.push.apple.com"
    return "https://api.push.apple.com"


def _apns_auth_token() -> str:
    now = int(time.time())
    if _jwt_cache.get("token") and _jwt_cache.get("exp", 0) > now + 120:
        return _jwt_cache["token"]

    import jwt

    key_id = os.environ["APNS_KEY_ID"]
    team_id = os.environ["APNS_TEAM_ID"]
    key_path = os.environ["APNS_KEY_PATH"]
    with open(key_path, "r", encoding="utf-8") as f:
        key = f.read()
    token = jwt.encode(
        {"iss": team_id, "iat": now},
        key,
        algorithm="ES256",
        headers={"alg": "ES256", "kid": key_id},
    )
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    _jwt_cache["token"] = token
    _jwt_cache["exp"] = now + 3000
    return token


def _send_apns_device(device_token: str, title: str, body: str) -> bool:
    try:
        import httpx
    except ImportError:
        print("[IOS_PUSH] httpx not installed")
        return False

    topic = os.environ["APNS_BUNDLE_ID"]
    url = f"{_apns_base_url()}/3/device/{device_token}"
    headers = {
        "authorization": f"bearer {_apns_auth_token()}",
        "apns-topic": topic,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }
    payload = {"aps": {"alert": {"title": title, "body": body}, "sound": "default"}}
    try:
        with httpx.Client(http2=True, timeout=12.0) as client:
            resp = client.post(url, headers=headers, content=json.dumps(payload))
        if resp.status_code == 200:
            return True
        print(f"[IOS_PUSH] APNs {resp.status_code} {device_token[:8]}…: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[IOS_PUSH] send error: {e}")
        return False


def send_push_to_email(email: str, title: str, body: str) -> bool:
    entries = token_entries_for_email(email)
    if not entries:
        return False
    ok = False
    for entry in entries:
        platform = entry.get("platform") or "ios"
        token = entry["token"]
        if platform == "android":
            ok = _send_fcm_device(token, title, body) or ok
        else:
            if apns_configured():
                ok = _send_apns_device(token, title, body) or ok
            else:
                print(f"[IOS_PUSH] skip APNs (not configured) → {email}")
    return ok


def send_push_to_emails(emails: list, title: str, body: str) -> int:
    sent = 0
    seen = set()
    for raw in emails:
        em = str(raw or "").strip().lower()
        if not em or em in seen:
            continue
        seen.add(em)
        if send_push_to_email(em, title, body):
            sent += 1
    return sent