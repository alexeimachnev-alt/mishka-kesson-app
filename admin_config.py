# -*- coding: utf-8 -*-
"""
Модуль динамической конфигурации прайс-листа, каталога, базовых комплектов и описаний схем.
Доступ к редактированию разрешен ТОЛЬКО главному администратору (OWNER_ADMIN_ID = 551209811).
Поддерживает:
1. Мгновенное обновление цен и позиций в памяти и локальном файле catalog_config.json.
2. Облачное сохранение/восстановление через GOOGLE_SHEET_WEBHOOK (защита от сброса на Render).
3. Автоматический бэкап файла catalog_config.json в личный чат Telegram главного администратора.
4. Загрузку файла catalog_config.json обратно в бота (через админ-панель или отправкой документа в чат бота).
"""
import os
import json
import threading
import requests
from constants import PRICES, KESSON_MODELS, TANK_CATALOG, PUMP_CATALOG

_BASE_TANK_REFERENCE_PRICES = {k: float(v.get("price", 0)) for k, v in TANK_CATALOG.items()}
from calc_module import ALL_CATALOG_ITEMS, SERVICES_CATALOG, ITEM_TRANSLATIONS

OWNER_ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog_config.json")
GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "").strip()

DEFAULT_SCHEMES = {
    "kesson_ga": {
        "badge": "Вариант 1 • Классическая система",
        "title": "Кессон с гидробаком (реле давления)",
        "essence": "Все ключевое оборудование (гидроаккумулятор, реле давления, манометры) находится в подземном герметичном кессоне. Насос работает по принципу «вкл/выкл» по достижении давления в баке.",
        "visual": "На разрезе грунта показана скважина глубиной 60 м и пластиковый кессон с утепленной крышкой. Погружный насос подает воду из скважины через трубу в кессон. Внутри кессона установлен большой гидробак (расширительный бак) и блок автоматики с манометрами.",
        "animText": "При открытии крана в доме вода сначала расходуется из гидробака. Когда давление падает до минимума, стрелка на реле давления смещается, и насос в скважине включается на полную мощность, наполняя бак заново. Вода поступает в дом (на кухню и в ванную)."
    },
    "kesson_vfd": {
        "badge": "Вариант 2 • Современная система",
        "title": "Кессон с частотным преобразователем (ЧРП)",
        "essence": "Похожа на первый вариант (оборудование в кессоне или доме), но вместо стандартного реле давления используется частотный преобразователь. Насос плавно регулирует обороты в зависимости от того, сколько кранов открыто в доме.",
        "visual": "На схеме показан кессон, скважина и дом, но ключевой элемент — блок Частотного преобразователя (ЧРП) с цифровым дисплеем (частота тока плавно меняется от 35 до 50 Гц). Гидробак при этом используется компактный.",
        "animText": "Когда вы открываете один кран, насос в скважине крутится на малых оборотах, поддерживая идеальное постоянное давление без скачков. Если открыть второй кран (душ + кухня), частотный преобразователь автоматически увеличивает обороты насоса, обеспечивая стабильный напор воды без просадок."
    },
    "adapter": {
        "badge": "Вариант 3 • Бюджетная и скрытая схема",
        "title": "Скважинный адаптер (оборудование в доме)",
        "essence": "На поверхности нет громоздкого кессона — только аккуратный люк или оголовок. Соединение трубы со скважиной происходит под землей ниже глубины промерзания через специальный адаптер, а вся автоматика и гидробак выносятся в теплое помещение (в подвал или котельную дома).",
        "visual": "На поверхности земли видна лишь небольшая крышка скважины. Ниже уровня промерзания грунта на обсадной трубе смонтирован скважинный адаптер, от которого отходит подземная труба прямо в дом.",
        "animText": "Внутри отапливаемого помещения дома аккуратно размещены: большой гидробак, коллектор, фильтры и блок управления. При расходе воды сигнал поступает на погружный насос в скважине, вода по подземной трубе поступает в домовой узел и распределяется по точкам водоразбора (кухня, ванная). Это решение экономит место на участке и защищает оборудование от сырости."
    }
}

