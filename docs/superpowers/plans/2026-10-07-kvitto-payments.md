# Kvitto Payments API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the specified FastAPI payment API with PostgreSQL, Docker Compose, exact kopeck calculations, idempotency, status transitions, signed bank webhooks, filters, tests, README, and AI_LOG.

**Architecture:** Use a small `app` package split into config/database, SQLAlchemy models, Pydantic schemas, pure payment business logic, and route modules. Use async SQLAlchemy with PostgreSQL/asyncpg; create schema and seed tariffs during application startup because Alembic is excluded. Test pure rules directly and HTTP behavior through httpx against a disposable PostgreSQL database.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg, PostgreSQL, pytest, httpx, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-07-kvitto-payments-design.md`

## Global Constraints

- Store and expose every monetary value as a non-negative integer number of kopecks; never use float.
- Seed `basic=990000`, `standard=1990000`, and `premium=2990000` idempotently at startup.
- Accept methods `card`, `sbp`, and `installment`; installment terms are exactly 3, 6, or 12.
- Apply `KVITTO10` case-insensitively as a 10% discount; unknown promo codes return standard FastAPI 422.
- Put remainder kopecks in the first installment entries and make schedule sum equal amount exactly.
- Allow only `pending -> succeeded`, `pending -> failed`, and `succeeded -> refunded`.
- Return an existing payment with 200 for a repeated `Idempotency-Key`; create a new payment with 201.
- Implement HMAC-SHA256 `X-Signature` verification using `WEBHOOK_SECRET` and constant-time comparison.
- Do not add Alembic, GitHub Actions, or assistant-rule files.

## Review Focus

- Concurrent/repeated idempotent creates must not duplicate rows: test unique-key behavior and same response payload.
- A discount must be calculated from integer kopecks without float rounding: test 10% on each seeded tariff.
- Installment remainder placement must be deterministic: assert exact schedules and sums for 3, 6, and 12.
- A rejected webhook must not mutate the status: assert status remains unchanged after 409 and 401.
- Startup must be repeatable: run initialization twice and assert exactly three tariffs.

### Task 1: Project scaffold and configuration

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces `Settings` with `database_url` and `webhook_secret` loaded from environment.

- [ ] **Step 1: Write the failing import/config test**

  Add a test asserting `Settings(database_url=..., webhook_secret=...)` stores values and defaults `webhook_secret` to a documented development value only when explicitly allowed by config.

- [ ] **Step 2: Run the focused test to verify it fails**

  Run `pytest tests/test_config.py -q`; expect import failure because `app.config` does not exist.

- [ ] **Step 3: Implement configuration and dependency metadata**

  Define typed settings with `pydantic-settings`; configure package/test commands and pinned minimum dependencies.

- [ ] **Step 4: Run the focused test**

  Run `pytest tests/test_config.py -q`; expect PASS.

### Task 2: Pure money, promo, schedule, and status rules

**Files:**
- Create: `app/services/payment_rules.py`
- Test: `tests/test_payment_rules.py`

**Interfaces:**
- Produces `calculate_discount(price: int, promo_code: str | None) -> tuple[int, int]`.
- Produces `build_schedule(amount: int, months: int) -> list[int]`.
- Produces `is_valid_transition(current: str, target: str) -> bool`.

- [ ] **Step 1: Write failing tests**

  Cover full prices and `kvitto10`/`KVITTO10`, unknown promo error, exact schedules for 3/6/12 including remainder-first allocation, invalid term, and the complete allowed transition matrix.

- [ ] **Step 2: Run `pytest tests/test_payment_rules.py -q` and verify RED**

  Expect missing-module or missing-function failures.

- [ ] **Step 3: Implement minimal integer-only rules**

  Use integer arithmetic for `discount = price // 10`, `amount = price - discount`; distribute `amount // months` plus one to the first `amount % months` entries. Raise a domain `ValueError` for unknown promo/invalid term and keep transitions in an explicit mapping.

- [ ] **Step 4: Run the focused tests and full unit file**

  Run `pytest tests/test_payment_rules.py -q`; expect all PASS.

### Task 3: Database models, startup initialization, and schemas

**Files:**
- Create: `app/database.py`
- Create: `app/models.py`
- Create: `app/schemas.py`
- Test: `tests/test_database_init.py`

**Interfaces:**
- Produces async `get_session()` dependency.
- Produces async `init_db()` that creates tables and seeds exactly three tariffs idempotently.
- Produces ORM models `Tariff` and `Payment` with unique nullable `idempotency_key`.
- Produces response/request schemas matching the assignment field names.

- [ ] **Step 1: Write the failing initialization/model tests**

  Against a PostgreSQL test URL, call `init_db()` twice and assert three tariffs, the exact integer prices, and that a payment can persist a JSON integer schedule and nullable idempotency key.

