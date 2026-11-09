from constants import EXTRA_ITEMS, ITEM_TRANSLATIONS

def add_extras(items, extras):
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
