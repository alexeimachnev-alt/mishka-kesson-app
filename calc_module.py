# -*- coding: utf-8 -*-
import os
import uuid
import urllib.parse
import threading
import requests
from telebot import types

from calc_well import get_well_items
from constants import PRICES, KESSON_MODELS, TANK_CATALOG, HYDRANT_CATALOG

ADMIN_1 = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
ADMIN_2 = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))
ADMIN_3 = int(os.getenv("THIRD_ADMIN_CHAT_ID", "840231919"))
ADMIN_CHAT_IDS = [ADMIN_1, ADMIN_2, ADMIN_3]

GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()
YANDEX_MAPS_URL = "https://yandex.ru/navi?text=56.047416,37.538633&si=vuyt53qweyhyb7h2vyjb16pg04"

ACTIVE_ORDERS = {}
REGISTERED_SHEET_ORDERS = set()

ITEM_TRANSLATIONS = {}

SERVICES_CATALOG = [{'code': 'work_kesson_std', 'cat': 'kesson', 'name': 'Монтаж кессона (обвязка, ПНР, выход под кабель и магистраль)', 'price': 23000.0, 'unit': 'усл.'}, {'code': 'work_kesson_weld', 'cat': 'kesson', 'name': 'Монтаж кессона со сваркой (обвязка, ПНР, кабель, магистраль)', 'price': 26000.0, 'unit': 'усл.'}, {'code': 'work_kesson_extra_outlet', 'cat': 'kesson', 'name': 'Дополнительный выход из кессона', 'price': 1500.0, 'unit': 'шт.'}, {'code': 'work_kesson_demount_mount', 'cat': 'kesson', 'name': 'Демонтаж и повторный монтаж кессона', 'price': 55000.0, 'unit': 'компл.'}, {'code': 'work_adapter_turnkey', 'cat': 'kesson', 'name': 'Монтаж скважинного адаптера «под ключ»', 'price': 17000.0, 'unit': 'усл.'}, {'code': 'work_well_turnkey', 'cat': 'kesson', 'name': 'Монтаж колодца «под ключ»', 'price': 17000.0, 'unit': 'усл.'}, {'code': 'work_summer_tap', 'cat': 'kesson', 'name': 'Монтаж узла летнего полива', 'price': 12000.0, 'unit': 'усл.'}, {'code': 'work_pump_change_50', 'cat': 'kesson', 'name': 'Замена скважинного насоса до 50 м (труба 32 мм)', 'price': 35000.0, 'unit': 'усл.'}, {'code': 'work_pump_change_100', 'cat': 'kesson', 'name': 'Замена скважинного насоса от 50 до 100 м (труба 32 мм)', 'price': 45000.0, 'unit': 'усл.'}, {'code': 'work_pump_demount', 'cat': 'kesson', 'name': 'Демонтаж скважинного насоса (отдельно)', 'price': 12000.0, 'unit': 'усл.'}, {'code': 'work_self_overflow_3', 'cat': 'kesson', 'name': 'Монтаж самоизливной скважины с кессоном (до 3 м³/ч)', 'price': 45000.0, 'unit': 'усл.'}, {'code': 'work_self_overflow_10', 'cat': 'kesson', 'name': 'Монтаж самоизливной скважины с кессоном (от 3 до 10 м³/ч)', 'price': 75000.0, 'unit': 'усл.'}, {'code': 'work_self_overflow_30', 'cat': 'kesson', 'name': 'Монтаж самоизливной скважины с кессоном (от 10 до 30 м³/ч)', 'price': 100000.0, 'unit': 'усл.'}, {'code': 'work_septic_mount', 'cat': 'septic', 'name': 'Монтаж септика от 3 до 6 (стандарт)', 'price': 15000.0, 'unit': 'усл.'}, {'code': 'work_pipe_110_lay', 'cat': 'septic', 'name': 'Укладка трубы 110 в траншею', 'price': 200.0, 'unit': 'м.п.'}, {'code': 'work_dig_septic', 'cat': 'septic', 'name': 'Копка котлована под септик (стандарт 1.2х2 м)', 'price': 10000.0, 'unit': 'усл.'}, {'code': 'work_dig_trench_50', 'cat': 'earth', 'name': 'Земляные работы (траншея глубиной до 50 см)', 'price': 650.0, 'unit': 'м.п.'}, {'code': 'work_dig_trench_100', 'cat': 'earth', 'name': 'Земляные работы (траншея глубиной до 100 см)', 'price': 800.0, 'unit': 'м.п.'}, {'code': 'work_dig_trench_150', 'cat': 'earth', 'name': 'Земляные работы (траншея глубиной до 150 см)', 'price': 1100.0, 'unit': 'м.п.'}, {'code': 'work_dig_trench_200', 'cat': 'earth', 'name': 'Земляные работы (траншея глубиной до 200 см)', 'price': 1600.0, 'unit': 'м.п.'}, {'code': 'work_dig_kesson_type2', 'cat': 'earth', 'name': 'Копка котлована под кессон Тип 2 (1.2 м)', 'price': 9000.0, 'unit': 'усл.'}, {'code': 'work_dig_kesson_type3', 'cat': 'earth', 'name': 'Копка котлована под кессон Тип 3 (1.2–2.0 м)', 'price': 12000.0, 'unit': 'усл.'}, {'code': 'work_dig_kesson_type4', 'cat': 'earth', 'name': 'Копка котлована под кессон Тип 4 (1.5–2.0 м)', 'price': 15000.0, 'unit': 'усл.'}, {'code': 'work_undermine_2m', 'cat': 'earth', 'name': 'Подкоп под фундаментом / препятствием (до 2 м)', 'price': 3000.0, 'unit': 'усл.'}, {'code': 'work_undermine_5m', 'cat': 'earth', 'name': 'Подкоп под фундаментом / препятствием (от 2 до 5 м)', 'price': 5000.0, 'unit': 'усл.'}, {'code': 'work_trench_under_stilts', 'cat': 'earth', 'name': 'Копка траншеи под домом на сваях (глубина до 1 м)', 'price': 2000.0, 'unit': 'м.п.'}, {'code': 'work_min_digger_shift', 'cat': 'earth', 'name': 'Минимальный выезд землекопа', 'price': 5000.0, 'unit': 'выход'}, {'code': 'work_formwork_mount', 'cat': 'earth', 'name': 'Монтаж опалубки в траншее / котловане', 'price': 10000.0, 'unit': 'усл.'}, {'code': 'work_jackhammer_rent', 'cat': 'earth', 'name': 'Аренда отбойного молотка (за 1 день)', 'price': 2000.0, 'unit': 'день'}, {'code': 'work_soil_move_20m', 'cat': 'earth', 'name': 'Перенос грунта по участку (до 20 м)', 'price': 2500.0, 'unit': 'м³'}, {'code': 'work_sand_move_20m', 'cat': 'earth', 'name': 'Перевозка песка по участку (до 20 м)', 'price': 1500.0, 'unit': 'м³'}, {'code': 'work_sand_move_50m', 'cat': 'earth', 'name': 'Перевозка песка по участку (от 20 до 50 м)', 'price': 2500.0, 'unit': 'м³'}, {'code': 'work_equip_carry_40m', 'cat': 'earth', 'name': 'Перенос оборудования по участку (от 20 до 40 м)', 'price': 2500.0, 'unit': 'усл.'}, {'code': 'work_storm_lay_50', 'cat': 'drainage', 'name': 'Монтаж ливнёвки (глубина до 50 см)', 'price': 750.0, 'unit': 'м.п.'}, {'code': 'work_drain_softrock_1m', 'cat': 'drainage', 'name': 'Монтаж дренажа «Софтрок» (глубина до 1 м)', 'price': 900.0, 'unit': 'м.п.'}, {'code': 'work_drain_storm_combo_1m', 'cat': 'drainage', 'name': 'Монтаж дренажа и ливнёвки в одной траншее (глубина до 1 м)', 'price': 1200.0, 'unit': 'м.п.'}, {'code': 'work_drain_classic_1m', 'cat': 'drainage', 'name': 'Монтаж классического дренажа в щебне (глубина до 1 м)', 'price': 850.0, 'unit': 'м.п.'}, {'code': 'work_drain_sand_rubble_move', 'cat': 'drainage', 'name': 'Перенос песка и щебня под дренаж (до 30 м)', 'price': 1000.0, 'unit': 'м³'}, {'code': 'work_boiler_mount', 'cat': 'plumbing', 'name': 'Монтаж водонагревателя (бойлера)', 'price': 3000.0, 'unit': 'шт.'}, {'code': 'work_boiler_bypass', 'cat': 'plumbing', 'name': 'Сборка байпаса водонагревателя', 'price': 1500.0, 'unit': 'шт.'}, {'code': 'work_water_point', 'cat': 'plumbing', 'name': 'Монтаж точки водоснабжения (ХВС / ГВС)', 'price': 750.0, 'unit': 'точка'}, {'code': 'work_pipe_water_lay', 'cat': 'plumbing', 'name': 'Укладка трубы водопровода внутри дома', 'price': 200.0, 'unit': 'м.п.'}, {'code': 'work_sewer_point_110', 'cat': 'plumbing', 'name': 'Монтаж точки канализации D=110 мм', 'price': 1500.0, 'unit': 'точка'}, {'code': 'work_sewer_point_50', 'cat': 'plumbing', 'name': 'Монтаж точки канализации D=50 мм', 'price': 1000.0, 'unit': 'точка'}, {'code': 'work_toilet_mount', 'cat': 'plumbing', 'name': 'Установка и подключение унитаза', 'price': 1500.0, 'unit': 'шт.'}, {'code': 'work_sink_mount', 'cat': 'plumbing', 'name': 'Установка и подключение раковины / мойки', 'price': 1500.0, 'unit': 'шт.'}, {'code': 'work_shower_cabin', 'cat': 'plumbing', 'name': 'Сборка душевой кабины (стандарт)', 'price': 7000.0, 'unit': 'шт.'}, {'code': 'work_wall_hole_50', 'cat': 'plumbing', 'name': 'Отверстие в стене диаметром до 50 мм', 'price': 2500.0, 'unit': 'шт.'}, {'code': 'work_wall_hole_110', 'cat': 'plumbing', 'name': 'Отверстие в стене диаметром 50–110 мм', 'price': 4000.0, 'unit': 'шт.'}, {'code': 'work_diamond_drilling', 'cat': 'plumbing', 'name': 'Алмазное бурение технологических отверстий', 'price': 15000.0, 'unit': 'усл.'}, {'code': 'work_diagnostic_visit', 'cat': 'plumbing', 'name': 'Выезд специалиста, осмотр и диагностика', 'price': 10000.0, 'unit': 'выезд'}]

