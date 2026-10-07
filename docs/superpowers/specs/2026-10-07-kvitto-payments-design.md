# Kvitto Payments API Design

## Goal

Build a small FastAPI payment service for an online school. The service must calculate money exactly in kopecks, support idempotent payment creation, installment schedules, constrained payment-status transitions, bank webhooks, and the optional filtering/signature features from the assignment.

The implementation includes PostgreSQL, Docker Compose, tests, README, and `AI_LOG.md`. It explicitly excludes Alembic migrations, GitHub Actions, and repository-specific assistant rules, as requested.

## Scope and API

### Tariffs

`GET /tariffs` returns the seeded tariffs as `{id, title, price}`. Startup seeding is idempotent and uses integer kopecks:

- `basic`: 990000
- `standard`: 1990000
- `premium`: 2990000

### Create payment

`POST /payments` accepts `tariff_id`, `email`, `method`, optional `installment_months`, and optional `promo_code`.

- `method` is one of `card`, `sbp`, or `installment`.
- `installment_months` is required for installment payments and must be 3, 6, or 12.
- For non-installment payments, `installment_months` is omitted/null and `schedule` is null.
- `KVITTO10` is case-insensitive and gives a 10% discount. Unknown promo codes produce the standard FastAPI 422 response.
- All amounts are integer kopecks. The installment schedule divides the discounted amount exactly; remainder kopecks go to the earliest installments.
- New payments start as `pending`.
- If `Idempotency-Key` is present and already belongs to a payment, return that same payment with status 200. A new payment returns 201. The key is scoped to the payment record and protected by a database uniqueness constraint.

### Read payments

`GET /payments/{id}` returns a payment or 404. The optional bonus endpoint `GET /payments` supports exact `email` and `status` filters.

Payment responses contain `id`, `status`, `tariff_id`, `amount`, `discount`, `method`, `installment_months`, `schedule`, `email`, and `created_at`.

### Bank webhook

`POST /webhooks/bank` accepts `payment_id` and a target status. Existing payments use the allowed transitions `pending -> succeeded`, `pending -> failed`, and `succeeded -> refunded`; all other transitions return `409` with `{ "error": "invalid_transition" }` without changing the payment.

For the optional signature bonus, the endpoint requires `X-Signature` to equal the lowercase hexadecimal HMAC-SHA256 of the exact request body using `WEBHOOK_SECRET`. Missing or invalid signatures return 401. The signature check uses constant-time comparison.

## Architecture

The application is split into configuration, database/session handling, ORM models, request/response schemas, focused business services, and route modules. Routes own HTTP concerns and delegate calculations, idempotency, and transition validation to services. SQLAlchemy 2 async sessions are used with PostgreSQL via `asyncpg`.

Tables are created at startup with SQLAlchemy metadata because migrations are intentionally out of scope. Tariff seeding runs in the same startup initialization and is safe to repeat.

The payment row stores the final `amount`, integer `discount`, method, optional installment term, schedule as a JSON list of integers, and the nullable idempotency key. The database uses a unique constraint on the idempotency key while allowing nulls.

## Validation and errors

Pydantic v2 validates enum values, installment rules, email shape, and positive tariff IDs. Unknown tariffs and missing payments return 404. Invalid promo codes and malformed request bodies use FastAPI's default 422 format. Invalid status transitions are the only business conflict and return the specified 409 body. Webhook authentication happens before mutation.

## Testing strategy

Tests use pytest and httpx against an isolated PostgreSQL test database when Docker is available. The core calculation and transition functions also have unit coverage so money rules can be verified without HTTP. Required scenarios cover discounted and undiscounted amounts, lowercase promo codes, exact schedules for 3/6/12 months, idempotency, forbidden transitions, missing payments, and filtering. Bonus scenarios cover valid/invalid HMAC signatures and the payment list filters.

## Operational files

- `Dockerfile` builds the API image.
- `docker-compose.yml` runs PostgreSQL and the API, wiring `DATABASE_URL` and `WEBHOOK_SECRET`.
- `README.md` documents `docker compose up`, tests, environment variables, and curl examples.
- `AI_LOG.md` records tools/models, representative prompts/context, and at least one model mistake found during verification.

## Explicit exclusions

Do not add Alembic migrations, GitHub Actions workflows, or assistant-rule files such as `CLAUDE.md`/`.cursorrules`.
