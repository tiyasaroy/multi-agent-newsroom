from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    service_name: str = "newsroom-api"
    database_url: str = "postgresql+asyncpg://newsroom:newsroom@localhost:5432/newsroom"
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
