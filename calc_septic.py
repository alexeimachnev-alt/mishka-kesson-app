from constants import PRICES

def get_septic_items(data):
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
    return items
