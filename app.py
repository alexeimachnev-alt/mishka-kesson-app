# -*- coding: utf-8 -*-
"""
Основной сервер Flask и Telegram-бот склада «МИШКА»
Поддержка Mini App, маршрутов заказов (/api/miniapp_order),
расчетов и уведомлений для 3 администраторов.
"""

import os
import json
import threading
from datetime import datetime
from flask import Flask, render_template, render_template_string, request, jsonify
import telebot
from telebot import types

from calc_well import get_well_items
from constants import PRICES

# 1. Flask Web App
app = Flask(__name__, template_folder="templates", static_folder=".")

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

# Список администраторов
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
SECOND_ADMIN_CHAT_ID = os.getenv("SECOND_ADMIN_CHAT_ID")
THIRD_ADMIN_CHAT_ID = os.getenv("THIRD_ADMIN_CHAT_ID", "840231919")

ADMIN_IDS = [
    int(x) for x in [ADMIN_CHAT_ID, SECOND_ADMIN_CHAT_ID, THIRD_ADMIN_CHAT_ID]
    if x and str(x).strip().isdigit()
]

ADMIN_NAMES = {
    int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID and ADMIN_CHAT_ID.isdigit() else 0: "Алексей",
    int(SECOND_ADMIN_CHAT_ID) if SECOND_ADMIN_CHAT_ID and SECOND_ADMIN_CHAT_ID.isdigit() else 0: "Артур",
    int(THIRD_ADMIN_CHAT_ID) if str(THIRD_ADMIN_CHAT_ID).isdigit() else 840231919: "Администратор 3",
}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def notify_all_admins(text: str, reply_markup=None):
    """Отправка уведомления всем трем администраторам"""
    if not bot:
        return
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки администратору {admin_id}: {e}")

# ==============================================================================
# FLASK МАРШРУТЫ И MINI APP
# ==============================================================================

def serve_mini_app():
    if os.path.exists(os.path.join("templates", "app.html")):
        return render_template("app.html")
    elif os.path.exists("app.html"):
        with open("app.html", "r", encoding="utf-8") as f:
            return render_template_string(f.read())
    return "Файл app.html не найден", 404

@app.route("/")
@app.route("/app")
@app.route("/webapp")
@app.route("/app.html")
def index_pages():
    return serve_mini_app()

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "mishka-bot", "admins": len(ADMIN_IDS)}), 200

@app.route("/api/prices", methods=["GET"])
@app.route("/api/constants", methods=["GET"])
def api_prices():
    return jsonify(PRICES)

@app.route("/api/calc_well", methods=["POST"])
@app.route("/api/calc", methods=["POST"])
@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.json or {}
    category = data.get("category", "kesson")
    
    if category in ["kesson", "well", "скважина", "кессон", "адаптер"]:
        items = get_well_items(data)
    else:
        # Для других категорий (септики, ливневки) отдаем переданные или заглушку
        items = data.get("items", [])
    
    total = sum(x.get("price", 0) * x.get("qty", 1) for x in items)
    return jsonify({"items": items, "total": total, "status": "success"})

@app.route("/api/miniapp_order", methods=["POST"])
@app.route("/api/order", methods=["POST"])
def api_miniapp_order():
    """Прием заказа из Mini App и рассылка администраторам со списком и чек-боксами"""
    try:
        data = request.json or {}
        client_name = data.get("client_name") or data.get("name") or "Не указан"
        client_phone = data.get("client_phone") or data.get("phone") or "Не указан"
        order_type = data.get("type") or data.get("category") or "Кессон/Скважина"
        items = data.get("items", [])
        total_price = data.get("total") or sum(x.get("price", 0) * x.get("qty", 1) for x in items)
        comment = data.get("comment", "")

        order_id = int(datetime.now().strftime("%d%H%M%S"))

        # Формируем текст уведомления для администраторов
        lines = [
            f"<b>📦 НОВЫЙ ЗАКАЗ #{order_id}</b>",
            f"<b>Тип:</b> {order_type}",
            f"<b>Клиент:</b> {client_name} ({client_phone})",
        ]
        if comment:
            lines.append(f"<b>Примечание:</b> {comment}")

        lines.append("\n<b>Состав заказа:</b>")
        for i, item in enumerate(items, 1):
            name = item.get("name", "Товар")
            qty = item.get("qty", 1)
            unit = item.get("unit", "шт")
            price = item.get("price", 0)
            item_sum = item.get("sum", qty * price)
            lines.append(f"{i}. {name} — {qty} {unit} ({item_sum:,.2f} ₽)")

        lines.append(f"\n💰 <b>ИТОГО К ОПЛАТЕ: {total_price:,.2f} ₽</b>")
        msg_text = "\n".join(lines)

        # Клавиатура сборки для администраторов
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_take = types.InlineKeyboardButton("🛠 Взять в сборку", callback_data=f"take_{order_id}")
        btn_done = types.InlineKeyboardButton("✅ Заказ собран", callback_data=f"done_{order_id}")
        btn_cancel = types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{order_id}")
        markup.add(btn_take, btn_done)
        markup.add(btn_cancel)

        notify_all_admins(msg_text, reply_markup=markup)

        return jsonify({"status": "ok", "order_id": order_id, "message": "Заказ отправлен на склад"}), 200

    except Exception as e:
        print(f"Ошибка обработки заказа: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==============================================================================
# TELEGRAM BOT HANDLERS
# ==============================================================================

if bot:
    @bot.message_handler(commands=["start"])
    def start_handler(message):
        webapp_url = os.getenv("WEBAPP_URL", "https://mishka-kesson-app.onrender.com/app")
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("📦 Открыть склад «МИШКА»", web_app=types.WebAppInfo(url=webapp_url))
        markup.add(btn)
        bot.reply_to(
            message,
            "👋 Добро пожаловать на склад «МИШКА»!\nНажмите кнопку ниже, чтобы открыть приложение:",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "У вас нет прав администратора.", show_alert=True)
            return

        admin_name = ADMIN_NAMES.get(call.from_user.id, call.from_user.first_name)
        data = call.data

        if data.startswith("take_"):
            order_id = data.split("_")[1]
            bot.answer_callback_query(call.id, f"Вы взяли заказ #{order_id} в сборку!")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text + f"\n\n🛠 <b>В сборке у:</b> {admin_name}",
                parse_mode="HTML"
            )
        elif data.startswith("done_"):
            order_id = data.split("_")[1]
            bot.answer_callback_query(call.id, f"Заказ #{order_id} готов к выдаче!")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text + f"\n\n✅ <b>СОБРАН:</b> {admin_name}",
                parse_mode="HTML"
            )
        elif data.startswith("cancel_"):
            order_id = data.split("_")[1]
            bot.answer_callback_query(call.id, f"Заказ #{order_id} отменен.")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text + f"\n\n❌ <b>ОТМЕНЕН:</b> {admin_name}",
                parse_mode="HTML"
            )

def run_bot_polling():
    if bot:
        print(f"Telegram polling запущен для админов: {ADMIN_IDS}")
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"Ошибка polling: {e}")

if __name__ == "__main__":
    t = threading.Thread(target=run_bot_polling, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
