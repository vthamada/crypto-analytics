from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import (
    OpportunityRecord,
    ConfigRecord,
    RawMarketObservationRecord,
    SignalFeedbackRecord,
    SignalOutcomeRecord,
    TechnicalSignalRecord,
    WorkspaceSignalProjectionRecord,
    WorkspaceConfigRecord,
    async_session,
    normalize_db_datetime,
)
from app.models.schemas import AppConfig, HistoryRecord, MovementType, Opportunity, ScoreWeights
from app.filters.executability import calculate_executability_score, classify_executability_band, classify_opportunity_type, rescale_slippage_bps
from app.services.workspace_profiles import (
    explain_workspace_visibility,
    highest_order_notional,
    resolve_trading_profile,
    widest_slippage_cap,
)

logger = logging.getLogger(__name__)


_DEDUP_WINDOW_MINUTES = 5  # só salva o mesmo par+exchange uma vez a cada N minutos
_SEMANTIC_DEDUP_WINDOW_MINUTES = 30
_last_history_retention_run: datetime | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


DEFAULT_WORKSPACE_ID = "default"


MOVEMENT_MODIFIERS = {
    MovementType.STRONG_RANGE.value: 1.15,
    MovementType.SPIKE.value: 1.05,
    MovementType.WEAK.value: 0.7,
    MovementType.TRAP.value: 0.5,
}


def get_workspace_score(
    *,
    volatility_score: float,
    volume_score: float,
    liquidity_score: float,
    spread_score: float,
    repetition_score: float,
    movement_type: str,
    historical_confidence: float,
    weights: ScoreWeights,
) -> float:
    raw_score = (
        volatility_score * weights.volatility
        + volume_score * weights.volume
        + liquidity_score * weights.liquidity
        + spread_score * weights.spread
        + repetition_score * weights.repetition
    )
    movement_multiplier = MOVEMENT_MODIFIERS.get(movement_type, 1.0)
    score = raw_score * 100 * movement_multiplier * historical_confidence
    return min(max(round(score, 1), 0), 100)


def opportunity_matches_config(opportunity: Opportunity | HistoryRecord | OpportunityRecord, config: AppConfig) -> bool:
    if isinstance(opportunity, Opportunity):
        return explain_workspace_visibility(opportunity, config)[0]

    exchange = opportunity.exchange.value if hasattr(opportunity.exchange, "value") else opportunity.exchange
    movement = (
        opportunity.movement_type.value
        if hasattr(opportunity.movement_type, "value")
        else opportunity.movement_type
    )
    enabled_exchanges = {item.value if hasattr(item, "value") else item for item in config.enabled_exchanges}

    profile = resolve_trading_profile(config)
    return (
        exchange in enabled_exchanges
        and (config.pair_universe_mode != "watchlist_only" or opportunity.pair in config.enabled_pairs)
        and opportunity.volatility_pct >= config.thresholds.min_volatility_pct
        and opportunity.liquidity_units >= config.thresholds.min_liquidity_units
        and opportunity.spread_pct <= config.thresholds.max_spread_pct
        and opportunity.quote_volume_24h >= max(config.thresholds.min_volume_brl_small, profile.min_quote_volume_brl)
        and movement in {item.value if hasattr(item, "value") else item for item in MovementType}
    )


def get_workspace_operability_fields(
    *,
    bid_notional_top_n: float | None,
    ask_notional_top_n: float | None,
    spread_pct: float,
    quote_volume_24h: float,
    fillable_notional_within_slippage_cap: float | None,
    baseline_order_notional_brl: float | None,
    estimated_buy_slippage_bps: float | None,
    estimated_sell_slippage_bps: float | None,
    movement_persistence_score: float | None,
    config: AppConfig,
) -> dict[str, object]:
    if bid_notional_top_n is None and ask_notional_top_n is None:
        return {}

    profile = resolve_trading_profile(config)
    buy_slippage = rescale_slippage_bps(
        estimated_buy_slippage_bps,
        baseline_order_notional_brl=baseline_order_notional_brl,
        target_order_notional_brl=profile.order_notional_brl,
    )
    sell_slippage = rescale_slippage_bps(
        estimated_sell_slippage_bps,
        baseline_order_notional_brl=baseline_order_notional_brl,
        target_order_notional_brl=profile.order_notional_brl,
    )
    executability_score = calculate_executability_score(
        bid_notional_top_n=bid_notional_top_n or 0.0,
        ask_notional_top_n=ask_notional_top_n or 0.0,
        estimated_buy_slippage_bps=buy_slippage,
        estimated_sell_slippage_bps=sell_slippage,
        spread_pct=spread_pct,
        quote_volume_24h=quote_volume_24h,
        fillable_notional_within_slippage_cap=fillable_notional_within_slippage_cap,
        order_notional_brl=profile.order_notional_brl,
    )
    operable_signal = (
        executability_score >= 60.0
        and quote_volume_24h >= profile.min_quote_volume_brl
        and buy_slippage is not None
        and sell_slippage is not None
        and buy_slippage <= profile.max_entry_slippage_bps
        and sell_slippage <= profile.max_exit_slippage_bps
        and (movement_persistence_score or 0.0) >= 0.02
        and spread_pct <= min(config.thresholds.max_spread_pct, 0.6)
    )
    return {
        "executability_score": executability_score,
        "executability_band": classify_executability_band(executability_score),
        "operable_signal": operable_signal,
        "estimated_buy_slippage_bps": buy_slippage,
        "estimated_sell_slippage_bps": sell_slippage,
        "baseline_order_notional_brl": profile.order_notional_brl,
    }


