import os
import uuid
import urllib.parse
import requests
from telebot import types

PRIMARY_ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
SECOND_ADMIN_ID = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))
ADMIN_CHAT_IDS = [PRIMARY_ADMIN_ID, SECOND_ADMIN_ID]

GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()

# Хранилище заказов: order_id -> dict
ACTIVE_ORDERS = {}

# Прайс-лист оборудования завода МИШКА (руб.)
PRICES = {
    # 1. Скважина и кессон
    "pnd32": 130,
    "pnd25": 95,
    "cable": 220,
    "rope": 90,
    "insul": 60,
    "heat_cable": 350,
    "ball_valve": 1250,
    "fitting_32_1": 420,
    "elbow_32": 480,
    "unipak": 650,
    "check_valve": 1450,
    "nipple": 380,
    "rope_clips": 120,
    "rope_thimble": 90,
    "carabiner": 250,
    "cable_sleeve": 950,
    "cable_ties": 5,
    "well_head": 4200,
    "wall_seal": 850,
    "pressure_switch": 2800,
    "manometer": 650,
    "five_way": 1650,
    "filter_bb": 4500,
    "garden_tap": 1100,

    # Кессоны МИШКА
    "kesson_m1": 39650,
    "kesson_m2": 50700,
    "kesson_m3": 76500,
    "kesson_m4": 156000,
    "kesson_long": 65000,
    "pump_60": 26500,
    "pump_85": 32000,
    "pump_110": 39500,
    "pump_120": 48000,
    "tank_80": 9800,
    "tank_150": 17500,
    "tank_200": 24000,

    # 2. Септики и канализация
    "septic_bio3": 85000,
    "septic_bio5": 105000,
    "septic_bio8": 138000,
    "septic_bio10": 165000,
    "septic_tank2": 62000,
    "septic_tank3": 82000,
    "drain_pump": 8500,
    "drain_hose": 250,
    "pipe110": 480,
    "insul110": 140,
    "elbow110_45": 280,
    "tee110": 490,
    "bacteria": 1200,
    "cable_heat_septic": 380,

    # 3. Дренаж участка
    "drain_pipe_classic": 280,
    "drain_softrock": 750,
    "geotextile_roll": 4500,
    "well_drain_315": 3800,
    "well_drain_coupling": 350,
    "well_cone": 1800,
    "softrock_coupling": 420,

    # 4. Подземная ливнёвка
    "storm_inlet_box": 1950,
    "storm_pipe110": 480,
    "storm_well_315": 3800,
    "sand_trap": 2400,
    "leaf_grate": 350,
    "storm_back_valve": 2900
}

EXTRA_ITEMS = {
    "pnd32": {"unit": "м", "name": "Труба ПНД 32 SDR11", "price": PRICES["pnd32"]},
    "pnd25": {"unit": "м", "name": "Труба ПНД 25 (полив)", "price": PRICES["pnd25"]},
    "insul": {"unit": "м", "name": "Утеплитель Энергофлекс 32", "price": PRICES["insul"]},
    "heat_cable": {"unit": "м", "name": "Кабель греющий саморег.", "price": PRICES["heat_cable"]},
    "ball_valve": {"unit": "шт.", "name": "Кран 1\" с американкой", "price": PRICES["ball_valve"]},
    "fitting_32_1": {"unit": "шт.", "name": "Муфта ПНД 32х1\" НР", "price": PRICES["fitting_32_1"]},
    "elbow_32": {"unit": "шт.", "name": "Уголок ПНД 32х32 (90°)", "price": PRICES["elbow_32"]},
    "unipak": {"unit": "шт.", "name": "Лён + паста Unipak", "price": PRICES["unipak"]},
    "pipe110": {"unit": "м", "name": "Труба рыжая 110х3.2 наружная", "price": PRICES["pipe110"]},
    "insul110": {"unit": "м", "name": "Утеплитель для трубы 110", "price": PRICES["insul110"]},
    "elbow110_45": {"unit": "шт.", "name": "Отвод 110х45° рыжий", "price": PRICES["elbow110_45"]},
    "tee110": {"unit": "шт.", "name": "Тройник 110х110х87° рыжий", "price": PRICES["tee110"]},
    "bacteria": {"unit": "шт.", "name": "Бактерии для септика (старт)", "price": PRICES["bacteria"]},
    "drain_pipe": {"unit": "м", "name": "Труба дренажная 110 с перфорацией", "price": PRICES["drain_pipe_classic"]},
    "geotextile": {"unit": "рул.", "name": "Геотекстиль иглопробивной (рулон)", "price": PRICES["geotextile_roll"]},
    "well_cone": {"unit": "шт.", "name": "Конус-переходник для колодца 315", "price": PRICES["well_cone"]},
    "sand_trap": {"unit": "шт.", "name": "Пескоуловитель пластиковый 110", "price": PRICES["sand_trap"]},
    "leaf_grate": {"unit": "шт.", "name": "Листвоуловитель для дождеприёмника", "price": PRICES["leaf_grate"]}
}

