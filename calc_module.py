# -*- coding: utf-8 -*-
import os
import uuid
import urllib.parse
import threading
import requests
from telebot import types

# Администраторы склада «МИШКА»
ADMIN_1 = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
ADMIN_2 = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))
ADMIN_3 = int(os.getenv("THIRD_ADMIN_CHAT_ID", "840231919"))
ADMIN_CHAT_IDS = [ADMIN_1, ADMIN_2, ADMIN_3]

GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()
YANDEX_MAPS_URL = "https://yandex.ru/navi?text=56.047416,37.538633&si=vuyt53qweyhyb7h2vyjb16pg04"

ACTIVE_ORDERS = {}
REGISTERED_SHEET_ORDERS = set()

# ==============================================================================
# ПРАЙС-ЛИСТ СКЛАДА «МИШКА» (СОГЛАСОВАННЫЙ ОТ 09.11.2026)
# ==============================================================================
PRICES = {
    # Кессоны и Адаптер
    "kesson_m1": 41170.00,
    "kesson_m2": 52000.00,
    "kesson_m3": 65000.00,
    "kesson_m4": 82000.00,
    "kesson_long": 58000.00,
    "adapter_tim_1": 3627.31,
    "cover_adapter": 3351.60,
    "well_head_osp": 1916.39,

    # Автоматика и баки
    "vfd_fil10": 7708.80,
    "tank_8bw": 1832.00,
    "tank_50": 5420.00,
    "tank_80": 7150.00,
    "tank_100": 8747.70,
    "tank_150": 13900.00,
    "tank_200": 18200.00,
    "tank_300": 26500.00,
    "pressure_switch": 782.40,
    "manometer": 181.31,

    # Трубы, кабель, трос
    "pipe_ppr_32": 151.42,
    "pipe_pnd_32": 78.00,
    "pipe_pnd_20": 42.54,
    "pipe_pnd_25": 48.46,
    "cable_pvs_3x2_5": 84.89,
    "rope_3mm_304": 19.20,

    # Краны и клапаны
    "valve_ppr_32": 180.93,
    "valve_watering_1_2": 436.13,
    "valve_brass_1": 874.43,
    "check_valve_1": 750.00,

    # Полипропилен
    "ppr_union_32_1": 648.03,
    "ppr_comb_coupling_32_1_hp": 99.88,
    "ppr_elbow_90_32": 48.33,
    "ppr_elbow_45_32": 38.20,
    "ppr_tee_32": 74.70,
    "ppr_plug_32": 37.50,
    "ppr_coupling_32": 29.83,
    "ppr_comb_elbow_32_1_2_bp": 169.35,
    "ppr_comb_elbow_32_1_2_hp": 274.83,
    "ppr_trans_tee_32_1_2_bp": 174.15,
    "ppr_trans_tee_32_1_bp": 190.46,
    "ppr_trans_tee_32_1_hp": 305.00,

    # Фитинги Unidelta ПНД
    "pnd_coupling_32_1_hp": 263.84,
    "pnd_elbow_32_1_hp": 319.60,
    "pnd_coupling_32_32": 472.60,
    "pnd_reduct_32_20": 435.20,

    # Латунь и подводки
    "hose_giant_1_80cm": 761.93,
    "hose_straight_1_2_60cm": 160.00,
    "brass_tee_1_bbb": 640.17,
    "brass_tee_1_2_bbb": 192.42,
    "brass_nipple_1": 196.76,
    "brass_nipple_1_2": 70.88,
    "brass_nipple_1_2_1_4": 70.88,
    "brass_nipple_1_2_3_8": 66.54,
    "brass_bushing_1_2_1_4": 75.23,
    "cable_clamp_4mm": 40.80,
    "plug_16a": 64.42,

    # Септики
    "septic_bio3": 85000.00,
    "septic_bio5": 105000.00,
    "septic_bio8": 138000.00,
    "septic_bio10": 165000.00,
    "septic_tank2": 62000.00,
    "septic_tank3": 82000.00,
    "drain_pump": 8500.00,
    "drain_hose": 250.00,
    "pipe110": 480.00,
    "insul110": 140.00,
    "elbow110_45": 280.00,
    "tee110": 490.00,
    "bacteria": 1200.00,
    "cable_heat_septic": 380.00,

    # Дренаж и ливневка
    "drain_pipe_classic": 280.00,
    "drain_softrock": 750.00,
    "geotextile_roll": 4500.00,
    "well_drain_315": 3800.00,
    "well_drain_coupling": 350.00,
    "well_cone": 1800.00,
    "softrock_coupling": 420.00,
    "storm_inlet_box": 1950.00,
    "storm_pipe110": 480.00,
    "storm_well_315": 3800.00,
    "sand_trap": 2400.00,
    "leaf_grate": 350.00,
    "storm_back_valve": 2900.00
}

