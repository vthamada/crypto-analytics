"""Shared state contract between scanner/worker and API.

Provides persisted scanner runtime state, opportunity snapshots,
technical signals, workspace projections, outcome tracking, and
persistent repetition counts.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    OpportunitySnapshotRecord,
    RepetitionCountRecord,
    ScannerRuntimeStateRecord,
    SignalOutcomeRecord,
    TechnicalSignalRecord,
    WorkspaceSignalProjectionRecord,
    async_session,
)
from app.models.schemas import AppConfig, Opportunity, ScoreWeights

logger = logging.getLogger(__name__)

SCORE_VERSION = "v1"
_DEDUP_SIGNAL_WINDOW_MINUTES = 5


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def calculate_technical_score(
    *,
    volatility_score: float,
    volume_score: float,
    liquidity_score: float,
    spread_score: float,
    repetition_score: float,
    movement_multiplier: float,
    historical_confidence: float,
) -> float:
    """Calculate a workspace-neutral technical score using fixed default weights."""
    weights = ScoreWeights()  # always default: vol=0.30, volume=0.25, liq=0.20, spread=0.15, rep=0.10
    raw = (
        volatility_score * weights.volatility
        + volume_score * weights.volume
        + liquidity_score * weights.liquidity
        + spread_score * weights.spread
        + repetition_score * weights.repetition
    )
    score = raw * 100 * movement_multiplier * historical_confidence
    return min(max(round(score, 1), 0), 100)


# ---------------------------------------------------------------------------
# Scanner runtime state
# ---------------------------------------------------------------------------

async def update_scanner_runtime_state(
    *,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
    success_at: datetime | None = None,
    opportunities_count: int | None = None,
) -> None:
    async with async_session() as session:
        record = await session.get(ScannerRuntimeStateRecord, "singleton")
        if record is None:
            record = ScannerRuntimeStateRecord(id="singleton")
            session.add(record)

        if started_at is not None:
            record.last_cycle_started_at = started_at
        if completed_at is not None:
            record.last_cycle_completed_at = completed_at
        if duration_ms is not None:
            record.last_cycle_duration_ms = duration_ms
        if error is not None:
            record.last_cycle_error = error
        elif completed_at is not None:
            record.last_cycle_error = None
        if success_at is not None:
            record.last_success_at = success_at
        if opportunities_count is not None:
            record.opportunities_count = opportunities_count
        record.score_version = SCORE_VERSION
        record.updated_at = utcnow()

        await session.commit()


async def get_scanner_runtime_state() -> dict | None:
    async with async_session() as session:
        record = await session.get(ScannerRuntimeStateRecord, "singleton")
        if record is None:
            return None
        return {
            "last_cycle_started_at": record.last_cycle_started_at.isoformat() if record.last_cycle_started_at else None,
            "last_cycle_completed_at": record.last_cycle_completed_at.isoformat() if record.last_cycle_completed_at else None,
            "last_cycle_duration_ms": record.last_cycle_duration_ms,
            "last_cycle_error": record.last_cycle_error,
            "last_success_at": record.last_success_at.isoformat() if record.last_success_at else None,
            "opportunities_count": record.opportunities_count,
            "score_version": record.score_version,
        }


# ---------------------------------------------------------------------------
# Opportunity snapshots (current cycle state, shared between worker and API)
# ---------------------------------------------------------------------------

async def write_opportunity_snapshots(
    opportunities: list[Opportunity],
    cycle_id: str,
) -> None:
    """Replace the current snapshot with the latest scan cycle results."""
    async with async_session() as session:
        # Clear previous snapshots
        await session.execute(delete(OpportunitySnapshotRecord))

        for opp in opportunities:
            technical_score = calculate_technical_score(
                volatility_score=opp.volatility_score,
                volume_score=opp.volume_score,
                liquidity_score=opp.liquidity_score,
                spread_score=opp.spread_score,
                repetition_score=opp.repetition_score,
                movement_multiplier=opp.movement_multiplier,
                historical_confidence=opp.historical_confidence,
            )
            record = OpportunitySnapshotRecord(
                id=opp.id,
                exchange=opp.exchange.value,
                pair=opp.pair,
                score=opp.score,
                technical_score=technical_score,
                score_version=SCORE_VERSION,
                volatility_pct=opp.volatility_pct,
                volume_24h=opp.volume_24h,
                quote_volume_24h=opp.quote_volume_24h,
                liquidity_units=opp.liquidity_units,
                spread_pct=opp.spread_pct,
                movement_type=opp.movement_type.value,
                last_price=opp.last_price,
                change_pct=opp.change_pct,
                detected_at=opp.detected_at,
                historical_confidence=opp.historical_confidence,
                volatility_score=opp.volatility_score,
                volume_score=opp.volume_score,
                liquidity_score=opp.liquidity_score,
                spread_score=opp.spread_score,
                repetition_score=opp.repetition_score,
                movement_multiplier=opp.movement_multiplier,
                cross_exchange_gap_pct=opp.cross_exchange_gap_pct,
                cross_exchange_reference_exchange=(
                    opp.cross_exchange_reference_exchange.value
                    if opp.cross_exchange_reference_exchange else None
                ),
                cross_exchange_reference_price=opp.cross_exchange_reference_price,
                arbitrage_available=opp.arbitrage_available,
                snapshot_cycle_id=cycle_id,
            )
            session.add(record)

        await session.commit()

    logger.info("snapshot_written cycle_id=%s count=%s", cycle_id, len(opportunities))


async def read_opportunity_snapshots() -> list[dict]:
    """Read the current opportunity snapshots from shared state."""
    async with async_session() as session:
        result = await session.execute(
            select(OpportunitySnapshotRecord).order_by(OpportunitySnapshotRecord.score.desc())
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "exchange": r.exchange,
                "pair": r.pair,
                "score": r.score,
                "technical_score": r.technical_score,
                "score_version": r.score_version,
                "volatility_pct": r.volatility_pct,
                "volume_24h": r.volume_24h,
                "quote_volume_24h": r.quote_volume_24h,
                "liquidity_units": r.liquidity_units,
                "spread_pct": r.spread_pct,
                "movement_type": r.movement_type,
                "last_price": r.last_price,
                "change_pct": r.change_pct,
                "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                "historical_confidence": r.historical_confidence,
                "volatility_score": r.volatility_score,
                "volume_score": r.volume_score,
                "liquidity_score": r.liquidity_score,
                "spread_score": r.spread_score,
                "repetition_score": r.repetition_score,
                "movement_multiplier": r.movement_multiplier,
                "cross_exchange_gap_pct": r.cross_exchange_gap_pct,
                "cross_exchange_reference_exchange": r.cross_exchange_reference_exchange,
                "cross_exchange_reference_price": r.cross_exchange_reference_price,
                "arbitrage_available": r.arbitrage_available,
            }
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Technical signals (dual-write with opportunities)
# ---------------------------------------------------------------------------

async def save_technical_signals(opportunities: list[Opportunity]) -> dict[str, str]:
    """Persist technical signals and return mapping of opp.id -> signal_id."""
    if not opportunities:
        return {}

    signal_map: dict[str, str] = {}

    async with async_session() as session:
        cutoff = utcnow() - timedelta(minutes=_DEDUP_SIGNAL_WINDOW_MINUTES)
        recent_q = select(
            TechnicalSignalRecord.exchange,
            TechnicalSignalRecord.pair,
        ).where(TechnicalSignalRecord.detected_at >= cutoff)
        recent_result = await session.execute(recent_q)
        recent_keys: set[tuple[str, str]] = {(r[0], r[1]) for r in recent_result.all()}

        for opp in opportunities:
            exchange_val = opp.exchange.value
            key = (exchange_val, opp.pair)
            if key in recent_keys:
                continue

            technical_score = calculate_technical_score(
                volatility_score=opp.volatility_score,
                volume_score=opp.volume_score,
                liquidity_score=opp.liquidity_score,
                spread_score=opp.spread_score,
                repetition_score=opp.repetition_score,
                movement_multiplier=opp.movement_multiplier,
                historical_confidence=opp.historical_confidence,
            )

            signal_id = str(uuid.uuid4())
            record = TechnicalSignalRecord(
                id=signal_id,
                exchange=exchange_val,
                pair=opp.pair,
                technical_score=technical_score,
                score_version=SCORE_VERSION,
                volatility_pct=opp.volatility_pct,
                volatility_score=opp.volatility_score,
                volume_24h=opp.volume_24h,
                quote_volume_24h=opp.quote_volume_24h,
                volume_score=opp.volume_score,
                liquidity_units=opp.liquidity_units,
                liquidity_score=opp.liquidity_score,
                spread_pct=opp.spread_pct,
                spread_score=opp.spread_score,
                repetition_score=opp.repetition_score,
                movement_type=opp.movement_type.value,
                movement_multiplier=opp.movement_multiplier,
                last_price=opp.last_price,
                change_pct=opp.change_pct,
                historical_confidence=opp.historical_confidence,
                cross_exchange_gap_pct=opp.cross_exchange_gap_pct,
                cross_exchange_reference_exchange=(
                    opp.cross_exchange_reference_exchange.value
                    if opp.cross_exchange_reference_exchange else None
                ),
                cross_exchange_reference_price=opp.cross_exchange_reference_price,
                arbitrage_available=opp.arbitrage_available,
                detected_at=opp.detected_at,
            )
            session.add(record)
            signal_map[opp.id] = signal_id
            recent_keys.add(key)

        if signal_map:
            await session.commit()

    logger.info("technical_signals_saved count=%s", len(signal_map))
    return signal_map


# ---------------------------------------------------------------------------
# Workspace signal projections
# ---------------------------------------------------------------------------

async def save_workspace_projections(
    workspace_id: str,
    technical_signal_id: str,
    workspace_score: float,
    *,
    visible: bool = True,
    alert_eligible: bool = False,
    projection_reason: str | None = None,
) -> None:
    async with async_session() as session:
        record = WorkspaceSignalProjectionRecord(
            workspace_id=workspace_id,
            technical_signal_id=technical_signal_id,
            workspace_score=workspace_score,
            visible=visible,
            alert_eligible=alert_eligible,
            projection_reason=projection_reason,
            created_at=utcnow(),
        )
        session.add(record)
        await session.commit()


async def save_workspace_projections_batch(
    projections: list[dict],
) -> int:
    """Save a batch of workspace signal projections.

    Each dict should have: workspace_id, technical_signal_id, workspace_score,
    visible, alert_eligible, projection_reason.
    """
    if not projections:
        return 0

    async with async_session() as session:
        for proj in projections:
            record = WorkspaceSignalProjectionRecord(
                workspace_id=proj["workspace_id"],
                technical_signal_id=proj["technical_signal_id"],
                workspace_score=proj["workspace_score"],
                visible=proj.get("visible", True),
                alert_eligible=proj.get("alert_eligible", False),
                projection_reason=proj.get("projection_reason"),
                created_at=utcnow(),
            )
            session.add(record)
        await session.commit()

    return len(projections)


# ---------------------------------------------------------------------------
# Signal outcomes
# ---------------------------------------------------------------------------

async def create_pending_outcomes(signals: list[dict]) -> int:
    """Create outcome records for signals that need future price evaluation.

    Each dict should have: technical_signal_id, exchange, pair, entry_price, signal_detected_at.
    """
    if not signals:
        return 0

    async with async_session() as session:
        for sig in signals:
            record = SignalOutcomeRecord(
                technical_signal_id=sig["technical_signal_id"],
                exchange=sig["exchange"],
                pair=sig["pair"],
                entry_price=sig["entry_price"],
                signal_detected_at=sig["signal_detected_at"],
                created_at=utcnow(),
            )
            session.add(record)
        await session.commit()

    return len(signals)


async def get_pending_outcomes(
    *,
    min_age_minutes: int = 5,
    max_age_hours: int = 5,
    limit: int = 100,
) -> list[dict]:
    """Get outcomes that haven't been fully evaluated yet."""
    now = utcnow()
    min_age_cutoff = now - timedelta(minutes=min_age_minutes)
    max_age_cutoff = now - timedelta(hours=max_age_hours)

    async with async_session() as session:
        query = (
            select(SignalOutcomeRecord)
            .where(
                SignalOutcomeRecord.evaluated_at.is_(None),
                SignalOutcomeRecord.signal_detected_at <= min_age_cutoff,
                SignalOutcomeRecord.signal_detected_at >= max_age_cutoff,
            )
            .order_by(SignalOutcomeRecord.signal_detected_at)
            .limit(limit)
        )
        result = await session.execute(query)
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "technical_signal_id": r.technical_signal_id,
                "exchange": r.exchange,
                "pair": r.pair,
                "entry_price": r.entry_price,
                "signal_detected_at": r.signal_detected_at,
            }
            for r in rows
        ]


