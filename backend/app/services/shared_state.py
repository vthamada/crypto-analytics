"""Shared state contract between scanner/worker and API.

Provides persisted scanner runtime state, opportunity snapshots,
technical signals, workspace projections, outcome tracking, and
persistent repetition counts.
"""

from __future__ import annotations

import logging
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    OpportunitySnapshotRecord,
    RawMarketObservationRecord,
    RepetitionCountRecord,
    ScannerCycleAuditRecord,
    ScannerRuntimeStateRecord,
    SignalPipelineEventRecord,
    SignalFeedbackRecord,
    SignalOutcomeRecord,
    TechnicalSignalRecord,
    WorkspaceSignalProjectionRecord,
    async_session,
    normalize_db_datetime,
)
from app.models.schemas import AppConfig, Opportunity, ScoreWeights
from app.services.telegram import telegram_destination_configured

logger = logging.getLogger(__name__)

SCORE_VERSION = "v1"
EXECUTABILITY_VERSION = "v1"
MOVEMENT_VERSION = "v1"
PROFILE_VERSION = "v1"
REWEIGHTING_VERSION = "v1"
_DEDUP_SIGNAL_WINDOW_MINUTES = 5
_PIPELINE_EVENT_RETENTION_DAYS = 14
_SCANNER_CYCLE_AUDIT_RETENTION_DAYS = 90


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    scan_diagnostics: dict | None = None,
) -> None:
    async with async_session() as session:
        record = await session.get(ScannerRuntimeStateRecord, "singleton")
        if record is None:
            record = ScannerRuntimeStateRecord(id="singleton")
            session.add(record)

        if started_at is not None:
            record.last_cycle_started_at = normalize_db_datetime(started_at)
        if completed_at is not None:
            record.last_cycle_completed_at = normalize_db_datetime(completed_at)
        if duration_ms is not None:
            record.last_cycle_duration_ms = duration_ms
        if error is not None:
            record.last_cycle_error = error
        elif completed_at is not None:
            record.last_cycle_error = None
        if success_at is not None:
            record.last_success_at = normalize_db_datetime(success_at)
        if opportunities_count is not None:
            record.opportunities_count = opportunities_count
        if scan_diagnostics is not None:
            record.last_scan_diagnostics = json.dumps(scan_diagnostics)
        record.score_version = SCORE_VERSION
        record.executability_version = EXECUTABILITY_VERSION
        record.movement_version = MOVEMENT_VERSION
        record.profile_version = PROFILE_VERSION
        record.updated_at = utcnow()

        await session.commit()


async def get_scanner_runtime_state() -> dict | None:
    async with async_session() as session:
        record = await session.get(ScannerRuntimeStateRecord, "singleton")
        if record is None:
            return None
        diagnostics = {}
        if getattr(record, "last_scan_diagnostics", None):
            try:
                diagnostics = json.loads(record.last_scan_diagnostics or "{}")
            except json.JSONDecodeError:
                diagnostics = {}
        return {
            "last_cycle_started_at": record.last_cycle_started_at.isoformat() if record.last_cycle_started_at else None,
            "last_cycle_completed_at": record.last_cycle_completed_at.isoformat() if record.last_cycle_completed_at else None,
            "last_cycle_duration_ms": record.last_cycle_duration_ms,
            "last_cycle_error": record.last_cycle_error,
            "last_success_at": record.last_success_at.isoformat() if record.last_success_at else None,
            "opportunities_count": record.opportunities_count,
            "last_scan_diagnostics": diagnostics,
            "score_version": record.score_version,
            "executability_version": getattr(record, "executability_version", EXECUTABILITY_VERSION),
            "movement_version": getattr(record, "movement_version", MOVEMENT_VERSION),
            "profile_version": getattr(record, "profile_version", PROFILE_VERSION),
        }


# ---------------------------------------------------------------------------
# Scanner cycle and signal pipeline audit
# ---------------------------------------------------------------------------

def _safe_json_dumps(payload: object) -> str:
    return json.dumps(payload, default=str, ensure_ascii=False)


def _safe_json_loads(payload: str | None, fallback):
    if not payload:
        return fallback
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return fallback


