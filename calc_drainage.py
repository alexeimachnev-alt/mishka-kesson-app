from constants import PRICES

def get_drainage_items(data):
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
    return items
