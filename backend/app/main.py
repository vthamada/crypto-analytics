from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.database import init_db
from app.models.schemas import AppConfig, Opportunity
from app.api.routes import router, update_state, get_config, set_config
from app.api.websocket import websocket_endpoint, manager
from app.services.scanner import Scanner
from app.services.persistence import save_opportunities, load_config, save_config
from app.services.telegram import send_telegram_alert

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scanner: Scanner | None = None
scan_task: asyncio.Task | None = None


async def scan_loop() -> None:
    """Background task that periodically scans for opportunities."""
    global scanner
    while True:
        try:
            config = get_config()

            if scanner is None:
                scanner = Scanner(config)

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
                f"Scan cycle complete: {len(opportunities)} opportunities. "
                f"Next scan in {config.scan_interval_seconds}s"
            )

        except Exception as e:
            logger.error(f"Scan loop error: {e}", exc_info=True)

        await asyncio.sleep(get_config().scan_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scan_task, scanner

    # Initialize database
    await init_db()

    # Load saved config
    saved_config = await load_config()
    if saved_config:
        set_config(saved_config)
        logger.info("Loaded saved configuration")
    else:
        await save_config(get_config())
        logger.info("Saved default configuration")

    # Start scanner
    scanner = Scanner(get_config())
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.add_api_websocket_route("/ws", websocket_endpoint)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
