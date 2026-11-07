import os
from telebot import types

PRIMARY_ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
SECOND_ADMIN_ID = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))

ADMIN_CHAT_IDS = [PRIMARY_ADMIN_ID, SECOND_ADMIN_ID]

# Базовый прайс на комплектующие (руб.)
PRICES = {
    # Скважина: трубы, кабель, изоляция
    "pnd32": 130,          # за м
    "pnd25": 95,           # за м
    "cable": 220,          # за м (КВВ-П 3х2.5)
    "rope": 90,            # за м (нерж. трос 4 мм)
    "insul": 60,           # за м (энергофлекс 32)
    "heat_cable": 350,     # за м (саморегулирующийся)
    "ball_valve": 1250,    # шт.
    "fitting_32_1": 420,   # шт.
    "elbow_32": 480,       # шт.
    "unipak": 650,         # компл.
    "check_valve": 1450,   # шт.
    "nipple": 380,         # шт.
    "rope_clips": 120,     # шт.
    "rope_thimble": 90,    # шт.
    "carabiner": 250,      # шт.
    "cable_sleeve": 950,   # компл.
    "cable_ties": 5,       # шт.
    "well_head": 4200,     # шт.
    "wall_seal": 850,      # шт.
    "pressure_switch": 2800,
    "manometer": 650,
    "five_way": 1650,
    "filter_bb": 4500,
    "garden_tap": 1100,

    # Кессоны МИШКА (по прайсу 06.2026-2)
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

    # Септики и канализация
    "septic_bio3": 85000,   # Станция биоочистки МИШКА-Био 3
    "septic_bio5": 105000,  # Станция биоочистки МИШКА-Био 5
    "septic_bio8": 138000,  # Станция биоочистки МИШКА-Био 8
    "septic_bio10": 165000, # Станция биоочистки МИШКА-Био 10
    "septic_tank2": 62000,  # Накопитель МИШКА 2.0 м³
    "septic_tank3": 82000,  # Накопитель МИШКА 3.0 м³
    "drain_pump": 8500,     # Дренажный насос для принудительного сброса
    "drain_hose": 250,      # Шланг напорный армированный за м
    "pipe110": 480,         # Труба рыжая ПВХ 110х3.2 наружная за м
    "insul110": 140,        # Утеплитель для 110 трубы за м
    "elbow110_45": 280,     # Отвод 110х45° рыжий шт.
    "tee110": 490,          # Тройник 110х110х87° рыжий шт.
    "bacteria": 1200,       # Стартовые биобактерии компл.
    "drain_pipe": 320,      # Труба дренажная 110 перфорированная с фильтром за м
    "cable_heat_septic": 380 # Кабель саморег. для слива за м
}

EXTRA_ITEMS = {
    # Скважина
    "pnd32": {"unit": "м", "name": "Труба ПНД 32 SDR11", "price": PRICES["pnd32"]},
    "pnd25": {"unit": "м", "name": "Труба ПНД 25 (полив)", "price": PRICES["pnd25"]},
    "insul": {"unit": "м", "name": "Утеплитель Энергофлекс 32", "price": PRICES["insul"]},
    "heat_cable": {"unit": "м", "name": "Кабель греющий саморег.", "price": PRICES["heat_cable"]},
    "ball_valve": {"unit": "шт.", "name": "Кран 1\" с американкой", "price": PRICES["ball_valve"]},
    "fitting_32_1": {"unit": "шт.", "name": "Муфта ПНД 32х1\" НР", "price": PRICES["fitting_32_1"]},
    "elbow_32": {"unit": "шт.", "name": "Уголок ПНД 32х32 (90°)", "price": PRICES["elbow_32"]},
    "unipak": {"unit": "шт.", "name": "Лён + паста Unipak", "price": PRICES["unipak"]},

    # Септик
    "pipe110": {"unit": "м", "name": "Труба рыжая 110х3.2 наружная", "price": PRICES["pipe110"]},
    "insul110": {"unit": "м", "name": "Утеплитель для трубы 110", "price": PRICES["insul110"]},
    "elbow110_45": {"unit": "шт.", "name": "Отвод 110х45° рыжий", "price": PRICES["elbow110_45"]},
    "tee110": {"unit": "шт.", "name": "Тройник 110х110х87° рыжий", "price": PRICES["tee110"]},
    "bacteria": {"unit": "шт.", "name": "Бактерии для септика (старт)", "price": PRICES["bacteria"]},
    "drain_pipe": {"unit": "м", "name": "Труба дренажная 110 с перфорацией", "price": PRICES["drain_pipe"]}
}

