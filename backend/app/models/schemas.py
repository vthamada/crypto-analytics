from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
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


class MovementPhase(str, Enum):
    ACCUMULATION = "accumulation"
    EARLY_BREAKOUT = "early_breakout"
    CONTINUATION = "continuation"
    EXTENDED = "extended"
    DISTRIBUTION_OR_PROFIT_ZONE = "distribution_or_profit_zone"
    EXHAUSTION = "exhaustion"
    NEUTRAL = "neutral"


OpportunitySubtype = Literal[
    "directional_trade",
    "range_trade",
    "hold_continuation",
    "breakout_trade",
    "intra_exchange_spread",
    "book_scalping",
    "cross_exchange_arbitrage",
    "inventory_arbitrage",
    "transfer_arbitrage",
    "profit_zone",
    "observe_only",
    "avoid",
]


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


class OrderSizeSimulation(BaseModel):
    notional_brl: float
    buy_slippage_bps: float | None = None
    sell_slippage_bps: float | None = None
    buy_fillable_notional_brl: float = 0.0
    sell_fillable_notional_brl: float = 0.0
    executable: bool = False
    status: str = "not_operable"


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
    operational_score: float | None = None
    score_version: str = "v1"
    executability_version: str = "v1"
    movement_version: str = "v1"
    profile_version: str = "v1"
    reweighting_version: str = "v1"
    technical_signal_id: str | None = None
    semantic_signal_key: str | None = None
    pipeline_status: Literal[
        "observed_pair",
        "discarded_observation",
        "candidate",
        "evaluated_signal",
        "operational_opportunity",
        "published_opportunity",
        "alerted_opportunity",
        "blocked_signal",
        "technical_audit_event",
        "signal_outcome",
    ] = "evaluated_signal"
    visibility_reason: str | None = None
    operationally_visible: bool = False
    operation_status: str | None = None
    opportunity_family: str | None = None
    entry_zone: str | None = None
    exit_zone: str | None = None
    suggested_capital_range_brl: str | None = None
    liquidity_label: str | None = None
    risk_label: str | None = None
    main_reason: str | None = None
    actionability_label: str | None = None
    requires_limited_order: bool = False
    requires_transfer: bool = False
    executability_score: float | None = None
    executability_band: str | None = None
    interesting_signal: bool | None = None
    operable_signal: bool | None = None
    estimated_trade_margin_pct: float | None = None
    operational_friction_pct: float | None = None
    estimated_net_trade_edge_pct: float | None = None
    trade_margin_score: float | None = None
    opportunity_type: Literal["trade", "hold", "observe", "avoid"] | None = None
    opportunity_subtype: OpportunitySubtype | None = None
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
    order_size_simulations: list[OrderSizeSimulation] = Field(default_factory=list)
    max_operable_order_notional_brl: float | None = None
    operability_size_label: str | None = None
    movement_type: MovementType
    movement_regime: MovementRegime | None = None
    movement_phase: MovementPhase = MovementPhase.NEUTRAL
    phase_confidence_score: float | None = None
    phase_reason: str | None = None
    is_late_entry_risk: bool = False
    is_profit_zone_candidate: bool = False
    distance_from_accumulation_zone_pct: float | None = None
    distance_from_breakout_pct: float | None = None
    operational_buy_zone_low: float | None = None
    operational_buy_zone_high: float | None = None
    operational_sell_zone_low: float | None = None
    operational_sell_zone_high: float | None = None
    operational_range_margin_pct: float | None = None
    range_reuse_count: int = 0
    range_reliability_score: float | None = None
    zone_liquidity_score: float | None = None
    capital_capacity_estimate_brl: float | None = None
    operational_range_quality: str = "none"
    alert_moment_type: Literal["preparation", "early_breakout", "continuation", "extended", "profit_zone", "neutral"] = "neutral"
    alert_reason: str | None = None
    max_operable_order_notional_brl: float | None = None
    operability_size_label: str | None = None
    alert_worthiness_score: float | None = None
    alert_trigger_type: str | None = None
    has_actionable_trigger: bool = False
    alert_state_key: str | None = None
    alert_block_reason: str | None = None
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
    min_volatility_pct: float = 3.0
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
    pair_universe_mode: Literal["all_brl", "watchlist_only"] = "all_brl"
    enabled_exchanges: list[Exchange] = [
        Exchange.NOVADAX,
        Exchange.MERCADO_BITCOIN,
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
    telegram_daily_alert_limit: int | None = None
    telegram_alert_types: list[str] = Field(default_factory=lambda: ["operable", "high_score", "arbitrage"])
    telegram_operable_only: bool = True
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
    operable_opportunities: int = 0
    trade_opportunities: int = 0
    hold_opportunities: int = 0
    observe_opportunities: int = 0
    avoid_opportunities: int = 0
    last_scan: datetime | None = None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    opportunities: list[Opportunity]


class OpportunitySummary(BaseModel):
    id: str
    exchange: Exchange
    pair: str
    score: float
    technical_score: float | None = None
    operational_score: float | None = None
    reweighting_version: str = "v1"
    executability_score: float | None = None
    trade_margin_score: float | None = None
    estimated_net_trade_edge_pct: float | None = None
    executability_band: str | None = None
    pipeline_status: Literal[
        "observed_pair",
        "discarded_observation",
        "candidate",
        "evaluated_signal",
        "operational_opportunity",
        "published_opportunity",
        "alerted_opportunity",
        "blocked_signal",
        "technical_audit_event",
        "signal_outcome",
    ] = "evaluated_signal"
    visibility_reason: str | None = None
    operationally_visible: bool = False
    operation_status: str | None = None
    opportunity_family: str | None = None
    entry_zone: str | None = None
    exit_zone: str | None = None
    suggested_capital_range_brl: str | None = None
    liquidity_label: str | None = None
    risk_label: str | None = None
    main_reason: str | None = None
    actionability_label: str | None = None
    requires_limited_order: bool = False
    requires_transfer: bool = False
    opportunity_type: Literal["trade", "hold", "observe", "avoid"] | None = None
    opportunity_subtype: OpportunitySubtype | None = None
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
    order_size_simulations: list[OrderSizeSimulation] = Field(default_factory=list)
    max_operable_order_notional_brl: float | None = None
    operability_size_label: str | None = None
    last_price: float
    change_pct: float
    movement_type: MovementType
    movement_regime: MovementRegime | None = None
    movement_phase: MovementPhase = MovementPhase.NEUTRAL
    phase_confidence_score: float | None = None
    phase_reason: str | None = None
    is_late_entry_risk: bool = False
    is_profit_zone_candidate: bool = False
    distance_from_accumulation_zone_pct: float | None = None
    distance_from_breakout_pct: float | None = None
    operational_range_margin_pct: float | None = None
    capital_capacity_estimate_brl: float | None = None
    operational_range_quality: str = "none"
    alert_moment_type: Literal["preparation", "early_breakout", "continuation", "extended", "profit_zone", "neutral"] = "neutral"
    alert_reason: str | None = None
    alert_worthiness_score: float | None = None
    alert_trigger_type: str | None = None
    has_actionable_trigger: bool = False
    alert_state_key: str | None = None
    alert_block_reason: str | None = None
    outcome_label: str | None = None
    feedback_label: str | None = None
    detected_at: datetime
    cross_exchange_gap_pct: float = 0.0
    cross_exchange_reference_exchange: Exchange | None = None
    cross_exchange_reference_price: float | None = None
    arbitrage_available: bool = False
    historical_confidence: float = 1.0


class DashboardSummaryResponse(BaseModel):
    stats: DashboardStats
    shortlist: list[OpportunitySummary]


class HistoryRecord(BaseModel):
    id: str
    exchange: Exchange
    pair: str
    score: float
    technical_score: float | None = None
    operational_score: float | None = None
    score_version: str = "v1"
    executability_version: str = "v1"
    movement_version: str = "v1"
    profile_version: str = "v1"
    reweighting_version: str = "v1"
    technical_signal_id: str | None = None
    semantic_signal_key: str | None = None
    pipeline_status: Literal[
        "observed_pair",
        "discarded_observation",
        "candidate",
        "evaluated_signal",
        "operational_opportunity",
        "published_opportunity",
        "alerted_opportunity",
        "blocked_signal",
        "technical_audit_event",
        "signal_outcome",
    ] = "evaluated_signal"
    visibility_reason: str | None = None
    operationally_visible: bool = False
    operation_status: str | None = None
    opportunity_family: str | None = None
    entry_zone: str | None = None
    exit_zone: str | None = None
    suggested_capital_range_brl: str | None = None
    liquidity_label: str | None = None
    risk_label: str | None = None
    main_reason: str | None = None
    actionability_label: str | None = None
    requires_limited_order: bool = False
    requires_transfer: bool = False
    executability_score: float | None = None
    executability_band: str | None = None
    interesting_signal: bool | None = None
    operable_signal: bool | None = None
    estimated_trade_margin_pct: float | None = None
    operational_friction_pct: float | None = None
    estimated_net_trade_edge_pct: float | None = None
    trade_margin_score: float | None = None
    opportunity_type: Literal["trade", "hold", "observe", "avoid"] | None = None
    opportunity_subtype: OpportunitySubtype | None = None
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
    order_size_simulations: list[OrderSizeSimulation] = Field(default_factory=list)
    max_operable_order_notional_brl: float | None = None
    operability_size_label: str | None = None
    movement_type: MovementType
    movement_regime: MovementRegime | None = None
    movement_phase: MovementPhase = MovementPhase.NEUTRAL
    phase_confidence_score: float | None = None
    phase_reason: str | None = None
    is_late_entry_risk: bool = False
    is_profit_zone_candidate: bool = False
    distance_from_accumulation_zone_pct: float | None = None
    distance_from_breakout_pct: float | None = None
    operational_buy_zone_low: float | None = None
    operational_buy_zone_high: float | None = None
    operational_sell_zone_low: float | None = None
    operational_sell_zone_high: float | None = None
    operational_range_margin_pct: float | None = None
    range_reuse_count: int = 0
    range_reliability_score: float | None = None
    zone_liquidity_score: float | None = None
    capital_capacity_estimate_brl: float | None = None
    operational_range_quality: str = "none"
    alert_moment_type: Literal["preparation", "early_breakout", "continuation", "extended", "profit_zone", "neutral"] = "neutral"
    alert_reason: str | None = None
    alert_worthiness_score: float | None = None
    alert_trigger_type: str | None = None
    has_actionable_trigger: bool = False
    alert_state_key: str | None = None
    alert_block_reason: str | None = None
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


class HistorySummaryRecord(BaseModel):
    id: str
    exchange: Exchange
    pair: str
    score: float
    operational_score: float | None = None
    executability_score: float | None = None
    trade_margin_score: float | None = None
    estimated_net_trade_edge_pct: float | None = None
    pipeline_status: Literal[
        "observed_pair",
        "discarded_observation",
        "candidate",
        "evaluated_signal",
        "operational_opportunity",
        "published_opportunity",
        "alerted_opportunity",
        "blocked_signal",
        "technical_audit_event",
        "signal_outcome",
    ] = "evaluated_signal"
    visibility_reason: str | None = None
    operationally_visible: bool = False
    operation_status: str | None = None
    opportunity_family: str | None = None
    entry_zone: str | None = None
    exit_zone: str | None = None
    suggested_capital_range_brl: str | None = None
    liquidity_label: str | None = None
    risk_label: str | None = None
    main_reason: str | None = None
    actionability_label: str | None = None
    requires_limited_order: bool = False
    requires_transfer: bool = False
    opportunity_type: Literal["trade", "hold", "observe", "avoid"] | None = None
    opportunity_subtype: OpportunitySubtype | None = None
    spread_pct: float
    last_price: float
    change_pct: float
    movement_type: MovementType
    movement_phase: MovementPhase = MovementPhase.NEUTRAL
    is_late_entry_risk: bool = False
    operational_range_margin_pct: float | None = None
    operational_range_quality: str = "none"
    max_operable_order_notional_brl: float | None = None
    operability_size_label: str | None = None
    alert_moment_type: Literal["preparation", "early_breakout", "continuation", "extended", "profit_zone", "neutral"] = "neutral"
    alert_reason: str | None = None
    alert_worthiness_score: float | None = None
    alert_trigger_type: str | None = None
    has_actionable_trigger: bool = False
    alert_state_key: str | None = None
    alert_block_reason: str | None = None
    detected_at: datetime


class SignalFeedbackCreate(BaseModel):
    signal_id: str | None = None
    opportunity_id: str | None = None
    feedback_label: Literal[
        "useful",
        "weak",
        "late",
        "illiquid",
        "good_for_trade",
        "good_for_hold",
        "ignore",
        "false_positive",
        "good_margin",
        "insufficient_margin",
        "trapped_risk",
    ]
    feedback_note: str | None = None


class SignalFeedbackResponse(BaseModel):
    id: str
    signal_id: str | None = None
    opportunity_id: str | None = None
    user_id: str | None = None
    workspace_id: str | None = None
    feedback_label: str
    feedback_note: str | None = None
    created_at: datetime


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
    normalized_symbol: str | None = None
    base_asset: str | None = None
    quote_asset: str | None = None
    is_brl_pair: bool = False
    raw_symbols: dict[str, str | None] = Field(default_factory=dict)
    is_active: dict[str, bool] = Field(default_factory=dict)
    is_tradable: dict[str, bool] = Field(default_factory=dict)
    status: dict[str, str] = Field(default_factory=dict)
    error_message: dict[str, str | None] = Field(default_factory=dict)


class AvailablePairProviderStatus(BaseModel):
    exchange: Exchange
    returned_pairs: int
    brl_pairs: int
    status: Literal["ok", "empty", "error", "disabled", "stale"]
    checked_at: datetime
    error_message: str | None = None
    examples: list[str] = Field(default_factory=list)


class AvailablePairsResponse(BaseModel):
    generated_at: datetime
    expires_at: datetime
    pairs: list[AvailablePairRecord]
    provider_status: list[AvailablePairProviderStatus] = Field(default_factory=list)


class PairDiagnosticCheck(BaseModel):
    name: Literal["catalog", "ticker", "order_book", "klines"]
    status: Literal["ok", "error"]
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class PairExchangeDiagnosticResponse(BaseModel):
    exchange: Exchange
    pair: str
    display_name: str
    raw_symbol: str
    exists_in_catalog: bool
    overall_status: Literal["ok", "warning", "error"]
    checked_at: datetime
    checks: list[PairDiagnosticCheck]
    monitorable: bool = False
    monitorability_reason: str | None = None


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
    storage_mode: str = "postgres"
    durable_storage_enabled: bool = True
    degraded_features: list[str] = Field(default_factory=list)


class ExchangeCredentialValidationResult(BaseModel):
    exchange: Exchange
    state: Literal["missing", "valid", "invalid", "no_trading_permission", "error"]
    checked_at: datetime
    can_trade: bool | None = None
    message: str


class ExchangeCredentialValidationResponse(BaseModel):
    results: list[ExchangeCredentialValidationResult]
