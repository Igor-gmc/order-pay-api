from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title="Order Pay API",
    version="0.1.0",
    debug=settings.debug,
)


@app.get("/ping")
async def ping():
    return {"status": "ok"}
