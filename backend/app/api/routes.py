from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.models.schemas import (
    Opportunity, AppConfig, DashboardStats, FilterThresholds, ScoreWeights, Exchange,
)
from app.services.persistence import get_history, get_analytics, save_config, load_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# In-memory state (populated by the scanner background task)
_current_opportunities: list[Opportunity] = []
_last_scan: datetime | None = None
_config: AppConfig = AppConfig()


def update_state(opportunities: list[Opportunity], scan_time: datetime) -> None:
    global _current_opportunities, _last_scan
    _current_opportunities = opportunities
    _last_scan = scan_time


def get_config() -> AppConfig:
    return _config


def set_config(config: AppConfig) -> None:
    global _config
    _config = config


# --- Dashboard ---

@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats():
    opps = _current_opportunities
    exchanges_online = len(set(o.exchange for o in opps))
    return DashboardStats(
        total_opportunities=len(opps),
        active_opportunities=len([o for o in opps if o.score >= 40]),
        monitored_pairs=len(_config.enabled_pairs),
        total_volume_24h=sum(o.quote_volume_24h for o in opps),
        best_score=max((o.score for o in opps), default=0),
        exchanges_online=exchanges_online,
        last_scan=_last_scan,
    )


# --- Opportunities ---

@router.get("/opportunities", response_model=list[Opportunity])
async def list_opportunities(
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    movement_type: str | None = None,
    sort_by: str = "score",
    limit: int = Query(default=50, le=200),
):
    opps = _current_opportunities

    if exchange:
        opps = [o for o in opps if o.exchange.value == exchange]
    if pair:
        opps = [o for o in opps if o.pair == pair]
    if min_score is not None:
        opps = [o for o in opps if o.score >= min_score]
    if movement_type:
        opps = [o for o in opps if o.movement_type.value == movement_type]

    sort_keys = {
        "score": lambda o: o.score,
        "volatility": lambda o: o.volatility_pct,
        "volume": lambda o: o.quote_volume_24h,
        "spread": lambda o: o.spread_pct,
        "price": lambda o: o.last_price,
    }
    key_fn = sort_keys.get(sort_by, sort_keys["score"])
    opps.sort(key=key_fn, reverse=(sort_by != "spread"))

    return opps[:limit]


@router.get("/opportunities/{opp_id}", response_model=Opportunity | None)
async def get_opportunity(opp_id: str):
    for opp in _current_opportunities:
        if opp.id == opp_id:
            return opp
    return None


# --- History ---

@router.get("/history")
async def history(
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
):
    return await get_history(
        limit=limit, offset=offset, exchange=exchange,
        pair=pair, min_score=min_score, hours=hours,
    )


@router.get("/analytics")
async def analytics():
    return await get_analytics()


# --- Config ---

class ConfigUpdate(BaseModel):
    thresholds: FilterThresholds | None = None
    weights: ScoreWeights | None = None
    enabled_exchanges: list[Exchange] | None = None
    enabled_pairs: list[str] | None = None
    scan_interval_seconds: int | None = None
    telegram_enabled: bool | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    novadax_api_key: str | None = None
    novadax_api_secret: str | None = None
    mb_api_key: str | None = None
    mb_api_secret: str | None = None
    binance_api_key: str | None = None
    binance_api_secret: str | None = None


@router.get("/config", response_model=AppConfig)
async def get_config_endpoint():
    return _config


@router.put("/config", response_model=AppConfig)
async def update_config(update: ConfigUpdate):
    global _config
    data = _config.model_dump()
    update_data = update.model_dump(exclude_none=True)
    data.update(update_data)
    _config = AppConfig(**data)
    await save_config(_config)
    return _config


# --- Health ---

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "last_scan": _last_scan.isoformat() if _last_scan else None,
        "opportunities_count": len(_current_opportunities),
    }