def get_system_name_ru(mode: str) -> str:
    mapping = {
        "well": "Скважина / Кессон",
        "septic": "Септик / Канализация",
        "drainage": "Дренаж участка",
        "storm": "Ливнёвка в земле"
    }
    return mapping.get(str(mode).lower().strip(), "Скважина / Кессон")

def extract_delivery_address(delivery_info: str) -> str:
    """Извлекает чистый адрес из строки описания доставки."""
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

def sync_to_google_sheet(order_id: str, data: dict, total_sum: int):
    """Выгрузка нового заказа в Google Таблицу (Колонки A-J)."""
    webhook_url = GOOGLE_SHEET_WEBHOOK
    if not webhook_url:
        return

    client_name = data.get("worker_name", "Монтажник")
    worker_tag = data.get("worker_tag", "")
    full_client_info = f"{client_name} ({worker_tag})" if worker_tag else client_name

    payload = {
        "action": "create_order",
        "order_id": str(order_id).strip(),
        "client_name": str(full_client_info),
        "phone": str(data.get("phone", "")),
        "system_type": get_system_name_ru(data.get("mode", "well")),
        "delivery_type": str(data.get("delivery_type", "Самовывоз")),
        "delivery_info": str(data.get("delivery_info", "-")),
        "total_sum": int(total_sum)
    }

    try:
        requests.post(webhook_url, json=payload, timeout=10, allow_redirects=True)
    except Exception as e:
        print(f"[SHEET SYNC ERR] {e}")

def update_sheet_status(order_id: str, status: str, cancel_reason: str = ""):
    """Обновление статуса (Колонка I) и причины отмены (Колонка J)."""
    webhook_url = GOOGLE_SHEET_WEBHOOK
    if not webhook_url:
        return

    order = ACTIVE_ORDERS.get(order_id, {})
    raw_data = order.get("raw_data", {})
    client_name = raw_data.get("worker_name", "Монтажник")
    worker_tag = raw_data.get("worker_tag", "")
    full_client_info = f"{client_name} ({worker_tag})" if worker_tag else client_name

    payload = {
        "action": "update_status",
        "order_id": str(order_id).strip(),
        "client_name": str(full_client_info),
        "phone": str(order.get("phone", "")),
        "system_type": get_system_name_ru(raw_data.get("mode", "well")),
        "delivery_type": str(order.get("delivery_type", "")),
        "delivery_info": str(order.get("delivery_info", "")),
        "total_sum": int(order.get("total_sum", 0)),
        "status": str(status),
        "cancel_reason": str(cancel_reason)
    }

    try:
        res = requests.post(webhook_url, json=payload, timeout=10, allow_redirects=True)
        print(f"[SHEET UPDATE] {order_id} -> {status}: {res.status_code}")
    except Exception as e:
        print(f"[SHEET UPDATE ERR] {e}")

