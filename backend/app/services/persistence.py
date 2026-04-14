from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import OpportunityRecord, ConfigRecord, async_session
from app.models.schemas import Opportunity, AppConfig, FilterThresholds, ScoreWeights, Exchange

logger = logging.getLogger(__name__)


_DEDUP_WINDOW_MINUTES = 5  # só salva o mesmo par+exchange uma vez a cada N minutos


async def save_opportunities(opportunities: list[Opportunity]) -> None:
    """Persist detected opportunities, deduplicating within a time window.

    Same pair+exchange combination is recorded at most once every
    _DEDUP_WINDOW_MINUTES minutes, preventing the table from growing one row
    per scan cycle (every 30 s) for each persistent opportunity.
    """
    if not opportunities:
        return

    async with async_session() as session:
        cutoff = datetime.utcnow() - timedelta(minutes=_DEDUP_WINDOW_MINUTES)

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
                detected_at=opp.detected_at,
                duration_minutes=opp.duration_minutes,
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


async def get_history(
    limit: int = 100,
    offset: int = 0,
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
) -> list[dict]:
    """Retrieve opportunity history from the database."""
    async with async_session() as session:
        query = select(OpportunityRecord).order_by(desc(OpportunityRecord.detected_at))

        if exchange:
            query = query.where(OpportunityRecord.exchange == exchange)
        if pair:
            query = query.where(OpportunityRecord.pair == pair)
        if min_score is not None:
            query = query.where(OpportunityRecord.score >= min_score)
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.where(OpportunityRecord.detected_at >= since)

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        rows = result.scalars().all()

        return [
            {
                "id": r.id,
                "exchange": r.exchange,
                "pair": r.pair,
                "score": r.score,
                "volatility_pct": r.volatility_pct,
                "volume_24h": r.volume_24h,
                "quote_volume_24h": r.quote_volume_24h,
                "liquidity_units": r.liquidity_units,
                "spread_pct": r.spread_pct,
                "movement_type": r.movement_type,
                "last_price": r.last_price,
                "change_pct": r.change_pct,
                "detected_at": r.detected_at.isoformat(),
                "duration_minutes": r.duration_minutes,
            }
            for r in rows
        ]


async def get_analytics() -> dict:
    """Get aggregated analytics from history."""
    async with async_session() as session:
        # Total records
        total = await session.execute(select(func.count(OpportunityRecord.id)))
        total_count = total.scalar() or 0

        # Top pairs by count
        top_pairs_q = (
            select(OpportunityRecord.pair, func.count(OpportunityRecord.id).label("cnt"))
            .group_by(OpportunityRecord.pair)
            .order_by(desc("cnt"))
            .limit(10)
        )
        top_pairs_result = await session.execute(top_pairs_q)
        top_pairs = [{"pair": r[0], "count": r[1]} for r in top_pairs_result.all()]

        # Average score by exchange
        avg_score_q = (
            select(OpportunityRecord.exchange, func.avg(OpportunityRecord.score).label("avg"))
            .group_by(OpportunityRecord.exchange)
        )
        avg_score_result = await session.execute(avg_score_q)
        avg_by_exchange = [
            {"exchange": r[0], "avg_score": round(r[1], 1)} for r in avg_score_result.all()
        ]

        # Score distribution
        score_dist_q = select(OpportunityRecord.score).order_by(desc(OpportunityRecord.detected_at)).limit(500)
        score_dist_result = await session.execute(score_dist_q)
        scores = [r[0] for r in score_dist_result.all()]

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

        return {
            "total_records": total_count,
            "top_pairs": top_pairs,
            "avg_score_by_exchange": avg_by_exchange,
            "score_distribution": buckets,
        }


async def save_config(config: AppConfig) -> None:
    """Persist configuration to the database."""
    async with async_session() as session:
        record = await session.get(ConfigRecord, "app_config")
        value = config.model_dump_json()
        if record:
            record.value = value
            record.updated_at = datetime.utcnow()
        else:
            record = ConfigRecord(key="app_config", value=value)
            session.add(record)
        await session.commit()


async def load_config() -> AppConfig | None:
    """Load configuration from the database."""
    async with async_session() as session:
        record = await session.get(ConfigRecord, "app_config")
        if record:
            return AppConfig.model_validate_json(record.value)
        return None
