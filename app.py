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
    ACTIVE_ORDERS, 
    ADMIN_CHAT_IDS,
    MESSAGES
)

TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip().strip("'\"")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

YANDEX_MAPS_URL = "https://yandex.ru/navi?text=56.047416,37.538633&si=vuyt53qweyhyb7h2vyjb16pg04"
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
            "delivery_type": data.get("delivery_type", "Самовывоз со склада"),
            "delivery_info": data.get("delivery_info", "-"),
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

        order_id, admin_text, client_text, total_sum = build_order_payload(session_data)
        kb_admin = make_warehouse_keyboard(order_id)

        # 1. Отправка администраторам склада (на русском языке)
        for a_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(a_id, admin_text, parse_mode="HTML", reply_markup=kb_admin)
            except Exception as e:
                print(f"[ERR ADMIN SEND] {a_id}: {e}")

        # 2. Отправка подтверждения заказчику (на его родном языке)
        if user_id:
            try:
                lang = session_data.get("lang", "ru")
                t_client = MESSAGES.get(lang, MESSAGES["ru"])

                kb_client = tele_types.InlineKeyboardMarkup(row_width=1)
                if not session_data.get("is_delivery"):
                    kb_client.add(tele_types.InlineKeyboardButton(t_client["btn_nav_sklad"], url=YANDEX_MAPS_URL))
                kb_client.add(tele_types.InlineKeyboardButton(t_client["btn_repeat"], callback_data=f"repeat_{order_id}"))

                client_msg = t_client["accepted"].format(order_id=order_id, body=client_text)
                bot.send_message(user_id, client_msg, parse_mode="HTML", reply_markup=kb_client)
            except Exception as client_err:
                print(f"[ERR CLIENT SEND] {user_id}: {client_err}")

        return jsonify({"status": "ok", "order_id": order_id}), 200
    except Exception as e:
        print(f"[ERROR API] {e}")
        return jsonify({"error": str(e)}), 500

# Обработка нажатий кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data

    # Отметка позиций
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

    # Заказ полностью собран
    elif data.startswith("fin_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        order["status"] = "completed"
        # Клавиатура перерисуется, но кнопка маршрута к клиенту останется активной
        new_kb = make_warehouse_keyboard(order_id)
        try:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_kb)
        except Exception:
            pass

        update_sheet_status(order_id, "Собран на складе")
        bot.answer_callback_query(call.id, f"Заказ #{order_id} собран! Клиент уведомлен.")

        # Уведомляем клиента на ЕГО родном языке
        client_id = order.get("client_id")
        if client_id:
            try:
                lang = order.get("lang", "ru")
                t_client = MESSAGES.get(lang, MESSAGES["ru"])
                
                sum_formatted = f"{order['total_sum']:,}".replace(",", " ")
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

    # Запрос на отмену (спрашиваем причину у менеджера)
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
            f"<i>(Причина пойдет в Google Таблицу и админам, клиент её НЕ увидит):</i>",
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, process_cancel_reason, order_id, call.message.message_id)

    # Запрос на корректировку
    elif data.startswith("edit_"):
        order_id = data.split("_")[1]
        order = ACTIVE_ORDERS.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден")
            return

        bot.answer_callback_query(call.id, "Запрос на корректировку отправлен клиенту")
        client_id = order.get("client_id")
        if client_id:
            try:
                lang = order.get("lang", "ru")
                edit_msgs = {
                    "ru": f"✏️ <b>По заказу #{order_id} требуется уточнение!</b>\nМенеджер склада свяжется с вами или отправьте обновлённый расчёт через приложение.",
                    "tj": f"✏️ <b>Оид ба фармоиши #{order_id} маълумоти иловагӣ лозим аст!</b>\nМенеҷери анбор бо шумо тамос мегирад ё метавонед ҳисоби навро тавассути барнома фиристед.",
                    "uz": f"✏️ <b>#{order_id} buyurtmasi bo'yicha aniqlik kiritish kerak!</b>\nOmbor menejeri siz bilan bog'lanadi yoki dastur orqali yangilangan hisob-kitobni yuboring.",
                    "hy": f"✏️ <b>#{order_id} պատվերի վերաբերյալ ճշգրտում է պահանջվում:</b>\nՊահեստապետը կկապվի Ձեզ հետ կամ կարող եք ուղարկել թարմացված հաշվարկը:",
                    "ky": f"✏️ <b>#{order_id} буйрутмасы боюнча тактоо талап кылынат!</b>\nКампа менеджери сиз менен байланышат же тиркеме аркылуу жаңыланган эсепти жөнөтүңүз."
                }
                bot.send_message(client_id, edit_msgs.get(lang, edit_msgs["ru"]), parse_mode="HTML")
            except Exception:
                pass

    # Повтор заказа
    elif data.startswith("repeat_"):
        old_order_id = data.split("_")[1]
        old_order = ACTIVE_ORDERS.get(old_order_id)
        if not old_order:
            bot.answer_callback_query(call.id, "Предыдущий заказ не найден в базе, соберите новый через приложение")
            return

        bot.answer_callback_query(call.id, "Создаём повторный заказ...")
        new_data = dict(old_order["raw_data"])
        new_order_id, admin_text, client_text, _ = build_order_payload(new_data)
        new_kb = make_warehouse_keyboard(new_order_id)

        for a_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(a_id, f"🔄 <b>ПОВТОР ЗАКАЗА #{old_order_id} ➔ #{new_order_id}</b>\n\n" + admin_text, parse_mode="HTML", reply_markup=new_kb)
            except Exception:
                pass

        try:
            lang = new_data.get("lang", "ru")
            repeat_confirm = {
                "ru": f"✅ <b>Заказ успешно повторен! Новый номер: #{new_order_id}</b>\n\nСклад уже приступил к сборке.",
                "tj": f"✅ <b>Фармоиш такрор шуд! Рақами нав: #{new_order_id}</b>\n\nАнбор ба тайёр кардани бор оғоз кард.",
                "uz": f"✅ <b>Buyurtma muvaffaqiyatli takrorlandi! Yangi raqam: #{new_order_id}</b>\n\nOmbor mahsulotlarni yig'ishga kirishdi.",
                "hy": f"✅ <b>Պատվերը հաջողությամբ կրկնվեց: Նոր համար: #{new_order_id}</b>\n\nՊահեստը սկսել է հավաքել:",
                "ky": f"✅ <b>Заказ кайталанды! Жаңы номери: #{new_order_id}</b>\n\nКампа топтоону баштады."
            }
            bot.send_message(call.message.chat.id, repeat_confirm.get(lang, repeat_confirm["ru"]), parse_mode="HTML")
        except Exception:
            pass

