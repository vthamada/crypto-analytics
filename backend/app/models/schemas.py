from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Exchange(str, Enum):
    NOVADAX = "novadax"
    MERCADO_BITCOIN = "mercado_bitcoin"
    BINANCE = "binance"


class MovementType(str, Enum):
    STRONG_RANGE = "strong_range"
    SPIKE = "spike"
    WEAK = "weak"
    TRAP = "trap"


class Ticker(BaseModel):
    exchange: Exchange
    pair: str
    last_price: float
    high_24h: float
    low_24h: float
    volume_24h: float
    quote_volume_24h: float
    change_pct_24h: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderBookEntry(BaseModel):
    price: float
    quantity: float


class OrderBook(BaseModel):
    exchange: Exchange
    pair: str
    bids: list[OrderBookEntry]
    asks: list[OrderBookEntry]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
    volatility_pct: float
    volume_24h: float
    quote_volume_24h: float
    liquidity_units: float
    spread_pct: float
    movement_type: MovementType
    last_price: float
    change_pct: float
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    duration_minutes: float = 0.0
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
    enabled_pairs: list[str] = [
        "BTC_BRL",
        "ETH_BRL",
        "SOL_BRL",
        "ADA_BRL",
        "XRP_BRL",
        "DOGE_BRL",
        "DOT_BRL",
        "AVAX_BRL",
        "MATIC_BRL",
        "LINK_BRL",
    ]
    scan_interval_seconds: int = 30
    telegram_enabled: bool = True
    # Credenciais (sobrepõem variáveis de ambiente quando preenchidas)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    novadax_api_key: str = ""
    novadax_api_secret: str = ""
    mb_api_key: str = ""
    mb_api_secret: str = ""
    binance_api_key: str = ""
    binance_api_secret: str = ""


class DashboardStats(BaseModel):
    total_opportunities: int
    active_opportunities: int
    monitored_pairs: int
    total_volume_24h: float
    best_score: float
    exchanges_online: int
    last_scan: datetime | None = None


class HistoryRecord(BaseModel):
    id: str
    exchange: Exchange
    pair: str
    score: float
    volatility_pct: float
    volume_24h: float
    liquidity_units: float
    spread_pct: float
    movement_type: MovementType
    last_price: float
    detected_at: datetime
    duration_minutes: float