def get_projected_opportunity_type(
    *,
    stored_type: str | None,
    operable_signal: bool | None,
    interesting_signal: bool | None,
    executability_score: float | None,
    trade_margin_score: float | None,
    estimated_net_trade_edge_pct: float | None,
    movement_regime: str | None,
) -> str | None:
    if trade_margin_score is None or estimated_net_trade_edge_pct is None:
        return stored_type
    return classify_opportunity_type(
        operable_signal=operable_signal,
        interesting_signal=interesting_signal,
        executability_score=executability_score,
        trade_margin_score=trade_margin_score,
        estimated_net_trade_edge_pct=estimated_net_trade_edge_pct,
        movement_regime=movement_regime,
    )


def serialize_history_record(record: OpportunityRecord, config: AppConfig | None = None) -> dict:
    detected_at = ensure_utc_datetime(record.detected_at)
    workspace_score = record.score
    if config is not None:
        workspace_score = get_workspace_score(
            volatility_score=record.volatility_score or 0,
            volume_score=record.volume_score or 0,
            liquidity_score=record.liquidity_score or 0,
            spread_score=record.spread_score or 0,
            repetition_score=record.repetition_score or 0,
            movement_type=record.movement_type,
            historical_confidence=record.historical_confidence or 1.0,
            weights=config.weights,
        )
        workspace_operability = get_workspace_operability_fields(
            bid_notional_top_n=getattr(record, "bid_notional_top_n", None),
            ask_notional_top_n=getattr(record, "ask_notional_top_n", None),
            spread_pct=record.spread_pct,
            quote_volume_24h=record.quote_volume_24h,
            fillable_notional_within_slippage_cap=getattr(record, "fillable_notional_within_slippage_cap", None),
            baseline_order_notional_brl=getattr(record, "baseline_order_notional_brl", None),
            estimated_buy_slippage_bps=getattr(record, "estimated_buy_slippage_bps", None),
            estimated_sell_slippage_bps=getattr(record, "estimated_sell_slippage_bps", None),
            movement_persistence_score=getattr(record, "movement_persistence_score", None),
            config=config,
        )
    else:
        workspace_operability = {}

    executability_score = workspace_operability.get("executability_score", getattr(record, "executability_score", None))
    operable_signal = workspace_operability.get("operable_signal", getattr(record, "operable_signal", None))
    movement_regime = getattr(record, "movement_regime", None)
    opportunity_type = get_projected_opportunity_type(
        stored_type=getattr(record, "opportunity_type", None),
        operable_signal=operable_signal,
        interesting_signal=getattr(record, "interesting_signal", None),
        executability_score=executability_score,
        trade_margin_score=getattr(record, "trade_margin_score", None),
        estimated_net_trade_edge_pct=getattr(record, "estimated_net_trade_edge_pct", None),
        movement_regime=movement_regime,
    )

    return {
        "id": record.id,
        "exchange": record.exchange,
        "pair": record.pair,
        "score": workspace_score,
        "technical_score": getattr(record, "technical_score", None),
        "score_version": getattr(record, "score_version", "v1"),
        "executability_version": getattr(record, "executability_version", "v1"),
        "movement_version": getattr(record, "movement_version", "v1"),
        "profile_version": getattr(record, "profile_version", "v1"),
        "reweighting_version": getattr(record, "reweighting_version", "v1"),
        "technical_signal_id": getattr(record, "technical_signal_id", None),
        "semantic_signal_key": getattr(record, "semantic_signal_key", None),
        "executability_score": executability_score,
        "executability_band": workspace_operability.get("executability_band", getattr(record, "executability_band", None)),
        "interesting_signal": getattr(record, "interesting_signal", None),
        "operable_signal": operable_signal,
        "estimated_trade_margin_pct": getattr(record, "estimated_trade_margin_pct", None),
        "operational_friction_pct": getattr(record, "operational_friction_pct", None),
        "estimated_net_trade_edge_pct": getattr(record, "estimated_net_trade_edge_pct", None),
        "trade_margin_score": getattr(record, "trade_margin_score", None),
        "opportunity_type": opportunity_type,
        "volatility_pct": record.volatility_pct,
        "volume_24h": record.volume_24h,
        "quote_volume_24h": record.quote_volume_24h,
        "liquidity_units": record.liquidity_units,
        "bid_notional_top_n": getattr(record, "bid_notional_top_n", None),
        "ask_notional_top_n": getattr(record, "ask_notional_top_n", None),
        "total_notional_top_n": getattr(record, "total_notional_top_n", None),
        "spread_pct": record.spread_pct,
        "estimated_buy_slippage_bps": workspace_operability.get("estimated_buy_slippage_bps", getattr(record, "estimated_buy_slippage_bps", None)),
        "estimated_sell_slippage_bps": workspace_operability.get("estimated_sell_slippage_bps", getattr(record, "estimated_sell_slippage_bps", None)),
        "fillable_notional_within_slippage_cap": getattr(record, "fillable_notional_within_slippage_cap", None),
        "baseline_order_notional_brl": workspace_operability.get("baseline_order_notional_brl", getattr(record, "baseline_order_notional_brl", None)),
        "movement_type": record.movement_type,
        "movement_regime": movement_regime,
        "movement_phase": getattr(record, "movement_phase", None) or "neutral",
        "phase_confidence_score": getattr(record, "phase_confidence_score", None),
        "phase_reason": getattr(record, "phase_reason", None),
        "is_late_entry_risk": getattr(record, "is_late_entry_risk", False),
        "is_profit_zone_candidate": getattr(record, "is_profit_zone_candidate", False),
        "distance_from_accumulation_zone_pct": getattr(record, "distance_from_accumulation_zone_pct", None),
        "distance_from_breakout_pct": getattr(record, "distance_from_breakout_pct", None),
        "operational_buy_zone_low": getattr(record, "operational_buy_zone_low", None),
        "operational_buy_zone_high": getattr(record, "operational_buy_zone_high", None),
        "operational_sell_zone_low": getattr(record, "operational_sell_zone_low", None),
        "operational_sell_zone_high": getattr(record, "operational_sell_zone_high", None),
        "operational_range_margin_pct": getattr(record, "operational_range_margin_pct", None),
        "range_reuse_count": getattr(record, "range_reuse_count", 0),
        "range_reliability_score": getattr(record, "range_reliability_score", None),
        "zone_liquidity_score": getattr(record, "zone_liquidity_score", None),
        "capital_capacity_estimate_brl": getattr(record, "capital_capacity_estimate_brl", None),
        "operational_range_quality": getattr(record, "operational_range_quality", None) or "none",
        "alert_moment_type": getattr(record, "alert_moment_type", None) or "neutral",
        "alert_reason": getattr(record, "alert_reason", None),
        "movement_persistence_score": getattr(record, "movement_persistence_score", None),
        "last_price": record.last_price,
        "change_pct": record.change_pct,
        "detected_at": detected_at.isoformat(),
        "duration_minutes": record.duration_minutes,
        "cross_exchange_gap_pct": record.cross_exchange_gap_pct,
        "cross_exchange_reference_exchange": record.cross_exchange_reference_exchange,
        "cross_exchange_reference_price": record.cross_exchange_reference_price,
        "arbitrage_available": record.arbitrage_available,
        "historical_confidence": record.historical_confidence,
        "volatility_score": record.volatility_score,
        "volume_score": record.volume_score,
        "liquidity_score": record.liquidity_score,
        "spread_score": record.spread_score,
        "repetition_score": record.repetition_score,
        "movement_multiplier": record.movement_multiplier,
    }