async def update_outcome(
    outcome_id: str,
    *,
    price_after_5m: float | None = None,
    price_after_15m: float | None = None,
    price_after_1h: float | None = None,
    price_after_4h: float | None = None,
    max_price_1h: float | None = None,
    min_price_1h: float | None = None,
) -> None:
    """Update an outcome with price observations."""
    async with async_session() as session:
        record = await session.get(SignalOutcomeRecord, outcome_id)
        if record is None:
            return

        if price_after_5m is not None:
            record.price_after_5m = price_after_5m
            record.outcome_pct_5m = round((price_after_5m - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if price_after_15m is not None:
            record.price_after_15m = price_after_15m
            record.outcome_pct_15m = round((price_after_15m - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if price_after_1h is not None:
            record.price_after_1h = price_after_1h
            record.outcome_pct_1h = round((price_after_1h - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if price_after_4h is not None:
            record.price_after_4h = price_after_4h
            record.outcome_pct_4h = round((price_after_4h - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if max_price_1h is not None:
            record.max_price_1h = max_price_1h
        if min_price_1h is not None:
            record.min_price_1h = min_price_1h

        record.evaluated_at = utcnow()
        await session.commit()


# ---------------------------------------------------------------------------
# Persistent repetition counts
# ---------------------------------------------------------------------------

async def load_repetition_counts() -> dict[str, int]:
    """Load all repetition counts from database."""
    async with async_session() as session:
        result = await session.execute(select(RepetitionCountRecord))
        rows = result.scalars().all()
        return {r.id: r.count for r in rows}


async def save_repetition_counts(counts: dict[str, int]) -> None:
    """Persist repetition counts, upserting each key."""
    if not counts:
        return

    async with async_session() as session:
        for key, count in counts.items():
            record = await session.get(RepetitionCountRecord, key)
            if record is None:
                parts = key.split(":", 1)
                exchange = parts[0] if len(parts) > 1 else ""
                pair = parts[1] if len(parts) > 1 else key
                record = RepetitionCountRecord(
                    id=key,
                    exchange=exchange,
                    pair=pair,
                    count=count,
                    last_seen_at=utcnow(),
                    updated_at=utcnow(),
                )
                session.add(record)
            else:
                record.count = count
                record.last_seen_at = utcnow()
                record.updated_at = utcnow()

        await session.commit()


async def decay_stale_repetitions(*, max_age_minutes: int = 30) -> int:
    """Reduce counts for keys not seen recently. Returns number removed."""
    cutoff = utcnow() - timedelta(minutes=max_age_minutes)
    async with async_session() as session:
        result = await session.execute(
            delete(RepetitionCountRecord).where(RepetitionCountRecord.last_seen_at < cutoff)
        )
        await session.commit()
        return result.rowcount or 0
