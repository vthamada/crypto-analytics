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
from app.api.routes import router, update_state, get_scan_config, set_scan_config
from app.api.websocket import websocket_endpoint, manager
from app.services.scanner import Scanner
from app.services.persistence import (
    build_merged_scan_config,
    get_historical_pair_calibration,
    load_all_workspace_configs,
    save_opportunities,
)
from app.services.monitoring import scan_monitor
from app.services.logging_handlers import HTTPLogHandler
from app.services.auth import ensure_admin_bootstrap
from app.services.telegram import send_telegram_alert

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
    while True:
        cycle_started = time.perf_counter()
        scan_monitor.begin_cycle()
        try:
            workspace_configs = await load_all_workspace_configs()
            config = build_merged_scan_config(list(workspace_configs.values()))
            set_scan_config(config)

            if scanner is None or scanner.config != config:
                if scanner is not None:
                    await scanner.close()
                scanner = Scanner(config)
                logger.info("Scanner configuration refreshed")

            scanner.set_historical_calibration(await get_historical_pair_calibration())
            opportunities = await scanner.scan_all()
            now = datetime.now(timezone.utc)
            update_state(opportunities, now)

            # Persist to database
            if opportunities:
                await save_opportunities(opportunities)

            # Broadcast via WebSocket
            await manager.broadcast({
                "type": "opportunities_update",
                "data": [o.model_dump(exclude={"klines"}, mode="json") for o in opportunities],
                "timestamp": now.isoformat(),
                "count": len(opportunities),
            })

            # Send Telegram alert for high-score opportunities
            if config.telegram_enabled:
                high_score = [o for o in opportunities if o.score >= 60]
                if high_score:
                    await send_telegram_alert(
                        high_score,
                        token=config.telegram_bot_token,
                        chat_id=config.telegram_chat_id,
                    )

            logger.info(
                "scan_cycle_complete opportunities=%s next_scan_seconds=%s duration_ms=%.2f",
                len(opportunities),
                config.scan_interval_seconds,
                (time.perf_counter() - cycle_started) * 1000,
            )
            scan_monitor.complete_cycle(
                opportunities_count=len(opportunities),
                duration_ms=(time.perf_counter() - cycle_started) * 1000,
            )

        except Exception as e:
            scan_monitor.fail_cycle(str(e), duration_ms=(time.perf_counter() - cycle_started) * 1000)
            logger.error("scan_loop_error error=%s", e, exc_info=True)

        await asyncio.sleep(get_scan_config().scan_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scan_task, scanner

    # Initialize database
    await init_db()
    await ensure_admin_bootstrap()

    workspace_configs = await load_all_workspace_configs()
    merged_config = build_merged_scan_config(list(workspace_configs.values()))
    set_scan_config(merged_config)
    logger.info("Loaded workspace scan configuration")

    # Start scanner
    scanner = Scanner(get_scan_config())
    scan_task = asyncio.create_task(scan_loop())
    logger.info("Scanner started")

    yield

    # Shutdown
    if scan_task:
        scan_task.cancel()
        try:
            await scan_task
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