def build_merged_scan_config(configs: list[AppConfig]) -> AppConfig:
    if not configs:
        return AppConfig()

    enabled_exchanges = []
    enabled_pairs = []
    seen_exchanges: set[str] = set()
    seen_pairs: set[str] = set()
    for config in configs:
        for exchange in config.enabled_exchanges:
            exchange_value = exchange.value if hasattr(exchange, "value") else exchange
            if exchange_value not in seen_exchanges:
                seen_exchanges.add(exchange_value)
                enabled_exchanges.append(exchange)
        for pair in config.enabled_pairs:
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                enabled_pairs.append(pair)

    scan_interval_seconds = min(config.scan_interval_seconds for config in configs)
    order_notional_brl = highest_order_notional(configs)
    max_exit_slippage_bps = widest_slippage_cap(configs)
    max_entry_slippage_bps = max(resolve_trading_profile(config).max_entry_slippage_bps for config in configs)
    min_quote_volume_brl = min(resolve_trading_profile(config).min_quote_volume_brl for config in configs)
    min_exec_candidates = [
        config.telegram_min_executability_score
        for config in configs
        if config.telegram_min_executability_score is not None
    ]

    return AppConfig(
        thresholds={
            "min_volatility_pct": min(config.thresholds.min_volatility_pct for config in configs),
            "min_volume_brl": min(config.thresholds.min_volume_brl for config in configs),
            "min_volume_brl_small": min(config.thresholds.min_volume_brl_small for config in configs),
            "min_liquidity_units": min(config.thresholds.min_liquidity_units for config in configs),
            "max_spread_pct": max(config.thresholds.max_spread_pct for config in configs),
        },
        weights=configs[0].weights,
        pair_universe_mode=(
            "all_brl"
            if any(config.pair_universe_mode == "all_brl" for config in configs)
            else "watchlist_only"
        ),
        enabled_exchanges=enabled_exchanges,
        enabled_pairs=enabled_pairs,
        scan_interval_seconds=scan_interval_seconds,
        trading_profile="intraday_liquido",
        order_notional_brl=order_notional_brl,
        max_entry_slippage_bps=max_entry_slippage_bps,
        max_exit_slippage_bps=max_exit_slippage_bps,
        min_quote_volume_brl=min_quote_volume_brl,
        telegram_enabled=any(config.telegram_enabled for config in configs),
        telegram_alert_threshold=max(config.telegram_alert_threshold for config in configs),
        telegram_alert_cooldown_seconds=max(config.telegram_alert_cooldown_seconds for config in configs),
        telegram_daily_alert_limit=max(
            [config.telegram_daily_alert_limit for config in configs if config.telegram_daily_alert_limit is not None],
            default=None,
        ),
        telegram_alert_types=list({alert_type for config in configs for alert_type in config.telegram_alert_types}),
        telegram_operable_only=any(config.telegram_operable_only for config in configs),
        telegram_min_executability_score=max(min_exec_candidates) if min_exec_candidates else None,
        telegram_alert_exchanges=[
            exchange
            for exchange in enabled_exchanges
            if any(not config.telegram_alert_exchanges or exchange in config.telegram_alert_exchanges for config in configs)
        ],
        telegram_alert_pairs=list({pair for config in configs for pair in config.telegram_alert_pairs}),
        telegram_bot_token=next((config.telegram_bot_token for config in configs if config.telegram_bot_token), ""),
        telegram_chat_id=next((config.telegram_chat_id for config in configs if config.telegram_chat_id), ""),
        novadax_api_key=next((config.novadax_api_key for config in configs if config.novadax_api_key), ""),
        novadax_api_secret=next((config.novadax_api_secret for config in configs if config.novadax_api_secret), ""),
        mb_api_key=next((config.mb_api_key for config in configs if config.mb_api_key), ""),
        mb_api_secret=next((config.mb_api_secret for config in configs if config.mb_api_secret), ""),
        binance_api_key=next((config.binance_api_key for config in configs if config.binance_api_key), ""),
        binance_api_secret=next((config.binance_api_secret for config in configs if config.binance_api_secret), ""),
    )


