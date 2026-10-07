from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import payments, tariffs, webhooks
from app.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="Kvitto Payments API", lifespan=lifespan)
    application.include_router(tariffs.router)
    application.include_router(payments.router)
    application.include_router(webhooks.router)
    return application


app = create_app()
