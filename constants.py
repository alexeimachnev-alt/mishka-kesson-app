# -*- coding: utf-8 -*-
"""
Единые константы и справочник цен склада «МИШКА»
Прайс кессонов с дилерской скидкой 40% и розничными ценами.
"""
import math

PRICES = {
    # --- КЕССОНЫ «МИШКА» (Дилерская цена со скидкой 40% по умолчанию) ---
    "kesson_m1_no_cuff": 39000.00,
    "kesson_m1": 40800.00,
    "kesson_m1_long_no_cuff": 42900.00,
    "kesson_m1_long": 55200.00,
    "kesson_m1_159": 57840.00,
    "kesson_m1_long_159": 60000.00,
    "kesson_m2_no_cuff": 53400.00,
    "kesson_m2": 55200.00,
    "kesson_m2_long_no_cuff": 57600.00,
    "kesson_m2_long": 72000.00,
    "kesson_m2_159": 75000.00,
    "kesson_m2_219": 77400.00,
    "kesson_m2_long_159": 78600.00,
    "kesson_m3_no_cuff": 81000.00,
    "kesson_m3": 83400.00,
    "kesson_m3_long_no_cuff": 96600.00,
    "kesson_m3_long": 99000.00,
    "kesson_m3_159": 101400.00,
    "kesson_m3_long_159": 138600.00,
    "kesson_m4": 141360.00,
    "kesson_m4_long_no_cuff": 143400.00,
    "kesson_m4_long": 170400.00,
    "kesson_m4_159": 172560.00,
    "kesson_m4_long_159": 174600.00,
    "kesson_long": 55200.00,
    "sgon_32_extruder": 380.00,

    # --- АДАПТЕР И КРЫШКА ---
    "adapter_tim_1": 3627.31,
    "cover_adapter": 3351.60,
    "well_head_osp": 1916.39,

    # --- АВТОМАТИКА И БАКИ ---
    "vfd_fil10": 7708.80,
    "tank_8bw": 1833,
    "tank_50": 5421,
    "tank_80": 7151,
    "tank_100": 8749,
    "tank_150": 13901,
    "tank_200": 18201,
    "tank_300": 26501,
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
    "pnd_tee_32": 645.00,

    # --- ПОДВОДКИ, ЛАТУНЬ, ГРЕЮЩИЙ КАБЕЛЬ И ГИДРАНТЫ ---
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
    "heat_cable": 350.00,
    "heat_cable_kit": 1400.00,
    "hydrant_gdr_1900": 5902.80,
    "tap_non_freezing_tim": 7381.20,

    # --- НАСОСЫ СКВАЖИННЫЕ И ДРЕНАЖНЫЕ ---
    "pump_waterstry_3_90": 19484.72,
    "pump_waterstry_2_50": 12327.42,
    "pump_waterstry_2_120": 19092.00,
    "pump_waterstry_2_85": 13800.00,
    "pump_waterstry_1_60": 11084.56,
    "pump_waterstry_2_100": 16574.72,
    "pump_pw_tf3_80": 14292.09,
    "pump_pw_tf3_60": 11806.14,
    "pump_pw_tf3_40": 9427.50,
    "pump_pw_tf3_110": 18435.00,
    "pump_belamos_tf3_80_50m": 14695.20,
    "pump_belamos_tf3_80_1_5m": 11152.80,
    "pump_belamos_tf3_60": 20350.00,
    "pump_belamos_tf3_40": 9771.60,
    "pump_belamos_tf3_200": 35043.60,
    "pump_belamos_tf3_150": 25555.20,
    "pump_belamos_tf3_110_65m": 18363.60,
    "pump_belamos_tf3_110_1_5m": 12730.80,
    "pump_aquario_75_1_5m": 14976.00,
    "pump_aquario_125_15m": 22959.73,
    "pump_aquario_100_60m": 27251.63,
    "pump_aquario_55_35m": 16321.52,
    "pump_belamos_dwp_180": 6083.75,
    "pump_belamos_omega_25": 3064.80,
}

