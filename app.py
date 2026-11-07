import os
import time
import threading
from flask import Flask, render_template, request, jsonify
import telebot
from telebot import types as tele_types
from calc_module import build_warehouse_checklist, send_to_all_admins

TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip().strip("'\"")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

@app.route("/")
@app.route("/health")
def health_check():
    return "Mishka MiniApp Backend is alive!", 200

# Отдача HTML-страницы приложения
@app.route("/app")
def serve_webapp():
    return render_template("app.html")

# Приём заказа из Mini App
@app.route("/api/miniapp_order", methods=["POST"])
def handle_miniapp_order():
    try:
        data = request.json or {}
        session_data = {
            "depth": data.get("depth", 40),
            "yield_flow": data.get("yield_flow", 2.5),
            "houses": data.get("houses", 1),
            "distances": data.get("distances", [15]),
            "extras": data.get("extras", {}),
            "chosen_kesson": data.get("chosen_kesson", "auto"),
            "lang": data.get("lang", "ru"),
            "worker_tag": f"@{data.get('username')}" if data.get('username') else "нет username",
            "worker_name": data.get("first_name", "Монтажник"),
            "chat_id": data.get("user_id", 0)
        }
        checklist = build_warehouse_checklist(session_data)
        send_to_all_admins(bot, checklist)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"[ERROR API] {e}")
        return jsonify({"error": str(e)}), 500

# Команда /start с кнопкой открытия Mini App
@bot.message_handler(commands=['start'])
def handle_start(message):
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://ВАШ_СЕРВИС.onrender.com").rstrip("/")
    kb = tele_types.InlineKeyboardMarkup()
    web_app_info = tele_types.WebAppInfo(url=f"{render_url}/app")
    kb.add(tele_types.InlineKeyboardButton("📱 Открыть приложение склада МИШКА", web_app=web_app_info))

    bot.reply_to(
        message,
        "👋 <b>Склад кессонов и скважинного оборудования «МИШКА»</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть калькулятор и собрать заказ к вашему приезду:",
        reply_markup=kb,
        parse_mode="HTML"
    )

def setup_menu():
    try:
        bot.set_my_commands([
            tele_types.BotCommand("start", "Открыть приложение склада")
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

if __name__ == "__main__":
    t = threading.Thread(target=run_telebot, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
