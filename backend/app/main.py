from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
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
    create_pending_outcomes,
    decay_stale_repetitions,
    get_scanner_runtime_state,
    load_repetition_counts,
    read_opportunity_snapshots,
    save_repetition_counts,
    save_technical_signals,
    save_workspace_projections_batch,
    update_scanner_runtime_state,
    write_opportunity_snapshots,
)
from app.services.monitoring import scan_monitor
from app.services.logging_handlers import HTTPLogHandler
from app.services.auth import ensure_admin_bootstrap
from app.services.scan_runtime import wait_for_refresh_or_timeout
from app.services.telegram import send_telegram_alert
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

    while True:
        cycle_started = time.perf_counter()
        cycle_id = f"cycle-{int(time.time())}"
        now = datetime.now(timezone.utc)
        scan_monitor.begin_cycle()
        await update_scanner_runtime_state(started_at=now)
        try:
            workspace_configs = await load_all_workspace_configs()
            config = build_merged_scan_config(list(workspace_configs.values()))
            set_scan_config(config)

            if scanner is None or scanner.config != config:
                if scanner is not None:
                    await scanner.close()
                scanner = Scanner(config)
                logger.info("Scanner configuration refreshed")

            # Restore persistent repetition counts
            scanner.load_repetition_counts(persisted_reps)

            scanner.set_historical_calibration(await get_historical_pair_calibration())
            opportunities = await scanner.scan_all()
            now = datetime.now(timezone.utc)
            update_state(opportunities, now)

            # Persist repetition counts
            persisted_reps = dict(scanner._repetition_counts)
            await save_repetition_counts(persisted_reps)
            await decay_stale_repetitions(max_age_minutes=30)

            # Write shared snapshot for API decoupling
            await write_opportunity_snapshots(opportunities, cycle_id)

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

            # Workspace projections and Telegram alerts
            projected_opportunities_by_workspace: dict[str, list] = {}
            all_projections: list[dict] = []
            alerts_sent = 0
            alerts_suppressed = 0

            for workspace_id, workspace_config in workspace_configs.items():
                projected_opportunities = [
                    projected
                    for projected in (
                        project_workspace_opportunity(opportunity, workspace_config)
                        for opportunity in opportunities
                    )
                    if projected is not None
                ]
                projected_opportunities_by_workspace[workspace_id] = projected_opportunities

                # Save workspace signal projections for signals that have IDs
                alert_threshold = getattr(workspace_config, "telegram_alert_threshold", 60.0)
                for projected in projected_opportunities:
                    if projected.technical_signal_id:
                        all_projections.append({
                            "workspace_id": workspace_id,
                            "technical_signal_id": projected.technical_signal_id,
                            "workspace_score": projected.score,
                            "visible": True,
                            "alert_eligible": projected.score >= alert_threshold,
                            "projection_reason": "config_match",
                        })

                await manager.broadcast_workspace(
                    workspace_id,
                    {
                        "type": "opportunities_update",
                        "data": [
                            opportunity.model_dump(exclude={"klines"}, mode="json")
                            for opportunity in projected_opportunities
                        ],
                        "timestamp": now.isoformat(),
                        "count": len(projected_opportunities),
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
                        "signal_detected_at": opp.detected_at,
                    })
            if outcome_entries:
                await create_pending_outcomes(outcome_entries)

            # Evaluate pending outcomes from previous cycles
            outcomes_evaluated = await evaluate_pending_outcomes(limit=50)

            # Send Telegram alerts with per-workspace configurable threshold
            for workspace_id, workspace_config in workspace_configs.items():
                if not (
                    workspace_config.telegram_enabled
                    and workspace_config.telegram_bot_token
                    and workspace_config.telegram_chat_id
                ):
                    continue

                alert_threshold = getattr(workspace_config, "telegram_alert_threshold", 60.0)
                projected_opportunities = projected_opportunities_by_workspace.get(workspace_id, [])
                high_score = [opp for opp in projected_opportunities if opp.score >= alert_threshold]

                # Filter by alert types if configured
                alert_types = getattr(workspace_config, "telegram_alert_types", ["high_score", "arbitrage"])
                eligible = []
                for opp in high_score:
                    if "high_score" in alert_types:
                        eligible.append(opp)
                    elif "arbitrage" in alert_types and opp.arbitrage_available:
                        eligible.append(opp)

                if eligible:
                    sent = await send_telegram_alert(
                        eligible,
                        token=workspace_config.telegram_bot_token,
                        chat_id=workspace_config.telegram_chat_id,
                    )
                    if sent:
                        alerts_sent += len(eligible)
                    else:
                        alerts_suppressed += len(eligible)
                else:
                    alerts_suppressed += len(high_score)

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
                completed_at=datetime.now(timezone.utc),
                success_at=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                opportunities_count=len(opportunities),
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - cycle_started) * 1000
            scan_monitor.fail_cycle(str(e), duration_ms=duration_ms)
            logger.error("scan_loop_error error=%s", e, exc_info=True)
            await update_scanner_runtime_state(
                completed_at=datetime.now(timezone.utc),
                duration_ms=duration_ms,
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
            if projected is not None
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
