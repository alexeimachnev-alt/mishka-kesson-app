import os
import uuid
import urllib.parse
import threading
import requests
from telebot import types

from constants import PRICES, EXTRA_ITEMS, ITEM_TRANSLATIONS, ALL_CATALOG_ITEMS, MESSAGES
from calc_well import get_well_items
from calc_septic import get_septic_items
from calc_drainage import get_drainage_items
from calc_storm import get_storm_items
from calc_extras import add_extras

PRIMARY_ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
SECOND_ADMIN_ID = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))
ADMIN_CHAT_IDS = [PRIMARY_ADMIN_ID, SECOND_ADMIN_ID]

GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()

ACTIVE_ORDERS = {}
REGISTERED_SHEET_ORDERS = set()

def get_admin_name(user_id) -> str:
    try:
        uid = int(str(user_id).strip())
    except (ValueError, TypeError):
        return "Алексей"

    if uid in [SECOND_ADMIN_ID, 447208738]:
        return "Артур"
    return "Алексей"

def format_worker_name(worker_name: str, worker_tag: str) -> str:
    name = str(worker_name or "").strip()
    tag = str(worker_tag or "").strip()
    if name in ["4:20", "Монтажник", ""]:
        return tag if tag else "Монтажник"
    return f"{name} ({tag})" if tag else name

def get_system_name_ru(mode: str) -> str:
    mapping = {
        "well": "Скважина / Кессон",
        "septic": "Септик / Канализация",
        "drainage": "Дренаж участка",
        "storm": "Ливнёвка в земле"
    }
    return mapping.get(str(mode).lower().strip(), "Скважина / Кессон")

def extract_delivery_address(delivery_info: str) -> str:
    if not delivery_info:
        return ""
    text = str(delivery_info)
    if "Адрес:" in text:
        addr_part = text.split("Адрес:")[1]
        if "|" in addr_part:
            addr_part = addr_part.split("|")[0]
        return addr_part.strip()
    if "|" in text:
        return text.split("|")[0].strip()
    return text.strip()

def _send_to_sheet_now(payload: dict):
    webhook_url = GOOGLE_SHEET_WEBHOOK
    if not webhook_url:
        return
    try:
        res = requests.post(webhook_url, json=payload, timeout=10, allow_redirects=True)
        print(f"[SHEET SYNC] Action: {payload.get('action')}, Order: {payload.get('order_id')}, Code: {res.status_code}")
    except Exception as e:
        print(f"[SHEET SYNC ERR] {e}")

def sync_to_google_sheet(order_id: str, data: dict, total_sum: int, items_list: list = None):
    clean_id = str(order_id).strip()
    if clean_id in REGISTERED_SHEET_ORDERS:
        return
    REGISTERED_SHEET_ORDERS.add(clean_id)

    full_client_info = format_worker_name(data.get("worker_name"), data.get("worker_tag"))
    
    items_summary = ""
    if items_list:
        items_summary = ", ".join([f"{it['name']} ({it['qty']} {it['unit']})" for it in items_list])

    payload = {
        "action": "create_order",
        "order_id": clean_id,
        "client_name": full_client_info,
        "phone": str(data.get("phone", "")),
        "items": items_summary or get_system_name_ru(data.get("mode", "well")),
        "total_sum": int(total_sum),
        "delivery_info": str(data.get("delivery_info", "-")),
        "delivery_type": str(data.get("delivery_type", "Самовывоз со склада"))
    }

    threading.Thread(target=_send_to_sheet_now, args=(payload,), daemon=True).start()

def update_sheet_status(order_id: str, status: str, cancel_reason: str = "", manager: str = "", payment_method: str = "-", **kwargs):
    order = ACTIVE_ORDERS.get(order_id, {})
    assembler_val = kwargs.get("assembler") or manager or order.get("collected_by", "")
    payment_val = kwargs.get("payment_type") or payment_method or order.get("payment_method", "")
    if payment_val == "-":
        payment_val = ""
    comment_val = kwargs.get("comment") or cancel_reason or order.get("cancel_reason", "")

    payload = {
        "action": "update_order",
        "order_id": str(order_id).strip(),
        "status": str(status),
        "comment": str(comment_val),
        "assembler": str(assembler_val),
        "payment_type": str(payment_val)
    }

    threading.Thread(target=_send_to_sheet_now, args=(payload,), daemon=True).start()

