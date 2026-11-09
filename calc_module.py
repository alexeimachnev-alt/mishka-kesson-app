import os
import uuid
import urllib.parse
import threading
import requests
from telebot import types

PRIMARY_ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
SECOND_ADMIN_ID = int(os.getenv("SECOND_ADMIN_CHAT_ID", "447208738"))
ADMIN_CHAT_IDS = [PRIMARY_ADMIN_ID, SECOND_ADMIN_ID]

GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()

ACTIVE_ORDERS = {}
REGISTERED_SHEET_ORDERS = set()

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

    # Оборудование для вариантов скважины
    "vfd_controller": 24500,
    "tank_small_vfd": 3800,
    "well_adapter_1": 4900,
    "cover_adapter": 3200,

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
    "fitting_32_1": {"ru": "Муфта ПНД 32х1\" НР", "tj": "Муфтаи ПНД 32х1\" БО", "uz": "Mufta PND 32x1\" TQ", "hy": "Կցորդիչ ՊՆԴ 32х1\" ԱՊ", "ky": "Муфта ПНД 32х1\" СТ"},
    "elbow_32": {"ru": "Уголок ПНД 32х32 (90°)", "tj": "Кунҷак ПНД 32х32 (90°)", "uz": "Tirsak PND 32x32 (90°)", "hy": "Անկյունակ ՊՆԴ 32х32 (90°)", "ky": "Бурчтук ПНД 32х32 (90°)"},
    "unipak": {"ru": "Лён + паста Unipak", "tj": "Зиғирпоя (лён) + хамираи Unipak", "uz": "Zig'ir tolasi + Unipak pasta", "hy": "Վուշաթել + մածուկ Unipak", "ky": "Зыгыр буласы + Unipak пастасы"},
    "pipe110": {"ru": "Труба рыжая 110х3.2 наружная", "tj": "Қубури норинҷӣ 110 беруна", "uz": "Zarg'aldoq quvur 110 tashqi", "hy": "Նարնջագույն խողովակ 110", "ky": "Кызгылт түтүк 110 тышкы"},
    "insul110": {"ru": "Утеплитель для трубы 110", "tj": "Гармидиҳанда барои қубури 110", "uz": "110 quvur uchun izolyatsiya", "hy": "Ջերմամեկուսիչ 110", "ky": "110 түтүк жылуулагычы"},
    "elbow110_45": {"ru": "Отвод 110х45° рыжий", "tj": "Кунҷак 110х45° норинҷӣ", "uz": "Tirsak 110x45° zarg'aldoq", "hy": "Անկյունակ 110х45°", "ky": "Бурчтук 110х45°"},
    "tee110": {"ru": "Тройник 110х110х87° рыжий", "tj": "Тройник 110х110х87°", "uz": "Troynik 110x110x87°", "hy": "Եռաբաշխիչ 110х110х87°", "ky": "Тройник 110х110х87°"},
    "bacteria": {"ru": "Бактерии для септика (старт)", "tj": "Бактерия барои септик", "uz": "Septik uchun bakteriyalar", "hy": "Բակտերիաներ սեպտիկի համար", "ky": "Септик бактериялары"},
    "drain_pipe": {"ru": "Труба дренажная 110 с перфорацией", "tj": "Қубури дренажӣ 110", "uz": "Drenaj quvuri 110", "hy": "Դրենաժային խողովակ 110", "ky": "Дренаж түтүгү 110"},
    "geotextile": {"ru": "Геотекстиль иглопробивной (рулон)", "tj": "Геотекстил (рулон)", "uz": "Geotekstil (rulon)", "hy": "Գեոտեքստիլ (ռուլոն)", "ky": "Геотекстиль (рулон)"},
    "well_cone": {"ru": "Конус-переходник для колодца 315", "tj": "Гузаришгоҳ барои чоҳи 315", "uz": "315 quduq adapteri", "hy": "315 հորի կոն", "ky": "315 кудук конусу"},
    "sand_trap": {"ru": "Пескоуловитель пластиковый 110", "tj": "Қумгирак 110", "uz": "Qum tutgich 110", "hy": "Ավազորսիչ 110", "ky": "Кум туткуч 110"},
    "leaf_grate": {"ru": "Листвоуловитель для дождеприёмника", "tj": "Барггирак барои бороноб", "uz": "Barg tutqich panjara", "hy": "Տերևորսիչ ցանց", "ky": "Жалбырак тоскуч"}
}

