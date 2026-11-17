# -*- coding: utf-8 -*-
from constants import PRICES, KESSON_MODELS, TANK_CATALOG, PUMP_CATALOG, round_length_custom

def get_well_items(data):
    raw_depth = float(data.get("depth", 40))
    houses_count = int(data.get("houses_count", 1))
    distances = data.get("distances")
    if not distances or not isinstance(distances, list):
        d1 = float(data.get("distance", 15))
        if houses_count == 2:
            d2 = float(data.get("distance_2", 15))
            distances = [d1, d2]
        else:
            distances = [d1]
    else:
        distances = [float(x) for x in distances[:houses_count]]

    # 1. Применяем правило округления (<=15 -> 15; >15 -> вверх кратно 5)
    pump_h = round_length_custom(raw_depth)
    rounded_dists = [round_length_custom(d) for d in distances]
    total_dist_m = sum(rounded_dists)

    selected_kesson_key = data.get("chosen_kesson", "kesson_m1")
    price_tier = data.get("price_tier", "dealer")  # 'dealer' (скидка 40%) или 'retail' (розница)
    equip_type = data.get("equip_type", "kesson_vfd")
    chosen_tank_key = str(data.get("chosen_tank", "tank_100vt"))
    chosen_pump_key = str(data.get("chosen_pump", "pump_none"))
    include_heat_cable = bool(data.get("include_heat_cable", False))
    heat_cable_len = float(data.get("heat_cable_length", 3 * len(rounded_dists)))
    include_adapter_hydrants = bool(data.get("include_adapter_hydrants", False))
    sgon_32_qty = int(data.get("sgon_32_qty", 0))

    base_kesson_obj = KESSON_MODELS.get(selected_kesson_key, KESSON_MODELS["kesson_m1"])
    kesson_price = base_kesson_obj.get("retail_price", base_kesson_obj["price"]) if price_tier == "retail" else base_kesson_obj.get("dealer_price", base_kesson_obj["price"])
    tier_label = "Розн." if price_tier == "retail" else "Дилер -40%"
    kesson_obj = {"name": f"{base_kesson_obj['name']} [{tier_label}]", "price": kesson_price}
    tank_obj = TANK_CATALOG.get(chosen_tank_key, TANK_CATALOG.get("tank_100vt", {"name": "Гидробак", "price": 0}))
    pump_obj = PUMP_CATALOG.get(chosen_pump_key, PUMP_CATALOG["pump_none"])

    items = []

    if pump_obj["price"] > 0:
        items.append({
            "item_key": chosen_pump_key, "name": pump_obj["name"], "qty": 1, 
            "unit": "шт", "unit_key": "unit_pcs", "price": pump_obj["price"]
        })

    if equip_type == "adapter":
        items.extend([
            {"item_key": "adapter_tim_1", "name": "Адаптер скважинный со сливным клапаном 1' TIM", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["adapter_tim_1"]},
            {"item_key": "cover_adapter", "name": "Крышка скважины Джилекс КС 110-133", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["cover_adapter"]},
            {"item_key": "pnd_coupling_32_1_hp", "name": "Муфта ПНД 32x1' HP Unidelta", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_1_hp"]},
            {"item_key": chosen_tank_key, "name": f"{tank_obj['name']} (в дом)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": tank_obj["price"]},
            {"item_key": "pressure_switch", "name": "Реле давления AQUARIO PS-5-2 (вращ. гайка) Акварио", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pressure_switch"]},
            {"item_key": "manometer", "name": "Манометр радиальный 0-10 бар D53мм 1/4", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["manometer"]},
            {"item_key": "hose_giant_1_80cm", "name": "Подводка для воды угловая 1' 80см г/г ГИГАНТ", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hose_giant_1_80cm"]},
            {"item_key": "valve_brass_1", "name": "Кран шаровой Вн/Нр (бабочка) 1'", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_brass_1"]},
            {"item_key": "brass_tee_1_bbb", "name": "Тройник для труб с внутренней резьбой ВВВ 1' латунь Millenium", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_tee_1_bbb"]},
            {"item_key": "brass_tee_1_2_bbb", "name": "Тройник ВВВ 1/2' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_tee_1_2_bbb"]},
            {"item_key": "brass_nipple_1", "name": "Ниппель НН 1' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1"]},
            {"item_key": "brass_bushing_1_2_1_4", "name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_bushing_1_2_1_4"]},
            {"item_key": "brass_nipple_1_2", "name": "Ниппель НН 1/2' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2"]},
            {"item_key": "brass_nipple_1_2_1_4", "name": "Ниппель перех. НН 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2_1_4"]},
        ])

        # 4. Дополнительные опции для набора со скважинным адаптером (незамерзающие гидранты/краны)
        if include_adapter_hydrants:
            items.extend([
                {"item_key": "hydrant_gdr_1900", "name": 'Гидрант незамерзающий GDR " 1900 мм Беламос', "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hydrant_gdr_1900"]},
                {"item_key": "tap_non_freezing_tim", "name": "Кран незамерзающий, 2.2м Гидрант W-HF0122 TIM", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["tap_non_freezing_tim"]},
            ])

    elif equip_type == "kesson_vfd":
        items.extend([
            {"item_key": selected_kesson_key, "name": kesson_obj["name"], "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": kesson_obj["price"]},
            {"item_key": "pipe_ppr_32", "name": "Труба полипропиленовая 32х5,4мм PN20 (цвет белый)", "qty": 4, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_ppr_32"]},
            {"item_key": "ppr_elbow_90_32", "name": "Отвод 90 PP-R Millennium 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_elbow_90_32"]},
            {"item_key": "ppr_elbow_45_32", "name": "Отвод 45 PP-R Millennium 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_elbow_45_32"]},
            {"item_key": "ppr_plug_32", "name": "Заглушка PP-R Millennium 32мм (цвет белый)", "qty": 3, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_plug_32"]},
            {"item_key": "valve_ppr_32", "name": "Кран шаровой PP-R VALFEX OPTIMA 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_ppr_32"]},
            {"item_key": "valve_watering_1_2", "name": "Кран шаровый VALFEX 1/2' водоразборный, ручка рычаг, с носиком под шланг", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_watering_1_2"]},
            {"item_key": "ppr_union_32_1", "name": "Муфта разъемная PP-R с внутренней резьбой Millennium 32-1' (цвет белый), американка", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_union_32_1"]},
            {"item_key": "ppr_comb_coupling_32_1_hp", "name": "Муфта комб. PP-R с наружной резьбой Millennium 32-1' (цвет белый), неразъемная", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_coupling_32_1_hp"]},
            {"item_key": "ppr_tee_32", "name": "Тройник PP-R Millennium 32мм (цвет белый)", "qty": 3, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_tee_32"]},
            {"item_key": "ppr_coupling_32", "name": "Муфта PP-R Millennium 32мм (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_coupling_32"]},
            {"item_key": "ppr_comb_elbow_32_1_2_bp", "name": "Отвод комб. с внутренней резьбой 90 PP-R Millennium 32-1/2' (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_elbow_32_1_2_bp"]},
            {"item_key": "ppr_comb_elbow_32_1_2_hp", "name": "Отвод комб. с наружной резьбой 90 PP-R Millennium 32-1/2' (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_elbow_32_1_2_hp"]},
            {"item_key": "hose_straight_1_2_60cm", "name": "Подводка для воды прямая 1/2' 60см г/г", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hose_straight_1_2_60cm"]},
            {"item_key": "brass_bushing_1_2_1_4", "name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_bushing_1_2_1_4"]},
            {"item_key": "vfd_fil10", "name": "Частотный преобразователь FIL-10 2.2KW 220V", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["vfd_fil10"]},
            {"item_key": chosen_tank_key, "name": tank_obj["name"], "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": tank_obj["price"]},
            {"item_key": "ppr_trans_tee_32_1_2_bp", "name": "Тройник переходной комб. с внутренней резьбой PP-R Millennium 32x1/2'x32 (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_trans_tee_32_1_2_bp"]},
            {"item_key": "ppr_trans_tee_32_1_bp", "name": "Тройник переходной комб. с внутренней резьбой PP-R Millennium 32x1'x32 (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_trans_tee_32_1_bp"]},
        ])

    else:
        items.extend([
            {"item_key": selected_kesson_key, "name": kesson_obj["name"], "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": kesson_obj["price"]},
            {"item_key": "pipe_ppr_32", "name": "Труба полипропиленовая 32х5,4мм PN20 (цвет белый)", "qty": 4, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_ppr_32"]},
            {"item_key": chosen_tank_key, "name": tank_obj["name"], "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": tank_obj["price"]},
            {"item_key": "ppr_elbow_90_32", "name": "Отвод 90 PP-R Millennium 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_elbow_90_32"]},
            {"item_key": "ppr_elbow_45_32", "name": "Отвод 45 PP-R Millennium 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_elbow_45_32"]},
            {"item_key": "ppr_plug_32", "name": "Заглушка PP-R Millennium 32мм (цвет белый)", "qty": 3, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_plug_32"]},
            {"item_key": "valve_ppr_32", "name": "Кран шаровой PP-R VALFEX OPTIMA 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_ppr_32"]},
            {"item_key": "valve_watering_1_2", "name": "Кран шаровый VALFEX 1/2' водоразборный, ручка рычаг, с носиком под шланг", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_watering_1_2"]},
            {"item_key": "ppr_union_32_1", "name": "Муфта разъемная PP-R с внутренней резьбой Millennium 32-1' (цвет белый), американка", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_union_32_1"]},
            {"item_key": "ppr_comb_coupling_32_1_hp", "name": "Муфта комб. PP-R с наружной резьбой Millennium 32-1' (цвет белый), неразъемная", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_coupling_32_1_hp"]},
            {"item_key": "ppr_trans_tee_32_1_hp", "name": "Тройник переходной комб. с наружной резьбой PP-R Millennium 32x1'x32 (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_trans_tee_32_1_hp"]},
            {"item_key": "ppr_tee_32", "name": "Тройник PP-R Millennium 32мм (цвет белый)", "qty": 3, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_tee_32"]},
            {"item_key": "ppr_coupling_32", "name": "Муфта PP-R Millennium 32мм (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_coupling_32"]},
            {"item_key": "ppr_comb_elbow_32_1_2_bp", "name": "Отвод комб. с внутренней резьбой 90 PP-R Millennium 32-1/2' (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_elbow_32_1_2_bp"]},
            {"item_key": "ppr_comb_elbow_32_1_2_hp", "name": "Отвод комб. с наружной резьбой 90 PP-R Millennium 32-1/2' (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_elbow_32_1_2_hp"]},
            {"item_key": "hose_giant_1_80cm", "name": "Подводка для воды угловая 1' 80см г/г ГИГАНТ", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hose_giant_1_80cm"]},
            {"item_key": "hose_straight_1_2_60cm", "name": "Подводка для воды прямая 1/2' 60см г/г", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hose_straight_1_2_60cm"]},
            {"item_key": "pressure_switch", "name": "Реле давления AQUARIO PS-5-2 (вращ. гайка) Акварио", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pressure_switch"]},
            {"item_key": "manometer", "name": "Манометр радиальный 0-10 бар D53мм 1/4", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["manometer"]},
            {"item_key": "brass_tee_1_2_bbb", "name": "Тройник ВВВ 1/2' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_tee_1_2_bbb"]},
            {"item_key": "brass_nipple_1_2_3_8", "name": "Ниппель переходной НН 1/2'x3/8' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2_3_8"]},
            {"item_key": "brass_nipple_1_2_1_4", "name": "Ниппель перех. НН 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2_1_4"]},
            {"item_key": "brass_bushing_1_2_1_4", "name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_bushing_1_2_1_4"]},
            {"item_key": "brass_nipple_1_2", "name": "Ниппель НН 1/2' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2"]},
        ])

    # Опуск насоса
    if equip_type != "adapter":
        items.extend([
            {"item_key": "check_valve_1", "name": "Обратный клапан с металлическим седлом 1' г/ш Millennium", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["check_valve_1"]},
            {"item_key": "pnd_coupling_32_1_hp", "name": "Муфта ПНД 32х1' HP Unidelta", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_1_hp"]},
            {"item_key": "well_head_osp", "name": "Оголовок для скважины Джилекс ОСП 110-133/32", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["well_head_osp"]},
            {"item_key": "pnd_elbow_32_1_hp", "name": "Угол ПНД 32x1' HP Unidelta", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_elbow_32_1_hp"]},
            {"item_key": "cable_clamp_4mm", "name": "Зажим для троса, AISI 316 (А4), 4мм", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["cable_clamp_4mm"]},
            {"item_key": "plug_16a", "name": "Вилка электрическая прямая с заземлением белая 16A 250B", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["plug_16a"]},
        ])
    else:
        items.extend([
            {"item_key": "check_valve_1", "name": "Обратный клапан с металлическим седлом 1' г/ш Millennium", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["check_valve_1"]},
            {"item_key": "cable_clamp_4mm", "name": "Зажим для троса, AISI 316 (А4), 4мм", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["cable_clamp_4mm"]},
        ])

    # Трос и труба ПНД 32х3,0 (сумма: округленная глубина насоса + сумма округленных трасс до каждого дома)
    total_pipe_pnd_32 = pump_h + total_dist_m
    items.extend([
        {"item_key": "rope_3mm_304", "name": "Трос нержавеющая сталь 7x7 AISI 304, 3мм", "qty": pump_h, "unit": "м", "unit_key": "unit_m", "price": PRICES["rope_3mm_304"]},
        {"item_key": "pipe_pnd_32", "name": "Труба ПНД 32х3,0 SDR 11 (PN 16) бух.250м (синяя)", "qty": total_pipe_pnd_32, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_pnd_32"]},
    ])

    # Трасса и фитинги (для 1 или 2 домов)
    reduct_32_20_qty = 2 if len(rounded_dists) >= 2 else 1
    items.extend([
        {"item_key": "pnd_coupling_32_32", "name": "Муфта ПНД 32x32 Unidelta", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_32"]},
        {"item_key": "pnd_reduct_32_20", "name": "Муфта ПНД редукц. 32х20 Unidelta", "qty": reduct_32_20_qty, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_reduct_32_20"]},
        {"item_key": "pnd_coupling_32_1_hp", "name": "Муфта ПНД 32х1' HP Unidelta", "qty": len(rounded_dists), "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_1_hp"]},
        {"item_key": "valve_brass_1", "name": "Кран шаровой Вн/Нр (бабочка) 1'", "qty": len(rounded_dists), "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_brass_1"]},
        {"item_key": "pipe_pnd_20", "name": "Труба ПНД 20x2,0 SDR 11 (PN 16) бух. 500 м (синяя)", "qty": total_dist_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_pnd_20"]},
        {"item_key": "cable_pvs_3x2_5", "name": "Кабель ПВС 3х2,5, белый, гибкий", "qty": total_dist_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["cable_pvs_3x2_5"]},
    ])

    # 2. Если выбрано 2 дома: добавляем Тройник компрессионный ПНД 32х32х32
    if len(rounded_dists) >= 2:
        items.append({
            "item_key": "pnd_tee_32",
            "name": "Тройник компрессионный ПНД 32х32х32 Unidelta (разветвитель на 2 дома)",
            "qty": 1,
            "unit": "шт",
            "unit_key": "unit_pcs",
            "price": PRICES["pnd_tee_32"]
        })

    # 3. Если включен греющий кабель -> обязательно добавляем Монтажный набор (1400 руб. за каждый ввод/дом)
    if include_heat_cable and heat_cable_len > 0:
        items.extend([
            {"item_key": "heat_cable", "name": "Кабель греющий саморегулирующийся (защита от замерзания)", "qty": heat_cable_len, "unit": "м", "unit_key": "unit_m", "price": PRICES["heat_cable"]},
            {"item_key": "heat_cable_kit", "name": "Монтажный набор для греющего кабеля (обязательный комплект)", "qty": len(rounded_dists), "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["heat_cable_kit"]},
        ])

    if equip_type != "adapter" and sgon_32_qty > 0:
        items.insert(1 if pump_obj["price"] == 0 else 2, {
            "item_key": "sgon_32_extruder",
            "name": "Сгон 32 мм (экструдерная пайка) [Дилер: По согласованию / Розн. 380 ₽]",
            "qty": sgon_32_qty,
            "unit": "шт",
            "unit_key": "unit_pcs",
            "price": PRICES["sgon_32_extruder"]
        })

    # Подключаем пользовательские позиции из админ-панели (если добавлены в базовый комплект)
    try:
        from admin_config import CUSTOM_BUNDLE_ITEMS
        for cb in CUSTOM_BUNDLE_ITEMS:
            t = cb.get("target", "all_well")
            if t == "all_well" or t == equip_type:
                items.append({
                    "item_key": cb["code"],
                    "name": cb["name"],
                    "qty": cb.get("qty", 1),
                    "unit": cb.get("unit", "шт"),
                    "unit_key": "unit_m" if cb.get("unit") == "м" else "unit_pcs",
                    "price": cb["price"]
                })
    except Exception:
        pass

    return items