def _count_provider_errors(diagnostics: dict) -> int:
    light_errors = sum(
        count
        for reason, count in diagnostics.get("light_discard_reasons", {}).items()
        if "provider" in reason or "timeout" in reason or "ticker" in reason or "missing" in reason
    )
    deep_errors = sum(
        count
        for reason, count in diagnostics.get("deep_discard_reasons", {}).items()
        if "provider" in reason or "timeout" in reason or "failed" in reason or "missing" in reason
    )
    return int(light_errors + deep_errors)


async def save_signal_pipeline_events(cycle_id: str, events: list[dict]) -> int:
    """Persist compact per-pair/per-workspace audit events for missed-signal diagnosis."""
    if not events:
        return 0

    async with async_session() as session:
        for event in events:
            exchange = event.get("exchange")
            if hasattr(exchange, "value"):
                exchange = exchange.value
            created_at = event.get("created_at") or utcnow()
            session.add(
                SignalPipelineEventRecord(
                    cycle_id=event.get("cycle_id") or cycle_id,
                    exchange=exchange,
                    pair=event.get("pair"),
                    stage=event["stage"],
                    status=event["status"],
                    reason=event.get("reason"),
                    event_type=event.get("event_type", "scanner"),
                    workspace_id=event.get("workspace_id"),
                    technical_signal_id=event.get("technical_signal_id"),
                    opportunity_id=event.get("opportunity_id"),
                    details=_safe_json_dumps(event.get("details", {})),
                    created_at=normalize_db_datetime(created_at),
                )
            )
        await session.commit()
    return len(events)


