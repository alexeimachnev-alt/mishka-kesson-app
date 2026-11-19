# Native iOS + Render

Base URL: `https://mishka-kesson-app.onrender.com`

## Почта (обязательно для регистрации)

В **Render → Environment** задайте:

| Переменная | Пример |
|------------|--------|
| `BREVO_API_KEY` | ключ из [Brevo](https://app.brevo.com) → SMTP & API → API keys |
| `BREVO_SENDER_EMAIL` | подтверждённый отправитель (например `noreply@mishka.ru`) |
| `BREVO_SENDER_NAME` | `ПК МИШКА` |

Проверка после деплоя:

```bash
curl -s https://mishka-kesson-app.onrender.com/health
```

Ожидается `"email_delivery":"brevo"`, `"brevo_auth_ok":true`, `"ios_api_version":2`.

Если **`brevo_auth_ok":false`** или в приложении ошибка **401**:
- В Brevo → **Transactional** → **API keys** создайте ключ вида `xkeysib-…` (не SMTP-пароль).
- Render → **Environment**: `BREVO_API_KEY` — вставить **без кавычек и переносов строк**.
- `BREVO_SENDER_EMAIL` — адрес **подтверждён** в Brevo (Senders).
- **Manual Deploy** после сохранения env.

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