from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routers.orders import router as orders_router
from app.api.routers.payments import router as payments_router
from app.core.config import settings
from app.database.base import Base
from app.database.models import *  # noqa: F401,F403 — register all models
from app.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE SEQUENCE IF NOT EXISTS order_number_seq"),
        )
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Order Pay API",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(orders_router)
app.include_router(payments_router)


@app.get("/ping")
async def ping():
    return {"status": "ok"}
