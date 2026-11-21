# Native iOS + Render

Base URL (Render): `https://mishka-kesson-app.onrender.com`

## iPhone не достучится до onrender.com (TCP RST, -1001)

С Mac `curl /health` часто **200**, с iPhone — **таймаут**: провайдер режет **onrender.com**.

**Бесплатно:** прокси [Cloudflare Workers](../cloudflare-worker/README.md) — приложение ходит на `*.workers.dev`, worker дергает Render (Brevo/env не переносим).

1. `cd cloudflare-worker && npx wrangler deploy`
2. Safari на iPhone: `https://<ваш-worker>.workers.dev/health`
3. `MishkaKesson/Info.plist` → `MishkaAPIBaseURLs` — первой строкой worker URL
4. ⌘R в Xcode

Приложение само перебирает адреса из plist + запасной Render.

## Почта (обязательно для регистрации)

В **Render → Environment** задайте:

| Переменная | Пример |
|------------|--------|
| `BREVO_API_KEY` | `xkeysib-…` (Transactional → API keys, право **Send emails**) |
| `BREVO_SENDER_EMAIL` | подтверждённый отправитель в Brevo → Senders |
| `BREVO_SENDER_NAME` | `ПК МИШКА` |
| `BREVO_SMTP_KEY` | только **не на Render** (VPS): `xsmtpsib-…` |
| `BREVO_SMTP_LOGIN` | логин из Brevo → SMTP |

**Render блокирует исходящий SMTP** (таймаут ~15 с). На Render письма **только через `BREVO_API_KEY` (xkeysib)**.  
Ошибка «Brevo SMTP: timed out» = не настройка логина, а лимит платформы.

### 401 и `unrecognised IP address` (часто на Render)

Ключ **может быть правильным**. Brevo режет **IP Render** (`74.220.49.x`).

1. Почта от Brevo — подтвердить неизвестный IP.  
2. **app.brevo.com** → **Security** → **Authorized IPs** — **выключить** ограничение (для serverless IP плавающий).  
3. Повторить `curl … send_email_code`.

Проверка после деплоя:

```bash
curl -s https://mishka-kesson-app.onrender.com/health
curl -s -X POST https://mishka-kesson-app.onrender.com/api/auth/send_email_code \
  -H 'Content-Type: application/json' -d '{"email":"ваш@email.ru"}'
```

`/health`: `"brevo_auth_ok":true` (probe реальной отправки).  
`send_email_code`: `"status":"ok"`, не 401.

Тест кода:

```bash
curl -s -X POST https://mishka-kesson-app.onrender.com/api/auth/send_email_code \
  -H 'Content-Type: application/json' \
  -d '{"email":"ваш@email.ru"}'
```

`"smtp_active":true` — письмо ушло; `503` — почта не настроена или Brevo отклонил отправку.

## Auth API

| Method | Path |
|--------|------|
| POST | `/api/auth/send_email_code` |
| POST | `/api/auth/verify_email_code` |
| POST | `/api/auth/login` |
| POST | `/api/auth/request_password_reset` |
| POST | `/api/auth/confirm_password_reset` |

## Деплой

1. Push в GitHub → Render **Manual Deploy** (или auto).
2. Убедиться, что в репозитории есть `brevo_mail.py`.
3. Переменные Brevo на Render.
4. В Brevo: отправитель верифицирован, лимиты API не исчерпаны.