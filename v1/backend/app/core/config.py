from decimal import Decimal
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="postgresql+psycopg://maymay:maymay_dev@localhost:5544/maymayinvest_v1")
    database_url_async: str = Field(default="postgresql+asyncpg://maymay:maymay_dev@localhost:5544/maymayinvest_v1")

    alpaca_api_key: SecretStr = Field(default=SecretStr(""))
    alpaca_api_secret: SecretStr = Field(default=SecretStr(""))
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_data_feed: str = "iex"

    jwt_secret: SecretStr = Field(default=SecretStr("dev-only-change-me"))
    jwt_alg: str = "HS256"

    vault_master_key: SecretStr = Field(default=SecretStr("dev-only-32-byte-master-key-rotate"))

    log_level: str = "INFO"
    log_format: str = "json"

    global_max_orders_per_min: int = 20
    global_max_notional_per_day: Decimal = Decimal("50000")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
