# -*- coding: utf-8 -*-
"""Расчёт доставки: маршрут по дорогам, геокодирование, тариф склада «МИШКА»."""
from __future__ import annotations

import math
import os
import re
import urllib.parse
from typing import Any, Optional

import requests

WAREHOUSE_LAT = float(os.getenv("MISHKA_WAREHOUSE_LAT", "56.047416"))
WAREHOUSE_LON = float(os.getenv("MISHKA_WAREHOUSE_LON", "37.538633"))
DELIVERY_BASE_RUB = float(os.getenv("MISHKA_DELIVERY_BASE_RUB", "2000"))
DELIVERY_PER_KM_RUB = float(os.getenv("MISHKA_DELIVERY_PER_KM_RUB", "45"))

YANDEX_GEOCODER_API_KEY = (
    os.getenv("YANDEX_GEOCODER_API_KEY") or os.getenv("YANDEX_MAPS_API_KEY") or ""
).strip()
YANDEX_ROUTING_API_KEY = (
    os.getenv("YANDEX_ROUTING_API_KEY") or os.getenv("YANDEX_MAPS_API_KEY") or ""
).strip()

OSRM_DRIVING_URL = os.getenv(
    "OSRM_DRIVING_URL", "https://router.project-osrm.org/route/v1/driving"
).rstrip("/")

DELIVERY_ITEM_KEY = "delivery_truck_fee"


def delivery_price_from_road_km(road_km: float) -> dict:
    """2000 + ceil(distance_km) * 45; при 0 км — всё равно 2000 ₽."""
    raw = max(0.0, float(road_km))
    billed_km = int(math.ceil(raw)) if raw > 0 else 0
    variable = billed_km * DELIVERY_PER_KM_RUB
    total = int(DELIVERY_BASE_RUB + variable)
    return {
        "distance_km_raw": round(raw, 2),
        "distance_km_billed": billed_km,
        "base_rub": int(DELIVERY_BASE_RUB),
        "per_km_rub": int(DELIVERY_PER_KM_RUB),
        "variable_rub": int(variable),
        "delivery_price": total,
    }


def yandex_navi_url(lat: float, lon: float) -> str:
    return f"https://yandex.ru/navi?whatshere%5Bpoint%5D={lon},{lat}&whatshere%5Bzoom%5D=16"