async def save_opportunities(opportunities: list[Opportunity]) -> None:
    """Persist detected opportunities, deduplicating within a time window.

    Same pair+exchange combination is recorded at most once every
    _DEDUP_WINDOW_MINUTES minutes, preventing the table from growing one row
    per scan cycle (every 30 s) for each persistent opportunity.
    """
    if not opportunities:
        return

    async with async_session() as session:
        cutoff = utcnow() - timedelta(minutes=_SEMANTIC_DEDUP_WINDOW_MINUTES)

        # Load (exchange, pair) keys that were already saved within the window
        recent_q = select(
            OpportunityRecord.exchange,
            OpportunityRecord.pair,
            OpportunityRecord.semantic_signal_key,
        ).where(OpportunityRecord.detected_at >= cutoff)
        recent_result = await session.execute(recent_q)
        recent_rows = recent_result.all()
        recent_keys: set[tuple[str, str]] = {(r[0], r[1]) for r in recent_rows}
        recent_semantic_keys: set[str] = {r[2] for r in recent_rows if r[2]}

        new_count = 0
        for opp in opportunities:
            key = (opp.exchange.value, opp.pair)
            if opp.semantic_signal_key and opp.semantic_signal_key in recent_semantic_keys:
                continue
            if not opp.semantic_signal_key and key in recent_keys:
                continue  # already recorded recently — skip

            record = OpportunityRecord(
                id=opp.id,
                exchange=opp.exchange.value,
                pair=opp.pair,
                score=opp.score,
                volatility_pct=opp.volatility_pct,
                volume_24h=opp.volume_24h,
                quote_volume_24h=opp.quote_volume_24h,
                liquidity_units=opp.liquidity_units,
                spread_pct=opp.spread_pct,
                movement_type=opp.movement_type.value,
                last_price=opp.last_price,
                change_pct=opp.change_pct,
                detected_at=normalize_db_datetime(opp.detected_at),
                duration_minutes=opp.duration_minutes,
                cross_exchange_gap_pct=opp.cross_exchange_gap_pct,
                cross_exchange_reference_exchange=(
                    opp.cross_exchange_reference_exchange.value
                    if opp.cross_exchange_reference_exchange
                    else None
                ),
                cross_exchange_reference_price=opp.cross_exchange_reference_price,
                arbitrage_available=opp.arbitrage_available,
                historical_confidence=opp.historical_confidence,
                volatility_score=opp.volatility_score,
                volume_score=opp.volume_score,
                liquidity_score=opp.liquidity_score,
                spread_score=opp.spread_score,
                repetition_score=opp.repetition_score,
                movement_multiplier=opp.movement_multiplier,
                technical_score=opp.technical_score,
                score_version=opp.score_version,
                executability_version=opp.executability_version,
                movement_version=opp.movement_version,
                profile_version=opp.profile_version,
                reweighting_version=opp.reweighting_version,
                technical_signal_id=opp.technical_signal_id,
                semantic_signal_key=opp.semantic_signal_key,
                executability_score=opp.executability_score,
                executability_band=opp.executability_band,
                interesting_signal=opp.interesting_signal,
                operable_signal=opp.operable_signal,
                estimated_trade_margin_pct=opp.estimated_trade_margin_pct,
                operational_friction_pct=opp.operational_friction_pct,
                estimated_net_trade_edge_pct=opp.estimated_net_trade_edge_pct,
                trade_margin_score=opp.trade_margin_score,
                opportunity_type=opp.opportunity_type,
                bid_notional_top_n=opp.bid_notional_top_n,
                ask_notional_top_n=opp.ask_notional_top_n,
                total_notional_top_n=opp.total_notional_top_n,
                estimated_buy_slippage_bps=opp.estimated_buy_slippage_bps,
                estimated_sell_slippage_bps=opp.estimated_sell_slippage_bps,
                fillable_notional_within_slippage_cap=opp.fillable_notional_within_slippage_cap,
                baseline_order_notional_brl=opp.baseline_order_notional_brl,
                movement_regime=opp.movement_regime.value if opp.movement_regime else None,
                movement_phase=opp.movement_phase.value if hasattr(opp.movement_phase, "value") else opp.movement_phase,
                phase_confidence_score=opp.phase_confidence_score,
                phase_reason=opp.phase_reason,
                is_late_entry_risk=opp.is_late_entry_risk,
                is_profit_zone_candidate=opp.is_profit_zone_candidate,
                distance_from_accumulation_zone_pct=opp.distance_from_accumulation_zone_pct,
                distance_from_breakout_pct=opp.distance_from_breakout_pct,
                operational_buy_zone_low=opp.operational_buy_zone_low,
                operational_buy_zone_high=opp.operational_buy_zone_high,
                operational_sell_zone_low=opp.operational_sell_zone_low,
                operational_sell_zone_high=opp.operational_sell_zone_high,
                operational_range_margin_pct=opp.operational_range_margin_pct,
                range_reuse_count=opp.range_reuse_count,
                range_reliability_score=opp.range_reliability_score,
                zone_liquidity_score=opp.zone_liquidity_score,
                capital_capacity_estimate_brl=opp.capital_capacity_estimate_brl,
                operational_range_quality=opp.operational_range_quality,
                alert_moment_type=opp.alert_moment_type,
                alert_reason=opp.alert_reason,
                movement_persistence_score=opp.movement_persistence_score,
            )
            session.add(record)
            recent_keys.add(key)  # evita duplicata dentro do mesmo lote
            if opp.semantic_signal_key:
                recent_semantic_keys.add(opp.semantic_signal_key)
            new_count += 1

        if new_count > 0:
            await session.commit()

        skipped = len(opportunities) - new_count
        logger.info(
            f"Saved {new_count} opportunities "
            f"({skipped} skipped — semantic dedup {_SEMANTIC_DEDUP_WINDOW_MINUTES}min)"
        )


