# -*- coding: utf-8 -*-
"""Shared authentication and authorization helpers for the native iOS client."""
import os
import time
import secrets
from admin_config import OWNER_ADMIN_ID, get_user_modifier

OTP_TTL_SECONDS = int(os.getenv("EMAIL_OTP_TTL", "600"))

STAFF_PRIVILEGED_ROLES = frozenset({"owner", "admin", "manager", "warehouse"})


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
    r = str(role or "").lower()
    return r in {"owner", "admin", "manager", "warehouse"}


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


def map_payment_type_ios(payment_type: str) -> str:
    p = str(payment_type or "").lower()
    if "cash" in p or "налич" in p:
        return "cash"
    if "invoice" in p or "безнал" in p or "счёт" in p or "счет" in p:
        return "invoice"
    if "перевод" in p or "bank" in p:
        return "bank_transfer"
    return payment_type or ""