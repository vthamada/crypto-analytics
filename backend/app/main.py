from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.database import init_db
from app.models.schemas import AppConfig, Opportunity
from app.api.routes import router, update_state, get_scan_config, set_scan_config, project_workspace_opportunity
from app.api.websocket import websocket_endpoint, manager
from app.services.scanner import Scanner
from app.services.persistence import (
    DEFAULT_WORKSPACE_ID,
    build_merged_scan_config,
    get_historical_pair_calibration,
    load_config,
    load_all_workspace_configs,
    load_workspace_config,
    run_history_retention_if_due,
    save_opportunities,
)
from app.services.shared_state import (
    calculate_technical_score,
    count_workspace_alerts_sent_since,
    create_pending_outcomes,
    decay_stale_repetitions,
    get_scanner_runtime_state,
    load_scanner_pair_states,
    load_repetition_counts,
    read_opportunity_snapshots,
    run_audit_retention_if_due,
    save_raw_market_observations,
    save_repetition_counts,
    save_scanner_pair_states,
    save_scanner_cycle_audit,
    save_signal_pipeline_events,
    save_technical_signals,
    save_workspace_projections_batch,
    update_scanner_runtime_state,
    write_opportunity_snapshots,
)
from app.services.signal_audit import build_signal_pipeline_event, split_top_telegram_candidates
from app.services.workspace_profiles import (
    explain_alert_scope,
    explain_workspace_visibility,
    opportunity_matches_alert_scope,
)
from app.services.monitoring import scan_monitor
from app.services.logging_handlers import HTTPLogHandler
from app.services.auth import ensure_admin_bootstrap
from app.services.scan_runtime import wait_for_refresh_or_timeout
from app.services.telegram import send_telegram_alert, split_alerts_by_state_change, telegram_destination_configured
from app.services.operational_visibility import classify_alert_worthiness, is_telegram_alertable
from app.services.outcome_evaluator import evaluate_pending_outcomes

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except ImportError:  # pragma: no cover - optional dependency guard
    sentry_sdk = None
    FastApiIntegration = None

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scanner: Scanner | None = None
scan_task: asyncio.Task | None = None
api_only_broadcast_task: asyncio.Task | None = None


def init_observability() -> None:
    if not settings.sentry_dsn:
        return

    if sentry_sdk is None or FastApiIntegration is None:
        logger.warning("sentry_not_initialized reason=dependency_missing")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.0,
    )
    logger.info("sentry_initialized environment=%s", settings.sentry_environment)


def init_log_aggregation() -> None:
    if not settings.log_aggregation_url:
        return

    handler = HTTPLogHandler(
        url=settings.log_aggregation_url,
        token=settings.log_aggregation_token,
    )
    handler.setLevel(getattr(logging, settings.log_level))
    logging.getLogger().addHandler(handler)
    logger.info("log_aggregation_initialized url=%s", settings.log_aggregation_url)


