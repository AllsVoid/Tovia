from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://tovia:tovia_local_only@localhost:5432/tovia"
    auth_mode: Literal["disabled", "development", "oidc"] = "disabled"
    dev_user_id: UUID = UUID("00000000-0000-4000-8000-000000000001")
    oidc_issuer: AnyHttpUrl | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: AnyHttpUrl | None = None
    oidc_clock_skew_seconds: int = Field(default=30, ge=0, le=300)
    cors_origins: list[str] = ["http://localhost:3000"]

    @model_validator(mode="after")
    def validate_auth(self) -> "Settings":
        if self.app_env == "production" and self.auth_mode != "oidc":
            raise ValueError("Production requires OIDC authentication")
        if self.auth_mode == "oidc" and not all(
            (self.oidc_issuer, self.oidc_audience, self.oidc_jwks_url)
        ):
            raise ValueError("OIDC authentication requires issuer, audience, and JWKS URL")
        if self.app_env == "production" and self.oidc_issuer is not None:
            if self.oidc_issuer.scheme != "https":
                raise ValueError("Production OIDC issuer must use HTTPS")
            if not self.oidc_audience or not self.oidc_audience.strip():
                raise ValueError("Production OIDC audience must not be empty")
            if make_url(self.database_url).password == "tovia_local_only":
                raise ValueError("Production must replace the sample database password")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
