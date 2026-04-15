from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.api.routes import get_scan_config, set_scan_config, update_state
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
from app.services.scan_runtime import wait_for_refresh_or_timeout
from app.services.scanner import Scanner
from app.services.telegram import send_telegram_alert

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    await init_db()
    await ensure_admin_bootstrap()
    workspace_configs = await load_all_workspace_configs()
    merged_config = build_merged_scan_config(list(workspace_configs.values()))
    set_scan_config(merged_config)

    scanner: Scanner | None = None

    while True:
        started_at = asyncio.get_running_loop().time()
        scan_monitor.begin_cycle()

        try:
            workspace_configs = await load_all_workspace_configs()
            config = build_merged_scan_config(list(workspace_configs.values()))
            set_scan_config(config)
            if scanner is None or scanner.config != config:
                if scanner is not None:
                    await scanner.close()
                scanner = Scanner(config)

            scanner.set_historical_calibration(await get_historical_pair_calibration())
            opportunities = await scanner.scan_all()
            now = datetime.now(timezone.utc)
            update_state(opportunities, now)

            if opportunities:
                await save_opportunities(opportunities)

            await run_history_retention_if_due(now=now)

            if config.telegram_enabled:
                high_score = [opportunity for opportunity in opportunities if opportunity.score >= 60]
                if high_score:
                    await send_telegram_alert(
                        high_score,
                        token=config.telegram_bot_token,
                        chat_id=config.telegram_chat_id,
                    )

            scan_monitor.complete_cycle(
                opportunities_count=len(opportunities),
                duration_ms=(asyncio.get_running_loop().time() - started_at) * 1000,
            )
        except Exception as exc:
            scan_monitor.fail_cycle(
                str(exc),
                duration_ms=(asyncio.get_running_loop().time() - started_at) * 1000,
            )
            logger.exception("worker_scan_failed error=%s", exc)

        await wait_for_refresh_or_timeout(get_scan_config().scan_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(run_worker())
