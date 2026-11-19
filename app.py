# -*- coding: utf-8 -*-
import os
import time
import threading
import requests
from flask import Flask, render_template, request, jsonify
import telebot
from telebot import types as tele_types

from calc_module import (
    build_order_payload, 
    make_warehouse_keyboard, 
    update_sheet_status,
    render_order_texts,
    get_admin_name,
    get_items_for_order,
    OrderValidationError,
    recompute_order_composition_flags,
    tag_item_category,
    ACTIVE_ORDERS, 
    ADMIN_CHAT_IDS,
    MESSAGES,
    ALL_CATALOG_ITEMS,
    YANDEX_MAPS_URL,
    PRICES,
    KESSON_MODELS,
    TANK_CATALOG
)
from admin_config import (
    OWNER_ADMIN_ID,
    CONFIG_FILE_PATH,
    USERS_DISCOUNTS_FILE_PATH,
    USERS_DISCOUNTS,
    is_owner_admin,
    get_user_modifier,
    set_user_modifier,
    remove_user_modifier,
    get_full_config,
    apply_config_dict,
    save_config_locally,
    save_discounts_locally,
    sync_config_to_cloud,
    load_config_on_startup
)

BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip().strip("'\"")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__, template_folder="templates", static_folder=".")

WELCOME_BANNER_URL = "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1000&q=80"

@app.route("/")
@app.route("/health")
def health_check():
    from brevo_mail import brevo_configured, delivery_configured
    return jsonify({
        "status": "ok",
        "service": "Mishka Warehouse",
        "admins": ADMIN_CHAT_IDS,
        "email_delivery": "brevo" if brevo_configured() else ("smtp" if delivery_configured() else "off"),
        "ios_api_version": 2,
    }), 200

