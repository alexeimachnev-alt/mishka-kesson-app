FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py brevo_mail.py calc_module.py calc_well.py calc_extras.py delivery_module.py \
    warehouse_items.py ios_push.py admin_config.py ios_auth_helpers.py repo_constants.py constants.py ./
COPY templates/ ./templates/
COPY app.html ./

EXPOSE 8080

# Один worker: заказы в памяти (ACTIVE_ORDERS), иначе «Заказ не найден» при чередовании запросов.
CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 120 app:app