def process_cancel_reason(message, order_id, original_msg_id):
    reason = message.text.strip()
    order = ACTIVE_ORDERS.get(order_id)
    if not order:
        bot.reply_to(message, "Заказ не найден в текущей сессии.")
        return

    order["status"] = "cancelled"
    order["cancel_reason"] = reason

    new_kb = make_warehouse_keyboard(order_id)
    try:
        bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=original_msg_id, reply_markup=new_kb)
    except Exception:
        pass

    update_sheet_status(order_id, "Отменён", reason)
    bot.reply_to(message, f"✅ Заказ #{order_id} отменён.\nПричина <i>«{reason}»</i> записана в Google Таблицу.", parse_mode="HTML")

    client_id = order.get("client_id")
    if client_id:
        try:
            lang = order.get("lang", "ru")
            cancel_msgs = {
                "ru": f"❌ <b>Ваш заказ #{order_id} отменён складом.</b>\nЕсли у вас есть вопросы, свяжитесь с отделом продаж завода «МИШКА».",
                "tj": f"❌ <b>Фармоиши шумо #{order_id} аз ҷониби анбор бекор карда шуд.</b>\nАгар саволҳо бошанд, бо шуъбаи фурӯши корхонаи «МИШКА» дар тамос шавед.",
                "uz": f"❌ <b>#{order_id} raqamli buyurtmangiz ombor tomonidan bekor qilindi.</b>\nSavollaringiz bo'lsa, «MISHKA» savdo bo'limi bilan bog'laning.",
                "hy": f"❌ <b>Ձեր #{order_id} պատվերը չեղարկվել է պահեստի կողմից:</b>\nՀարցերի դեպքում կապվեք «ՄԻՇԿԱ» գործարանի վաճառքի բաժնի հետ:",
                "ky": f"❌ <b>Сиздин #{order_id} буйрутмаңыз кампа тарабынан жокко чыгарылды.</b>\nСуроолор болсо, «МИШКА» сатуу бөлүмүнө кайрылыңыз."
            }
            bot.send_message(client_id, cancel_msgs.get(lang, cancel_msgs["ru"]), parse_mode="HTML")
        except Exception:
            pass

@bot.message_handler(commands=['start'])
def handle_start(message):
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://mishka-kesson-app.onrender.com").rstrip("/")
    web_app_url = f"{render_url}/app"

    inline_kb = tele_types.InlineKeyboardMarkup(row_width=1)
    inline_kb.add(
        tele_types.InlineKeyboardButton("🚀 НАЖМИТЕ СЮДА — ОТКРЫТЬ СКЛАД 📦", web_app=tele_types.WebAppInfo(url=web_app_url)),
        tele_types.InlineKeyboardButton("📍 Где наш склад? (Маршрут)", url=YANDEX_MAPS_URL)
    )

    caption_text = (
        "👋 <b>Добро пожаловать на склад завода «МИШКА»!</b>\n\n"
        "Здесь вы можете за 1 минуту собрать полную смету с ценами:\n"
        "• <b>Кессоны</b> и обустройство скважин\n"
        "• <b>Септики</b> и канализация\n"
        "• <b>Дренаж</b> («Софтрок» или классика)\n"
        "• <b>Подземная ливнёвка</b> от дома\n\n"
        "🚚 <i>Доступен самовывоз со склада или доставка на ваш объект!</i>\n\n"
        "👇 <b>НАЖМИТЕ КНОПКУ НИЖЕ ДЛЯ ВХОДА В ПРИЛОЖЕНИЕ:</b>\n"
        "⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️"
    )

    try:
        bot.send_photo(message.chat.id, photo=WELCOME_BANNER_URL, caption=caption_text, reply_markup=inline_kb, parse_mode="HTML")
    except Exception:
        bot.send_message(message.chat.id, caption_text, reply_markup=inline_kb, parse_mode="HTML")

def setup_menu():
    try:
        bot.set_my_commands([tele_types.BotCommand("start", "Открыть склад и калькулятор")])
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