KESSON_MODELS = {
    "kesson_m1": {"name": "Кессон Мишка 1 (муфта 125/133) 1050x2000", "price": PRICES["kesson_m1"]},
    "kesson_m2": {"name": "Кессон Мишка 2 (муфта 125/133) 1300x2000", "price": PRICES["kesson_m2"]},
    "kesson_m3": {"name": "Кессон Мишка 3 (муфта 125/133) 1600x2000", "price": PRICES["kesson_m3"]},
    "kesson_m4": {"name": "Кессон Мишка 4 (муфта 125/133) 2000x2000", "price": PRICES["kesson_m4"]},
    "kesson_long": {"name": "Кессон Мишка LONG (муфта 125/133) H=2500", "price": PRICES["kesson_long"]},
}

TANK_CATALOG = {
    "tank_50": {"name": "Гидроаккумулятор 50VT BELAMOS", "price": PRICES["tank_50"]},
    "tank_80": {"name": "Гидроаккумулятор 80VT BELAMOS", "price": PRICES["tank_80"]},
    "tank_100": {"name": "Гидроаккумулятор 100VT BELAMOS", "price": PRICES["tank_100"]},
    "tank_150": {"name": "Гидроаккумулятор 150VT BELAMOS", "price": PRICES["tank_150"]},
    "tank_200": {"name": "Гидроаккумулятор 200VT BELAMOS", "price": PRICES["tank_200"]},
    "tank_300": {"name": "Гидроаккумулятор 300VT BELAMOS", "price": PRICES["tank_300"]},
}

