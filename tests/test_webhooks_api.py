import hashlib
import hmac
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


def sign(body: bytes) -> str:
    return hmac.new(os.getenv("WEBHOOK_SECRET", "change-me").encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_invalid_transition_returns_409_without_mutation(client: AsyncClient) -> None:
    payment = await client.post("/payments", json={"tariff_id": 1, "email": "bank@example.com", "method": "card"})
    payment_id = payment.json()["id"]
    body = b'{"payment_id":%d,"status":"refunded"}' % payment_id
    response = await client.post("/webhooks/bank", content=body, headers={"X-Signature": sign(body)})
    assert response.status_code == 409
    assert response.json() == {"error": "invalid_transition"}
    assert (await client.get(f"/payments/{payment_id}")).json()["status"] == "pending"


@pytest.mark.asyncio
async def test_missing_signature_is_unauthorized(client: AsyncClient) -> None:
    body = b'{"payment_id":1,"status":"succeeded"}'
    response = await client.post("/webhooks/bank", content=body)
    assert response.status_code == 401
