from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Exchange(str, Enum):
    NOVADAX = "novadax"
    MERCADO_BITCOIN = "mercado_bitcoin"
    BINANCE = "binance"


class MovementType(str, Enum):
    STRONG_RANGE = "strong_range"
    SPIKE = "spike"
    WEAK = "weak"
    TRAP = "trap"


class MovementRegime(str, Enum):
    TREND_CONTINUATION = "trend_continuation"
    BREAKOUT_CLEAN = "breakout_clean"
    BREAKOUT_EXHAUSTION = "breakout_exhaustion"
    MEAN_REVERSION_CANDIDATE = "mean_reversion_candidate"
    ILLIQUID_SPIKE = "illiquid_spike"


class Ticker(BaseModel):
    exchange: Exchange
    pair: str
    last_price: float
    high_24h: float
    low_24h: float
    volume_24h: float
    quote_volume_24h: float
    change_pct_24h: float
    timestamp: datetime = Field(default_factory=utcnow)


class OrderBookEntry(BaseModel):
    price: float
    quantity: float


class OrderBook(BaseModel):
    exchange: Exchange
    pair: str
    bids: list[OrderBookEntry]
    asks: list[OrderBookEntry]
    timestamp: datetime = Field(default_factory=utcnow)


class Trade(BaseModel):
    exchange: Exchange
    pair: str
    price: float
    quantity: float
    side: str  # "buy" or "sell"
    timestamp: datetime


class Kline(BaseModel):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: datetime | None = None


class Opportunity(BaseModel):
    id: str = ""
    exchange: Exchange
    pair: str
    score: float = Field(ge=0, le=100)
    technical_score: float | None = None
    score_version: str = "v1"
    executability_version: str = "v1"
    movement_version: str = "v1"
    profile_version: str = "v1"
    reweighting_version: str = "v1"
    technical_signal_id: str | None = None
    semantic_signal_key: str | None = None
    executability_score: float | None = None
    executability_band: str | None = None
    interesting_signal: bool | None = None
    operable_signal: bool | None = None
    volatility_pct: float
    volume_24h: float
    quote_volume_24h: float
    liquidity_units: float
    bid_notional_top_n: float | None = None
    ask_notional_top_n: float | None = None
    total_notional_top_n: float | None = None
    spread_pct: float
    estimated_buy_slippage_bps: float | None = None
    estimated_sell_slippage_bps: float | None = None
    fillable_notional_within_slippage_cap: float | None = None
    baseline_order_notional_brl: float | None = None
    movement_type: MovementType
    movement_regime: MovementRegime | None = None
    movement_persistence_score: float | None = None
    last_price: float
    change_pct: float
    detected_at: datetime = Field(default_factory=utcnow)
    duration_minutes: float = 0.0
    cross_exchange_gap_pct: float = 0.0
    cross_exchange_reference_exchange: Exchange | None = None
    cross_exchange_reference_price: float | None = None
    arbitrage_available: bool = False
    historical_confidence: float = 1.0
    volatility_score: float = 0.0
    volume_score: float = 0.0
    liquidity_score: float = 0.0
    spread_score: float = 0.0
    repetition_score: float = 0.0
    movement_multiplier: float = 1.0
    klines: list[Kline] = []


class FilterThresholds(BaseModel):
    min_volatility_pct: float = 2.0
    min_volume_brl: float = 10000.0
    min_volume_brl_small: float = 3000.0
    min_liquidity_units: float = 1000.0
    max_spread_pct: float = 1.0


class ScoreWeights(BaseModel):
    volatility: float = 0.30
    volume: float = 0.25
    liquidity: float = 0.20
    spread: float = 0.15
    repetition: float = 0.10


class AppConfig(BaseModel):
    thresholds: FilterThresholds = FilterThresholds()
    weights: ScoreWeights = ScoreWeights()
    enabled_exchanges: list[Exchange] = [
        Exchange.NOVADAX,
        Exchange.MERCADO_BITCOIN,
        Exchange.BINANCE,
    ]
    enabled_pairs: list[str] = Field(default_factory=list)
    scan_interval_seconds: int = 30
    trading_profile: Literal["conservador", "intraday_liquido", "agressivo", "scalp"] = "intraday_liquido"
    order_notional_brl: float | None = None
    max_entry_slippage_bps: float | None = None
    max_exit_slippage_bps: float | None = None
    min_quote_volume_brl: float | None = None
    telegram_enabled: bool = True
    telegram_alert_threshold: float = 60.0
    telegram_alert_cooldown_seconds: int = 900
    telegram_alert_types: list[str] = Field(default_factory=lambda: ["high_score", "arbitrage"])
    telegram_operable_only: bool = False
    telegram_min_executability_score: float | None = None
    telegram_alert_exchanges: list[Exchange] = Field(default_factory=list)
    telegram_alert_pairs: list[str] = Field(default_factory=list)
    # Credenciais (sobrepõem variáveis de ambiente quando preenchidas)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    novadax_api_key: str = ""
    novadax_api_secret: str = ""
    mb_api_key: str = ""
    mb_api_secret: str = ""
    binance_api_key: str = ""
    binance_api_secret: str = ""