def _route_distance_osrm(dest_lat: float, dest_lon: float) -> float:
    coords = f"{WAREHOUSE_LON},{WAREHOUSE_LAT};{dest_lon},{dest_lat}"
    url = f"{OSRM_DRIVING_URL}/{coords}"
    resp = requests.get(
        url,
        params={"overview": "false", "alternatives": "false", "steps": "false"},
        timeout=25,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError(data.get("message") or "OSRM: маршрут не найден")
    meters = float(data["routes"][0]["distance"])
    return meters / 1000.0


def _route_distance_yandex(dest_lat: float, dest_lon: float) -> float:
    if not YANDEX_ROUTING_API_KEY:
        raise ValueError("Yandex Routing API key not configured")
    waypoints = f"{WAREHOUSE_LON},{WAREHOUSE_LAT}|{dest_lon},{dest_lat}"
    url = "https://api.routing.yandex.net/v2/route"
    resp = requests.get(
        url,
        params={"waypoints": waypoints, "apikey": YANDEX_ROUTING_API_KEY},
        timeout=25,
    )
    resp.raise_for_status()
    data = resp.json()
    route = data.get("route") or {}
    legs = route.get("legs") or []
    if not legs:
        raise ValueError("Yandex: пустой маршрут")
    meters = 0.0
    for leg in legs:
        meters += float(leg.get("length", 0))
    if meters <= 0:
        raise ValueError("Yandex: не удалось получить длину маршрута")
    return meters / 1000.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def _straight_line_road_estimate_km(dest_lat: float, dest_lon: float) -> float:
    """Запасной километраж, если внешний роутер недоступен (≈1.32× по прямой)."""
    air = _haversine_km(WAREHOUSE_LAT, WAREHOUSE_LON, dest_lat, dest_lon)
    return max(0.1, air * 1.32)


def road_distance_km(dest_lat: float, dest_lon: float) -> tuple[float, str]:
    """Километраж по дорогам; возвращает (km, provider)."""
    errors = []
    if YANDEX_ROUTING_API_KEY:
        try:
            return _route_distance_yandex(dest_lat, dest_lon), "yandex"
        except Exception as e:
            errors.append(f"Yandex: {e}")
    try:
        return _route_distance_osrm(dest_lat, dest_lon), "osrm"
    except Exception as e:
        errors.append(f"OSRM: {e}")
    est = _straight_line_road_estimate_km(dest_lat, dest_lon)
    print(f"[DELIVERY] road routers failed ({errors}); estimate_km={est:.2f}")
    return est, "estimate"


def calculate_delivery_quote(dest_lat: float, dest_lon: float) -> dict:
    km, provider = road_distance_km(dest_lat, dest_lon)
    pricing = delivery_price_from_road_km(km)
    return {
        "status": "ok",
        "warehouse_lat": WAREHOUSE_LAT,
        "warehouse_lon": WAREHOUSE_LON,
        "delivery_lat": dest_lat,
        "delivery_lon": dest_lon,
        "route_provider": provider,
        "yandex_navi_url": yandex_navi_url(dest_lat, dest_lon),
        **pricing,
    }


def _yandex_geocode_request(geocode: str) -> list[dict]:
    if not YANDEX_GEOCODER_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://geocode-maps.yandex.ru/1.x/",
            params={
                "apikey": YANDEX_GEOCODER_API_KEY,
                "format": "json",
                "geocode": geocode,
                "results": 7,
                "lang": "ru_RU",
            },
            timeout=20,
        )
        if resp.status_code == 403:
            print("[GEOCODE] Yandex 403 — проверьте продукт «HTTP Геокодер» для ключа; fallback OSM")
            return []
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[GEOCODE] Yandex error: {e}")
        return []
    members = (
        data.get("response", {})
        .get("GeoObjectCollection", {})
        .get("featureMember", [])
    )
    out = []
    for m in members:
        obj = m.get("GeoObject", {})
        pos = (
            obj.get("Point", {}).get("pos")
            or obj.get("point", {}).get("pos")
        )
        if not pos:
            continue
        lon_s, lat_s = str(pos).split()[:2]
        name = (
            obj.get("metaDataProperty", {})
            .get("GeocoderMetaData", {})
            .get("text")
            or obj.get("name", "")
        )
        out.append(
            {
                "address": name,
                "lat": float(lat_s),
                "lon": float(lon_s),
            }
        )
    return out


def _nominatim_search(query: str, limit: int = 7) -> list[dict]:
    resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": limit, "countrycodes": "ru"},
        headers={"User-Agent": "MishkaKesson/1.0 (warehouse delivery)"},
        timeout=20,
    )
    resp.raise_for_status()
    rows = resp.json() or []
    return [
        {
            "address": r.get("display_name", query),
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
        }
        for r in rows
        if r.get("lat") and r.get("lon")
    ]


def _nominatim_reverse(lat: float, lon: float) -> Optional[str]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "accept-language": "ru"},
            headers={"User-Agent": "MishkaKesson/1.0 (warehouse delivery)"},
            timeout=12,
        )
        if resp.status_code in (403, 429, 503):
            return None
        resp.raise_for_status()
        data = resp.json()
        return data.get("display_name")
    except Exception as e:
        print(f"[GEOCODE] nominatim reverse: {e}")
        return None