async def purge_history_older_than(*, retention_days: int, now: datetime | None = None) -> int:
    if retention_days <= 0:
        return 0

    reference_time = now or utcnow()
    cutoff = reference_time - timedelta(days=retention_days)

    async with async_session() as session:
        count_query = (
            select(func.count())
            .select_from(OpportunityRecord)
            .where(OpportunityRecord.detected_at < cutoff)
        )
        removable_count = int((await session.scalar(count_query)) or 0)
        await session.execute(delete(OpportunityRecord).where(OpportunityRecord.detected_at < cutoff))
        await session.execute(delete(RawMarketObservationRecord).where(RawMarketObservationRecord.detected_at < cutoff))
        await session.execute(delete(TechnicalSignalRecord).where(TechnicalSignalRecord.detected_at < cutoff))
        await session.execute(delete(WorkspaceSignalProjectionRecord).where(WorkspaceSignalProjectionRecord.created_at < cutoff))
        await session.execute(delete(SignalOutcomeRecord).where(SignalOutcomeRecord.signal_detected_at < cutoff))
        await session.commit()

    logger.info(
        "history_retention_pruned removed=%s retention_days=%s cutoff=%s",
        removable_count,
        retention_days,
        cutoff.isoformat(),
    )
    return removable_count


async def run_history_retention_if_due(*, now: datetime | None = None) -> int:
    global _last_history_retention_run

    if settings.history_retention_days <= 0:
        return 0

    reference_time = now or utcnow()
    check_interval = timedelta(minutes=max(settings.history_retention_check_minutes, 1))
    if _last_history_retention_run is not None and reference_time - _last_history_retention_run < check_interval:
        return 0

    removed = await purge_history_older_than(
        retention_days=settings.history_retention_days,
        now=reference_time,
    )
    _last_history_retention_run = reference_time
    return removed


async def get_history(
    limit: int = 100,
    offset: int = 0,
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    workspace_config: AppConfig | None = None,
) -> list[dict]:
    """Retrieve opportunity history from the database."""
    async with async_session() as session:
        query = select(OpportunityRecord).order_by(desc(OpportunityRecord.detected_at))

        if exchange:
            query = query.where(OpportunityRecord.exchange == exchange)
        if pair:
            query = query.where(OpportunityRecord.pair == pair)
        if min_score is not None and workspace_config is None:
            query = query.where(OpportunityRecord.score >= min_score)
        if hours:
            since = utcnow() - timedelta(hours=hours)
            query = query.where(OpportunityRecord.detected_at >= since)

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        rows = result.scalars().all()

        serialized_rows = [
            serialize_history_record(record, workspace_config)
            for record in rows
            if workspace_config is None or opportunity_matches_config(record, workspace_config)
        ]
        if workspace_config is not None and min_score is not None:
            serialized_rows = [record for record in serialized_rows if record["score"] >= min_score]
        return serialized_rows