- [ ] **Step 2: Run the database test to verify RED**

  Run `pytest tests/test_database_init.py -q`; expect missing application modules or tables.

- [ ] **Step 3: Implement async engine, models, and schemas**

  Use `create_async_engine`, `async_sessionmaker`, `JSON`, UTC timestamps, enum-compatible string columns, and SQLAlchemy metadata creation. Add Pydantic validators for email, method, installment term, and positive tariff ID.

- [ ] **Step 4: Run database tests**

  Run `pytest tests/test_database_init.py -q`; expect PASS with PostgreSQL available.

### Task 4: Payment service and tariff/payment routes

**Files:**
- Create: `app/services/payments.py`
- Create: `app/api/tariffs.py`
- Create: `app/api/payments.py`
- Test: `tests/test_payments_api.py`

**Interfaces:**
- Produces `POST /payments`, `GET /payments`, `GET /payments/{id}`, and `GET /tariffs`.
- Service creates payments from a tariff, calculates amount/discount/schedule, and resolves idempotency before creating a row.

- [ ] **Step 1: Write failing HTTP tests**

  Assert tariff response, undiscounted and discounted payment amounts, lowercase promo behavior, all installment terms, invalid promo/term 422, unknown tariff 404, missing payment 404, idempotent second create 200 with one row, and email/status filters.

- [ ] **Step 2: Run `pytest tests/test_payments_api.py -q` and verify RED**

  Expect route/module/endpoint failures.

- [ ] **Step 3: Implement service and routes**

  Use a transaction per request. For an idempotency race, catch the unique-key integrity error, roll back, reload the existing payment, and return it as a replay. Map domain errors to the required HTTP status and serialize ORM models through response schemas.

- [ ] **Step 4: Run focused API tests**

  Run `pytest tests/test_payments_api.py -q`; expect PASS.

### Task 5: Webhook status transitions and HMAC security

**Files:**
- Create: `app/api/webhooks.py`
- Modify: `app/main.py`
- Test: `tests/test_webhooks_api.py`

**Interfaces:**
- Produces `POST /webhooks/bank` returning `{ "result": "ok" }` on success or `{ "error": "invalid_transition" }` with 409.

- [ ] **Step 1: Write failing webhook tests**

  Cover a valid signed transition, missing/invalid signature 401, unknown payment 404, forbidden transition 409, and unchanged status after rejection.

- [ ] **Step 2: Run `pytest tests/test_webhooks_api.py -q` and verify RED**

  Expect missing route/endpoint failures.

- [ ] **Step 3: Implement exact-body HMAC verification and transition route**

  Read raw request bytes, compare `hmac.new(secret, body, sha256).hexdigest()` with `X-Signature` using `hmac.compare_digest`, then load and mutate only on a valid allowed transition.

- [ ] **Step 4: Run webhook tests**

  Run `pytest tests/test_webhooks_api.py -q`; expect PASS.

### Task 6: Application lifecycle, Docker, documentation, and AI log

**Files:**
- Create: `app/main.py`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `README.md`
- Create: `AI_LOG.md`
- Create: `.dockerignore`
- Test: `tests/test_app.py`

**Interfaces:**
- Produces `app.main:create_app()`/`app.main:app` with startup initialization and all routers mounted.

- [ ] **Step 1: Write failing app smoke test**

  Assert the app exposes OpenAPI routes for all required endpoints and startup initialization is wired through the lifespan.

- [ ] **Step 2: Run the smoke test to verify RED**

  Run `pytest tests/test_app.py -q`; expect missing `app.main` or routes.

- [ ] **Step 3: Implement app lifecycle and container files**

  Add lifespan calling `init_db`, a PostgreSQL healthcheck, API dependency wiring, and an API command that binds `0.0.0.0:8000`. Document environment variables, Docker startup, tests, and curl examples. Record actual prompts, tools, model usage, and verification findings in `AI_LOG.md`.

- [ ] **Step 4: Run smoke test and inspect configuration**

  Run `pytest tests/test_app.py -q` and `docker compose config`; expect PASS and valid Compose output.

### Task 7: Full verification and final review

**Files:**
- Modify: any files required by verification failures only.

- [ ] **Step 1: Run the complete test suite**

  Run `pytest -q`; record the exact result and fix failures with regression tests.

- [ ] **Step 2: Run static/packaging checks**

  Run `python -m compileall app tests` and `docker compose config`; expect exit code 0.

- [ ] **Step 3: Run the Docker smoke test**

  Run `docker compose up --build -d`, query `/tariffs` and one payment flow, then run `docker compose down` and record results.

- [ ] **Step 4: Check scope and review focus**

  Confirm no Alembic files, GitHub Actions workflow, or assistant-rule files were added; inspect `git diff --stat`/working tree and verify all requirements map to implementation and tests.
