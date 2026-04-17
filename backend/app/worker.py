from __future__ import annotations

import asyncio
import logging
import time

from app.api.routes import get_scan_config, set_scan_config, update_state, project_workspace_opportunity
from app.models.database import init_db
from app.services.monitoring import scan_monitor
from app.services.auth import ensure_admin_bootstrap
from app.services.persistence import (
    build_merged_scan_config,
    get_historical_pair_calibration,
    load_all_workspace_configs,
    run_history_retention_if_due,
    save_opportunities,
)
from app.services.shared_state import (
    create_pending_outcomes,
    decay_stale_repetitions,
    load_repetition_counts,
    save_repetition_counts,
    save_technical_signals,
    save_workspace_projections_batch,
    update_scanner_runtime_state,
    utcnow,
    write_opportunity_snapshots,
)
from app.services.scan_runtime import wait_for_refresh_or_timeout
from app.services.scanner import Scanner
from app.services.telegram import send_telegram_alert
from app.services.outcome_evaluator import evaluate_pending_outcomes

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    await init_db()
    await ensure_admin_bootstrap()
    workspace_configs = await load_all_workspace_configs()
    merged_config = build_merged_scan_config(list(workspace_configs.values()))
    set_scan_config(merged_config)

    scanner: Scanner | None = None
    persisted_reps = await load_repetition_counts()

    while True:
        cycle_started = time.perf_counter()
        cycle_id = f"cycle-{int(time.time())}"
        now = utcnow()
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

            scanner.load_repetition_counts(persisted_reps)
            scanner.set_historical_calibration(await get_historical_pair_calibration())
            opportunities = await scanner.scan_all()
            now = utcnow()
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
                for opp in opportunities:
                    if opp.id in signal_map:
                        opp.technical_signal_id = signal_map[opp.id]
                await save_opportunities(opportunities)

            await run_history_retention_if_due(now=now)

            # Workspace projections and Telegram alerts
            all_projections: list[dict] = []
            for workspace_id, workspace_config in workspace_configs.items():
                if not (
                    workspace_config.telegram_enabled
                    and workspace_config.telegram_bot_token
                    and workspace_config.telegram_chat_id
                ):
                    continue

                projected_opportunities = [
                    projected
                    for projected in (
                        project_workspace_opportunity(opportunity, workspace_config)
                        for opportunity in opportunities
                    )
                    if projected is not None
                ]

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

                high_score = [opp for opp in projected_opportunities if opp.score >= alert_threshold]
                if high_score:
                    await send_telegram_alert(
                        high_score,
                        token=workspace_config.telegram_bot_token,
                        chat_id=workspace_config.telegram_chat_id,
                    )

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

            duration_ms = (time.perf_counter() - cycle_started) * 1000
            scan_monitor.complete_cycle(
                opportunities_count=len(opportunities),
                duration_ms=duration_ms,
            )
            await update_scanner_runtime_state(
                completed_at=utcnow(),
                success_at=utcnow(),
                duration_ms=duration_ms,
                opportunities_count=len(opportunities),
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - cycle_started) * 1000
            scan_monitor.fail_cycle(str(exc), duration_ms=duration_ms)
            logger.exception("worker_scan_failed error=%s", exc)
            await update_scanner_runtime_state(
                completed_at=utcnow(),
                duration_ms=duration_ms,
                error=str(exc),
            )

        await wait_for_refresh_or_timeout(get_scan_config().scan_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(run_worker())