async def get_analytics() -> dict:
    """Get aggregated analytics from history."""
    return await get_filtered_analytics()


def _apply_history_filters(
    query,
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
):
    if exchange:
        query = query.where(OpportunityRecord.exchange == exchange)
    if pair:
        query = query.where(OpportunityRecord.pair == pair)
    if min_score is not None:
        query = query.where(OpportunityRecord.score >= min_score)
    if hours:
        since = utcnow() - timedelta(hours=hours)
        query = query.where(OpportunityRecord.detected_at >= since)
    return query


def _apply_workspace_history_filters(query, workspace_config: AppConfig | None):
    if workspace_config is None:
        return query

    enabled_exchanges = [
        exchange.value if hasattr(exchange, "value") else exchange
        for exchange in workspace_config.enabled_exchanges
    ]
    profile = resolve_trading_profile(workspace_config)
    query = query.where(OpportunityRecord.exchange.in_(enabled_exchanges))
    if workspace_config.pair_universe_mode == "watchlist_only":
        query = query.where(OpportunityRecord.pair.in_(workspace_config.enabled_pairs))
    query = query.where(OpportunityRecord.volatility_pct >= workspace_config.thresholds.min_volatility_pct)
    query = query.where(OpportunityRecord.liquidity_units >= workspace_config.thresholds.min_liquidity_units)
    query = query.where(OpportunityRecord.spread_pct <= workspace_config.thresholds.max_spread_pct)
    query = query.where(
        OpportunityRecord.quote_volume_24h
        >= max(workspace_config.thresholds.min_volume_brl_small, profile.min_quote_volume_brl)
    )
    return query


def _workspace_adjusted_score(row: dict, workspace_config: AppConfig | None) -> float:
    if workspace_config is None:
        return row["score"]
    return get_workspace_score(
        volatility_score=row.get("volatility_score") or 0,
        volume_score=row.get("volume_score") or 0,
        liquidity_score=row.get("liquidity_score") or 0,
        spread_score=row.get("spread_score") or 0,
        repetition_score=row.get("repetition_score") or 0,
        movement_type=row.get("movement_type") or "",
        historical_confidence=row.get("historical_confidence") or 1.0,
        weights=workspace_config.weights,
    )


async def get_history_summary(
    limit: int = 100,
    offset: int = 0,
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    workspace_config: AppConfig | None = None,
) -> list[dict]:
    """Retrieve a reduced history payload for list views."""
    async with async_session() as session:
        query = select(
            OpportunityRecord.id,
            OpportunityRecord.exchange,
            OpportunityRecord.pair,
            OpportunityRecord.score,
            OpportunityRecord.executability_score,
            OpportunityRecord.trade_margin_score,
            OpportunityRecord.estimated_net_trade_edge_pct,
            OpportunityRecord.opportunity_type,
            OpportunityRecord.spread_pct,
            OpportunityRecord.last_price,
            OpportunityRecord.change_pct,
            OpportunityRecord.movement_type,
            OpportunityRecord.movement_phase,
            OpportunityRecord.is_late_entry_risk,
            OpportunityRecord.operational_range_margin_pct,
            OpportunityRecord.operational_range_quality,
            OpportunityRecord.alert_moment_type,
            OpportunityRecord.alert_reason,
            OpportunityRecord.detected_at,
            OpportunityRecord.volatility_score,
            OpportunityRecord.volume_score,
            OpportunityRecord.liquidity_score,
            OpportunityRecord.spread_score,
            OpportunityRecord.repetition_score,
            OpportunityRecord.historical_confidence,
        ).order_by(desc(OpportunityRecord.detected_at))

        query = _apply_history_filters(query, exchange=exchange, pair=pair, min_score=None if workspace_config else min_score, hours=hours)
        query = _apply_workspace_history_filters(query, workspace_config)
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        rows = [dict(row) for row in result.mappings().all()]

    summaries = []
    for row in rows:
        score = _workspace_adjusted_score(row, workspace_config)
        if min_score is not None and score < min_score:
            continue
        detected_at = ensure_utc_datetime(row["detected_at"])
        summaries.append(
            {
                "id": row["id"],
                "exchange": row["exchange"],
                "pair": row["pair"],
                "score": score,
                "executability_score": row["executability_score"],
                "trade_margin_score": row["trade_margin_score"],
                "estimated_net_trade_edge_pct": row["estimated_net_trade_edge_pct"],
                "opportunity_type": row["opportunity_type"],
                "spread_pct": row["spread_pct"],
                "last_price": row["last_price"],
                "change_pct": row["change_pct"],
                "movement_type": row["movement_type"],
                "movement_phase": row["movement_phase"] or "neutral",
                "is_late_entry_risk": row["is_late_entry_risk"] or False,
                "operational_range_margin_pct": row["operational_range_margin_pct"],
                "operational_range_quality": row["operational_range_quality"] or "none",
                "alert_moment_type": row["alert_moment_type"] or "neutral",
                "alert_reason": row["alert_reason"],
                "detected_at": detected_at.isoformat(),
            }
        )
    return summaries


