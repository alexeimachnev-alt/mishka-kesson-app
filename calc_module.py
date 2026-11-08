import os
import uuid
import urllib.parse
import requests
from telebot import types

PRIMARY_ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
SECOND_ADMIN_ID = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))
ADMIN_CHAT_IDS = [PRIMARY_ADMIN_ID, SECOND_ADMIN_ID]

GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()

ACTIVE_ORDERS = {}

# Прайс-лист склада «МИШКА» (руб.)
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
    "pnd32": {"unit": "м", "price": PRICES["pnd32"]},
    "pnd25": {"unit": "м", "price": PRICES["pnd25"]},
    "insul": {"unit": "м", "price": PRICES["insul"]},
    "heat_cable": {"unit": "м", "price": PRICES["heat_cable"]},
    "ball_valve": {"unit": "шт.", "price": PRICES["ball_valve"]},
    "fitting_32_1": {"unit": "шт.", "price": PRICES["fitting_32_1"]},
    "elbow_32": {"unit": "шт.", "price": PRICES["elbow_32"]},
    "unipak": {"unit": "шт.", "price": PRICES["unipak"]},
    "pipe110": {"unit": "м", "price": PRICES["pipe110"]},
    "insul110": {"unit": "м", "price": PRICES["insul110"]},
    "elbow110_45": {"unit": "шт.", "price": PRICES["elbow110_45"]},
    "tee110": {"unit": "шт.", "price": PRICES["tee110"]},
    "bacteria": {"unit": "шт.", "price": PRICES["bacteria"]},
    "drain_pipe": {"unit": "м", "price": PRICES["drain_pipe_classic"]},
    "geotextile": {"unit": "рул.", "price": PRICES["geotextile_roll"]},
    "well_cone": {"unit": "шт.", "price": PRICES["well_cone"]},
    "sand_trap": {"unit": "шт.", "price": PRICES["sand_trap"]},
    "leaf_grate": {"unit": "шт.", "price": PRICES["leaf_grate"]}
}

ITEM_TRANSLATIONS = {
    "pnd32": {"ru": "Труба ПНД 32 SDR11", "tj": "Қубури ПНД 32 SDR11", "uz": "PND 32 trubasi SDR11", "hy": "Խողովակ ՊՆԴ 32 SDR11", "ky": "ПНД 32 түтүгү SDR11"},
    "pnd25": {"ru": "Труба ПНД 25 (полив)", "tj": "Қубури ПНД 25 (обёрӣ)", "uz": "PND 25 trubasi (sug'orish)", "hy": "Խողովակ ՊՆԴ 25 (ոռոգում)", "ky": "ПНД 25 түтүгү (сугаруу)"},
    "insul": {"ru": "Утеплитель Энергофлекс 32", "tj": "Гармидиҳандаи Энергофлекс 32", "uz": "Energofleks izolyatsiyasi 32", "hy": "Ջերմամեկուսիչ Էներգոֆլեքս 32", "ky": "Энергофлекс жылуулагычы 32"},
    "heat_cable": {"ru": "Кабель греющий саморег.", "tj": "Кабели гармкунанда", "uz": "Isitish kabeli", "hy": "Տաքացնող մալուխ", "ky": "Жылытуучу кабель"},
    "ball_valve": {"ru": "Кран 1\" с американкой", "tj": "Крани 1\" бо американка", "uz": "Kran 1\" amerikanka bilan", "hy": "Ծորակ 1\" ամերիկանկայով", "ky": "Кран 1\" американка менен"},
    "fitting_32_1": {"ru": "Муфта ПНД 32х1\" НР", "tj": "Муфтаи ПНД 32х1\" БО", "uz": "Mufta PND 32x1\" TQ", "hy": "Կցորդիչ ՊՆԴ 32х1\" ԱՊ", "ky": "Муфта
