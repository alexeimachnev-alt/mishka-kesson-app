# -*- coding: utf-8 -*-
"""
Основной сервер Flask и Telegram-бот склада «МИШКА»
Обслуживание Mini App (HTML), API расчета и Telegram-бота с 3 администраторами.
"""

import os
import threading
from flask import Flask, render_template, render_template_string, request, jsonify, send_from_directory
import telebot
from telebot import types

from calc_well import get_well_items
from constants import PRICES

# Инициализация Flask (ищет шаблоны в папке templates и в корне)
app = Flask(__name__, template_folder="templates", static_folder=".")

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

# Список администраторов (Алексей, Артур, 3-й админ)
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
    if not bot:
        return
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки администратору {admin_id}: {e}")

# ==============================================================================
# FLASK МАРШРУТЫ ДЛЯ MINI APP (ОБРАБОТКА ВСЕХ ВОЗМОЖНЫХ URL ТЕЛЕГРАМА)
# ==============================================================================

def serve_mini_app():
    """Отдает app.html из папки templates или из корня"""
    if os.path.exists(os.path.join("templates", "app.html")):
        return render_template("app.html")
    elif os.path.exists("app.html"):
        with open("app.html", "r", encoding="utf-8") as f:
            return render_template_string(f.read())
    return "Шаблон app.html не найден", 404

@app.route("/")
def home():
    return serve_mini_app()

@app.route("/app")
@app.route("/webapp")
@app.route("/app.html")
@app.route("/templates/app.html")
def app_pages():
    return serve_mini_app()

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "mishka-bot"}), 200

@app.route("/api/calc_well", methods=["POST"])
def api_calc_well():
    data = request.json or {}
    items = get_well_items(data)
    total = sum(x["price"] * x["qty"] for x in items)
    return jsonify({"items": items, "total": total})

# ==============================================================================
# TELEGRAM BOT HANDLERS & POLLING
# ==============================================================================

if bot:
    @bot.message_handler(commands=["start"])
    def start_handler(message):
        keyboard = types.InlineKeyboardMarkup()
        # Ссылка на Mini App (URL сервиса Render)
        webapp_url = os.getenv("WEBAPP_URL", "https://mishka-kesson-app.onrender.com")
        btn = types.InlineKeyboardButton("📦 Открыть склад «МИШКА»", web_app=types.WebAppInfo(url=webapp_url))
        keyboard.add(btn)
        bot.reply_to(
            message,
            "👋 Добро пожаловать на склад «МИШКА»! Нажмите кнопку ниже, чтобы открыть калькулятор и каталог:",
            reply_markup=keyboard
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
