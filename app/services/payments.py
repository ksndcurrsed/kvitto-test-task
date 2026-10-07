from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Tariff
from app.schemas import PaymentCreate
from app.services.payment_rules import build_schedule, calculate_discount


class UnknownPromoCodeError(ValueError):
    pass


async def create_payment(
    session: AsyncSession, payload: PaymentCreate, idempotency_key: str | None
) -> tuple[Payment, bool]:
    if idempotency_key:
        existing = await session.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
        if existing:
            return existing, True

    tariff = await session.get(Tariff, payload.tariff_id)
    if tariff is None:
        raise LookupError("tariff_not_found")
    try:
        discount, amount = calculate_discount(tariff.price, payload.promo_code)
    except ValueError as exc:
        raise UnknownPromoCodeError(str(exc)) from exc
    schedule = build_schedule(amount, payload.installment_months) if payload.method.value == "installment" else None
    payment = Payment(
        status="pending",
        tariff_id=tariff.id,
        amount=amount,
        discount=discount,
        method=payload.method.value,
        installment_months=payload.installment_months,
        schedule=schedule,
        email=str(payload.email),
        idempotency_key=idempotency_key,
    )
    session.add(payment)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        if idempotency_key:
            existing = await session.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
            if existing:
                return existing, True
        raise
    await session.refresh(payment)
    return payment, False