def send_to_all_admins(bot, text: str):
    """Отправляет смету обоим администраторам."""
    for a_id in ADMIN_CHAT_IDS:
        try:
            bot.send_message(a_id, text, parse_mode="HTML")
            print(f"[SUCCESS] Отправлено админу: {a_id}")
        except Exception as e:
            print(f"[ERROR] Не удалось отправить админу {a_id}: {e}")

def calculate_well_estimate(data: dict):
    """Расчет оборудования и стоимости для скважины/кессона."""
    depth = data["depth"]
    houses = data["houses"]
    distances = data["distances"]
    extras = data.get("extras", {})
    selected_kesson = data.get("chosen_kesson", "auto")

    total_dist = sum(distances)
    max_dist = max(distances)

    pump_depth = max(10, int(depth - 5))
    total_pipe_run = pump_depth + max_dist
    req_head = int(pump_depth + (total_pipe_run * 0.10) + 35)

    if req_head <= 60:
        pump_name, pump_p = "Насос скважинный 3\"/4\" (напор до 65 м)", PRICES["pump_60"]
    elif req_head <= 85:
        pump_name, pump_p = "Насос скважинный 3\"/4\" (напор до 90 м)", PRICES["pump_85"]
    elif req_head <= 110:
        pump_name, pump_p = "Насос усиленный 3\"/4\" (напор до 115 м)", PRICES["pump_110"]
    else:
        pump_name, pump_p = "Насос промышленный высоконапорный (120+ м)", PRICES["pump_120"]

    if "Мишка 1" in selected_kesson:
        kesson_name, kesson_p = "Кессон пластиковый «МИШКА-1» (Ø1050)", PRICES["kesson_m1"]
    elif "Мишка 2" in selected_kesson:
        kesson_name, kesson_p = "Кессон пластиковый «МИШКА-2» (Ø1300)", PRICES["kesson_m2"]
    elif "Мишка 3" in selected_kesson:
        kesson_name, kesson_p = "Кессон пластиковый «МИШКА-3» (Ø1600)", PRICES["kesson_m3"]
    elif "Мишка 4" in selected_kesson:
        kesson_name, kesson_p = "Кессон пластиковый «МИШКА-4» (Ø2100)", PRICES["kesson_m4"]
    elif "LONG" in selected_kesson:
        kesson_name, kesson_p = "Кессон пластиковый «МИШКА LONG» (H=2500)", PRICES["kesson_long"]
    else:
        if houses == 1:
            kesson_name, kesson_p = "Кессон пластиковый «МИШКА-2» (1000х2000 мм)", PRICES["kesson_m2"]
        else:
            kesson_name, kesson_p = f"Кессон «МИШКА-3» (увеличенный на {houses} вывода)", PRICES["kesson_m3"]

    if houses == 1:
        tank_name, tank_p = "Гидроаккумулятор 80-100 л (нерж. фланец)", PRICES["tank_80"]
    elif houses == 2:
        tank_name, tank_p = "Гидроаккумулятор 150 л", PRICES["tank_150"]
    else:
        tank_name, tank_p = f"Гидроаккумулятор 200-300 л (под {houses} домов)", PRICES["tank_200"]

    pnd_meters = int((pump_depth * 1.05) + (total_dist * 1.05) + (houses * 4))
    cable_meters = int((pump_depth + 5) * 1.1)
    rope_meters = int(pump_depth + 6)
    insul_meters = int(total_dist + (houses * 2))
    ties_count = max(40, int(pump_depth * 1.5))
    wall_seals = houses + 1
    valves_count = 2 * houses
    heat_cable_m = houses * 3

    items = [
        {"name": kesson_name, "qty": 1, "unit": "шт.", "price": kesson_p},
        {"name": "Оголовок скважинный 125-133/32", "qty": 1, "unit": "шт.", "price": PRICES["well_head"]},
        {"name": "Гермоввод ПНД 32 в кессон", "qty": wall_seals, "unit": "шт.", "price": PRICES["wall_seal"]},
        {"name": pump_name, "qty": 1, "unit": "шт.", "price": pump_p},
        {"name": "Трос нержавеющий А2 (Ø4 мм)", "qty": rope_meters, "unit": "м", "price": PRICES["rope"]},
        {"name": "Зажимы троса дуплекс 4 мм", "qty": 4, "unit": "шт.", "price": PRICES["rope_clips"]},
        {"name": "Коуши нерж. 4 мм + карабин 8 мм", "qty": 1, "unit": "компл.", "price": (2 * PRICES["rope_thimble"] + PRICES["carabiner"])},
        {"name": "Обратный клапан 1\" + ниппель 1\"", "qty": 1, "unit": "компл.", "price": (PRICES["check_valve"] + PRICES["nipple"])},
        {"name": "Муфта латунная ПНД 32х1\" НР", "qty": 1, "unit": "шт.", "price": PRICES["fitting_32_1"]},
        {"name": "Труба питьевая ПНД PE-100 SDR11 Ø32 мм", "qty": pnd_meters, "unit": "м", "price": PRICES["pnd32"]},
        {"name": "Кабель водопогружной КВВ-П 3х2.5", "qty": cable_meters, "unit": "м", "price": PRICES["cable"]},
        {"name": "Муфта термоусадочная клеевая", "qty": 1, "unit": "компл.", "price": PRICES["cable_sleeve"]},
        {"name": "Стяжки нейлоновые уличные черные", "qty": ties_count, "unit": "шт.", "price": PRICES["cable_ties"]},
        {"name": "Утеплитель для ПНД 32 (энергофлекс)", "qty": insul_meters, "unit": "м", "price": PRICES["insul"]},
        {"name": tank_name, "qty": 1, "unit": "шт.", "price": tank_p},
        {"name": "Пятивыводной штуцер 1\" латунь", "qty": max(1, houses), "unit": "шт.", "price": PRICES["five_way"]},
        {"name": "Реле давления + манометр 0-6 бар", "qty": 1, "unit": "компл.", "price": (PRICES["pressure_switch"] + PRICES["manometer"])},
        {"name": "Магистральный фильтр BB + картридж", "qty": 1, "unit": "шт.", "price": PRICES["filter_bb"]},
        {"name": "Краны шаровые 1\" с американкой", "qty": valves_count, "unit": "шт.", "price": PRICES["ball_valve"]},
        {"name": "Кран полива 3/4\" со штуцером", "qty": 1, "unit": "шт.", "price": PRICES["garden_tap"]},
        {"name": "Греющий кабель саморег. + сальники ввода", "qty": heat_cable_m, "unit": "м", "price": PRICES["heat_cable"]}
    ]

    for k, q in extras.items():
        if k in EXTRA_ITEMS and q > 0:
            e = EXTRA_ITEMS[k]
            items.append({"name": f"[Доп] {e['name']}", "qty": q, "unit": e["unit"], "price": e["price"]})

    total_sum = 0
    lines = []
    for it in items:
        subtotal = int(it["qty"] * it["price"])
        total_sum += subtotal
        qty_str = f"{it['qty']:g}" if isinstance(it["qty"], float) else str(it["qty"])
        lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {it['unit']} × {it['price']:,} ₽ = <b>{subtotal:,} ₽</b>".replace(",", " "))

    return lines, total_sum, pump_depth, req_head


