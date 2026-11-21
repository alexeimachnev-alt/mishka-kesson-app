# -*- coding: utf-8 -*-
"""Какие позиции заказа реально собирают на складе (без доставки и работ)."""

DELIVERY_ITEM_KEY = "delivery_truck_fee"


def is_delivery_fee_item(item: dict) -> bool:
    key = str(item.get("item_key") or item.get("code") or "").strip()
    if key == DELIVERY_ITEM_KEY:
        return True
    cat = str(item.get("category", "")).lower()
    return cat == "delivery"


def is_physical_goods_item(item: dict) -> bool:
    if item.get("is_work"):
        return False
    return not is_delivery_fee_item(item)


def goods_indices_for_collection(items: list) -> list:
    return [i for i, it in enumerate(items) if is_physical_goods_item(it)]


def initial_collected_flags(items: list) -> list:
    """Доставка сразу «готова» — её не собирают на складе."""
    return [not is_physical_goods_item(it) for it in items]


def sync_delivery_collected_flags(order: dict) -> None:
    items = order.get("items") or []
    collected = order.get("collected") or []
    if len(collected) < len(items):
        collected = list(collected) + [False] * (len(items) - len(collected))
    for idx, it in enumerate(items):
        if is_delivery_fee_item(it):
            collected[idx] = True
    order["collected"] = collected


def goods_collection_complete(order: dict) -> bool:
    items = order.get("items") or []
    collected = order.get("collected") or []
    indices = goods_indices_for_collection(items)
    if not indices:
        return True
    return all(collected[i] for i in indices if i < len(collected))