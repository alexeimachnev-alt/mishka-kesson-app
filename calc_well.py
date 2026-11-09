# -*- coding: utf-8 -*-
from constants import PRICES, KESSON_MODELS, TANK_CATALOG

def get_well_items(data):
    """
    Расчет обустройства скважины строго по утвержденным сметам от 09.11.2026:
    Динамически учитывает:
    - выбранную модель кессона (Мишка 1, 2, 3, 4, Long)
    - выбранный объем гидроаккумулятора (50, 80, 100, 150, 200, 300 л)
    - опуск насоса (от глубины depth)
    - трассу воды и кабеля (от расстояния distance)
    """
    depth = float(data.get("depth", 40))
    distances = data.get("distances", [15])
    distance = float(distances[0]) if distances else float(data.get("distance", 15))
    
    selected_kesson_key = data.get("chosen_kesson", "kesson_m1")
    equip_type = data.get("equip_type", "kesson_vfd")
    chosen_tank_key = str(data.get("chosen_tank", "tank_100"))

    # Определение кессона
    kesson_obj = KESSON_MODELS.get(selected_kesson_key, KESSON_MODELS["kesson_m1"])
    # Определение гидроаккумулятора
    tank_obj = TANK_CATALOG.get(chosen_tank_key, TANK_CATALOG["tank_100"])

    items = []

    # =========================================================================
    # 1. БАЗОВЫЙ НАБОР ОБУСТРОЙСТВА
    # =========================================================================
    if equip_type == "adapter":
        # Смета: Набор Адаптер 1.pdf
        items.extend([
            {"name": "Адаптер скважинный со сливным клапаном 1' TIM", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["adapter_tim_1"]},
            {"name": "Крышка скважины Джилекс КС 110-133", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["cover_adapter"]},
            {"name": "Муфта ПНД 32x1' HP Unidelta", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_1_hp"]},
            {"name": f"{tank_obj['name']} (в дом)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": tank_obj["price"]},
            {"name": "Реле давления AQUARIO PS-5-2 (вращ. гайка) Акварио", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pressure_switch"]},
            {"name": "Манометр радиальный 0-10 бар D53мм 1/4", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["manometer"]},
            {"name": "Подводка для воды угловая 1' 80см г/г ГИГАНТ", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hose_giant_1_80cm"]},
            {"name": "Кран шаровой Вн/Нр (бабочка) 1'", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_brass_1"]},
            {"name": "Тройник для труб с внутренней резьбой ВВВ 1' латунь Millenium", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_tee_1_bbb"]},
            {"name": "Тройник ВВВ 1/2' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_tee_1_2_bbb"]},
            {"name": "Ниппель НН 1' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1"]},
            {"name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_bushing_1_2_1_4"]},
            {"name": "Ниппель НН 1/2' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2"]},
            {"name": "Ниппель перех. НН 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2_1_4"]},
        ])

    elif equip_type == "kesson_vfd":
        # Смета: Набор_кессона_мишка_1_с_частотный_приоброзователь.pdf
        items.extend([
            {"name": kesson_obj["name"], "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": kesson_obj["price"]},
            {"name": "Труба полипропиленовая 32х5,4мм PN20 (цвет белый)", "qty": 4, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_ppr_32"]},
            {"name": "Отвод 90 PP-R Millennium 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_elbow_90_32"]},
            {"name": "Отвод 45 PP-R Millennium 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_elbow_45_32"]},
            {"name": "Заглушка PP-R Millennium 32мм (цвет белый)", "qty": 3, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_plug_32"]},
            {"name": "Кран шаровой PP-R VALFEX OPTIMA 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_ppr_32"]},
            {"name": "Кран шаровый VALFEX 1/2' водоразборный, ручка рычаг, с носиком под шланг", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_watering_1_2"]},
            {"name": "Муфта разъемная PP-R с внутренней резьбой Millennium 32-1' (цвет белый), американка", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_union_32_1"]},
            {"name": "Муфта комб. PP-R с наружной резьбой Millennium 32-1' (цвет белый), неразъемная", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_coupling_32_1_hp"]},
            {"name": "Тройник PP-R Millennium 32мм (цвет белый)", "qty": 3, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_tee_32"]},
            {"name": "Муфта PP-R Millennium 32мм (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_coupling_32"]},
            {"name": "Отвод комб. с внутренней резьбой 90 PP-R Millennium 32-1/2' (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_elbow_32_1_2_bp"]},
            {"name": "Отвод комб. с наружной резьбой 90 PP-R Millennium 32-1/2' (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_elbow_32_1_2_hp"]},
            {"name": "Подводка для воды прямая 1/2' 60см г/г", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hose_straight_1_2_60cm"]},
            {"name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_bushing_1_2_1_4"]},
            {"name": "Частотный преобразователь FIL-10 2.2KW 220V", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["vfd_fil10"]},
            {"name": "Гидроаккумулятор BELAMOS 8BW синий, подвесной", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["tank_8bw"]},
            {"name": "Тройник переходной комб. с внутренней резьбой PP-R Millennium 32x1/2'x32 (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_trans_tee_32_1_2_bp"]},
            {"name": "Тройник переходной комб. с внутренней резьбой PP-R Millennium 32x1'x32 (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_trans_tee_32_1_bp"]},
        ])

    else:
        # Смета: набор_Кессон_мишка_1_обвяска_на_гидробаке_и_РДМ_.pdf
        items.extend([
            {"name": kesson_obj["name"], "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": kesson_obj["price"]},
            {"name": "Труба полипропиленовая 32х5,4мм PN20 (цвет белый)", "qty": 4, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_ppr_32"]},
            {"name": tank_obj["name"], "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": tank_obj["price"]},
            {"name": "Отвод 90 PP-R Millennium 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_elbow_90_32"]},
            {"name": "Отвод 45 PP-R Millennium 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_elbow_45_32"]},
            {"name": "Заглушка PP-R Millennium 32мм (цвет белый)", "qty": 3, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_plug_32"]},
            {"name": "Кран шаровой PP-R VALFEX OPTIMA 32мм (цвет белый)", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_ppr_32"]},
            {"name": "Кран шаровый VALFEX 1/2' водоразборный, ручка рычаг, с носиком под шланг", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_watering_1_2"]},
            {"name": "Муфта разъемная PP-R с внутренней резьбой Millennium 32-1' (цвет белый), американка", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_union_32_1"]},
            {"name": "Муфта комб. PP-R с наружной резьбой Millennium 32-1' (цвет белый), неразъемная", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_coupling_32_1_hp"]},
            {"name": "Тройник переходной комб. с наружной резьбой PP-R Millennium 32x1'x32 (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_trans_tee_32_1_hp"]},
            {"name": "Тройник PP-R Millennium 32мм (цвет белый)", "qty": 3, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_tee_32"]},
            {"name": "Муфта PP-R Millennium 32мм (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_coupling_32"]},
            {"name": "Отвод комб. с внутренней резьбой 90 PP-R Millennium 32-1/2' (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_elbow_32_1_2_bp"]},
            {"name": "Отвод комб. с наружной резьбой 90 PP-R Millennium 32-1/2' (цвет белый)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["ppr_comb_elbow_32_1_2_hp"]},
            {"name": "Подводка для воды угловая 1' 80см г/г ГИГАНТ", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hose_giant_1_80cm"]},
            {"name": "Подводка для воды прямая 1/2' 60см г/г", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["hose_straight_1_2_60cm"]},
            {"name": "Реле давления AQUARIO PS-5-2 (вращ. гайка) Акварио", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pressure_switch"]},
            {"name": "Манометр радиальный 0-10 бар D53мм 1/4", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["manometer"]},
            {"name": "Тройник ВВВ 1/2' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_tee_1_2_bbb"]},
            {"name": "Ниппель переходной НН 1/2'x3/8' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2_3_8"]},
            {"name": "Ниппель перех. НН 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2_1_4"]},
            {"name": "Футорка НВ 1/2'x1/4' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_bushing_1_2_1_4"]},
            {"name": "Ниппель НН 1/2' (латунь)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["brass_nipple_1_2"]},
        ])

    # =========================================================================
    # 2. ОПУСК НАСОСА В СКВАЖИНУ (от глубины depth)
    # =========================================================================
    if equip_type != "adapter":
        items.extend([
            {"name": "Обратный клапан с металлическим седлом 1' г/ш Millennium", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["check_valve_1"]},
            {"name": "Муфта ПНД 32х1' HP Unidelta", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_1_hp"]},
            {"name": "Оголовок для скважины Джилекс ОСП 110-133/32", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["well_head_osp"]},
            {"name": "Угол ПНД 32x1' HP Unidelta", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_elbow_32_1_hp"]},
            {"name": "Зажим для троса, AISI 316 (А4), 4мм", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["cable_clamp_4mm"]},
            {"name": "Вилка электрическая прямая с заземлением белая 16A 250B", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["plug_16a"]},
        ])
    else:
        items.extend([
            {"name": "Обратный клапан с металлическим седлом 1' г/ш Millennium", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["check_valve_1"]},
            {"name": "Зажим для троса, AISI 316 (А4), 4мм", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["cable_clamp_4mm"]},
        ])

    pump_h = int(depth)
    items.extend([
        {"name": "Трос нержавеющая сталь 7х7 AISI 304, 3мм", "qty": pump_h, "unit": "м", "unit_key": "unit_m", "price": PRICES["rope_3mm_304"]},
        {"name": "Труба ПНД 32х3,0 SDR 11 (PN 16) бух. 250м (синяя)", "qty": pump_h, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_pnd_32"]},
    ])

    # =========================================================================
    # 3. ТРАССА В ДОМ (от расстояния distance)
    # =========================================================================
    dist_m = int(distance)
    items.extend([
        {"name": "Муфта ПНД 32x32 Unidelta", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_32"]},
        {"name": "Муфта ПНД редукц. 32х20 Unidelta", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_reduct_32_20"]},
        {"name": "Муфта ПНД 32х1' HP Unidelta", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_1_hp"]},
        {"name": "Кран шаровой Вн/Нр (бабочка) 1'", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["valve_brass_1"]},
        {"name": "Труба ПНД 32х3,0 SDR 11 (PN 16) бух. 250м (синяя)", "qty": dist_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_pnd_32"]},
        {"name": "Труба ПНД 20x2,0 SDR 11 (PN 16) бух. 500 м (синяя)", "qty": dist_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_pnd_20"]},
        {"name": "Кабель ПВС 3х2,5, белый, гибкий", "qty": dist_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["cable_pvs_3x2_5"]},
    ])

    return items
