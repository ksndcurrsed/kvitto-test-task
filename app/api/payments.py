from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Payment
from app.schemas import PaymentCreate, PaymentResponse, PaymentStatus
from app.services.payments import UnknownPromoCodeError, create_payment

router = APIRouter(tags=["payments"])


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def post_payment(
    payload: PaymentCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> Payment:
    try:
        payment, replayed = await create_payment(session, payload, idempotency_key)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Tariff not found") from exc
    except UnknownPromoCodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if replayed:
        response.status_code = status.HTTP_200_OK
    return payment


@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(
    email: str | None = Query(default=None),
    payment_status: PaymentStatus | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[Payment]:
    query = select(Payment).order_by(Payment.id)
    if email:
        query = query.where(Payment.email == email)
    if payment_status:
        query = query.where(Payment.status == payment_status.value)
    return list((await session.scalars(query)).all())


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int, session: AsyncSession = Depends(get_session)) -> Payment:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
