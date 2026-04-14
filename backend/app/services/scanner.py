from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.models.schemas import (
    Exchange, Opportunity, Ticker, OrderBook, Kline,
    FilterThresholds, ScoreWeights, AppConfig,
)
from app.providers.base import ExchangeProvider
from app.providers.novadax import NovaDaxProvider
from app.providers.mercado_bitcoin import MercadoBitcoinProvider
from app.providers.binance import BinanceProvider
from app.filters.volatility import calculate_volatility, passes_volatility_filter, calculate_recent_change
from app.filters.volume import passes_volume_filter
from app.filters.liquidity import calculate_liquidity, passes_liquidity_filter
from app.filters.spread import calculate_spread, passes_spread_filter
from app.filters.movement import classify_movement
from app.filters.scoring import calculate_score

logger = logging.getLogger(__name__)


class Scanner:
    """Main scanner that collects data from all exchanges and detects opportunities."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self._providers: dict[Exchange, ExchangeProvider] = {}
        self._opportunities: list[Opportunity] = []
        self._repetition_counts: dict[str, int] = {}  # pair -> count
        self._running = False

        self._init_providers()

    def _init_providers(self) -> None:
        provider_map: dict[Exchange, type[ExchangeProvider]] = {
            Exchange.NOVADAX: NovaDaxProvider,
            Exchange.MERCADO_BITCOIN: MercadoBitcoinProvider,
            Exchange.BINANCE: BinanceProvider,
        }
        for exchange in self.config.enabled_exchanges:
            if exchange in provider_map:
                self._providers[exchange] = provider_map[exchange]()

    @property
    def opportunities(self) -> list[Opportunity]:
        return sorted(self._opportunities, key=lambda o: o.score, reverse=True)

    @property
    def providers(self) -> dict[Exchange, ExchangeProvider]:
        return self._providers

    async def scan_pair(self, provider: ExchangeProvider, pair: str) -> Opportunity | None:
        """Scan a single pair on a single exchange and return an opportunity if filters pass."""
        try:
            ticker, order_book, klines = await asyncio.gather(
                provider.get_ticker(pair),
                provider.get_order_book(pair),
                provider.get_klines(pair, interval="5m", limit=50),
                return_exceptions=True,
            )

            # Skip if any request failed
            if isinstance(ticker, Exception):
                logger.debug(f"[{provider.exchange}] Ticker failed for {pair}: {ticker}")
                return None
            if isinstance(order_book, Exception):
                logger.debug(f"[{provider.exchange}] OrderBook failed for {pair}: {order_book}")
                return None
            if isinstance(klines, Exception):
                logger.debug(f"[{provider.exchange}] Klines failed for {pair}: {klines}")
                return None

            thresholds = self.config.thresholds

            # Apply filters
            if not passes_volatility_filter(klines, thresholds.min_volatility_pct):
                return None

            if not passes_volume_filter(ticker, thresholds.min_volume_brl, thresholds.min_volume_brl_small):
                return None

            if not passes_liquidity_filter(order_book, thresholds.min_liquidity_units):
                return None

            if not passes_spread_filter(order_book, thresholds.max_spread_pct):
                return None

            # Classify movement
            movement_type = classify_movement(klines)

            # Track repetition
            key = f"{provider.exchange}:{pair}"
            self._repetition_counts[key] = self._repetition_counts.get(key, 0) + 1

            # Calculate score
            score = calculate_score(
                ticker=ticker,
                order_book=order_book,
                klines=klines,
                movement_type=movement_type,
                weights=self.config.weights,
                repetition_count=self._repetition_counts[key],
            )

            return Opportunity(
                id=str(uuid.uuid4()),
                exchange=provider.exchange,
                pair=pair,
                score=score,
                volatility_pct=round(calculate_volatility(klines), 2),
                volume_24h=ticker.volume_24h,
                quote_volume_24h=ticker.quote_volume_24h,
                liquidity_units=round(calculate_liquidity(order_book), 2),
                spread_pct=round(calculate_spread(order_book), 4),
                movement_type=movement_type,
                last_price=ticker.last_price,
                change_pct=round(calculate_recent_change(klines), 2),
                detected_at=datetime.now(timezone.utc),
                klines=klines[-20:],
            )

        except Exception as e:
            logger.error(f"[{provider.exchange}] Error scanning {pair}: {e}")
            return None

    async def scan_all(self) -> list[Opportunity]:
        """Run a full scan across all enabled exchanges and pairs."""
        tasks = []
        for exchange, provider in self._providers.items():
            for pair in self.config.enabled_pairs:
                tasks.append(self.scan_pair(provider, pair))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        new_opportunities = []
        for result in results:
            if isinstance(result, Opportunity):
                new_opportunities.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Scan task error: {result}")

        self._opportunities = new_opportunities
        logger.info(f"Scan complete: {len(new_opportunities)} opportunities found")
        return new_opportunities

    async def close(self) -> None:
        for provider in self._providers.values():
            await provider.close()
