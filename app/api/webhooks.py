import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import Payment
from app.schemas import BankWebhook
from app.services.payment_rules import is_valid_transition

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/bank")
async def bank_webhook(
    request: Request,
    payload: BankWebhook,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    body = await request.body()
    expected = hmac.new(get_settings().webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not x_signature or not hmac.compare_digest(expected, x_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
    payment = await session.get(Payment, payload.payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if not is_valid_transition(payment.status, payload.status.value):
        return JSONResponse(status_code=409, content={"error": "invalid_transition"})
    payment.status = payload.status.value
    await session.commit()
    return {"result": "ok"}
