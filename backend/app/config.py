import os
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field

_BASE_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB = f"sqlite+aiosqlite:///{_BASE_DIR / 'crypto_analytics.db'}"


class Settings(BaseSettings):
    # Database
    database_url: str = _DEFAULT_DB

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # NovaDAX
    novadax_api_key: str = ""
    novadax_api_secret: str = ""

    # Mercado Bitcoin
    mb_api_key: str = ""
    mb_api_secret: str = ""

    # Binance
    binance_api_key: str = ""
    binance_api_secret: str = ""

    # Scanning
    scan_interval_seconds: int = 30

    # Default filter thresholds
    min_volatility_pct: float = 2.0
    min_volume_brl: float = 10000.0
    min_volume_brl_small: float = 3000.0
    min_liquidity_units: float = 1000.0
    max_spread_pct: float = 1.0

    # Score weights (must sum to 1.0)
    weight_volatility: float = 0.30
    weight_volume: float = 0.25
    weight_liquidity: float = 0.20
    weight_spread: float = 0.15
    weight_repetition: float = 0.10

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