# Пользовательские позиции, добавленные через админку в базовые комплекты (kesson_vfd, kesson_ga, adapter, all_well) или доп. склад
CUSTOM_BUNDLE_ITEMS = []
SCHEME_DESCRIPTIONS = json.loads(json.dumps(DEFAULT_SCHEMES))

USERS_DISCOUNTS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_discounts.json")
# Словарь персональных условий: { "123456789": {"percent": -10.0, "note": "Постоянный монтажник"} }
# percent < 0 -> скидка (например, -10.0 означает скидку 10%)
# percent > 0 -> наценка (например, +5.0 означает наценку 5%)
USERS_DISCOUNTS = {}


def _normalize_tank_price(key: str, price: float) -> float:
    """Repairs tank prices corrupted by UI parse bug (e.g. 1908 → 190800)."""
    try:
        price = float(price)
    except (ValueError, TypeError):
        return 0.0
    ref = _BASE_TANK_REFERENCE_PRICES.get(key)
    if ref and ref > 0:
        ratio = price / float(ref)
        if 99.5 <= ratio <= 100.5:
            return float(ref)
    return price


def get_user_modifier(user_id) -> float:
    """Возвращает процент скидки (<0) или наценки (>0) для заданного Telegram ID."""
    if not user_id:
        return 0.0
    key = str(user_id).strip()
    entry = USERS_DISCOUNTS.get(key)
    if isinstance(entry, dict):
        try:
            return float(entry.get("percent", 0.0))
        except (ValueError, TypeError):
            return 0.0
    elif isinstance(entry, (int, float)):
        return float(entry)
    return 0.0


def set_user_modifier(user_id, percent: float, note: str = ""):
    """Устанавливает персональную скидку (<0) или наценку (>0) для Telegram ID."""
    key = str(user_id).strip()
    if not key or key == "0":
        return
    pct = round(float(percent), 2)
    if pct == 0.0 and not note:
        USERS_DISCOUNTS.pop(key, None)
    else:
        USERS_DISCOUNTS[key] = {
            "telegram_id": key,
            "percent": pct,
            "note": str(note or "").strip()
        }
    save_discounts_locally()


def remove_user_modifier(user_id):
    key = str(user_id).strip()
    USERS_DISCOUNTS.pop(key, None)
    save_discounts_locally()


