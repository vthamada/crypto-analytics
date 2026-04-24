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
from app.services.pairs import get_scannable_pairs_by_exchange
from app.services.shared_state import (
    EXECUTABILITY_VERSION,
    MOVEMENT_VERSION,
    PROFILE_VERSION,
    SCORE_VERSION,
    calculate_technical_score,
)
from app.services.workspace_profiles import resolve_trading_profile
from app.filters.volatility import calculate_volatility, passes_volatility_filter, calculate_recent_change
from app.filters.volume import passes_volume_filter, volume_score
from app.filters.executability import (
    calculate_executability_score,
    classify_executability_band,
    estimate_fillable_notional,
    estimate_slippage_bps,
)
from app.filters.liquidity import (
    calculate_liquidity,
    calculate_notional_depth,
    calculate_total_notional_depth,
    passes_liquidity_filter,
    liquidity_score,
)
from app.filters.spread import calculate_spread, passes_spread_filter, spread_score
from app.filters.movement import classify_movement
from app.filters.movement import classify_movement_regime
from app.filters.scoring import calculate_score

logger = logging.getLogger(__name__)

DEFAULT_OPERABLE_EXECUTABILITY_SCORE = 60.0


MOVEMENT_MODIFIERS = {
    "strong_range": 1.15,
    "spike": 1.05,
    "weak": 0.7,
    "trap": 0.5,
}


