# -*- coding: utf-8 -*-
"""
Единые константы и справочник цен склада «МИШКА»
Сметы согласованы от 09.11.2026.
"""

PRICES = {
    # --- КЕССОНЫ (ЛИНЕЙКА МИШКА) ---
    "kesson_m1": 41170.00,
    "kesson_m2": 52000.00,
    "kesson_m3": 65000.00,
    "kesson_m4": 82000.00,
    "kesson_long": 58000.00,

    # --- АДАПТЕР И КРЫШКА ---
    "adapter_tim_1": 3627.31,
    "cover_adapter": 3351.60,
    "well_head_osp": 1916.39,

    # --- ГИДРАНТЫ И КРАНЫ НЕЗАМЕРЗАЮЩИЕ ---
    "hydrant_belamos_1900": 5902.80,
    "hydrant_tim_2200": 7381.20,

    # --- АВТОМАТИКА И БАКИ ---
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

    # --- ТРУБЫ И КАБЕЛЬ (цена за 1 метр) ---
    "pipe_ppr_32": 151.42,
    "pipe_pnd_32": 78.00,
    "pipe_pnd_20": 42.54,
    "pipe_pnd_25": 48.46,
    "cable_pvs_3x2_5": 84.89,
    "rope_3mm_304": 19.20,

    # --- КРАНЫ И КЛАПАНЫ ---
    "valve_ppr_32": 180.93,
    "valve_watering_1_2": 436.13,
    "valve_brass_1": 874.43,
    "check_valve_1": 750.00,

    # --- ФИТИНГИ ПОЛИПРОПИЛЕН (PP-R) ---
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

    # --- ФИТИНГИ КОМПРЕССИОННЫЕ ПНД (Unidelta) ---
    "pnd_coupling_32_1_hp": 263.84,
    "pnd_elbow_32_1_hp": 319.60,
    "pnd_coupling_32_32": 472.60,
    "pnd_reduct_32_20": 435.20,

    # --- ПОДВОДКИ, ЛАТУНЬ И МЕЛОЧЕВКА ---
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
}

KESSON_MODELS = {
    "kesson_m1": {"name": "Кессон Мишка 1 (муфта 125/133) 1050x2000", "price": 41170.00},
    "kesson_m2": {"name": "Кессон Мишка 2 (муфта 125/133) 1300x2000", "price": 52000.00},
    "kesson_m3": {"name": "Кессон Мишка 3 (муфта 125/133) 1600x2000", "price": 65000.00},
    "kesson_m4": {"name": "Кессон Мишка 4 (муфта 125/133) 2000x2000", "price": 82000.00},
    "kesson_long": {"name": "Кессон Мишка LONG (муфта 125/133) H=2500", "price": 58000.00},
}

HYDRANT_CATALOG = {
    "hydrant_none": {"name": "Без дополнительного гидранта / крана", "price": 0.00},
    "hydrant_belamos_1900": {"name": "Гидрант незамерзающий GDR 1900 мм Беламос", "price": 5902.80},
    "hydrant_tim_2200": {"name": "Кран незамерзающий, 2.2м Гидрант W-HF0122 TIM", "price": 7381.20},
}

TANK_CATALOG = {
    "tank_8bw": {"name": "Гидроаккумулятор 8л BELAMOS 8BW (подвесной)", "price": 1183.20},
    "tank_24": {"name": "Гидроаккумулятор 24л BELAMOS 24СТ2 синий", "price": 1906.80},
    "tank_50_hit": {"name": "Гидроаккумулятор 50л Джилекс Г 50 «ХИТ»", "price": 3783.00},
    "tank_50vt": {"name": "Гидроаккумулятор 50л BELAMOS 50VT", "price": 3940.80},
    "tank_80vt": {"name": "Гидроаккумулятор 80л BELAMOS 80VT", "price": 7566.00},
    "tank_100vt": {"name": "Гидроаккумулятор 100л BELAMOS 100VT", "price": 8747.70},
    "tank_300_dzhileks": {"name": "Гидроаккумулятор 300л Джилекс 300 В", "price": 23049.00},
}

PUMP_CATALOG = {
    "pump_none": {"name": "Без насоса (свой или приобретается отдельно)", "price": 0.00},
    "pump_belamos_tf3_60": {"name": "Скважинный насос Belamos TF3-60 каб. 35м", "price": 11152.80},
    "pump_belamos_tf3_80": {"name": "Скважинный насос Belamos TF3-80 каб. 50м", "price": 14695.20},
    "pump_waterstry_3_90": {"name": "Скважиннный насос WATERSTRY 3\"3ST 3-90 H=108м", "price": 19484.72},
    "pump_waterstry_2_50": {"name": "Скважиннный насос WATERSTRY 3\"3ST 2-50 H=64м", "price": 12327.42},
    "pump_waterstry_2_120": {"name": "Скважиннный насос WATERSTRY 3\"3ST 2-120", "price": 19092.00},
    "pump_waterstry_2_85": {"name": "Скважиннный насос WATERSTRY 3\"3ST 2-85", "price": 13800.00},
    "pump_waterstry_1_60": {"name": "Скважиннный насос WATERSTRY 3\"3ST 1-60", "price": 11084.56},
    "pump_waterstry_2_100": {"name": "Скважиннный насос WATERSTRY 3\"3ST 2-100", "price": 16574.72},
    "pump_pw_tf3_80": {"name": "Насос скважинный Power Water PW TF3-80 каб.50м", "price": 14292.09},
    "pump_pw_tf3_60": {"name": "Насос скважинный Power Water PW TF3-60 каб.35м", "price": 11806.14},
    "pump_pw_tf3_40": {"name": "Насос скважинный Power Water PW TF3-40 каб.20м", "price": 9427.50},
    "pump_pw_tf3_110": {"name": "Насос скважинный Power Water PW TF3-110 каб.65м", "price": 18435.00},
    "pump_belamos_tf3_80_1_5m": {"name": "Скважинный насос Belamos TF3-80 каб. 1.5м", "price": 11152.80},
    "pump_belamos_tf3_40": {"name": "Скважинный насос Belamos TF3-40 каб. 20м", "price": 9771.60},
    "pump_belamos_tf3_200": {"name": "Скважинный насос Belamos TF3-200 каб. 80м", "price": 35043.60},
    "pump_belamos_tf3_150": {"name": "Скважинный насос Belamos TF3-150 каб. 80м", "price": 25555.20},
    "pump_belamos_tf3_110_65m": {"name": "Скважинный насос Belamos TF3-110 каб. 65м", "price": 18363.60},
    "pump_belamos_tf3_110_1_5m": {"name": "Скважинный насос Belamos TF3-110 каб. 1.5м", "price": 12730.80},
    "pump_aquario_75_1_5m": {"name": "Скважинный насос Aquario ASP1E-75-75 каб. 1.5м", "price": 14976.00},
    "pump_aquario_125_15m": {"name": "Скважинный насос Aquario ASP1E-125-75 каб. 15м", "price": 22959.73},
    "pump_aquario_100_60m": {"name": "Скважинный насос Aquario ASP1E-100-75 каб.60м", "price": 27251.63},
    "pump_aquario_55_35m": {"name": "Скважинный насос Aquario ASP1E-55-75 каб. 35м", "price": 16321.52},
}
