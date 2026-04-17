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
    WorkspaceConfigRecord,
    async_session,
    normalize_db_datetime,
)
from app.models.schemas import AppConfig, HistoryRecord, MovementType, Opportunity, ScoreWeights

logger = logging.getLogger(__name__)


_DEDUP_WINDOW_MINUTES = 5  # só salva o mesmo par+exchange uma vez a cada N minutos
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
    exchange = opportunity.exchange.value if hasattr(opportunity.exchange, "value") else opportunity.exchange
    movement = (
        opportunity.movement_type.value
        if hasattr(opportunity.movement_type, "value")
        else opportunity.movement_type
    )
    enabled_exchanges = {item.value if hasattr(item, "value") else item for item in config.enabled_exchanges}

    return (
        exchange in enabled_exchanges
        and opportunity.pair in config.enabled_pairs
        and opportunity.volatility_pct >= config.thresholds.min_volatility_pct
        and opportunity.liquidity_units >= config.thresholds.min_liquidity_units
        and opportunity.spread_pct <= config.thresholds.max_spread_pct
        and (
            opportunity.quote_volume_24h >= config.thresholds.min_volume_brl
            or opportunity.quote_volume_24h >= config.thresholds.min_volume_brl_small
        )
        and movement in {item.value if hasattr(item, "value") else item for item in MovementType}
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

    return {
        "id": record.id,
        "exchange": record.exchange,
        "pair": record.pair,
        "score": workspace_score,
        "technical_score": getattr(record, "technical_score", None),
        "score_version": getattr(record, "score_version", "v1"),
        "volatility_pct": record.volatility_pct,
        "volume_24h": record.volume_24h,
        "quote_volume_24h": record.quote_volume_24h,
        "liquidity_units": record.liquidity_units,
        "spread_pct": record.spread_pct,
        "movement_type": record.movement_type,
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

    return AppConfig(
        thresholds={
            "min_volatility_pct": min(config.thresholds.min_volatility_pct for config in configs),
            "min_volume_brl": min(config.thresholds.min_volume_brl for config in configs),
            "min_volume_brl_small": min(config.thresholds.min_volume_brl_small for config in configs),
            "min_liquidity_units": min(config.thresholds.min_liquidity_units for config in configs),
            "max_spread_pct": max(config.thresholds.max_spread_pct for config in configs),
        },
        weights=configs[0].weights,
        enabled_exchanges=enabled_exchanges,
        enabled_pairs=enabled_pairs,
        scan_interval_seconds=scan_interval_seconds,
        telegram_enabled=any(config.telegram_enabled for config in configs),
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
        cutoff = utcnow() - timedelta(minutes=_DEDUP_WINDOW_MINUTES)

        # Load (exchange, pair) keys that were already saved within the window
        recent_q = select(
            OpportunityRecord.exchange,
            OpportunityRecord.pair,
        ).where(OpportunityRecord.detected_at >= cutoff)
        recent_result = await session.execute(recent_q)
        recent_keys: set[tuple[str, str]] = {(r[0], r[1]) for r in recent_result.all()}

        new_count = 0
        for opp in opportunities:
            key = (opp.exchange.value, opp.pair)
            if key in recent_keys:
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
                technical_signal_id=opp.technical_signal_id,
            )
            session.add(record)
            recent_keys.add(key)  # evita duplicata dentro do mesmo lote
            new_count += 1

        if new_count > 0:
            await session.commit()

        skipped = len(opportunities) - new_count
        logger.info(
            f"Saved {new_count} opportunities "
            f"({skipped} skipped — dedup window {_DEDUP_WINDOW_MINUTES}min)"
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
        if removable_count == 0:
            return 0

        await session.execute(delete(OpportunityRecord).where(OpportunityRecord.detected_at < cutoff))
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


async def get_filtered_analytics(
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    workspace_config: AppConfig | None = None,
) -> dict:
    """Get aggregated analytics from history with the same filters used by /history."""
    history_rows = await get_history(
        limit=1000,
        offset=0,
        exchange=exchange,
        pair=pair,
        min_score=min_score,
        hours=hours,
        workspace_config=workspace_config,
    )
    total_count = len(history_rows)

    pair_counts: dict[str, int] = {}
    exchange_totals: dict[str, list[float]] = {}
    scores = [row["score"] for row in history_rows]
    movement_distribution: dict[str, int] = {}
    hourly_distribution = {str(hour): 0 for hour in range(24)}
    arbitrage_count = 0
    gap_values: list[float] = []

    for row in history_rows:
        pair_counts[row["pair"]] = pair_counts.get(row["pair"], 0) + 1
        exchange_totals.setdefault(row["exchange"], []).append(row["score"])
        movement_distribution[row["movement_type"]] = movement_distribution.get(row["movement_type"], 0) + 1
        detected_at = ensure_utc_datetime(datetime.fromisoformat(row["detected_at"]))
        hourly_distribution[str(detected_at.hour)] += 1
        if row["arbitrage_available"]:
            arbitrage_count += 1
        if row["cross_exchange_gap_pct"] is not None:
            gap_values.append(row["cross_exchange_gap_pct"])

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
        "movement_distribution": movement_distribution,
        "hourly_distribution": hourly_distribution,
        "arbitrage_count": arbitrage_count,
        "avg_cross_exchange_gap_pct": avg_cross_exchange_gap,
    }


async def get_historical_pair_calibration(hours: int = 168) -> dict[str, dict[str, float]]:
    """Return recent pair-level calibration data to slightly adjust live scores."""
    async with async_session() as session:
        since = utcnow() - timedelta(hours=hours)
        query = (
            select(
                OpportunityRecord.pair,
                func.count(OpportunityRecord.id).label("cnt"),
                func.avg(OpportunityRecord.score).label("avg_score"),
                func.avg(OpportunityRecord.cross_exchange_gap_pct).label("avg_gap"),
            )
            .where(OpportunityRecord.detected_at >= since)
            .group_by(OpportunityRecord.pair)
        )
        result = await session.execute(query)
        calibration: dict[str, dict[str, float]] = {}
        for pair_name, count, avg_score, avg_gap in result.all():
            score_component = min(max(((avg_score or 50) - 50) / 100, -0.08), 0.08)
            count_component = min((count or 0) / 500, 0.05)
            gap_component = min((avg_gap or 0) / 10, 0.04)
            factor = round(1.0 + score_component + count_component + gap_component, 4)
            calibration[pair_name] = {
                "factor": min(max(factor, 0.9), 1.15),
                "count": float(count or 0),
                "avg_score": round(avg_score or 0, 2),
                "avg_gap": round(avg_gap or 0, 4),
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