class Scanner:
    """Main scanner that collects data from all exchanges and detects opportunities."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self._providers: dict[Exchange, ExchangeProvider] = {}
        self._opportunities: list[Opportunity] = []
        self._repetition_counts: dict[str, int] = {}  # pair -> count
        self._historical_calibration: dict[str, dict[str, float]] = {}
        self._running = False

        self._init_providers()

    def load_repetition_counts(self, counts: dict[str, int]) -> None:
        """Restore repetition counts from persistent storage."""
        self._repetition_counts.update(counts)

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

    def set_historical_calibration(self, calibration: dict[str, dict[str, float]]) -> None:
        self._historical_calibration = calibration

    def _build_semantic_signal_key(
        self,
        *,
        exchange: Exchange,
        pair: str,
        movement_type: str,
        movement_regime: str | None,
    ) -> str:
        return ":".join(
            [
                exchange.value,
                pair,
                movement_type,
                movement_regime or "regime_unknown",
            ]
        )

    async def _get_scannable_pairs_by_exchange(self) -> dict[Exchange, list[str]]:
        enabled_exchanges = list(self._providers.keys())
        try:
            return await get_scannable_pairs_by_exchange(
                enabled_pairs=self.config.enabled_pairs,
                enabled_exchanges=enabled_exchanges,
            )
        except Exception as exc:
            logger.warning("scan_pair_catalog_filter_failed error=%s", exc)
            return {
                exchange: list(self.config.enabled_pairs)
                for exchange in enabled_exchanges
            }

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
            trading_profile = resolve_trading_profile(self.config)

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
            movement_regime = classify_movement_regime(
                klines,
                spread_pct=round(calculate_spread(order_book), 4),
                quote_volume_24h=ticker.quote_volume_24h,
            )

            # Track repetition
            key = f"{provider.exchange}:{pair}"
            self._repetition_counts[key] = self._repetition_counts.get(key, 0) + 1
            duration_minutes = round((self._repetition_counts[key] * self.config.scan_interval_seconds) / 60, 2)
            persistence_baseline = min(duration_minutes / 20.0, 1.0)
            movement_persistence_score = round(
                min(
                    1.0,
                    persistence_baseline
                    * (1.1 if movement_type.value in {"strong_range", "spike"} else 0.95),
                ),
                4,
            )
            semantic_signal_key = self._build_semantic_signal_key(
                exchange=provider.exchange,
                pair=pair,
                movement_type=movement_type.value,
                movement_regime=movement_regime.value,
            )

            # Calculate score
            volatility_pct = calculate_volatility(klines)
            volatility_component = min(volatility_pct / 10.0, 1.0)
            volume_component = volume_score(ticker)
            liquidity_component = liquidity_score(order_book)
            spread_component = spread_score(order_book)
            repetition_component = min(self._repetition_counts[key] / 5.0, 1.0)
            movement_multiplier = MOVEMENT_MODIFIERS.get(movement_type.value, 1.0)
            bid_notional_top_n = calculate_notional_depth(order_book, "bid")
            ask_notional_top_n = calculate_notional_depth(order_book, "ask")
            total_notional_top_n = calculate_total_notional_depth(order_book)
            estimated_buy_slippage_bps = estimate_slippage_bps(
                order_book,
                "buy",
                order_notional_brl=trading_profile.order_notional_brl,
            )
            estimated_sell_slippage_bps = estimate_slippage_bps(
                order_book,
                "sell",
                order_notional_brl=trading_profile.order_notional_brl,
            )
            fillable_notional_within_slippage_cap = min(
                estimate_fillable_notional(order_book, trading_profile.max_entry_slippage_bps, "buy"),
                estimate_fillable_notional(order_book, trading_profile.max_exit_slippage_bps, "sell"),
            )
            serialized_buy_slippage = (
                None if estimated_buy_slippage_bps == float("inf") else round(estimated_buy_slippage_bps, 2)
            )
            serialized_sell_slippage = (
                None if estimated_sell_slippage_bps == float("inf") else round(estimated_sell_slippage_bps, 2)
            )
            serialized_fillable_notional = round(fillable_notional_within_slippage_cap, 2)
            executability_score = calculate_executability_score(
                bid_notional_top_n=bid_notional_top_n,
                ask_notional_top_n=ask_notional_top_n,
                estimated_buy_slippage_bps=serialized_buy_slippage,
                estimated_sell_slippage_bps=serialized_sell_slippage,
                spread_pct=round(calculate_spread(order_book), 4),
                quote_volume_24h=ticker.quote_volume_24h,
                fillable_notional_within_slippage_cap=serialized_fillable_notional,
                order_notional_brl=trading_profile.order_notional_brl,
            )
            executability_band = classify_executability_band(executability_score)

            score = calculate_score(
                ticker=ticker,
                order_book=order_book,
                klines=klines,
                movement_type=movement_type,
                weights=self.config.weights,
                repetition_count=self._repetition_counts[key],
            )
            historical_confidence = self._historical_calibration.get(pair, {}).get("factor", 1.0)
            score = min(max(round(score * historical_confidence, 1), 0), 100)
            interesting_signal = score >= 40
            spread_pct = round(calculate_spread(order_book), 4)
            operable_signal = (
                executability_score >= DEFAULT_OPERABLE_EXECUTABILITY_SCORE
                and ticker.quote_volume_24h >= trading_profile.min_quote_volume_brl
                and serialized_sell_slippage is not None
                and serialized_sell_slippage <= trading_profile.max_exit_slippage_bps
                and serialized_buy_slippage is not None
                and serialized_buy_slippage <= trading_profile.max_entry_slippage_bps
                and spread_pct <= self.config.thresholds.max_spread_pct
                and movement_persistence_score >= 0.02
            )

            technical_score = calculate_technical_score(
                volatility_score=volatility_component,
                volume_score=volume_component,
                liquidity_score=liquidity_component,
                spread_score=spread_component,
                repetition_score=repetition_component,
                movement_multiplier=movement_multiplier,
                historical_confidence=historical_confidence,
            )

            return Opportunity(
                id=str(uuid.uuid4()),
                exchange=provider.exchange,
                pair=pair,
                score=score,
                technical_score=technical_score,
                score_version=SCORE_VERSION,
                executability_version=EXECUTABILITY_VERSION,
                movement_version=MOVEMENT_VERSION,
                profile_version=PROFILE_VERSION,
                executability_score=executability_score,
                executability_band=executability_band,
                interesting_signal=interesting_signal,
                operable_signal=operable_signal,
                semantic_signal_key=semantic_signal_key,
                reweighting_version="v1",
                volatility_pct=round(volatility_pct, 2),
                volume_24h=ticker.volume_24h,
                quote_volume_24h=ticker.quote_volume_24h,
                liquidity_units=round(calculate_liquidity(order_book), 2),
                bid_notional_top_n=round(bid_notional_top_n, 2),
                ask_notional_top_n=round(ask_notional_top_n, 2),
                total_notional_top_n=round(total_notional_top_n, 2),
                spread_pct=spread_pct,
                estimated_buy_slippage_bps=serialized_buy_slippage,
                estimated_sell_slippage_bps=serialized_sell_slippage,
                fillable_notional_within_slippage_cap=serialized_fillable_notional,
                baseline_order_notional_brl=trading_profile.order_notional_brl,
                movement_type=movement_type,
                movement_regime=movement_regime,
                movement_persistence_score=movement_persistence_score,
                last_price=ticker.last_price,
                change_pct=round(calculate_recent_change(klines), 2),
                detected_at=datetime.now(timezone.utc),
                duration_minutes=duration_minutes,
                historical_confidence=historical_confidence,
                volatility_score=round(volatility_component, 4),
                volume_score=round(volume_component, 4),
                liquidity_score=round(liquidity_component, 4),
                spread_score=round(spread_component, 4),
                repetition_score=round(repetition_component, 4),
                movement_multiplier=movement_multiplier,
                klines=klines[-20:],
            )

        except Exception as e:
            logger.error(f"[{provider.exchange}] Error scanning {pair}: {e}")
            return None

    async def scan_all(self) -> list[Opportunity]:
        """Run a full scan across all enabled exchanges and pairs."""
        tasks = []
        scannable_pairs = await self._get_scannable_pairs_by_exchange()
        for exchange, provider in self._providers.items():
            for pair in scannable_pairs.get(exchange, []):
                tasks.append(self.scan_pair(provider, pair))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        new_opportunities = []
        for result in results:
            if isinstance(result, Opportunity):
                new_opportunities.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Scan task error: {result}")

        self._opportunities = self._enrich_cross_exchange_context(new_opportunities)
        logger.info(f"Scan complete: {len(new_opportunities)} opportunities found")
        return self._opportunities

    def _enrich_cross_exchange_context(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        opportunities_by_pair: dict[str, list[Opportunity]] = {}
        for opportunity in opportunities:
            opportunities_by_pair.setdefault(opportunity.pair, []).append(opportunity)

        for pair_opportunities in opportunities_by_pair.values():
            if len(pair_opportunities) < 2:
                continue

            cheapest = min(pair_opportunities, key=lambda opp: opp.last_price)
            priciest = max(pair_opportunities, key=lambda opp: opp.last_price)
            avg_price = (cheapest.last_price + priciest.last_price) / 2
            if avg_price <= 0:
                continue

            gap_pct = abs(priciest.last_price - cheapest.last_price) / avg_price * 100
            estimated_friction = cheapest.spread_pct + priciest.spread_pct + 0.2
            arbitrage = gap_pct > estimated_friction

            for opportunity in pair_opportunities:
                reference = priciest if opportunity.exchange != priciest.exchange else cheapest
                opportunity.cross_exchange_gap_pct = round(gap_pct, 4)
                opportunity.cross_exchange_reference_exchange = reference.exchange
                opportunity.cross_exchange_reference_price = reference.last_price
                opportunity.arbitrage_available = arbitrage

                if arbitrage:
                    boosted = opportunity.score * 1.05
                    opportunity.score = min(round(boosted, 1), 100)

        return opportunities

    async def close(self) -> None:
        for provider in self._providers.values():
            await provider.close()
