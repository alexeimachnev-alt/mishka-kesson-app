# -*- coding: utf-8 -*-
"""
Основной сервер Flask и Telegram-бот склада «МИШКА»
Совместим с Render Web Service (биндится к $PORT) + Long Polling в потоке.
"""

import os
import threading
from flask import Flask, render_template, request, jsonify
import telebot
from telebot import types

from calc_well import get_well_items
from constants import PRICES

# 1. Flask Web App (для Render и Mini App)
server = Flask(__name__, template_folder="templates")

@server.route("/")
def index():
    return "Склад МИШКА работает!", 200

@server.route("/health")
def health():
    return jsonify({"status": "ok", "service": "mishka-bot"}), 200

# 2. Инициализация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

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

if bot:
    @bot.message_handler(commands=["start"])
    def cmd_start(message):
        bot.reply_to(message, "Добро пожаловать в систему склада «МИШКА»!")

def run_bot_polling():
    if bot:
        print(f"Telegram polling запущен для админов: {ADMIN_IDS}")
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"Ошибка polling: {e}")

if __name__ == "__main__":
    print(f"Склад «МИШКА» запущен. Администраторы: {ADMIN_IDS}")
    
    # Запуск polling в фоновом потоке
    t = threading.Thread(target=run_bot_polling, daemon=True)
    t.start()
    
    # Запуск Flask на порту Render
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)