def calculate_septic_estimate(data: dict):
    """Расчет оборудования и стоимости для септика/канализации."""
    users = data.get("users", 5)
    discharge = data.get("discharge", "gravity")
    distance = data.get("distance", 10)
    chosen_septic = data.get("chosen_septic", "auto")
    extras = data.get("extras", {})

    # Подбор модели септика
    if "Био 3" in chosen_septic:
        s_name, s_price = "Станция биоочистки «МИШКА-Био 3»", PRICES["septic_bio3"]
    elif "Био 5" in chosen_septic:
        s_name, s_price = "Станция биоочистки «МИШКА-Био 5»", PRICES["septic_bio5"]
    elif "Био 8" in chosen_septic:
        s_name, s_price = "Станция биоочистки «МИШКА-Био 8»", PRICES["septic_bio8"]
    elif "2.0 м³" in chosen_septic:
        s_name, s_price = "Септик-накопитель «МИШКА» 2.0 м³", PRICES["septic_tank2"]
    elif "3.0 м³" in chosen_septic:
        s_name, s_price = "Септик-накопитель «МИШКА» 3.0 м³", PRICES["septic_tank3"]
    else:
        # Автоподбор по числу проживающих
        if users <= 3:
            s_name, s_price = "Станция биоочистки «МИШКА-Био 3» (до 3 чел.)", PRICES["septic_bio3"]
        elif users <= 5:
            s_name, s_price = "Станция биоочистки «МИШКА-Био 5» (до 5 чел.)", PRICES["septic_bio5"]
        elif users <= 8:
            s_name, s_price = "Станция биоочистки «МИШКА-Био 8» (до 8 чел.)", PRICES["septic_bio8"]
        else:
            s_name, s_price = "Станция биоочистки «МИШКА-Био 10» (до 10 чел.)", PRICES["septic_bio10"]

    pipe_meters = int(distance * 1.05)
    insul_meters = pipe_meters
    elbows_count = max(2, int(distance // 6) + 1)

    items = [
        {"name": s_name, "qty": 1, "unit": "шт.", "price": s_price},
        {"name": "Труба ПВХ рыжая наружная 110х3.2 мм", "qty": pipe_meters, "unit": "м", "price": PRICES["pipe110"]},
        {"name": "Утеплитель для канализационной трубы 110", "qty": insul_meters, "unit": "м", "price": PRICES["insul110"]},
        {"name": "Отводы 110х45° рыжие (для плавных поворотов)", "qty": elbows_count, "unit": "шт.", "price": PRICES["elbow110_45"]},
        {"name": "Тройник ревизионный 110х110х87° с заглушкой", "qty": 1, "unit": "шт.", "price": PRICES["tee110"]},
        {"name": "Бактерии биологические для быстрого запуска", "qty": 1, "unit": "компл.", "price": PRICES["bacteria"]}
    ]

    # Добавление элементов принудительного сброса
    if discharge == "forced":
        items.extend([
            {"name": "Насос дренажный погружной с поплавком", "qty": 1, "unit": "шт.", "price": PRICES["drain_pump"]},
            {"name": "Шланг напорный армированный для выброса (Ø32)", "qty": 10, "unit": "м", "price": PRICES["drain_hose"]},
            {"name": "Кабель греющий саморегулирующийся для сброса", "qty": 5, "unit": "м", "price": PRICES["cable_heat_septic"]}
        ])

    for k, q in extras.items():
        if k in EXTRA_ITEMS and q > 0:
            e = EXTRA_ITEMS[k]
            items.append({"name": f"[Доп] {e['name']}", "qty": q, "unit": e["unit"], "price": e["price"]})

    total_sum = 0
    lines = []
    for it in items:
        subtotal = int(it["qty"] * it["price"])
        total_sum += subtotal
        qty_str = f"{it['qty']:g}" if isinstance(it["qty"], float) else str(it["qty"])
        lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {it['unit']} × {it['price']:,} ₽ = <b>{subtotal:,} ₽</b>".replace(",", " "))

    return lines, total_sum, s_name


def build_warehouse_checklist(data: dict) -> str:
    """Формирует смету в зависимости от выбранного режима (скважина или септик)."""
    mode = data.get("mode", "well")

    if mode == "septic":
        lines, total_sum, s_name = calculate_septic_estimate(data)
        discharge_text = "Принудительный (насос)" if data.get("discharge") == "forced" else "Самотечный"
        items_block = "\n".join(lines)

        text = (
            f"🧾 <b>СМЕТА НА СЕПТИК И КАНАЛИЗАЦИЮ «МИШКА»</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👷 <b>Монтажник:</b> {data['worker_name']} ({data['worker_tag']})\n"
            f"🆔 ID клиента: <code>{data['chat_id']}</code>\n\n"
            f"📋 <b>Параметры объекта:</b>\n"
            f"• Проживающих: <b>до {data.get('users', 5)} чел.</b>\n"
            f"• Трасса канализации: <b>{data.get('distance', 10)} м</b>\n"
            f"• Сброс воды: <b>{discharge_text}</b>\n\n"
            f"📦 <b>СПЕЦИФИКАЦИЯ И СТОИМОСТЬ ПО ПОЗИЦИЯМ:</b>\n\n"
            f"{items_block}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>ИТОГО К ОПЛАТЕ: {total_sum:,} ₽</b>".replace(",", " ")
        )
        return text

    else:
        # Режим скважины
        lines, total_sum, pump_depth, req_head = calculate_well_estimate(data)
        houses = data["houses"]
        distances = data["distances"]

        if houses == 1:
            routes_detail = f"• Трасса до дома: <b>{distances[0]} м</b>\n"
        else:
            routes_detail = f"• Домов: <b>{houses} шт.</b> (общая длина: <b>{sum(distances)} м</b>):\n"
            for idx, d in enumerate(distances, start=1):
                routes_detail += f"   ▫️ Дом №{idx}: <b>{d} м</b>\n"

        items_block = "\n".join(lines)

        text = (
            f"🧾 <b>СМЕТА И СБОРОЧНЫЙ ЛИСТ «МИШКА» (СКВАЖИНА)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👷 <b>Монтажник:</b> {data['worker_name']} ({data['worker_tag']})\n"
            f"🆔 ID клиента: <code>{data['chat_id']}</code>\n\n"
            f"📋 <b>Параметры объекта:</b>\n"
            f"• Глубина: <b>{data['depth']} м</b> (погружение насоса: ~{pump_depth} м)\n"
            f"• Дебит: <b>{data['yield_flow']} м³/ч</b> | Расчётный напор: <b>{req_head} м</b>\n"
            f"{routes_detail}\n"
            f"📦 <b>СПЕЦИФИКАЦИЯ И СТОИМОСТЬ ПО ПОЗИЦИЯМ:</b>\n\n"
            f"{items_block}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>ИТОГО К ОПЛАТЕ: {total_sum:,} ₽</b>".replace(",", " ")
        )
        return text
