from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = (
        "postgresql+psycopg://customerops:customerops_dev@localhost:5434/customerops"
    )
    migration_database_url: str = ""
    redis_url: str = "redis://localhost:6381/0"
    ai_mode: Literal["demo", "openai"] = "demo"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""
    embedding_model: str = "text-embedding-3-small"
    session_hours: int = Field(default=8, gt=0)
    cookie_secure: bool = False
    allowed_origin: str = "http://127.0.0.1:8000"
    demo_password: SecretStr = SecretStr("")
    otel_endpoint: str = ""
    input_usd_per_million: float = Field(default=0, ge=0, allow_inf_nan=False)
    output_usd_per_million: float = Field(default=0, ge=0, allow_inf_nan=False)
    frontend_dir: Path = ROOT / "frontend" / "dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()
