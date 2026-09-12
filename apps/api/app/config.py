from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://tovia:tovia_local_only@localhost:5432/tovia"
    auth_mode: Literal["disabled", "development"] = "disabled"
    dev_user_id: UUID = UUID("00000000-0000-4000-8000-000000000001")
    cors_origins: list[str] = ["http://localhost:3000"]

    @model_validator(mode="after")
    def validate_auth(self) -> "Settings":
        if self.app_env == "production" and self.auth_mode == "development":
            raise ValueError("Development authentication is forbidden in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