def geocode_suggest(query: str) -> dict:
    q = (query or "").strip()
    if len(q) < 3:
        return {"status": "ok", "suggestions": []}
    suggestions = _yandex_geocode_request(q)
    provider = "yandex" if suggestions else "nominatim"
    if not suggestions:
        try:
            suggestions = _nominatim_search(q)
        except Exception:
            suggestions = []
    return {"status": "ok", "suggestions": suggestions, "provider": provider}


def geocode_forward(address: str) -> dict:
    addr = (address or "").strip()
    if not addr:
        return {"status": "error", "message": "Пустой адрес"}
    hits = _yandex_geocode_request(addr)
    if not hits:
        try:
            hits = _nominatim_search(addr, limit=1)
        except Exception as e:
            return {"status": "error", "message": str(e)}
    if not hits:
        return {"status": "error", "message": "Адрес не найден"}
    top = hits[0]
    return {"status": "ok", **top}


def geocode_reverse(lat: float, lon: float) -> dict:
    hits = _yandex_geocode_request(f"{lon},{lat}")
    if hits:
        return {"status": "ok", **hits[0]}
    addr = _nominatim_reverse(lat, lon)
    if not addr:
        addr = f"{lat:.6f}, {lon:.6f}"
    return {"status": "ok", "address": addr, "lat": lat, "lon": lon}


_COORD_PATTERNS = [
    re.compile(
        r"(?:https?://)?(?:maps\.yandex\.(?:ru|com)[^\s]*?(?:pt|ll)=)?"
        r"(-?\d{1,3}\.\d+)[,\s]+(-?\d{1,3}\.\d+)",
        re.I,
    ),
    re.compile(
        r"(?:https?://)?yandex\.ru/navi[^\s]*(?:text|ll)=(-?\d{1,3}\.\d+)[,\s%]+(-?\d{1,3}\.\d+)",
        re.I,
    ),
    re.compile(r"^\s*(-?\d{1,3}\.\d+)\s*[,;\s]\s*(-?\d{1,3}\.\d+)\s*$"),
]


def parse_coordinates(text: str) -> Optional[tuple[float, float]]:
    raw = (text or "").strip()
    if not raw:
        return None
    for pat in _COORD_PATTERNS:
        m = pat.search(raw)
        if not m:
            continue
        lat = float(m.group(1))
        lon = float(m.group(2))
        if abs(lat) > 90 and abs(lon) <= 90:
            lat, lon = lon, lat
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        return lat, lon
    return None


def should_charge_delivery_fee(data: dict) -> bool:
    """Платная доставка со склада до точки клиента (все режимы заказа, кроме самовывоза товаров)."""
    flag = data.get("charge_delivery_fee")
    if flag is True or str(flag).lower() in ("1", "true", "yes"):
        return True
    mode = str(data.get("mode", "well")).lower()
    if mode in ("works", "combined"):
        return True
    dtype = str(data.get("delivery_type", ""))
    if "самовывоз" in dtype.lower():
        return False
    if "Доставка" in dtype or "доставка на объект" in dtype.lower():
        return True
    return False


def should_charge_goods_delivery(data: dict) -> bool:
    """Совместимость — то же, что should_charge_delivery_fee."""
    return should_charge_delivery_fee(data)