async def scan_loop() -> None:
    """Background task that periodically scans for opportunities."""
    global scanner
    # Load persistent repetition counts on startup
    persisted_reps = await load_repetition_counts()
    persisted_pair_states = await load_scanner_pair_states()

    while True:
        cycle_started = time.perf_counter()
        cycle_id = f"cycle-{int(time.time())}"
        cycle_started_at = utcnow()
        scan_monitor.begin_cycle()
        await update_scanner_runtime_state(started_at=cycle_started_at)
        try:
            workspace_configs = await load_all_workspace_configs()
            config = build_merged_scan_config(list(workspace_configs.values()))
            set_scan_config(config)

            if scanner is None or scanner.config != config:
                if scanner is not None:
                    await scanner.close()
                scanner = Scanner(config)
                scanner.load_pair_scan_states(persisted_pair_states)
                logger.info("Scanner configuration refreshed")

            # Restore persistent repetition counts
            scanner.load_repetition_counts(persisted_reps)

            scanner.set_historical_calibration(await get_historical_pair_calibration())
            opportunities = await scanner.scan_all()
            scan_monitor.record_scan_diagnostics(scanner.scan_diagnostics)
            await save_signal_pipeline_events(cycle_id, scanner.pipeline_events)
            now = utcnow()
            update_state(opportunities, now)

            # Persist repetition counts
            persisted_reps = dict(scanner._repetition_counts)
            await save_repetition_counts(persisted_reps)
            persisted_pair_states = scanner.export_pair_scan_states()
            await save_scanner_pair_states(persisted_pair_states)
            await decay_stale_repetitions(max_age_minutes=30)

            # Write shared snapshot for API decoupling
            await write_opportunity_snapshots(opportunities, cycle_id)
            await save_raw_market_observations(opportunities, cycle_id)

            # Technical signals dual-write
            signal_map: dict[str, str] = {}
            if opportunities:
                signal_map = await save_technical_signals(opportunities)
                # Annotate opportunities with signal IDs
                for opp in opportunities:
                    if opp.id in signal_map:
                        opp.technical_signal_id = signal_map[opp.id]

                await save_opportunities(opportunities)

            await run_history_retention_if_due(now=now)
            await run_audit_retention_if_due(now=now)

            # Workspace projections and Telegram alerts
            projected_opportunities_by_workspace: dict[str, list] = {}
            all_projections: list[dict] = []
            alerts_sent = 0
            alerts_suppressed = 0
            alerts_created = 0
            alert_block_reasons: dict[str, int] = {}
            alert_events: list[dict] = []

            for workspace_id, workspace_config in workspace_configs.items():
                projected_opportunities = []
                for opportunity in opportunities:
                    visible, block_reason, visibility_details = explain_workspace_visibility(opportunity, workspace_config)
                    projected = project_workspace_opportunity(opportunity, workspace_config) if visible else None
                    if projected is None:
                        alert_block_reasons[block_reason or "workspace_projection_blocked"] = (
                            alert_block_reasons.get(block_reason or "workspace_projection_blocked", 0) + 1
                        )
                        alert_events.append(
                            build_signal_pipeline_event(
                                opportunity,
                                stage="workspace_projection",
                                status="blocked",
                                reason=block_reason or "workspace_projection_blocked",
                                event_type="workspace_projection",
                                workspace_id=workspace_id,
                                details=visibility_details,
                            )
                        )
                        continue

                    projected_opportunities.append(projected)
                    alert_events.append(
                        build_signal_pipeline_event(
                            projected,
                            stage="workspace_projection",
                            status="visible",
                            reason="config_match",
                            event_type="workspace_projection",
                            workspace_id=workspace_id,
                            details={
                                "score": projected.score,
                                "opportunity_type": projected.opportunity_type,
                                "operable_signal": projected.operable_signal,
                            },
                        )
                    )
                projected_opportunities_by_workspace[workspace_id] = projected_opportunities

                # Save workspace signal projections for signals that have IDs
                alert_threshold = getattr(workspace_config, "telegram_alert_threshold", 60.0)
                for projected in projected_opportunities:
                    if projected.technical_signal_id:
                        all_projections.append({
                            "workspace_id": workspace_id,
                            "technical_signal_id": projected.technical_signal_id,
                            "workspace_score": projected.score,
                            "score_version": projected.score_version,
                            "executability_version": projected.executability_version,
                            "movement_version": projected.movement_version,
                            "profile_version": projected.profile_version,
                            "reweighting_version": projected.reweighting_version,
                            "visible": True,
                            "alert_eligible": (
                                projected.score >= alert_threshold
                                and opportunity_matches_alert_scope(projected, workspace_config)
                                and is_telegram_alertable(projected)
                            ),
                            "alert_worthiness_score": projected.alert_worthiness_score,
                            "alert_trigger_type": projected.alert_trigger_type,
                            "has_actionable_trigger": projected.has_actionable_trigger,
                            "alert_state_key": projected.alert_state_key,
                            "alert_block_reason": projected.alert_block_reason,
                            "projection_reason": "config_match",
                        })

                await manager.broadcast_workspace(
                    workspace_id,
                    {
                        "type": "opportunities_update",
                        "data": [
                            opportunity.model_dump(exclude={"klines"}, mode="json")
                            for opportunity in projected_opportunities
                            if opportunity.operationally_visible
                        ],
                        "timestamp": now.isoformat(),
                        "count": len([opportunity for opportunity in projected_opportunities if opportunity.operationally_visible]),
                    },
                )

            # Batch save all workspace projections
            if all_projections:
                await save_workspace_projections_batch(all_projections)

            # Create pending outcomes for new technical signals
            outcome_entries = []
            for opp in opportunities:
                if opp.technical_signal_id:
                    outcome_entries.append({
                        "technical_signal_id": opp.technical_signal_id,
                        "exchange": opp.exchange.value,
                        "pair": opp.pair,
                        "entry_price": opp.last_price,
                        "late_signal_detected": opp.is_late_entry_risk,
                        "signal_detected_at": opp.detected_at,
                    })
            if outcome_entries:
                await create_pending_outcomes(outcome_entries)

            # Evaluate pending outcomes from previous cycles
            outcomes_evaluated = await evaluate_pending_outcomes(limit=50)

            # Send Telegram alerts with per-workspace configurable threshold
            for workspace_id, workspace_config in workspace_configs.items():
                projected_opportunities = projected_opportunities_by_workspace.get(workspace_id, [])
                if not (
                    workspace_config.telegram_enabled
                    and telegram_destination_configured(
                        token=workspace_config.telegram_bot_token,
                        chat_id=workspace_config.telegram_chat_id,
                    )
                ):
                    reason = "telegram_disabled" if not workspace_config.telegram_enabled else "telegram_not_configured"
                    alert_block_reasons[reason] = alert_block_reasons.get(reason, 0) + len(projected_opportunities)
                    for opp in projected_opportunities:
                        alert_events.append(
                            build_signal_pipeline_event(
                                opp,
                                stage="alert",
                                status="blocked",
                                reason=reason,
                                event_type="alert",
                                workspace_id=workspace_id,
                                details={"score": opp.score, "opportunity_type": opp.opportunity_type},
                            )
                        )
                    continue

                alert_threshold = getattr(workspace_config, "telegram_alert_threshold", 60.0)

                # Filter by alert types if configured
                alert_types = set(getattr(workspace_config, "telegram_alert_types", ["operable", "high_score", "arbitrage"]))
                eligible = []
                for opp in projected_opportunities:
                    is_alertable, alert_block_reason, alert_worthiness_details = classify_alert_worthiness(opp)
                    if not is_alertable:
                        reason = alert_block_reason or opp.visibility_reason or "opportunity_type_not_alertable"
                        alert_block_reasons[reason] = alert_block_reasons.get(reason, 0) + 1
                        alert_events.append(
                            build_signal_pipeline_event(
                                opp,
                                stage="alert",
                                status="blocked",
                                reason=reason,
                                event_type="alert",
                                workspace_id=workspace_id,
                                details={
                                    "score": opp.score,
                                    "opportunity_type": opp.opportunity_type,
                                    "pipeline_status": opp.pipeline_status,
                                    "operationally_visible": opp.operationally_visible,
                                    **alert_worthiness_details,
                                },
                            )
                        )
                        continue
                    in_scope, scope_reason, scope_details = explain_alert_scope(opp, workspace_config)
                    if not in_scope:
                        reason = scope_reason or "workspace_alert_scope_mismatch"
                        alert_block_reasons[reason] = alert_block_reasons.get(reason, 0) + 1
                        alert_events.append(
                            build_signal_pipeline_event(
                                opp,
                                stage="alert",
                                status="blocked",
                                reason=reason,
                                event_type="alert",
                                workspace_id=workspace_id,
                                details=scope_details,
                            )
                        )
                        continue
                    matches_alert_type = (
                        ("operable" in alert_types and bool(opp.operable_signal))
                        or ("high_score" in alert_types and opp.score >= alert_threshold)
                        or ("arbitrage" in alert_types and opp.arbitrage_available)
                    )
                    if not matches_alert_type:
                        alert_block_reasons["below_alert_threshold"] = alert_block_reasons.get("below_alert_threshold", 0) + 1
                        alert_events.append(
                            build_signal_pipeline_event(
                                opp,
                                stage="alert",
                                status="blocked",
                                reason="below_alert_threshold",
                                event_type="alert",
                                workspace_id=workspace_id,
                                details={
                                    "score": opp.score,
                                    "threshold": alert_threshold,
                                    "alert_types": sorted(alert_types),
                                },
                            )
                        )
                        continue
                    eligible.append(opp)

                if eligible:
                    alerts_created += len(eligible)
                    alert_candidates, lower_priority = split_top_telegram_candidates(eligible, top_n=5)
                    alerts_suppressed += len(lower_priority)
                    for opp in lower_priority:
                        alert_block_reasons["lower_than_competing_signals"] = alert_block_reasons.get("lower_than_competing_signals", 0) + 1
                        alert_events.append(
                            build_signal_pipeline_event(
                                opp,
                                stage="alert",
                                status="blocked",
                                reason="lower_than_competing_signals",
                                event_type="alert",
                                workspace_id=workspace_id,
                                details={"score": opp.score, "candidate_count": len(eligible), "top_n": 5},
                            )
                        )
                    daily_limit = workspace_config.telegram_daily_alert_limit
                    if daily_limit is not None and daily_limit >= 0:
                        day_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                        sent_today = await count_workspace_alerts_sent_since(workspace_id, day_start)
                        remaining_today = max(daily_limit - sent_today, 0)
                        if remaining_today < len(alert_candidates):
                            blocked_by_daily_limit = alert_candidates[remaining_today:]
                            alert_candidates = alert_candidates[:remaining_today]
                            alerts_suppressed += len(blocked_by_daily_limit)
                            alert_block_reasons["daily_alert_limit_reached"] = (
                                alert_block_reasons.get("daily_alert_limit_reached", 0) + len(blocked_by_daily_limit)
                            )
                            for opp in blocked_by_daily_limit:
                                alert_events.append(
                                    build_signal_pipeline_event(
                                        opp,
                                        stage="alert",
                                        status="blocked",
                                        reason="daily_alert_limit_reached",
                                        event_type="alert",
                                        workspace_id=workspace_id,
                                        details={
                                            "score": opp.score,
                                            "daily_limit": daily_limit,
                                            "sent_today": sent_today,
                                        },
                                    )
                                )
                    if not alert_candidates:
                        continue
                    alert_candidates, unchanged_state = split_alerts_by_state_change(
                        alert_candidates,
                        token=workspace_config.telegram_bot_token,
                        chat_id=workspace_config.telegram_chat_id,
                    )
                    if unchanged_state:
                        alerts_suppressed += len(unchanged_state)
                        alert_block_reasons["no_state_change"] = (
                            alert_block_reasons.get("no_state_change", 0) + len(unchanged_state)
                        )
                        for opp in unchanged_state:
                            alert_events.append(
                                build_signal_pipeline_event(
                                    opp,
                                    stage="alert",
                                    status="blocked",
                                    reason="no_state_change",
                                    event_type="alert",
                                    workspace_id=workspace_id,
                                    details={
                                        "score": opp.score,
                                        "alert_state_key": opp.alert_state_key,
                                        "alert_trigger_type": opp.alert_trigger_type,
                                        "alert_worthiness_score": opp.alert_worthiness_score,
                                    },
                                )
                            )
                    if not alert_candidates:
                        continue
                    sent = await send_telegram_alert(
                        alert_candidates,
                        token=workspace_config.telegram_bot_token,
                        chat_id=workspace_config.telegram_chat_id,
                        cooldown_seconds=workspace_config.telegram_alert_cooldown_seconds,
                    )
                    if sent:
                        alerts_sent += len(alert_candidates)
                    else:
                        alerts_suppressed += len(alert_candidates)
                    for opp in alert_candidates:
                        alert_events.append(
                            build_signal_pipeline_event(
                                opp,
                                stage="alert",
                                status="sent" if sent else "blocked",
                                reason="telegram_sent" if sent else "cooldown_active",
                                event_type="alert",
                                workspace_id=workspace_id,
                                details={"score": opp.score, "opportunity_type": opp.opportunity_type},
                            )
                        )
                else:
                    alerts_suppressed += len(projected_opportunities)

            if alert_events:
                await save_signal_pipeline_events(cycle_id, alert_events)

            duration_ms = (time.perf_counter() - cycle_started) * 1000
            logger.info(
                "scan_cycle_complete opportunities=%s next_scan_seconds=%s duration_ms=%.2f "
                "signals_saved=%s projections_saved=%s outcomes_evaluated=%s "
                "alerts_sent=%s alerts_suppressed=%s",
                len(opportunities),
                config.scan_interval_seconds,
                duration_ms,
                len(signal_map),
                len(all_projections),
                outcomes_evaluated,
                alerts_sent,
                alerts_suppressed,
            )
            scan_monitor.complete_cycle(
                opportunities_count=len(opportunities),
                duration_ms=duration_ms,
            )
            await update_scanner_runtime_state(
                completed_at=utcnow(),
                success_at=utcnow(),
                duration_ms=duration_ms,
                opportunities_count=len(opportunities),
                scan_diagnostics=scanner.scan_diagnostics,
            )
            await save_scanner_cycle_audit(
                cycle_id=cycle_id,
                started_at=cycle_started_at,
                completed_at=utcnow(),
                duration_ms=duration_ms,
                status="completed",
                diagnostics=scanner.scan_diagnostics,
                signals_created=len(signal_map),
                shortlist_count=len(opportunities),
                alerts_created=alerts_created,
                alerts_sent=alerts_sent,
                block_reasons=alert_block_reasons,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - cycle_started) * 1000
            scan_monitor.fail_cycle(str(e), duration_ms=duration_ms)
            logger.error("scan_loop_error error=%s", e, exc_info=True)
            await update_scanner_runtime_state(
                completed_at=utcnow(),
                duration_ms=duration_ms,
                error=str(e),
            )
            await save_scanner_cycle_audit(
                cycle_id=cycle_id,
                started_at=cycle_started_at,
                completed_at=utcnow(),
                duration_ms=duration_ms,
                status="failed",
                diagnostics=scanner.scan_diagnostics if scanner else {},
                error=str(e),
            )

        await wait_for_refresh_or_timeout(get_scan_config().scan_interval_seconds)