def get_items_for_order(data: dict):
    mode = data.get("mode", "well")
    extras = data.get("extras", {})
    items = []

    if mode == "well":
        items = get_well_items(data)
    elif mode == "septic":
        items = get_septic_items(data)
    elif mode == "drainage":
        items = get_drainage_items(data)
    elif mode == "storm":
        items = get_storm_items(data)

    items = add_extras(items, extras)
    return items

def render_order_texts(order_id: str, data: dict, items: list, total_sum: int, lang: str):
    t_client = MESSAGES.get(lang, MESSAGES["ru"])
    admin_lines = []
    client_lines = []

    for it in items:
        subtotal = int(it["qty"] * it["price"])
        qty_str = f"{it['qty']:g}" if isinstance(it["qty"], float) else str(it["qty"])
        admin_lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {it['unit']} × {it['price']:,} ₽ = <b>{subtotal:,} ₽</b>".replace(",", " "))
        
        item_key = it.get("item_key")
        if item_key and item_key in ITEM_TRANSLATIONS:
            client_item_name = f"[Доп] {ITEM_TRANSLATIONS[item_key].get(lang, it['name'])}"
        else:
            client_item_name = it["name"]
        
        unit_translated = t_client.get(it.get("unit_key", "unit_pcs"), it["unit"])
        client_lines.append(f"• <b>{client_item_name}</b>\n   └ {qty_str} {unit_translated} × {it['price']:,} ₽ = <b>{subtotal:,} ₽</b>".replace(",", " "))

    delivery_type = data.get("delivery_type", "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = "Доставка" in delivery_type
    clean_address = extract_delivery_address(delivery_info)
    phone = data.get("phone", "Не указан")
    worker_name = format_worker_name(data.get("worker_name"), data.get("worker_tag"))

    if is_delivery:
        admin_logistics = (
            f"🚚 <b>Получение:</b> 🚛 <b>ДОСТАВКА НА ОБЪЕКТ</b>\n"
            f"📍 <b>Адрес доставки:</b> <code>{clean_address or 'Не указан'}</code>\n"
            f"🕒 <b>Детали/Время:</b> <i>{delivery_info}</i>"
        )
        client_logistics = (
            f"{t_client['delivery_type']}\n"
            f"{t_client['addr_label'].format(addr=clean_address or '-')}\n"
            f"{t_client['time_label'].format(time=delivery_info)}"
        )
    else:
        admin_logistics = (
            f"🚚 <b>Получение:</b> 📦 <b>Самовывоз со склада</b>\n"
            f"🕒 <b>Время приезда:</b> <i>{delivery_info}</i>"
        )
        client_logistics = (
            f"{t_client['pickup_type']}\n"
            f"{t_client['time_label'].format(time=delivery_info)}"
        )

    admin_header = (
        f"🧾 <b>ЗАКАЗ #{order_id} «МИШКА»</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👷 <b>Заказчик:</b> {worker_name}\n"
        f"📞 <b>Телефон:</b> <a href='tel:{phone}'>{phone}</a>\n"
        f"{admin_logistics}\n"
        f"🆔 ID клиента: <code>{data.get('chat_id')}</code>\n\n"
        f"📦 <b>СПЕЦИФИКАЦИЯ:</b>\n\n"
        f"{chr(10).join(admin_lines)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>ИТОГО К ОПЛАТЕ: {total_sum:,} ₽</b>"
    ).replace(",", " ")

    client_header = (
        f"{t_client['order_title'].format(order_id=order_id)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t_client['client'].format(name=worker_name, tag='')}\n"
        f"{t_client['phone'].format(phone=phone)}\n"
        f"🚚 <b>Способ:</b> {client_logistics}\n\n"
        f"{t_client['spec_title']}\n\n"
        f"{chr(10).join(client_lines)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t_client['total'].format(sum=f'{total_sum:,}').replace(',', ' ')}"
    )

    return admin_header, client_header

def build_order_payload(data: dict):
    order_id = str(uuid.uuid4())[:8]
    items = get_items_for_order(data)
    lang = data.get("lang", "ru")
    if lang not in MESSAGES:
        lang = "ru"

    total_sum = sum(int(it["qty"] * it["price"]) for it in items)
    admin_header, client_header = render_order_texts(order_id, data, items, total_sum, lang)

    delivery_type = data.get("delivery_type", "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = "Доставка" in delivery_type
    clean_address = extract_delivery_address(delivery_info)

    ACTIVE_ORDERS[order_id] = {
        "client_id": data.get("chat_id"),
        "client_name": format_worker_name(data.get("worker_name"), data.get("worker_tag")),
        "phone": data.get("phone", "Не указан"),
        "delivery_type": delivery_type,
        "delivery_info": delivery_info,
        "clean_address": clean_address,
        "is_delivery": is_delivery,
        "lang": lang,
        "raw_data": data,
        "items": items,
        "collected": [False] * len(items),
        "total_sum": total_sum,
        "status": "active",
        "payment_status": "unpaid"
    }

    sync_to_google_sheet(order_id, data, total_sum, items_list=items)
    return order_id, admin_header, client_header, total_sum

def make_warehouse_keyboard(order_id: str):
    order = ACTIVE_ORDERS.get(order_id)
    if not order:
        return None

    kb = types.InlineKeyboardMarkup(row_width=1)

    if order.get("is_delivery"):
        addr = order.get("clean_address") or extract_delivery_address(order.get("delivery_info", ""))
        if addr:
            nav_url = f"https://yandex.ru/navi?text={urllib.parse.quote(addr)}"
            kb.add(types.InlineKeyboardButton("🚗 Построить маршрут к клиенту (Яндекс)", url=nav_url))

    if order.get("status") == "cancelled":
        reason = order.get("cancel_reason", "")
        reason_txt = f": {reason}" if reason else ""
        kb.add(types.InlineKeyboardButton(f"❌ ЗАКАЗ ОТМЕНЁН{reason_txt}", callback_data="none"))
        return kb

    if order.get("status") == "paid":
        method = order.get("payment_method", "Оплачено")
        kb.add(types.InlineKeyboardButton(f"✅ ОПЛАЧЕН И ВЫДАН ({method})", callback_data="none"))
        return kb

    if order.get("status") == "completed":
        kb.add(types.InlineKeyboardButton("🎉 ЗАКАЗ СОБРАН НА СКЛАДЕ", callback_data="none"))
        kb.add(types.InlineKeyboardButton("💳 ОПЛАТИТЬ И ВЫДАТЬ ТОВАР", callback_data=f"paymenu_{order_id}"))
        kb.row(
            types.InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_{order_id}"),
            types.InlineKeyboardButton("✏️ Изменить комплектацию", callback_data=f"editmenu_{order_id}")
        )
        return kb

    for idx, (item, is_done) in enumerate(zip(order["items"], order["collected"])):
        mark = "🟢" if is_done else "⬜"
        qty_str = f"{item['qty']:g}" if isinstance(item['qty'], float) else str(item['qty'])
        short_name = (item['name'][:22] + "..") if len(item['name']) > 22 else item['name']
        btn_text = f"{mark} {idx+1}. {short_name} ({qty_str} {item['unit']})"
        kb.add(types.InlineKeyboardButton(btn_text, callback_data=f"chk_{order_id}_{idx}"))

    all_done = all(order["collected"])
    finish_icon = "🚀" if all_done else "📦"
    kb.add(types.InlineKeyboardButton(f"{finish_icon} ЗАКАЗ ПОЛНОСТЬЮ СОБРАН", callback_data=f"fin_{order_id}"))

    kb.row(
        types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{order_id}"),
        types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"editmenu_{order_id}")
    )

    return kb
