from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Tariff
from app.schemas import TariffResponse

router = APIRouter(tags=["tariffs"])


@router.get("/tariffs", response_model=list[TariffResponse])
async def list_tariffs(session: AsyncSession = Depends(get_session)) -> list[Tariff]:
    return list((await session.scalars(select(Tariff).order_by(Tariff.id))).all())
