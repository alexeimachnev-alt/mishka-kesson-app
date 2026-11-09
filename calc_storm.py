from constants import PRICES

def get_storm_items(data):
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
    return items
