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
    ACTIVE_ORDERS, 
    ADMIN_CHAT_IDS,
    MESSAGES,
    ALL_CATALOG_ITEMS
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
            "worker_tag": f"@{data.get('username')}" if data.get('username') else "",
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

        for a_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(a_id, admin_text, parse_mode="HTML", reply_markup=kb_admin)
            except Exception as e:
                print(f"[ERR ADMIN SEND] {a_id}: {e}")

        if user_id:
            try:
                lang = session_data.get("lang", "ru")
                t_client = MESSAGES.get(lang, MESSAGES["ru"])

                kb_client = tele_types.Inline