def round_length_custom(val) -> int:
    """
    Правило округления длины труб, кабеля и троса:
    - Если <= 15 м -> строго 15 м
    - Если > 15 м -> округление вверх до ближайшего числа, кратного 5
    """
    try:
        v = float(val)
    except (ValueError, TypeError):
        v = 15.0
    if v <= 15:
        return 15
    return int(math.ceil(v / 5.0) * 5)

KESSON_MODELS = {
    "kesson_m1_no_cuff": {"name": "Кессон Мишка 1 без муфты (2000х1050)", "price": 39000.00, "dealer_price": 39000.00, "retail_price": 65000.00},
    "kesson_m1": {"name": "Кессон Мишка 1 (2000х1050)", "price": 40800.00, "dealer_price": 40800.00, "retail_price": 68000.00},
    "kesson_m1_long_no_cuff": {"name": "Кессон Мишка 1 - Long без муфты (2500х1050)", "price": 42900.00, "dealer_price": 42900.00, "retail_price": 71500.00},
    "kesson_m1_long": {"name": "Кессон Мишка 1 - Long (2500х1050)", "price": 55200.00, "dealer_price": 55200.00, "retail_price": 92000.00},
    "kesson_m1_159": {"name": "Кессон Мишка 1 (муфта 159, 2000х1050)", "price": 57840.00, "dealer_price": 57840.00, "retail_price": 96400.00},
    "kesson_m1_long_159": {"name": "Кессон Мишка 1 - Long (муфта 159, 2500х1050)", "price": 60000.00, "dealer_price": 60000.00, "retail_price": 100000.00},
    "kesson_m2_no_cuff": {"name": "Кессон Мишка 2 без муфты (2000х1300)", "price": 53400.00, "dealer_price": 53400.00, "retail_price": 89000.00},
    "kesson_m2": {"name": "Кессон Мишка 2 (2000х1300)", "price": 55200.00, "dealer_price": 55200.00, "retail_price": 92000.00},
    "kesson_m2_long_no_cuff": {"name": "Кессон Мишка 2 - Long без муфты (2500х1300)", "price": 57600.00, "dealer_price": 57600.00, "retail_price": 96000.00},
    "kesson_m2_long": {"name": "Кессон Мишка 2 - Long (2500х1300)", "price": 72000.00, "dealer_price": 72000.00, "retail_price": 120000.00},
    "kesson_m2_159": {"name": "Кессон Мишка 2 (муфта 159, 2000х1300)", "price": 75000.00, "dealer_price": 75000.00, "retail_price": 125000.00},
    "kesson_m2_219": {"name": "Кессон Мишка 2 (муфта 219, 2000х1300)", "price": 77400.00, "dealer_price": 77400.00, "retail_price": 129000.00},
    "kesson_m2_long_159": {"name": "Кессон Мишка 2 - Long (муфта 159, 2500х1300)", "price": 78600.00, "dealer_price": 78600.00, "retail_price": 131000.00},
    "kesson_m3_no_cuff": {"name": "Кессон Мишка 3 без муфты (2000х1600)", "price": 81000.00, "dealer_price": 81000.00, "retail_price": 135000.00},
    "kesson_m3": {"name": "Кессон Мишка 3 (2000х1600)", "price": 83400.00, "dealer_price": 83400.00, "retail_price": 139000.00},
    "kesson_m3_long_no_cuff": {"name": "Кессон Мишка 3 - Long без муфты (2500х1600)", "price": 96600.00, "dealer_price": 96600.00, "retail_price": 161000.00},
    "kesson_m3_long": {"name": "Кессон Мишка 3 - Long (2500х1600)", "price": 99000.00, "dealer_price": 99000.00, "retail_price": 165000.00},
    "kesson_m3_159": {"name": "Кессон Мишка 3 (муфта 159, 2000х1600)", "price": 101400.00, "dealer_price": 101400.00, "retail_price": 169000.00},
    "kesson_m3_long_159": {"name": "Кессон Мишка 3 - Long (муфта 159, 2500х1600)", "price": 138600.00, "dealer_price": 138600.00, "retail_price": 231000.00},
    "kesson_m4": {"name": "Кессон Мишка 4 (2000х2100)", "price": 141360.00, "dealer_price": 141360.00, "retail_price": 235600.00},
    "kesson_m4_long_no_cuff": {"name": "Кессон Мишка 4 - Long без муфты (2500х2100)", "price": 143400.00, "dealer_price": 143400.00, "retail_price": 239000.00},
    "kesson_m4_long": {"name": "Кессон Мишка 4 - Long (2500х2100)", "price": 170400.00, "dealer_price": 170400.00, "retail_price": 284000.00},
    "kesson_m4_159": {"name": "Кессон Мишка 4 (муфта 159, 2000х2100)", "price": 172560.00, "dealer_price": 172560.00, "retail_price": 287600.00},
    "kesson_m4_long_159": {"name": "Кессон Мишка 4 - Long (муфта 159, 2500х2100)", "price": 174600.00, "dealer_price": 174600.00, "retail_price": 291000.00},
    "kesson_long": {"name": "Кессон Мишка 1 - Long (2500х1050)", "price": 55200.00, "dealer_price": 55200.00, "retail_price": 92000.00},
}