async def _build_workspace_broadcast_payloads(*, timestamp: str) -> int:
    if manager.connection_count == 0:
        return 0

    workspace_configs = await load_all_workspace_configs()
    if workspace_configs:
        set_scan_config(build_merged_scan_config(list(workspace_configs.values())))

    snapshots = await read_opportunity_snapshots()
    opportunities: list[Opportunity] = []
    for snapshot in snapshots:
        try:
            opportunities.append(Opportunity(**snapshot))
        except Exception:
            logger.warning("api_only_snapshot_deserialize_failed", exc_info=True)

    broadcasts = 0
    for workspace_id in manager.workspace_ids:
        config = workspace_configs.get(workspace_id)
        if config is None:
            if workspace_id == DEFAULT_WORKSPACE_ID:
                config = await load_config() or AppConfig()
            else:
                config = await load_workspace_config(workspace_id) or AppConfig()

        projected_opportunities = [
            projected
            for projected in (
                project_workspace_opportunity(opportunity, config)
                for opportunity in opportunities
            )
            if projected is not None and projected.operationally_visible
        ]

        await manager.broadcast_workspace(
            workspace_id,
            {
                "type": "opportunities_update",
                "data": [
                    opportunity.model_dump(exclude={"klines"}, mode="json")
                    for opportunity in projected_opportunities
                ],
                "timestamp": timestamp,
                "count": len(projected_opportunities),
            },
        )
        broadcasts += 1

    return broadcasts