ALL_CATALOG_ITEMS = [
    {"code": "kesson_m1", "name": "Кессон Мишка 1 (1050х2000)", "price": PRICES["kesson_m1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "kesson_m2", "name": "Кессон Мишка 2 (1300х2000)", "price": PRICES["kesson_m2"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "adapter_tim_1", "name": "Адаптер 1' TIM со сливным клапаном", "price": PRICES["adapter_tim_1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "hydrant_belamos_1900", "name": "Гидрант незамерзающий GDR 1900 мм Беламос", "price": PRICES["hydrant_belamos_1900"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "hydrant_tim_2200", "name": "Кран незамерзающий 2.2м Гидрант W-HF0122 TIM", "price": PRICES["hydrant_tim_2200"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "vfd_fil10", "name": "Частотный преобразователь FIL-10 2.2kW", "price": PRICES["vfd_fil10"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "tank_100", "name": "Гидроаккумулятор 100VT BELAMOS", "price": PRICES["tank_100"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "tank_80", "name": "Гидроаккумулятор 80VT BELAMOS", "price": PRICES["tank_80"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "pipe_pnd_32", "name": "Труба ПНД 32х3,0 SDR 11 (синяя)", "price": PRICES["pipe_pnd_32"], "unit": "м", "unit_key": "unit_m"},
    {"code": "cable_pvs_3x2_5", "name": "Кабель ПВС 3х2,5 белый гибкий", "price": PRICES["cable_pvs_3x2_5"], "unit": "м", "unit_key": "unit_m"},
    {"code": "rope_3mm_304", "name": "Трос нерж. 3мм AISI 304", "price": PRICES["rope_3mm_304"], "unit": "м", "unit_key": "unit_m"},
    {"code": "check_valve_1", "name": "Обратный клапан 1' Millennium", "price": PRICES["check_valve_1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "valve_watering_1_2", "name": "Кран поливочный 1/2' с носиком", "price": PRICES["valve_watering_1_2"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "valve_brass_1", "name": "Кран шаровой 1' латунь", "price": PRICES["valve_brass_1"], "unit": "шт.", "unit_key": "unit_pcs"},
]

MESSAGES = {
    "ru": {
        "works_type": "🔨 <b>ВЫЕЗД МОНТАЖНОЙ БРИГАДЫ НА ОБЪЕКТ</b>",
        "order_title": "🧾 <b>НОВЫЙ ЗАКАЗ #{order_id} «МИШКА»</b>",
        "client": "👷 <b>Заказчик / Менеджер:</b> {name} {tag}",
        "phone": "📞 <b>Телефон:</b> {phone}",
        "pickup_type": "📦 <b>Самовывоз со склада (п. Некрасовский)</b>",
        "delivery_type": "🚛 <b>ДОСТАВКА НА ОБЪЕКТ</b>",
        "spec_title": "📦 <b>СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ:</b>",
        "total": "💰 <b>ИТОГО К ОПЛАТЕ: {sum} ₽</b>",
        "accepted": "✅ <b>Ваш заказ принят складом! Номер: #{order_id}</b>\n\n{body}\n\n⏳ <i>Мы оповестим вас здесь, как только менеджер укомплектует заказ!</i>",
        "agree_title": "🤝 <b>ВАШ ЗАКАЗ НА РАБОТЫ #{order_id} СОГЛАСОВАН!</b>",
        "agree_body": "👷 Бригада монтажников назначена. Менеджер свяжется с вами для подтверждения даты выезда.\n💰 Сумма к оплате: <b>{sum} ₽</b>\n📍 Адрес объекта: <b>{addr}</b>",
        "collected_title": "🎉 <b>ВАШ ЗАКАЗ #{order_id} ПОЛНОСТЬЮ СОБРАН!</b>",
        "collected_body": "📦 Все комплектующие проверены и готовы к выдаче на складе «МИШКА».\n💰 Сумма к оплате: <b>{sum} ₽</b>\n🚚 Способ получения: <b>{delivery}</b>\n\nЖдём вас на складе!",
        "paid_title": "✅ <b>ЗАКАЗ #{order_id} ОПЛАЧЕН И ВЫДАН!</b>",
        "paid_body": "💰 Оплата успешно проведена: <b>{method}</b>\nСумма: <b>{sum} ₽</b>\n\nБлагодарим за сотрудничество с заводом «МИШКА»!",
        "cancel_msg": "❌ <b>Ваш заказ #{order_id} отменён складом.</b>\nПричина: <i>{reason}</i>",
        "btn_nav_sklad": "📍 Маршрут к складу (Яндекс)",
        "btn_repeat": "🔄 Повторить этот заказ",
        "unit_m": "м",
        "unit_pcs": "шт",
        "unit_set": "компл."
    }
}

def get_admin_name(user_id) -> str:
    try:
        uid = int(str(user_id).strip())
    except (ValueError, TypeError):
        return "Алексей"
    if uid == ADMIN_2:
        return "Артур"
    elif uid == ADMIN_3:
        return "Администратор 3"
    return "Алексей"

def _send_to_sheet_now(payload: dict):
    if not GOOGLE_SHEET_WEBHOOK:
        return
    try:
        requests.post(GOOGLE_SHEET_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"[SHEET SYNC ERR] {e}")

def sync_to_google_sheet(order_id: str, data: dict, total_sum: float, items_list: list = None):
    clean_id = str(order_id).strip()
    if clean_id in REGISTERED_SHEET_ORDERS:
        return
    REGISTERED_SHEET_ORDERS.add(clean_id)

    client_name = data.get("client_name") or data.get("worker_name", "Заказчик")
    company = data.get("company", "").strip()
    full_client_info = f"{client_name} [{company}]" if company else client_name
    tag = data.get("worker_tag", "")
    if tag:
        full_client_info += f" ({tag})"

    items_summary = ", ".join([f"{it['name']} ({it['qty']} {it.get('unit','шт')})" for it in (items_list or [])])

    payload = {
        "action": "create_order",
        "order_id": clean_id,
        "client_name": full_client_info,
        "phone": str(data.get("phone", data.get("client_phone", ""))),
        "items": items_summary or "Оборудование скважины",
        "total_sum": round(total_sum, 2),
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
    if mode == "works":
        items = data.get("items", [])
        clean_works = []
        for it in items:
            q = float(it.get("qty", 0))
            if q > 0:
                clean_works.append({
                    "item_key": it.get("item_key") or it.get("code", ""),
                    "name": it.get("name", "Монтажные работы"),
                    "qty": q,
                    "unit": it.get("unit", "усл."),
                    "price": float(it.get("price", 0))
                })
        return clean_works

    if mode in ["well", "kesson", "адаптер", "скважина"]:
        return get_well_items(data)
    
    return data.get("items", [])

def get_translated_name(item, lang):
    return item["name"]

def get_translated_unit(unit_str, lang):
    return unit_str

def render_order_texts(order_id: str, data: dict, items: list, total_sum: float, lang: str):
    t_client = MESSAGES.get(lang, MESSAGES["ru"])
    admin_lines = []
    client_lines = []

    for it in items:
        subtotal = round(it["qty"] * it["price"], 2)
        qty_str = f"{it['qty']:g}" if isinstance(it["qty"], float) else str(it["qty"])
        u_admin = it.get('unit', 'шт')
        p = it['price']
        admin_lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {u_admin} × {p:,.2f} ₽ = <b>{subtotal:,.2f} ₽</b>")
        client_lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {u_admin} × {p:,.2f} ₽ = <b>{subtotal:,.2f} ₽</b>")

    is_works = (data.get("mode") == "works")
    delivery_type = data.get("delivery_type", "Выезд бригады на объект" if is_works else "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = ("Доставка" in delivery_type) or is_works
    phone = data.get("phone") or data.get("client_phone") or "Не указан"
    raw_name = data.get("client_name") or data.get("worker_name", "Монтажник")
    company = data.get("company", "").strip()
    worker_name = f"{raw_name} [Организация: {company}]" if company else raw_name
    tag = data.get("worker_tag", "")

    if is_works:
        admin_logistics = f"🔨 <b>Тип заказа:</b> 🛠 <b>ВЫЕЗД БРИГАДЫ НА РАБОТЫ</b>\n📍 <b>Адрес объекта:</b> <code>{delivery_info}</code>"
    elif is_delivery:
        admin_logistics = f"🚚 <b>Получение:</b> 🚛 <b>ДОСТАВКА НА ОБЪЕКТ</b>\n📍 <b>Адрес доставки:</b> <code>{delivery_info}</code>"
    else:
        admin_logistics = f"🚚 <b>Получение:</b> 📦 <b>Самовывоз со склада</b>\n🕒 <b>Время приезда:</b> <i>{delivery_info}</i>"

    newline = chr(10)
    admin_spec = newline.join(admin_lines)
    client_spec = newline.join(client_lines)

    admin_header = (
        f"🧾 <b>ЗАКАЗ #{order_id} «МИШКА»</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👷 <b>Заказчик:</b> {worker_name} {tag}\n"
        f"📞 <b>Телефон:</b> <a href='tel:{phone}'>{phone}</a>\n"
        f"{admin_logistics}\n\n"
        f"📦 <b>СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ:</b>\n\n"
        f"{admin_spec}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>ИТОГО К ОПЛАТЕ: {total_sum:,.2f} ₽</b>"
    )

    client_total_str = f"{total_sum:,.2f}"
    client_header = (
        f"{t_client['order_title'].format(order_id=order_id)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t_client['client'].format(name=worker_name, tag=tag)}\n"
        f"{t_client['phone'].format(phone=phone)}\n"
        f"🚚 <b>Способ:</b> {delivery_type}\n\n"
        f"{t_client['spec_title']}\n\n"
        f"{client_spec}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t_client['total'].format(sum=client_total_str)}"
    )

    return admin_header, client_header

def build_order_payload(data: dict):
    order_id = str(uuid.uuid4())[:8]
    items = data.get("items") or get_items_for_order(data)
    lang = data.get("lang", "ru")
    if lang not in MESSAGES:
        lang = "ru"

    total_sum = round(sum(it["qty"] * it["price"] for it in items), 2)
    admin_header, client_header = render_order_texts(order_id, data, items, total_sum, lang)

    is_works = (data.get("mode") == "works")
    delivery_type = data.get("delivery_type", "Выезд бригады на объект" if is_works else "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = ("Доставка" in delivery_type) or is_works

    ACTIVE_ORDERS[order_id] = {
        "client_id": data.get("user_id") or data.get("chat_id"),
        "client_name": data.get("client_name") or data.get("worker_name", "Заказчик"),
        "phone": data.get("phone") or data.get("client_phone", "Не указан"),
        "delivery_type": delivery_type,
        "delivery_info": delivery_info,
        "is_delivery": is_delivery,
        "is_works": is_works,
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
    is_works = bool(order.get("is_works"))

    if order.get("is_delivery") or is_works:
        addr = order.get("delivery_info", "")
        if addr and addr != "-":
            clean_addr = addr.replace("Объект:", "").replace("Адрес:", "").split("|")[0].strip()
            nav_url = f"https://yandex.ru/navi?text={urllib.parse.quote(clean_addr)}"
            nav_title = "🚗 Маршрут к объекту (Яндекс)" if is_works else "🚗 Маршрут доставки (Яндекс)"
            kb.add(types.InlineKeyboardButton(nav_title, url=nav_url))

    if order.get("status") == "cancelled":
        reason = order.get("cancel_reason", "")
        kb.add(types.InlineKeyboardButton(f"❌ ЗАКАЗ ОТМЕНЁН: {reason}", callback_data="none"))
        return kb

    if order.get("status") == "paid":
        method = order.get("payment_method", "Оплачено")
        paid_label = f"✅ РАБОТЫ ОПЛАЧЕНЫ ({method})" if is_works else f"✅ ОПЛАЧЕН И ВЫДАН ({method})"
        kb.add(types.InlineKeyboardButton(paid_label, callback_data="none"))
        return kb

    if order.get("status") == "completed":
        status_label = "🤝 ЗАКАЗ СОГЛАСОВАН С КЛИЕНТОМ" if is_works else "🎉 ЗАКАЗ СОБРАН НА СКЛАДЕ"
        pay_btn_label = "💳 ПРИНЯТЬ ОПЛАТУ ЗА РАБОТЫ" if is_works else "💳 ОПЛАТИТЬ И ВЫДАТЬ ТОВАР"
        kb.add(types.InlineKeyboardButton(status_label, callback_data="none"))
        kb.add(types.InlineKeyboardButton(pay_btn_label, callback_data=f"paymenu_{order_id}"))
        kb.row(
            types.InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_{order_id}"),
            types.InlineKeyboardButton("✏️ Изменить перечень", callback_data=f"editmenu_{order_id}")
        )
        return kb

    if is_works:
        kb.add(types.InlineKeyboardButton("🤝 СОГЛАСОВАТЬ ЗАКАЗ", callback_data=f"agree_{order_id}"))
    else:
        for idx, (item, is_done) in enumerate(zip(order["items"], order["collected"])):
            mark = "🟢" if is_done else "⬜"
            qty_str = f"{item['qty']:g}" if isinstance(item['qty'], float) else str(item['qty'])
            short_name = (item['name'][:22] + "..") if len(item['name']) > 22 else item['name']
            btn_text = f"{mark} {idx+1}. {short_name} ({qty_str} {item.get('unit','шт')})"
            kb.add(types.InlineKeyboardButton(btn_text, callback_data=f"chk_{order_id}_{idx}"))

        all_done = all(order["collected"])
        finish_icon = "🚀" if all_done else "📦"
        kb.add(types.InlineKeyboardButton(f"{finish_icon} ЗАКАЗ ПОЛНОСТЬЮ СОБРАН", callback_data=f"fin_{order_id}"))

    kb.row(
        types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{order_id}"),
        types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"editmenu_{order_id}")
    )

    return kb
