"""
Application settings organized by component/agent.
Uses Pydantic BaseSettings for modular, type-safe configuration.
"""

from pathlib import Path
from typing import List

from pydantic import Field, BaseModel, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseModel):
    """PostgreSQL connection settings."""
    host: str = "localhost"
    port: int = 5432
    db: str = "xalpha"
    user: str = "xalpha"
    password: str = ""
    pool_size: int = 5

    @computed_field
    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseModel):
    """Redis connection settings."""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0

    @computed_field
    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class GeminiSettings(BaseModel):
    """Google Gemini API settings."""
    api_key: str = ""
    model_pro: str = "gemini-2.5-pro"
    model_flash: str = "gemini-2.5-flash"
    model_lite: str = "gemini-2.5-flash-lite"


class TelegramSettings(BaseModel):
    """Telegram Bot settings."""
    token: str = ""
    chat_id: str = ""
    enabled: bool = True


class NewsSettings(BaseModel):
    """News Agent specific settings."""
    fetch_timeout: int = 30
    max_concurrent: int = 10
    default_limit: int = 50
    sources_path_raw: str = "config/sources.yaml"
    # Configurable schedule: list of hours (0-23)
    schedule_hours: List[int] = [7, 19]

    @computed_field
    @property
    def sources_path(self) -> Path:
        path = Path(self.sources_path_raw)
        if path.is_absolute():
            return path
        # Project root is 2 levels up from src/config/settings.py
        project_root = Path(__file__).resolve().parent.parent.parent
        return project_root / path


class VnstockSettings(BaseModel):
    """Vnstock library settings."""
    api_key: str = ""
    req_delay: float = 2.0  # Delay between requests to respect rate limits


class AppSettings(BaseSettings):
    """Main application settings aggregating components."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Allows nested settings like NEWS__SCHEDULE_HOURS
        extra="ignore",
    )

    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"

    # Component Settings
    postgres: PostgresSettings = PostgresSettings()
    redis: RedisSettings = RedisSettings()
    gemini: GeminiSettings = GeminiSettings()
    news: NewsSettings = NewsSettings()
    telegram: TelegramSettings = TelegramSettings()
    vnstock: VnstockSettings = VnstockSettings()

    # Auth
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440


# Singleton instance
settings = AppSettings()
