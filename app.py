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
    ACTIVE_ORDERS, 
    ADMIN_CHAT_IDS
)

TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip().strip("'\"")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

WELCOME_BANNER_URL = "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1000&q=80"

@app.route("/")
@app.route("/health")
def health_check():
    return "Mishka MiniApp Backend is alive and running!", 200

@app.route("/app")
def serve_webapp():
    return render_template("app.html")

@app.route("/api/miniapp_order", methods=["POST"])
def handle_miniapp_order():
    try:
        data = request.json or {}
        user_id = data.get("user_id", 0)

        session_data = {
            "mode": data.get("mode", "well"),
            "lang": data.get("lang", "ru"),
            "phone": data.get("phone", "Не указан"),
            "extras": data.get("extras", {}),
            "worker_tag": f"@{data.get('username')}" if data.get('username') else "нет username",
            "worker_name": data.get("first_name", "Монтажник"),
            "chat_id": user_id,
            "depth": data.get("depth", 40),
            "yield_flow": data.get("yield_flow", 2.5),
            "houses": data.get("houses", 1),
            "distances": data.get("distances", [15]),
            "chosen_kesson": data.get("chosen_kesson", "auto"),
            "users": data.get("users", 5),
            "discharge": data.get("discharge", "gravity"),
            "distance": data.get("distance", 10),
            "chosen_septic": data.get("chosen_septic", "auto"),
            "drain_type": data.get("drain_type", "softrock"),
            "drain_length": data.get("drain_length", 50),
            "drain_wells": data.get("drain_wells", 3),
            "storm_inlets": data.get("storm_inlets", 4),
            "storm_length": data.get("storm_length", 30),
            "storm_wells": data.get("storm_wells", 2),
            "storm_discharge": data.get("storm_discharge", "ditch")
        }

        # 1. Генерируем смету и создаём складской заказ с чек-листом
        order_id, estimate_text, total_sum = build_order_payload(session_data)
        kb = make_warehouse_keyboard(order_id)

        # 2. Отправляем администраторам склада интерактивную смету с кнопками-галочками
        for a_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(a_id, estimate_text, parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                print(f"[ERR ADMIN SEND] {a_id}: {e}")

        # 3. Отправляем клиенту подтверждение с полным списком и контактами
        if user_id:
            try:
                client_msg = (
                    f"✅ <b>Ваш заказ принят складом! Номер заказа: #{order_id}</b>\n\n"
                    f"{estimate_text}\n\n"
                    f"📞 Контакт для связи: {session_data['phone']}\n"
                    f"⏳ <i>Мы оповестим вас здесь, как только заказ будет полностью скомплектован!</i>"
                )
                bot.send_message(user_id, client_msg, parse_mode="HTML")
            except Exception as client_err:
                print(f"[ERR CLIENT SEND] {user_id}: {client_err}")

        return jsonify({"status": "ok", "order_id": order_id}), 200
    except Exception as e:
        print(f"[ERROR API] {e}")
        return jsonify({"error": str(e)}), 500

# Обработчик кликов по кнопкам комплектации позиций и кнопке «ЗАКАЗ СОБРАН»
@bot.callback_query_handler(func=lambda call: True)
def handle_warehouse_clicks(call):
    data = call.data
    if data.startswith("chk_"):
        parts = data.split("_")
        order_id = parts[1]
        item_idx = int(parts[2])

        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден в текущей сессии")
            return

        # Переключаем статус (собрано / не собрано)
        order["collected"][item_idx] = not order["collected"][item_idx]
        new_kb = make_warehouse_keyboard(order_id)

        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_kb)
        except Exception:
            pass

        item_name = order["items"][item_idx]["name"]
        status = "взят со склада ✅" if order["collected"][item_idx] else "снят с отметки ❌"
        bot.answer_callback_query(call.id, f"{item_name}: {status}")

    elif data.startswith("fin_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        order["completed"] = True
        new_kb = make_warehouse_keyboard(order_id)
        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_kb)
        except Exception:
            pass

        bot.answer_callback_query(call.id, f"Заказ #{order_id} собран! Клиент уведомлен.")

        # Оповещаем клиента о готовности
        client_id = order.get("client_id")
        if client_id:
            try:
                alert_text = (
                    f"🎉 <b>ВАШ ЗАКАЗ #{order_id} ПОЛНОСТЬЮ СОБРАН!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 Все комплектующие проверены и готовы к отгрузке на складе «МИШКА».\n"
                    f"💰 Сумма к оплате: <b>{order['total_sum']:,} ₽</b>\n\n"
                    f"Ждём вас на складе для получения оборудования!".replace(",", " ")
                )
                bot.send_message(client_id, alert_text, parse_mode="HTML")
            except Exception as e:
                print(f"[ERR NOTIFY CLIENT] {client_id}: {e}")

@bot.message_handler(commands=['start'])
def handle_start(message):
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://mishka-kesson-app.onrender.com").rstrip("/")
    web_app_url = f"{render_url}/app"

    inline_kb = tele_types.InlineKeyboardMarkup()
    inline_kb.add(
        tele_types.InlineKeyboardButton(
            "🚀 НАЖМИТЕ СЮДА — ОТКРЫТЬ СКЛАД 📦",
            web_app=tele_types.WebAppInfo(url=web_app_url)
        )
    )

    caption_text = (
        "👋 <b>Добро пожаловать на склад оборудования «МИШКА»!</b>\n\n"
        "Здесь вы можете за 1 минуту собрать полную смету с ценами:\n"
        "• <b>Кессоны</b> и обустройство скважин\n"
        "• <b>Септики</b> и канализация\n"
        "• <b>Дренаж</b> («Софтрок» или классика)\n"
        "• <b>Подземная ливнёвка</b> от дома\n\n"
        "👇 <b>НАЖМИТЕ КНОПКУ НИЖЕ ДЛЯ ВХОДА В ПРИЛОЖЕНИЕ:</b>\n"
        "⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️"
    )

    try:
        bot.send_photo(
            message.chat.id,
            photo=WELCOME_BANNER_URL,
            caption=caption_text,
            reply_markup=inline_kb,
            parse_mode="HTML"
        )
    except Exception:
        bot.send_message(
            message.chat.id,
            caption_text,
            reply_markup=inline_kb,
            parse_mode="HTML"
        )

def setup_menu():
    try:
        bot.set_my_commands([
            tele_types.BotCommand("start", "Открыть склад и калькулятор")
        ])
    except Exception:
        pass

def run_telebot():
    print("Запуск Telegram Polling...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(1)
    except Exception:
        pass
    setup_menu()
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"Сбой polling: {e}. Перезапуск...")
            time.sleep(3)

def keep_alive_ping():
    time.sleep(40)
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://mishka-kesson-app.onrender.com").rstrip("/")
    ping_url = f"{render_url}/health"

    while True:
        try:
            requests.get(ping_url, timeout=15)
        except Exception:
            pass
        time.sleep(540)

if __name__ == "__main__":
    t_bot = threading.Thread(target=run_telebot, daemon=True)
    t_bot.start()

    t_ping = threading.Thread(target=keep_alive_ping, daemon=True)
    t_ping.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