async def get_filtered_analytics(
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    workspace_config: AppConfig | None = None,
) -> dict:
    """Get aggregated analytics from history with the same filters used by /history."""
    async with async_session() as session:
        query = select(
            OpportunityRecord.pair,
            OpportunityRecord.exchange,
            OpportunityRecord.score,
            OpportunityRecord.movement_type,
            OpportunityRecord.movement_regime,
            OpportunityRecord.movement_phase,
            OpportunityRecord.operational_range_quality,
            OpportunityRecord.alert_moment_type,
            OpportunityRecord.detected_at,
            OpportunityRecord.arbitrage_available,
            OpportunityRecord.cross_exchange_gap_pct,
            OpportunityRecord.executability_score,
            OpportunityRecord.profile_version,
            OpportunityRecord.opportunity_type,
            OpportunityRecord.estimated_net_trade_edge_pct,
            OpportunityRecord.volatility_score,
            OpportunityRecord.volume_score,
            OpportunityRecord.liquidity_score,
            OpportunityRecord.spread_score,
            OpportunityRecord.repetition_score,
            OpportunityRecord.historical_confidence,
        ).order_by(desc(OpportunityRecord.detected_at)).limit(5000)
        query = _apply_history_filters(query, exchange=exchange, pair=pair, min_score=None if workspace_config else min_score, hours=hours)
        query = _apply_workspace_history_filters(query, workspace_config)
        result = await session.execute(query)
        history_rows = [dict(row) for row in result.mappings().all()]

        feedback_query = select(SignalFeedbackRecord.feedback_label, func.count()).group_by(
            SignalFeedbackRecord.feedback_label
        )
        if hours:
            feedback_query = feedback_query.where(SignalFeedbackRecord.created_at >= utcnow() - timedelta(hours=hours))
        feedback_result = await session.execute(feedback_query)
        feedback_distribution = {
            label: int(count)
            for label, count in feedback_result.all()
        }

    if workspace_config is not None or min_score is not None:
        adjusted_rows = []
        for row in history_rows:
            row["score"] = _workspace_adjusted_score(row, workspace_config)
            if min_score is not None and row["score"] < min_score:
                continue
            adjusted_rows.append(row)
        history_rows = adjusted_rows

    total_count = len(history_rows)

    pair_counts: dict[str, int] = {}
    exchange_totals: dict[str, list[float]] = {}
    scores = [row["score"] for row in history_rows]
    movement_distribution: dict[str, int] = {}
    movement_regime_distribution: dict[str, int] = {}
    movement_phase_distribution: dict[str, int] = {}
    operational_range_distribution: dict[str, int] = {}
    alert_moment_distribution: dict[str, int] = {}
    hourly_distribution = {str(hour): 0 for hour in range(24)}
    arbitrage_count = 0
    gap_values: list[float] = []
    executability_buckets = {"0-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    opportunity_type_distribution = {"trade": 0, "hold": 0, "observe": 0, "avoid": 0}
    net_edge_by_type: dict[str, list[float]] = {}

    for row in history_rows:
        pair_counts[row["pair"]] = pair_counts.get(row["pair"], 0) + 1
        exchange_totals.setdefault(row["exchange"], []).append(row["score"])
        movement_distribution[row["movement_type"]] = movement_distribution.get(row["movement_type"], 0) + 1
        if row.get("movement_regime"):
            movement_regime_distribution[row["movement_regime"]] = movement_regime_distribution.get(row["movement_regime"], 0) + 1
        if row.get("movement_phase"):
            movement_phase_distribution[row["movement_phase"]] = movement_phase_distribution.get(row["movement_phase"], 0) + 1
        if row.get("operational_range_quality"):
            operational_range_distribution[row["operational_range_quality"]] = operational_range_distribution.get(row["operational_range_quality"], 0) + 1
        if row.get("alert_moment_type"):
            alert_moment_distribution[row["alert_moment_type"]] = alert_moment_distribution.get(row["alert_moment_type"], 0) + 1
        detected_at_value = row["detected_at"]
        detected_at = ensure_utc_datetime(
            datetime.fromisoformat(detected_at_value)
            if isinstance(detected_at_value, str)
            else detected_at_value
        )
        hourly_distribution[str(detected_at.hour)] += 1
        if row["arbitrage_available"]:
            arbitrage_count += 1
        if row["cross_exchange_gap_pct"] is not None:
            gap_values.append(row["cross_exchange_gap_pct"])
        if row.get("executability_score") is not None:
            exec_score = float(row["executability_score"])
            if exec_score < 40:
                executability_buckets["0-40"] += 1
            elif exec_score < 60:
                executability_buckets["40-60"] += 1
            elif exec_score < 80:
                executability_buckets["60-80"] += 1
            else:
                executability_buckets["80-100"] += 1
        opportunity_type = row.get("opportunity_type")
        if opportunity_type in opportunity_type_distribution:
            opportunity_type_distribution[opportunity_type] += 1
            if row.get("estimated_net_trade_edge_pct") is not None:
                net_edge_by_type.setdefault(opportunity_type, []).append(float(row["estimated_net_trade_edge_pct"]))

    top_pairs = [
        {"pair": pair_name, "count": count}
        for pair_name, count in sorted(pair_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    avg_by_exchange = [
        {"exchange": exchange_name, "avg_score": round(sum(values) / len(values), 1)}
        for exchange_name, values in exchange_totals.items()
    ]

    buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for s in scores:
        if s < 20:
            buckets["0-20"] += 1
        elif s < 40:
            buckets["20-40"] += 1
        elif s < 60:
            buckets["40-60"] += 1
        elif s < 80:
            buckets["60-80"] += 1
        else:
            buckets["80-100"] += 1

    avg_cross_exchange_gap = round(sum(gap_values) / len(gap_values), 4) if gap_values else 0

    return {
        "total_records": total_count,
        "top_pairs": top_pairs,
        "avg_score_by_exchange": avg_by_exchange,
        "score_distribution": buckets,
        "executability_distribution": executability_buckets,
        "movement_distribution": movement_distribution,
        "movement_regime_distribution": movement_regime_distribution,
        "movement_phase_distribution": movement_phase_distribution,
        "operational_range_distribution": operational_range_distribution,
        "alert_moment_distribution": alert_moment_distribution,
        "feedback_distribution": feedback_distribution,
        "opportunity_type_distribution": opportunity_type_distribution,
        "avg_net_trade_edge_by_type": {
            opportunity_type: round(sum(values) / len(values), 4)
            for opportunity_type, values in net_edge_by_type.items()
            if values
        },
        "hourly_distribution": hourly_distribution,
        "arbitrage_count": arbitrage_count,
        "avg_cross_exchange_gap_pct": avg_cross_exchange_gap,
        "profile_distribution": (
            {workspace_config.trading_profile: total_count}
            if workspace_config is not None
            else {}
        ),
    }


async def get_historical_pair_calibration(hours: int = 168) -> dict[str, dict[str, float]]:
    """Return recent pair-level calibration data using measured signal outcomes."""
    async with async_session() as session:
        since = utcnow() - timedelta(hours=hours)
        query = select(SignalOutcomeRecord).where(SignalOutcomeRecord.signal_detected_at >= since)
        result = await session.execute(query)
        calibration: dict[str, dict[str, float]] = {}
        grouped: dict[str, list[SignalOutcomeRecord]] = {}
        for row in result.scalars().all():
            grouped.setdefault(row.pair, []).append(row)

        for pair_name, rows in grouped.items():
            count = len(rows)
            if count == 0:
                continue
            usable_outcomes = [
                value
                for row in rows
                for value in (row.outcome_pct_15m, row.outcome_pct_1h, row.outcome_pct_4h, row.outcome_pct_24h)
                if value is not None
            ]
            avg_outcome = sum(usable_outcomes) / len(usable_outcomes) if usable_outcomes else 0.0
            success_count = sum(
                1
                for row in rows
                if any(
                    (value or 0) > 0
                    for value in (row.outcome_pct_15m, row.outcome_pct_1h, row.outcome_pct_4h, row.outcome_pct_24h)
                )
            )
            success_rate = success_count / count
            factor = 1.0 + min(max(avg_outcome / 10.0, -0.06), 0.06) + min(max((success_rate - 0.5) * 0.12, -0.06), 0.06)
            calibration[pair_name] = {
                "factor": round(min(max(factor, 0.9), 1.15), 4),
                "count": float(count),
                "avg_outcome": round(avg_outcome, 4),
                "success_rate": round(success_rate, 4),
            }
        return calibration


async def save_workspace_config(workspace_id: str, config: AppConfig) -> None:
    async with async_session() as session:
        record = await session.get(WorkspaceConfigRecord, workspace_id)
        value = config.model_dump_json()
        if record:
            record.value = value
            record.updated_at = utcnow()
        else:
            record = WorkspaceConfigRecord(workspace_id=workspace_id, value=value)
            session.add(record)
        await session.commit()


async def load_workspace_config(workspace_id: str) -> AppConfig | None:
    async with async_session() as session:
        record = await session.get(WorkspaceConfigRecord, workspace_id)
        if record:
            return AppConfig.model_validate_json(record.value)
        return None


async def load_all_workspace_configs() -> dict[str, AppConfig]:
    async with async_session() as session:
        result = await session.execute(select(WorkspaceConfigRecord))
        rows = result.scalars().all()
    return {row.workspace_id: AppConfig.model_validate_json(row.value) for row in rows}


async def save_config(config: AppConfig) -> None:
    """Backward-compatible default workspace config persistence."""
    async with async_session() as session:
        record = await session.get(ConfigRecord, "app_config")
        value = config.model_dump_json()
        if record:
            record.value = value
            record.updated_at = utcnow()
        else:
            record = ConfigRecord(key="app_config", value=value)
            session.add(record)
        await session.commit()
    await save_workspace_config(DEFAULT_WORKSPACE_ID, config)


async def load_config() -> AppConfig | None:
    """Backward-compatible default workspace config loading."""
    workspace_config = await load_workspace_config(DEFAULT_WORKSPACE_ID)
    if workspace_config is not None:
        return workspace_config

    async with async_session() as session:
        record = await session.get(ConfigRecord, "app_config")
        if record:
            return AppConfig.model_validate_json(record.value)
        return None
