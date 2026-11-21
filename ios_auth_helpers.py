# -*- coding: utf-8 -*-
"""Shared authentication and authorization helpers for the native iOS client."""
import os
import time
import secrets
from werkzeug.security import check_password_hash, generate_password_hash

from admin_config import OWNER_ADMIN_ID, get_user_modifier

OTP_TTL_SECONDS = int(os.getenv("EMAIL_OTP_TTL", "600"))

STAFF_PRIVILEGED_ROLES = frozenset({"owner", "admin", "manager", "warehouse", "auditor"})
STAFF_MANAGE_ROLES = frozenset({"owner", "admin"})
STAFF_ACCOUNT_ROLES = frozenset({"owner", "admin", "manager", "warehouse", "auditor"})
STAFF_MODIFY_ORDER_ROLES = frozenset({"owner", "admin", "manager", "warehouse"})


def normalize_phone_digits(p: str) -> str:
    digits = "".join(ch for ch in str(p or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    return digits


def issue_session_token(user_id: str) -> str:
    raw = f"mishka_ios_{user_id}_{secrets.token_hex(16)}"
    return raw


def store_otp(otp_store: dict, email: str, code: str) -> None:
    otp_store[email] = {
        "code": str(code),
        "expires_at": time.time() + OTP_TTL_SECONDS,
    }


def verify_otp(otp_store: dict, email: str, code: str) -> bool:
    entry = otp_store.get(email)
    if not entry:
        return False
    if time.time() > float(entry.get("expires_at", 0)):
        otp_store.pop(email, None)
        return False
    ok = str(entry.get("code", "")) == str(code).strip()
    if ok:
        otp_store.pop(email, None)
    return ok


def user_payload_from_record(record: dict) -> dict:
    uid = str(record.get("id") or record.get("user_id") or "")
    discount = get_user_modifier(uid)
    token = record.get("token") or issue_session_token(uid)
    return {
        "id": uid,
        "email": record.get("email", ""),
        "phone": record.get("phone", ""),
        "name": record.get("name", "Заказчик"),
        "company": record.get("company", ""),
        "role": record.get("role", "client"),
        "token": token,
        "personalDiscount": discount,
    }


def is_privileged_role(role: str) -> bool:
    return str(role or "").lower() in STAFF_PRIVILEGED_ROLES


def can_manage_orders(role: str) -> bool:
    """Просмотр всех заказов (склад, менеджер, аудитор)."""
    r = str(role or "").lower()
    return r in {"owner", "admin", "manager", "warehouse", "auditor"}


def client_owns_order(order: dict, *, email: str = "", phone: str = "", user_id: str = "") -> bool:
    """Принадлежит ли заказ клиенту (email / id / телефон, в т.ч. старые записи)."""
    raw = order.get("raw_data") or {}
    em = str(email or "").strip().lower()
    uid = str(user_id or "").strip()
    req_phone = normalize_phone_digits(phone)
    ord_email = str(order.get("client_email") or raw.get("email") or "").strip().lower()
    ord_uid = str(order.get("client_id", "")).strip()
    ord_phone = normalize_phone_digits(order.get("phone", ""))
    uid_digits = normalize_phone_digits(uid)

    if em and ord_email and em == ord_email:
        return True
    if uid and ord_uid and uid == ord_uid:
        return True
    if uid_digits and ord_phone and uid_digits == ord_phone:
        return True
    if req_phone and ord_phone and req_phone == ord_phone:
        return True
    # частичное совпадение, если в заказе телефон с форматированием
    if phone and phone.strip() and phone in str(order.get("phone", "")):
        return True
    # Telegram / legacy: client_id — числовой chat_id, в профиле id = телефон
    try:
        if ord_uid and ord_uid not in ("0", "", "Не определен") and uid and str(ord_uid) == str(uid):
            return True
    except Exception:
        pass
    return False


def can_modify_orders(role: str) -> bool:
    """Галочки сборки, смена статуса, отмена."""
    return str(role or "").lower() in STAFF_MODIFY_ORDER_ROLES


def find_staff_login(identifier: str, users_db: dict, builtin: dict):
    """Вход по email или полю login (например 19652200, sklad1)."""
    key = str(identifier or "").strip().lower()
    if not key:
        return None, None
    merged = {**builtin, **users_db}
    if key in merged and str(merged[key].get("role", "client")).lower() != "client":
        return key, merged[key]
    for email, rec in merged.items():
        if str(rec.get("login", "")).strip().lower() == key:
            return email, rec
        if str(rec.get("phone", "")).replace("+", "").endswith(key) and key.isdigit():
            if str(rec.get("role", "client")).lower() != "client":
                return email, rec
    return None, None


def can_edit_catalog(role: str, user_id: str = "") -> bool:
    r = str(role or "").lower()
    if r in {"owner", "admin"}:
        return True
    try:
        return user_id and int(str(user_id).strip()) == OWNER_ADMIN_ID
    except (ValueError, TypeError):
        return False


def map_order_status_for_ios(internal: str) -> str:
    s = str(internal or "active").lower()
    mapping = {
        "active": "in_assembly",
        "in_assembly": "in_assembly",
        "completed": "assembled",
        "assembled": "assembled",
        "paid": "paid_issued",
        "cancelled": "cancelled",
    }
    return mapping.get(s, s)


def hash_password(plain: str) -> str:
    return generate_password_hash(str(plain or ""), method="pbkdf2:sha256")


def verify_password(stored: str, provided: str) -> bool:
    if not stored or not provided:
        return False
    stored_s = str(stored)
    if stored_s.startswith("pbkdf2:") or stored_s.startswith("scrypt:"):
        return check_password_hash(stored_s, provided)
    return stored_s == provided


def can_manage_staff(role: str) -> bool:
    return str(role or "").lower() in STAFF_MANAGE_ROLES


def staff_record_public(record: dict) -> dict:
    role = str(record.get("role", "manager")).lower()
    if role == "owner":
        role = "admin"
    return {
        "id": str(record.get("id") or ""),
        "email": str(record.get("email") or ""),
        "name": str(record.get("name") or ""),
        "phone": str(record.get("phone") or ""),
        "role": role,
        "isActive": not bool(record.get("blocked", False)),
    }


def resolve_user_by_token(token: str, users_db: dict, builtin: dict):
    token = str(token or "").strip()
    if not token:
        return None
    merged = {**builtin, **users_db}
    for rec in merged.values():
        if str(rec.get("token") or "") == token:
            return dict(rec)
    if token.startswith("mishka_ios_"):
        suffix = token[len("mishka_ios_") :]
        uid = suffix.split("_", 1)[0] if suffix else ""
        if uid:
            for rec in merged.values():
                if str(rec.get("id") or "") == uid:
                    return dict(rec)
    return None


def user_from_bearer(request, users_db: dict, builtin: dict):
    auth = request.headers.get("Authorization", "") or ""
    if auth.lower().startswith("bearer "):
        return resolve_user_by_token(auth[7:].strip(), users_db, builtin)
    return None


def map_payment_type_ios(payment_type: str) -> str:
    p = str(payment_type or "").lower()
    if "cash" in p or "налич" in p:
        return "cash"
    if "invoice" in p or "безнал" in p or "счёт" in p or "счет" in p:
        return "invoice"
    if "перевод" in p or "bank" in p:
        return "bank_transfer"
    return payment_type or ""