"""Environment-based application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ChannelForge ERP"
    app_env: Literal["development", "staging", "production"] = "development"
    secret_key: str = "change-me-in-production-use-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    database_url: str = "sqlite+aiosqlite:///./channelforge.db"
    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    cors_origins: str = "http://localhost:3000"

    encryption_key: str = "channel-forge-demo-fernet-key-32b!!"

    user_llm_api_key: str = ""
    user_llm_base_url: str = "https://api.openai.com/v1"
    user_llm_model: str = "gpt-4o-mini"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    sync_poll_interval_seconds: int = 30
    inventory_conflict_policy: Literal["erp_wins", "marketplace_wins", "newest_wins"] = "erp_wins"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