async def save_scanner_cycle_audit(
    *,
    cycle_id: str,
    started_at: datetime,
    completed_at: datetime | None = None,
    duration_ms: float | None = None,
    status: str = "completed",
    diagnostics: dict | None = None,
    signals_created: int = 0,
    shortlist_count: int = 0,
    alerts_created: int = 0,
    alerts_sent: int = 0,
    block_reasons: dict | None = None,
    error: str | None = None,
) -> None:
    diagnostics = diagnostics or {}
    discard_reasons = {
        **diagnostics.get("light_discard_reasons", {}),
        **diagnostics.get("deep_discard_reasons", {}),
        **diagnostics.get("skip_reasons", {}),
    }

    async with async_session() as session:
        result = await session.execute(
            select(ScannerCycleAuditRecord).where(ScannerCycleAuditRecord.cycle_id == cycle_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = ScannerCycleAuditRecord(cycle_id=cycle_id, started_at=normalize_db_datetime(started_at))
            session.add(record)

        record.status = status
        record.started_at = normalize_db_datetime(started_at) or utcnow()
        record.completed_at = normalize_db_datetime(completed_at)
        record.duration_ms = duration_ms
        record.total_pairs = int(diagnostics.get("total_pairs", 0) or 0)
        record.brl_pairs = int(diagnostics.get("brl_pairs", diagnostics.get("total_pairs", 0)) or 0)
        record.light_candidates = int(diagnostics.get("light_candidates", 0) or 0)
        record.deep_candidates = int(diagnostics.get("deep_candidates", 0) or 0)
        record.deep_completed = int(diagnostics.get("deep_completed", 0) or 0)
        record.signals_created = signals_created
        record.shortlist_count = shortlist_count
        record.alerts_created = alerts_created
        record.alerts_sent = alerts_sent
        record.provider_errors = _count_provider_errors(diagnostics)
        record.discard_reasons = _safe_json_dumps(discard_reasons)
        record.block_reasons = _safe_json_dumps(block_reasons or {})
        record.diagnostics = _safe_json_dumps(diagnostics)
        record.error = error
        record.created_at = record.created_at or utcnow()
        await session.commit()


async def get_missed_signal_diagnostic(
    *,
    exchange: str,
    pair: str,
    from_time: datetime,
    to_time: datetime,
    workspace_id: str | None = None,
    workspace_config: AppConfig | None = None,
    catalog_status: dict | None = None,
) -> dict:
    normalized_exchange = exchange.value if hasattr(exchange, "value") else str(exchange)
    normalized_pair = pair.upper().replace("/", "_")

    async with async_session() as session:
        events_result = await session.execute(
            select(SignalPipelineEventRecord)
            .where(
                SignalPipelineEventRecord.exchange == normalized_exchange,
                SignalPipelineEventRecord.pair == normalized_pair,
                SignalPipelineEventRecord.created_at >= normalize_db_datetime(from_time),
                SignalPipelineEventRecord.created_at <= normalize_db_datetime(to_time),
            )
            .order_by(SignalPipelineEventRecord.created_at.asc())
            .limit(500)
        )
        events = events_result.scalars().all()

        cycles = []
        if events:
            cycle_ids = sorted({event.cycle_id for event in events})
            cycles_result = await session.execute(
                select(ScannerCycleAuditRecord)
                .where(ScannerCycleAuditRecord.cycle_id.in_(cycle_ids))
                .order_by(ScannerCycleAuditRecord.started_at.asc())
            )
            cycles = cycles_result.scalars().all()

    timeline = [
        {
            "cycle_id": event.cycle_id,
            "exchange": event.exchange,
            "pair": event.pair,
            "stage": event.stage,
            "status": event.status,
            "reason": event.reason,
            "event_type": event.event_type,
            "workspace_id": event.workspace_id,
            "technical_signal_id": event.technical_signal_id,
            "opportunity_id": event.opportunity_id,
            "details": _safe_json_loads(event.details, {}),
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in events
    ]
    cycle_summaries = [
        {
            "cycle_id": cycle.cycle_id,
            "status": cycle.status,
            "started_at": cycle.started_at.isoformat() if cycle.started_at else None,
            "completed_at": cycle.completed_at.isoformat() if cycle.completed_at else None,
            "duration_ms": cycle.duration_ms,
            "total_pairs": cycle.total_pairs,
            "brl_pairs": cycle.brl_pairs,
            "light_candidates": cycle.light_candidates,
            "deep_candidates": cycle.deep_candidates,
            "deep_completed": cycle.deep_completed,
            "signals_created": cycle.signals_created,
            "shortlist_count": cycle.shortlist_count,
            "alerts_created": cycle.alerts_created,
            "alerts_sent": cycle.alerts_sent,
            "provider_errors": cycle.provider_errors,
            "discard_reasons": _safe_json_loads(cycle.discard_reasons, {}),
            "block_reasons": _safe_json_loads(cycle.block_reasons, {}),
            "error": cycle.error,
        }
        for cycle in cycles
    ]

    if timeline:
        status = "events_found"
    else:
        status = "insufficient_audit_data"
    final_state, root_cause_event = _summarize_signal_final_state(timeline, workspace_id=workspace_id)

    return {
        "exchange": normalized_exchange,
        "pair": normalized_pair,
        "from": normalize_db_datetime(from_time).isoformat(),
        "to": normalize_db_datetime(to_time).isoformat(),
        "status": status,
        "final_state": final_state,
        "root_cause_stage": root_cause_event.get("stage") if root_cause_event else None,
        "root_cause_reason": root_cause_event.get("reason") if root_cause_event else None,
        "workspace_status": _build_workspace_signal_status(
            exchange=normalized_exchange,
            pair=normalized_pair,
            workspace_id=workspace_id,
            config=workspace_config,
            timeline=timeline,
        ),
        "catalog_status": catalog_status,
        "message": (
            "Linha do tempo encontrada para o par no intervalo."
            if timeline
            else "Nenhum evento auditável encontrado; o intervalo pode ser anterior à auditoria ou o par não foi relevante no ciclo."
        ),
        "timeline": timeline,
        "cycle_summaries": cycle_summaries,
    }


def _summarize_signal_final_state(
    timeline: list[dict],
    *,
    workspace_id: str | None,
) -> tuple[str, dict | None]:
    if not timeline:
        return "insufficient_audit_data", None

    scoped_events = [
        event
        for event in timeline
        if workspace_id is None or event.get("workspace_id") in (None, workspace_id)
    ]
    workspace_events = [
        event for event in timeline if workspace_id is not None and event.get("workspace_id") == workspace_id
    ]
    events = scoped_events or timeline

    for event in reversed(events):
        if event.get("stage") == "alert" and event.get("status") == "sent":
            return "alerted", event
    for event in reversed(workspace_events):
        if event.get("stage") == "alert" and event.get("status") == "blocked":
            return "alert_blocked", event
    for event in reversed(workspace_events):
        if event.get("stage") == "workspace_projection" and event.get("status") == "blocked":
            return "not_visible_for_workspace", event
    for event in reversed(workspace_events):
        if event.get("stage") == "workspace_projection" and event.get("status") == "visible":
            return "visible_not_alerted", event
    for event in reversed(events):
        if event.get("status") == "error":
            return "provider_error", event
    for event in reversed(events):
        if event.get("status") in {"blocked", "discarded"}:
            return "discarded_before_alert", event
    for event in reversed(events):
        if event.get("stage") == "ranking" and event.get("status") in {"ranked", "opportunity"}:
            return "technical_signal_created", event
    return "audited_without_terminal_decision", events[-1] if events else None


def _build_workspace_signal_status(
    *,
    exchange: str,
    pair: str,
    workspace_id: str | None,
    config: AppConfig | None,
    timeline: list[dict],
) -> dict | None:
    if config is None:
        return None

    enabled_exchanges = {
        item.value if hasattr(item, "value") else str(item)
        for item in config.enabled_exchanges
    }
    workspace_events = [
        event for event in timeline if workspace_id is None or event.get("workspace_id") == workspace_id
    ]
    latest_projection = next(
        (event for event in reversed(workspace_events) if event.get("stage") == "workspace_projection"),
        None,
    )
    latest_alert = next(
        (event for event in reversed(workspace_events) if event.get("stage") == "alert"),
        None,
    )
    return {
        "workspace_id": workspace_id,
        "exchange_enabled": exchange in enabled_exchanges,
        "pair_enabled_or_dynamic": not config.enabled_pairs or pair in config.enabled_pairs,
        "telegram_enabled": config.telegram_enabled,
        "telegram_destination_configured": telegram_destination_configured(
            token=config.telegram_bot_token,
            chat_id=config.telegram_chat_id,
        ),
        "telegram_alert_threshold": config.telegram_alert_threshold,
        "telegram_alert_types": list(config.telegram_alert_types),
        "latest_projection_status": latest_projection.get("status") if latest_projection else None,
        "latest_projection_reason": latest_projection.get("reason") if latest_projection else None,
        "latest_alert_status": latest_alert.get("status") if latest_alert else None,
        "latest_alert_reason": latest_alert.get("reason") if latest_alert else None,
    }


async def run_audit_retention_if_due(now: datetime | None = None) -> None:
    """Keep audit useful for diagnostics without turning it into raw market storage."""
    now = normalize_db_datetime(now or utcnow()) or utcnow()
    event_cutoff = now - timedelta(days=_PIPELINE_EVENT_RETENTION_DAYS)
    cycle_cutoff = now - timedelta(days=_SCANNER_CYCLE_AUDIT_RETENTION_DAYS)
    async with async_session() as session:
        await session.execute(delete(SignalPipelineEventRecord).where(SignalPipelineEventRecord.created_at < event_cutoff))
        await session.execute(delete(ScannerCycleAuditRecord).where(ScannerCycleAuditRecord.created_at < cycle_cutoff))
        await session.commit()


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
                executability_version=opp.executability_version,
                movement_version=opp.movement_version,
                profile_version=opp.profile_version,
                reweighting_version=opp.reweighting_version,
                volatility_pct=opp.volatility_pct,
                volume_24h=opp.volume_24h,
                quote_volume_24h=opp.quote_volume_24h,
                liquidity_units=opp.liquidity_units,
                bid_notional_top_n=opp.bid_notional_top_n,
                ask_notional_top_n=opp.ask_notional_top_n,
                total_notional_top_n=opp.total_notional_top_n,
                spread_pct=opp.spread_pct,
                executability_score=opp.executability_score,
                executability_band=opp.executability_band,
                interesting_signal=opp.interesting_signal,
                operable_signal=opp.operable_signal,
                estimated_trade_margin_pct=opp.estimated_trade_margin_pct,
                operational_friction_pct=opp.operational_friction_pct,
                estimated_net_trade_edge_pct=opp.estimated_net_trade_edge_pct,
                trade_margin_score=opp.trade_margin_score,
                opportunity_type=opp.opportunity_type,
                estimated_buy_slippage_bps=opp.estimated_buy_slippage_bps,
                estimated_sell_slippage_bps=opp.estimated_sell_slippage_bps,
                fillable_notional_within_slippage_cap=opp.fillable_notional_within_slippage_cap,
                baseline_order_notional_brl=opp.baseline_order_notional_brl,
                movement_type=opp.movement_type.value,
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
                last_price=opp.last_price,
                change_pct=opp.change_pct,
                detected_at=normalize_db_datetime(opp.detected_at),
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
                "executability_version": getattr(r, "executability_version", EXECUTABILITY_VERSION),
                "movement_version": getattr(r, "movement_version", MOVEMENT_VERSION),
                "profile_version": getattr(r, "profile_version", PROFILE_VERSION),
                "reweighting_version": getattr(r, "reweighting_version", REWEIGHTING_VERSION),
                "volatility_pct": r.volatility_pct,
                "volume_24h": r.volume_24h,
                "quote_volume_24h": r.quote_volume_24h,
                "liquidity_units": r.liquidity_units,
                "bid_notional_top_n": getattr(r, "bid_notional_top_n", None),
                "ask_notional_top_n": getattr(r, "ask_notional_top_n", None),
                "total_notional_top_n": getattr(r, "total_notional_top_n", None),
                "spread_pct": r.spread_pct,
                "executability_score": getattr(r, "executability_score", None),
                "executability_band": getattr(r, "executability_band", None),
                "interesting_signal": getattr(r, "interesting_signal", None),
                "operable_signal": getattr(r, "operable_signal", None),
                "estimated_trade_margin_pct": getattr(r, "estimated_trade_margin_pct", None),
                "operational_friction_pct": getattr(r, "operational_friction_pct", None),
                "estimated_net_trade_edge_pct": getattr(r, "estimated_net_trade_edge_pct", None),
                "trade_margin_score": getattr(r, "trade_margin_score", None),
                "opportunity_type": getattr(r, "opportunity_type", None),
                "estimated_buy_slippage_bps": getattr(r, "estimated_buy_slippage_bps", None),
                "estimated_sell_slippage_bps": getattr(r, "estimated_sell_slippage_bps", None),
                "fillable_notional_within_slippage_cap": getattr(r, "fillable_notional_within_slippage_cap", None),
                "baseline_order_notional_brl": getattr(r, "baseline_order_notional_brl", None),
                "movement_type": r.movement_type,
                "movement_regime": getattr(r, "movement_regime", None),
                "movement_phase": getattr(r, "movement_phase", None) or "neutral",
                "phase_confidence_score": getattr(r, "phase_confidence_score", None),
                "phase_reason": getattr(r, "phase_reason", None),
                "is_late_entry_risk": getattr(r, "is_late_entry_risk", False),
                "is_profit_zone_candidate": getattr(r, "is_profit_zone_candidate", False),
                "distance_from_accumulation_zone_pct": getattr(r, "distance_from_accumulation_zone_pct", None),
                "distance_from_breakout_pct": getattr(r, "distance_from_breakout_pct", None),
                "operational_buy_zone_low": getattr(r, "operational_buy_zone_low", None),
                "operational_buy_zone_high": getattr(r, "operational_buy_zone_high", None),
                "operational_sell_zone_low": getattr(r, "operational_sell_zone_low", None),
                "operational_sell_zone_high": getattr(r, "operational_sell_zone_high", None),
                "operational_range_margin_pct": getattr(r, "operational_range_margin_pct", None),
                "range_reuse_count": getattr(r, "range_reuse_count", 0),
                "range_reliability_score": getattr(r, "range_reliability_score", None),
                "zone_liquidity_score": getattr(r, "zone_liquidity_score", None),
                "capital_capacity_estimate_brl": getattr(r, "capital_capacity_estimate_brl", None),
                "operational_range_quality": getattr(r, "operational_range_quality", None) or "none",
                "alert_moment_type": getattr(r, "alert_moment_type", None) or "neutral",
                "alert_reason": getattr(r, "alert_reason", None),
                "movement_persistence_score": getattr(r, "movement_persistence_score", None),
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
            TechnicalSignalRecord.semantic_signal_key,
        ).where(TechnicalSignalRecord.detected_at >= cutoff)
        recent_result = await session.execute(recent_q)
        recent_rows = recent_result.all()
        recent_keys: set[tuple[str, str]] = {(r[0], r[1]) for r in recent_rows}
        recent_semantic_keys: set[str] = {r[2] for r in recent_rows if r[2]}

        for opp in opportunities:
            exchange_val = opp.exchange.value
            key = (exchange_val, opp.pair)
            if key in recent_keys and (not opp.semantic_signal_key or opp.semantic_signal_key in recent_semantic_keys):
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
                executability_version=opp.executability_version,
                movement_version=opp.movement_version,
                profile_version=opp.profile_version,
                reweighting_version=opp.reweighting_version,
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
                movement_regime=opp.movement_regime.value if opp.movement_regime else None,
                movement_phase=opp.movement_phase.value if hasattr(opp.movement_phase, "value") else opp.movement_phase,
                phase_confidence_score=opp.phase_confidence_score,
                phase_reason=opp.phase_reason,
                is_late_entry_risk=opp.is_late_entry_risk,
                is_profit_zone_candidate=opp.is_profit_zone_candidate,
                distance_from_accumulation_zone_pct=opp.distance_from_accumulation_zone_pct,
                distance_from_breakout_pct=opp.distance_from_breakout_pct,
                operational_range_margin_pct=opp.operational_range_margin_pct,
                operational_range_quality=opp.operational_range_quality,
                alert_moment_type=opp.alert_moment_type,
                alert_reason=opp.alert_reason,
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
                semantic_signal_key=opp.semantic_signal_key,
                detected_at=normalize_db_datetime(opp.detected_at),
            )
            session.add(record)
            signal_map[opp.id] = signal_id
            recent_keys.add(key)
            if opp.semantic_signal_key:
                recent_semantic_keys.add(opp.semantic_signal_key)

        if signal_map:
            await session.commit()

    logger.info("technical_signals_saved count=%s", len(signal_map))
    return signal_map


async def save_raw_market_observations(opportunities: list[Opportunity], cycle_id: str) -> int:
    if not opportunities:
        return 0

    async with async_session() as session:
        for opp in opportunities:
            session.add(
                RawMarketObservationRecord(
                    observation_cycle_id=cycle_id,
                    exchange=opp.exchange.value,
                    pair=opp.pair,
                    semantic_signal_key=opp.semantic_signal_key,
                    movement_type=opp.movement_type.value,
                    movement_regime=opp.movement_regime.value if opp.movement_regime else None,
                    movement_phase=opp.movement_phase.value if hasattr(opp.movement_phase, "value") else opp.movement_phase,
                    phase_confidence_score=opp.phase_confidence_score,
                    phase_reason=opp.phase_reason,
                    is_late_entry_risk=opp.is_late_entry_risk,
                    is_profit_zone_candidate=opp.is_profit_zone_candidate,
                    distance_from_accumulation_zone_pct=opp.distance_from_accumulation_zone_pct,
                    distance_from_breakout_pct=opp.distance_from_breakout_pct,
                    operational_range_margin_pct=opp.operational_range_margin_pct,
                    operational_range_quality=opp.operational_range_quality,
                    alert_moment_type=opp.alert_moment_type,
                    alert_reason=opp.alert_reason,
                    last_price=opp.last_price,
                    quote_volume_24h=opp.quote_volume_24h,
                    liquidity_units=opp.liquidity_units,
                    spread_pct=opp.spread_pct,
                    bid_notional_top_n=opp.bid_notional_top_n,
                    ask_notional_top_n=opp.ask_notional_top_n,
                    total_notional_top_n=opp.total_notional_top_n,
                    detected_at=normalize_db_datetime(opp.detected_at),
                )
            )
        await session.commit()
    return len(opportunities)


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
    score_version: str = SCORE_VERSION,
    executability_version: str = EXECUTABILITY_VERSION,
    movement_version: str = MOVEMENT_VERSION,
    profile_version: str = PROFILE_VERSION,
    reweighting_version: str = REWEIGHTING_VERSION,
) -> None:
    async with async_session() as session:
        record = WorkspaceSignalProjectionRecord(
            workspace_id=workspace_id,
            technical_signal_id=technical_signal_id,
            workspace_score=workspace_score,
            score_version=score_version,
            executability_version=executability_version,
            movement_version=movement_version,
            profile_version=profile_version,
            reweighting_version=reweighting_version,
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
                score_version=proj.get("score_version", SCORE_VERSION),
                executability_version=proj.get("executability_version", EXECUTABILITY_VERSION),
                movement_version=proj.get("movement_version", MOVEMENT_VERSION),
                profile_version=proj.get("profile_version", PROFILE_VERSION),
                reweighting_version=proj.get("reweighting_version", REWEIGHTING_VERSION),
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
                late_signal_detected=sig.get("late_signal_detected"),
                signal_detected_at=normalize_db_datetime(sig["signal_detected_at"]),
                created_at=utcnow(),
            )
            session.add(record)
        await session.commit()

    return len(signals)