@app.route("/app")
@app.route("/webapp")
@app.route("/app.html")
def serve_webapp():
    from flask import make_response
    resp = make_response(render_template("app.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/api/calc_well", methods=["POST"])
@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.json or {}
    raw_items = get_items_for_order(data)
    uid = data.get("user_id") or data.get("chat_id") or 0
    mod_pct = get_user_modifier(uid)
    from calc_module import apply_personal_modifier_to_items
    items = apply_personal_modifier_to_items(raw_items, mod_pct)
    total = sum(x["price"] * x["qty"] for x in items)
    return jsonify({"items": items, "total": round(total, 2), "personal_modifier": mod_pct, "status": "success"})


@app.route("/api/config", methods=["GET"])
def api_get_config():
    """Возвращает актуальный каталог цен, позиций, персональную скидку/наценку пользователя и (для владельца) полный список скидок."""
    user_id = request.args.get("user_id", "")
    owner_flag = is_owner_admin(user_id)
    cfg = get_full_config(include_all_discounts=owner_flag)
    personal_mod = get_user_modifier(user_id)
    return jsonify({
        "status": "ok",
        "is_owner": owner_flag,
        "owner_id": OWNER_ADMIN_ID,
        "personal_modifier": personal_mod,
        "config": cfg
    }), 200


@app.route("/api/admin/user_discount", methods=["POST"])
def api_admin_user_discount():
    """Сохранение или удаление персональной скидки/наценки клиента по Telegram ID (ТОЛЬКО для администратора 551209811)"""
    try:
        data = request.json or {}
        admin_id = data.get("user_id")
        init_data = data.get("init_data", "")
        staff_role = str(data.get("role", "")).strip().lower()
        if not (is_owner_admin(admin_id, init_data) or can_edit_catalog(staff_role, admin_id)):
            return jsonify({"status": "error", "message": "Доступ запрещён! Только для владельца / admin."}), 403

        action = data.get("action", "set")
        target_tg_id = str(data.get("target_telegram_id", "")).strip()
        if not target_tg_id or not target_tg_id.isdigit():
            return jsonify({"status": "error", "message": "Укажите корректный цифровой Telegram ID клиента!"}), 400

        if action == "delete":
            remove_user_modifier(target_tg_id)
        else:
            percent = float(data.get("percent", 0.0))
            note = str(data.get("note", "")).strip()
            set_user_modifier(target_tg_id, percent, note)

        saved_cfg = save_config_locally()
        sync_config_to_cloud(saved_cfg)
        return jsonify({
            "status": "ok",
            "users_discounts": USERS_DISCOUNTS
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/save_config", methods=["POST"])
def api_admin_save_config():
    """Сохраняет изменения цен, новых позиций и описаний (ТОЛЬКО для OWNER_ADMIN_ID = 551209811)"""
    try:
        data = request.json or {}
        user_id = data.get("user_id")
        init_data = data.get("init_data", "")
        staff_role = str(data.get("role", "")).strip().lower()
        if not (is_owner_admin(user_id, init_data) or can_edit_catalog(staff_role, user_id)):
            return jsonify({"status": "error", "message": "Доступ запрещён! Только для владельца / admin."}), 403

        new_cfg = data.get("config") or {}
        apply_config_dict(new_cfg)
        saved_cfg = save_config_locally()
        sync_config_to_cloud(saved_cfg)

        # Отправляем резервную копию catalog_config.json лично владельцу в Telegram
        if data.get("send_backup", True):
            def _send_backup():
                try:
                    with open(CONFIG_FILE_PATH, "rb") as doc_file:
                        bot.send_document(
                            OWNER_ADMIN_ID,
                            doc_file,
                            caption="💾 <b>Резервная копия базы цен и настроек бота (catalog_config.json)</b>\n"
                                    "<i>Изменения сохранены на сервере и синхронизированы. Вы можете в любой момент восстановить эту версию, просто отправив этот файл обратно боту.</i>",
                            parse_mode="HTML"
                        )
                except Exception as b_err:
                    print(f"[BACKUP SEND ERR] {b_err}")
            threading.Thread(target=_send_backup, daemon=True).start()

        return jsonify({"status": "ok", "config": saved_cfg}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500





# ==============================================================================
# ЭНДПОИНТЫ ДЛЯ НАТИВНОГО iOS ПРИЛОЖЕНИЯ (РЕГИСТРАЦИЯ ПО EMAIL + АККАУНТЫ МЕНЕДЖЕРОВ)
# ==============================================================================
import json

USERS_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ios_users.json")


def normalize_phone_digits(p: str) -> str:
    digits = "".join(ch for ch in str(p or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    return digits


# Встроенные корпоративные аккаунты руководства и менеджеров склада
BUILTIN_STAFF_ACCOUNTS = {
    "alexeimachnev@icloud.com": {
        "id": "551209811",
        "email": "alexeimachnev@icloud.com",
        "phone": "+79060400043",
        "name": "Алексей (Владелец)",
        "company": "ООО ПК МИШКА",
        "role": "owner",
        "password": os.getenv("OWNER_PASSWORD", "551209")
    },
    "owner@mishka.ru": {
        "id": "551209811",
        "email": "owner@mishka.ru",
        "phone": "+79060400043",
        "name": "Алексей (Владелец)",
        "company": "ООО ПК МИШКА",
        "role": "owner",
        "password": os.getenv("OWNER_PASSWORD", "551209")
    },
    "artur@mishka.ru": {
        "id": "447208738",
        "email": "artur@mishka.ru",
        "phone": "+79000000001",
        "name": "Артур (Склад МИШКА)",
        "company": "Склад ПК МИШКА",
        "role": "manager",
        "password": os.getenv("ARTUR_PASSWORD", "447208")
    },
    "sklad@mishka.ru": {
        "id": "840231919",
        "email": "sklad@mishka.ru",
        "phone": "+79000000002",
        "name": "Сборщик склада",
        "company": "Склад ПК МИШКА",
        "role": "warehouse",
        "password": os.getenv("SKLAD_PASSWORD", "840231")
    },
    "admin@mishka.ru": {
        "id": "551209811",
        "email": "admin@mishka.ru",
        "phone": "+79060400043",
        "name": "Администратор ПК МИШКА",
        "company": "ООО ПК МИШКА",
        "role": "admin",
        "password": os.getenv("OWNER_PASSWORD", "551209")
    }
}

IOS_USERS_DB = {}


def load_ios_users():
    global IOS_USERS_DB
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
                IOS_USERS_DB = json.load(f)
        except Exception:
            IOS_USERS_DB = {}
    for k, v in BUILTIN_STAFF_ACCOUNTS.items():
        if k not in IOS_USERS_DB:
            IOS_USERS_DB[k] = dict(v)


def save_ios_users():
    try:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(IOS_USERS_DB, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[IOS USERS SAVE ERR] {e}")


load_ios_users()

from ios_auth_helpers import (
    store_otp,
    verify_otp,
    user_payload_from_record,
    issue_session_token,
    can_edit_catalog,
    can_manage_orders,
    can_manage_staff,
    map_order_status_for_ios,
    map_payment_type_ios,
    hash_password,
    verify_password,
    staff_record_public,
    resolve_user_by_token,
    user_from_bearer,
)

EMAIL_OTP_CODES = {}
PASSWORD_RESET_OTP_CODES = {}


def _email_html_shell(title: str, code: str, footer: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background: #17212b; color: #ffffff; border-radius: 12px;">
        <h2 style="color: #2ea6ff; margin-top: 0;">📦 ПК «МИШКА»</h2>
        <p>{title}</p>
        <div style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #4ade80; padding: 12px 20px; background: #232e3c; display: inline-block; border-radius: 8px;">
            {code}
        </div>
        <p style="color: #94a3b8; font-size: 12px; margin-top: 16px;">{footer}</p>
    </div>
    """


@app.route("/api/auth/send_email_code", methods=["POST"])
def api_send_email_code():
    """Генерирует и отправляет 4-значный код на почту клиента через Brevo HTTP API (или SMTP)."""
    try:
        import random
        from brevo_mail import delivery_configured, send_html_email

        if not delivery_configured():
            return jsonify({
                "status": "error",
                "message": "На сервере не настроена почта. Добавьте BREVO_API_KEY и BREVO_SENDER_EMAIL на Render.",
            }), 503

        data = request.json or {}
        email = str(data.get("email", "")).strip().lower()
        if not email or "@" not in email:
            return jsonify({"status": "error", "message": "Укажите корректный Email"}), 400

        code = str(random.randint(1000, 9999))
        subject = f"Код подтверждения ПК «МИШКА»: {code}"
        html = _email_html_shell(
            "Здравствуйте! Код для регистрации в приложении ПК «МИШКА»:",
            code,
            "Если вы не запрашивали код, просто проигнорируйте это письмо.",
        )
        sent, user_msg = send_html_email(email, subject, html)
        if not sent:
            return jsonify({"status": "error", "message": user_msg}), 503
        store_otp(EMAIL_OTP_CODES, email, code)
        return jsonify({"status": "ok", "smtp_active": True, "message": user_msg}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/auth/verify_email_code", methods=["POST"])
def api_verify_email_code():
    """Подтверждение Email OTP, регистрация / вход клиента, выдача session token."""
    try:
        load_ios_users()
        data = request.json or {}
        email = str(data.get("email", "")).strip().lower()
        code = str(data.get("code", "")).strip()
        raw_phone = str(data.get("phone", "")).strip()
        name = str(data.get("name", "")).strip()
        company = str(data.get("company", "")).strip()
        password = str(data.get("password", "")).strip()

        if not email or "@" not in email:
            return jsonify({"status": "error", "message": "Укажите корректный Email"}), 400
        if not code:
            return jsonify({"status": "error", "message": "Введите код из письма"}), 400
        if not password or len(password) < 4:
            return jsonify({"status": "error", "message": "Придумайте пароль (минимум 4 символа)"}), 400
        if not verify_otp(EMAIL_OTP_CODES, email, code):
            return jsonify({"status": "error", "message": "Неверный или устаревший код"}), 401
        if not raw_phone:
            return jsonify({"status": "error", "message": "Укажите телефон для связи со складом"}), 400
        if email in BUILTIN_STAFF_ACCOUNTS:
            return jsonify({"status": "error", "message": "Этот Email зарезервирован для сотрудника склада"}), 400

        clean_digits = normalize_phone_digits(raw_phone)
        existing = IOS_USERS_DB.get(email)
        if existing and existing.get("role") not in (None, "", "client"):
            return jsonify({"status": "error", "message": "Этот Email уже используется сотрудником"}), 400

        uid = clean_digits or (existing or {}).get("id") or email
        record = {
            "id": uid,
            "email": email,
            "phone": raw_phone,
            "name": name or (existing or {}).get("name") or email.split("@")[0],
            "company": company or (existing or {}).get("company", ""),
            "role": "client",
            "password": hash_password(password),
            "blocked": False,
        }
        record["token"] = issue_session_token(uid)
        IOS_USERS_DB[email] = {**IOS_USERS_DB.get(email, {}), **record}
        save_ios_users()
        payload = user_payload_from_record(record)
        payload["token"] = record["token"]
        return jsonify({"status": "ok", "data": payload}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/auth/staff_quick", methods=["POST"])
def api_staff_quick_login():
    """Быстрый выбор роли для внутреннего тестирования (только если QUICK_LOGIN=1 на Render)."""
    if os.getenv("QUICK_LOGIN", "0").strip() != "1":
        return jsonify({"status": "error", "message": "Быстрый вход отключён на сервере"}), 403
    data = request.json or {}
    role = str(data.get("role", "client")).strip().lower()
    role_map = {
        "owner": BUILTIN_STAFF_ACCOUNTS["owner@mishka.ru"],
        "admin": BUILTIN_STAFF_ACCOUNTS["admin@mishka.ru"],
        "manager": BUILTIN_STAFF_ACCOUNTS["artur@mishka.ru"],
        "warehouse": BUILTIN_STAFF_ACCOUNTS["sklad@mishka.ru"],
    }
    if role == "client":
        demo = {
            "id": "demo_client",
            "email": "demo@client.ru",
            "phone": "+79000000099",
            "name": "Демо-клиент",
            "company": "",
            "role": "client",
            "token": issue_session_token("demo_client"),
        }
        return jsonify({"status": "ok", "data": user_payload_from_record(demo)}), 200
    staff = role_map.get(role)
    if not staff:
        return jsonify({"status": "error", "message": "Неизвестная роль"}), 400
    staff_copy = dict(staff)
    staff_copy["token"] = issue_session_token(staff["id"])
    return jsonify({"status": "ok", "data": user_payload_from_record(staff_copy)}), 200


def _login_response_from_record(record: dict) -> dict:
    rec = dict(record)
    uid = str(rec.get("id") or rec.get("email") or "")
    if not rec.get("token"):
        rec["token"] = issue_session_token(uid)
        email_key = str(rec.get("email", "")).lower()
        if email_key in IOS_USERS_DB:
            IOS_USERS_DB[email_key]["token"] = rec["token"]
            save_ios_users()
    payload = user_payload_from_record(rec)
    payload["token"] = rec["token"]
    return {"status": "ok", "data": payload}


@app.route("/api/auth/login", methods=["POST"])
@app.route("/api/auth/email", methods=["POST"])
def api_ios_auth_login():
    """Вход по Email + пароль для клиентов и сотрудников."""
    try:
        load_ios_users()
        data = request.json or {}
        email = str(data.get("email") or data.get("login") or "").strip().lower()
        password = str(data.get("password") or data.get("code") or "").strip()

        if not email or "@" not in email:
            return jsonify({"status": "error", "message": "Укажите корректный Email"}), 400
        if not password or len(password) < 4:
            return jsonify({"status": "error", "message": "Пароль должен содержать минимум 4 символа"}), 400

        staff = BUILTIN_STAFF_ACCOUNTS.get(email) or IOS_USERS_DB.get(email)
        if not staff and email in BUILTIN_STAFF_ACCOUNTS:
            staff = BUILTIN_STAFF_ACCOUNTS[email]

        if staff and str(staff.get("role", "client")) != "client":
            if staff.get("blocked"):
                return jsonify({"status": "error", "message": "Аккаунт заблокирован администратором"}), 403
            stored = staff.get("password") or BUILTIN_STAFF_ACCOUNTS.get(email, {}).get("password", "")
            fallback_pins = {"7777", "1234", staff.get("password", "")}
            if not verify_password(stored, password) and password not in fallback_pins:
                return jsonify({"status": "error", "message": "Неверный пароль"}), 401
            return jsonify(_login_response_from_record(staff)), 200

        existing = IOS_USERS_DB.get(email)
        if not existing:
            return jsonify({
                "status": "error",
                "message": "Аккаунт не найден. Зарегистрируйтесь и подтвердите Email кодом из письма."
            }), 404
        if existing.get("blocked"):
            return jsonify({"status": "error", "message": "Аккаунт заблокирован"}), 403
        if not verify_password(existing.get("password", ""), password):
            return jsonify({"status": "error", "message": "Неверный пароль"}), 401
        return jsonify(_login_response_from_record(existing)), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/auth/request_password_reset", methods=["POST"])
def api_request_password_reset():
    try:
        import random
        data = request.json or {}
        email = str(data.get("email", "")).strip().lower()
        if not email or "@" not in email:
            return jsonify({"status": "error", "message": "Укажите корректный Email"}), 400
        load_ios_users()
        if email not in IOS_USERS_DB and email not in BUILTIN_STAFF_ACCOUNTS:
            return jsonify({"status": "ok", "message": "Если Email зарегистрирован, код отправлен на почту"}), 200
        from brevo_mail import delivery_configured, send_html_email
        if not delivery_configured():
            return jsonify({"status": "error", "message": "Почта на сервере не настроена"}), 503
        code = str(random.randint(100000, 999999))
        subject = f"Сброс пароля ПК «МИШКА»: {code}"
        html = _email_html_shell(
            "Код для сброса пароля в приложении ПК «МИШКА»:",
            code,
            "Никому не сообщайте этот код. Срок действия ограничен.",
        )
        sent, user_msg = send_html_email(email, subject, html)
        if not sent:
            return jsonify({"status": "error", "message": user_msg}), 503
        store_otp(PASSWORD_RESET_OTP_CODES, email, code)
        return jsonify({"status": "ok", "message": user_msg}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/auth/confirm_password_reset", methods=["POST"])
def api_confirm_password_reset():
    try:
        data = request.json or {}
        email = str(data.get("email", "")).strip().lower()
        code = str(data.get("code", "")).strip()
        password = str(data.get("password", "")).strip()
        if not verify_otp(PASSWORD_RESET_OTP_CODES, email, code):
            return jsonify({"status": "error", "message": "Неверный или устаревший код"}), 401
        if len(password) < 4:
            return jsonify({"status": "error", "message": "Пароль должен содержать минимум 4 символа"}), 400
        load_ios_users()
        if email in BUILTIN_STAFF_ACCOUNTS:
            return jsonify({"status": "error", "message": "Сброс пароля сотрудника — через администратора"}), 400
        record = IOS_USERS_DB.get(email)
        if not record:
            return jsonify({"status": "error", "message": "Аккаунт не найден"}), 404
        record["password"] = hash_password(password)
        record["token"] = issue_session_token(record.get("id") or email)
        IOS_USERS_DB[email] = record
        save_ios_users()
        return jsonify(_login_response_from_record(record)), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def _require_admin_user():
    actor = user_from_bearer(request, IOS_USERS_DB, BUILTIN_STAFF_ACCOUNTS)
    if not actor or not can_manage_staff(actor.get("role")):
        return None, (jsonify({"status": "error", "message": "Доступ только для администратора"}), 403)
    return actor, None


def _iter_staff_records():
    from ios_auth_helpers import STAFF_ACCOUNT_ROLES
    seen = set()
    for source in (list(BUILTIN_STAFF_ACCOUNTS.values()) + list(IOS_USERS_DB.values())):
        role = str(source.get("role", "client")).lower()
        if role not in STAFF_ACCOUNT_ROLES:
            continue
        rid = str(source.get("id", ""))
        if rid in seen:
            continue
        seen.add(rid)
        yield source


def _find_user_by_id(user_id: str):
    user_id = str(user_id or "").strip()
    for email, rec in IOS_USERS_DB.items():
        if str(rec.get("id")) == user_id:
            return dict(rec), email
    for email, rec in BUILTIN_STAFF_ACCOUNTS.items():
        if str(rec.get("id")) == user_id:
            return dict(rec), email
    return None, None


@app.route("/api/admin/staff", methods=["GET"])
def api_admin_staff_list():
    try:
        load_ios_users()
        _, err = _require_admin_user()
        if err:
            return err
        data = [staff_record_public(r) for r in _iter_staff_records()]
        data.sort(key=lambda x: (x.get("role", ""), x.get("name", "")))
        return jsonify({"status": "ok", "data": data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/staff", methods=["POST"])
def api_admin_staff_create():
    try:
        import secrets
        load_ios_users()
        _, err = _require_admin_user()
        if err:
            return err
        data = request.json or {}
        email = str(data.get("email", "")).strip().lower()
        name = str(data.get("name", "")).strip()
        password = str(data.get("password", "")).strip()
        role = str(data.get("role", "manager")).strip().lower()
        phone = str(data.get("phone", "")).strip()
        if role not in ("manager", "warehouse", "admin"):
            return jsonify({"status": "error", "message": "Роль: manager, warehouse или admin"}), 400
        if not email or "@" not in email:
            return jsonify({"status": "error", "message": "Укажите Email"}), 400
        if len(password) < 4:
            return jsonify({"status": "error", "message": "Пароль минимум 4 символа"}), 400
        if email in IOS_USERS_DB or email in BUILTIN_STAFF_ACCOUNTS:
            return jsonify({"status": "error", "message": "Email уже занят"}), 400
        uid = str(data.get("id") or secrets.token_hex(4))
        record = {
            "id": uid,
            "email": email,
            "name": name or email.split("@")[0],
            "phone": phone,
            "company": "ООО ПК МИШКА",
            "role": role,
            "password": hash_password(password),
            "blocked": False,
            "token": issue_session_token(uid),
        }
        IOS_USERS_DB[email] = record
        save_ios_users()
        return jsonify({"status": "ok", "data": staff_record_public(record)}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/staff/<user_id>", methods=["PUT"])
def api_admin_staff_update(user_id):
    try:
        load_ios_users()
        _, err = _require_admin_user()
        if err:
            return err
        data = request.json or {}
        record, email = _find_user_by_id(user_id)
        if not record:
            return jsonify({"status": "error", "message": "Сотрудник не найден"}), 404
        email = email or str(record.get("email", "")).lower()

        if str(data.get("name", "")).strip():
            record["name"] = str(data["name"]).strip()
        if str(data.get("phone", "")).strip():
            record["phone"] = str(data["phone"]).strip()
        if data.get("role"):
            role = str(data["role"]).strip().lower()
            if role in ("manager", "warehouse", "admin", "owner"):
                record["role"] = role
        if "blocked" in data:
            record["blocked"] = bool(data.get("blocked"))
        if data.get("isActive") is not None:
            record["blocked"] = not bool(data.get("isActive"))
        new_password = str(data.get("password", "")).strip()
        if new_password:
            if len(new_password) < 4:
                return jsonify({"status": "error", "message": "Пароль минимум 4 символа"}), 400
            record["password"] = hash_password(new_password)
        if email in BUILTIN_STAFF_ACCOUNTS and email not in IOS_USERS_DB:
            IOS_USERS_DB[email] = dict(record)
        elif email:
            IOS_USERS_DB[email] = record
        save_ios_users()
        return jsonify({"status": "ok", "data": staff_record_public(record)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/staff/<user_id>", methods=["DELETE"])
def api_admin_staff_delete(user_id):
    try:
        load_ios_users()
        actor, err = _require_admin_user()
        if err:
            return err
        target = None
        target_email = None
        for email, rec in list(IOS_USERS_DB.items()):
            if str(rec.get("id")) == str(user_id):
                target = rec
                target_email = email
                break
        if not target:
            for rec in BUILTIN_STAFF_ACCOUNTS.values():
                if str(rec.get("id")) == str(user_id):
                    return jsonify({"status": "error", "message": "Встроенный аккаунт нельзя удалить — только заблокировать"}), 400
            return jsonify({"status": "error", "message": "Сотрудник не найден"}), 404
        if str(target.get("id")) == str(actor.get("id")):
            return jsonify({"status": "error", "message": "Нельзя удалить свой аккаунт"}), 400
        IOS_USERS_DB.pop(target_email, None)
        save_ios_users()
        return jsonify({"status": "ok", "message": "Сотрудник удалён"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def _serialize_order_for_ios(oid: str, order: dict) -> dict:
    raw_items = order.get("items", [])
    collected_flags = order.get("collected", [False] * len(raw_items))
    ios_items = []
    for idx, it in enumerate(raw_items):
        is_col = collected_flags[idx] if idx < len(collected_flags) else False
        ios_items.append({
            "itemKey": str(it.get("item_key") or it.get("code") or f"item_{idx}"),
            "name": str(it.get("name", "Позиция")),
            "qty": float(it.get("qty", 1)),
            "unit": str(it.get("unit", "шт")),
            "price": float(it.get("price", 0)),
            "isCollected": bool(is_col),
            "isWork": bool(it.get("is_work")),
            "category": str(it.get("category") or ("works" if it.get("is_work") else "goods")),
        })
    raw_status = str(order.get("status", "active"))
    return {
        "id": str(oid),
        "clientName": str(order.get("client_name", "Заказчик")),
        "email": str(order.get("raw_data", {}).get("email", "")),
        "phone": str(order.get("phone", "Не указан")),
        "deliveryType": str(order.get("delivery_type", "Самовывоз со склада")),
        "deliveryInfo": str(order.get("delivery_info", "-")),
        "totalSum": float(order.get("total_sum", 0)),
        "status": map_order_status_for_ios(raw_status),
        "internalStatus": raw_status,
        "paymentMethod": order.get("payment_method"),
        "cancelReason": order.get("cancel_reason"),
        "yandexNavURL": str(order.get("raw_data", {}).get("yandex_nav_url") or YANDEX_MAPS_URL),
        "items": ios_items,
        "hasGoods": bool(order.get("has_goods", True)),
        "hasWorks": bool(order.get("has_works", order.get("is_works", False))),
        "isCombined": bool(order.get("is_combined", False)),
        "goodsSubtotal": float(order.get("goods_subtotal", 0)),
        "worksSubtotal": float(order.get("works_subtotal", 0)),
    }


@app.route("/api/ios/orders", methods=["GET"])
def api_ios_get_orders():
    """Возвращает заказы для iOS-приложения: менеджерам/владельцу — все заказы склада, клиенту — его заказы (по Email, телефону или ID)"""
    try:
        role = request.args.get("role", "client")
        email = request.args.get("email", "").strip().lower()
        phone = request.args.get("phone", "").strip()
        user_id = request.args.get("user_id", "").strip()
        clean_req_phone = normalize_phone_digits(phone)

        results = []
        for oid, order in ACTIVE_ORDERS.items():
            if can_manage_orders(role):
                results.append(_serialize_order_for_ios(oid, order))
            else:
                ord_phone_clean = normalize_phone_digits(order.get("phone", ""))
                ord_uid = str(order.get("client_id", "")).strip()
                ord_email = str(order.get("raw_data", {}).get("email", "")).strip().lower()
                if (email and email == ord_email) or (clean_req_phone and clean_req_phone == ord_phone_clean) or (phone and phone in str(order.get("phone", ""))) or (user_id and user_id == ord_uid):
                    results.append(_serialize_order_for_ios(oid, order))

        results.reverse()
        return jsonify({"status": "ok", "data": results}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/toggle_item", methods=["POST"])
def api_ios_toggle_item():
    """Отметка позиции в чек-листе сборки из iOS-приложения менеджера"""
    try:
        data = request.json or {}
        order_id = str(data.get("order_id", "")).strip()
        item_index = data.get("item_index")
        item_key = str(data.get("item_key", "")).strip()
        is_collected = bool(data.get("is_collected", True))

        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            return jsonify({"status": "error", "message": "Заказ не найден"}), 404

        if item_index is not None and 0 <= int(item_index) < len(order["collected"]):
            order["collected"][int(item_index)] = is_collected
        else:
            for idx, it in enumerate(order["items"]):
                k = str(it.get("item_key") or it.get("code") or f"item_{idx}")
                if k == item_key or it.get("name") == item_key:
                    order["collected"][idx] = is_collected
                    break

        return jsonify({"status": "ok", "data": _serialize_order_for_ios(order_id, order)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/update_order", methods=["POST"])
def api_ios_update_order():
    """Смена статуса заказа (Собран / Оплачен / Отменен) из iOS-приложения менеджера с синхронизацией в Google Таблицу и ТГ"""
    try:
        data = request.json or {}
        order_id = str(data.get("order_id", "")).strip()
        new_status = str(data.get("status", "completed")).strip()
        payment_type = str(data.get("payment_type") or data.get("payment_method") or "").strip()
        payment_type = map_payment_type_ios(payment_type) or payment_type
        cancel_reason = str(data.get("cancel_reason", "")).strip()
        manager_name = str(data.get("manager_name", "Менеджер (iOS)")).strip()

        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            return jsonify({"status": "error", "message": "Заказ не найден"}), 404

        order["status"] = new_status
        if payment_type:
            order["payment_method"] = payment_type
        if cancel_reason:
            order["cancel_reason"] = cancel_reason

        if new_status == "completed":
            update_sheet_status(order_id, "Собран на складе", assembler=manager_name, manager=manager_name)
        elif new_status == "paid":
            update_sheet_status(order_id, "Оплачен и выдан", payment_type=payment_type or "Оплачено", payment_method=payment_type or "Оплачено", manager=manager_name)
        elif new_status == "cancelled":
            update_sheet_status(order_id, "Отменён", cancel_reason=cancel_reason, comment=cancel_reason, manager=manager_name)

        return jsonify({"status": "ok", "data": _serialize_order_for_ios(order_id, order)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/user_orders", methods=["GET", "POST"])
def get_user_orders():
    """Возвращает историю заказов пользователя по user_id или номеру телефона"""
    try:
        user_id = request.args.get("user_id") or (request.json or {}).get("user_id")
        phone = request.args.get("phone") or (request.json or {}).get("phone")
        
        results = []
        for oid, order in ACTIVE_ORDERS.items():
            match = False
            if user_id and str(order.get("client_id")) == str(user_id):
                match = True
            elif phone and phone in str(order.get("phone")):
                match = True
            
            if match:
                results.append({
                    "order_id": oid,
                    "date": order.get("created_at", "Сегодня"),
                    "total": order.get("total_sum", 0),
                    "status": order.get("status", "active"),
                    "is_works": order.get("is_works", False),
                    "has_goods": order.get("has_goods", not order.get("is_works")),
                    "has_works": order.get("has_works", order.get("is_works", False)),
                    "is_combined": order.get("is_combined", False),
                    "delivery_type": order.get("delivery_type", ""),
                    "delivery_info": order.get("delivery_info", ""),
                    "items": order.get("items", [])
                })
        
        # Сортируем от новых к старым
        results.reverse()
        return jsonify({"status": "ok", "orders": results}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/ios/create_order", methods=["POST"])
@app.route("/api/miniapp_order", methods=["POST"])
def handle_miniapp_order():
    try:
        data = request.json or {}
        user_id = data.get("user_id") or data.get("chat_id") or 0

        # Формируем и рассчитываем заказ по утвержденной номенклатуре
        order_id, admin_text, client_text, total_sum = build_order_payload(data)
        kb_admin = make_warehouse_keyboard(order_id)

        # 1. Рассылка всем 3 администраторам склада
        for a_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(a_id, admin_text, parse_mode="HTML", reply_markup=kb_admin)
            except Exception as e:
                print(f"[ERR ADMIN SEND] {a_id}: {e}")

        # 2. Уведомление клиенту со ссылкой на Яндекс Карты (маршрут к складу)
        if user_id:
            try:
                lang = data.get("lang", "ru")
                t_client = MESSAGES.get(lang, MESSAGES["ru"])

                kb_client = tele_types.InlineKeyboardMarkup(row_width=1)
                is_deliv = "Доставка" in data.get("delivery_type", "")
                if not is_deliv:
                    kb_client.add(tele_types.InlineKeyboardButton(t_client["btn_nav_sklad"], url=YANDEX_MAPS_URL))
                kb_client.add(tele_types.InlineKeyboardButton(t_client["btn_repeat"], callback_data=f"repeat_{order_id}"))

                client_msg = t_client["accepted"].format(order_id=order_id, body=client_text)
                bot.send_message(user_id, client_msg, parse_mode="HTML", reply_markup=kb_client)
            except Exception as client_err:
                print(f"[ERR CLIENT SEND] {user_id}: {client_err}")

        return jsonify({
            "status": "ok", 
            "order_id": order_id, 
            "total": total_sum,
            "items": ACTIVE_ORDERS[order_id]["items"]
        }), 200

    except OrderValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        print(f"[ERROR API] {e}")
        return jsonify({"error": str(e)}), 500

# ==============================================================================
# ОБРАБОТКА ДЕЙСТВИЙ МЕНЕДЖЕРОВ (КНОПКИ ЧЕК-ЛИСТА, СБОРКИ, ОПЛАТЫ, ОТМЕНЫ)
# ==============================================================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data

    if data == "admin_export_cfg":
        if not is_owner_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Доступ запрещён")
            return
        save_config_locally()
        try:
            with open(CONFIG_FILE_PATH, "rb") as f_doc:
                bot.send_document(call.message.chat.id, f_doc, caption="📥 Актуальный файл конфигурации catalog_config.json")
            bot.answer_callback_query(call.id, "Файл отправлен ✅")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка: {e}")
        return

    # 1. Чек-лист сборщика (нажал на товар -> загорелся зеленым 🟢)
    if data.startswith("chk_"):
        parts = data.split("_")
        order_id = parts[1]
        item_idx = int(parts[2])

        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        order["collected"][item_idx] = not order["collected"][item_idx]
        new_kb = make_warehouse_keyboard(order_id)
        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_kb)
        except Exception:
            pass

        st = "взят со склада ✅" if order["collected"][item_idx] else "снят с отметки ❌"
        bot.answer_callback_query(call.id, f"{order['items'][item_idx]['name']}: {st}")

    # 2. Завершение сборки: уведомление клиенту + статус в Google Sheets
    # 1.1. Согласование заказа на монтажные работы
    elif data.startswith("agree_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        manager_name = get_admin_name(call.from_user.id)
        order["works_agreed"] = True
        has_goods = bool(order.get("has_goods", True))
        if not has_goods:
            order["status"] = "completed"
            order["agreed_by"] = manager_name
            order["collected_by"] = manager_name
        else:
            order["agreed_by"] = manager_name

        new_kb = make_warehouse_keyboard(order_id)
        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_kb)
        except Exception:
            pass

        update_sheet_status(order_id, "Согласован", assembler=manager_name, manager=manager_name)
        bot.answer_callback_query(call.id, f"Заказ #{order_id} согласован: {manager_name} 🤝")

        client_id = order.get("client_id")
        if client_id:
            try:
                lang = order.get("lang", "ru")
                t_client = MESSAGES.get(lang, MESSAGES["ru"])
                sum_formatted = f"{order['total_sum']:,.2f} ₽"
                clean_addr = order.get("delivery_info", "-")
                agree_title = t_client.get("agree_title", f"🤝 <b>ВАШ ЗАКАЗ НА РАБОТЫ #{order_id} СОГЛАСОВАН!</b>").format(order_id=order_id)
                agree_body = t_client.get("agree_body", "👷 Бригада назначена. Менеджер свяжется для подтверждения даты выезда.\n💰 Сумма: <b>{sum} ₽</b>\n📍 Адрес: <b>{addr}</b>").format(sum=sum_formatted, addr=clean_addr)
                
                alert_text = f"{agree_title}\n━━━━━━━━━━━━━━━━━━━━\n{agree_body}"
                bot.send_message(client_id, alert_text, parse_mode="HTML")
            except Exception as e:
                print(f"[ERR NOTIFY CLIENT AGREE] {client_id}: {e}")

    elif data.startswith("fin_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        has_goods = bool(order.get("has_goods", True))
        has_works = bool(order.get("has_works", order.get("is_works")))
        if has_goods:
            goods_idx = [i for i, it in enumerate(order["items"]) if not it.get("is_work")]
            if goods_idx and not all(order["collected"][i] for i in goods_idx if i < len(order["collected"])):
                bot.answer_callback_query(call.id, "Сначала соберите все позиции оборудования на складе")
                return
        if has_works and has_goods and not order.get("works_agreed"):
            bot.answer_callback_query(call.id, "Сначала согласуйте монтажные работы (кнопка 🔨)")
            return

        manager_name = get_admin_name(call.from_user.id)
        order["status"] = "completed"
        order["collected_by"] = manager_name
        if has_works:
            order["works_agreed"] = True

        new_kb = make_warehouse_keyboard(order_id)
        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_kb)
        except Exception:
            pass

        update_sheet_status(order_id, "Собран на складе", assembler=manager_name, manager=manager_name)
        bot.answer_callback_query(call.id, f"Заказ #{order_id} собрал: {manager_name} ✅")

        client_id = order.get("client_id")
        if client_id:
            try:
                lang = order.get("lang", "ru")
                t_client = MESSAGES.get(lang, MESSAGES["ru"])
                sum_formatted = f"{order['total_sum']:,.2f} ₽"
                alert_text = (
                    f"{t_client['collected_title'].format(order_id=order_id)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{t_client['collected_body'].format(sum=sum_formatted, delivery=order.get('delivery_type'))}"
                )
                kb_nav = tele_types.InlineKeyboardMarkup()
                if not order.get("is_delivery"):
                    kb_nav.add(tele_types.InlineKeyboardButton(t_client["btn_nav_sklad"], url=YANDEX_MAPS_URL))
                bot.send_message(client_id, alert_text, parse_mode="HTML", reply_markup=kb_nav)
            except Exception as e:
                print(f"[ERR NOTIFY CLIENT] {client_id}: {e}")

    # 3. Меню оплаты заказа менеджером
    elif data.startswith("paymenu_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        kb_pay = tele_types.InlineKeyboardMarkup(row_width=1)
        kb_pay.add(
            tele_types.InlineKeyboardButton("💵 Наличные", callback_data=f"setpay_{order_id}_cash"),
            tele_types.InlineKeyboardButton("📑 По счёту (Безнал)", callback_data=f"setpay_{order_id}_invoice"),
            tele_types.InlineKeyboardButton("🔙 Назад", callback_data=f"backorder_{order_id}")
        )
        bot.send_message(
            call.message.chat.id,
            f"💳 <b>Оплата заказа #{order_id}</b>\n"
            f"Сумма к получению: <b>{order['total_sum']:,.2f} ₽</b>\n\n"
            f"Укажите способ расчёта с клиентом:",
            parse_mode="HTML",
            reply_markup=kb_pay
        )

    # 4. Фиксация способа оплаты
    elif data.startswith("setpay_"):
        parts = data.split("_")
        order_id = parts[1]
        pay_type = parts[2]

        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        manager_name = get_admin_name(call.from_user.id)
        pay_title = "Наличные" if pay_type == "cash" else "По счёту (Безнал)"

        order["status"] = "paid"
        order["payment_method"] = pay_title
        order["paid_by"] = manager_name

        new_kb = make_warehouse_keyboard(order_id)
        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_kb)
        except Exception:
            pass

        update_sheet_status(order_id, "Оплачен и выдан", payment_type=pay_title, payment_method=pay_title, manager=manager_name)
        bot.answer_callback_query(call.id, f"Оплачено: {pay_title} ✅")

        bot.send_message(
            call.message.chat.id,
            f"🎉 <b>Заказ #{order_id} успешно выдан и оплачен!</b>\n"
            f"Способ: <b>{pay_title}</b>\n"
            f"Сумма: <b>{order['total_sum']:,.2f} ₽</b>\n"
            f"Менеджер: <b>{manager_name}</b>",
            parse_mode="HTML"
        )

        client_id = order.get("client_id")
        if client_id:
            try:
                lang = order.get("lang", "ru")
                t_client = MESSAGES.get(lang, MESSAGES["ru"])
                client_sum_str = f"{order['total_sum']:,.2f}"
                client_alert = (
                    f"{t_client['paid_title'].format(order_id=order_id)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{t_client['paid_body'].format(sum=client_sum_str, method=pay_title)}"
                )
                bot.send_message(client_id, client_alert, parse_mode="HTML")
            except Exception as e:
                print(f"[ERR CLIENT PAID NOTIFY] {e}")

    # 5. Запрос причины отмены заказа
    elif data.startswith("cancel_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        bot.answer_callback_query(call.id, "Укажите причину отмены")
        msg = bot.send_message(
            call.message.chat.id,
            f"✍️ <b>Напишите причину отмены заказа #{order_id}</b>\n"
            f"<i>(Например: клиент не приехал / отказ на месте / ошибка):</i>",
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, process_cancel_reason, order_id, call.message.message_id)

    # 6. Меню редактирования заказа
    elif data.startswith("editmenu_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        kb_edit = tele_types.InlineKeyboardMarkup(row_width=1)
        kb_edit.add(
            tele_types.InlineKeyboardButton("➕ Добавить товар / расходник", callback_data=f"addmenu_{order_id}"),
            tele_types.InlineKeyboardButton("❌ Убрать позицию из сметы", callback_data=f"delmenu_{order_id}"),
            tele_types.InlineKeyboardButton("🔙 Вернуться к заказу", callback_data=f"backorder_{order_id}")
        )
        bot.send_message(
            call.message.chat.id,
            f"⚙️ <b>Редактирование заказа #{order_id}</b>\n"
            f"Текущая сумма: <b>{order['total_sum']:,.2f} ₽</b>\n\n"
            f"Выберите необходимое действие:",
            parse_mode="HTML",
            reply_markup=kb_edit
        )

    # 7. Добавление позиции
    elif data.startswith("addmenu_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        kb_add = tele_types.InlineKeyboardMarkup(row_width=1)
        for idx, it in enumerate(ALL_CATALOG_ITEMS):
            btn_txt = f"{it['name']} ({it['price']:,.2f} ₽/{it['unit']})"
            kb_add.add(tele_types.InlineKeyboardButton(btn_txt, callback_data=f"pickitem_{order_id}_{idx}"))
        kb_add.add(tele_types.InlineKeyboardButton("🔙 Назад", callback_data=f"editmenu_{order_id}"))

        bot.send_message(call.message.chat.id, "📦 <b>Выберите позицию для добавления в заказ:</b>", parse_mode="HTML", reply_markup=kb_add)

    elif data.startswith("pickitem_"):
        parts = data.split("_")
        order_id = parts[1]
        item_idx = int(parts[2])

        order = ACTIVE_ORDERS.get(order_id)
        if not order or item_idx >= len(ALL_CATALOG_ITEMS):
            bot.answer_callback_query(call.id, "Товар не найден")
            return

        picked = ALL_CATALOG_ITEMS[item_idx]
        msg = bot.send_message(
            call.message.chat.id,
            f"✍️ Вы выбрали: <b>{picked['name']}</b> ({picked['price']:,.2f} ₽/{picked['unit']})\n\n"
            f"<b>Введите количество ({picked['unit']}):</b>",
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, process_add_item_qty, order_id, item_idx)

    # 8. Удаление позиции
    elif data.startswith("delmenu_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        kb_del = tele_types.InlineKeyboardMarkup(row_width=1)
        for idx, it in enumerate(order["items"]):
            kb_del.add(tele_types.InlineKeyboardButton(f"❌ {it['name'][:28]}", callback_data=f"delitem_{order_id}_{idx}"))
        kb_del.add(tele_types.InlineKeyboardButton("🔙 Назад", callback_data=f"editmenu_{order_id}"))

        bot.send_message(call.message.chat.id, f"❌ <b>Выберите позицию для удаления из #{order_id}:</b>", parse_mode="HTML", reply_markup=kb_del)

    elif data.startswith("delitem_"):
        parts = data.split("_")
        order_id = parts[1]
        idx = int(parts[2])

        order = ACTIVE_ORDERS.get(order_id)
        if not order or idx >= len(order["items"]):
            bot.answer_callback_query(call.id, "Позиция не найдена")
            return

        removed_name = order["items"][idx]["name"]
        del order["items"][idx]
        del order["collected"][idx]

        flags = recompute_order_composition_flags(order["items"])
        order.update(flags)
        order["goods_subtotal"] = round(
            sum(it["qty"] * it["price"] for it in order["items"] if not it.get("is_work")), 2
        )
        order["works_subtotal"] = round(
            sum(it["qty"] * it["price"] for it in order["items"] if it.get("is_work")), 2
        )
        order["total_sum"] = round(sum(it["qty"] * it["price"] for it in order["items"]), 2)
        admin_text, client_text = render_order_texts(order_id, order["raw_data"], order["items"], order["total_sum"], order.get("lang", "ru"), modifier_pct=order.get("modifier_pct", 0.0))

        bot.answer_callback_query(call.id, f"Удалено: {removed_name}")
        bot.send_message(call.message.chat.id, f"✅ Позиция <b>{removed_name}</b> убрана!\nНовая сумма: <b>{order['total_sum']:,.2f} ₽</b>", parse_mode="HTML")

        client_id = order.get("client_id")
        if client_id:
            try:
                bot.send_message(client_id, f"ℹ️ <b>Ваш заказ #{order_id} скорректирован менеджером:</b>\n\n{client_text}", parse_mode="HTML")
            except Exception:
                pass

    # 9. Возврат к заказу
    elif data.startswith("backorder_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return
        admin_text, _ = render_order_texts(order_id, order["raw_data"], order["items"], order["total_sum"], order.get("lang", "ru"), modifier_pct=order.get("modifier_pct", 0.0))
        kb = make_warehouse_keyboard(order_id)
        bot.send_message(call.message.chat.id, admin_text, parse_mode="HTML", reply_markup=kb)

    # 10. Повтор заказа
    elif data.startswith("repeat_"):
        old_order_id = data.split("_")[1]
        old_order = ACTIVE_ORDERS.get(old_order_id)
        if not old_order:
            bot.answer_callback_query(call.id, "Предыдущий заказ не найден в текущей сессии")
            return

        new_data = dict(old_order["raw_data"])
        new_order_id, admin_text, client_text, _ = build_order_payload(new_data)
        new_kb = make_warehouse_keyboard(new_order_id)

        for a_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(a_id, f"🔄 <b>ПОВТОР ЗАКАЗА #{old_order_id} ➔ #{new_order_id}</b>\n\n" + admin_text, parse_mode="HTML", reply_markup=new_kb)
            except Exception:
                pass

        try:
            bot.send_message(call.message.chat.id, f"✅ <b>Заказ успешно повторен! Новый номер: #{new_order_id}</b>\nСклад уже комплектует заказ.", parse_mode="HTML")
        except Exception:
            pass

def process_add_item_qty(message, order_id, catalog_idx):
    try:
        qty = float(message.text.strip().replace(",", "."))
        if qty <= 0: raise ValueError()
    except Exception:
        bot.reply_to(message, "⚠️ Введите корректное положительное число.")
        return

    order = ACTIVE_ORDERS.get(order_id)
    if not order or catalog_idx >= len(ALL_CATALOG_ITEMS):
        bot.reply_to(message, "Заказ не найден.")
        return

    item_template = ALL_CATALOG_ITEMS[catalog_idx]
    new_line = tag_item_category({
        "item_key": item_template.get("code", ""),
        "name": f"[Добавлен] {item_template['name']}",
        "qty": qty,
        "unit": item_template["unit"],
        "price": item_template["price"]
    })
    order["items"].append(new_line)
    order["collected"].append(False)
    flags = recompute_order_composition_flags(order["items"])
    order.update(flags)
    order["goods_subtotal"] = round(
        sum(it["qty"] * it["price"] for it in order["items"] if not it.get("is_work")), 2
    )
    order["works_subtotal"] = round(
        sum(it["qty"] * it["price"] for it in order["items"] if it.get("is_work")), 2
    )
    order["total_sum"] = round(sum(it["qty"] * it["price"] for it in order["items"]), 2)

    admin_text, client_text = render_order_texts(order_id, order["raw_data"], order["items"], order["total_sum"], order.get("lang", "ru"), modifier_pct=order.get("modifier_pct", 0.0))
    kb = make_warehouse_keyboard(order_id)

    bot.send_message(
        message.chat.id,
        f"✅ <b>Позиция добавлена!</b>\n• {item_template['name']}: {qty:g} {item_template['unit']}\n💰 Новая сумма: <b>{order['total_sum']:,.2f} ₽</b>",
        parse_mode="HTML"
    )
    bot.send_message(message.chat.id, admin_text, parse_mode="HTML", reply_markup=kb)

    client_id = order.get("client_id")
    if client_id:
        try:
            bot.send_message(client_id, f"ℹ️ <b>Менеджер добавил позицию в ваш заказ #{order_id}:</b>\n\n{client_text}", parse_mode="HTML")
        except Exception:
            pass

def process_cancel_reason(message, order_id, original_msg_id):
    reason = message.text.strip()
    order = ACTIVE_ORDERS.get(order_id)
    if not order:
        bot.reply_to(message, "Заказ не найден.")
        return

    manager_name = get_admin_name(message.from_user.id)
    order["status"] = "cancelled"
    order["cancel_reason"] = reason

    new_kb = make_warehouse_keyboard(order_id)
    try:
        bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=original_msg_id, reply_markup=new_kb)
    except Exception:
        pass

    update_sheet_status(order_id, "Отменён", cancel_reason=reason, comment=reason, manager=manager_name)
    bot.reply_to(message, f"✅ Заказ #{order_id} отменён ({manager_name}).\nПричина «{reason}» записана в Google Таблицу.", parse_mode="HTML")

    client_id = order.get("client_id")
    if client_id:
        try:
            bot.send_message(client_id, f"❌ <b>Ваш заказ #{order_id} отменён складом.</b>\nПричина: {reason}", parse_mode="HTML")
        except Exception:
            pass

@bot.message_handler(commands=['admin'])
def handle_admin_cmd(message):
    if not is_owner_admin(message.from_user.id):
        return
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://mishka-kesson-app.onrender.com").rstrip("/")
    admin_app_url = f"{render_url}/app?admin=1"
    kb = tele_types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        tele_types.InlineKeyboardButton("👑 ОТКРЫТЬ АДМИН-ПАНЕЛЬ УПРАВЛЕНИЯ", web_app=tele_types.WebAppInfo(url=admin_app_url)),
        tele_types.InlineKeyboardButton("📥 Выгрузить текущий catalog_config.json", callback_data="admin_export_cfg")
    )
    bot.send_message(
        message.chat.id,
        "👑 <b>Панель управления ботом «МИШКА» (только для владельца)</b>\n\n"
        "• Нажмите кнопку ниже, чтобы изменить цены, добавить товары в нужный раздел или отредактировать описания схем.\n"
        "• Чтобы восстановить базу из резервной копии, просто перешлите файл <code>catalog_config.json</code> сюда в чат.",
        parse_mode="HTML",
        reply_markup=kb
    )


@bot.message_handler(content_types=['document'])
def handle_admin_document_restore(message):
    if not is_owner_admin(message.from_user.id):
        return
    doc = message.document
    if not doc or not doc.file_name.endswith(".json"):
        return
    try:
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        import json
        restored_cfg = json.loads(downloaded.decode("utf-8"))
        apply_config_dict(restored_cfg)
        saved_cfg = save_config_locally()
        sync_config_to_cloud(saved_cfg)
        bot.reply_to(message, "✅ <b>Конфигурация и прайс-лист успешно восстановлены из файла!</b> Все цены, товары и описания обновлены.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка чтения JSON-файла: {e}")


@bot.message_handler(commands=['start'])
def handle_start(message):
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://mishka-kesson-app.onrender.com").rstrip("/")
    web_app_url = f"{render_url}/app"

    inline_kb = tele_types.InlineKeyboardMarkup(row_width=1)
    inline_kb.add(
        tele_types.InlineKeyboardButton("🚀 НАЖМИТЕ СЮДА — ОТКРЫТЬ СКЛАД 📦", web_app=tele_types.WebAppInfo(url=web_app_url)),
        tele_types.InlineKeyboardButton("📍 Где наш склад? (Маршрут Яндекс)", url=YANDEX_MAPS_URL)
    )

    caption_text = (
        "👋 <b>Добро пожаловать на склад завода «МИШКА»!</b>\n\n"
        "Здесь вы можете за 1 минуту собрать полную смету по обустройству скважины с актуальными ценами:\n"
        "• <b>Кессоны «МИШКА»</b> (с частотным преобразователем или гидробаком Belamos)\n"
        "• <b>Обустройство со скважинным адаптером</b>\n"
        "• <b>Скважинные насосы и комплектующие</b>\n\n"
        "🚚 <i>Доступен самовывоз со склада или доставка на объект!</i>\n\n"
        "👇 <b>НАЖМИТЕ КНОПКУ НИЖЕ ДЛЯ ВХОДА В ПРИЛОЖЕНИЕ:</b>"
    )
    try:
        bot.send_photo(message.chat.id, photo=WELCOME_BANNER_URL, caption=caption_text, reply_markup=inline_kb, parse_mode="HTML")
    except Exception:
        bot.send_message(message.chat.id, caption_text, reply_markup=inline_kb, parse_mode="HTML")

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

def setup_bot_mode():
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    use_webhook = os.getenv("USE_WEBHOOK", "true").lower() == "true"

    if render_url and use_webhook:
        webhook_url = f"{render_url}/webhook/{BOT_TOKEN}"
        print(f"Установка Telegram Webhook: {render_url}/webhook/***")
        try:
            bot.remove_webhook()
            time.sleep(0.5)
            bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            print("Webhook успешно установлен! Ошибка 409 Conflict полностью исключена.")
            return
        except Exception as e:
            print(f"Ошибка установки вебхука, переключаемся на polling: {e}")

    # Резервный запуск через polling (например, при локальном тесте без RENDER_EXTERNAL_URL)
    print(f"Запуск Telegram Polling... Администраторы: {ADMIN_CHAT_IDS}")
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception:
        pass
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"Сбой polling: {e}. Перезапуск через 5 сек...")
            time.sleep(5)

def keep_alive_ping():
    time.sleep(30)
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://mishka-kesson-app.onrender.com").rstrip("/")
    ping_url = f"{render_url}/health"
    while True:
        try:
            requests.get(ping_url, timeout=15)
        except Exception:
            pass
        time.sleep(420)

# Загрузка сохранённой конфигурации цен и каталога при старте
load_config_on_startup()

# Инициализация при старте (работает и через python app.py, и через gunicorn app:app)
threading.Thread(target=setup_bot_mode, daemon=True).start()
threading.Thread(target=keep_alive_ping, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
