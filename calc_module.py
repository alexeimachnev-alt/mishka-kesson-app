import os
import uuid
import requests
from telebot import types

PRIMARY_ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
SECOND_ADMIN_ID = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))
ADMIN_CHAT_IDS = [PRIMARY_ADMIN_ID, SECOND_ADMIN_ID]

GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()

# Хранилище заказов: order_id -> dict
ACTIVE_ORDERS = {}

# Цены (руб.)
PRICES = {
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

    "drain_pipe_classic": 280,
    "drain_softrock": 750,
    "geotextile_roll": 4500,
    "well_drain_315": 3800,
    "well_drain_coupling": 350,
    "well_cone": 1800,
    "softrock_coupling": 420,

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

def sync_to_google_sheet(order_id: str, data: dict, total_sum: int):
    """Выгружает новую строчку в Google Таблицу по вебхуку."""
    if not GOOGLE_SHEET_WEBHOOK:
        return
    payload = {
        "order_id": order_id,
        "client_name": data.get("worker_name", "Заказчик"),
        "phone": data.get("phone", "Не указан"),
        "delivery_type": data.get("delivery_type", "Самовывоз"),
        "delivery_info": data.get("delivery_info", "-"),
        "mode": data.get("mode", "well"),
        "total_sum": total_sum
    }
    try:
        requests.post(GOOGLE_SHEET_WEBHOOK, json=payload, timeout=5)
        print(f"[SHEET SYNC] Заказ #{order_id} отправлен в Google Таблицу")
    except Exception as e:
        print(f"[SHEET SYNC ERR] {e}")

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