async def get_pending_outcomes(
    *,
    min_age_minutes: int = 5,
    max_age_hours: int = 25,
    limit: int = 100,
) -> list[dict]:
    """Get outcomes that haven't been fully evaluated yet."""
    now = utcnow()
    min_age_cutoff = now - timedelta(minutes=min_age_minutes)
    max_age_cutoff = now - timedelta(hours=max_age_hours)

    async with async_session() as session:
        missing_windows = [
            SignalOutcomeRecord.price_after_5m.is_(None),
            SignalOutcomeRecord.price_after_15m.is_(None),
            SignalOutcomeRecord.price_after_1h.is_(None),
            SignalOutcomeRecord.price_after_4h.is_(None),
        ]
        if max_age_hours >= 24:
            missing_windows.append(SignalOutcomeRecord.price_after_24h.is_(None))

        query = (
            select(SignalOutcomeRecord)
            .where(
                SignalOutcomeRecord.signal_detected_at <= min_age_cutoff,
                SignalOutcomeRecord.signal_detected_at >= max_age_cutoff,
                or_(*missing_windows),
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
                "late_signal_detected": getattr(r, "late_signal_detected", None),
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
    price_after_24h: float | None = None,
    max_price_1h: float | None = None,
    min_price_1h: float | None = None,
    max_price_after_signal: float | None = None,
    min_price_after_signal: float | None = None,
    volume_after_signal: float | None = None,
    late_signal_detected: bool | None = None,
) -> None:
    """Update an outcome with price observations."""
    async with async_session() as session:
        record = await session.get(SignalOutcomeRecord, outcome_id)
        if record is None:
            return

        if price_after_5m is not None and record.price_after_5m is None:
            record.price_after_5m = price_after_5m
            record.outcome_pct_5m = round((price_after_5m - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if price_after_15m is not None and record.price_after_15m is None:
            record.price_after_15m = price_after_15m
            record.outcome_pct_15m = round((price_after_15m - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if price_after_1h is not None and record.price_after_1h is None:
            record.price_after_1h = price_after_1h
            record.outcome_pct_1h = round((price_after_1h - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if price_after_4h is not None and record.price_after_4h is None:
            record.price_after_4h = price_after_4h
            record.outcome_pct_4h = round((price_after_4h - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if price_after_24h is not None and record.price_after_24h is None:
            record.price_after_24h = price_after_24h
            record.outcome_pct_24h = round((price_after_24h - record.entry_price) / record.entry_price * 100, 4) if record.entry_price else None
        if max_price_1h is not None:
            record.max_price_1h = max(
                [value for value in (record.max_price_1h, max_price_1h) if value is not None]
            )
        if min_price_1h is not None:
            record.min_price_1h = min(
                [value for value in (record.min_price_1h, min_price_1h) if value is not None]
            )
        if max_price_after_signal is not None:
            record.max_price_after_signal = max(
                [value for value in (record.max_price_after_signal, max_price_after_signal) if value is not None]
            )
        if min_price_after_signal is not None:
            record.min_price_after_signal = min(
                [value for value in (record.min_price_after_signal, min_price_after_signal) if value is not None]
            )
        if volume_after_signal is not None:
            record.volume_after_signal = volume_after_signal
        if late_signal_detected is not None:
            record.late_signal_detected = late_signal_detected

        if record.entry_price:
            if record.max_price_after_signal is not None:
                record.max_favorable_excursion_pct = round(
                    (record.max_price_after_signal - record.entry_price) / record.entry_price * 100,
                    4,
                )
            if record.min_price_after_signal is not None:
                record.max_adverse_excursion_pct = round(
                    (record.min_price_after_signal - record.entry_price) / record.entry_price * 100,
                    4,
                )

        best_return = max(
            [
                value
                for value in (
                    record.outcome_pct_5m,
                    record.outcome_pct_15m,
                    record.outcome_pct_1h,
                    record.outcome_pct_4h,
                    record.outcome_pct_24h,
                    record.max_favorable_excursion_pct,
                )
                if value is not None
            ],
            default=None,
        )
        worst_return = min(
            [
                value
                for value in (
                    record.outcome_pct_5m,
                    record.outcome_pct_15m,
                    record.outcome_pct_1h,
                    record.outcome_pct_4h,
                    record.outcome_pct_24h,
                    record.max_adverse_excursion_pct,
                )
                if value is not None
            ],
            default=None,
        )
        record.movement_continued = (
            (record.outcome_pct_1h is not None and record.outcome_pct_1h > 0.5)
            or (record.outcome_pct_4h is not None and record.outcome_pct_4h > 1.0)
            or (record.outcome_pct_24h is not None and record.outcome_pct_24h > 2.0)
        )
        record.breakout_confirmed = best_return is not None and best_return >= 2.0
        record.outcome_label = _classify_outcome_label(
            best_return=best_return,
            worst_return=worst_return,
            late_signal_detected=record.late_signal_detected,
            movement_continued=record.movement_continued,
        )

        if all(
            value is not None
            for value in (
                record.price_after_5m,
                record.price_after_15m,
                record.price_after_1h,
                record.price_after_4h,
            )
        ):
            record.evaluated_at = utcnow()
        await session.commit()


def _classify_outcome_label(
    *,
    best_return: float | None,
    worst_return: float | None,
    late_signal_detected: bool | None,
    movement_continued: bool | None,
) -> str | None:
    if best_return is None and worst_return is None:
        return None
    if late_signal_detected and (best_return or 0) < 1.0:
        return "late"
    if best_return is not None and best_return >= 5.0:
        return "excellent"
    if best_return is not None and best_return >= 2.0 and movement_continued:
        return "good"
    if worst_return is not None and worst_return <= -3.0 and (best_return or 0) < 1.0:
        return "false_positive"
    if best_return is not None and best_return < 0.5:
        return "neutral"
    return "good" if movement_continued else "neutral"


async def create_signal_feedback(
    *,
    signal_id: str | None,
    opportunity_id: str | None,
    user_id: str | None,
    workspace_id: str | None,
    feedback_label: str,
    feedback_note: str | None = None,
) -> dict:
    async with async_session() as session:
        record = SignalFeedbackRecord(
            signal_id=signal_id,
            opportunity_id=opportunity_id,
            user_id=user_id,
            workspace_id=workspace_id,
            feedback_label=feedback_label,
            feedback_note=feedback_note,
            created_at=utcnow(),
        )
        session.add(record)
        await session.commit()
        return {
            "id": record.id,
            "signal_id": record.signal_id,
            "opportunity_id": record.opportunity_id,
            "user_id": record.user_id,
            "workspace_id": record.workspace_id,
            "feedback_label": record.feedback_label,
            "feedback_note": record.feedback_note,
            "created_at": record.created_at,
        }


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
