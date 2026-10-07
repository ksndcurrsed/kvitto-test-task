import pytest
from sqlalchemy import delete, select

from app.database import SessionLocal, engine, init_db
from app.models import Payment, Tariff

pytestmark = pytest.mark.skipif(
    not __import__("os").getenv("TEST_DATABASE_URL"),
    reason="set TEST_DATABASE_URL to run PostgreSQL integration tests",
)


@pytest.mark.asyncio
async def test_init_db_is_repeatable_and_seeds_exact_tariffs() -> None:
    await init_db()
    await init_db()
    async with SessionLocal() as session:
        await session.execute(delete(Payment))
        await session.commit()
        tariffs = list((await session.scalars(select(Tariff).order_by(Tariff.id))).all())
    assert [(tariff.title, tariff.price) for tariff in tariffs] == [
        ("basic", 990_000),
        ("standard", 1_990_000),
        ("premium", 2_990_000),
    ]


@pytest.fixture(scope="session", autouse=True)
async def dispose_engine() -> None:
    yield
    await engine.dispose()