def ensure_delivery_pricing_in_data(data: dict) -> dict:
    """Заполняет delivery_* по координатам (2000 + ceil(km)×45), если клиент не прислал цену."""
    d = dict(data)
    if not should_charge_delivery_fee(d):
        return d
    lat, lon = d.get("delivery_lat"), d.get("delivery_lon")
    if lat is None or lon is None:
        addr = (d.get("delivery_address") or d.get("delivery_info") or "").strip()
        coords = parse_coordinates(addr) if addr else None
        if coords:
            lat, lon = coords
        elif addr:
            g = geocode_forward(addr)
            if g.get("status") == "ok":
                lat, lon = g["lat"], g["lon"]
                d.setdefault("delivery_address", g.get("address", addr))
    if lat is None or lon is None:
        return d
    try:
        lat_f, lon_f = float(lat), float(lon)
        quote = calculate_delivery_quote(lat_f, lon_f)
        d["delivery_lat"] = lat_f
        d["delivery_lon"] = lon_f
        d["delivery_price"] = quote["delivery_price"]
        d["delivery_distance_km"] = quote["distance_km_billed"]
        d["delivery_distance_km_billed"] = quote["distance_km_billed"]
        d["delivery_distance_km_raw"] = quote["distance_km_raw"]
        d["delivery_base_rub"] = quote["base_rub"]
        d["delivery_per_km_rub"] = quote["per_km_rub"]
        d["delivery_variable_rub"] = quote["variable_rub"]
        d["yandex_navi_url"] = quote.get("yandex_navi_url") or yandex_navi_url(lat_f, lon_f)
        if not d.get("delivery_address"):
            rev = geocode_reverse(lat_f, lon_f)
            if rev.get("status") == "ok":
                d["delivery_address"] = rev.get("address", "")
    except Exception as e:
        print(f"[DELIVERY] ensure_delivery_pricing: {e}")
    return d


def order_needs_goods_delivery_fee(data: dict) -> bool:
    if not should_charge_delivery_fee(data):
        return False
    try:
        return float(data.get("delivery_price", 0)) > 0
    except (TypeError, ValueError):
        return False


def apply_delivery_to_order_items(items: list, data: dict) -> tuple[list, float]:
    """Добавляет строку «Доставка на объект» и возвращает (items, extra_sum)."""
    if not order_needs_goods_delivery_fee(data):
        return items, 0.0
    price = float(data.get("delivery_price", 0))
    km_billed = int(data.get("delivery_distance_km_billed") or data.get("delivery_distance_km") or 0)
    addr = str(data.get("delivery_address") or data.get("delivery_info") or "Доставка")
    base = int(data.get("delivery_base_rub", DELIVERY_BASE_RUB))
    per_km = int(data.get("delivery_per_km_rub", DELIVERY_PER_KM_RUB))
    name = (
        f"🚛 Доставка со склада: {base:,} ₽ (подача) + {km_billed} км × {per_km:,} ₽ "
        f"= {int(price):,} ₽ — {addr[:60]}"
    )
    filtered = [it for it in items if str(it.get("item_key")) != DELIVERY_ITEM_KEY]
    line = {
        "item_key": DELIVERY_ITEM_KEY,
        "name": name,
        "qty": 1,
        "unit": "рейс",
        "price": round(price, 2),
        "category": "delivery",
        "is_work": False,
    }
    filtered.append(line)
    return filtered, price


def delivery_admin_logistics_block(data: dict) -> str:
    if not order_needs_goods_delivery_fee(data):
        return ""
    km = data.get("delivery_distance_km_billed") or data.get("delivery_distance_km")
    price = data.get("delivery_price")
    base = data.get("delivery_base_rub", DELIVERY_BASE_RUB)
    per_km = data.get("delivery_per_km_rub", DELIVERY_PER_KM_RUB)
    addr = data.get("delivery_address") or data.get("delivery_info", "")
    nav = data.get("yandex_navi_url") or ""
    lines = [
        f"🛣 <b>Доставка от склада:</b> <code>{km} км</code> по дорогам",
        f"💵 <b>Расчёт:</b> {int(base):,} ₽ (подача) + {km} км × {int(per_km):,} ₽ = <b>{int(float(price)):,} ₽</b>",
        f"📍 <b>Точка:</b> <code>{addr}</code>",
    ]
    if nav:
        lines.append(f"🚗 <b>Навигатор:</b> <a href='{nav}'>Открыть маршрут</a>")
    lat = data.get("delivery_lat")
    lon = data.get("delivery_lon")
    if lat is not None and lon is not None:
        lines.append(f"📌 <b>Координаты:</b> <code>{lat}, {lon}</code>")
    return "\n".join(lines)