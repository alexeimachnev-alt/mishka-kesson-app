from constants import PRICES

def get_well_items(data):
    depth = data.get("depth", 40)
    houses = data.get("houses", 1)
    distances = data.get("distances", [15])
    selected_kesson = data.get("chosen_kesson", "auto")
    equip_type = data.get("equip_type", "kesson_vfd")
    chosen_tank = data.get("chosen_tank", "auto")

    total_dist = sum(distances)
    max_dist = max(distances)
    pump_depth = max(10, int(depth - 5))
    total_pipe_run = pump_depth + max_dist
    req_head = int(pump_depth + (total_pipe_run * 0.10) + 35)

    if req_head <= 60:
        pump_name, pump_p = "Насос скважинный (до 65 м)", PRICES["pump_60"]
    elif req_head <= 85:
        pump_name, pump_p = "Насос скважинный (до 90 м)", PRICES["pump_85"]
    elif req_head <= 110:
        pump_name, pump_p = "Насос усиленный (до 115 м)", PRICES["pump_110"]
    else:
        pump_name, pump_p = "Насос высоконапорный (120+ м)", PRICES["pump_120"]

    pnd_m = int((pump_depth * 1.05) + (total_dist * 1.05) + (houses * 4))
    cable_m = int((pump_depth + 5) * 1.1)
    rope_m = int(pump_depth + 6)
    insul_m = int(total_dist + (houses * 2))

    items = [
        {"name": pump_name, "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": pump_p},
        {"name": "Трос нерж. А2 (Ø4 мм)", "qty": rope_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["rope"]},
        {"name": "Зажимы троса + коуши + карабин", "qty": 1, "unit": "компл.", "unit_key": "unit_set", "price": 950},
        {"name": "Обратный клапан 1\" + ниппель 1\"", "qty": 1, "unit": "компл.", "unit_key": "unit_set", "price": 1830},
        {"name": "Труба ПНД PE-100 SDR11 Ø32 мм", "qty": pnd_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["pnd32"]},
        {"name": "Кабель водопогружной КВВ-П 3х2.5", "qty": cable_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["cable"]},
        {"name": "Муфта термоусадочная клеевая", "qty": 1, "unit": "компл.", "unit_key": "unit_set", "price": PRICES["cable_sleeve"]},
        {"name": "Утеплитель для ПНД 32", "qty": insul_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["insul"]},
        {"name": "Краны шаровые 1\" с американкой", "qty": houses * 2, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["ball_valve"]},
        {"name": "Греющий кабель саморег. для ввода", "qty": houses * 3, "unit": "м", "unit_key": "unit_m", "price": PRICES["heat_cable"]}
    ]

    if equip_type == "adapter":
        items.extend([
            {"name": "Адаптер скважинный 1\" (бронза)", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["well_adapter_1"]},
            {"name": "Крышка скважинная под адаптер d125-133", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["cover_adapter"]},
            {"name": "Гидроаккумулятор 80-100 л (в дом)", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["tank_80"]},
            {"name": "Автоматика: реле + манометр + штуцер", "qty": 1, "unit": "компл.", "unit_key": "unit_set", "price": 5100}
        ])
    else:
        if "Мишка 1" in selected_kesson:
            k_name, k_p = "Кессон «МИШКА-1» (Ø1050)", PRICES["kesson_m1"]
        elif "Мишка 2" in selected_kesson:
            k_name, k_p = "Кессон «МИШКА-2» (Ø1300)", PRICES["kesson_m2"]
        elif "Мишка 3" in selected_kesson:
            k_name, k_p = "Кессон «МИШКА-3» (Ø1600)", PRICES["kesson_m3"]
        elif "Мишка 4" in selected_kesson:
            k_name, k_p = "Кессон «МИШКА-4» (Ø2100)", PRICES["kesson_m4"]
        elif "LONG" in selected_kesson:
            k_name, k_p = "Кессон «МИШКА LONG» (H=2500)", PRICES["kesson_long"]
        else:
            k_name, k_p = ("Кессон «МИШКА-2» (1000х2000)", PRICES["kesson_m2"]) if houses == 1 else (f"Кессон «МИШКА-3» ({houses} вывода)", PRICES["kesson_m3"])

        items.extend([
            {"name": k_name, "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": k_p},
            {"name": "Оголовок скважинный 125-133/32", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["well_head"]},
            {"name": "Гермоввод ПНД 32 в кессон", "qty": houses + 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["wall_seal"]}
        ])

        if equip_type == "kesson_vfd":
            items.extend([
                {"name": "Частотный преобразователь с датчиком давления", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["vfd_controller"]},
                {"name": "Гидроаккумулятор буферный 5–8 л для ПЧ", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["tank_small_vfd"]}
            ])
        else:
            if chosen_tank == "tank_150" or (chosen_tank == "auto" and houses > 1):
                tank_name, tank_p = "Гидроаккумулятор 150-200 л", PRICES["tank_150"]
            else:
                tank_name, tank_p = "Гидроаккумулятор 80-100 л", PRICES["tank_80"]

            items.extend([
                {"name": tank_name, "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": tank_p},
                {"name": "Автоматика: реле + манометр + штуцер", "qty": 1, "unit": "компл.", "unit_key": "unit_set", "price": 5100}
            ])
    return items
