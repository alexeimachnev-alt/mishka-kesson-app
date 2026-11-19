# Native iOS REST API (ПК «МИШКА»)

Base URL: `https://mishka-kesson-app.onrender.com`

All JSON requests use `Content-Type: application/json`. Authenticated calls may pass `Authorization: Bearer <token>` or `token` in the JSON body.

## Auth (email OTP)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/send_email_code` | Body: `{ "email": "client@mail.ru" }` — sends 4-digit OTP via SMTP |
| POST | `/api/auth/verify_email_code` | Body: `{ "email", "code", "name?", "company?", "phone" }` — verify OTP, register/login |
| POST | `/api/auth/login` | Staff: `{ "email", "password", "mode": "login" }` — password login for built-in staff |
| POST | `/api/auth/staff_quick` | Dev: `{ "role": "owner\|manager\|warehouse\|client" }` — internal test login |

## Catalog & calculation

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config?user_id=` | Full catalog + personal modifier; owner gets all discounts |
| POST | `/api/calculate` | Well/kesson estimate (same payload as Telegram mini-app) |
| POST | `/api/admin/save_config` | Owner/admin: `{ "user_id", "role", "config" }` |
| POST | `/api/admin/user_discount` | Owner/admin: set/remove client discount |

## Orders

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/ios/orders?role=&email=&phone=&user_id=` | List orders (staff: all; client: own) |
| POST | `/api/ios/create_order` | Place order from iOS (alias of mini-app payload) |
| POST | `/api/admin/toggle_item` | Warehouse checklist toggle |
| POST | `/api/admin/update_order` | Status: `completed`, `paid`, `cancelled` + payment/cancel reason |

## Render environment variables

```bash
# Required (existing)
TELEGRAM_BOT_TOKEN=...
RENDER_EXTERNAL_URL=https://mishka-kesson-app.onrender.com

# SMTP (email OTP for iOS clients)
SMTP_EMAIL=your-login@yandex.ru
SMTP_PASSWORD=your-app-password
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
EMAIL_OTP_TTL=600

# Optional staff passwords (defaults in code if unset)
OWNER_PASSWORD=551209
ARTUR_PASSWORD=447208
SKLAD_PASSWORD=840231
```

### Yandex Mail setup

1. Enable IMAP/SMTP in Yandex mailbox settings.
2. Create an **app password** (not the main mailbox password).
3. Set `SMTP_EMAIL` to the mailbox address and `SMTP_PASSWORD` to the app password.

### Gmail alternative

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
```

Use a [Google App Password](https://myaccount.google.com/apppasswords) with 2FA enabled.