def save_discounts_locally():
    try:
        with open(USERS_DISCOUNTS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(USERS_DISCOUNTS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DISCOUNTS SAVE ERR] {e}")
    return USERS_DISCOUNTS


def load_discounts_locally():
    if os.path.exists(USERS_DISCOUNTS_FILE_PATH):
        try:
            with open(USERS_DISCOUNTS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                USERS_DISCOUNTS.clear()
                for k, v in data.items():
                    ks = str(k).strip()
                    if isinstance(v, dict):
                        USERS_DISCOUNTS[ks] = {
                            "telegram_id": ks,
                            "percent": float(v.get("percent", 0.0)),
                            "note": str(v.get("note", ""))
                        }
                    else:
                        USERS_DISCOUNTS[ks] = {
                            "telegram_id": ks,
                            "percent": float(v),
                            "note": ""
                        }
        except Exception as e:
            print(f"[DISCOUNTS LOAD ERR] {e}")
    else:
        save_discounts_locally()



def is_owner_admin(user_id, init_data: str = "") -> bool:
    try:
        if user_id and int(str(user_id).strip()) == OWNER_ADMIN_ID:
            return True
    except (ValueError, TypeError):
        pass
    if init_data and f'"id":{OWNER_ADMIN_ID}' in init_data.replace(" ", ""):
        return True
    return False


def get_full_config(include_all_discounts: bool = False) -> dict:
    res = {
        "prices": PRICES,
        "kesson_models": KESSON_MODELS,
        "tank_catalog": TANK_CATALOG,
        "pump_catalog": PUMP_CATALOG,
        "extra_catalog": ALL_CATALOG_ITEMS,
        "services_catalog": SERVICES_CATALOG,
        "custom_bundle_items": CUSTOM_BUNDLE_ITEMS,
        "schemes": SCHEME_DESCRIPTIONS
    }
    if include_all_discounts:
        res["users_discounts"] = USERS_DISCOUNTS
    return res


def apply_config_dict(cfg: dict):
    """Применяет словарь конфигурации ко всем таблицам в памяти Python."""
    if not isinstance(cfg, dict):
        return

    if "prices" in cfg and isinstance(cfg["prices"], dict):
        for k, v in cfg["prices"].items():
            try:
                val = float(v)
                if k in _BASE_TANK_REFERENCE_PRICES:
                    val = _normalize_tank_price(k, val)
                PRICES[k] = val
            except (ValueError, TypeError):
                pass

    if "kesson_models" in cfg and isinstance(cfg["kesson_models"], dict):
        for k, v in cfg["kesson_models"].items():
            if isinstance(v, dict) and "name" in v:
                dp = float(v.get("dealer_price", v.get("price", 0)))
                rp = float(v.get("retail_price", round(dp / 0.6, 2) if dp else 0))
                KESSON_MODELS[k] = {
                    "name": str(v["name"]),
                    "price": dp,
                    "dealer_price": dp,
                    "retail_price": rp
                }
                PRICES[k] = dp
                ITEM_TRANSLATIONS.setdefault(k, {"ru": str(v["name"])})["ru"] = str(v["name"])

    if "tank_catalog" in cfg and isinstance(cfg["tank_catalog"], dict):
        for k, v in cfg["tank_catalog"].items():
            if isinstance(v, dict) and "name" in v:
                p = _normalize_tank_price(k, float(v.get("price", 0)))
                TANK_CATALOG[k] = {"name": str(v["name"]), "price": p}
                PRICES[k] = p
                ITEM_TRANSLATIONS.setdefault(k, {"ru": str(v["name"])})["ru"] = str(v["name"])

    if "pump_catalog" in cfg and isinstance(cfg["pump_catalog"], dict):
        for k, v in cfg["pump_catalog"].items():
            if isinstance(v, dict) and "name" in v:
                p = float(v.get("price", 0))
                PUMP_CATALOG[k] = {"name": str(v["name"]), "price": p}
                PRICES[k] = p
                ITEM_TRANSLATIONS.setdefault(k, {"ru": str(v["name"])})["ru"] = str(v["name"])

    if "extra_catalog" in cfg and isinstance(cfg["extra_catalog"], list):
        ALL_CATALOG_ITEMS.clear()
        for it in cfg["extra_catalog"]:
            if isinstance(it, dict) and "code" in it and "name" in it:
                p = float(it.get("price", 0))
                u = str(it.get("unit", "шт."))
                ALL_CATALOG_ITEMS.append({
                    "code": str(it["code"]),
                    "name": str(it["name"]),
                    "price": p,
                    "retail_price": float(it.get("retail_price", p)),
                    "unit": u,
                    "unit_key": "unit_m" if u in ["м", "м.п."] else "unit_pcs"
                })
                PRICES[str(it["code"])] = p

    if "services_catalog" in cfg and isinstance(cfg["services_catalog"], list):
        SERVICES_CATALOG.clear()
        for w in cfg["services_catalog"]:
            if isinstance(w, dict) and "code" in w and "name" in w:
                SERVICES_CATALOG.append({
                    "code": str(w["code"]),
                    "cat": str(w.get("cat", "kesson")),
                    "name": str(w["name"]),
                    "price": float(w.get("price", 0)),
                    "unit": str(w.get("unit", "усл."))
                })
                ITEM_TRANSLATIONS.setdefault(str(w["code"]), {"ru": str(w["name"])})["ru"] = str(w["name"])

    if "custom_bundle_items" in cfg and isinstance(cfg["custom_bundle_items"], list):
        CUSTOM_BUNDLE_ITEMS.clear()
        for b in cfg["custom_bundle_items"]:
            if isinstance(b, dict) and "name" in b:
                code = str(b.get("code") or f"custom_{len(CUSTOM_BUNDLE_ITEMS)+1}")
                p = float(b.get("price", 0))
                CUSTOM_BUNDLE_ITEMS.append({
                    "code": code,
                    "target": str(b.get("target", "all_well")),  # kesson_vfd, kesson_ga, adapter, all_well
                    "name": str(b["name"]),
                    "price": p,
                    "qty": float(b.get("qty", 1)),
                    "unit": str(b.get("unit", "шт"))
                })
                PRICES[code] = p

    if "schemes" in cfg and isinstance(cfg["schemes"], dict):
        for sk, sv in cfg["schemes"].items():
            if sk in SCHEME_DESCRIPTIONS and isinstance(sv, dict):
                for field in ["badge", "title", "essence", "visual", "animText"]:
                    if field in sv:
                        SCHEME_DESCRIPTIONS[sk][field] = str(sv[field])

    if "users_discounts" in cfg and isinstance(cfg["users_discounts"], dict):
        USERS_DISCOUNTS.clear()
        for k, v in cfg["users_discounts"].items():
            ks = str(k).strip()
            if not ks or ks == "0":
                continue
            if isinstance(v, dict):
                pct = float(v.get("percent", 0.0))
                note = str(v.get("note", ""))
            else:
                pct = float(v)
                note = ""
            if pct != 0.0 or note:
                USERS_DISCOUNTS[ks] = {"telegram_id": ks, "percent": pct, "note": note}
        save_discounts_locally()


def save_config_locally():
    cfg = get_full_config(include_all_discounts=True)
    save_discounts_locally()
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ADMIN CONFIG SAVE ERR] {e}")
    return cfg


def sync_config_to_cloud(cfg: dict):
    if not GOOGLE_SHEET_WEBHOOK:
        return
    def _send():
        try:
            requests.post(
                GOOGLE_SHEET_WEBHOOK,
                json={"action": "save_bot_config", "config_json": json.dumps(cfg, ensure_ascii=False)},
                timeout=12
            )
        except Exception as e:
            print(f"[CLOUD CONFIG SYNC ERR] {e}")
    threading.Thread(target=_send, daemon=True).start()


def load_config_on_startup():
    load_discounts_locally()
    # 1. Сначала загружаем локальный файл catalog_config.json, если он есть
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                local_cfg = json.load(f)
            apply_config_dict(local_cfg)
            print("[CONFIG] Локальный catalog_config.json успешно загружен.")
        except Exception as e:
            print(f"[CONFIG LOCAL LOAD ERR] {e}")
    else:
        save_config_locally()

    # 2. Пробуем фоново проверить актуальный конфиг из облака (Google Sheets Webhook), если настроен
    if GOOGLE_SHEET_WEBHOOK:
        def _fetch_cloud():
            try:
                resp = requests.post(GOOGLE_SHEET_WEBHOOK, json={"action": "get_bot_config"}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    cloud_cfg = data.get("config") or data.get("config_json")
                    if isinstance(cloud_cfg, str):
                        cloud_cfg = json.loads(cloud_cfg)
                    if isinstance(cloud_cfg, dict) and "prices" in cloud_cfg:
                        apply_config_dict(cloud_cfg)
                        save_config_locally()
                        print("[CONFIG] Облачный конфиг успешно синхронизирован.")
            except Exception:
                pass
        threading.Thread(target=_fetch_cloud, daemon=True).start()
