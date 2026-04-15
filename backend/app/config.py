from pathlib import Path

from pydantic_settings import BaseSettings

_BASE_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB = f"sqlite+aiosqlite:///{_BASE_DIR / 'crypto_analytics.db'}"


class Settings(BaseSettings):
    # Database
    database_url: str = _DEFAULT_DB

    # Admin
    admin_token: str = ""
    admin_username: str = ""
    admin_password: str = ""
    auth_secret_key: str = ""
    access_token_ttl_minutes: int = 480
    refresh_token_ttl_days: int = 30

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_alert_cooldown_seconds: int = 900

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
    history_retention_days: int = 90
    history_retention_check_minutes: int = 60

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

    # Observability
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    log_aggregation_url: str = ""
    log_aggregation_token: str = ""

    # CORS
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def effective_auth_secret(self) -> str:
        return self.auth_secret_key or self.admin_token


settings = Settings()
