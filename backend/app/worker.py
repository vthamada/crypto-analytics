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
    run_audit_retention_if_due,
    save_raw_market_observations,
    save_repetition_counts,
    save_scanner_cycle_audit,
    save_signal_pipeline_events,
    save_technical_signals,
    save_workspace_projections_batch,
    update_scanner_runtime_state,
    utcnow,
    write_opportunity_snapshots,
)
from app.services.scan_runtime import wait_for_refresh_or_timeout
from app.services.scanner import Scanner
from app.services.telegram import send_telegram_alert, telegram_destination_configured
from app.services.outcome_evaluator import evaluate_pending_outcomes
from app.services.signal_audit import build_signal_pipeline_event, split_top_telegram_candidates
from app.services.workspace_profiles import (
    explain_alert_scope,
    explain_workspace_visibility,
    opportunity_matches_alert_scope,
)

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
            await decay_stale_repetitions(max_age_minutes=30)

            # Write shared snapshot for API decoupling
            await write_opportunity_snapshots(opportunities, cycle_id)
            await save_raw_market_observations(opportunities, cycle_id)

            # Technical signals dual-write
            signal_map: dict[str, str] = {}
            if opportunities:
                signal_map = await save_technical_signals(opportunities)
                for opp in opportunities:
                    if opp.id in signal_map:
                        opp.technical_signal_id = signal_map[opp.id]
                await save_opportunities(opportunities)

            await run_history_retention_if_due(now=now)
            await run_audit_retention_if_due(now=now)

            # Workspace projections and Telegram alerts
            all_projections: list[dict] = []
            alerts_created = 0
            alerts_sent = 0
            alert_block_reasons: dict[str, int] = {}
            alert_events: list[dict] = []
            for workspace_id, workspace_config in workspace_configs.items():
                projected_opportunities = []
                for opportunity in opportunities:
                    visible, block_reason, visibility_details = explain_workspace_visibility(opportunity, workspace_config)
                    projected = project_workspace_opportunity(opportunity, workspace_config) if visible else None
                    if projected is None:
                        reason = block_reason or "workspace_projection_blocked"
                        alert_block_reasons[reason] = alert_block_reasons.get(reason, 0) + 1
                        alert_events.append(
                            build_signal_pipeline_event(
                                opportunity,
                                stage="workspace_projection",
                                status="blocked",
                                reason=reason,
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
                            "alert_eligible": projected.score >= alert_threshold and opportunity_matches_alert_scope(projected, workspace_config),
                            "projection_reason": "config_match",
                        })

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

                alert_types = set(getattr(workspace_config, "telegram_alert_types", ["operable", "high_score", "arbitrage"]))
                eligible = []
                for opp in projected_opportunities:
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
                    sent = await send_telegram_alert(
                        alert_candidates,
                        token=workspace_config.telegram_bot_token,
                        chat_id=workspace_config.telegram_chat_id,
                        cooldown_seconds=workspace_config.telegram_alert_cooldown_seconds,
                    )
                    alerts_sent += len(alert_candidates) if sent else 0
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

            if all_projections:
                await save_workspace_projections_batch(all_projections)
            if alert_events:
                await save_signal_pipeline_events(cycle_id, alert_events)

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
        except Exception as exc:
            duration_ms = (time.perf_counter() - cycle_started) * 1000
            scan_monitor.fail_cycle(str(exc), duration_ms=duration_ms)
            logger.exception("worker_scan_failed error=%s", exc)
            await update_scanner_runtime_state(
                completed_at=utcnow(),
                duration_ms=duration_ms,
                error=str(exc),
            )
            await save_scanner_cycle_audit(
                cycle_id=cycle_id,
                started_at=cycle_started_at,
                completed_at=utcnow(),
                duration_ms=duration_ms,
                status="failed",
                diagnostics=scanner.scan_diagnostics if scanner else {},
                error=str(exc),
            )

        await wait_for_refresh_or_timeout(get_scan_config().scan_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(run_worker())