def get_items_for_order(data: dict):
    mode = data.get("mode", "well")
    extras = data.get("extras", {})
    items = []

    if mode == "well":
        depth = data.get("depth", 40)
        houses = data.get("houses", 1)
        distances = data.get("distances", [15])
        selected_kesson = data.get("chosen_kesson", "auto")

        total_dist = sum(distances)
        max_dist = max(distances)
        pump_depth = max(10, int(depth - 5))
        total_pipe_run = pump_depth + max_dist
        req_head = int(pump_depth + (total_pipe_run * 0.10) + 35)

        if req_head <= 60: pump_name, pump_p = "Насос скважинный (до 65 м)", PRICES["pump_60"]
        elif req_head <= 85: pump_name, pump_p = "Насос скважинный (до 90 м)", PRICES["pump_85"]
        elif req_head <= 110: pump_name, pump_p = "Насос усиленный (до 115 м)", PRICES["pump_110"]
        else: pump_name, pump_p = "Насос высоконапорный (120+ м)", PRICES["pump_120"]

        if "Мишка 1" in selected_kesson: k_name, k_p = "Кессон «МИШКА-1» (Ø1050)", PRICES["kesson_m1"]
        elif "Мишка 2" in selected_kesson: k_name, k_p = "Кессон «МИШКА-2» (Ø1300)", PRICES["kesson_m2"]
        elif "Мишка 3" in selected_kesson: k_name, k_p = "Кессон «МИШКА-3» (Ø1600)", PRICES["kesson_m3"]
        elif "Мишка 4" in selected_kesson: k_name, k_p = "Кессон «МИШКА-4» (Ø2100)", PRICES["kesson_m4"]
        elif "LONG" in selected_kesson: k_name, k_p = "Кессон «МИШКА LONG» (H=2500)", PRICES["kesson_long"]
        else:
            k_name, k_p = ("Кессон «МИШКА-2» (1000х2000)", PRICES["kesson_m2"]) if houses == 1 else (f"Кессон «МИШКА-3» ({houses} вывода)", PRICES["kesson_m3"])

        tank_name, tank_p = ("Гидроаккумулятор 80-100 л", PRICES["tank_80"]) if houses == 1 else ("Гидроаккумулятор 150-200 л", PRICES["tank_150"])

        pnd_m = int((pump_depth * 1.05) + (total_dist * 1.05) + (houses * 4))
        cable_m = int((pump_depth + 5) * 1.1)
        rope_m = int(pump_depth + 6)
        insul_m = int(total_dist + (houses * 2))

        items = [
            {"name": k_name, "qty": 1, "unit": "шт.", "price": k_p},
            {"name": "Оголовок скважинный 125-133/32", "qty": 1, "unit": "шт.", "price": PRICES["well_head"]},
            {"name": "Гермоввод ПНД 32 в кессон", "qty": houses + 1, "unit": "шт.", "price": PRICES["wall_seal"]},
            {"name": pump_name, "qty": 1, "unit": "шт.", "price": pump_p},
            {"name": "Трос нерж. А2 (Ø4 мм)", "qty": rope_m, "unit": "м", "price": PRICES["rope"]},
            {"name": "Зажимы троса + коуши + карабин", "qty": 1, "unit": "компл.", "price": 950},
            {"name": "Обратный клапан 1\" + ниппель 1\"", "qty": 1, "unit": "компл.", "price": 1830},
            {"name": "Труба ПНД PE-100 SDR11 Ø32 мм", "qty": pnd_m, "unit": "м", "price": PRICES["pnd32"]},
            {"name": "Кабель водопогружной КВВ-П 3х2.5", "qty": cable_m, "unit": "м", "price": PRICES["cable"]},
            {"name": "Муфта термоусадочная клеевая", "qty": 1, "unit": "компл.", "price": PRICES["cable_sleeve"]},
            {"name": "Утеплитель для ПНД 32", "qty": insul_m, "unit": "м", "price": PRICES["insul"]},
            {"name": tank_name, "qty": 1, "unit": "шт.", "price": tank_p},
            {"name": "Автоматика: реле + манометр + штуцер", "qty": 1, "unit": "компл.", "price": 5100},
            {"name": "Краны шаровые 1\" с американкой", "qty": houses * 2, "unit": "шт.", "price": PRICES["ball_valve"]},
            {"name": "Греющий кабель саморег. для ввода", "qty": houses * 3, "unit": "м", "price": PRICES["heat_cable"]}
        ]

    elif mode == "septic":
        dist = data.get("distance", 10)
        discharge = data.get("discharge", "gravity")
        chosen = data.get("chosen_septic", "auto")

        if "Био 3" in chosen: s_n, s_p = "Станция «МИШКА-Био 3»", PRICES["septic_bio3"]
        elif "Био 8" in chosen: s_n, s_p = "Станция «МИШКА-Био 8»", PRICES["septic_bio8"]
        else: s_n, s_p = "Станция «МИШКА-Био 5»", PRICES["septic_bio5"]

        pipe_m = int(dist * 1.05)
        items = [
            {"name": s_n, "qty": 1, "unit": "шт.", "price": s_p},
            {"name": "Труба ПВХ рыжая наружная 110х3.2", "qty": pipe_m, "unit": "м", "price": PRICES["pipe110"]},
            {"name": "Утеплитель для трубы 110", "qty": pipe_m, "unit": "м", "price": PRICES["insul110"]},
            {"name": "Отводы 110х45° рыжие", "qty": max(2, int(dist // 6) + 1), "unit": "шт.", "price": PRICES["elbow110_45"]},
            {"name": "Тройник ревизионный 110 с заглушкой", "qty": 1, "unit": "шт.", "price": PRICES["tee110"]},
            {"name": "Бактерии для быстрого запуска", "qty": 1, "unit": "компл.", "price": PRICES["bacteria"]}
        ]
        if discharge == "forced":
            items.extend([
                {"name": "Насос дренажный с поплавком", "qty": 1, "unit": "шт.", "price": PRICES["drain_pump"]},
                {"name": "Шланг напорный армированный 32", "qty": 10, "unit": "м", "price": PRICES["drain_hose"]},
                {"name": "Кабель греющий для слива", "qty": 5, "unit": "м", "price": PRICES["cable_heat_septic"]}
            ])

    elif mode == "drainage":
        dtype = data.get("drain_type", "softrock")
        length = data.get("drain_length", 50)
        wells = data.get("drain_wells", 3)

        if dtype == "softrock":
            items = [
                {"name": "Блоки «Софтрок/Лайтдрок» 110 (L=3м)", "qty": length, "unit": "м", "price": PRICES["drain_softrock"]},
                {"name": "Соединительные муфты Софтрок", "qty": int(length // 3) + 1, "unit": "шт.", "price": PRICES["softrock_coupling"]}
            ]
        else:
            items = [
                {"name": "Труба дренажная 110 с фильтром", "qty": length, "unit": "м", "price": PRICES["drain_pipe_classic"]},
                {"name": "Геотекстиль Дорнит (рулон 2х50м)", "qty": max(1, int(length // 45) + 1), "unit": "рул.", "price": PRICES["geotextile_roll"]}
            ]
        items.extend([
            {"name": "Колодец смотровой d315 + люк + дно", "qty": wells, "unit": "шт.", "price": PRICES["well_drain_315"]},
            {"name": "Муфты врезки 110 в колодец 315", "qty": wells * 2, "unit": "шт.", "price": PRICES["well_drain_coupling"]}
        ])

    elif mode == "storm":
        inlets = data.get("storm_inlets", 4)
        length = data.get("storm_length", 30)
        wells = data.get("storm_wells", 2)
        discharge = data.get("storm_discharge", "ditch")

        items = [
            {"name": "Дождеприёмник 300х300 с корзиной и решёткой", "qty": inlets, "unit": "шт.", "price": PRICES["storm_inlet_box"]},
            {"name": "Труба ПВХ рыжая 110х3.2 наружная", "qty": int(length * 1.05), "unit": "м", "price": PRICES["storm_pipe110"]},
            {"name": "Отводы 110х45° рыжие", "qty": inlets * 2 + wells * 2, "unit": "шт.", "price": PRICES["elbow110_45"]},
            {"name": "Тройники 110х110х87° рыжие", "qty": max(1, inlets - 1), "unit": "шт.", "price": PRICES["tee110"]},
            {"name": "Колодец поворотный d315 с люком", "qty": wells, "unit": "шт.", "price": PRICES["storm_well_315"]}
        ]
        if discharge == "ditch":
            items.append({"name": "Клапан обратный 110 против подпора", "qty": 1, "unit": "шт.", "price": PRICES["storm_back_valve"]})

    for k, q in extras.items():
        if k in EXTRA_ITEMS and q > 0:
            e = EXTRA_ITEMS[k]
            items.append({"name": f"[Доп] {e['name']}", "qty": q, "unit": e["unit"], "price": e["price"]})

    return items

def build_order_payload(data: dict):
    order_id = str(uuid.uuid4())[:8]
    items = get_items_for_order(data)

    total_sum = 0
    lines = []
    for it in items:
        subtotal = int(it["qty"] * it["price"])
        total_sum += subtotal
        qty_str = f"{it['qty']:g}" if isinstance(it["qty"], float) else str(it["qty"])
        lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {it['unit']} × {it['price']:,} ₽ = <b>{subtotal:,} ₽</b>".replace(",", " "))

    delivery_type = data.get("delivery_type", "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = "Доставка" in delivery_type
    clean_address = extract_delivery_address(delivery_info)

    ACTIVE_ORDERS[order_id] = {
        "client_id": data.get("chat_id"),
        "client_name": data.get("worker_name", "Монтажник"),
        "phone": data.get("phone", "Не указан"),
        "delivery_type": delivery_type,
        "delivery_info": delivery_info,
        "clean_address": clean_address,
        "is_delivery": is_delivery,
        "raw_data": data,
        "items": items,
        "collected": [False] * len(items),
        "total_sum": total_sum,
        "status": "active"
    }

    # Выгрузка нового заказа в Google Таблицу
    sync_to_google_sheet(order_id, data, total_sum)

    phone = data.get("phone", "Не указан")
    items_block = "\n".join(lines)

    # Формируем наглядный блок логистики для менеджера
    if is_delivery:
        logistics_block = (
            f"🚚 <b>Получение:</b> 🚛 <b>ДОСТАВКА НА ОБЪЕКТ</b>\n"
            f"📍 <b>Адрес доставки:</b> <code>{clean_address or 'Не указан'}</code>\n"
            f"🕒 <b>Детали/Время:</b> <i>{delivery_info}</i>"
        )
    else:
        logistics_block = (
            f"🚚 <b>Получение:</b> 📦 <b>Самовывоз со склада</b>\n"
            f"🕒 <b>Время приезда:</b> <i>{delivery_info}</i>"
        )

    header = (
        f"🧾 <b>НОВЫЙ ЗАКАЗ #{order_id} «МИШКА»</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👷 <b>Заказчик:</b> {data.get('worker_name')} ({data.get('worker_tag')})\n"
        f"📞 <b>Телефон:</b> <a href='tel:{phone}'>{phone}</a>\n"
        f"{logistics_block}\n"
        f"🆔 ID клиента: <code>{data.get('chat_id')}</code>\n\n"
        f"📦 <b>СПЕЦИФИКАЦИЯ:</b>\n\n"
        f"{items_block}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>ИТОГО К ОПЛАТЕ: {total_sum:,} ₽</b>"
    ).replace(",", " ")

    return order_id, header, total_sum

def make_warehouse_keyboard(order_id: str):
    """Клавиатура склада с кнопкой маршрута к клиенту, отметками и отменой."""
    order = ACTIVE_ORDERS.get(order_id)
    if not order:
        return None

    kb = types.InlineKeyboardMarkup(row_width=1)

    if order.get("status") == "cancelled":
        reason = order.get("cancel_reason", "")
        reason_txt = f": {reason}" if reason else ""
        kb.add(types.InlineKeyboardButton(f"❌ ЗАКАЗ ОТМЕНЁН{reason_txt}", callback_data="none"))
        return kb

    if order.get("status") == "completed":
        kb.add(types.InlineKeyboardButton("🎉 ЗАКАЗ СОБРАН И ВЫДАН", callback_data="none"))
        return kb

    # Кнопка маршрута прямо к объекту клиента при доставке
    if order.get("is_delivery"):
        addr = order.get("clean_address") or extract_delivery_address(order.get("delivery_info", ""))
        if addr:
            nav_url = f"https://yandex.ru/navi?text={urllib.parse.quote(addr)}"
            kb.add(types.InlineKeyboardButton("🚗 Построить маршрут к клиенту (Яндекс)", url=nav_url))

    # Кнопки сбора позиций на складе
    for idx, (item, is_done) in enumerate(zip(order["items"], order["collected"])):
        mark = "🟢" if is_done else "⬜"
        qty_str = f"{item['qty']:g}" if isinstance(item['qty'], float) else str(item['qty'])
        short_name = (item['name'][:22] + "..") if len(item['name']) > 22 else item['name']
        btn_text = f"{mark} {idx+1}. {short_name} ({qty_str} {item['unit']})"
        kb.add(types.InlineKeyboardButton(btn_text, callback_data=f"chk_{order_id}_{idx}"))

    # Завершить заказ
    all_done = all(order["collected"])
    finish_icon = "🚀" if all_done else "📦"
    kb.add(types.InlineKeyboardButton(f"{finish_icon} ЗАКАЗ ПОЛНОСТЬЮ СОБРАН", callback_data=f"fin_{order_id}"))

    # Отмена и корректировка
    row_ctrl = [
        types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{order_id}"),
        types.InlineKeyboardButton("✏️ Корректировка", callback_data=f"edit_{order_id}")
    ]
    kb.row(*row_ctrl)

    return kb
