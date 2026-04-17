"""Outcome evaluator — periodic job that fetches current prices for pending
signal outcomes and fills in the 5m / 15m / 1h / 4h price observations.

Designed to be called from scan_loop or as a standalone periodic task.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.models.schemas import Exchange
from app.providers.base import ExchangeProvider
from app.providers.binance import BinanceProvider
from app.providers.mercado_bitcoin import MercadoBitcoinProvider
from app.providers.novadax import NovaDaxProvider
from app.services.shared_state import get_pending_outcomes, update_outcome

logger = logging.getLogger(__name__)

_PROVIDER_MAP: dict[str, type[ExchangeProvider]] = {
    Exchange.NOVADAX.value: NovaDaxProvider,
    Exchange.MERCADO_BITCOIN.value: MercadoBitcoinProvider,
    Exchange.BINANCE.value: BinanceProvider,
}

# Time windows for outcome evaluation (minutes since signal detection)
_WINDOW_5M = timedelta(minutes=5)
_WINDOW_15M = timedelta(minutes=15)
_WINDOW_1H = timedelta(hours=1)
_WINDOW_4H = timedelta(hours=4)


def _window_ready(signal_detected_at: datetime, window: timedelta, now: datetime) -> bool:
    """Check if enough time has passed for this window to be evaluated."""
    return now >= signal_detected_at + window


async def evaluate_pending_outcomes(*, limit: int = 50) -> int:
    """Fetch current prices for pending outcomes and update the relevant
    time-window fields.  Returns the number of outcomes updated.

    The function is safe to call every scan cycle — it only fetches prices
    for outcomes whose time window has actually elapsed and that haven't
    been evaluated yet.
    """
    outcomes = await get_pending_outcomes(min_age_minutes=5, max_age_hours=5, limit=limit)
    if not outcomes:
        return 0

    now = datetime.now(timezone.utc)

    # Group by exchange to reuse provider instances
    by_exchange: dict[str, list[dict]] = {}
    for outcome in outcomes:
        by_exchange.setdefault(outcome["exchange"], []).append(outcome)

    providers: dict[str, ExchangeProvider] = {}
    updated = 0

    try:
        for exchange_key, exchange_outcomes in by_exchange.items():
            provider_cls = _PROVIDER_MAP.get(exchange_key)
            if provider_cls is None:
                logger.warning("outcome_evaluator_unknown_exchange exchange=%s", exchange_key)
                continue

            provider = providers.get(exchange_key)
            if provider is None:
                provider = provider_cls()
                providers[exchange_key] = provider

            # Deduplicate pairs — fetch ticker once per pair per exchange
            pairs_needed: dict[str, float | None] = {}
            for outcome in exchange_outcomes:
                pair = outcome["pair"]
                if pair not in pairs_needed:
                    pairs_needed[pair] = None

            # Fetch current price for each pair
            for pair in pairs_needed:
                try:
                    ticker = await provider.get_ticker(pair)
                    pairs_needed[pair] = ticker.last_price
                except Exception:
                    logger.warning(
                        "outcome_evaluator_ticker_failed exchange=%s pair=%s",
                        exchange_key, pair, exc_info=True,
                    )

            # Update each outcome with the current price for the appropriate windows
            for outcome in exchange_outcomes:
                current_price = pairs_needed.get(outcome["pair"])
                if current_price is None:
                    continue

                detected_at = outcome["signal_detected_at"]
                if isinstance(detected_at, str):
                    detected_at = datetime.fromisoformat(detected_at)
                if detected_at.tzinfo is None:
                    detected_at = detected_at.replace(tzinfo=timezone.utc)

                kwargs: dict[str, float] = {}
                within_1h_window = now <= detected_at + _WINDOW_1H

                if _window_ready(detected_at, _WINDOW_5M, now):
                    kwargs["price_after_5m"] = current_price
                if _window_ready(detected_at, _WINDOW_15M, now):
                    kwargs["price_after_15m"] = current_price
                if _window_ready(detected_at, _WINDOW_1H, now):
                    kwargs["price_after_1h"] = current_price
                if _window_ready(detected_at, _WINDOW_4H, now):
                    kwargs["price_after_4h"] = current_price

                # Track the observed range while the signal is still inside the first hour.
                if within_1h_window:
                    kwargs["max_price_1h"] = current_price
                    kwargs["min_price_1h"] = current_price

                if kwargs:
                    await update_outcome(outcome["id"], **kwargs)
                    updated += 1

    finally:
        for provider in providers.values():
            try:
                await provider.close()
            except Exception:
                pass

    if updated:
        logger.info("outcome_evaluator_complete updated=%s total_pending=%s", updated, len(outcomes))

    return updated
