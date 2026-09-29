from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_COMPANY_IMPORT_SIGNING_KEY = "development-company-import-signing-key"


class Settings(BaseSettings):
    app_name: str = "SKMC ERP API"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str
    company_import_signing_key: SecretStr = SecretStr(
        DEFAULT_COMPANY_IMPORT_SIGNING_KEY
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # BaseSettings supplies required fields from environment sources at runtime.
    return Settings()  # pyright: ignore[reportCallIssue]