class ConfigResponse(BaseModel):
    config: AppConfig
    configured_secrets: dict[str, bool]


class DashboardStats(BaseModel):
    total_opportunities: int
    active_opportunities: int
    monitored_pairs: int
    total_volume_24h: float
    best_score: float
    exchanges_online: int
    arbitrage_opportunities: int = 0
    last_scan: datetime | None = None


class HistoryRecord(BaseModel):
    id: str
    exchange: Exchange
    pair: str
    score: float
    technical_score: float | None = None
    score_version: str = "v1"
    executability_version: str = "v1"
    movement_version: str = "v1"
    profile_version: str = "v1"
    reweighting_version: str = "v1"
    technical_signal_id: str | None = None
    semantic_signal_key: str | None = None
    executability_score: float | None = None
    executability_band: str | None = None
    interesting_signal: bool | None = None
    operable_signal: bool | None = None
    volatility_pct: float
    volume_24h: float
    liquidity_units: float
    quote_volume_24h: float
    bid_notional_top_n: float | None = None
    ask_notional_top_n: float | None = None
    total_notional_top_n: float | None = None
    spread_pct: float
    estimated_buy_slippage_bps: float | None = None
    estimated_sell_slippage_bps: float | None = None
    fillable_notional_within_slippage_cap: float | None = None
    baseline_order_notional_brl: float | None = None
    movement_type: MovementType
    movement_regime: MovementRegime | None = None
    movement_persistence_score: float | None = None
    last_price: float
    change_pct: float
    detected_at: datetime
    duration_minutes: float
    cross_exchange_gap_pct: float = 0.0
    cross_exchange_reference_exchange: Exchange | None = None
    cross_exchange_reference_price: float | None = None
    arbitrage_available: bool = False
    historical_confidence: float = 1.0
    volatility_score: float = 0.0
    volume_score: float = 0.0
    liquidity_score: float = 0.0
    spread_score: float = 0.0
    repetition_score: float = 0.0
    movement_multiplier: float = 1.0


class WorkspaceSummary(BaseModel):
    id: str
    slug: str
    name: str
    role: str
    is_active: bool = True


class OrganizationSummary(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    stripe_customer_id: str | None = None
    subscription_status: str
    trial_ends_at: datetime | None = None


class UserSessionResponse(BaseModel):
    user_id: str
    username: str
    email: str | None = None
    role: str
    token_version: int
    auth_mode: str
    password_last_changed_at: datetime | None = None
    must_change_password: bool = False
    onboarding_completed_at: datetime | None = None
    organization: OrganizationSummary | None = None
    workspaces: list[WorkspaceSummary] = []


class UserRecordResponse(BaseModel):
    id: str
    username: str
    email: str | None = None
    role: str
    is_active: bool
    must_change_password: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    password_last_changed_at: datetime | None = None
    created_by_user_id: str | None = None
    token_version: int = 0


class UserCreateResponse(BaseModel):
    user: UserRecordResponse
    temporary_password: str


class AvailablePairRecord(BaseModel):
    pair: str
    display_name: str
    availability: dict[str, bool]


class AvailablePairsResponse(BaseModel):
    generated_at: datetime
    expires_at: datetime
    pairs: list[AvailablePairRecord]


class InviteRecordResponse(BaseModel):
    id: str
    code: str
    email: str
    workspace_id: str
    workspace_name: str
    organization_id: str
    organization_name: str
    role: str
    status: Literal["pending", "used", "expired"]
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime


class InvitePreviewResponse(BaseModel):
    code: str
    email: str
    workspace_name: str
    organization_name: str
    role: str
    status: Literal["pending", "used", "expired"]
    expires_at: datetime


class WorkspaceStatusResponse(BaseModel):
    workspace: WorkspaceSummary
    organization: OrganizationSummary | None = None
    configured_pairs_count: int
    enabled_exchange_count: int
    telegram_configured: bool
    exchange_credentials_configured: dict[str, bool]
    onboarding_completed_at: datetime | None = None


class ExchangeCredentialValidationResult(BaseModel):
    exchange: Exchange
    state: Literal["missing", "valid", "invalid", "no_trading_permission", "error"]
    checked_at: datetime
    can_trade: bool | None = None
    message: str


class ExchangeCredentialValidationResponse(BaseModel):
    results: list[ExchangeCredentialValidationResult]
