# LTE в РФ: только свой сервер (без Cloudflare)

Если на **LTE** не открывается `….workers.dev/health` — у оператора режется Cloudflare.  
**Worker и Render с телефона не спасут.** Нужен API **в России** с **HTTPS**.

---

## Шаг 1 — Сервер Timeweb (~5 мин)

1. [timeweb.cloud](https://timeweb.cloud) → **Облачные серверы** → **Создать**
2. **Ubuntu 22.04**, регион **Россия**, 1 CPU / 1 GB RAM
3. Запиши **IPv4** и пароль `root`

---

## Шаг 2 — Залить проект с Mac

На Mac:

```bash
cd /Users/administrator/Projects/mishka-kesson-app
cp env.timeweb.example .env
nano .env   # пароль ALEXEI_ICLOUD_PASSWORD и BREVO_* как на Render, IOS_API_ONLY=1

scp -r . root@ВАШ_IP:/opt/mishka
```

---

## Шаг 3 — Установка на сервере

```bash
ssh root@ВАШ_IP
cd /opt/mishka
bash scripts/vps-install.sh
```

Safari на **LTE**: `http://ВАШ_IP:8080/health` — должен быть JSON.

> iOS из коробки любит **HTTPS**. HTTP по IP — для проверки; в проде — шаг 4.

---

## Шаг 4 — HTTPS (обязательно для приложения)

Нужен **домен** (Timeweb / REG.RU), A-запись на IP сервера.

На сервере (подставь домен):

```bash
apt-get install -y nginx certbot python3-certbot-nginx
```

`/etc/nginx/sites-available/mishka`:

```nginx
server {
    listen 80;
    server_name api.ВАШ-ДОМЕН.ru;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
```

```bash
ln -sf /etc/nginx/sites-available/mishka /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d api.ВАШ-ДОМЕН.ru
```

Проверка LTE: `https://api.ВАШ-ДОМЕН.ru/health`

---

## Шаг 5 — iPhone

1. `Info.plist` → **MishkaAPIBaseURLs** → `https://api.ВАШ-ДОМЕН.ru`
2. В приложении тот же URL → **Сбросить кэш**
3. ⌘R на телефон

**Brevo** → Authorized IPs → IP VPS.

---

## Пока нет домена

- Склад **на Wi‑Fi** можно пробовать Worker (если `/health` на Wi‑Fi открывается)
- На **LTE** без домена и HTTPS нормально в App Store-сборку не закрыть — домен всё равно нужен

---

## Данные с Render

Скачай `catalog_config.json` с Render (если есть) → `/opt/mishka/` на VPS → `docker compose restart`