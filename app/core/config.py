from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "congress-trades-mvp"
    environment: str = "development"
    api_prefix: str = ""
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/congress"
    raw_storage_dir: Path = Path("./data/raw")
    user_agent: str = "congress-trades-mvp/0.1"
    default_page_size: int = Field(default=50, ge=1, le=500)
    max_page_size: int = Field(default=200, ge=1, le=1000)
    http_timeout_seconds: float = Field(default=30.0, gt=0)

    model_config = SettingsConfigDict(
        env_prefix="CONGRESS_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.raw_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings

