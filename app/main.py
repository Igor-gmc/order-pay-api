from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from app.api.routers.bank_sync import router as bank_sync_router
from app.api.routers.logs import router as logs_router
from app.api.routers.orders import router as orders_router
from app.api.routers.payments import router as payments_router
from app.api.routers.refunds import router as refunds_router
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


_BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Order Pay API",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=_BASE_DIR / "static"), name="static")
_templates = Jinja2Templates(directory=_BASE_DIR / "templates")

app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(refunds_router)
app.include_router(bank_sync_router)
app.include_router(logs_router)


@app.get("/", include_in_schema=False)
async def index(request: Request):
    return _templates.TemplateResponse("index.html", {"request": request})


@app.get("/ping")
async def ping():
    return {"status": "ok"}