ALL_CATALOG_ITEMS = [
    {"code": "kesson_m1", "name": "Кессон Мишка 1 (1050х2000)", "price": PRICES["kesson_m1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "kesson_m2", "name": "Кессон Мишка 2 (1300х2000)", "price": PRICES["kesson_m2"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "adapter_tim_1", "name": "Адаптер 1' TIM со сливным клапаном", "price": PRICES["adapter_tim_1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "vfd_fil10", "name": "Частотный преобразователь FIL-10 2.2kW", "price": PRICES["vfd_fil10"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "tank_100", "name": "Гидроаккумулятор 100VT BELAMOS", "price": PRICES["tank_100"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "tank_80", "name": "Гидроаккумулятор 80VT BELAMOS", "price": PRICES["tank_80"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "pipe_pnd_32", "name": "Труба ПНД 32х3,0 SDR 11 (синяя)", "price": PRICES["pipe_pnd_32"], "unit": "м", "unit_key": "unit_m"},
    {"code": "cable_pvs_3x2_5", "name": "Кабель ПВС 3х2,5 белый гибкий", "price": PRICES["cable_pvs_3x2_5"], "unit": "м", "unit_key": "unit_m"},
    {"code": "rope_3mm_304", "name": "Трос нерж. 3мм AISI 304", "price": PRICES["rope_3mm_304"], "unit": "м", "unit_key": "unit_m"},
    {"code": "check_valve_1", "name": "Обратный клапан 1' Millennium", "price": PRICES["check_valve_1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "valve_watering_1_2", "name": "Кран поливочный 1/2' с носиком", "price": PRICES["valve_watering_1_2"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "valve_brass_1", "name": "Кран шаровой 1' латунь", "price": PRICES["valve_brass_1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "septic_bio5", "name": "Станция «МИШКА-Био 5»", "price": PRICES["septic_bio5"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "pipe110", "name": "Труба рыжая 110х3.2 наружная", "price": PRICES["pipe110"], "unit": "м", "unit_key": "unit_m"},
    {"code": "bacteria", "name": "Бактерии для септика (старт)", "price": PRICES["bacteria"], "unit": "шт.", "unit_key": "unit_pcs"},
]

# Мультиязычные шаблоны (RU, TJ, UZ, HY, KY)
MESSAGES = {
    "ru": {
        "order_title": "🧾 <b>НОВЫЙ ЗАКАЗ #{order_id} «МИШКА»</b>",
        "client": "👷 <b>Заказчик / Менеджер:</b> {name} {tag}",
        "phone": "📞 <b>Телефон:</b> {phone}",
        "pickup_type": "📦 <b>Самовывоз со склада (п. Некрасовский)</b>",
        "delivery_type": "🚛 <b>ДОСТАВКА НА ОБЪЕКТ</b>",
        "spec_title": "📦 <b>СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ:</b>",
        "total": "💰 <b>ИТОГО К ОПЛАТЕ: {sum} ₽</b>",
        "accepted": "✅ <b>Ваш заказ принят складом! Номер: #{order_id}</b>\n\n{body}\n\n⏳ <i>Мы оповестим вас здесь, как только менеджер укомплектует заказ!</i>",
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
    },
    "tj": {
        "order_title": "🧾 <b>ФАРМОИШИ НАВ #{order_id} «МИШКА»</b>",
        "client": "👷 <b>Мизоҷ:</b> {name} {tag}",
        "phone": "📞 <b>Телефон:</b> {phone}",
        "pickup_type": "📦 <b>Худам аз анбор мегирам (Некрасовский)</b>",
        "delivery_type": "🚛 <b>БУРДАН БА СУРОҒАИ МАНЗИЛ</b>",
        "spec_title": "📦 <b>РӮЙХАТИ ТАҶҲИЗОТ:</b>",
        "total": "💰 <b>ҲАМАГӢ БАРОИ ПАРДОХТ: {sum} ₽</b>",
        "accepted": "✅ <b>Фармоиши шумо қабул шуд! Рақам: #{order_id}</b>\n\n{body}\n\n⏳ <i>Ҳамин ки бор дар анбор омода шуд, мо хабар медиҳем!</i>",
        "collected_title": "🎉 <b>ФАРМОИШИ ШУМО #{order_id} ПУРРА ОМОДА ШУД!</b>",
        "collected_body": "📦 Бор дар анбори «МИШКА» санҷида шуд ва тайёр аст.\n💰 Маблағ: <b>{sum} ₽</b>\n🚚 Тарзи гирифтан: <b>{delivery}</b>",
        "paid_title": "✅ <b>ФАРМОИШ #{order_id} СУПОРИДА ШУД!</b>",
        "paid_body": "💰 Пардохт қабул шуд: <b>{method}</b>\nМаблағ: <b>{sum} ₽</b>",
        "cancel_msg": "❌ <b>Фармоиши шумо #{order_id} бекор карда шуд.</b>\nСабаб: <i>{reason}</i>",
        "btn_nav_sklad": "📍 Харитаи роҳ ба анбор (Яндекс)",
        "btn_repeat": "🔄 Ин фармоишро такрор кардан",
        "unit_m": "м",
        "unit_pcs": "дона",
        "unit_set": "маҷм."
    },
    "uz": {
        "order_title": "🧾 <b>YANGI BUYURTMA #{order_id} «MISHKA»</b>",
        "client": "👷 <b>Buyurtmachi:</b> {name} {tag}",
        "phone": "📞 <b>Telefon:</b> {phone}",
        "pickup_type": "📦 <b>Ombordan olib ketish (Nekrasovskiy)</b>",
        "delivery_type": "🚛 <b>OBYEKTGA YETKAZIB BERISH</b>",
        "spec_title": "📦 <b>MAHSULOTLAR RO'YXATI:</b>",
        "total": "💰 <b>TO'LOV UCHUN JAMI: {sum} ₽</b>",
        "accepted": "✅ <b>Buyurtmangiz qabul qilindi! Raqam: #{order_id}</b>\n\n{body}\n\n⏳ <i>Omborda buyurtma tayyor bo'lishi bilan xabar beramiz!</i>",
        "collected_title": "🎉 <b>BUYURTMANGIZ #{order_id} TO'LIQ TAYYOR!</b>",
        "collected_body": "📦 Barcha uskunalar «MISHKA» omborida tayyor.\n💰 Summa: <b>{sum} ₽</b>\n🚚 Usul: <b>{delivery}</b>",
        "paid_title": "✅ <b>BUYURTMA #{order_id} TO'LANDI VA TOPSHIRILDI!</b>",
        "paid_body": "💰 To'lov: <b>{method}</b>\nSumma: <b>{sum} ₽</b>",
        "cancel_msg": "❌ <b>Buyurtmangiz #{order_id} bekor qilindi.</b>\nSababi: <i>{reason}</i>",
        "btn_nav_sklad": "📍 Omborga yo'nalish (Yandeks)",
        "btn_repeat": "🔄 Ushbu buyurtmani takrorlash",
        "unit_m": "m",
        "unit_pcs": "dona",
        "unit_set": "to'plam"
    },
    "hy": {
        "order_title": "🧾 <b>ՆՈՐ ՊԱՏՎԵՐ #{order_id} «ՄԻՇԿԱ»</b>",
        "client": "👷 <b>Հաճախորդ:</b> {name} {tag}",
        "phone": "📞 <b>Հեռախոս:</b> {phone}",
        "pickup_type": "📦 <b>Ինքնուրույն պահեստից (Նեկրասովսկի)</b>",
        "delivery_type": "🚛 <b>ԱՌԱՔՈՒՄ ՕԲՅԵԿՏ</b>",
        "spec_title": "📦 <b>ԱՊՐԱՆՔԱՑՈՒՑԱԿ:</b>",
        "total": "💰 <b>ԸՆԴԱՄԵՆԸ ՎՃԱՐՄԱՆ: {sum} ₽</b>",
        "accepted": "✅ <b>Ձեր պատվերն ընդունված է: Համար: #{order_id}</b>\n\n{body}\n\n⏳ <i>Մենք կտեղեկացնենք Ձեզ, երբ պատվերը պատրաստ լինի:</i>",
        "collected_title": "🎉 <b>ՁԵՐ ՊԱՏՎԵՐԸ #{order_id} ՀԱՎԱՔՎԱԾ Է:</b>",
        "collected_body": "📦 Բոլոր ապրանքները պատրաստ են «ՄԻՇԿԱ» պահեստում:\n💰 Գումար: <b>{sum} ₽</b>\n🚚 Ստացում: <b>{delivery}</b>",
        "paid_title": "✅ <b>ՊԱՏՎԵՐ #{order_id} ՎՃԱՐՎԱԾ Է:</b>",
        "paid_body": "💰 Վճարում: <b>{method}</b>\nԳումար: <b>{sum} ₽</b>",
        "cancel_msg": "❌ <b>Ձեր պատվերը #{order_id} չեղարկվել է:</b>\nՊատճառ: <i>{reason}</i>",
        "btn_nav_sklad": "📍 Ճանապարհ դեպի պահեստ (Yandex)",
        "btn_repeat": "🔄 Կրկնել պատվերը",
        "unit_m": "մ",
        "unit_pcs": "հատ",
        "unit_set": "հավաք."
    },
    "ky": {
        "order_title": "🧾 <b>ЖАҢЫ ЗАКАЗ #{order_id} «МИШКА»</b>",
        "client": "👷 <b>Кардар:</b> {name} {tag}",
        "phone": "📞 <b>Телефон:</b> {phone}",
        "pickup_type": "📦 <b>Кампадан өзү алып кетүү (Некрасовский)</b>",
        "delivery_type": "🚛 <b>ОБЪЕКТКЕ ЖЕТКИРҮҮ</b>",
        "spec_title": "📦 <b>СПЕЦИФИКАЦИЯ:</b>",
        "total": "💰 <b>ТӨЛӨМ ҮЧҮН ЖАЛПЫ: {sum} ₽</b>",
        "accepted": "✅ <b>Заказыңыз кабыл алынды! Номери: #{order_id}</b>\n\n{body}\n\n⏳ <i>Кампада жүк топтолору менен кабар беребиз!</i>",
        "collected_title": "🎉 <b>СИЗДИН ЗАКАЗ #{order_id} ТОПТОЛДУ!</b>",
        "collected_body": "📦 Жабдуулар «МИШКА» кампасында даяр.\n💰 Сумма: <b>{sum} ₽</b>\n🚚 Алуу: <b>{delivery}</b>",
        "paid_title": "✅ <b>ЗАКАЗ #{order_id} ТӨЛӨНДҮ ЖАНА БЕРИЛДИ!</b>",
        "paid_body": "💰 Төлөм: <b>{method}</b>\nСумма: <b>{sum} ₽</b>",
        "cancel_msg": "❌ <b>Сиздин буйрутмаңыз #{order_id} жокко чыгарылды.</b>\nСебеби: <i>{reason}</i>",
        "btn_nav_sklad": "📍 Кампага баруучу жол (Яндекс)",
        "btn_repeat": "🔄 Бул заказды кайталоо",
        "unit_m": "м",
        "unit_pcs": "даана",
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

    if mode in ["well", "kesson", "адаптер", "скважина"]:
        depth = float(data.get("depth", 40))
        distances = data.get("distances", [15])
        distance = float(distances[0]) if distances else float(data.get("distance", 15))
        
        equip_type = data.get("equip_type", "kesson_vfd")
        chosen_kesson_key = data.get("chosen_kesson", "kesson_m1")
        chosen_tank_key = str(data.get("chosen_tank", "tank_100"))

        kesson_obj = KESSON_MODELS.get(chosen_kesson_key, KESSON_MODELS["kesson_m1"])
        tank_obj = TANK_CATALOG.get(chosen_tank_key, TANK_CATALOG["tank_100"])

        items = []

        if equip_type == "adapter":
            items.extend([
                {"name": "Адаптер скважинный со сливным клапаном 1' TIM", "qty": 1, "unit": "шт", "price": PRICES["adapter_tim_1"]},
                {"name": "Крышка скважины Джилекс КС 110-133", "qty": 1, "unit": "шт", "price": PRICES["cover_adapter"]},
                {"name": "Муфта ПНД 32x1' HP Unidelta", "qty": 4, "unit": "шт", "price": PRICES["pnd_coupling_32_1_hp"]},
                {"name": f"{tank_obj['name']} (в дом)", "qty": 1, "unit": "шт", "price": tank_obj["price"]},
                {"name": "Реле давления AQUARIO PS-5-2 (вращ. гайка) Акварио", "qty": 1, "unit": "шт", "price": PRICES["pressure_switch"]},
                {"name": "Манометр радиальный 0-10 бар D53мм 1/4", "qty": 1, "unit": "шт", "price": PRICES["manometer"]},
                {"name": "Подводка для воды угловая 1' 80см г/г ГИГАНТ", "qty": 1, "unit": "шт", "price": PRICES["hose_giant_1_80cm"]},
                {"name": "Кран шаровой Вн/Нр (бабочка) 1'", "qty": 1, "unit": "шт", "price": PRICES["valve_brass_1"]},
                {"name": "Тройник для труб с внутренней резьбой ВВВ 1' латунь Millenium", "qty": 1, "unit": "шт", "price": PRICES["brass_tee_1_bbb"]},
                {"name": "Тройник ВВВ 1/2' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_tee_1_2_bbb"]},
                {"name": "Ниппель НН 1' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_nipple_1"]},
                {"name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_bushing_1_2_1_4"]},
                {"name": "Ниппель НН 1/2' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_nipple_1_2"]},
                {"name": "Ниппель перех. НН 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_nipple_1_2_1_4"]},
            ])
        elif equip_type == "kesson_vfd":
            items.extend([
                {"name": kesson_obj["name"], "qty": 1, "unit": "шт", "price": kesson_obj["price"]},
                {"name": "Труба полипропиленовая 32х5,4мм PN20 (белая)", "qty": 4, "unit": "м", "price": PRICES["pipe_ppr_32"]},
                {"name": "Отвод 90 PP-R Millennium 32мм (белый)", "qty": 4, "unit": "шт", "price": PRICES["ppr_elbow_90_32"]},
                {"name": "Отвод 45 PP-R Millennium 32мм (белый)", "qty": 4, "unit": "шт", "price": PRICES["ppr_elbow_45_32"]},
                {"name": "Заглушка PP-R Millennium 32мм (белая)", "qty": 3, "unit": "шт", "price": PRICES["ppr_plug_32"]},
                {"name": "Кран шаровой PP-R VALFEX OPTIMA 32мм (белый)", "qty": 4, "unit": "шт", "price": PRICES["valve_ppr_32"]},
                {"name": "Кран шаровый VALFEX 1/2' с носиком под шланг", "qty": 1, "unit": "шт", "price": PRICES["valve_watering_1_2"]},
                {"name": "Муфта разъемная PP-R 32-1' ВР (американка)", "qty": 4, "unit": "шт", "price": PRICES["ppr_union_32_1"]},
                {"name": "Муфта комб. PP-R 32-1' HP неразъемная", "qty": 4, "unit": "шт", "price": PRICES["ppr_comb_coupling_32_1_hp"]},
                {"name": "Тройник PP-R Millennium 32мм (белый)", "qty": 3, "unit": "шт", "price": PRICES["ppr_tee_32"]},
                {"name": "Муфта PP-R Millennium 32мм (белая)", "qty": 1, "unit": "шт", "price": PRICES["ppr_coupling_32"]},
                {"name": "Отвод комб. с внутренней резьбой 90 PP-R 32-1/2'", "qty": 1, "unit": "шт", "price": PRICES["ppr_comb_elbow_32_1_2_bp"]},
                {"name": "Отвод комб. с наружной резьбой 90 PP-R 32-1/2'", "qty": 1, "unit": "шт", "price": PRICES["ppr_comb_elbow_32_1_2_hp"]},
                {"name": "Подводка для воды прямая 1/2' 60см г/г", "qty": 1, "unit": "шт", "price": PRICES["hose_straight_1_2_60cm"]},
                {"name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_bushing_1_2_1_4"]},
                {"name": "Частотный преобразователь FIL-10 2.2KW 220V", "qty": 1, "unit": "шт", "price": PRICES["vfd_fil10"]},
                {"name": "Гидроаккумулятор BELAMOS 8BW синий (подвесной)", "qty": 1, "unit": "шт", "price": PRICES["tank_8bw"]},
                {"name": "Тройник переходной комб. ВР PP-R 32x1/2'x32", "qty": 1, "unit": "шт", "price": PRICES["ppr_trans_tee_32_1_2_bp"]},
                {"name": "Тройник переходной комб. ВР PP-R 32x1'x32", "qty": 1, "unit": "шт", "price": PRICES["ppr_trans_tee_32_1_bp"]},
            ])
        else:
            items.extend([
                {"name": kesson_obj["name"], "qty": 1, "unit": "шт", "price": kesson_obj["price"]},
                {"name": "Труба полипропиленовая 32х5,4мм PN20 (белая)", "qty": 4, "unit": "м", "price": PRICES["pipe_ppr_32"]},
                {"name": tank_obj["name"], "qty": 1, "unit": "шт", "price": tank_obj["price"]},
                {"name": "Отвод 90 PP-R Millennium 32мм (белый)", "qty": 4, "unit": "шт", "price": PRICES["ppr_elbow_90_32"]},
                {"name": "Отвод 45 PP-R Millennium 32мм (белый)", "qty": 4, "unit": "шт", "price": PRICES["ppr_elbow_45_32"]},
                {"name": "Заглушка PP-R Millennium 32мм (белая)", "qty": 3, "unit": "шт", "price": PRICES["ppr_plug_32"]},
                {"name": "Кран шаровой PP-R VALFEX OPTIMA 32мм", "qty": 4, "unit": "шт", "price": PRICES["valve_ppr_32"]},
                {"name": "Кран шаровый VALFEX 1/2' с носиком под шланг", "qty": 1, "unit": "шт", "price": PRICES["valve_watering_1_2"]},
                {"name": "Муфта разъемная PP-R 32-1' ВР (американка)", "qty": 4, "unit": "шт", "price": PRICES["ppr_union_32_1"]},
                {"name": "Муфта комб. PP-R 32-1' HP неразъемная", "qty": 4, "unit": "шт", "price": PRICES["ppr_comb_coupling_32_1_hp"]},
                {"name": "Тройник переходной комб. HP PP-R 32x1'x32", "qty": 1, "unit": "шт", "price": PRICES["ppr_trans_tee_32_1_hp"]},
                {"name": "Тройник PP-R Millennium 32мм (белый)", "qty": 3, "unit": "шт", "price": PRICES["ppr_tee_32"]},
                {"name": "Муфта PP-R Millennium 32мм (белая)", "qty": 1, "unit": "шт", "price": PRICES["ppr_coupling_32"]},
                {"name": "Отвод комб. ВР 90 PP-R 32-1/2'", "qty": 1, "unit": "шт", "price": PRICES["ppr_comb_elbow_32_1_2_bp"]},
                {"name": "Отвод комб. HP 90 PP-R 32-1/2'", "qty": 1, "unit": "шт", "price": PRICES["ppr_comb_elbow_32_1_2_hp"]},
                {"name": "Подводка для воды угловая 1' 80см г/г ГИГАНТ", "qty": 1, "unit": "шт", "price": PRICES["hose_giant_1_80cm"]},
                {"name": "Подводка для воды прямая 1/2' 60см г/г", "qty": 1, "unit": "шт", "price": PRICES["hose_straight_1_2_60cm"]},
                {"name": "Реле давления AQUARIO PS-5-2 (вращ. гайка)", "qty": 1, "unit": "шт", "price": PRICES["pressure_switch"]},
                {"name": "Манометр радиальный 0-10 бар D53мм 1/4", "qty": 1, "unit": "шт", "price": PRICES["manometer"]},
                {"name": "Тройник ВВВ 1/2' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_tee_1_2_bbb"]},
                {"name": "Ниппель переходной НН 1/2'x3/8' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_nipple_1_2_3_8"]},
                {"name": "Ниппель перех. НН 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_nipple_1_2_1_4"]},
                {"name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_bushing_1_2_1_4"]},
                {"name": "Ниппель НН 1/2' (латунь)", "qty": 1, "unit": "шт", "price": PRICES["brass_nipple_1_2"]},
            ])

        if equip_type != "adapter":
            items.extend([
                {"name": "Обратный клапан 1' Millennium с металл. седлом", "qty": 1, "unit": "шт", "price": PRICES["check_valve_1"]},
                {"name": "Муфта ПНД 32х1' HP Unidelta", "qty": 1, "unit": "шт", "price": PRICES["pnd_coupling_32_1_hp"]},
                {"name": "Оголовок для скважины Джилекс ОСП 110-133/32", "qty": 1, "unit": "шт", "price": PRICES["well_head_osp"]},
                {"name": "Угол ПНД 32x1' HP Unidelta", "qty": 1, "unit": "шт", "price": PRICES["pnd_elbow_32_1_hp"]},
                {"name": "Зажим для троса AISI 316 4мм", "qty": 4, "unit": "шт", "price": PRICES["cable_clamp_4mm"]},
                {"name": "Вилка электрическая 16A 250B", "qty": 1, "unit": "шт", "price": PRICES["plug_16a"]},
            ])
        else:
            items.extend([
                {"name": "Обратный клапан 1' Millennium с металл. седлом", "qty": 1, "unit": "шт", "price": PRICES["check_valve_1"]},
                {"name": "Зажим для троса AISI 316 4мм", "qty": 4, "unit": "шт", "price": PRICES["cable_clamp_4mm"]},
            ])

        pump_h = int(depth)
        items.extend([
            {"name": "Трос нержавеющая сталь 3мм AISI 304", "qty": pump_h, "unit": "м", "price": PRICES["rope_3mm_304"]},
            {"name": "Труба ПНД 32х3,0 SDR 11 синяя", "qty": pump_h, "unit": "м", "price": PRICES["pipe_pnd_32"]},
        ])

        dist_m = int(distance)
        items.extend([
            {"name": "Муфта ПНД 32x32 Unidelta", "qty": 1, "unit": "шт", "price": PRICES["pnd_coupling_32_32"]},
            {"name": "Муфта ПНД редукц. 32х20 Unidelta", "qty": 1, "unit": "шт", "price": PRICES["pnd_reduct_32_20"]},
            {"name": "Муфта ПНД 32х1' HP Unidelta", "qty": 1, "unit": "шт", "price": PRICES["pnd_coupling_32_1_hp"]},
            {"name": "Кран шаровой Вн/Нр (бабочка) 1'", "qty": 1, "unit": "шт", "price": PRICES["valve_brass_1"]},
            {"name": "Труба ПНД 32х3,0 SDR 11 синяя", "qty": dist_m, "unit": "м", "price": PRICES["pipe_pnd_32"]},
            {"name": "Труба ПНД 20x2,0 SDR 11 (под кабель)", "qty": dist_m, "unit": "м", "price": PRICES["pipe_pnd_20"]},
            {"name": "Кабель ПВС 3х2,5 белый гибкий", "qty": dist_m, "unit": "м", "price": PRICES["cable_pvs_3x2_5"]},
        ])
        return items

    elif mode == "septic":
        dist = data.get("distance", 10)
        discharge = data.get("discharge", "gravity")
        chosen = data.get("chosen_septic", "auto")

        s_n, s_p = "Станция «МИШКА-Био 5»", PRICES["septic_bio5"]
        if "Био 3" in chosen: s_n, s_p = "Станция «МИШКА-Био 3»", PRICES["septic_bio3"]
        elif "Био 8" in chosen: s_n, s_p = "Станция «МИШКА-Био 8»", PRICES["septic_bio8"]

        pipe_m = int(dist * 1.05)
        items = [
            {"name": s_n, "qty": 1, "unit": "шт", "price": s_p},
            {"name": "Труба ПВХ рыжая наружная 110х3.2", "qty": pipe_m, "unit": "м", "price": PRICES["pipe110"]},
            {"name": "Утеплитель для трубы 110", "qty": pipe_m, "unit": "м", "price": PRICES["insul110"]},
            {"name": "Отводы 110х45° рыжие", "qty": max(2, int(dist // 6) + 1), "unit": "шт", "price": PRICES["elbow110_45"]},
            {"name": "Тройник ревизионный 110 с заглушкой", "qty": 1, "unit": "шт", "price": PRICES["tee110"]},
            {"name": "Бактерии для быстрого запуска", "qty": 1, "unit": "компл.", "price": PRICES["bacteria"]}
        ]
        if discharge == "forced":
            items.extend([
                {"name": "Насос дренажный с поплавком", "qty": 1, "unit": "шт", "price": PRICES["drain_pump"]},
                {"name": "Шланг напорный армированный 32", "qty": 10, "unit": "м", "price": PRICES["drain_hose"]},
                {"name": "Кабель греющий для слива", "qty": 5, "unit": "м", "price": PRICES["cable_heat_septic"]}
            ])
        return items

    elif mode == "drainage":
        dtype = data.get("drain_type", "softrock")
        length = data.get("drain_length", 50)
        wells = data.get("drain_wells", 3)
        if dtype == "softrock":
            items = [
                {"name": "Блоки «Софтрок/Лайтдрок» 110 (L=3м)", "qty": length, "unit": "м", "price": PRICES["drain_softrock"]},
                {"name": "Соединительные муфты Софтрок", "qty": int(length // 3) + 1, "unit": "шт", "price": PRICES["softrock_coupling"]}
            ]
        else:
            items = [
                {"name": "Труба дренажная 110 с фильтром", "qty": length, "unit": "м", "price": PRICES["drain_pipe_classic"]},
                {"name": "Геотекстиль Дорнит (рулон 2х50м)", "qty": max(1, int(length // 45) + 1), "unit": "рул", "price": PRICES["geotextile_roll"]}
            ]
        items.extend([
            {"name": "Колодец смотровой d315 + люк + дно", "qty": wells, "unit": "шт", "price": PRICES["well_drain_315"]},
            {"name": "Муфты врезки 110 в колодец 315", "qty": wells * 2, "unit": "шт", "price": PRICES["well_drain_coupling"]}
        ])
        return items

    elif mode == "storm":
        inlets = data.get("storm_inlets", 4)
        length = data.get("storm_length", 30)
        wells = data.get("storm_wells", 2)
        items = [
            {"name": "Дождеприёмник 300х300 с корзиной и решёткой", "qty": inlets, "unit": "шт", "price": PRICES["storm_inlet_box"]},
            {"name": "Труба ПВХ рыжая 110х3.2 наружная", "qty": int(length * 1.05), "unit": "м", "price": PRICES["storm_pipe110"]},
            {"name": "Отводы 110х45° рыжие", "qty": inlets * 2 + wells * 2, "unit": "шт", "price": PRICES["elbow110_45"]},
            {"name": "Тройники 110х110х87° рыжие", "qty": max(1, inlets - 1), "unit": "шт", "price": PRICES["tee110"]},
            {"name": "Колодец поворотный d315 с люком", "qty": wells, "unit": "шт", "price": PRICES["storm_well_315"]}
        ]
        return items

    return data.get("items", [])

def render_order_texts(order_id: str, data: dict, items: list, total_sum: float, lang: str):
    t_client = MESSAGES.get(lang, MESSAGES["ru"])
    admin_lines = []
    client_lines = []

    for it in items:
        subtotal = round(it["qty"] * it["price"], 2)
        qty_str = f"{it['qty']:g}" if isinstance(it["qty"], float) else str(it["qty"])
        u = it.get('unit', 'шт')
        p = it['price']
        admin_lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {u} × {p:,.2f} ₽ = <b>{subtotal:,.2f} ₽</b>")
        client_lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {u} × {p:,.2f} ₽ = <b>{subtotal:,.2f} ₽</b>")

    delivery_type = data.get("delivery_type", "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = "Доставка" in delivery_type
    phone = data.get("phone") or data.get("client_phone") or "Не указан"
    raw_name = data.get("client_name") or data.get("worker_name", "Монтажник")
    company = data.get("company", "").strip()
    worker_name = f"{raw_name} [Организация: {company}]" if company else raw_name
    tag = data.get("worker_tag", "")

    if is_delivery:
        admin_logistics = f"🚚 <b>Получение:</b> 🚛 <b>ДОСТАВКА НА ОБЪЕКТ</b>\n📍 <b>Адрес доставки:</b> <code>{delivery_info}</code>"
        client_logistics = f"{t_client['delivery_type']}\n📍 {delivery_info}"
    else:
        admin_logistics = f"🚚 <b>Получение:</b> 📦 <b>Самовывоз со склада</b>\n🕒 <b>Время приезда:</b> <i>{delivery_info}</i>"
        client_logistics = f"{t_client['pickup_type']}\n🕒 {delivery_info}"

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
        f"🚚 <b>Способ:</b> {client_logistics}\n\n"
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

    delivery_type = data.get("delivery_type", "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = "Доставка" in delivery_type

    ACTIVE_ORDERS[order_id] = {
        "client_id": data.get("user_id") or data.get("chat_id"),
        "client_name": data.get("client_name") or data.get("worker_name", "Заказчик"),
        "phone": data.get("phone") or data.get("client_phone", "Не указан"),
        "delivery_type": delivery_type,
        "delivery_info": delivery_info,
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
        addr = order.get("delivery_info", "")
        if addr and addr != "-":
            nav_url = f"https://yandex.ru/navi?text={urllib.parse.quote(addr)}"
            kb.add(types.InlineKeyboardButton("🚗 Маршрут доставки к клиенту (Яндекс)", url=nav_url))

    if order.get("status") == "cancelled":
        reason = order.get("cancel_reason", "")
        kb.add(types.InlineKeyboardButton(f"❌ ЗАКАЗ ОТМЕНЁН: {reason}", callback_data="none"))
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