TANK_CATALOG = {
    "tank_8bw": {"name": "Гидроаккумулятор 8л BELAMOS 8BW (подвесной)", "price": 1184},
    "tank_24": {"name": "Гидроаккумулятор 24л BELAMOS 24СТ2 синий", "price": 1908},
    "tank_50_hit": {"name": "Гидроаккумулятор 50л Джилекс Г 50 «ХИТ»", "price": 3784},
    "tank_50vt": {"name": "Гидроаккумулятор 50л BELAMOS 50VT", "price": 3942},
    "tank_80vt": {"name": "Гидроаккумулятор 80л BELAMOS 80VT", "price": 7567},
    "tank_100vt": {"name": "Гидроаккумулятор 100л BELAMOS 100VT", "price": 8749},
    "tank_300_dzhileks": {"name": "Гидроаккумулятор 300л Джилекс 300 В", "price": 23050},
}

PUMP_CATALOG = {
    "pump_none": {"name": "Без насоса (свой или приобретается отдельно)", "price": 0.00},
    "pump_waterstry_3_90": {"name": 'Скважинный насос WATERSTRY 3" 3ST 3-90 (Н=108м, 5.4м3/час, каб. 1м, 1.5kW, 230V)', "price": 19484.72},
    "pump_waterstry_2_50": {"name": 'Скважинный насос WATERSTRY 3" 3ST 2-50 (Н=64м, 3.6м3/час, 0.55kW, 230V)', "price": 12327.42},
    "pump_waterstry_2_120": {"name": 'Скважинный насос WATERSTRY 3" 3ST 2-120 тм (1.5kW, 230V)', "price": 19092.00},
    "pump_waterstry_2_85": {"name": 'Скважинный насос WATERSTRY 3" 3ST 2-85 (0.92kW, 230V)', "price": 13800.00},
    "pump_waterstry_1_60": {"name": 'Скважинный насос WATERSTRY 3" 3ST 1-60 тм (Н=64м, 2.7м3/ч, каб. 1м, 0.37kW, 230V)', "price": 11084.56},
    "pump_waterstry_2_100": {"name": 'Скважинный насос WATERSTRY 3" 3ST 2-100 тм (1.1kW, 230V)', "price": 16574.72},
    "pump_pw_tf3_80": {"name": 'Насос скважинный Power Water PW TF3-80 2.0 (каб. 50м, 85м, 3м3/час)', "price": 14292.09},
    "pump_pw_tf3_60": {"name": 'Насос скважинный Power Water PW TF3-60 2.0 (каб. 35м, 65м, 3м3/час)', "price": 11806.14},
    "pump_pw_tf3_40": {"name": 'Насос скважинный Power Water PW TF3-40 2.0 (каб. 20м, 45м, 3м3/час)', "price": 9427.50},
    "pump_pw_tf3_110": {"name": 'Насос скважинный Power Water PW TF3-110 2.0 (каб. 65м, 110м, 3м3/час)', "price": 18435.00},
    "pump_belamos_tf3_80_50m": {"name": 'Насос скважинный Belamos TF3-80 (2.7 м3/час, 45 л/мин, Н-80 м, d-78 мм, каб. 50 м)', "price": 14695.20},
    "pump_belamos_tf3_80_1_5m": {"name": 'Насос скважинный Belamos TF3-80 (2.7 м3/час, 45 л/мин, Н-80 м, d-78 мм, каб. 1.5 м)', "price": 11152.80},
    "pump_belamos_tf3_60": {"name": 'Насос скважинный Belamos TF3-60 (2.7 м3/час, 45 л/мин, Н-60 м, d-78 мм, каб. 35м)', "price": 20350.00},
    "pump_belamos_tf3_40": {"name": 'Насос скважинный Belamos TF3-40 (2.7 м3/час, 45 л/мин, Н-40 м, d-78 мм, каб. 20 м)', "price": 9771.60},
    "pump_belamos_tf3_200": {"name": 'Насос скважинный Belamos TF3-200 (2.7 м3/час, 45 л/мин, Н-200 м, d-78 мм, каб. 80 м)', "price": 35043.60},
    "pump_belamos_tf3_150": {"name": 'Насос скважинный Belamos TF3-150 (2.7 м3/час, 45 л/мин, Н-150 м, d-78 мм, каб. 80м)', "price": 25555.20},
    "pump_belamos_tf3_110_65m": {"name": 'Насос скважинный Belamos TF3-110 (2.7 м3/час, 45 л/мин, Н-110 м, d-78 мм, каб. 65 м)', "price": 18363.60},
    "pump_belamos_tf3_110_1_5m": {"name": 'Насос скважинный Belamos TF3-110 (2.7 м3/час, 45 л/мин, Н-110 м, d-78 мм, каб. 1.5 м)', "price": 12730.80},
    "pump_aquario_75_1_5m": {"name": 'Насос скважинный Aquario ASP1E-75-75 (встр. конд., каб. 1.5м, Q-50 л/мин, Н-85м)', "price": 14976.00},
    "pump_aquario_125_15m": {"name": 'Насос скважинный Aquario ASP1E-125-75 (встр. конд., каб. 15м, Q-50 л/мин, Н-135м)', "price": 22959.73},
    "pump_aquario_100_60m": {"name": 'Насос скважинный Aquario ASP1E-100-75 (встр. конд., каб. 60м, Q-50 л/мин, Н-110м)', "price": 27251.63},
    "pump_aquario_55_35m": {"name": 'Насос погружной скважинный Aquario ASP1E-55-75 (3 м3/час, 50 л/мин, Н-60 м, d-76 мм, каб. 35 м)', "price": 16321.52},
    "pump_belamos_dwp_180": {"name": 'Насос дренажный Belamos DWP 180 (116 л/мин, каб. 10м, Н-6м, с измельчителем для грязной воды)', "price": 6083.75},
    "pump_belamos_omega_25": {"name": 'Насос погружной Belamos Omega 25 (83 л/мин, Н-6м, каб. 6м)', "price": 3064.80},
    "pump_belamos_tf3_80": {"name": 'Насос скважинный Belamos TF3-80 (2.7 м3/час, 45 л/мин, Н-80 м, d-78 мм, каб. 50 м)', "price": 14695.20},
}
