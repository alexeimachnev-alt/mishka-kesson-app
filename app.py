import os
import time
import threading
import requests
from flask import Flask, render_template, request, jsonify
import telebot
from telebot import types as tele_types
from calc_module import build_warehouse_checklist, send_to_all_admins

TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip().strip("'\"")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# Эндпоинты для проверки здоровья и пингатора
@app.route("/")
@app.route("/health")
def health_check():
    return "Mishka MiniApp Backend is alive and running!", 200

# Отдача HTML-страницы Mini App
@app.route("/app")
def serve_webapp():
    return render_template("app.html")

# Приём заказа из Mini App (Кессон или Септик)
@app.route("/api/miniapp_order", methods=["POST"])
def handle_miniapp_order():
    try:
        data = request.json or {}
        user_id = data.get("user_id", 0)

        session_data = {
            "mode": data.get("mode", "well"),
            "lang": data.get("lang", "ru"),
            "extras": data.get("extras", {}),
            "worker_tag": f"@{data.get('username')}" if data.get('username') else "нет username",
            "worker_name": data.get("first_name", "Монтажник"),
            "chat_id": user_id,
            # Параметры скважины
            "depth": data.get("depth", 40),
            "yield_flow": data.get("yield_flow", 2.5),
            "houses": data.get("houses", 1),
            "distances": data.get("distances", [15]),
            "chosen_kesson": data.get("chosen_kesson", "auto"),
            # Параметры септика
            "users": data.get("users", 5),
            "discharge": data.get("discharge", "gravity"),
            "distance": data.get("distance", 10),
            "chosen_septic": data.get("chosen_septic", "auto")
        }

        # Генерация подробной сметы с ценами
        checklist = build_warehouse_checklist(session_data)

        # 1. Отправка администраторам (551209811 и 447208738)
        send_to_all_admins(bot, checklist)

        # 2. Отправка сметы заказчику/монтажнику в чат Telegram
        if user_id:
            try:
                bot.send_message(user_id, f"✅ <b>Заказ принят складом!</b>\n\n{checklist}", parse_mode="HTML")
            except Exception as client_err:
                print(f"[WARN] Ошибка отправки заказчику {user_id}: {client_err}")

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"[ERROR API] {e}")
        return jsonify({"error": str(e)}), 500

# Команда /start с вызовом Mini App
@bot.message_handler(commands=['start'])
def handle_start(message):
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://mishka-kesson-app.onrender.com").rstrip("/")
    kb = tele_types.InlineKeyboardMarkup()
    web_app_info = tele_types.WebAppInfo(url=f"{render_url}/app")
    kb.add(tele_types.InlineKeyboardButton("📱 Открыть склад МИШКА (Кессоны и Септики)", web_app=web_app_info))

    bot.reply_to(
        message,
        "👋 <b>Склад завода «МИШКА»</b>\n\n"
        "Нажмите кнопку ниже, чтобы выбрать оборудование (кессоны для скважин или станции септиков) и сформировать смету комплекта к отгрузке:",
        reply_markup=kb,
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
            print(f"Сбой polling: {e}. Перезапуск через 3 сек...")
            time.sleep(3)

def keep_alive_ping():
    """Фоновый пингатор: стучится на сервер каждые 9 минут, чтобы Render не засыпал."""
    time.sleep(40)  # Даём сервису полностью стартовать
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://mishka-kesson-app.onrender.com").rstrip("/")
    ping_url = f"{render_url}/health"
    print(f"[PINGATOR] Запущен автопинг для: {ping_url}")

    while True:
        try:
            res = requests.get(ping_url, timeout=15)
            print(f"[PINGATOR] Успешный пинг на {ping_url} (Статус: {res.status_code})")
        except Exception as err:
            print(f"[PINGATOR] Ошибка при автопинге: {err}")
        # Пингуем каждые 540 секунд (9 минут), тайм-аут сна Render — 15 минут
        time.sleep(540)

if __name__ == "__main__":
    # Запуск бота в отдельном потоке
    t_bot = threading.Thread(target=run_telebot, daemon=True)
    t_bot.start()

    # Запуск внутреннего пингатора в отдельном потоке
    t_ping = threading.Thread(target=keep_alive_ping, daemon=True)
    t_ping.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
