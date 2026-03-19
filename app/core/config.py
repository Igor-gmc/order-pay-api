from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/order_processing"
    bank_api_url: str = "http://localhost:8000/mock-bank"
    debug: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
