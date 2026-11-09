# -*- coding: utf-8 -*-
"""
Основной сервер и Telegram-бот склада «МИШКА»
Интеграция с тремя администраторами и модулями расчета смет.
"""

import os
import telebot
from telebot import types
from calc_well import get_well_items
from constants import PRICES

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

# Список администраторов (Алексей, Артур, 3-й админ)
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
SECOND_ADMIN_CHAT_ID = os.getenv("SECOND_ADMIN_CHAT_ID")
THIRD_ADMIN_CHAT_ID = os.getenv("THIRD_ADMIN_CHAT_ID", "840231919")

# Список всех ID для прав и уведомлений
ADMIN_IDS = [
    int(x) for x in [ADMIN_CHAT_ID, SECOND_ADMIN_CHAT_ID, THIRD_ADMIN_CHAT_ID]
    if x and str(x).strip().isdigit()
]

# Имена администраторов для отметок о сборщике заказа
ADMIN_NAMES = {
    int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID and ADMIN_CHAT_ID.isdigit() else 0: "Алексей",
    int(SECOND_ADMIN_CHAT_ID) if SECOND_ADMIN_CHAT_ID and SECOND_ADMIN_CHAT_ID.isdigit() else 0: "Артур",
    int(THIRD_ADMIN_CHAT_ID) if str(THIRD_ADMIN_CHAT_ID).isdigit() else 840231919: "Администратор 3",
}

def is_admin(user_id: int) -> bool:
    """Проверка прав доступа администратора."""
    return user_id in ADMIN_IDS

def notify_all_admins(text: str, reply_markup=None):
    """Рассылка нового заказа или статуса всем трем администраторам."""
    if not bot:
        return
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки уведомления администратору {admin_id}: {e}")

if __name__ == "__main__":
    print(f"Склад «МИШКА» запущен. Администраторы: {ADMIN_IDS}")
    if bot:
        bot.infinity_polling(skip_pending=True)
