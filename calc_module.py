import os
from telebot import types

PRIMARY_ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
SECOND_ADMIN_ID = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))

ADMIN_CHAT_IDS = [PRIMARY_ADMIN_ID, SECOND_ADMIN_ID]

EXTRA_ITEMS = {
    "pnd32": {"unit": "м", "name": "Труба ПНД 32 SDR11"},
    "pnd25": {"unit": "м", "name": "Труба ПНД 25 (полив)"},
    "insul": {"unit": "м", "name": "Утеплитель Энергофлекс 32"},
    "heat_cable": {"unit": "м", "name": "Кабель греющий саморег."},
    "ball_valve": {"unit": "шт.", "name": "Кран 1\" с американкой"},
    "fitting_32_1": {"unit": "шт.", "name": "Муфта ПНД 32х1\" НР"},
    "elbow_32": {"unit": "шт.", "name": "Уголок ПНД 32х32 (90°)"},
    "unipak": {"unit": "шт.", "name": "Лён + паста Unipak"}
}

def send_to_all_admins(bot, text: str):
    """Отправляет сборочный лист обоим администраторам."""
    for a_id in ADMIN_CHAT_IDS:
        try:
            bot.send_message(a_id, text, parse_mode="HTML")
            print(f"[SUCCESS] Отправлено админу: {a_id}")
        except Exception as e:
            print(f"[ERROR] Не удалось отправить админу {a_id}: {e}")

