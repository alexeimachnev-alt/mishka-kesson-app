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
    return jsonify({"status": "ok", "service": "Mishka Warehouse", "admins": ADMIN_CHAT_IDS}), 200

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
        if not is_owner_admin(admin_id, init_data):
            return jsonify({"status": "error", "message": "Доступ запрещён! Только для владельца бота."}), 403

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
        if not is_owner_admin(user_id, init_data):
            return jsonify({"status": "error", "message": "Доступ запрещён! Только для владельца бота."}), 403

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
import smtplib
from email.mime.text import MIMEText

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
        "name": "Менеджер склада",
        "company": "Склад ПК МИШКА",
        "role": "manager",
        "password": os.getenv("SKLAD_PASSWORD", "840231")
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

EMAIL_OTP_CODES = {}

def send_verification_email_smtp(target_email: str, code: str) -> bool:
    """Отправляет 4-значный код подтверждения на Email клиента через SMTP (Яндекс / Mail.ru / Gmail)"""
    smtp_user = os.getenv("SMTP_EMAIL", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.yandex.ru").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not smtp_user or not smtp_pass:
        return False

    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = target_email
        msg["Subject"] = f"Код подтверждения ПК «МИШКА»: {code}"

        html_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background: #17212b; color: #ffffff; border-radius: 12px;">
            <h2 style="color: #2ea6ff; margin-top: 0;">📦 ПК «МИШКА»</h2>
            <p>Здравствуйте! Ваш код для входа и подтверждения регистрации в мобильном приложении:</p>
            <div style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #4ade80; padding: 12px 20px; background: #232e3c; display: inline-block; border-radius: 8px;">
                {code}
            </div>
            <p style="color: #94a3b8; font-size: 12px; margin-top: 16px;">Если вы не запрашивали код, просто проигнорируйте это письмо.</p>
        </div>
        """
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, target_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[SMTP SEND ERR] {e}")
        return False


@app.route("/api/auth/send_email_code", methods=["POST"])
def api_send_email_code():
    """Генерирует и отправляет 4-значный код на почту клиента (если настроен SMTP_EMAIL/SMTP_PASSWORD)"""
    try:
        import random
        data = request.json or {}
        email = str(data.get("email", "")).strip().lower()
        if not email or "@" not in email:
            return jsonify({"status": "error", "message": "Укажите корректный Email"}), 400

        code = str(random.randint(1000, 9999))
        EMAIL_OTP_CODES[email] = code
        sent = send_verification_email_smtp(email, code)

        return jsonify({
            "status": "ok",
            "smtp_active": sent,
            "message": "Код отправлен на вашу почту!" if sent else "Регистрация по паролю (без кода из письма)"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/auth/login", methods=["POST"])
@app.route("/api/auth/email", methods=["POST"])
def api_ios_auth_login():
    """Регистрация и вход по Email + Пароль для клиентов и менеджеров склада (без платных СМС)"""
    try:
        load_ios_users()
        data = request.json or {}
        mode = str(data.get("mode", "login")).strip().lower()  # 'login' или 'register'
        email = str(data.get("email") or data.get("login") or "").strip().lower()
        password = str(data.get("password") or data.get("code") or "").strip()
        raw_phone = str(data.get("phone", "")).strip()
        name = str(data.get("name", "")).strip()
        company = str(data.get("company", "")).strip()

        clean_digits = normalize_phone_digits(raw_phone)

        # 1. Быстрый вход для руководителей/менеджеров по Email, телефону или ID
        if email in BUILTIN_STAFF_ACCOUNTS or raw_phone in ["551209811", "447208738", "840231919"] or clean_digits == "79060400043":
            staff = BUILTIN_STAFF_ACCOUNTS.get(email)
            if not staff:
                if raw_phone == "447208738":
                    staff = BUILTIN_STAFF_ACCOUNTS["artur@mishka.ru"]
                elif raw_phone == "840231919":
                    staff = BUILTIN_STAFF_ACCOUNTS["sklad@mishka.ru"]
                else:
                    staff = BUILTIN_STAFF_ACCOUNTS["alexeimachnev@icloud.com"]

            # Проверяем пароль (принимаем штатный пароль или резервный пин 7777 / 1234 для первого входа)
            if password and password not in [staff["password"], "7777", "1234", "551209811", "447208738"]:
                return jsonify({"status": "error", "message": "Неверный пароль сотрудника склада"}), 401

            uid = staff["id"]
            discount_pct = get_user_modifier(uid)
            user_payload = {
                "id": uid,
                "email": staff["email"],
                "phone": raw_phone or staff["phone"],
                "name": name or staff["name"],
                "company": company or staff["company"],
                "role": staff["role"],
                "token": f"mishka_ios_{uid}",
                "personalDiscount": discount_pct
            }
            return jsonify({"status": "ok", "data": user_payload}), 200

        if not email or "@" not in email:
            return jsonify({"status": "error", "message": "Пожалуйста, укажите корректный Email (например: client@mail.ru)"}), 400
        if not password or len(password) < 4:
            return jsonify({"status": "error", "message": "Пароль должен содержать минимум 4 символа"}), 400

        existing = IOS_USERS_DB.get(email)

        if mode == "register":
            if existing and existing.get("password") and existing.get("password") != password:
                return jsonify({"status": "error", "message": "Этот Email уже зарегистрирован. Переключитесь на вкладку «Вход» или введите верный пароль."}), 400
            if not raw_phone:
                return jsonify({"status": "error", "message": "Укажите контактный телефон для связи со складом"}), 400

            uid = clean_digits or email
            new_user = {
                "id": uid,
                "email": email,
                "phone": raw_phone,
                "name": name or "Заказчик",
                "company": company,
                "role": "client",
                "password": password
            }
            IOS_USERS_DB[email] = new_user
            save_ios_users()
            discount_pct = get_user_modifier(uid)
            return jsonify({
                "status": "ok",
                "data": {
                    "id": uid,
                    "email": email,
                    "phone": raw_phone,
                    "name": new_user["name"],
                    "company": company,
                    "role": "client",
                    "token": f"mishka_ios_{uid}",
                    "personalDiscount": discount_pct
                }
            }), 200
        else:
            # Режим входа ('login')
            if existing:
                if existing.get("password") != password:
                    return jsonify({"status": "error", "message": "Неверный пароль для этого Email"}), 401
                uid = existing.get("id") or clean_digits or email
                discount_pct = get_user_modifier(uid)
                return jsonify({
                    "status": "ok",
                    "data": {
                        "id": uid,
                        "email": email,
                        "phone": existing.get("phone") or raw_phone,
                        "name": existing.get("name") or name or "Заказчик",
                        "company": existing.get("company") or company,
                        "role": existing.get("role", "client"),
                        "token": f"mishka_ios_{uid}",
                        "personalDiscount": discount_pct
                    }
                }), 200
            else:
                # Если аккаунт еще не создан — автоматически регистрируем при первом входе
                uid = clean_digits or email
                auto_user = {
                    "id": uid,
                    "email": email,
                    "phone": raw_phone or "Не указан",
                    "name": name or email.split("@")[0],
                    "company": company,
                    "role": "client",
                    "password": password
                }
                IOS_USERS_DB[email] = auto_user
                save_ios_users()
                discount_pct = get_user_modifier(uid)
                return jsonify({
                    "status": "ok",
                    "data": {
                        "id": uid,
                        "email": email,
                        "phone": auto_user["phone"],
                        "name": auto_user["name"],
                        "company": company,
                        "role": "client",
                        "token": f"mishka_ios_{uid}",
                        "personalDiscount": discount_pct
                    }
                }), 200
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
            "isCollected": bool(is_col)
        })
    return {
        "id": str(oid),
        "clientName": str(order.get("client_name", "Заказчик")),
        "email": str(order.get("raw_data", {}).get("email", "")),
        "phone": str(order.get("phone", "Не указан")),
        "deliveryType": str(order.get("delivery_type", "Самовывоз со склада")),
        "deliveryInfo": str(order.get("delivery_info", "-")),
        "totalSum": float(order.get("total_sum", 0)),
        "status": str(order.get("status", "active")),
        "paymentMethod": order.get("payment_method"),
        "cancelReason": order.get("cancel_reason"),
        "items": ios_items
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
            if role in ["manager", "owner"]:
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
        payment_type = str(data.get("payment_type", "")).strip()
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
                    "delivery_type": order.get("delivery_type", ""),
                    "delivery_info": order.get("delivery_info", ""),
                    "items": order.get("items", [])
                })
        
        # Сортируем от новых к старым
        results.reverse()
        return jsonify({"status": "ok", "orders": results}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
        order["status"] = "completed"
        order["agreed_by"] = manager_name
        order["collected_by"] = manager_name

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

        manager_name = get_admin_name(call.from_user.id)
        order["status"] = "completed"
        order["collected_by"] = manager_name

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
    order["items"].append({
        "name": f"[Добавлен] {item_template['name']}",
        "qty": qty,
        "unit": item_template["unit"],
        "price": item_template["price"]
    })
    order["collected"].append(False)
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
        time.sleep(540)

# Загрузка сохранённой конфигурации цен и каталога при старте
load_config_on_startup()

# Инициализация при старте (работает и через python app.py, и через gunicorn app:app)
threading.Thread(target=setup_bot_mode, daemon=True).start()
threading.Thread(target=keep_alive_ping, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
