# С нуля: API в РФ без Amvera

Два пути. **Сначала путь 1** (10 минут), потом **путь 2** (надёжно).

---

## Путь 1 — Cloudflare Worker (пока нет своего сервера)

1. На Mac:
   ```bash
   cd cloudflare-worker
   npx wrangler deploy
   ```
2. iPhone Safari (без VPN):  
   `https://mishka.alexeimachnev.workers.dev/health`
3. iOS: **Адрес API** = этот URL → **Сбросить кэш**

Render остаётся «мозгом», Worker — вход из РФ.

---

## Путь 2 — Timeweb Cloud VPS (рекомендуем)

### Шаг A — VPS (5–10 мин)

1. [timeweb.cloud](https://timeweb.cloud) → регистрация
2. **Облачные серверы** → создать:
   - Ubuntu **22.04**
   - 1 vCPU, 1–2 GB RAM
   - регион **Россия**
3. Записать **публичный IPv4** и пароль root (или SSH-ключ)

### Шаг B — Подключение по SSH (на Mac)

```bash
ssh root@ВАШ_IP
```

### Шаг C — Docker (на сервере, один раз)

```bash
apt update && apt install -y docker.io docker-compose-v2 git
systemctl enable --now docker
```

### Шаг D — Код на сервер

**Вариант 1 — git** (если репозиторий на GitHub):

```bash
cd /opt
git clone https://github.com/ВАШ_ЛОГИН/mishka-kesson-app.git mishka
cd mishka
```

**Вариант 2 — с Mac без публичного git:**

```bash
# на Mac, из папки проекта:
scp -r /Users/administrator/Projects/mishka-kesson-app root@ВАШ_IP:/opt/mishka
ssh root@ВАШ_IP
cd /opt/mishka
```

### Шаг E — Переменные

```bash
cp env.timeweb.example .env
nano .env
```

Минимум заполнить:

- `ALEXEI_ICLOUD_PASSWORD` — как на Render
- `BREVO_*` — как на Render  
- Оставить `IOS_API_ONLY=1` (бот Telegram на этом сервере не нужен)

### Шаг F — Запуск

```bash
docker compose up -d --build
docker compose logs -f
```

Лог без `Worker failed to boot` → ок.

### Шаг G — Проверка

С iPhone (без VPN):

```text
http://ВАШ_IP:8080/health
```

Должен быть JSON `"status":"ok"`.

### Шаг H — Красивый HTTPS (по желанию)

Купи домен (Timeweb / REG.RU), A-запись на `ВАШ_IP`, на сервере nginx + certbot.  
Пока можно жить на `http://IP:8080` только для теста; в iOS лучше **https** — тогда домен обязателен.

### Шаг I — iOS

`Info.plist` → **MishkaAPIBaseURLs**:

```xml
<string>https://api.твой-домен.ru</string>
```

или на время теста (если разрешите HTTP в настройках) IP — лучше сразу HTTPS.

В приложении: **Сбросить кэш** → вход `alexeimachnev@icloud.com`.

### Brevo

В Brevo → **Authorized IPs** добавь **IP VPS**.

---

## Что отключить на Render (когда VPS живой)

1. Остановить сервис на Render **или** оставить только как резерв
2. Worker можно оставить — переключить backend URL в `cloudflare-worker` на новый API (опционально)

---

## Amvera

Можно не трогать или удалить проект — для этого плана не нужна.