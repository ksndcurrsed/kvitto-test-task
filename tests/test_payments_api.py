import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="set TEST_DATABASE_URL to run PostgreSQL integration tests")


@pytest.fixture
async def client():
    from app.database import SessionLocal, init_db
    from app.main import create_app
    from app.models import Payment
    await init_db()
    async with SessionLocal() as session:
        await session.execute(delete(Payment))
        await session.commit()
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_create_payment_applies_lowercase_promo_and_exact_schedule(client: AsyncClient) -> None:
    response = await client.post("/payments", json={"tariff_id": 2, "email": "student@example.com", "method": "installment", "installment_months": 3, "promo_code": "kvitto10"})
    assert response.status_code == 201
    assert response.json()["amount"] == 1_791_000
    assert response.json()["discount"] == 199_000
    assert response.json()["schedule"] == [597_000, 597_000, 597_000]


@pytest.mark.asyncio
async def test_repeated_idempotency_key_returns_same_payment(client: AsyncClient) -> None:
    payload = {"tariff_id": 1, "email": "one@example.com", "method": "card"}
    first = await client.post("/payments", json=payload, headers={"Idempotency-Key": "same-key"})
    second = await client.post("/payments", json=payload, headers={"Idempotency-Key": "same-key"})
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_filters_and_missing_payment(client: AsyncClient) -> None:
    await client.post("/payments", json={"tariff_id": 1, "email": "filter@example.com", "method": "sbp"})
    filtered = await client.get("/payments", params={"email": "filter@example.com", "status": "pending"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert (await client.get("/payments/999999")).status_code == 404
