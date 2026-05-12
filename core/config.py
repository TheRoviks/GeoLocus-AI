from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: SecretStr = Field(..., alias="BOT_TOKEN")

    deepseek_api_key: SecretStr = Field(..., alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field("deepseek-chat", alias="DEEPSEEK_MODEL")
    deepseek_base_url: str = Field("https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")

    database_url: str = Field(..., alias="DATABASE_URL")

    debug: bool = Field(False, alias="DEBUG")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    default_timezone: str = Field("Europe/Moscow", alias="DEFAULT_TIMEZONE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