ALL_CATALOG_ITEMS = [
    {"code": "kesson_m1", "name": "Кессон «МИШКА-1» (Ø1050)", "price": PRICES["kesson_m1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "kesson_m2", "name": "Кессон «МИШКА-2» (Ø1300)", "price": PRICES["kesson_m2"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "kesson_m3", "name": "Кессон «МИШКА-3» (Ø1600)", "price": PRICES["kesson_m3"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "kesson_m4", "name": "Кессон «МИШКА-4» (Ø2100)", "price": PRICES["kesson_m4"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "kesson_long", "name": "Кессон «МИШКА LONG» (H=2500)", "price": PRICES["kesson_long"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "vfd_controller", "name": "Частотный преобразователь с датчиком", "price": PRICES["vfd_controller"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "well_adapter_1", "name": "Адаптер скважинный 1\" (бронза)", "price": PRICES["well_adapter_1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "cover_adapter", "name": "Крышка скважинная под адаптер", "price": PRICES["cover_adapter"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "pump_60", "name": "Насос скважинный (до 65 м)", "price": PRICES["pump_60"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "pump_85", "name": "Насос скважинный (до 90 м)", "price": PRICES["pump_85"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "pump_110", "name": "Насос усиленный (до 115 м)", "price": PRICES["pump_110"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "tank_80", "name": "Гидроаккумулятор 80-100 л", "price": PRICES["tank_80"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "tank_150", "name": "Гидроаккумулятор 150-200 л", "price": PRICES["tank_150"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "tank_small_vfd", "name": "Гидроаккумулятор буферный 5–8 л для ПЧ", "price": PRICES["tank_small_vfd"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "septic_bio3", "name": "Станция «МИШКА-Био 3»", "price": PRICES["septic_bio3"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "septic_bio5", "name": "Станция «МИШКА-Био 5»", "price": PRICES["septic_bio5"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "septic_bio8", "name": "Станция «МИШКА-Био 8»", "price": PRICES["septic_bio8"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "septic_tank2", "name": "Накопитель МИШКА 2.0 м³", "price": PRICES["septic_tank2"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "drain_softrock", "name": "Блоки «Софтрок/Лайтдрок» 110 (L=3м)", "price": PRICES["drain_softrock"], "unit": "м", "unit_key": "unit_m"},
    {"code": "drain_pipe", "name": "Труба дренажная 110 с перфорацией", "price": PRICES["drain_pipe_classic"], "unit": "м", "unit_key": "unit_m"},
    {"code": "well_drain_315", "name": "Колодец смотровой d315 + люк + дно", "price": PRICES["well_drain_315"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "storm_inlet_box", "name": "Дождеприёмник 300х300 с решёткой", "price": PRICES["storm_inlet_box"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "pnd32", "name": "Труба ПНД PE-100 SDR11 Ø32 мм", "price": PRICES["pnd32"], "unit": "м", "unit_key": "unit_m"},
    {"code": "pnd25", "name": "Труба ПНД 25 (полив)", "price": PRICES["pnd25"], "unit": "м", "unit_key": "unit_m"},
    {"code": "pipe110", "name": "Труба рыжая 110х3.2 наружная", "price": PRICES["pipe110"], "unit": "м", "unit_key": "unit_m"},
    {"code": "insul", "name": "Утеплитель Энергофлекс 32", "price": PRICES["insul"], "unit": "м", "unit_key": "unit_m"},
    {"code": "insul110", "name": "Утеплитель для трубы 110", "price": PRICES["insul110"], "unit": "м", "unit_key": "unit_m"},
    {"code": "heat_cable", "name": "Кабель греющий саморег.", "price": PRICES["heat_cable"], "unit": "м", "unit_key": "unit_m"},
    {"code": "ball_valve", "name": "Кран 1\" с американкой", "price": PRICES["ball_valve"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "fitting_32_1", "name": "Муфта ПНД 32х1\" НР", "price": PRICES["fitting_32_1"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "elbow_32", "name": "Уголок ПНД 32х32 (90°)", "price": PRICES["elbow_32"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "elbow110_45", "name": "Отвод 110х45° рыжий", "price": PRICES["elbow110_45"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "tee110", "name": "Тройник 110х110х87° рыжий", "price": PRICES["tee110"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "bacteria", "name": "Бактерии для септика (старт)", "price": PRICES["bacteria"], "unit": "шт.", "unit_key": "unit_pcs"},
    {"code": "geotextile", "name": "Геотекстиль иглопробивной (рулон)", "price": PRICES["geotextile_roll"], "unit": "рул.", "unit_key": "unit_roll"},
    {"code": "sand_trap", "name": "Пескоуловитель пластиковый 110", "price": PRICES["sand_trap"], "unit": "шт.", "unit_key": "unit_pcs"}
]

MESSAGES = {
    "ru": {
        "order_title": "🧾 <b>НОВЫЙ ЗАКАЗ #{order_id} «МИШКА»</b>",
        "client": "👷 <b>Заказчик:</b> {name} ({tag})",
        "phone": "📞 <b>Телефон:</b> {phone}",
        "pickup_type": "📦 <b>Самовывоз со склада</b>",
        "delivery_type": "🚛 <b>ДОСТАВКА НА ОБЪЕКТ</b>",
        "addr_label": "📍 <b>Адрес доставки:</b> <code>{addr}</code>",
        "time_label": "🕒 <b>Время:</b> <i>{time}</i>",
        "spec_title": "📦 <b>СПЕЦИФИКАЦИЯ:</b>",
        "total": "💰 <b>ИТОГО К ОПЛАТЕ: {sum} ₽</b>",
        "accepted": "✅ <b>Ваш заказ принят складом! Номер: #{order_id}</b>\n\n{body}\n\n⏳ <i>Мы оповестим вас здесь, как только заказ будет собран!</i>",
        "collected_title": "🎉 <b>ВАШ ЗАКАЗ #{order_id} ПОЛНОСТЬЮ СОБРАН!</b>",
        "collected_body": "📦 Все комплектующие проверены и готовы к выдаче на складе «МИШКА».\n💰 Сумма к оплате: <b>{sum} ₽</b>\n🚚 Способ: <b>{delivery}</b>\n\nЖдём вас на складе!",
        "paid_title": "✅ <b>ЗАКАЗ #{order_id} ОПЛАЧЕН И ВЫДАН!</b>",
        "paid_body": "💰 Оплата успешно проведена: <b>{method}</b>\nСумма: <b>{sum} ₽</b>\n\nБлагодарим за сотрудничество с заводом «МИШКА»!",
        "btn_nav_sklad": "📍 Маршрут к складу (Яндекс)",
        "btn_repeat": "🔄 Повторить этот заказ",
        "unit_m": "м",
        "unit_pcs": "шт.",
        "unit_set": "компл.",
        "unit_roll": "рул."
    },
    "tj": {
        "order_title": "🧾 <b>ФАРМОИШИ НАВ #{order_id} «МИШКА»</b>",
        "client": "👷 <b>Мизоҷ:</b> {name} ({tag})",
        "phone": "📞 <b>Телефон:</b> {phone}",
        "pickup_type": "📦 <b>Худам аз анбор мегирам</b>",
        "delivery_type": "🚛 <b>БУРДАН БА СУРОҒАИ МАНЗИЛ</b>",
        "addr_label": "📍 <b>Суроғаи расонидан:</b> <code>{addr}</code>",
        "time_label": "🕒 <b>Вақт:</b> <i>{time}</i>",
        "spec_title": "📦 <b>РӮЙХАТИ ТАҶҲИЗОТ:</b>",
        "total": "💰 <b>ҲАМАГӢ БАРОИ ПАРДОХТ: {sum} ₽</b>",
        "accepted": "✅ <b>Фармоиши шумо қабул шуд! Рақам: #{order_id}</b>\n\n{body}\n\n⏳ <i>Ҳамин ки бор дар анбор омода шуд, мо ба шумо хабар медиҳем!</i>",
        "collected_title": "🎉 <b>ФАРМОИШИ ШУМО #{order_id} ПУРРА ОМОДА ШУД!</b>",
        "collected_body": "📦 Ҳамаи таҷҳизот санҷида шуда, дар анбори «МИШКА» омода аст.\n💰 Маблағи пардохт: <b>{sum} ₽</b>\n🚚 Тарзи гирифтан: <b>{delivery}</b>\n\nШуморо дар анбор интизорем!",
        "paid_title": "✅ <b>ФАРМОИШ #{order_id} СУПОРИДА ШУД!</b>",
        "paid_body": "💰 Пардохт қабул шуд: <b>{method}</b>\nМаблағ: <b>{sum} ₽</b>\n\nТашаккур барои ҳамкорӣ бо корхонаи «МИШКА»!",
        "btn_nav_sklad": "📍 Харитаи роҳ ба анбор (Яндекс)",
        "btn_repeat": "🔄 Ин фармоишро такрор кардан",
        "unit_m": "м",
        "unit_pcs": "дона",
        "unit_set": "маҷм.",
        "unit_roll": "рулон"
    },
    "uz": {
        "order_title": "🧾 <b>YANGI BUYURTMA #{order_id} «MISHKA»</b>",
        "client": "👷 <b>Buyurtmachi:</b> {name} ({tag})",
        "phone": "📞 <b>Telefon:</b> {phone}",
        "pickup_type": "📦 <b>Ombordan olib ketish</b>",
        "delivery_type": "🚛 <b>OBYEKTGA YETKAZIB BERISH</b>",
        "addr_label": "📍 <b>Yetkazish manzili:</b> <code>{addr}</code>",
        "time_label": "🕒 <b>Vaqti:</b> <i>{time}</i>",
        "spec_title": "📦 <b>MAHSULOTLAR RO'YXATI:</b>",
        "total": "💰 <b>TO'LOV UCHUN JAMI: {sum} ₽</b>",
        "accepted": "✅ <b>Buyurtmangiz qabul qilindi! Raqam: #{order_id}</b>\n\n{body}\n\n⏳ <i>Buyurtma omborda tayyor bo'lishi bilan bu yerda xabar beramiz!</i>",
        "collected_title": "🎉 <b>BUYURTMANGIZ #{order_id} TO'LIQ TAYYOR BO'LDI!</b>",
        "collected_body": "📦 Barcha uskunalar tekshirildi va «MISHKA» omborida tayyor.\n💰 To'lov summasi: <b>{sum} ₽</b>\n🚚 Qabul qilish: <b>{delivery}</b>\n\nSizni omborda kutamiz!",
        "paid_title": "✅ <b>BUYURTMA #{order_id} TO'LANDI VA TOPSHIRILDI!</b>",
        "paid_body": "💰 To'lov qabul qilindi: <b>{method}</b>\nSumma: <b>{sum} ₽</b>\n\n«MISHKA» zavodi bilan hamkorlik uchun rahmat!",
        "btn_nav_sklad": "📍 Omborga yo'nalish (Yandeks)",
        "btn_repeat": "🔄 Ushbu buyurtmani takrorlash",
        "unit_m": "m",
        "unit_pcs": "dona",
        "unit_set": "to'plam",
        "unit_roll": "rulon"
    },
    "hy": {
        "order_title": "🧾 <b>ՆՈՐ ՊԱՏՎԵՐ #{order_id} «ՄԻՇԿԱ»</b>",
        "client": "👷 <b>Հաճախորդ:</b> {name} ({tag})",
        "phone": "📞 <b>Հեռախոս:</b> {phone}",
        "pickup_type": "📦 <b>Ինքնուրույն պահեստից</b>",
        "delivery_type": "🚛 <b>ԱՌԱՔՈՒՄ ԴԵՊԻ ՕԲՅԵԿՏ</b>",
        "addr_label": "📍 <b>Առաքման հասցե:</b> <code>{addr}</code>",
        "time_label": "🕒 <b>Ժամ:</b> <i>{time}</i>",
        "spec_title": "📦 <b>ԱՊՐԱՆՔԱՑՈՒՑԱԿ:</b>",
        "total": "💰 <b>ԸՆԴԱՄԵՆԸ ՎՃԱՐՄԱՆ: {sum} ₽</b>",
        "accepted": "✅ <b>Ձեր պատվերն ընդունված է: Համար: #{order_id}</b>\n\n{body}\n\n⏳ <i>Մենք կտեղեկացնենք Ձեզ, երբ պատվերը պատրաստ լինի:</i>",
        "collected_title": "🎉 <b>ՁԵՐ ՊԱՏՎԵՐԸ #{order_id} ԱՄԲՈՂՋՈՒԹՅԱՄԲ ՀԱՎԱՔՎԱԾ Է:</b>",
        "collected_body": "📦 Բոլոր ապրանքները ստուգված են և պատրաստ են «ՄԻՇԿԱ» պահեստում:\n💰 Գումար: <b>{sum} ₽</b>\n🚚 Ստացում: <b>{delivery}</b>\n\nՍպասում ենք Ձեզ պահեստում:",
        "paid_title": "✅ <b>ՊԱՏՎԵՐ #{order_id} ՎՃԱՐՎԱԾ Է:</b>",
        "paid_body": "💰 Վճարման եղանակ: <b>{method}</b>\nԳումար: <b>{sum} ₽</b>\n\nՇնորհակալություն «ՄԻՇԿԱ» գործարանի հետ համագործակցության համար:",
        "btn_nav_sklad": "📍 Ճանապարհ դեպի պահեստ (Yandex)",
        "btn_repeat": "🔄 Կրկնել այս պատվերը",
        "unit_m": "մ",
        "unit_pcs": "հատ",
        "unit_set": "հավաք.",
        "unit_roll": "ռուլոն"
    },
    "ky": {
        "order_title": "🧾 <b>ЖАҢЫ ЗАКАЗ #{order_id} «МИШКА»</b>",
        "client": "👷 <b>Кардар:</b> {name} ({tag})",
        "phone": "📞 <b>Телефон:</b> {phone}",
        "pickup_type": "📦 <b>Кампадан өзү алып кетүү</b>",
        "delivery_type": "🚛 <b>ОБЪЕКТКЕ ЖЕТКИРҮҮ</b>",
        "addr_label": "📍 <b>Жеткирүү дареги:</b> <code>{addr}</code>",
        "time_label": "🕒 <b>Убактысы:</b> <i>{time}</i>",
        "spec_title": "📦 <b>СПЕЦИФИКАЦИЯ:</b>",
        "total": "💰 <b>ТӨЛӨМ ҮЧҮН ЖАЛПЫ: {sum} ₽</b>",
        "accepted": "✅ <b>Заказыңыз кабыл алынды! Номери: #{order_id}</b>\n\n{body}\n\n⏳ <i>Кампада жүк топтолору менен сизге кабар беребиз!</i>",
        "collected_title": "🎉 <b>СИЗДИН ЗАКАЗ #{order_id} ТОЛУГУ МЕНЕН ТОПТОЛДУ!</b>",
        "collected_body": "📦 Бардык жабдуулар текшерилди жана «МИШКА» кампасында даяр.\n💰 Төлөм суммасы: <b>{sum} ₽</b>\n🚚 Алуу түрү: <b>{delivery}</b>\n\nКампада сизди күтөбүз!",
        "paid_title": "✅ <b>ЗАКАЗ #{order_id} ТӨЛӨНДҮ ЖАНА БЕРИЛДИ!</b>",
        "paid_body": "💰 Төлөм түрү: <b>{method}</b>\nСумма: <b>{sum} ₽</b>\n\n«МИШКА» заводу менен кызматташканыңыз үчүн рахмат!",
        "btn_nav_sklad": "📍 Кампага баруучу жол (Яндекс)",
        "btn_repeat": "🔄 Бул заказды кайталоо",
        "unit_m": "м",
        "unit_pcs": "даана",
        "unit_set": "компл.",
        "unit_roll": "рулон"
    }
}

def get_admin_name(user_id) -> str:
    try:
        uid = int(str(user_id).strip())
    except (ValueError, TypeError):
        return "Алексей"

    if uid in [SECOND_ADMIN_ID, 447208738]:
        return "Артур"
    return "Алексей"

def format_worker_name(worker_name: str, worker_tag: str) -> str:
    name = str(worker_name or "").strip()
    tag = str(worker_tag or "").strip()
    if name in ["4:20", "Монтажник", ""]:
        return tag if tag else "Монтажник"
    return f"{name} ({tag})" if tag else name

def get_system_name_ru(mode: str) -> str:
    mapping = {
        "well": "Скважина / Кессон",
        "septic": "Септик / Канализация",
        "drainage": "Дренаж участка",
        "storm": "Ливнёвка в земле"
    }
    return mapping.get(str(mode).lower().strip(), "Скважина / Кессон")

def extract_delivery_address(delivery_info: str) -> str:
    if not delivery_info:
        return ""
    text = str(delivery_info)
    if "Адрес:" in text:
        addr_part = text.split("Адрес:")[1]
        if "|" in addr_part:
            addr_part = addr_part.split("|")[0]
        return addr_part.strip()
    if "|" in text:
        return text.split("|")[0].strip()
    return text.strip()

def _send_to_sheet_now(payload: dict):
    webhook_url = GOOGLE_SHEET_WEBHOOK
    if not webhook_url:
        return
    try:
        res = requests.post(webhook_url, json=payload, timeout=10, allow_redirects=True)
        print(f"[SHEET SYNC] Action: {payload.get('action')}, Order: {payload.get('order_id')}, Code: {res.status_code}")
    except Exception as e:
        print(f"[SHEET SYNC ERR] {e}")

def sync_to_google_sheet(order_id: str, data: dict, total_sum: int, items_list: list = None):
    clean_id = str(order_id).strip()
    if clean_id in REGISTERED_SHEET_ORDERS:
        return
    REGISTERED_SHEET_ORDERS.add(clean_id)

    full_client_info = format_worker_name(data.get("worker_name"), data.get("worker_tag"))
    
    items_summary = ""
    if items_list:
        items_summary = ", ".join([f"{it['name']} ({it['qty']} {it['unit']})" for it in items_list])

    payload = {
        "action": "create_order",
        "order_id": clean_id,
        "client_name": full_client_info,
        "phone": str(data.get("phone", "")),
        "items": items_summary or get_system_name_ru(data.get("mode", "well")),
        "total_sum": int(total_sum),
        "delivery_info": str(data.get("delivery_info", "-")),
        "delivery_type": str(data.get("delivery_type", "Самовывоз со склада"))
    }

    threading.Thread(target=_send_to_sheet_now, args=(payload,), daemon=True).start()

def update_sheet_status(order_id: str, status: str, cancel_reason: str = "", manager: str = "", payment_method: str = "-", **kwargs):
    order = ACTIVE_ORDERS.get(order_id, {})
    assembler_val = kwargs.get("assembler") or manager or order.get("collected_by", "")
    payment_val = kwargs.get("payment_type") or payment_method or order.get("payment_method", "")
    if payment_val == "-":
        payment_val = ""
    comment_val = kwargs.get("comment") or cancel_reason or order.get("cancel_reason", "")

    payload = {
        "action": "update_order",
        "order_id": str(order_id).strip(),
        "status": str(status),
        "comment": str(comment_val),
        "assembler": str(assembler_val),
        "payment_type": str(payment_val)
    }

    threading.Thread(target=_send_to_sheet_now, args=(payload,), daemon=True).start()

def get_items_for_order(data: dict):
    mode = data.get("mode", "well")
    extras = data.get("extras", {})
    items = []

    if mode == "well":
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

        # Базовая часть для всех скважин
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

        # ВАРИАНТ 3: Обустройство через скважинный адаптер (без кессона)
        if equip_type == "adapter":
            items.extend([
                {"name": "Адаптер скважинный 1\" (бронза)", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["well_adapter_1"]},
                {"name": "Крышка скважинная под адаптер d125-133", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["cover_adapter"]},
                {"name": "Гидроаккумулятор 80-100 л (в дом)", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["tank_80"]},
                {"name": "Автоматика: реле + манометр + штуцер", "qty": 1, "unit": "компл.", "unit_key": "unit_set", "price": 5100}
            ])
        else:
            # Обустройство с кессоном
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

            # ВАРИАНТ 1: Частотный преобразователь (ПЧ)
            if equip_type == "kesson_vfd":
                items.extend([
                    {"name": "Частотный преобразователь с датчиком давления", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["vfd_controller"]},
                    {"name": "Гидроаккумулятор буферный 5–8 л для ПЧ", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["tank_small_vfd"]}
                ])
            # ВАРИАНТ 2: Стандартный гидроаккумулятор (ГА) с выбором объема
            else:
                if chosen_tank == "tank_150" or (chosen_tank == "auto" and houses > 1):
                    tank_name, tank_p = "Гидроаккумулятор 150-200 л", PRICES["tank_150"]
                else:
                    tank_name, tank_p = "Гидроаккумулятор 80-100 л", PRICES["tank_80"]

                items.extend([
                    {"name": tank_name, "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": tank_p},
                    {"name": "Автоматика: реле + манометр + штуцер", "qty": 1, "unit": "компл.", "unit_key": "unit_set", "price": 5100}
                ])

    elif mode == "septic":
        dist = data.get("distance", 10)
        discharge = data.get("discharge", "gravity")
        chosen = data.get("chosen_septic", "auto")

        if "Био 3" in chosen:
            s_n, s_p = "Станция «МИШКА-Био 3»", PRICES["septic_bio3"]
        elif "Био 8" in chosen:
            s_n, s_p = "Станция «МИШКА-Био 8»", PRICES["septic_bio8"]
        else:
            s_n, s_p = "Станция «МИШКА-Био 5»", PRICES["septic_bio5"]

        pipe_m = int(dist * 1.05)
        items = [
            {"name": s_n, "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": s_p},
            {"name": "Труба ПВХ рыжая наружная 110х3.2", "qty": pipe_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["pipe110"]},
            {"name": "Утеплитель для трубы 110", "qty": pipe_m, "unit": "м", "unit_key": "unit_m", "price": PRICES["insul110"]},
            {"name": "Отводы 110х45° рыжие", "qty": max(2, int(dist // 6) + 1), "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["elbow110_45"]},
            {"name": "Тройник ревизионный 110 с заглушкой", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["tee110"]},
            {"name": "Бактерии для быстрого запуска", "qty": 1, "unit": "компл.", "unit_key": "unit_set", "price": PRICES["bacteria"]}
        ]
        if discharge == "forced":
            items.extend([
                {"name": "Насос дренажный с поплавком", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["drain_pump"]},
                {"name": "Шланг напорный армированный 32", "qty": 10, "unit": "м", "unit_key": "unit_m", "price": PRICES["drain_hose"]},
                {"name": "Кабель греющий для слива", "qty": 5, "unit": "м", "unit_key": "unit_m", "price": PRICES["cable_heat_septic"]}
            ])

    elif mode == "drainage":
        dtype = data.get("drain_type", "softrock")
        length = data.get("drain_length", 50)
        wells = data.get("drain_wells", 3)

        if dtype == "softrock":
            items = [
                {"name": "Блоки «Софтрок/Лайтдрок» 110 (L=3м)", "qty": length, "unit": "м", "unit_key": "unit_m", "price": PRICES["drain_softrock"]},
                {"name": "Соединительные муфты Софтрок", "qty": int(length // 3) + 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["softrock_coupling"]}
            ]
        else:
            items = [
                {"name": "Труба дренажная 110 с фильтром", "qty": length, "unit": "м", "unit_key": "unit_m", "price": PRICES["drain_pipe_classic"]},
                {"name": "Геотекстиль Дорнит (рулон 2х50м)", "qty": max(1, int(length // 45) + 1), "unit": "рул.", "unit_key": "unit_roll", "price": PRICES["geotextile_roll"]}
            ]
        items.extend([
            {"name": "Колодец смотровой d315 + люк + дно", "qty": wells, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["well_drain_315"]},
            {"name": "Муфты врезки 110 в колодец 315", "qty": wells * 2, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["well_drain_coupling"]}
        ])

    elif mode == "storm":
        inlets = data.get("storm_inlets", 4)
        length = data.get("storm_length", 30)
        wells = data.get("storm_wells", 2)
        discharge = data.get("storm_discharge", "ditch")

        items = [
            {"name": "Дождеприёмник 300х300 с корзиной и решёткой", "qty": inlets, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["storm_inlet_box"]},
            {"name": "Труба ПВХ рыжая 110х3.2 наружная", "qty": int(length * 1.05), "unit": "м", "unit_key": "unit_m", "price": PRICES["storm_pipe110"]},
            {"name": "Отводы 110х45° рыжие", "qty": inlets * 2 + wells * 2, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["elbow110_45"]},
            {"name": "Тройники 110х110х87° рыжие", "qty": max(1, inlets - 1), "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["tee110"]},
            {"name": "Колодец поворотный d315 с люком", "qty": wells, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["storm_well_315"]}
        ]
        if discharge == "ditch":
            items.append({"name": "Клапан обратный 110 против подпора", "qty": 1, "unit": "шт.", "unit_key": "unit_pcs", "price": PRICES["storm_back_valve"]})

    for k, q in extras.items():
        if k in EXTRA_ITEMS and q > 0:
            e = EXTRA_ITEMS[k]
            unit_key = "unit_m" if e["unit"] == "м" else ("unit_roll" if e["unit"] == "рул." else "unit_pcs")
            items.append({
                "name": f"[Доп] {ITEM_TRANSLATIONS.get(k, {}).get('ru', k)}",
                "item_key": k,
                "qty": q,
                "unit": e["unit"],
                "unit_key": unit_key,
                "price": e["price"]
            })

    return items

def render_order_texts(order_id: str, data: dict, items: list, total_sum: int, lang: str):
    t_client = MESSAGES.get(lang, MESSAGES["ru"])
    admin_lines = []
    client_lines = []

    for it in items:
        subtotal = int(it["qty"] * it["price"])
        qty_str = f"{it['qty']:g}" if isinstance(it["qty"], float) else str(it["qty"])
        admin_lines.append(f"• <b>{it['name']}</b>\n   └ {qty_str} {it['unit']} × {it['price']:,} ₽ = <b>{subtotal:,} ₽</b>".replace(",", " "))
        
        item_key = it.get("item_key")
        if item_key and item_key in ITEM_TRANSLATIONS:
            client_item_name = f"[Доп] {ITEM_TRANSLATIONS[item_key].get(lang, it['name'])}"
        else:
            client_item_name = it["name"]
        
        unit_translated = t_client.get(it.get("unit_key", "unit_pcs"), it["unit"])
        client_lines.append(f"• <b>{client_item_name}</b>\n   └ {qty_str} {unit_translated} × {it['price']:,} ₽ = <b>{subtotal:,} ₽</b>".replace(",", " "))

    delivery_type = data.get("delivery_type", "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = "Доставка" in delivery_type
    clean_address = extract_delivery_address(delivery_info)
    phone = data.get("phone", "Не указан")
    worker_name = format_worker_name(data.get("worker_name"), data.get("worker_tag"))

    if is_delivery:
        admin_logistics = (
            f"🚚 <b>Получение:</b> 🚛 <b>ДОСТАВКА НА ОБЪЕКТ</b>\n"
            f"📍 <b>Адрес доставки:</b> <code>{clean_address or 'Не указан'}</code>\n"
            f"🕒 <b>Детали/Время:</b> <i>{delivery_info}</i>"
        )
        client_logistics = (
            f"{t_client['delivery_type']}\n"
            f"{t_client['addr_label'].format(addr=clean_address or '-')}\n"
            f"{t_client['time_label'].format(time=delivery_info)}"
        )
    else:
        admin_logistics = (
            f"🚚 <b>Получение:</b> 📦 <b>Самовывоз со склада</b>\n"
            f"🕒 <b>Время приезда:</b> <i>{delivery_info}</i>"
        )
        client_logistics = (
            f"{t_client['pickup_type']}\n"
            f"{t_client['time_label'].format(time=delivery_info)}"
        )

    admin_header = (
        f"🧾 <b>ЗАКАЗ #{order_id} «МИШКА»</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👷 <b>Заказчик:</b> {worker_name}\n"
        f"📞 <b>Телефон:</b> <a href='tel:{phone}'>{phone}</a>\n"
        f"{admin_logistics}\n"
        f"🆔 ID клиента: <code>{data.get('chat_id')}</code>\n\n"
        f"📦 <b>СПЕЦИФИКАЦИЯ:</b>\n\n"
        f"{chr(10).join(admin_lines)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>ИТОГО К ОПЛАТЕ: {total_sum:,} ₽</b>"
    ).replace(",", " ")

    client_header = (
        f"{t_client['order_title'].format(order_id=order_id)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t_client['client'].format(name=worker_name, tag='')}\n"
        f"{t_client['phone'].format(phone=phone)}\n"
        f"🚚 <b>Способ:</b> {client_logistics}\n\n"
        f"{t_client['spec_title']}\n\n"
        f"{chr(10).join(client_lines)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t_client['total'].format(sum=f'{total_sum:,}').replace(',', ' ')}"
    )

    return admin_header, client_header

def build_order_payload(data: dict):
    order_id = str(uuid.uuid4())[:8]
    items = get_items_for_order(data)
    lang = data.get("lang", "ru")
    if lang not in MESSAGES:
        lang = "ru"

    total_sum = sum(int(it["qty"] * it["price"]) for it in items)
    admin_header, client_header = render_order_texts(order_id, data, items, total_sum, lang)

    delivery_type = data.get("delivery_type", "Самовывоз со склада")
    delivery_info = data.get("delivery_info", "-")
    is_delivery = "Доставка" in delivery_type
    clean_address = extract_delivery_address(delivery_info)

    ACTIVE_ORDERS[order_id] = {
        "client_id": data.get("chat_id"),
        "client_name": format_worker_name(data.get("worker_name"), data.get("worker_tag")),
        "phone": data.get("phone", "Не указан"),
        "delivery_type": delivery_type,
        "delivery_info": delivery_info,
        "clean_address": clean_address,
        "is_delivery": is_delivery,
        "lang": lang,
        "raw_data": data,
        "items": items,
        "collected": [False] * len(items),
        "total_sum": total_sum,
        "status": "active",
        "payment_status": "unpaid"
    }

    sync_to_google_sheet(order_id, data, total_sum, items_list=items)
    return order_id, admin_header, client_header, total_sum

def make_warehouse_keyboard(order_id: str):
    order = ACTIVE_ORDERS.get(order_id)
    if not order:
        return None

    kb = types.InlineKeyboardMarkup(row_width=1)

    if order.get("is_delivery"):
        addr = order.get("clean_address") or extract_delivery_address(order.get("delivery_info", ""))
        if addr:
            nav_url = f"https://yandex.ru/navi?text={urllib.parse.quote(addr)}"
            kb.add(types.InlineKeyboardButton("🚗 Построить маршрут к клиенту (Яндекс)", url=nav_url))

    if order.get("status") == "cancelled":
        reason = order.get("cancel_reason", "")
        reason_txt = f": {reason}" if reason else ""
        kb.add(types.InlineKeyboardButton(f"❌ ЗАКАЗ ОТМЕНЁН{reason_txt}", callback_data="none"))
        return kb

    if order.get("status") == "paid":
        method = order.get("payment_method", "Оплачено")
        kb.add(types.InlineKeyboardButton(f"✅ ОПЛАЧЕН И ВЫДАН ({method})", callback_data="none"))
        return kb

    if order.get("status") == "completed":
        kb.add(types.InlineKeyboardButton("🎉 ЗАКАЗ СОБРАН НА СКЛАДЕ", callback_data="none"))
        kb.add(types.InlineKeyboardButton("💳 ОПЛАТИТЬ И ВЫДАТЬ ТОВАР", callback_data=f"paymenu_{order_id}"))
        kb.row(
            types.InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_{order_id}"),
            types.InlineKeyboardButton("✏️ Изменить комплектацию", callback_data=f"editmenu_{order_id}")
        )
        return kb

    for idx, (item, is_done) in enumerate(zip(order["items"], order["collected"])):
        mark = "🟢" if is_done else "⬜"
        qty_str = f"{item['qty']:g}" if isinstance(item['qty'], float) else str(item['qty'])
        short_name = (item['name'][:22] + "..") if len(item['name']) > 22 else item['name']
        btn_text = f"{mark} {idx+1}. {short_name} ({qty_str} {item['unit']})"
        kb.add(types.InlineKeyboardButton(btn_text, callback_data=f"chk_{order_id}_{idx}"))

    all_done = all(order["collected"])
    finish_icon = "🚀" if all_done else "📦"
    kb.add(types.InlineKeyboardButton(f"{finish_icon} ЗАКАЗ ПОЛНОСТЬЮ СОБРАН", callback_data=f"fin_{order_id}"))

    kb.row(
        types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{order_id}"),
        types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"editmenu_{order_id}")
    )

    return kb