def build_warehouse_checklist(data: dict) -> str:
    """Формирует сборочный лист склада строго на русском языке."""
    depth = data["depth"]
    yield_flow = data["yield_flow"]
    houses = data["houses"]
    distances = data["distances"]
    extras = data.get("extras", {})
    selected_kesson = data.get("chosen_kesson", "auto")

    total_distance = sum(distances)
    max_distance = max(distances)

    pump_depth = max(10, int(depth - 5))
    total_pipe_run = pump_depth + max_distance
    friction_losses = total_pipe_run * 0.10
    required_head = int(pump_depth + friction_losses + 30 + 5)

    if required_head <= 60:
        pump_model = "Насос скважинный 3\"/4\" (напор 60-70 м, 2.5-3.0 м³/ч)"
    elif required_head <= 85:
        pump_model = "Насос скважинный 3\"/4\" (напор 80-90 м, 3.0-3.5 м³/ч)"
    elif required_head <= 110:
        pump_model = "Насос скважинный усиленный (напор 100-115 м)"
    else:
        pump_model = "Насос высоконапорный промышленной серии (напор 120+ м)"

    if selected_kesson == "auto":
        if houses == 1:
            kesson_name = "Кессон пластиковый «МИШКА-2» (1000х2000 мм) [Автоподбор склада]"
            branch_tees = 1
        else:
            kesson_name = f"Кессон пластиковый «МИШКА-3» (увеличенный под {houses} вывода) [Автоподбор склада]"
            branch_tees = houses
    else:
        kesson_name = f"Кессон «{selected_kesson}» [Выбран монтажником]"
        branch_tees = max(1, houses)

    if houses == 1:
        tank_spec = "Гидроаккумулятор 80-100 л (вертикальный, фланец нерж)"
    elif houses == 2:
        tank_spec = "Гидроаккумулятор 150 л (или 2 шт. по 80-100 л)"
    else:
        tank_spec = f"Гидроаккумулятор 200-300 л (под {houses} домов)"

    pnd_downhole = int(pump_depth * 1.05)
    pnd_trench = int(total_distance * 1.05)
    total_pnd_pipe = pnd_downhole + pnd_trench + (houses * 4)
    cable_m = int((pump_depth + 5) * 1.1)
    rope_m = int(pump_depth + 6)
    cable_ties = max(40, int(pump_depth * 1.5))
    insulation_m = int(total_distance + (houses * 2))

    if houses == 1:
        routes_detail = f"• Трасса до дома: <b>{distances[0]} м</b>\n"
    else:
        routes_detail = f"• Домов: <b>{houses} шт.</b> (общая длина трасс: <b>{total_distance} м</b>):\n"
        for idx, d in enumerate(distances, start=1):
            routes_detail += f"   ▫️ Дом №{idx}: <b>{d} м</b>\n"

    extras_block = ""
    if extras:
        extras_block = "\n🔥 <b>ДОПОЛНИТЕЛЬНЫЕ РАСХОДНИКИ (ПО ЗАПРОСУ МОНТАЖНИКА):</b>\n"
        for item_key, qty in extras.items():
            item_info = EXTRA_ITEMS.get(item_key)
            if item_info and qty > 0:
                extras_block += f"  ➕ <b>{item_info['name']}</b> — <b>{qty} {item_info['unit']}</b>\n"
    else:
        extras_block = "\n▫️ <i>Дополнительных расходников не запрошено.</i>\n"

    checklist = (
        f"📦 <b>ЗАКАЗ ИЗ MINI APP НА СКЛАДСКУЮ СБОРКУ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👷 <b>Монтажник:</b> {data['worker_name']} ({data['worker_tag']})\n"
        f"🆔 ID чата: <code>{data['chat_id']}</code>\n\n"
        f"📋 <b>Входные параметры объекта:</b>\n"
        f"• Глубина скважины: <b>{depth} м</b> (подвеска насоса на ~{pump_depth} м)\n"
        f"• Дебит: <b>{yield_flow} м³/ч</b> | Расчётный напор: <b>{required_head} м</b>\n"
        f"{routes_detail}\n"
        f"🛠 <b>ОСНОВНОЙ КОМПЛЕКТ НА ОТГРУЗКУ:</b>\n\n"
        f"<b>1. Кессон и устье:</b>\n"
        f"  ▫️ <b>{kesson_name}</b> — 1 шт.\n"
        f"  ▫️ Муфта обсадной трубы герметичная — 1 шт.\n"
        f"  ▫️ Оголовок скважинный 125-133/32 — 1 шт.\n"
        f"  ▫️ Гермовводы для ПНД 32 в стенки кессона — {houses + 1} шт. (трассы + полив)\n\n"
        f"<b>2. Спускной скважинный узел:</b>\n"
        f"  ▫️ {pump_model} — 1 шт.\n"
        f"  ▫️ Трос нержавеющий А2/А4 (Ø4 мм) — <b>{rope_m} м</b>\n"
        f"  ▫️ Зажимы троса нержавеющие дуплекс 4 мм — 4 шт.\n"
        f"  ▫️ Коуши нержавеющие 4 мм — 2 шт.\n"
        f"  ▫️ Карабин винтовой нержавеющий 8 мм — 1 шт.\n"
        f"  ▫️ Обратный клапан латунный 1\" — 1 шт.\n"
        f"  ▫️ Ниппель латунный 1\" НР-НР — 1 шт.\n"
        f"  ▫️ Муфта латунная компрессионная ПНД 32 х 1\" НР — 1 шт.\n\n"
        f"<b>3. Труба, кабель и изоляция:</b>\n"
        f"  ▫️ Труба питьевая ПНД PE-100 SDR11 Ø32 мм — <b>{total_pnd_pipe} м</b>\n"
        f"  ▫️ Кабель водопогружной КВВ-П 3х2.5 — <b>{cable_m} м</b>\n"
        f"  ▫️ Термоусадочная клеевая кабельная муфта — 1 компл.\n"
        f"  ▫️ Стяжки нейлоновые уличные черные — {cable_ties} шт.\n"
        f"  ▫️ Утеплитель для ПНД 32 (энергофлекс 9-13 мм) — <b>{insulation_m} м</b>\n\n"
        f"<b>4. Автоматика и разводка:</b>\n"
        f"  ▫️ {tank_spec} — 1 шт.\n"
        f"  ▫️ Пятивыводной штуцер (пятерник) 1\" латунь — {branch_tees} шт.\n"
        f"  ▫️ Реле давления (Italtecnica / Турбипресс) — 1 шт.\n"
        f"  ▫️ Манометр 0-6 бар (1/4\") — 1 шт.\n"
        f"  ▫️ Магистральный фильтр BB10/BB20 (1\") + картридж — 1 шт.\n"
        f"  ▫️ Краны шаровые латунные 1\" (с американкой) — {2 * houses} шт.\n"
        f"  ▫️ Кран летнего полива 3/4\" со штуцером — 1 шт.\n"
        f"  ▫️ Греющий кабель саморегулирующийся (вводы в дома) — <b>{houses * 3} м</b> + {houses} сальниковых узлов\n"
        f"{extras_block}"
    )
    return checklist
