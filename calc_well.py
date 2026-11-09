# -*- coding: utf-8 -*-
from constants import PRICES

def get_well_items(data):
    """
    Расчет обустройства скважины строго по утвержденным сметам от 09.11.2026:
    1. Базовый комплект обустройства (ЧП / ГА / Адаптер)
    2. Опуск насоса в скважину (рассчитывается от глубины depth)
    3. Трасса воды и кабеля в дом (рассчитывается от расстояния distance)
    """
    depth = float(data.get("depth", 40))
    distances = data.get("distances", [15])
    distance = float(distances[0]) if distances else float(data.get("distance", 15))
    selected_kesson = data.get("chosen_kesson", "auto")
    equip_type = data.get("equip_type", "kesson_vfd")
    chosen_tank = str(data.get("chosen_tank", "tank_100"))

    tank_catalog = {
        "tank_50": ("Гидроаккумулятор 50VT BELAMOS", PRICES.get("tank_50", 5420.00)),
        "tank_80": ("Гидроаккумулятор 80VT BELAMOS", PRICES.get("tank_80", 7150.00)),
        "tank_100": ("Гидроаккумулятор 100VT BELAMOS", PRICES.get("tank_100", 8747.70)),
        "tank_150": ("Гидроаккумулятор 150VT BELAMOS", PRICES.get("tank_150", 13900.00)),
        "tank_200": ("Гидроаккумулятор 200VT BELAMOS", PRICES.get("tank_200", 18200.00)),
        "tank_300": ("Гидроаккумулятор 300VT BELAMOS", PRICES.get("tank_300", 26500.00)),
    }

    items = []

    # 1. БАЗОВЫЙ КОМПЛЕКТ ОБУСТРОЙСТВА
    if equip_type == "adapter":
        t_name, t_price = tank_catalog.get(chosen_tank, tank_catalog["tank_100"])
        items.extend([
            {"name": "Адаптер скважинный со сливным клапаном 1' TIM", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["adapter_tim_1"]},
            {"name": "Крышка скважины Джилекс КС 110-133", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["cover_adapter"]},
            {"name": "Муфта ПНД 32x1' HP Unidelta", "qty": 4, "unit": "шт", "unit_key": "unit_pcs", "price": PRICES["pnd_coupling_32_1_hp"]},
            {"name": f"{t_name} (в дом)", "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": t_price},
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
        k_name = "Кессон Мишка 1 (муфта 125/133) 1050x2000"
        k_price = PRICES["kesson_m1"]
        if "Мишка 2" in selected_kesson:
            k_name, k_price = "Кессон Мишка 2 (муфта 125/133) 1300x2000", PRICES["kesson_m2"]
        elif "Мишка 3" in selected_kesson:
            k_name, k_price = "Кессон Мишка 3 (муфта 125/133) 1600x2000", PRICES["kesson_m3"]

        items.extend([
            {"name": k_name, "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": k_price},
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
        k_name = "Кессон Мишка 1 (муфта 125/133) 1050x2000"
        k_price = PRICES["kesson_m1"]
        if "Мишка 2" in selected_kesson:
            k_name, k_price = "Кессон Мишка 2 (муфта 125/133) 1300x2000", PRICES["kesson_m2"]
        elif "Мишка 3" in selected_kesson:
            k_name, k_price = "Кессон Мишка 3 (муфта 125/133) 1600x2000", PRICES["kesson_m3"]

        t_name, t_price = tank_catalog.get(chosen_tank, tank_catalog["tank_100"])

        items.extend([
            {"name": k_name, "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": k_price},
            {"name": "Труба полипропиленовая 32х5,4мм PN20 (цвет белый)", "qty": 4, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe_ppr_32"]},
            {"name": t_name, "qty": 1, "unit": "шт", "unit_key": "unit_pcs", "price": t_price},
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

    # 2. ОПУСК НАСОСА В СКВАЖИНУ (от глубины depth)
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

    # 3. ТРАССА В ДОМ (от расстояния distance)
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
