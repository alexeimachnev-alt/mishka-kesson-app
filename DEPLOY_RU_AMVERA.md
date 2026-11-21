# Этап 1: API в РФ (Amvera) — пошагово

Цель: iPhone в России **без VPN**, заказы и сборка в приложении.

---

## Шаг 1 — Сегодня, 15 мин (продолжать работать на Render)

Пока Amvera не готова:

1. Убедись, что Worker задеплоен: `cd cloudflare-worker && npx wrangler deploy`
2. На iPhone Safari: `https://mishka.alexeimachnev.workers.dev/health` → JSON `ok`
3. В приложении «Адрес API» → этот URL → **Сбросить кэш** → вход сотрудника

---

## Шаг 2 — Amvera (30–45 мин)

1. Зарегистрируйся: [amvera.ru](https://amvera.ru)
2. **Создать проект** → **Из Git** (GitHub `mishka-kesson-app`) или **Docker**
3. Если Git:
   - Корень репозитория
   - Сборка: **Dockerfile** (в корне репо)
   - Порт контейнера: **8080** (или переменная `PORT`)
4. **Диск / постоянное хранилище** (если есть в тарифе):
   - Смонтировать в `/app/data`
   - Позже: `catalog_config.json`, `ios_users.json` (пока можно без — каталог пересоздаётся)

---

## Шаг 3 — Переменные окружения

Скопируй с **Render → Environment** в Amvera (см. `env.amvera.example`):

| Переменная | Обязательно |
|------------|-------------|
| `BREVO_API_KEY` | да |
| `BREVO_SENDER_EMAIL` | да |
| `BREVO_SENDER_NAME` | да |
| `TELEGRAM_BOT_TOKEN` | если бот нужен |
| `ADMIN_CHAT_ID` | `551209811` |
| `ALEXEI_ICLOUD_PASSWORD` | да (iOS вход) |

После деплоя в **Brevo → Security → Authorized IPs** добавь **внешний IP Amvera**  
(или отключи жёсткий whitelist, как на Render).

---

## Шаг 4 — Деплой и проверка

1. **Deploy** в Amvera, дождись зелёного статуса.
2. Скопируй URL вида `https://<имя-проекта>-<user>.amvera.io`
3. С **iPhone без VPN**:
   ```text
   https://<amvera-url>/health
   ```
4. Тест входа:
   ```bash
   curl -s -X POST 'https://<amvera-url>/api/auth/login' \
     -H 'Content-Type: application/json' \
     -d '{"email":"alexeimachnev@icloud.com","password":"ВАШ_ПАРОЛЬ"}'
   ```
   Ответ: `"status":"ok"` и `data.token`.

---

## Шаг 5 — Прописать URL в iOS

Xcode → `MishkaKesson/Info.plist` → **MishkaAPIBaseURLs**:

```xml
<key>MishkaAPIBaseURLs</key>
<array>
  <string>https://ВАШ-ПРОЕКТ.amvera.io</string>
</array>
```

Убери зависимость от `onrender.com` как единственного адреса.

⌘R → на входе проверь, что «Адрес API» совпадает → **Сбросить кэш** → вход / заказ.

---

## Шаг 6 — Данные с Render (если нужны старые заказы)

1. С Render скачай файлы (если были): `catalog_config.json`, `ios_users.json`
2. Положи на том Amvera (SSH/файловый менеджер) в `/app` или примонтированный диск
3. Рестарт контейнера

---

## Шаг 7 — Следующий этап (мы сделаем в коде)

- Apple Push вместо Telegram для статусов заказа
- Флаг `TELEGRAM_NOTIFY=0` (только iOS + email)

---

## Если Amvera не подойдёт

Тот же **Dockerfile** на VPS Timeweb/Selectel:

```bash
docker build -t mishka-api .
docker run -d -p 8080:8080 --env-file .env mishka-api
```

Домен `api.ваш-домен.ru` → nginx → `localhost:8080`.