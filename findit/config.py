"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Anthropic
    anthropic_api_key: str = ""

    # Telegram
    telegram_bot_token: str = ""

    # Xiaohongshu
    xhs_cookie: str = ""

    # Database
    database_path: str = "data/findit.db"

    # Crawl settings
    crawl_city: str = "深圳"
    crawl_interval_hours: int = 24
    crawl_request_delay_min: float = 2.0
    crawl_request_delay_max: float = 5.0

    # Crawler service
    crawler_continuous: bool = True  # True = run_forever, False = run_once

    # Recommendation
    daily_match_count: int = 5
    high_match_count: int = 3
    push_hour: int = 20
    push_minute: int = 0

    @property
    def db_path(self) -> Path:
        p = Path(self.database_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