async def api_only_broadcast_loop() -> None:
    last_completed_at: str | None = None

    while True:
        try:
            if manager.connection_count == 0:
                await asyncio.sleep(2)
                continue

            scanner_state = await get_scanner_runtime_state()
            completed_at = None if scanner_state is None else scanner_state.get("last_cycle_completed_at")
            if not completed_at or completed_at == last_completed_at:
                await asyncio.sleep(2)
                continue

            last_completed_at = completed_at
            broadcasts = await _build_workspace_broadcast_payloads(timestamp=completed_at)
            if broadcasts:
                logger.info(
                    "api_only_websocket_broadcast_complete workspaces=%s timestamp=%s",
                    broadcasts,
                    completed_at,
                )
        except Exception as exc:
            logger.error("api_only_websocket_broadcast_failed error=%s", exc, exc_info=True)

        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scan_task, scanner, api_only_broadcast_task

    # Initialize database
    await init_db()
    await ensure_admin_bootstrap()

    workspace_configs = await load_all_workspace_configs()
    merged_config = build_merged_scan_config(list(workspace_configs.values()))
    set_scan_config(merged_config)
    logger.info("Loaded workspace scan configuration")

    # Start scanner only if enabled (disabled in API-only mode)
    if settings.scanner_enabled:
        scanner = Scanner(get_scan_config())
        scan_task = asyncio.create_task(scan_loop())
        logger.info("Scanner started")
    else:
        api_only_broadcast_task = asyncio.create_task(api_only_broadcast_loop())
        logger.info("Scanner disabled (SCANNER_ENABLED=false) — running in API-only mode")

    yield

    # Shutdown
    if scan_task:
        scan_task.cancel()
        try:
            await scan_task
        except asyncio.CancelledError:
            pass
    if api_only_broadcast_task:
        api_only_broadcast_task.cancel()
        try:
            await api_only_broadcast_task
        except asyncio.CancelledError:
            pass
    if scanner:
        await scanner.close()
    logger.info("Scanner stopped")


app = FastAPI(
    title="Crypto Analytics",
    description="Cryptocurrency opportunity detection system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_observability()
init_log_aggregation()

app.include_router(router)
app.add_api_websocket_route("/ws", websocket_endpoint)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
