# Kvitto Payments API

FastAPI-сервис для создания платежей онлайн-школы. Все суммы передаются и хранятся в копейках целыми числами.

## Запуск

Нужны Docker и Docker Compose:

```bash
docker compose up --build
```

API будет доступен на `http://localhost:8000`, документация - на `/docs`.

Переменные окружения:

- `DATABASE_URL` - PostgreSQL URL, по умолчанию `postgresql+asyncpg://kvitto:kvitto@localhost:5432/kvitto`.
- `WEBHOOK_SECRET` - секрет HMAC для банковского webhook.

## Тесты

Unit-тесты запускаются так:

```bash
python -m pytest -q
```

Для интеграционных тестов нужен PostgreSQL и переменная `TEST_DATABASE_URL`, например:

```bash
set TEST_DATABASE_URL=postgresql+asyncpg://kvitto:kvitto@localhost:5432/kvitto
set DATABASE_URL=%TEST_DATABASE_URL%
python -m pytest -q
```

Миграции Alembic намеренно не используются: таблицы и начальные тарифы создаются при старте приложения.

## Примеры

Получить тарифы:

```bash
curl http://localhost:8000/tariffs
```

Создать платёж standard со скидкой и рассрочкой:

```bash
curl -X POST http://localhost:8000/payments ^
  -H "Content-Type: application/json" ^
  -H "Idempotency-Key: order-1001" ^
  -d "{\"tariff_id\":2,\"email\":\"student@example.com\",\"method\":\"installment\",\"installment_months\":3,\"promo_code\":\"kvitto10\"}"
```

Проверить платёж:

```bash
curl http://localhost:8000/payments/1
```

Webhook требует HMAC-SHA256 подпись тела запроса в заголовке `X-Signature`:

```bash
curl -X POST http://localhost:8000/webhooks/bank ^
  -H "Content-Type: application/json" ^
  -H "X-Signature: <hex-hmac-sha256>" ^
  -d "{\"payment_id\":1,\"status\":\"succeeded\"}"
```
